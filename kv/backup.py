# -*- coding: utf-8 -*-
"""Sao lưu và khôi phục toàn bộ cài đặt (một file .zip): danh sách máy, tên hiển thị, cấu hình, lớp, thời khóa biểu, sơ đồ, danh sách Excel.
Dùng để chuyển sang máy giáo viên khác hoặc cài lại Windows. Ảnh vi phạm và ảnh chụp màn hình không nằm trong file sao lưu."""

import io
import json
import os
import time
import zipfile

from .config import save_config
from .paths import abs_path, CONFIG_PATH, VERSION
from .runtime import ApiError, CFG, CFG_LOCK, log
from .school import SCHOOL, SCHOOL_LOCK, school_path, school_save

MAGIC = 'KhoaVeyon-backup'
MAX_BACKUP = 40 * 1024 * 1024
# cài đặt riêng của từng máy giáo viên: không chép sang máy khác khi khôi phục (đường dẫn, địa chỉ mạng, khóa Veyon...)
MACHINE_KEYS = {'veyon_cli', 'list_dir', 'script_path', 'sync_dir', 'agent_host', 'agent_port', 'client_veyon_cli', 'auth_key_name',
                'netobj_location', 'update_skip', 'dist_target'}
SECRET_KEYS = {'agent_token'}
LIST_EXT = ('.xlsx', '.txt')


def _list_files():
    with CFG_LOCK:
        d = abs_path(CFG['list_dir'])
    out = []
    if os.path.isdir(d):
        for n in sorted(os.listdir(d)):
            p = os.path.join(d, n)
            if os.path.isfile(p) and n.lower().endswith(LIST_EXT) and not n.startswith('~$') and os.path.getsize(p) < 5 * 1024 * 1024:
                out.append((n, p))
    return out


def make_backup(include_secrets=True):
    """Trả về bytes của file .zip sao lưu."""
    with CFG_LOCK:
        cfg = json.loads(json.dumps(CFG))
    if not include_secrets:
        for k in SECRET_KEYS:
            cfg.pop(k, None)
    school_save()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json', json.dumps({'magic': MAGIC, 'version': VERSION, 'created': time.strftime('%Y-%m-%d %H:%M:%S'),
                                                'secrets': bool(include_secrets)}, ensure_ascii=False, indent=1))
        z.writestr('config.json', json.dumps(cfg, ensure_ascii=False, indent=1))
        try:
            z.write(school_path(), 'school.json')
        except OSError:
            pass
        for n, p in _list_files():
            z.write(p, 'lists/' + n)
        wd = os.path.join(os.path.dirname(CONFIG_PATH), 'walls')
        if os.path.isdir(wd):
            for n in sorted(os.listdir(wd)):
                if n.endswith('.jpg') and os.path.getsize(os.path.join(wd, n)) < 4 * 1024 * 1024:
                    z.write(os.path.join(wd, n), 'walls/' + n)
    return buf.getvalue()


def backup_name():
    return 'KhoaVeyon-backup-%s.zip' % time.strftime('%Y%m%d-%H%M')


def _read_zip(data):
    if len(data) > MAX_BACKUP:
        raise ApiError('File sao lưu quá lớn (tối đa 40 MB)')
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ApiError('Đây không phải file sao lưu KhoaVeyon (.zip)')
    names = z.namelist()
    if 'manifest.json' not in names:
        raise ApiError('Thiếu manifest.json: không phải file sao lưu KhoaVeyon')
    try:
        man = json.loads(z.read('manifest.json').decode('utf-8'))
    except ValueError:
        raise ApiError('manifest.json hỏng')
    if man.get('magic') != MAGIC:
        raise ApiError('Không phải file sao lưu KhoaVeyon')
    return z, man


def preview_backup(data):
    """Đọc nội dung file sao lưu để hiện cho giáo viên xem trước khi khôi phục."""
    z, man = _read_zip(data)
    out = {'version': man.get('version', ''), 'created': man.get('created', ''), 'secrets': bool(man.get('secrets')),
           'hosts': 0, 'classes': 0, 'slots': 0, 'lists': [n[6:] for n in z.namelist() if n.startswith('lists/')]}
    try:
        c = json.loads(z.read('config.json').decode('utf-8'))
        out['hosts'] = len(c.get('hosts') or [])
    except (KeyError, ValueError):
        pass
    try:
        s = json.loads(z.read('school.json').decode('utf-8'))
        out['classes'] = len(s.get('classes') or {})
        out['slots'] = len(s.get('slots') or [])
    except (KeyError, ValueError):
        pass
    return out


def restore_backup(data, parts=None):
    """Khôi phục từ file sao lưu. parts: tập con của {'config','school','lists'} (mặc định cả ba). Tự sao lưu bản hiện tại trước khi ghi."""
    z, _man = _read_zip(data)
    parts = set(parts or ('config', 'school', 'lists'))
    base = os.path.dirname(CONFIG_PATH)
    try:   # bản sao lưu an toàn của trạng thái hiện tại, phòng khôi phục nhầm
        os.makedirs(base, exist_ok=True)
        with open(os.path.join(base, 'truoc-khi-khoi-phuc.zip'), 'wb') as f:
            f.write(make_backup(True))
    except OSError:
        pass
    done = []
    if 'config' in parts and 'config.json' in z.namelist():
        try:
            c = json.loads(z.read('config.json').decode('utf-8'))
        except ValueError:
            raise ApiError('config.json trong file sao lưu bị hỏng')
        if not isinstance(c, dict):
            raise ApiError('config.json không hợp lệ')
        with CFG_LOCK:
            for k, v in c.items():
                if k in MACHINE_KEYS or k not in CFG:
                    continue
                if isinstance(CFG[k], dict) and isinstance(v, dict):
                    CFG[k] = v
                elif type(CFG[k]) is type(v) or CFG[k] in (None, ''):
                    CFG[k] = v
            save_config(CFG)
        done.append('cấu hình và danh sách máy')
    if 'school' in parts and 'school.json' in z.namelist():
        try:
            s = json.loads(z.read('school.json').decode('utf-8'))
        except ValueError:
            raise ApiError('school.json trong file sao lưu bị hỏng')
        if isinstance(s, dict):
            with SCHOOL_LOCK:
                SCHOOL.update({k: s[k] for k in SCHOOL if k in s})
            school_save()
            import re as _re
            wd = os.path.join(base, 'walls')
            for name in z.namelist():
                fn = os.path.basename(name)
                if name.startswith('walls/') and _re.match(r'^[0-9a-f]{16}\.jpg$', fn):
                    os.makedirs(wd, exist_ok=True)
                    with open(os.path.join(wd, fn), 'wb') as f:
                        f.write(z.read(name))
            done.append('lớp, thời khóa biểu, sơ đồ, hình nền')
    if 'lists' in parts:
        with CFG_LOCK:
            d = abs_path(CFG['list_dir'])
        os.makedirs(d, exist_ok=True)
        n = 0
        for name in z.namelist():
            if not name.startswith('lists/'):
                continue
            fn = os.path.basename(name)
            if not fn or not fn.lower().endswith(LIST_EXT) or fn.startswith('~$'):
                continue
            with open(os.path.join(d, fn), 'wb') as f:
                f.write(z.read(name))
            n += 1
        if n:
            done.append('%d danh sách Excel' % n)
    log('Đã khôi phục từ file sao lưu: ' + (', '.join(done) or 'không có gì để khôi phục'), 'ok' if done else 'warn')
    return done
