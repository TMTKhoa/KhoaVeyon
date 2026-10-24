# -*- coding: utf-8 -*-
"""Ghi nhớ lệnh hạn chế mà KhoaVeyon đã gửi cho từng máy."""

import json
import os
import threading
import time

from .paths import CONFIG_PATH
from .runtime import split_host_port


APPLY_CATS = {   # lệnh -> (nhóm, nhãn khi đang bật, bật?) để biết máy đang bị hạn chế gì theo lệnh KhoaVeyon đã gửi
    'lockall-start': ('lock', 'Khóa toàn bộ', True), 'lockall-stop': ('lock', '', False),
    'lockrun-start': ('run', 'Chặn mở app ngoài DS', True), 'lockrun-stop': ('run', '', False),
    'lockapp-start': ('kiosk', 'Kiosk', True), 'lockapp-stop': ('kiosk', '', False),
    'blockall': ('net', 'Chặn internet', True), 'allowpage': ('net', 'Chỉ trang cho phép', True), 'allowall': ('net', '', False),
    'webonly': ('net', 'Chỉ trang cho phép (trình duyệt)', True), 'weboff': ('net', '', False),
    'blockapp': ('blockapp', 'Chặn ứng dụng', True), 'unblockapp': ('blockapp', '', False),
    'lockdown': ('lockdown', 'Khóa Task Manager', True), 'unlock': ('lockdown', '', False),
    'mute': ('mute', 'Tắt tiếng', True), 'unmute': ('mute', '', False),
    'blockai': ('ai', 'Khóa AI', True), 'allowai': ('ai', '', False),
}
APPLIED = {}                     # máy -> {nhóm: {'label','on','ts','key'}}
APPLIED_LOCK = threading.Lock()


def applied_path():
    return os.path.join(os.path.dirname(CONFIG_PATH), 'applied.json')


def applied_load():
    try:
        with open(applied_path(), 'r', encoding='utf-8') as f:
            d = json.load(f)
        if isinstance(d, dict):
            with APPLIED_LOCK:
                APPLIED.update({k: v for k, v in d.items() if isinstance(v, dict)})
    except (OSError, ValueError):
        pass


def applied_record(host, key):
    cat = APPLY_CATS.get(key)
    if not cat:
        return
    hh, _ = split_host_port(host)
    with APPLIED_LOCK:
        APPLIED.setdefault(hh, {})[cat[0]] = {'label': cat[1], 'on': cat[2], 'ts': int(time.time()), 'key': key}
        try:
            tmp = applied_path() + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(APPLIED, f, ensure_ascii=False)
            os.replace(tmp, applied_path())
        except OSError:
            pass


def applied_list(host):
    hh, _ = split_host_port(host)
    with APPLIED_LOCK:
        d = dict(APPLIED.get(hh) or {})
    return [v['label'] for v in sorted(d.values(), key=lambda v: v['ts']) if v.get('on') and v.get('label')]


def applied_active(host):
    """Các lệnh hạn chế đang bật của một máy (theo lệnh KhoaVeyon đã gửi), xếp theo thứ tự đã gửi."""
    hh, _ = split_host_port(host)
    with APPLIED_LOCK:
        d = dict(APPLIED.get(hh) or {})
    return [v['key'] for v in sorted(d.values(), key=lambda v: v['ts']) if v.get('on') and v.get('key')]
