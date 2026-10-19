# -*- coding: utf-8 -*-
"""Chụp màn hình máy học sinh (theo yêu cầu hoặc trước khi khóa)."""

import json
import os
import shutil
import tempfile
import time

from .actions import ACTION_BY_KEY
from .jobs import job_action
from .paths import CONFIG_PATH, load_script
from .remote import distribute_to_host, remote_run_wait, rfs_read, rfs_remove
from .runtime import ApiError, CFG, CFG_LOCK, clean_hosts, log, pool_run, start_job
from .vcfg import vcfg_remote_dir, vcfg_safe


# ---------------------------------------------------------------- chụp màn hình máy học sinh (trước khi khóa)
SHOT_PS1 = load_script('kvshot.ps1')
SHOT_REMOTE_FILE = r'C:\Users\Public\kvshot.jpg'  # thư mục mà mọi người dùng đều ghi được
SHOT_PS1_NAME = 'kvshot.ps1'


def shot_root():
    d = os.path.join(os.path.dirname(CONFIG_PATH), 'screenshots')
    os.makedirs(d, exist_ok=True)
    return d


def _q(p):
    return '"%s"' % p if ' ' in p else p


def shot_one(cfg, host, folder):
    """Chụp màn hình người đang đăng nhập trên máy học sinh rồi lấy ảnh về máy giáo viên. Trả về (ok, mô tả)."""
    rdir = vcfg_remote_dir(cfg)
    tmp = tempfile.mkdtemp(prefix='kvshot')
    try:
        sp = os.path.join(tmp, SHOT_PS1_NAME)
        with open(sp, 'w', encoding='utf-8-sig', newline='') as f:  # BOM để PowerShell 5 đọc đúng
            f.write(SHOT_PS1.replace('\r\n', '\n').replace('\n', '\r\n'))
        distribute_to_host(host, [sp], rdir)
    except Exception as e:  # noqa
        return False, 'không chép được script chụp: %s' % e
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        rfs_remove(host, SHOT_REMOTE_FILE)
    except OSError:
        pass
    cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File %s -Out %s' % (
        _q(rdir + '\\' + SHOT_PS1_NAME), _q(SHOT_REMOTE_FILE))
    ok, msg = remote_run_wait(host, cmd, 45, interactive=True)
    if not ok:
        return False, msg
    dest = os.path.join(folder, vcfg_safe(host) + '.jpg')
    try:
        data = rfs_read(host, SHOT_REMOTE_FILE)
        with open(dest, 'wb') as f:
            f.write(data)
        try:
            rfs_remove(host, SHOT_REMOTE_FILE)
        except OSError:
            pass
    except OSError as e:
        return False, 'chụp xong nhưng không lấy được ảnh: %s' % e
    return True, 'đã lưu ' + os.path.basename(dest)


def job_shot(hosts, title='Chụp màn hình'):
    with CFG_LOCK:
        cfg = json.loads(json.dumps(CFG))
    folder = os.path.join(shot_root(), time.strftime('%Y%m%d-%H%M%S'))
    os.makedirs(folder, exist_ok=True)
    log('>>> %s (%d máy) -> %s' % (title, len(hosts), folder), 'head')
    pool_run(lambda h: shot_one(cfg, h, folder), hosts, title)


def job_shot_then_action(key, hosts):
    job_shot(hosts, 'Chụp màn hình trước khi "%s"' % ACTION_BY_KEY[key][1])
    job_action(key, hosts)  # máy chụp lỗi vẫn bị khóa, xem lỗi ở Nhật ký


def api_shot(b):
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào để chụp')
    start_job(job_shot, hosts)
    return {'ok': True}
