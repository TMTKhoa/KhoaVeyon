# -*- coding: utf-8 -*-
"""Tự áp lại hạn chế khi máy học sinh bật lại (từ bản 3.8.0).

Một số hạn chế mất khi máy khởi động lại (ví dụ chế độ kiosk là tiến trình nền). Chương trình theo dõi các máy
đang có hạn chế (theo applied.json); máy nào chuyển từ tắt sang bật thì đợi có người đăng nhập rồi gửi lại
đúng các lệnh đang bật, theo thứ tự đã gửi trước đó. Chỉ chạy khi KhoaVeyon đang mở."""

import threading
import time

from concurrent.futures import ThreadPoolExecutor

from .applied import applied_active
from .jobs import job_action
from .network import tcp_forget, tcp_probe
from .remote import logged_on_user
from .runtime import CFG, CFG_LOCK, log, split_host_port, start_job


REAPPLY_POLL = 8             # giây giữa hai lần dò máy
REAPPLY_LOGIN_WAIT = 300     # đợi tối đa chừng này giây cho tới khi có người đăng nhập
REAPPLY_LOGIN_STEP = 10
LAST_UP = {}                 # máy -> đã thấy đang bật ở lần dò trước
REAPPLY_BUSY = set()
REAPPLY_LOCK = threading.Lock()


def came_back(last_up, host, up):
    """True khi máy vừa chuyển từ tắt sang bật (lần dò đầu tiên chỉ ghi nhận, không tính)."""
    prev = last_up.get(host)
    last_up[host] = up
    return prev is False and up


def job_reapply(host, wait=REAPPLY_LOGIN_WAIT, step=REAPPLY_LOGIN_STEP):
    try:
        hh, pp = split_host_port(host)
        tcp_forget(hh, pp)
        end = time.time() + wait
        while not logged_on_user(hh):   # lệnh chạy trong phiên của học sinh nên cần có người đăng nhập
            if time.time() >= end:
                log('[%s] đã bật lại nhưng chưa có ai đăng nhập sau %d giây, chưa áp lại hạn chế' % (host, wait), 'warn')
                return
            time.sleep(step)
        keys = applied_active(host)
        if not keys:
            return
        log('[%s] máy vừa bật lại, áp lại %d hạn chế đang bật' % (host, len(keys)), 'head')
        for k in keys:
            job_action(k, [host])
    finally:
        with REAPPLY_LOCK:
            REAPPLY_BUSY.discard(host)


def reapply_tick(probe=tcp_probe, starter=start_job):
    with CFG_LOCK:
        if not CFG.get('reapply_on_boot', True):
            return
        hosts = list(CFG.get('hosts') or [])
    watched = []
    for h in hosts:
        if applied_active(h):
            watched.append(h)
        else:
            LAST_UP.pop(h, None)
    if not watched:
        return
    with ThreadPoolExecutor(max_workers=min(32, len(watched))) as ex:   # dò song song: nhiều máy tắt không làm chậm vòng theo dõi
        ups = list(ex.map(lambda h: bool(probe(*split_host_port(h), 0.8)), watched))
    for h, up in zip(watched, ups):
        if came_back(LAST_UP, h, up):
            with REAPPLY_LOCK:
                if h in REAPPLY_BUSY:
                    continue
                REAPPLY_BUSY.add(h)
            starter(job_reapply, h)


def reapply_loop():
    while True:
        try:
            reapply_tick()
        except Exception as e:  # noqa
            log('Lỗi theo dõi máy bật lại: %s' % e, 'err')
        time.sleep(REAPPLY_POLL)
