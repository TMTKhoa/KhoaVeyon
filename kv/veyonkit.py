# -*- coding: utf-8 -*-
"""Gửi và chạy Setup-MayHocSinh.bat xuống máy học sinh chỉ bằng Veyon (từ bản 3.10.0).

Máy học sinh mới chưa mở chia sẻ C$ và Task Scheduler từ xa, nên không chép file theo cách thường được.
Veyon File Transfer không gọi được từ veyon-cli, nên ở đây dùng tính năng "Start application" của Veyon:
nội dung Setup-MayHocSinh.bat (và khóa *_public.pem nếu có trong payload) được nén, mã hóa base64 rồi nhúng
vào một lệnh PowerShell. Lệnh này chạy trong phiên của người đang đăng nhập, ghi file ra %TEMP%\\KhoaVeyonSetup
rồi mở Setup-MayHocSinh.bat bằng quyền quản trị: máy học sinh hiện hộp thoại UAC, phải có người bấm Yes
(tài khoản thường thì nhập mật khẩu quản trị). Windows không cho bỏ qua bước này.
"""

import base64
import gzip
import json
import os
import time

from .paths import find_veyon_cli
from .remote import run_args, unc_target
from .runtime import CFG, CFG_LOCK, log, PAYLOAD_DIR, pool_run
from .setup import ensure_payload, STUDENT_SETUP_BAT

START_APP_UID = 'da9ca56a-b2ad-4fff-8f8a-929b2927b442'  # Veyon: "Start application" (StartApp)
MAX_CMDLINE = 30000  # giới hạn dòng lệnh Windows là 32767 ký tự


def _b64gz(data):
    return base64.b64encode(gzip.compress(data, 9)).decode('ascii')


def kit_files():
    """Các file nhúng vào lệnh: Setup-MayHocSinh.bat và khóa public (nếu có). Trả về [(tên, bytes)]."""
    out = []
    with open(os.path.join(PAYLOAD_DIR, STUDENT_SETUP_BAT), 'rb') as f:
        out.append((STUDENT_SETUP_BAT, f.read()))
    for n in sorted(os.listdir(PAYLOAD_DIR)):
        if n.lower().endswith('_public.pem'):
            with open(os.path.join(PAYLOAD_DIR, n), 'rb') as f:
                out.append((n, f.read()))
    return out


def build_kit_command(files):
    """Dòng lệnh PowerShell tự giải nén file vào %TEMP%\\KhoaVeyonSetup rồi chạy Setup bằng quyền quản trị.
    Không có dấu cách bên trong tham số (Veyon tách tham số theo dấu cách)."""
    ps = ["$d=Join-Path $env:TEMP 'KhoaVeyonSetup'",
          "New-Item -ItemType Directory -Force -Path $d|Out-Null",
          "function W($n,$b){$m=New-Object IO.MemoryStream(,[Convert]::FromBase64String($b));"
          "$g=New-Object IO.Compression.GZipStream($m,[IO.Compression.CompressionMode]::Decompress);"
          "$o=[IO.File]::Create((Join-Path $d $n));$g.CopyTo($o);$o.Close();$g.Close()}"]
    for name, data in files:
        ps.append("W '%s' '%s'" % (name.replace("'", "''"), _b64gz(data)))
    ps.append("Start-Process -FilePath (Join-Path $d '%s') -Verb RunAs" % STUDENT_SETUP_BAT)
    enc = base64.b64encode(';'.join(ps).encode('utf-16-le')).decode('ascii')
    return 'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -EncodedCommand ' + enc


def _share_ok(host, target):
    try:
        unc = unc_target(host, target)
        return os.path.isdir(unc) or os.path.isdir(os.path.dirname(unc.rstrip('\\')))
    except Exception:  # noqa
        return False


def job_veyon_kit(hosts, wait_then_push=True, wait_seconds=300):
    with CFG_LOCK:
        cfg = json.loads(json.dumps(CFG))
    log('>>> Gửi Setup-MayHocSinh.bat qua Veyon xuống %d máy' % len(hosts), 'head')
    ensure_payload(cfg)
    files = kit_files()
    cmd = build_kit_command(files)
    if len(cmd) > MAX_CMDLINE:
        log('Lệnh quá dài (%d ký tự): bớt file trong payload rồi thử lại.' % len(cmd), 'err')
        return
    log('Kèm: %s' % ', '.join(n for n, _ in files), 'ok')
    cli = find_veyon_cli(cfg['veyon_cli'])
    arg = json.dumps({'applications': [cmd]})

    def one(h):
        rc, out = run_args([cli, 'feature', 'start', h, START_APP_UID, arg], timeout=40)
        if rc != 0:
            return False, 'Veyon không chạy được lệnh (%s) %s' % (rc, out[-300:])
        return True, 'đã gửi, chờ bấm Yes ở hộp thoại UAC trên máy học sinh'
    pool_run(one, hosts, 'Gửi Setup-MayHocSinh.bat qua Veyon')
    log('Trên từng máy học sinh: bấm Yes ở hộp thoại UAC (tài khoản thường thì nhập mật khẩu quản trị). '
        'Máy không có ai đăng nhập Windows thì Veyon không mở được ứng dụng.', 'warn')
    if not wait_then_push:
        return
    log('Đang chờ tối đa %d giây để các máy mở chia sẻ C$, máy nào xong sẽ được thiết lập tiếp...' % wait_seconds, 'head')
    from .setup_jobs import job_setup_diagnose
    left, end = list(hosts), time.time() + wait_seconds
    while left and time.time() < end:
        time.sleep(10)
        ready = [h for h in left if _share_ok(h, cfg['dist_target'])]
        if ready:
            time.sleep(15)  # để Setup chạy nốt các bước sau (Veyon Service, thư mục C:\cmd)
            left = [h for h in left if h not in ready]
            job_setup_diagnose(ready, True)
    if left:
        log('Hết thời gian chờ, chưa mở được chia sẻ: %s. Kiểm tra UAC trên các máy này rồi bấm "Thiết lập máy học sinh".'
            % ', '.join(left), 'warn')
    else:
        log('--- xong: mọi máy đã chạy Setup và được thiết lập ---', 'head')
