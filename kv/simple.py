# -*- coding: utf-8 -*-
"""Giao diện rút gọn: một nút KHÓA / MỞ cả lớp.

KHÓA = tối đa ba thứ, giáo viên bật/tắt từng thứ (opts): chặn mọi ứng dụng trừ danh sách được phép (apps) + chỉ cho vào các trang web
trong danh sách bằng chính sách trình duyệt, gồm cả tên miền con (web) + khóa Desktop: icon, vị trí icon và hình nền do giáo viên
thiết kế, học sinh không đổi được (desk). Chỉ khóa đúng những thứ được chọn.
MỞ = luôn gỡ cả ba thứ theo thứ tự ngược lại (gỡ thứ chưa khóa thì vô hại), nên đổi lựa chọn giữa chừng không để sót khóa."""

import json
import os
import threading
import time

from .jobs import job_action, job_dist
from .network import is_this_pc, tcp_open
from .paths import CONFIG_PATH
from .runtime import ApiError, CFG, CFG_LOCK, clean_hosts, list_path, log, split_host_port, start_job

FILE = os.path.join(os.path.dirname(CONFIG_PATH), 'simple.json')
LOCK = threading.RLock()
LOCK_STEPS = ('lockall-start', 'webonly', 'desklock-start')       # thứ tự khi khóa
UNLOCK_STEPS = ('desklock-stop', 'weboff', 'lockall-stop')        # thứ tự khi mở
OPT_STEP = {'apps': 'lockall-start', 'web': 'webonly', 'desk': 'desklock-start'}   # lựa chọn -> bước khóa tương ứng
DEFAULT_OPTS = {'apps': True, 'web': True, 'desk': True}
STATE = {'locked': False, 'since': 0.0, 'hosts': [], 'busy': '', 'last': '', 'opts': dict(DEFAULT_OPTS)}


def clean_opts(o):
    """Chỉ nhận ba khóa apps/web/desk. Thiếu khóa nào thì giữ mặc định (bật)."""
    o = o if isinstance(o, dict) else {}
    out = {k: (bool(o[k]) if k in o else v) for k, v in DEFAULT_OPTS.items()}
    return out


def lock_steps_for(opts):
    return tuple(OPT_STEP[k] for k in ('apps', 'web', 'desk') if opts.get(k))


def simple_load():
    try:
        with open(FILE, 'r', encoding='utf-8') as f:
            d = json.load(f)
    except (OSError, ValueError):
        return
    if isinstance(d, dict):
        with LOCK:
            for k in ('locked', 'since', 'hosts', 'last'):
                if k in d:
                    STATE[k] = d[k]
            if 'opts' in d:
                STATE['opts'] = clean_opts(d['opts'])


def simple_save():
    with LOCK:
        snap = {k: STATE[k] for k in ('locked', 'since', 'hosts', 'last', 'opts')}
    try:
        with open(FILE, 'w', encoding='utf-8') as f:
            json.dump(snap, f, ensure_ascii=False)
    except OSError:
        pass


def api_simple(_q=None):
    with LOCK:
        d = dict(STATE, hosts=list(STATE['hosts']), opts=dict(STATE['opts']))
    with CFG_LOCK:
        d['hosts_n'] = len(CFG.get('hosts') or [])
    return d


def job_class_lock(on, hosts, opts=None):
    from .deskdesign import desk_load, push_design
    opts = clean_opts(opts)
    with LOCK:
        STATE['busy'] = 'lock' if on else 'unlock'
    try:
        mine = [h for h in hosts if is_this_pc(h)]
        if mine:   # không bao giờ khóa chính máy giáo viên (máy đang chạy KhoaVeyon)
            log('Bỏ qua máy giáo viên (máy này) khỏi danh sách: %s' % ', '.join(mine), 'warn')
            hosts = [h for h in hosts if h not in mine]
        if not hosts:
            log('Không còn máy học sinh nào để %s' % ('khóa' if on else 'mở khóa'), 'err')
            return
        log('=== %s CẢ LỚP (%d máy)%s ===' % ('KHÓA' if on else 'MỞ KHÓA', len(hosts),
            (': ' + ', '.join(n for k, n in (('apps', 'ứng dụng'), ('web', 'trang web'), ('desk', 'Desktop')) if opts[k])) if on else ''), 'head')
        online = [h for h in hosts if tcp_open(*split_host_port(h), 1.5)]
        if len(online) < len(hosts):
            log('Bỏ qua %d máy đang tắt hoặc không trả lời: %s' % (len(hosts) - len(online), ', '.join(h for h in hosts if h not in online)), 'warn')
        if not online:
            log('Không có máy nào đang bật, chưa làm gì', 'err')
            return
        if on:
            with CFG_LOCK:
                target = CFG.get('dist_target') or r'C:\cmd'
            files = []
            for kind in ['block'] + [k for k, need in (('keep', 'apps'), ('allow', 'web')) if opts[need]]:   # máy học sinh luôn nhận bản danh sách mới nhất trước khi khóa
                try:
                    p = list_path(kind)
                    if os.path.isfile(p):
                        files.append(p)
                except Exception:  # noqa
                    pass
            if files:
                job_dist(online, files, 'none', '', '', False, target, 'Gửi danh sách ứng dụng và trang web được phép')
            if opts['desk']:
                d = desk_load()
                if d['items'] or d['wall']:
                    push_design(online, d)
        for key in (lock_steps_for(opts) if on else UNLOCK_STEPS):
            job_action(key, online)
        with LOCK:
            STATE.update(locked=on, since=time.time() if on else 0.0, hosts=list(online) if on else [], opts=opts if on else STATE['opts'],
                         last='Đã khóa %d máy' % len(online) if on else 'Đã mở khóa %d máy' % len(online))
        simple_save()
        log('=== %s xong (%d máy) ===' % ('KHÓA' if on else 'MỞ KHÓA', len(online)), 'ok')
    finally:
        with LOCK:
            STATE['busy'] = ''


def api_simple_lock(b):
    on = bool(b.get('lock'))
    opts = clean_opts(b.get('opts') if b.get('opts') is not None else STATE['opts'])
    if on and not any(opts.values()):
        raise ApiError('Hãy chọn ít nhất một thứ để khóa (ứng dụng, trang web hoặc Desktop)')
    hosts = clean_hosts(b.get('hosts'))
    if not on and not hosts:
        with LOCK:
            hosts = list(STATE['hosts'])   # mở khóa đúng những máy đã khóa, kể cả khi danh sách máy đã đổi
        with CFG_LOCK:
            hosts = clean_hosts(hosts + list(CFG.get('hosts') or []))
    if not hosts:
        raise ApiError('Chưa có máy nào. Hãy thêm máy hoặc quét mạng trước.')
    with LOCK:
        if STATE['busy']:
            raise ApiError('Đang %s, vui lòng đợi' % ('khóa' if STATE['busy'] == 'lock' else 'mở khóa'))
        STATE['busy'] = 'lock' if on else 'unlock'
        if on:
            STATE['opts'] = opts   # nhớ lựa chọn cho lần sau
    simple_save()
    start_job(job_class_lock, on, hosts, opts)
    return api_simple()
