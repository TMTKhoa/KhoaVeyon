# -*- coding: utf-8 -*-
"""Tự cập nhật dịch vụ trên máy học sinh: máy nào đang kết nối Agent mà đang chạy KhoaVeyonServices.bat bản cũ
thì chép bản mới nhất trong payload xuống và chạy -install (không cần Setup lại)."""

import time

import hashlib
import ntpath
import os

from .agent import agent_online
from .health import exam_snapshot, health_probe, job_fix_service
from .remote import rfs_sha, rfs_write
from .runtime import CFG, CFG_LOCK, log, PAYLOAD_DIR, split_host_port

CHECK_EVERY = 600      # giây giữa hai lần kiểm tra bản của một máy
RETRY_AFTER = 1800     # giây: máy đã thử cập nhật mà vẫn cũ thì chờ chừng này mới thử lại
MAX_PER_ROUND = 4      # mỗi vòng cập nhật tối đa chừng này máy, tránh nghẽn mạng và tránh làm cả lớp khởi động lại dịch vụ cùng lúc
EXTRA_FILES = ['KhoaVeyonStudent.ps1']   # tệp phụ trong payload đi cùng dịch vụ (trợ lý học sinh); chỉ cần chép, không cần -install
_LAST_CHECK = {}
_LAST_TRY = {}


def sync_extra_files(host):
    """Chép các tệp phụ trong payload xuống máy nếu thiếu hoặc khác bản mới nhất. Trả về danh sách tệp đã chép."""
    with CFG_LOCK:
        sp = (CFG.get('script_path') or r'C:\cmd\KhoaVeyonServices.bat').replace('/', '\\')
    rdir = ntpath.dirname(sp) or 'C:\\cmd'
    done = []
    for name in EXTRA_FILES:
        local = os.path.join(PAYLOAD_DIR, name)
        if not os.path.isfile(local):
            continue
        try:
            with open(local, 'rb') as f:
                data = f.read()
            try:
                same = rfs_sha(split_host_port(host)[0], ntpath.join(rdir, name)) == hashlib.sha256(data).hexdigest()
            except FileNotFoundError:
                same = False
            if not same:
                rfs_write(split_host_port(host)[0], ntpath.join(rdir, name), data)
                done.append(name)
        except OSError as e:
            log('[%s] không chép được %s: %s' % (host, name, e), 'warn')
    if done:
        log('[%s] đã cập nhật %s' % (host, ', '.join(done)), 'ok')
    return done


def autoupdate_round(now=None):
    """Một vòng: trả về danh sách máy đã đưa đi cập nhật."""
    now = now or time.time()
    with CFG_LOCK:
        if not CFG.get('auto_update_students', True):
            return []
        hosts = list(CFG.get('hosts') or [])
    if exam_snapshot().get('active'):   # đang thi: không đụng vào máy học sinh
        return []
    todo = []
    for h in hosts:
        hh, _ = split_host_port(h)
        if len(todo) >= MAX_PER_ROUND or not agent_online(hh):
            continue
        if now - _LAST_CHECK.get(h, 0) < CHECK_EVERY or now - _LAST_TRY.get(h, 0) < RETRY_AFTER:
            continue
        _LAST_CHECK[h] = now
        if health_probe(hh).get('svc') == 'old':
            todo.append(h)
        sync_extra_files(h)
    if todo:
        for h in todo:
            _LAST_TRY[h] = now
        log('Tự cập nhật dịch vụ KhoaVeyon trên %d máy đang chạy bản cũ: %s' % (len(todo), ', '.join(todo)), 'head')
        job_fix_service(todo)
    return todo


def autoupdate_loop():
    time.sleep(90)   # đợi các máy học sinh kịp kết nối Agent sau khi mở chương trình
    while True:
        try:
            autoupdate_round()
        except Exception as e:  # noqa
            log('Lỗi tự cập nhật dịch vụ: %s' % e, 'err')
        time.sleep(60)
