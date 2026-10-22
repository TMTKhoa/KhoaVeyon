# -*- coding: utf-8 -*-
"""Máy học sinh đổi IP do DHCP: nhận ra cùng một máy (theo MAC, rồi theo tên PC) và chuyển IP cũ sang IP mới,
giữ nguyên tên hiển thị và MAC, không để lại IP cũ không dùng được."""

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from .config import save_config
from .network import arp_mac, mac_norm, scan_veyon_hosts
from .runtime import CFG, CFG_LOCK, log

_IP = re.compile(r'^\d{1,3}(\.\d{1,3}){3}(:\d+)?$')
SYNC_EVERY = 600       # giây giữa hai lần tự quét khi có máy không thấy
_SCAN_LOCK = threading.Lock()


def _is_ip(h):
    return bool(_IP.match(str(h)))


def reconcile_hosts(hosts, found, names, found_macs, macs, host_names, auto_names):
    """Hàm thuần (dễ kiểm thử). Trả về (hosts mới, macs, host_names, auto_names, danh sách (IP cũ, IP mới)).
    Chỉ đổi cho máy IP cũ KHÔNG còn thấy trong mạng mà cùng MAC (hoặc cùng tên PC) với một IP mới được thấy.
    Máy chỉ đang tắt, không trùng với IP nào mới, thì giữ nguyên."""
    macs = {k: mac_norm(v) for k, v in (macs or {}).items() if mac_norm(v)}
    host_names, auto_names = dict(host_names or {}), dict(auto_names or {})
    found = list(found)
    fset = set(found)
    found_macs = {ip: mac_norm(m) for ip, m in (found_macs or {}).items() if mac_norm(m)}
    by_mac = {}
    for ip, m in found_macs.items():
        by_mac.setdefault(m, ip)
    owner_of_mac = {}
    for h, m in macs.items():
        owner_of_mac.setdefault(m, h)
    by_name = {}
    for ip, n in (names or {}).items():
        by_name.setdefault(str(n).upper(), []).append(ip)
    mac_label = {m: host_names[h] for h, m in macs.items() if h in host_names}
    claimed, moves, new_hosts, dropped = set(), [], [], []
    for h in hosts:
        if not _is_ip(h) or h in fset:
            new_hosts.append(h)
            continue
        target = None
        m = macs.get(h)
        if m and by_mac.get(m) and by_mac[m] != h and by_mac[m] not in claimed:
            target = by_mac[m]
        elif not m:
            nm = str(auto_names.get(h) or '').upper()
            cands = [ip for ip in by_name.get(nm, []) if ip not in claimed and ip not in hosts
                     and owner_of_mac.get(found_macs.get(ip)) in (None, h)] if nm and not nm.isdigit() else []
            if len(cands) == 1:
                target = cands[0]
        if not target:
            new_hosts.append(h)
            continue
        claimed.add(target)
        moves.append((h, target))
        dropped.append(h)
        if target in hosts or target in new_hosts:
            continue            # IP mới đã có trong danh sách: chỉ bỏ IP cũ
        new_hosts.append(target)
    for h in dropped:
        macs.pop(h, None); host_names.pop(h, None); auto_names.pop(h, None)
    for ip in found:
        if found_macs.get(ip):
            if macs.get(ip) and macs[ip] != found_macs[ip]:   # IP này nay thuộc máy khác (DHCP cấp lại): bỏ tên của máy cũ
                host_names.pop(ip, None)
            macs[ip] = found_macs[ip]
            if found_macs[ip] in mac_label:
                host_names[ip] = mac_label[found_macs[ip]]
        if (names or {}).get(ip):
            auto_names[ip] = names[ip]
    return new_hosts, macs, host_names, auto_names, moves


def scan_and_reconcile():
    """Quét mạng, nối IP mới với máy cũ, rồi thêm máy mới thấy. Trả về dict: found, names, moves, added, hosts, auto, macs."""
    found, names, err = scan_veyon_hosts()
    if err:
        return {'error': err}
    found_macs = {}
    if found:
        with ThreadPoolExecutor(max_workers=16) as ex:
            for ip, m in zip(found, ex.map(arp_mac, found)):
                if m:
                    found_macs[ip] = m
    added = 0
    with CFG_LOCK:
        hosts, macs, hn, auto, moves = reconcile_hosts(CFG.get('hosts') or [], found, names, found_macs,
                                                       CFG.get('macs'), CFG.get('host_names'), CFG.get('host_auto_names'))
        for ip in found:
            # máy đã có trong danh sách bằng tên PC (cùng tên dò được) thì không thêm trùng bằng IP
            have_name = names.get(ip) and any(str(h).strip().upper() == str(names[ip]).upper() for h in hosts)
            if ip not in hosts and not have_name:
                hosts.append(ip)
                added += 1
        CFG['hosts'], CFG['macs'], CFG['host_names'], CFG['host_auto_names'] = hosts, macs, hn, auto
        try:
            save_config(CFG)
        except OSError:
            pass
        out = {'found': found, 'names': names, 'moves': moves, 'added': added, 'hosts': list(hosts),
               'auto': dict(auto), 'manual': dict(hn), 'macs': dict(macs)}
    for old, new in moves:
        log('Máy đổi IP (DHCP): %s -> %s, đã chuyển tên và MAC sang IP mới, xóa IP cũ' % (old, new), 'ok')
    return out


def sync_loop():
    """Tự quét nền khi có máy không thấy (thường do đổi IP). Tắt được ở Cài đặt: auto_scan_ip."""
    time.sleep(150)
    while True:
        try:
            from .health import exam_snapshot
            from .status import STATUS
            with CFG_LOCK:
                on = CFG.get('auto_scan_ip', True)
                n = len(CFG.get('hosts') or [])
            gone = any(v.get('checked') and not v.get('online') and _is_ip(h) for h, v in list(STATUS.items()))
            if on and n and gone and not exam_snapshot().get('active') and _SCAN_LOCK.acquire(blocking=False):
                try:
                    r = scan_and_reconcile()
                    if r.get('moves'):
                        from .setup import refresh_agent_cfg
                        refresh_agent_cfg()
                finally:
                    _SCAN_LOCK.release()
        except Exception as e:  # noqa
            log('Lỗi tự quét IP: %s' % e, 'err')
        time.sleep(SYNC_EVERY)
