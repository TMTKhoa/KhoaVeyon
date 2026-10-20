# -*- coding: utf-8 -*-
"""Khóa xác thực Veyon: tạo và xuất khóa ở máy giáo viên, chép khóa công khai xuống máy học sinh."""

import json
import os
import re
import stat

from .paths import find_veyon_cli
from .remote import run_args
from .runtime import CFG, CFG_LOCK, log, pool_run
from .vcfg import _bat, client_cli_path, client_script_run, elevated_op, vcfg_dir, vcfg_remote_dir


AUTHKEY_DEFAULT = 'KhoaVeyon'  # tên cặp khóa tự tạo khi Veyon chưa có cặp khóa nào


def force_remove(path):
    """Xóa file kể cả khi nó có thuộc tính chỉ-đọc. veyon-cli xuất khóa ra file chỉ-đọc, mà Windows không cho xóa file chỉ-đọc
    bằng os.remove, nên lần xuất sau báo \"already exists\". Trả về True nếu file không còn."""
    if not os.path.lexists(path):
        return True
    try:
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
    except OSError:
        pass
    try:
        os.remove(path)
    except OSError:
        pass
    return not os.path.lexists(path)


def parse_authkeys(out):
    """Đọc kết quả `veyon-cli authkeys list` thành {tên: {'private', 'public'}}. Định dạng chưa kiểm chứng nên thử nhiều cách."""
    keys = {}
    for m in re.finditer(r'([^\s/\\:;|,]+)/(private|public)\b', out or '', re.I):
        keys.setdefault(m.group(1), set()).add(m.group(2).lower())
    if not keys:
        for line in (out or '').splitlines():
            parts = [x for x in re.split(r'[\s;|]+', line.strip()) if x]
            if len(parts) >= 2 and parts[1].lower() in ('private', 'public'):
                keys.setdefault(parts[0], set()).add(parts[1].lower())
    return keys


def authkeys_dir():
    d = os.path.join(vcfg_dir(), 'authkeys')
    os.makedirs(d, exist_ok=True)
    return d


def authkeys_prepare_master(cfg, want=''):
    """Dùng cặp khóa có sẵn trên máy giáo viên (ưu tiên), chưa có mới tạo; xuất khóa public ra file để chép xuống máy học sinh."""
    cli = find_veyon_cli(cfg['veyon_cli'])
    if not os.path.isfile(cli):
        return False, 'Chưa thấy veyon-cli.exe'
    rc, out = run_args([cli, 'authkeys', 'list'], timeout=30)
    keys = parse_authkeys(out) if rc == 0 else {}
    want = (want or '').strip()
    name, note = '', ''
    if want and want in keys:
        name = want
    elif want and not keys.get(want):
        name = want  # người dùng chỉ định tên chưa có: sẽ tạo
    else:
        pairs = sorted(n for n, t in keys.items() if 'private' in t)
        both = [n for n in pairs if 'public' in keys[n]]
        name = (both or pairs or [''])[0]
    if name and 'private' in keys.get(name, ()):
        note = 'dùng cặp khóa có sẵn "%s"' % name
        if 'public' not in keys[name]:
            rc, out = run_args([cli, 'authkeys', 'extract', name], timeout=30)
            if rc != 0:
                return False, 'authkeys extract lỗi (%s): %s' % (rc, out[:200])
            note += ' (đã tách khóa public)'
    else:
        name = name or AUTHKEY_DEFAULT
        rc, out = run_args([cli, 'authkeys', 'create', name], timeout=30)
        if rc != 0:
            return False, 'Chưa có cặp khóa và tạo mới lỗi (%s): %s' % (rc, out[:200])
        note = 'chưa có cặp khóa nên đã tạo mới "%s"' % name
    dest = os.path.join(authkeys_dir(), '%s_public.pem' % name)
    if not force_remove(dest):
        return False, ('Không xóa được file khóa cũ %s (đang mở bởi chương trình khác hoặc không đủ quyền). '
                       'Đóng chương trình đang mở file đó rồi thử lại.' % dest)
    rc, out = run_args([cli, 'authkeys', 'export', '%s/public' % name, dest], timeout=30)
    if rc != 0 or not os.path.isfile(dest) or os.path.getsize(dest) == 0:
        return False, 'authkeys export lỗi (%s): %s' % (rc, out[:200])
    try:  # file xuất ra là chỉ-đọc: bỏ thuộc tính này để lần sau ghi đè được
        os.chmod(dest, stat.S_IREAD | stat.S_IWRITE)
    except OSError:
        pass
    with open(os.path.join(authkeys_dir(), 'current.txt'), 'w', encoding='utf-8') as f:
        f.write(name)
    return True, '%s, đã xuất khóa public ra %s' % (note, dest)


def authkeys_push_client(cfg, host, name, pub):
    """Chép khóa public xuống máy học sinh. Máy đã có đúng khóa này (so từng byte) thì bỏ qua."""
    t, cli = vcfg_remote_dir(cfg), client_cli_path(cfg)
    k = '%s/public' % name
    cur, new = t + '\\cur-key.pem', t + '\\key.pem'
    lines = ['chcp 65001 >nul',
             'del /f /q "%s" >nul 2>&1' % cur,
             '"%s" authkeys export "%s" "%s" >nul 2>&1' % (cli, k, cur),
             'if not exist "%s" goto imp' % cur,
             'fc /b "%s" "%s" >nul 2>&1' % (cur, new),
             'if errorlevel 1 goto imp',
             'del /f /q "%s" "%s" >nul 2>&1' % (cur, new),
             'exit /b 0',
             ':imp',
             '"%s" authkeys import "%s" "%s"' % (cli, k, new),
             'set R=%errorlevel%',
             'del /f /q "%s" "%s" >nul 2>&1' % (cur, new),
             'exit /b %R%']
    ok, msg = client_script_run(host, cfg, 'authkey-push.bat', _bat(lines), files={'key.pem': pub}, timeout=90)
    return ok, ('khóa "%s" đã khớp với máy giáo viên' % name) if ok else 'import khóa lỗi: %s' % msg


def job_authkeys(hosts):
    with CFG_LOCK:
        cfg = json.loads(json.dumps(CFG))
    log('>>> Khóa xác thực Veyon: dùng khóa có sẵn và chép xuống máy học sinh', 'head')
    ok, msg = elevated_op('authkeys', {'name': cfg.get('auth_key_name', '')})
    log('[master] %s %s' % ('OK' if ok else 'LỖI', msg), 'ok' if ok else 'err')
    if not ok:
        return
    try:
        with open(os.path.join(authkeys_dir(), 'current.txt'), 'r', encoding='utf-8') as f:
            name = f.read().strip()
    except OSError:
        log('Không đọc được tên khóa vừa xuất', 'err')
        return
    pub = os.path.join(authkeys_dir(), '%s_public.pem' % name)
    if not hosts:
        log('Chưa có máy học sinh nên chưa chép khóa được: bấm "Tìm máy học sinh trong mạng" rồi chạy lại.', 'warn')
        return
    pool_run(lambda h: authkeys_push_client(cfg, h, name, pub), hosts, 'Gửi khóa xác thực')
