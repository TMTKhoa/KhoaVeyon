# -*- coding: utf-8 -*-
"""Tự chạy KhoaVeyon khi giáo viên đăng nhập Windows (từ bản 3.9.0).

Đặt một file .vbs trong thư mục Startup của người dùng hiện tại. File này chạy Chay-KhoaVeyon.bat --background
(ẩn, không mở cửa sổ) để các việc nền như hẹn giờ, giám sát, tự áp lại hạn chế chạy ngay từ đầu buổi.
Không cần quyền quản trị, không ghi registry, gỡ bằng cách xóa file."""

import os

from .paths import APP_DIR
from .runtime import ApiError, log


STARTUP_NAME = 'KhoaVeyon.vbs'


def startup_dir():
    base = os.environ.get('APPDATA')
    if not base:
        return ''
    return os.path.join(base, 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')


def startup_path():
    d = startup_dir()
    return os.path.join(d, STARTUP_NAME) if d else ''


def startup_vbs(app_dir=None):
    """Nội dung .vbs: chạy bat ở chế độ nền, cửa sổ ẩn (0), không đợi."""
    app_dir = (app_dir or APP_DIR).replace('"', '')
    return ('Set sh = CreateObject("WScript.Shell")\r\n'
            'sh.CurrentDirectory = "%s"\r\n'
            'sh.Run """%s\\Chay-KhoaVeyon.bat"" --background", 0, False\r\n' % (app_dir, app_dir))


def startup_status():
    p = startup_path()
    return {'supported': os.name == 'nt' and bool(p), 'on': bool(p) and os.path.isfile(p), 'path': p}


def startup_set(on, path=None, app_dir=None):
    p = path or startup_path()
    if not p:
        raise ApiError('Chỉ dùng được trên Windows')
    if on:
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'w', encoding='utf-16', newline='') as f:   # WScript đọc đúng tiếng Việt trong đường dẫn khi file là UTF-16
                f.write(startup_vbs(app_dir))
        except OSError as e:
            raise ApiError('Không ghi được vào thư mục Startup: %s' % e)
        log('Đã bật tự chạy KhoaVeyon khi đăng nhập Windows (chạy nền)', 'ok')
    else:
        try:
            os.remove(p)
        except FileNotFoundError:
            pass
        except OSError as e:
            raise ApiError('Không xóa được %s: %s' % (p, e))
        log('Đã tắt tự chạy KhoaVeyon khi đăng nhập Windows', 'ok')
    return {'supported': True, 'on': os.path.isfile(p), 'path': p}


def api_startup(b):
    if b.get('action') == 'set':
        if os.name != 'nt':
            raise ApiError('Chỉ dùng được trên Windows')
        return startup_set(bool(b.get('on')))
    return startup_status()
