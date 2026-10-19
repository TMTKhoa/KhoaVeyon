# -*- coding: utf-8 -*-
"""Trạng thái dùng chung của chương trình: cài đặt đang chạy (CFG), nhật ký, công việc nền, nhóm luồng."""

import os
import re
import threading
import time

from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import load_config
from .excel_lists import check_entry, LISTS
from .meta import VEYON_PORT
from .paths import abs_path, APP_DIR


WEB_DIR = os.path.join(APP_DIR, 'web')
ASSET_TYPES = {'.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon',
               '.css': 'text/css; charset=utf-8', '.js': 'application/javascript; charset=utf-8'}
PAYLOAD_DIR = os.path.join(APP_DIR, 'payload')
IDLE_EXIT_SECONDS = 180      # đóng cửa sổ trình duyệt thì chương trình tự thoát sau chừng này giây
MAX_UPLOAD = 500 * 1024 * 1024

STATE = {'token': '', 'port': 0, 'last_ping': time.time(), 'pinged': False, 'busy': 0, 'server': None}
CFG_LOCK = threading.RLock()
CFG = load_config()
LOG = []
LOG_LOCK = threading.Lock()
LOG_SEQ = [0]


class ApiError(Exception):
    pass


def log(msg, kind=''):
    with LOG_LOCK:
        LOG_SEQ[0] += 1
        LOG.append({'id': LOG_SEQ[0], 't': time.strftime('%H:%M:%S'), 'msg': msg, 'kind': kind})
        if len(LOG) > 1500:
            del LOG[:300]


BUSY_LOCK = threading.Lock()
JOBS = {}                # id -> {'title', 'done', 'total', 'err'}; giao diện đọc qua /api/log
JOB_SEQ = [0]


def _busy(delta):
    with BUSY_LOCK:
        STATE['busy'] += delta


def start_job(fn, *args):
    def run():
        _busy(1)
        try:
            fn(*args)
        except Exception as e:  # noqa
            log('LỖI không mong muốn: %s' % e, 'err')
        finally:
            _busy(-1)
    threading.Thread(target=run, daemon=True).start()


def pool_run(fn, hosts, title='Đang thực hiện'):
    ok_n = err_n = 0
    with BUSY_LOCK:
        JOB_SEQ[0] += 1
        jid = JOB_SEQ[0]
        JOBS[jid] = {'title': title, 'done': 0, 'total': len(hosts), 'err': 0}
    try:
        with ThreadPoolExecutor(max_workers=min(16, max(1, len(hosts)))) as ex:
            futs = {ex.submit(fn, h): h for h in hosts}
            for fut in as_completed(futs):
                h = futs[fut]
                try:
                    ok, text = fut.result()
                except Exception as e:  # noqa
                    ok, text = False, str(e)
                if ok:
                    ok_n += 1
                else:
                    err_n += 1
                with BUSY_LOCK:
                    JOBS[jid]['done'] += 1
                    JOBS[jid]['err'] = err_n
                log('[%s] %s %s' % (h, 'OK' if ok else 'LỖI', text), 'ok' if ok else 'err')
    finally:
        with BUSY_LOCK:
            JOBS.pop(jid, None)
    log('--- xong: %d thành công, %d lỗi ---' % (ok_n, err_n), 'warn' if err_n else 'head')


def split_host_port(h):
    m = re.match(r'^(.+):(\d{1,5})$', h)
    return (m.group(1), int(m.group(2))) if m and h.count(':') == 1 else (h, VEYON_PORT)


# ---------------------------------------------------------------- API
def clean_hosts(value):
    out = []
    for h in value or []:
        h = str(h).strip()
        if h and h not in out:
            out.append(h)
    return out


def warnings_for(kind, rows):
    res = []
    for i, r in enumerate(rows):
        a = str(r[0]).strip()
        if a:
            w = check_entry(kind, a)
            if w:
                res.append({'row': i, 'msg': w})
    return res


def list_path(kind):
    with CFG_LOCK:
        return os.path.join(abs_path(CFG['list_dir']), LISTS[kind]['file'])
