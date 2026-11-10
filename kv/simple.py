# -*- coding: utf-8 -*-
"""Giao diện rút gọn: một nút KHÓA / MỞ cả lớp.

KHÓA = chặn mọi ứng dụng trừ danh sách được phép + chỉ cho vào các trang web trong danh sách (bằng chính sách trình duyệt nên gồm cả
tên miền con) + khóa Desktop (icon do giáo viên thiết kế; học sinh vẫn đổi hình nền và kéo icon được).
MỞ = gỡ ba thứ trên theo thứ tự ngược lại."""

import json
import os
import threading
import time

from .jobs import job_action, job_dist
from .network import tcp_open
from .paths import CONFIG_PATH
from .runtime import ApiError, CFG, CFG_LOCK, clean_hosts, list_path, log, split_host_port, start_job

FILE = os.path.join(os.path.dirname(CONFIG_PATH), 'simple.json')
LOCK = threading.RLock()
LOCK_STEPS = ('lockall-start', 'webonly', 'desklock-start')       # thứ tự khi khóa
UNLOCK_STEPS = ('desklock-stop', 'weboff', 'lockall-stop')        # thứ tự khi mở
STATE = {'locked': False, 'since': 0.0, 'hosts': [], 'busy': '', 'last': ''}


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


def simple_save():
    with LOCK:
        snap = {k: STATE[k] for k in ('locked', 'since', 'hosts', 'last')}
    try:
        with open(FILE, 'w', encoding='utf-8') as f:
            json.dump(snap, f, ensure_ascii=False)
    except OSError:
        pass


def api_simple(_q=None):
    with LOCK:
        d = dict(STATE, hosts=list(STATE['hosts']))
    with CFG_LOCK:
        d['hosts_n'] = len(CFG.get('hosts') or [])
    return d


def job_class_lock(on, hosts):
    from .deskdesign import desk_load, push_design
    with LOCK:
        STATE['busy'] = 'lock' if on else 'unlock'
    try:
        log('=== %s CẢ LỚP (%d máy) ===' % ('KHÓA' if on else 'MỞ KHÓA', len(hosts)), 'head')
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
            for kind in ('keep', 'allow', 'block'):   # máy học sinh luôn nhận bản danh sách mới nhất trước khi khóa
                try:
                    p = list_path(kind)
                    if os.path.isfile(p):
                        files.append(p)
                except Exception:  # noqa
                    pass
            if files:
                job_dist(online, files, 'none', '', '', False, target, 'Gửi danh sách ứng dụng và trang web được phép')
            d = desk_load()
            if d['items'] or d['wall']:
                push_design(online, d)
        for key in (LOCK_STEPS if on else UNLOCK_STEPS):
            job_action(key, online)
        with LOCK:
            STATE.update(locked=on, since=time.time() if on else 0.0, hosts=list(online) if on else [],
                         last='Đã khóa %d máy' % len(online) if on else 'Đã mở khóa %d máy' % len(online))
        simple_save()
        log('=== %s xong (%d máy) ===' % ('KHÓA' if on else 'MỞ KHÓA', len(online)), 'ok')
    finally:
        with LOCK:
            STATE['busy'] = ''


def api_simple_lock(b):
    on = bool(b.get('lock'))
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
    start_job(job_class_lock, on, hosts)
    return api_simple()
