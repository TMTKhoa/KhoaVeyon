# -*- coding: utf-8 -*-
"""Tra mã (UID) thật của mục “Programs & websites” trong Veyon theo tên mục hoặc theo dòng lệnh.

veyon-cli chỉ nhận đúng tên mục. Nếu trong Veyon mục tồn tại nhưng khác tên (ví dụ giáo viên tự tạo trước đó với tên “Khóa AI”,
hoặc Veyon đã có mục cùng dòng lệnh), gọi theo tên sẽ báo “Invalid feature name or UID specified”. Ở đây tra danh sách mục thật
rồi gọi bằng UID."""

import re
import threading
import time

_CACHE = {'t': 0.0, 'cli': '', 'items': None}
_LOCK = threading.Lock()
TTL = 20.0


def _nrm(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip().casefold()


def _items(cfg):
    from .paths import find_veyon_cli
    from .setup import _veyon_get_programs
    cli = find_veyon_cli(cfg.get('veyon_cli', ''))
    with _LOCK:
        if _CACHE['items'] is not None and _CACHE['cli'] == cli and time.time() - _CACHE['t'] < TTL:
            return _CACHE['items']
    try:
        items, _err = _veyon_get_programs(cli)
    except Exception:  # noqa
        items = None
    with _LOCK:
        _CACHE.update(t=time.time(), cli=cli, items=items)
    return items


def forget():
    """Xóa bộ nhớ tạm (sau khi ghi mục mới vào Veyon)."""
    with _LOCK:
        _CACHE.update(t=0.0, items=None)


def pick_uid(items, name, path=''):
    """Trả về UID của mục có đúng tên, nếu không có thì mục cùng dòng lệnh; không thấy thì ''."""
    if not items:
        return ''
    n = _nrm(name)
    for x in items:
        if isinstance(x, dict) and _nrm(x.get('Name')) == n and x.get('Uid'):
            return str(x['Uid'])
    p = _nrm(path)
    if p:
        for x in items:
            if isinstance(x, dict) and _nrm(x.get('Path')) == p and x.get('Uid'):
                return str(x['Uid'])
    return ''


def resolve(cfg, feature):
    """Tên mục (hoặc đã là UID) -> thứ nên đưa cho veyon-cli. Không tra được thì giữ nguyên tên."""
    f = str(feature or '').strip()
    if not f or f.startswith('{'):
        return f
    from .actions import ACTIONS
    path = ''
    for a in ACTIONS:
        if _nrm(cfg.get('features', {}).get(a[0]) or a[3]) == _nrm(f):
            path = 'cmd.exe /c %s %s' % (cfg.get('script_path', ''), a[2])
            break
    return pick_uid(_items(cfg), f, path) or f
