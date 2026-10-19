# -*- coding: utf-8 -*-
"""Bật, tắt, khởi động lại, đăng xuất máy học sinh và lưu địa chỉ MAC."""

import re
import threading
import time

from .config import save_config
from .network import mac_known, mac_learn, mac_norm, pc_name_lookup, tcp_probe, wol_send
from .remote import remote_run, run_args
from .runtime import ApiError, CFG, CFG_LOCK, clean_hosts, log, pool_run, split_host_port, start_job
from .status import STATUS_EVENT


def logged_on_sessions(host):
    """Danh sách mã phiên đăng nhập (kể cả phiên đã ngắt kết nối) trên máy học sinh."""
    rc, out = run_args(['query', 'user', '/server:' + host], timeout=20)
    ids = []
    if rc != 0:
        return ids
    for line in out.splitlines()[1:]:
        t = line.replace('>', ' ').split()
        for tok in t[1:]:
            if tok.isdigit():
                ids.append(tok)
                break
    return ids


POWER_ACTIONS = {'wake': 'Bật máy (Wake-on-LAN)', 'shutdown': 'Tắt máy', 'restart': 'Khởi động lại', 'logoff': 'Đăng xuất học sinh',
                 'cancel': 'Hủy lệnh tắt máy', 'getmac': 'Lấy địa chỉ MAC'}


def power_one(action, host, delay):
    hh, pp = split_host_port(host)
    if action == 'wake':
        if tcp_probe(hh, pp, 1.0):
            return True, 'máy đã bật sẵn'
        mac = mac_known(host)
        if not mac:
            return False, 'chưa biết địa chỉ MAC của máy này. Bật máy lên một lần rồi bấm "Lấy MAC", hoặc nhập MAC tay'
        wol_send(mac, hh)
        return True, 'đã gửi gói đánh thức tới %s (máy cần bật Wake-on-LAN trong BIOS và card mạng)' % mac
    if action == 'getmac':
        if not (tcp_probe(hh, pp, 1.0) or tcp_probe(hh, 445, 1.0)):
            return False, 'máy đang tắt nên chưa đọc được MAC' + (' (đã nhớ: %s)' % mac_known(host) if mac_known(host) else '')
        mac = mac_learn(host)
        return (True, 'MAC %s' % mac) if mac else (False, 'không đọc được MAC (máy khác mạng LAN với máy giáo viên?)')
    if not (tcp_probe(hh, pp, 1.0) or tcp_probe(hh, 445, 1.0)):
        return False, 'máy đang tắt hoặc không truy cập được'
    if action == 'logoff':
        ids = logged_on_sessions(hh)
        if not ids:
            return True, 'không có ai đăng nhập'
        bad = []
        for sid in ids:
            rc, out = run_args(['logoff', sid, '/server:' + hh], timeout=30)
            if rc != 0:
                rc, out = remote_run(hh, 'cmd.exe /c logoff %s' % sid, name='KhoaVeyonPower')
            if rc != 0:
                bad.append('%s (%s)' % (sid, out[:80]))
        return (False, 'không đăng xuất được phiên ' + ', '.join(bad)) if bad else (True, 'đã đăng xuất %d phiên' % len(ids))
    if action == 'cancel':
        rc, out = remote_run(hh, 'cmd.exe /c shutdown /a', name='KhoaVeyonPower')
        return rc == 0, 'đã gửi lệnh hủy tắt máy' if rc == 0 else '(%s) %s' % (rc, out)
    sw = '/s' if action == 'shutdown' else '/r'
    rc, out = remote_run(hh, 'cmd.exe /c shutdown %s /t %d /f /c KhoaVeyon' % (sw, delay), name='KhoaVeyonPower')
    if rc != 0:
        return False, '(%s) %s' % (rc, out)
    return True, 'đã ra lệnh %s sau %d giây' % ('tắt máy' if action == 'shutdown' else 'khởi động lại', delay)


def job_power(action, hosts, delay):
    title = POWER_ACTIONS[action]
    log('>>> %s  (%d máy)' % (title, len(hosts)), 'head')
    pool_run(lambda h: power_one(action, h, delay), hosts, title)
    STATUS_EVENT.set()


def api_power(b):
    action = b.get('action')
    if action not in POWER_ACTIONS:
        raise ApiError('Lệnh không hợp lệ')
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào để chạy')
    try:
        delay = max(0, min(3600, int(b.get('delay') if b.get('delay') not in (None, '') else 30)))
    except (TypeError, ValueError):
        raise ApiError('Số giây chờ phải là số')
    start_job(job_power, action, hosts, delay)
    return {'ok': True}


_NAME_TRIED = {}   # IP -> thời điểm thử dò tên gần nhất (không dò lại quá dày với máy không có tên)
_NAME_BUSY = threading.Lock()


def _names_resolve_missing():
    if not _NAME_BUSY.acquire(blocking=False):
        return
    try:
        with CFG_LOCK:
            hosts = list(CFG.get('hosts') or [])
            known = dict(CFG.get('host_auto_names') or {})
        now = time.time()
        todo = []
        for h in hosts:
            hh, _ = split_host_port(h)
            if re.match(r'^\d{1,3}(\.\d{1,3}){3}$', hh) and h not in known and now - _NAME_TRIED.get(h, 0) > 600:
                todo.append((h, hh))
        found = {}
        for h, hh in todo:
            _NAME_TRIED[h] = now
            n = pc_name_lookup(hh)
            if n:
                found[h] = n
        if found:
            with CFG_LOCK:
                CFG.setdefault('host_auto_names', {}).update(found)
                save_config(CFG)
            log('Tự dò được tên PC: %s' % ', '.join('%s = %s' % (k, v) for k, v in found.items()), 'ok')
    finally:
        _NAME_BUSY.release()


def api_hostnames(_q=None):
    """Trả bảng tên hiển thị hiện có và chạy nền việc dò tên PC cho các máy đang để IP."""
    threading.Thread(target=_names_resolve_missing, daemon=True).start()
    with CFG_LOCK:
        return {'manual': dict(CFG.get('host_names') or {}), 'auto': dict(CFG.get('host_auto_names') or {})}


def api_hostname_set(b):
    """Đặt tên hiển thị cho máy: {host: tên}; tên rỗng thì xóa. Chỉ đổi cách hiện trên KhoaVeyon, kết nối vẫn dùng IP hoặc tên gốc."""
    items = b.get('names') or {}
    if not isinstance(items, dict):
        raise ApiError('Dữ liệu không hợp lệ')
    with CFG_LOCK:
        names = CFG.setdefault('host_names', {})
        for h, v in items.items():
            h, v = str(h).strip(), str(v or '').strip()[:40]
            if not h:
                continue
            if v:
                names[h] = v
            else:
                names.pop(h, None)
        save_config(CFG)
    return {'ok': True, 'names': dict(names)}


def api_macs_set(b):
    """Nhập MAC bằng tay: {host: mac}; MAC rỗng thì xóa."""
    items = b.get('macs') or {}
    if not isinstance(items, dict):
        raise ApiError('Dữ liệu không hợp lệ')
    with CFG_LOCK:
        macs = CFG.setdefault('macs', {})
        for h, v in items.items():
            h = str(h).strip()
            if not h:
                continue
            if not str(v or '').strip():
                macs.pop(h, None)
                continue
            m = mac_norm(v)
            if not m:
                raise ApiError('MAC của %s không hợp lệ (cần dạng AA-BB-CC-DD-EE-FF)' % h)
            macs[h] = m
        save_config(CFG)
    return {'ok': True}
