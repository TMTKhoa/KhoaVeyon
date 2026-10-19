# -*- coding: utf-8 -*-
"""Thiết lập máy học sinh: khóa thư mục C:\\cmd, chẩn đoán, gửi file, cài dịch vụ."""

import json
import os

from concurrent.futures import ThreadPoolExecutor

from .authkeys import job_authkeys
from .config import save_config
from .excel_lists import LISTS
from .jobs import job_dist
from .network import diagnose_host
from .paths import CONFIG_PATH, load_script
from .remote import distribute_to_host, remote_install, remote_run_wait
from .runtime import CFG, CFG_LOCK, list_path, log, PAYLOAD_DIR, pool_run
from .setup import (
    _apply_with_firewall as _apply_with_firewall_, apply_veyon_items, elevated_apply_veyon_items, ensure_payload, seed_default_lists, SETUP_RESULT,
    STUDENT_SETUP_BAT,
)


CMDLOCK_NAME = 'CmdLock.bat'
CMDLOCK_BAT = load_script('cmdlock.bat')


def _kit_only(name):
    """File chỉ dành cho bộ cài ban đầu (bộ cài Veyon, khóa public): không gửi hàng loạt xuống C:\\cmd."""
    n = name.lower()
    return n == 'khoaveyonagent.cfg' or n.endswith('.pem') or (n.endswith('.exe') and 'veyon' in n)


def kit_copy_key():
    """Chép khóa public vừa xuất vào payload để Setup-MayHocSinh.bat nhập cùng lúc. Trả về tên file hoặc ''."""
    from .authkeys import authkeys_dir
    try:
        with open(os.path.join(authkeys_dir(), 'current.txt'), 'r', encoding='utf-8') as f:
            name = f.read().strip()
        src = os.path.join(authkeys_dir(), '%s_public.pem' % name)
        if name and os.path.isfile(src):
            os.makedirs(PAYLOAD_DIR, exist_ok=True)
            dst = os.path.join(PAYLOAD_DIR, os.path.basename(src))
            import shutil
            shutil.copy2(src, dst)
            return os.path.basename(dst)
    except OSError:
        pass
    return ''


def job_cmd_lock(hosts, lock):
    with CFG_LOCK:
        cfg = json.loads(json.dumps(CFG))
    folder = os.path.dirname(CONFIG_PATH)
    src = os.path.join(folder, CMDLOCK_NAME)
    with open(src, 'w', encoding='utf-8', newline='') as f:
        f.write(CMDLOCK_BAT.replace('\r\n', '\n').replace('\n', '\r\n'))
    target = cfg['dist_target'].rstrip('\\/')
    log('>>> %s %s (%d máy)' % ('Khóa' if lock else 'Mở khóa', target, len(hosts)), 'head')

    def one(h):
        try:
            distribute_to_host(h, [src], cfg['dist_target'])
        except Exception as e:  # noqa
            return False, 'không chép được %s: %s' % (CMDLOCK_NAME, e)
        ok, msg = remote_run_wait(h, 'cmd.exe /c %s\\%s %s <nul' % (target, CMDLOCK_NAME, 'lock' if lock else 'unlock'))
        return ok, ('đã khóa, học sinh chỉ đọc (log vẫn ghi được)' if lock else 'đã mở khóa') if ok else msg
    pool_run(one, hosts, 'Khóa hoặc mở khóa thư mục C:\\cmd')


def job_setup_diagnose(hosts, push):
    cfg = json.loads(json.dumps(CFG))
    log('>>> Kiểm tra %d máy học sinh' % len(hosts), 'head')
    ready, results = [], []

    def one(h):
        checks = diagnose_host(cfg, h)
        return h, checks
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(hosts)))) as ex:
        for h, checks in ex.map(one, hosts):
            results.append((h, checks))
            bad = [c for c in checks if not c[1]]
            log('[%s] %s' % (h, 'đã thiết lập đủ, không cần làm gì' if not bad else 'còn %d mục chưa đạt' % len(bad)), 'ok' if not bad else 'warn')
            for lab, ok, hint in checks:
                log('    %s %s%s' % ('✔' if ok else '✘', lab, '' if ok else '  →  ' + hint), 'ok' if ok else 'err')
            if not bad:
                continue
            if checks[1][1]:  # chép được file
                ready.append(h)
    need_install = [h for h, c in results if len(c) > 4 and not c[4][1]]
    if push and ready:
        files = [list_path(k) for k in LISTS if os.path.exists(list_path(k))]
        for f in sorted(os.listdir(PAYLOAD_DIR)) if os.path.isdir(PAYLOAD_DIR) else []:
            if f != STUDENT_SETUP_BAT and not _kit_only(f):
                files.append(os.path.join(PAYLOAD_DIR, f))
        if files:
            job_dist(ready, files, 'none', '', '', False, cfg['dist_target'], 'Gửi file thiết lập xuống %d máy' % len(ready))
        todo = [h for h in ready if h in need_install]
        sname = os.path.basename((cfg.get('script_path') or '').replace('\\', '/'))
        if todo and os.path.isfile(os.path.join(PAYLOAD_DIR, sname)):
            log('>>> Cài dịch vụ (%s -install) trên %d máy' % (sname, len(todo)), 'head')

            def inst(h):
                # <nul để lệnh pause trong script không treo khi chạy nền bằng SYSTEM
                ok, msg = remote_install(h, cfg['script_path'])
                return ok, 'đã cài dịch vụ' if ok else '-install lỗi: ' + msg
            pool_run(inst, todo, 'Cài dịch vụ trên máy học sinh')
        elif todo:
            log('Chưa có %s trong payload nên chưa cài dịch vụ được.' % sname, 'warn')
        if cfg.get('auto_lock'):
            job_cmd_lock(ready, True)
    elif push:
        pending = [h for h, c in results if any(not x[1] for x in c)]
        if pending:
            log('Máy chưa chép được file (%s): chạy %s trên các máy này một lần (quyền quản trị), rồi bấm lại.' % (', '.join(pending), STUDENT_SETUP_BAT), 'warn')
        else:
            log('Tất cả máy đã thiết lập đủ.', 'ok')


def job_setup_all(hosts):
    with CFG_LOCK:
        cfg = json.loads(json.dumps(CFG))
    log('>>> Thiết lập máy giáo viên', 'head')
    n = seed_default_lists(cfg)
    log('Danh sách Excel: đã tạo %d file mẫu' % n if n else 'Danh sách Excel: đã có đủ, giữ nguyên', 'ok')
    got, missing = ensure_payload(cfg)
    log('Đã tạo payload\\%s (chạy 1 lần trên mỗi máy học sinh)' % STUDENT_SETUP_BAT, 'ok')
    if got:
        log('Đã lấy %s vào payload' % ', '.join(got), 'ok')
    if missing:
        log('Chưa tìm thấy %s: hãy thêm vào payload (trang Phân phối & chạy)' % ', '.join(missing), 'warn')
    ok, msg = elevated_apply_veyon_items(cfg)
    log('Mục Veyon: ' + msg, 'ok' if ok else 'err')
    with CFG_LOCK:
        CFG['setup_done'] = True
        save_config(CFG)
    if hosts:  # tự động phân phối: kiểm tra, gửi file thiết lập và cài dịch vụ cho các máy học sinh
        log('>>> Tự động phân phối xuống %d máy học sinh' % len(hosts), 'head')
        job_setup_diagnose(hosts, True)
    else:
        log('Chưa có máy học sinh nên chưa phân phối được: bấm "Tìm máy học sinh trong mạng" rồi chạy lại.', 'warn')
    job_authkeys(hosts)
    key = kit_copy_key()
    inst = [f for f in (os.listdir(PAYLOAD_DIR) if os.path.isdir(PAYLOAD_DIR) else []) if f.lower().endswith('.exe') and 'veyon' in f.lower()]
    log('Bộ cài máy học sinh (thư mục payload): Setup-MayHocSinh.bat%s%s' % (' + khóa ' + key if key else ' (chưa có khóa public)',
        ' + ' + inst[0] if inst else ' (chưa có bộ cài Veyon: thêm veyon-*-setup.exe vào payload nếu máy học sinh chưa cài Veyon)'), 'ok')
    log('--- xong thiết lập máy giáo viên và phân phối ---', 'head')


def run_apply_mode():
    """Chế độ phụ (chạy bằng quyền quản trị): ghi mục Veyon rồi lưu kết quả cho tiến trình chính đọc."""
    try:
        ok, msg = _apply_with_firewall_(CFG)
    except Exception as e:  # noqa
        ok, msg = False, 'Lỗi: %s' % e
    with open(SETUP_RESULT(), 'w', encoding='utf-8') as f:
        json.dump({'ok': ok, 'msg': msg}, f, ensure_ascii=False)
