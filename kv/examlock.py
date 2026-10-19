# -*- coding: utf-8 -*-
"""Mở rộng chế độ thi (từ bản 3.8.0): khóa ổ USB, chặn in, chặn sao chép-dán, thu file bài làm.

- USB và in: script kvexam.ps1 chạy bằng SYSTEM (chính sách "Removable Disks: Deny read/write" và dừng Print Spooler).
  Cả hai nằm trong registry/dịch vụ nên TỒN TẠI sau khi khởi động lại: phải mở lại khi hết thi.
- Sao chép-dán: script kvclip.ps1 chạy trong phiên của học sinh, xóa clipboard mỗi 0,4 giây. Mất khi máy khởi động lại.
- Thu bài: chép file mới sửa từ các thư mục chỉ định trên máy học sinh (qua \\\\máy\\C$) về máy giáo viên."""

import json
import os
import re
import shutil
import tempfile
import time

from .paths import CONFIG_PATH, load_script
from .remote import distribute_to_host, logged_on_user, remote_run, unc_target
from .runtime import ApiError, CFG, CFG_LOCK, clean_hosts, log, pool_run, split_host_port, start_job
from .screenshot import _q
from .vcfg import client_script_run, vcfg_remote_dir


EXAM_PS1_NAME, EXAM_PS1 = 'kvexam.ps1', load_script('kvexam.ps1')
CLIP_PS1_NAME, CLIP_PS1 = 'kvclip.ps1', load_script('kvclip.ps1')
CLIP_TASK = 'KhoaVeyonClip'
CLIP_STOP = 'kvclip.stop'
LOCK_WHAT = ('usb', 'print')
COLLECT_MAX_FILE = 50 * 1024 * 1024        # bỏ qua file lớn hơn
COLLECT_MAX_TOTAL = 500 * 1024 * 1024      # tối đa mỗi máy
COLLECT_MAX_FILES = 1000
DEFAULT_COLLECT_PATHS = [r'C:\BaiLam']


def examfiles_root():
    d = os.path.join(os.path.dirname(CONFIG_PATH), 'exam_files')
    os.makedirs(d, exist_ok=True)
    return d


def _bom_copy(tmp, name, text):
    p = os.path.join(tmp, name)
    with open(p, 'w', encoding='utf-8-sig', newline='') as f:  # BOM để PowerShell 5 đọc đúng tiếng Việt
        f.write(text.replace('\r\n', '\n').replace('\n', '\r\n'))
    return p


def lock_bat(rdir, how, what):
    return '@echo off\npowershell -NoProfile -ExecutionPolicy Bypass -File "%s\\%s" -Mode %s -What "%s"\nexit /b %%errorlevel%%\n' % (
        rdir, EXAM_PS1_NAME, how, ','.join(what))


def lock_one(cfg, host, how, what):
    """Khóa hoặc mở USB / in trên một máy (SYSTEM qua schtasks)."""
    tmp = tempfile.mkdtemp(prefix='kvexam')
    try:
        sp = _bom_copy(tmp, EXAM_PS1_NAME, EXAM_PS1)
        ok, msg = client_script_run(host, cfg, 'kvexam.bat', lock_bat(vcfg_remote_dir(cfg), how, what), files={EXAM_PS1_NAME: sp}, timeout=60)
        return ok, ('đã %s %s' % ('khóa' if how == 'on' else 'mở', ' và '.join({'usb': 'ổ USB', 'print': 'in ấn'}[w] for w in what))) if ok else msg
    except Exception as e:  # noqa
        return False, 'không chạy được script: %s' % e
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def clip_one(cfg, host, how):
    rdir = vcfg_remote_dir(cfg)
    hh, _ = split_host_port(host)
    if how == 'off':
        try:
            d = unc_target(hh, rdir)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, CLIP_STOP), 'w') as f:
                f.write('stop')
        except OSError as e:
            return False, 'không gỡ được chặn sao chép-dán: %s' % e
        return True, 'đã gỡ chặn sao chép-dán'
    tmp = tempfile.mkdtemp(prefix='kvclip')
    try:
        distribute_to_host(host, [_bom_copy(tmp, CLIP_PS1_NAME, CLIP_PS1)], rdir)
    except Exception as e:  # noqa
        return False, 'không chép được script: %s' % e
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        os.remove(os.path.join(unc_target(hh, rdir), CLIP_STOP))
    except OSError:
        pass
    cmd = 'powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -WindowStyle Hidden -File %s' % _q(rdir + '\\' + CLIP_PS1_NAME)
    rc, out = remote_run(host, cmd, interactive=True, name=CLIP_TASK)
    return (rc == 0), ('đã chặn sao chép-dán' if rc == 0 else out)


def job_exam_lock(how, what, hosts):
    """how: on | off. what: tập con của usb, print, clip."""
    sys_what = [w for w in LOCK_WHAT if w in what]
    with CFG_LOCK:
        cfg = json.loads(json.dumps(CFG))
    names = {'usb': 'USB', 'print': 'in ấn', 'clip': 'sao chép-dán'}
    label = '%s %s' % ('Khóa' if how == 'on' else 'Mở khóa', ', '.join(names[w] for w in what if w in names))
    log('>>> %s (%d máy)' % (label, len(hosts)), 'head')
    if sys_what:
        pool_run(lambda h: lock_one(cfg, h, how, sys_what), hosts, label)
    if 'clip' in what:
        pool_run(lambda h: clip_one(cfg, h, how), hosts, label + ' (clipboard)')


def collect_paths_clean(raw):
    """Danh sách thư mục cần thu: mỗi dòng một đường dẫn dạng C:\\... (có thể chứa {user}). Trả về list đã kiểm tra."""
    if isinstance(raw, str):
        raw = raw.splitlines()
    out = []
    for p in raw or []:
        p = str(p).strip().strip('"')
        if not p:
            continue
        if not re.match(r'^[A-Za-z]:[\\/]', p) or '..' in p.replace('\\', '/').split('/'):
            raise ApiError('Thư mục thu bài phải có dạng C:\\Thư mục (không dùng ..): %s' % p)
        if p not in out:
            out.append(p)
    return out[:10]


def _safe(name):
    return re.sub(r'[^\w.\-]+', '_', name, flags=re.UNICODE).strip('_') or 'x'


def collect_one(host, paths, since, dest_root, user_fn=logged_on_user):
    """Chép file có thời gian sửa >= since từ các thư mục chỉ định về dest_root/<máy>/. Trả về (ok, mô tả)."""
    hh, _ = split_host_port(host)
    user = ''
    if any('{user}' in p for p in paths):
        user = (user_fn(hh) or '').split('\\')[-1]
    copied = skipped = total = 0
    missing = []
    for raw in paths:
        if '{user}' in raw and not user:
            missing.append(raw + ' (chưa có ai đăng nhập)')
            continue
        p = raw.replace('{user}', user)
        try:
            root = unc_target(hh, p)
        except ValueError:
            missing.append(raw)
            continue
        if not os.path.isdir(root):
            missing.append(raw)
            continue
        tag = _safe(p)
        for dp, _dirs, files in os.walk(root):
            for fn in files:
                if fn.startswith('~$') or fn.lower().endswith(('.tmp', '.lnk')):
                    continue
                src = os.path.join(dp, fn)
                try:
                    st = os.stat(src)
                except OSError:
                    continue
                if st.st_mtime < since or st.st_size > COLLECT_MAX_FILE or copied >= COLLECT_MAX_FILES or total + st.st_size > COLLECT_MAX_TOTAL:
                    skipped += 1
                    continue
                dst = os.path.join(dest_root, _safe(host), tag, os.path.relpath(src, root))
                try:
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                    copied += 1
                    total += st.st_size
                except OSError:
                    skipped += 1
    note = ('; không thấy thư mục: ' + ', '.join(missing)) if missing else ''
    if skipped:
        note += '; bỏ qua %d file (cũ hơn giờ thi, quá lớn hoặc vượt giới hạn)' % skipped
    return (copied > 0 or not missing), 'đã thu %d file (%.1f MB)%s' % (copied, total / 1048576.0, note)


def job_exam_collect(hosts, paths, since):
    dest = os.path.join(examfiles_root(), time.strftime('%Y%m%d-%H%M%S'))
    log('>>> Thu file bài làm (%d máy, %d thư mục) về %s' % (len(hosts), len(paths), dest), 'head')
    pool_run(lambda h: collect_one(h, paths, since, dest), hosts, 'Thu file bài làm')
    return dest


def api_exam_release(b):
    """Gỡ khóa USB, in, sao chép-dán trên các máy đã chọn (dùng khi máy tắt lúc kết thúc thi nên còn bị khóa)."""
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào')
    start_job(job_exam_lock, 'off', ['usb', 'print', 'clip'], hosts)
    return {'ok': True}


def api_exam_collect(b):
    hosts = clean_hosts(b.get('hosts'))
    paths = collect_paths_clean(b.get('paths'))
    if not hosts or not paths:
        raise ApiError('Cần có máy và ít nhất một thư mục để thu')
    try:
        minutes = max(0, min(1440, int(b.get('minutes') or 180)))
    except (TypeError, ValueError):
        raise ApiError('Số phút phải là số')
    start_job(job_exam_collect, hosts, paths, time.time() - minutes * 60)
    return {'ok': True}
