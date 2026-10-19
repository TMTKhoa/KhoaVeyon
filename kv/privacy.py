# -*- coding: utf-8 -*-
"""Quyền riêng tư dữ liệu giám sát (từ bản 3.8.0).

Ảnh chụp màn hình học sinh là dữ liệu nhạy cảm (có thể thấy tin nhắn, tài khoản cá nhân). Bản này thêm:
- Mã xem ảnh (tùy chọn): đặt mã thì ảnh vi phạm bị khóa, nhập mã mới xem được trong một khoảng thời gian.
  Mã chỉ lưu dưới dạng băm PBKDF2 ở data\\privacy.json, không bao giờ gửi lại giao diện.
- Giới hạn quyền đọc thư mục ảnh (tùy chọn, chỉ Windows): chỉ tài khoản Windows đang chạy chương trình, quản trị viên và SYSTEM đọc được."""

import hashlib
import hmac
import json
import os
import secrets
import threading
import time

from .evidence import evidence_root
from .paths import CONFIG_PATH
from .remote import run_args
from .runtime import ApiError, log


PIN_MIN = 4
PIN_ITER = 120000
UNLOCK_MINUTES = 15
FAIL_LIMIT = 5
FAIL_LOCK_SEC = 30
PRIV_LOCK = threading.RLock()
STATE = {'until': 0.0, 'fails': 0, 'locked_until': 0.0}
PRIV = {'salt': '', 'hash': '', 'acl': False}


def priv_path():
    return os.path.join(os.path.dirname(CONFIG_PATH), 'privacy.json')


def priv_load():
    try:
        with open(priv_path(), 'r', encoding='utf-8') as f:
            d = json.load(f)
    except (OSError, ValueError):
        return
    if isinstance(d, dict):
        with PRIV_LOCK:
            for k in PRIV:
                if k in d:
                    PRIV[k] = d[k]


def priv_save():
    with PRIV_LOCK:
        snap = dict(PRIV)
    try:
        tmp = priv_path() + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(snap, f)
        os.replace(tmp, priv_path())
    except OSError as e:
        raise ApiError('Không lưu được cài đặt riêng tư: %s' % e)


def _hash(pin, salt):
    return hashlib.pbkdf2_hmac('sha256', pin.encode('utf-8'), bytes.fromhex(salt), PIN_ITER).hex()


def pin_is_set():
    with PRIV_LOCK:
        return bool(PRIV['hash'])


def images_blocked():
    """True khi đã đặt mã xem ảnh và chưa mở khóa (hoặc đã hết thời gian mở khóa)."""
    with PRIV_LOCK:
        return bool(PRIV['hash']) and time.time() >= STATE['until']


def _check(pin):
    with PRIV_LOCK:
        now = time.time()
        if now < STATE['locked_until']:
            raise ApiError('Nhập sai nhiều lần. Thử lại sau %d giây.' % int(STATE['locked_until'] - now + 1))
        ok = bool(PRIV['hash']) and hmac.compare_digest(_hash(str(pin or ''), PRIV['salt']), PRIV['hash'])
        if ok:
            STATE['fails'] = 0
            return True
        STATE['fails'] += 1
        if STATE['fails'] >= FAIL_LIMIT:
            STATE['fails'] = 0
            STATE['locked_until'] = now + FAIL_LOCK_SEC
        return False


def privacy_status():
    with PRIV_LOCK:
        return {'pin_set': bool(PRIV['hash']), 'blocked': images_blocked(), 'acl': bool(PRIV['acl']),
                'left': max(0, int(STATE['until'] - time.time())) if PRIV['hash'] else 0, 'windows': os.name == 'nt'}


def api_privacy(_q=None):
    return privacy_status()


def api_privacy_pin(b):
    act = b.get('action')
    pin, new = str(b.get('pin') or ''), str(b.get('new_pin') or '')
    if act == 'lock':
        with PRIV_LOCK:
            STATE['until'] = 0.0
        return privacy_status()
    if act == 'unlock':
        if not pin_is_set():
            return privacy_status()
        if not _check(pin):
            raise ApiError('Mã không đúng')
        with PRIV_LOCK:
            STATE['until'] = time.time() + UNLOCK_MINUTES * 60
        return privacy_status()
    if act in ('set', 'clear'):
        if pin_is_set() and not _check(pin):
            raise ApiError('Mã hiện tại không đúng')
        if act == 'clear':
            with PRIV_LOCK:
                PRIV['salt'] = PRIV['hash'] = ''
                STATE['until'] = 0.0
            priv_save()
            log('Đã bỏ mã xem ảnh vi phạm', 'warn')
            return privacy_status()
        if len(new) < PIN_MIN:
            raise ApiError('Mã mới cần ít nhất %d ký tự' % PIN_MIN)
        salt = secrets.token_hex(16)
        with PRIV_LOCK:
            PRIV['salt'], PRIV['hash'] = salt, _hash(new, salt)
            STATE['until'] = time.time() + UNLOCK_MINUTES * 60   # vừa đặt xong thì cho xem tiếp một lúc
        priv_save()
        log('Đã đặt mã xem ảnh vi phạm. Ảnh tự khóa lại sau %d phút.' % UNLOCK_MINUTES, 'ok')
        return privacy_status()
    raise ApiError('Thao tác không hợp lệ')


def acl_args(path, user):
    """Lệnh icacls: bỏ quyền thừa kế, chỉ SYSTEM, Administrators và tài khoản đang chạy chương trình có toàn quyền."""
    args = ['icacls', path, '/inheritance:r', '/grant:r', '*S-1-5-18:(OI)(CI)F', '*S-1-5-32-544:(OI)(CI)F']
    if user:
        args.append('%s:(OI)(CI)F' % user)
    return args


def evidence_harden(runner=run_args):
    if os.name != 'nt':
        return False, 'Chỉ áp dụng trên Windows'
    rc, out = runner(acl_args(evidence_root(), os.environ.get('USERNAME', '')), 60)
    return rc == 0, out


def evidence_unharden(runner=run_args):
    if os.name != 'nt':
        return False, 'Chỉ áp dụng trên Windows'
    rc, out = runner(['icacls', evidence_root(), '/inheritance:e'], 60)
    return rc == 0, out


def api_privacy_acl(b):
    on = bool(b.get('on'))
    ok, out = (evidence_harden() if on else evidence_unharden())
    if not ok:
        raise ApiError('Không đổi được quyền thư mục ảnh: %s' % out)
    with PRIV_LOCK:
        PRIV['acl'] = on
    priv_save()
    log('Đã %s quyền đọc thư mục ảnh vi phạm' % ('giới hạn' if on else 'trả lại'), 'ok')
    return privacy_status()
