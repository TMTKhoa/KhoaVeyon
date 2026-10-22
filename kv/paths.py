# -*- coding: utf-8 -*-
"""Đường dẫn gốc, phiên bản chương trình, tìm veyon-cli và các file đi kèm (scripts, tài nguyên)."""

import os
import shutil
import sys


VERSION = '4.9.4'
APP_TITLE = 'KhoaVeyon - Hỗ trợ quản lý lớp học'
_HERE = os.path.dirname(os.path.abspath(__file__))   # thư mục kv/
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = os.path.dirname(_HERE)                      # thư mục chứa KhoaVeyon.py
ENTRY_SCRIPT = os.path.join(APP_DIR, 'KhoaVeyon.py')      # file khởi động (chạy lại khi cập nhật, nâng quyền)
LEGACY_CONFIG_PATH = os.path.join(APP_DIR, 'KhoaVeyon.json')


def _appdata_config_path():
    base = os.environ.get('APPDATA')
    if os.name == 'nt' and base:
        return os.path.join(base, 'KhoaVeyon', 'KhoaVeyon.json')
    return ''


def _config_path():
    """Chế độ portable: cài đặt nằm trong thư mục data cạnh chương trình, chép cả thư mục sang máy khác là đủ.
    Nếu thư mục chương trình không ghi được (Program Files, USB khóa ghi) thì dùng %APPDATA%\\KhoaVeyon."""
    folder = os.path.join(APP_DIR, 'data')
    try:
        os.makedirs(folder, exist_ok=True)
        probe = os.path.join(folder, '.write_test')
        with open(probe, 'w') as f:
            f.write('x')
        os.remove(probe)
        return os.path.join(folder, 'KhoaVeyon.json')
    except Exception:  # noqa
        pass
    alt = _appdata_config_path()
    if alt:
        try:
            os.makedirs(os.path.dirname(alt), exist_ok=True)
            return alt
        except Exception:  # noqa
            pass
    return LEGACY_CONFIG_PATH


CONFIG_PATH = _config_path()


def abs_path(p):
    """Đường dẫn tương đối (ví dụ 'lists') được tính từ thư mục chứa chương trình, để chép cả thư mục là chạy được."""
    p = os.path.expandvars((p or '').strip())
    if not p:
        return p
    return p if os.path.isabs(p) or p.startswith('\\\\') else os.path.normpath(os.path.join(APP_DIR, p))


def find_veyon_cli(configured=''):
    """Tìm veyon-cli: đường dẫn đã cài đặt, thư mục 'veyon' cạnh chương trình, PATH, rồi Program Files."""
    cands = []
    if configured:
        cands.append(abs_path(configured))
    cands += [os.path.join(APP_DIR, 'veyon', 'veyon-cli.exe'), os.path.join(APP_DIR, 'veyon-cli.exe')]
    found = shutil.which('veyon-cli')
    if found:
        cands.append(found)
    for env in ('ProgramFiles', 'ProgramFiles(x86)', 'ProgramW6432'):
        base = os.environ.get(env)
        if base:
            cands.append(os.path.join(base, 'Veyon', 'veyon-cli.exe'))
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return configured


def resource_path(name):
    """Đường dẫn tới file đi kèm (biểu tượng), cả khi chạy từ file .exe."""
    return os.path.join(getattr(sys, '_MEIPASS', APP_DIR), name)


CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0


def load_script(name):
    """Nội dung một script đi kèm trong thư mục scripts (PowerShell, bat gửi xuống máy học sinh)."""
    with open(os.path.join(resource_path('scripts'), name), 'rb') as f:
        return f.read().decode('utf-8').replace('\r\n', '\n')
