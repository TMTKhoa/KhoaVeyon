# -*- coding: utf-8 -*-
"""Màn hình khóa ứng dụng trên máy giáo viên.

Khi giáo viên rời máy, bấm khóa để che toàn bộ giao diện sau một mật khẩu, tránh học sinh lên chỉnh cài đặt hay
gửi lệnh. Mật khẩu mặc định là 0000, giáo viên đổi được (chữ, số, ký tự đều được). Chỉ lưu dạng băm PBKDF2 ở data\\applock.json.

Khi đang khóa, máy chủ từ chối mọi lệnh API (trừ xem trạng thái và nhập mật khẩu mở khóa ở /api/applock), nên chặn cả
khi ai đó gọi thẳng API chứ không chỉ che giao diện. Có thể bật tự khóa khi không thao tác sau một số phút."""

import hashlib
import hmac
import json
import os
import secrets
import threading
import time

from .paths import CONFIG_PATH
from .runtime import ApiError, log

PW_MIN = 4
PW_MAX = 128
PIN_ITER = 120000
FAIL_LIMIT = 5
FAIL_LOCK_SEC = 30
DEFAULT_PIN = '0000'

LOCK = threading.RLock()
STATE = {'locked': False, 'fails': 0, 'locked_until': 0.0}
DATA = {'salt': '', 'hash': '', 'idle_min': 0}   # idle_min: tự khóa sau N phút không thao tác (0 = tắt)


def _path():
    return os.path.join(os.path.dirname(CONFIG_PATH), 'applock.json')


def _hash(pin, salt):
    return hashlib.pbkdf2_hmac('sha256', pin.encode('utf-8'), bytes.fromhex(salt), PIN_ITER).hex()


def _set_pin(pin):
    salt = secrets.token_hex(16)
    DATA['salt'], DATA['hash'] = salt, _hash(pin, salt)


def applock_save():
    with LOCK:
        snap = dict(DATA)
    try:
        tmp = _path() + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(snap, f)
        os.replace(tmp, _path())
    except OSError as e:
        raise ApiError('Không lưu được cài đặt khóa: %s' % e)


def applock_load():
    """Nạp lúc khởi động. Chưa có file (lần chạy đầu) thì đặt mật khẩu mặc định 0000, không khóa sẵn để giáo viên vào được."""
    try:
        with open(_path(), 'r', encoding='utf-8') as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = None
    with LOCK:
        if isinstance(d, dict) and d.get('hash'):
            for k in DATA:
                if k in d:
                    DATA[k] = d[k]
        else:
            _set_pin(DEFAULT_PIN)
            try:
                applock_save()
            except ApiError:
                pass
        STATE['locked'] = False   # mở máy lên thì không khóa sẵn


def applock_is_locked():
    with LOCK:
        return bool(STATE['locked'])


def _check(pin):
    with LOCK:
        now = time.time()
        if now < STATE['locked_until']:
            raise ApiError('Nhập sai nhiều lần. Thử lại sau %d giây.' % int(STATE['locked_until'] - now + 1))
        ok = bool(DATA['hash']) and hmac.compare_digest(_hash(str(pin or ''), DATA['salt']), DATA['hash'])
        if ok:
            STATE['fails'] = 0
            return True
        STATE['fails'] += 1
        if STATE['fails'] >= FAIL_LIMIT:
            STATE['fails'] = 0
            STATE['locked_until'] = now + FAIL_LOCK_SEC
        return False


def applock_status():
    with LOCK:
        return {'locked': bool(STATE['locked']), 'idle_min': int(DATA['idle_min'] or 0),
                'is_default': bool(DATA['hash']) and hmac.compare_digest(DATA['hash'], _hash(DEFAULT_PIN, DATA['salt']))}


def api_applock(b=None):
    """GET (b=None): trạng thái. POST: action = lock | unlock | setpin | idle."""
    if not b:
        return applock_status()
    act = b.get('action')
    if act == 'lock':
        with LOCK:
            STATE['locked'] = True
        log('Đã khóa màn hình ứng dụng', 'warn')
        return applock_status()
    if act == 'unlock':
        if not _check(str(b.get('pin') or '')):
            raise ApiError('Mật khẩu không đúng')
        with LOCK:
            STATE['locked'] = False
        return applock_status()
    if act == 'setpin':
        if not _check(str(b.get('pin') or '')):
            raise ApiError('Mật khẩu hiện tại không đúng')
        new = str(b.get('new_pin') or '')
        if len(new) < PW_MIN or len(new) > PW_MAX:
            raise ApiError('Mật khẩu mới cần từ %d đến %d ký tự' % (PW_MIN, PW_MAX))
        if new != str(b.get('confirm') if b.get('confirm') is not None else new):
            raise ApiError('Hai lần nhập mật khẩu mới không khớp')
        with LOCK:
            _set_pin(new)
        applock_save()
        log('Đã đổi mật khẩu khóa màn hình ứng dụng', 'ok')
        return applock_status()
    if act == 'idle':
        try:
            m = max(0, min(240, int(b.get('idle_min') or 0)))
        except (TypeError, ValueError):
            raise ApiError('Số phút không hợp lệ')
        with LOCK:
            DATA['idle_min'] = m
        applock_save()
        return applock_status()
    raise ApiError('Thao tác không hợp lệ')
