# -*- coding: utf-8 -*-
"""API chính: trạng thái, chạy lệnh, cài đặt, phân phối file, thiết lập ban đầu, cập nhật, nhật ký."""

import json
import os
import re
import shutil
import threading
import time

from .actions import ACTION_BY_KEY
from .authkeys import job_authkeys, parse_authkeys
from .auto import job_run_key
from .config import save_config
from .evidence import evidence_root
from .examlock import examfiles_root
from .excel_lists import LISTS
from .jobs import job_dist, veyon_feature
from .meta import BOOL_KEYS, LIST_KEYS, STR_KEYS
from .network import scan_veyon_hosts
from .paths import abs_path, CONFIG_PATH, find_veyon_cli
from .remote import run_args, run_shell, sync_lists, unc_target, veyon_command
from .reports import report_root
from .runtime import (
    ApiError, BUSY_LOCK, CFG, CFG_LOCK, clean_hosts, JOBS, list_path, LOG, log, LOG_LOCK, LOG_SEQ,
    PAYLOAD_DIR, start_job, STATE,
)
from .screenshot import shot_root
from .setup import (
    elevated_apply_veyon_items, ensure_payload, find_script_file, is_admin, seed_default_lists,
    STUDENT_SETUP_BAT, veyon_items_status,
)
from .setup_jobs import job_cmd_lock, job_setup_all, job_setup_diagnose
from .updater import apply_update, check_update, restart_self


def api_run(b):
    key = b.get('key')
    if key not in ACTION_BY_KEY:
        raise ApiError('Lệnh không tồn tại')
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào để chạy')
    start_job(job_run_key, key, hosts)
    return {'ok': True}


def api_settings(b):
    with CFG_LOCK:
        new = json.loads(json.dumps(CFG))
        for k, v in b.items():
            if k in STR_KEYS:
                v = str(v).strip()
                if k == 'update_repo' and v and not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', v):
                    raise ApiError('Kho GitHub phải có dạng chủ-sở-hữu/tên-kho, ví dụ khoa/KhoaVeyon')
                if k == 'dist_mode' and v not in ('none', 'schtasks', 'veyon'):
                    raise ApiError('Cách chạy không hợp lệ')
                if k == 'dist_action' and v not in ACTION_BY_KEY:
                    raise ApiError('Mục Veyon không hợp lệ')
                if k == 'school_name':
                    v = v[:80]
                new[k] = v
            elif k in BOOL_KEYS:
                new[k] = bool(v)
            elif k in LIST_KEYS:
                new[k] = [str(x) for x in (v or [])]
            elif k == 'features' and isinstance(v, dict):
                for fk, fv in v.items():
                    if fk in ACTION_BY_KEY and str(fv).strip():
                        new['features'][fk] = str(fv).strip()
        for tk_ in ('run_template', 'list_template'):
            try:
                new[tk_].format(cli='x', host='h', feature='f')
            except Exception as e:  # noqa
                raise ApiError('Mẫu lệnh "%s" không hợp lệ (chỉ dùng {cli} {host} {feature}): %s' % (tk_, e))
        CFG.clear()
        CFG.update(new)
        save_config(CFG)
    return {'ok': True}


def resolve_dist_files(b):
    files = []
    if b.get('include_lists'):
        for k in LISTS:
            p = list_path(k)
            if os.path.exists(p):
                files.append(p)
    for name in b.get('payload') or []:
        p = os.path.join(PAYLOAD_DIR, os.path.basename(str(name)))
        files.append(p)
    for p in b.get('extra') or []:
        p = str(p).strip().strip('"')
        if p:
            files.append(p)
    return files


def api_dist(b):
    do_copy = bool(b.get('copy'))
    mode = b.get('mode', 'none') if b.get('run') else 'none'
    if mode not in ('none', 'schtasks', 'veyon'):
        raise ApiError('Cách chạy không hợp lệ')
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào để chạy')
    target = str(b.get('target') or '').strip()
    files = []
    if do_copy:
        files = resolve_dist_files(b)
        if not files:
            raise ApiError('Chưa có file nào để phân phối')
        missing = [f for f in files if not os.path.exists(abs_path(f))]
        if missing:
            raise ApiError('Không tìm thấy file:\n' + '\n'.join(missing[:8]))
        try:
            unc_target('x', target)
        except ValueError as e:
            raise ApiError(str(e))
    cmd, feature = '', ''
    if mode == 'schtasks':
        cmd = str(b.get('cmd') or '').strip()
        if not cmd:
            raise ApiError('Hãy nhập lệnh cần chạy trên máy học sinh')
    elif mode == 'veyon':
        action = b.get('action')
        if action not in ACTION_BY_KEY:
            raise ApiError('Mục Veyon không hợp lệ')
        feature = veyon_feature(action)
    if not do_copy and mode == 'none':
        raise ApiError('Chưa chọn việc cần làm')
    parts = []
    if do_copy:
        parts.append('chép %d mục sang %s' % (len(files), target))
    if mode == 'schtasks':
        parts.append('chạy lệnh: %s' % cmd)
    elif mode == 'veyon':
        parts.append('kích hoạt mục Veyon "%s"' % feature)
    start_job(job_dist, hosts, files, mode, cmd, feature, bool(b.get('interactive')), target, 'Phân phối & chạy: ' + '; '.join(parts))
    return {'ok': True}


def api_payload(_q=None):
    os.makedirs(PAYLOAD_DIR, exist_ok=True)
    items = []
    for name in sorted(os.listdir(PAYLOAD_DIR), key=str.lower):
        p = os.path.join(PAYLOAD_DIR, name)
        isdir = os.path.isdir(p)
        size = 0 if isdir else os.path.getsize(p)
        items.append({'name': name, 'dir': isdir, 'size': size})
    return {'items': items, 'dir': PAYLOAD_DIR}


def api_payload_delete(b):
    name = os.path.basename(str(b.get('name') or ''))
    p = os.path.join(PAYLOAD_DIR, name)
    if not name or not os.path.exists(p):
        raise ApiError('Không tìm thấy file')
    if os.path.isdir(p):
        shutil.rmtree(p)
    else:
        os.remove(p)
    return {'ok': True}


def api_open(b):
    with CFG_LOCK:
        folders = {'payload': PAYLOAD_DIR, 'lists': abs_path(CFG['list_dir']), 'data': os.path.dirname(CONFIG_PATH), 'shots': shot_root(), 'evidence': evidence_root(), 'reports': report_root(), 'examfiles': examfiles_root()}
    p = folders.get(b.get('what'))
    if not p:
        raise ApiError('Thư mục không hợp lệ')
    os.makedirs(p, exist_ok=True)
    if os.name == 'nt':
        os.startfile(p)  # noqa
    else:
        raise ApiError('Chỉ mở được thư mục trên Windows. Đường dẫn: %s' % p)
    return {'ok': True}


def api_veyon_list(b):
    host = str(b.get('host') or '').strip()
    if not host:
        raise ApiError('Hãy thêm ít nhất một máy ở trang Điều khiển lớp học')

    def work():
        try:
            with CFG_LOCK:
                cmd = veyon_command(CFG, host, '', 'list_template')
        except Exception as e:  # noqa
            log('Lỗi mẫu lệnh: %s' % e, 'err')
            return
        rc, out = run_shell(cmd)
        log('>>> veyon-cli feature list (%s) -> mã %s\n%s' % (host, rc, out), 'head' if rc == 0 else 'err')
    start_job(work)
    return {'ok': True}


def api_setup_status(_q=None):
    with CFG_LOCK:
        cfg = json.loads(json.dumps(CFG))
    cli = find_veyon_cli(cfg['veyon_cli'])
    have, total, err = veyon_items_status(cfg)
    auth_names = []
    if os.path.isfile(cli):
        rc_k, out_k = run_args([cli, 'authkeys', 'list'], timeout=20)
        if rc_k == 0:
            auth_names = sorted(n for n, t in parse_authkeys(out_k).items() if 'private' in t)
    lists_ok = sum(1 for k in LISTS if os.path.exists(list_path(k)))
    sname = os.path.basename((cfg.get('script_path') or '').replace('\\', '/')) or 'KhoaVeyonServices.bat'
    return {'cli': os.path.isfile(cli), 'cli_path': cli, 'items_have': have, 'items_total': total, 'items_err': err, 'auth_names': auth_names,
            'admin': is_admin(), 'lists_ok': lists_ok, 'lists_total': len(LISTS),
            'script_name': sname, 'script_in_payload': os.path.isfile(os.path.join(PAYLOAD_DIR, sname)),
            'script_found': bool(find_script_file(cfg)),
            'student_bat': os.path.isfile(os.path.join(PAYLOAD_DIR, STUDENT_SETUP_BAT)),
            'hosts': len(cfg.get('hosts') or []), 'done': bool(cfg.get('setup_done')), 'windows': os.name == 'nt'}


def api_setup_run(b):
    step = b.get('step')
    hosts = clean_hosts(b.get('hosts'))
    with CFG_LOCK:
        cfg = json.loads(json.dumps(CFG))
    if step == 'all':
        start_job(job_setup_all, hosts)
    elif step == 'lists':
        n = seed_default_lists(cfg)
        log('Danh sách Excel: đã tạo %d file mẫu' % n if n else 'Danh sách Excel: đã có đủ, giữ nguyên', 'ok')
    elif step == 'payload':
        got, missing = ensure_payload(cfg)
        log('Đã tạo payload\\%s' % STUDENT_SETUP_BAT + (', lấy %s' % ', '.join(got) if got else ''), 'ok')
        if missing:
            log('Chưa tìm thấy %s: hãy thêm vào payload (trang Phân phối & chạy)' % ', '.join(missing), 'warn')
    elif step == 'authkeys':
        start_job(job_authkeys, hosts)
    elif step == 'veyon':
        def work():
            ok, msg = elevated_apply_veyon_items(cfg)
            log('Mục Veyon: ' + msg, 'ok' if ok else 'err')
        start_job(work)
    elif step in ('lock', 'unlock'):
        if not hosts:
            raise ApiError('Chưa có máy học sinh nào')
        start_job(job_cmd_lock, hosts, step == 'lock')
    elif step == 'veyonkit':
        if not hosts:
            raise ApiError('Chưa có máy học sinh nào')
        from .veyonkit import job_veyon_kit
        start_job(job_veyon_kit, hosts)
    elif step in ('diagnose', 'push'):
        if not hosts:
            raise ApiError('Chưa có máy học sinh nào')
        start_job(job_setup_diagnose, hosts, step == 'push')
    else:
        raise ApiError('Bước "%s" không hợp lệ. Nếu vừa chép file mới, hãy tắt KhoaVeyon (Task Manager, pythonw.exe) rồi chạy lại Chay-KhoaVeyon.bat.' % step)
    return {'ok': True}


def api_setup_scan(_b=None):
    names, err = scan_veyon_hosts()
    if err:
        raise ApiError(err)
    added = 0
    with CFG_LOCK:
        for n in names:
            if n not in CFG['hosts']:
                CFG['hosts'].append(n)
                added += 1
        save_config(CFG)
        hosts = list(CFG['hosts'])
    log('Quét mạng: thấy %d máy chạy Veyon, thêm mới %d' % (len(names), added), 'ok' if names else 'warn')
    return {'found': names, 'added': added, 'hosts': hosts}


def api_setup_done(b):
    with CFG_LOCK:
        CFG['setup_done'] = bool(b.get('done', True))
        save_config(CFG)
    return {'ok': True}


def api_update_check(_q=None):
    with CFG_LOCK:
        repo = CFG.get('update_repo', '')
    info = check_update(repo)
    STATE['update'] = info
    return info


def api_update_apply(_b=None):
    info = STATE.get('update') or {}
    if not info.get('newer') or not info.get('url'):
        raise ApiError('Chưa có bản mới để cập nhật (hãy bấm kiểm tra trước)')

    def work():
        try:
            files = apply_update(info['url'])
            log('Đã cập nhật %d file lên %s, đang khởi động lại...' % (len(files), info['latest']), 'ok')
            restart_self()
        except Exception as e:  # noqa
            log('Cập nhật lỗi, giữ nguyên bản cũ: %s' % e, 'err')
    start_job(work)
    return {'ok': True}


def api_sync(_b=None):
    with CFG_LOCK:
        try:
            n, err = sync_lists(CFG)
        except Exception as e:  # noqa
            n, err = 0, str(e)
        dst = CFG.get('sync_dir')
    if err:
        raise ApiError(err)
    log('Đã đồng bộ %d file sang %s' % (n, dst), 'ok')
    return {'ok': True, 'count': n}


def api_log(q):
    STATE['last_ping'] = time.time()
    STATE['pinged'] = True
    since = int(q.get('since') or 0)
    with LOG_LOCK:
        items = [e for e in LOG if e['id'] > since]
        last = LOG_SEQ[0]
    with BUSY_LOCK:
        jobs = [dict(j) for j in JOBS.values()]
    return {'items': items, 'last': last, 'busy': STATE['busy'], 'jobs': jobs}


def api_ping(_q=None):
    STATE['last_ping'] = time.time()
    STATE['pinged'] = True
    return {'ok': True}


def api_quit(_b=None):
    srv = STATE.get('server')
    if srv:
        threading.Timer(0.4, srv.shutdown).start()
    return {'ok': True}
