# -*- coding: utf-8 -*-
"""Trạng thái máy học sinh: quét định kỳ ở nền và API trang Trạng thái máy."""

import threading
import time

from concurrent.futures import ThreadPoolExecutor

from .ai import ai_state_one
from .health import exam_snapshot, health_of, health_probe
from .applied import applied_list
from .network import mac_known, mac_learn, tcp_probe
from .remote import logged_on_user
from .runtime import CFG, CFG_LOCK, log, split_host_port


# ---------------------------------------------------------------- bảng trạng thái máy (từ bản 3.4.0)
STATUS = {}                      # máy -> thông tin lần kiểm tra gần nhất
STATUS_LOCK = threading.Lock()
STATUS_EVENT = threading.Event()
STATUS_WANT = [0.0]              # còn quét đến thời điểm này (giao diện mở trang trạng thái thì gia hạn)
STATUS_DEEP_SEC = 30             # giây giữa hai lần hỏi người đăng nhập và trạng thái AI của một máy
STATUS_DEEP_PENDING = set()
STATUS_POOL = ThreadPoolExecutor(max_workers=8)
PROBE_POOL = ThreadPoolExecutor(max_workers=64)  # riêng, để status_quick (chạy trong pool khác) không tự chờ chính nó


def status_quick(host):
    hh, pp = split_host_port(host)
    f_smb = PROBE_POOL.submit(tcp_probe, hh, 445, 0.8)  # hai cổng dò cùng lúc: máy tắt chỉ mất 0,8s thay vì 1,6s
    veyon = tcp_probe(hh, pp, 0.8)
    smb = f_smb.result()
    online = bool(veyon or smb)
    now = time.time()
    with STATUS_LOCK:
        old = STATUS.get(host) or {}
        e = dict(old)
        e.update({'host': host, 'online': online, 'veyon': bool(veyon), 'smb': bool(smb), 'checked': now})
        if old.get('online') != online:
            e['since'] = now
            if 'online' in old:
                log('[%s] %s' % (host, 'vừa bật máy' if online else 'vừa tắt hoặc mất kết nối'), 'ok' if online else 'warn')
        e.setdefault('since', now)
        if not online:
            e['user'] = ''
            e['ai'] = ''
            e['deep'] = 0
        STATUS[host] = e
    return online


def status_deep(host):
    """Việc chậm: hỏi ai đang đăng nhập, trạng thái khóa AI, đọc MAC. Chạy nền, mỗi máy mỗi STATUS_DEEP_SEC giây."""
    try:
        hh, _ = split_host_port(host)
        user = logged_on_user(hh)
        ai = 'unknown'
        with STATUS_LOCK:
            smb = (STATUS.get(host) or {}).get('smb')
        if smb:
            ok, txt = ai_state_one(host)
            ai = 'locked' if ok else ('half' if 'KHÓA DỞ' in txt else ('unknown' if 'không' in txt.lower() and 'CHƯA' not in txt else 'open'))
        if not mac_known(host):
            mac_learn(host)
        with STATUS_LOCK:
            e = STATUS.setdefault(host, {'host': host})
            e.update({'user': user, 'ai': ai, 'deep': time.time()})
        if smb:
            hp = health_probe(host)
            with STATUS_LOCK:
                STATUS.setdefault(host, {'host': host}).update(hp)
    finally:
        with STATUS_LOCK:
            STATUS_DEEP_PENDING.discard(host)


def status_cycle():
    with CFG_LOCK:
        hosts = list(CFG.get('hosts') or [])
    if not hosts:
        return
    with ThreadPoolExecutor(max_workers=min(64, len(hosts))) as ex:
        list(ex.map(status_quick, hosts))
    now = time.time()
    for h in hosts:
        with STATUS_LOCK:
            e = STATUS.get(h) or {}
            need = e.get('online') and now - e.get('deep', 0) > STATUS_DEEP_SEC and h not in STATUS_DEEP_PENDING
            if need:
                STATUS_DEEP_PENDING.add(h)
        if need:
            STATUS_POOL.submit(status_deep, h)


def status_loop():
    """Chạy nền: chỉ quét khi giao diện đang mở trang Trạng thái máy (hoặc đang chờ máy bật sau lệnh Bật/Tắt)."""
    while True:
        STATUS_EVENT.wait(5)
        STATUS_EVENT.clear()
        if time.time() > STATUS_WANT[0]:
            continue
        try:
            status_cycle()
        except Exception as e:  # noqa
            log('Lỗi quét trạng thái máy: %s' % e, 'err')


def api_status(q):
    now = time.time()
    STATUS_WANT[0] = now + 25
    if q.get('now'):
        STATUS_EVENT.set()
    with CFG_LOCK:
        hosts = list(CFG.get('hosts') or [])
        watching = {split_host_port(h)[0] for h in (CFG.get('watch_hosts') or [])}
    rows = []
    exam = exam_snapshot()
    for h in hosts:
        with STATUS_LOCK:
            e = dict(STATUS.get(h) or {})
        hh, _ = split_host_port(h)
        watching_now = hh in watching or h in watching
        level, probs = health_of({'online': bool(e.get('online')), 'veyon': bool(e.get('veyon')), 'smb': bool(e.get('smb')), 'svc': e.get('svc', '?'),
                                  'watch_alive': e.get('watch_alive'), 'watching': watching_now, 'ai': e.get('ai', '')} if e.get('checked') else {}, exam)
        rows.append({'health': level if e.get('checked') else 'wait', 'problems': probs, 'svc': e.get('svc', ''), 'watch_alive': e.get('watch_alive'), 'host': h, 'checked': bool(e.get('checked')), 'online': bool(e.get('online')), 'veyon': bool(e.get('veyon')),
                     'smb': bool(e.get('smb')), 'user': e.get('user', ''), 'ai': e.get('ai', ''), 'since': e.get('since', 0),
                     'age': int(now - e['checked']) if e.get('checked') else -1,
                     'watching': hh in watching or h in watching, 'restrict': applied_list(h), 'mac': mac_known(h)})
    return {'hosts': rows, 'ts': now, 'online': sum(1 for r in rows if r['online']), 'total': len(rows),
            'green': sum(1 for r in rows if r['health'] == 'green'), 'yellow': sum(1 for r in rows if r['health'] == 'yellow'),
            'red': sum(1 for r in rows if r['health'] == 'red'), 'off': sum(1 for r in rows if r['health'] == 'off')}
