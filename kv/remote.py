# -*- coding: utf-8 -*-
"""Chạy lệnh qua Veyon, chép file sang máy học sinh qua \\\\máy\\C$ và chạy lệnh từ xa bằng schtasks."""

import os
import re
import shutil
import subprocess
import time

from .excel_lists import LISTS
from .paths import abs_path, CREATE_NO_WINDOW, find_veyon_cli


def client_command(cfg, switch):
    """Lệnh để dán vào Veyon (Run program)."""
    return 'cmd.exe /c %s %s' % (cfg['script_path'], switch)


def veyon_command(cfg, host, feature, template_key='run_template'):
    return cfg[template_key].format(cli=find_veyon_cli(cfg['veyon_cli']), host=host, feature=feature)


def run_shell(cmdline, timeout=60):
    try:
        p = subprocess.run(cmdline, shell=True, capture_output=True, text=True, errors='replace',
                           timeout=timeout, creationflags=CREATE_NO_WINDOW)
        out = ((p.stdout or '') + (p.stderr or '')).strip()
        return p.returncode, out
    except subprocess.TimeoutExpired:
        return -1, 'Quá thời gian chờ'
    except Exception as e:  # noqa
        return -1, str(e)


def run_args(args, timeout=60):
    """Chạy lệnh dạng danh sách tham số, không cho đọc bàn phím (tránh treo khi lệnh hỏi mật khẩu)."""
    try:
        p = subprocess.run(args, capture_output=True, text=True, errors='replace', timeout=timeout,
                           stdin=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
        return p.returncode, ((p.stdout or '') + (p.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return -1, 'Quá thời gian chờ'
    except Exception as e:  # noqa
        return -1, str(e)


def unc_target(host, target_dir):
    """C:\\cmd trên máy học sinh -> \\\\HOST\\C$\\cmd (chia sẻ quản trị)."""
    m = re.match(r'^([A-Za-z]):[\\/]*(.*)$', (target_dir or '').strip())
    if not m:
        raise ValueError('Thư mục đích phải bắt đầu bằng ổ đĩa, ví dụ C:\\cmd')
    return '\\\\%s\\%s$\\%s' % (host, m.group(1).upper(), m.group(2).replace('/', '\\'))


def distribute_to_host(host, files, target_dir):
    """Chép file/thư mục sang máy học sinh. Trả về số mục đã chép."""
    dst = unc_target(host, target_dir)
    os.makedirs(dst, exist_ok=True)
    n = 0
    for f in files:
        src = abs_path(f)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(dst, os.path.basename(src.rstrip('\\/'))), dirs_exist_ok=True)
        else:
            shutil.copy2(src, os.path.join(dst, os.path.basename(src)))
        n += 1
    return n


def logged_on_user(host):
    rc, out = run_args(['query', 'user', '/server:' + host], timeout=20)
    if rc != 0:
        return ''
    for line in out.splitlines()[1:]:
        t = line.replace('>', ' ').split()
        if t:
            return t[0]
    return ''


def remote_run(host, cmdline, interactive=False, name='KhoaVeyonRun'):
    """Chạy 1 lệnh trên máy học sinh bằng Task Scheduler (schtasks) rồi kích hoạt ngay.
    Mặc định chạy bằng SYSTEM (nền, học sinh không thấy cửa sổ). interactive=True: chạy bằng người đang đăng nhập."""
    ru = 'SYSTEM'
    if interactive:
        ru = logged_on_user(host)
        if not ru:
            return -1, 'Không tìm thấy người đang đăng nhập trên máy này'
    create = ['schtasks', '/Create', '/S', host, '/TN', name, '/TR', cmdline, '/SC', 'ONCE', '/ST', '00:00',
              '/RU', ru, '/F']
    create += ['/IT'] if interactive else ['/RL', 'HIGHEST']
    rc, out = run_args(create)
    if rc != 0:
        return rc, out
    rc2, out2 = run_args(['schtasks', '/Run', '/S', host, '/TN', name])
    return rc2, (out + '\n' + out2).strip()


def sync_lists(cfg):
    """Chép 3 file Excel từ thư mục danh sách sang thư mục đồng bộ. Trả về (số file đã chép, lỗi)."""
    dst = (cfg.get('sync_dir') or '').strip()
    if not dst:
        return 0, 'Chưa đặt thư mục đồng bộ'
    dst = abs_path(dst)
    os.makedirs(dst, exist_ok=True)
    n = 0
    for meta in LISTS.values():
        src = os.path.join(abs_path(cfg['list_dir']), meta['file'])
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dst, meta['file']))
            n += 1
    return n, ''


def parse_task_result(csv_text):
    """Lấy mã 'Last Result' (cột 7) từ kết quả schtasks /Query /FO CSV /V. Trả về số nguyên hoặc None."""
    import csv
    import io
    rows = list(csv.reader(io.StringIO(csv_text)))
    for r in rows[1:] if len(rows) > 1 else []:
        if len(r) > 6:
            try:
                return int(r[6])
            except ValueError:
                return None
    return None


def remote_run_wait(host, cmdline, timeout=60, interactive=False):
    """Như remote_run (mặc định SYSTEM) nhưng đợi lệnh chạy xong và trả về (ok, mô tả)."""
    rc, out = remote_run(host, cmdline, interactive)
    if rc != 0:
        return False, '(%s) %s' % (rc, out)
    end = time.time() + timeout
    while time.time() < end:
        time.sleep(2)
        rc, out = run_args(['schtasks', '/Query', '/S', host, '/TN', 'KhoaVeyonRun', '/FO', 'CSV', '/V'], timeout=25)
        code = parse_task_result(out) if rc == 0 else None
        if code is not None and code not in (267009, 267011, 267014):  # đang chạy / chưa chạy / bị dừng
            return code == 0, 'xong' if code == 0 else 'mã lỗi %s' % code
    return False, 'quá thời gian chờ'
