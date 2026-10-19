# -*- coding: utf-8 -*-
"""Cấu hình Veyon: sao lưu, so sánh, đẩy xuống máy học sinh, nhóm máy trong Veyon Master, nâng quyền quản trị."""

import json
import os
import re
import shutil
import sys
import tempfile
import time

from .config import DEFAULT_CONFIG, save_config
from .paths import APP_DIR, CONFIG_PATH, ENTRY_SCRIPT, find_veyon_cli
from .remote import distribute_to_host, remote_run_wait, run_args, unc_target
from .runtime import ApiError, CFG, CFG_LOCK, clean_hosts, log, pool_run, start_job
from .setup import is_admin, SETUP_RESULT


# ---------------------------------------------------------------- cấu hình Veyon: sao lưu, so sánh, khôi phục, đẩy xuống client, danh sách máy của Master
VCFG_KEY_RE = re.compile(r'^[A-Za-z0-9_]+(/[A-Za-z0-9_]+)+$')
VCFG_PRESETS = [  # (khóa, giá trị, mô tả). Chưa kiểm chứng trên Veyon thật: xem lại bằng "So sánh" sau khi đẩy.
    ('Network/PrimaryServicePort', '11100', 'Cổng Veyon Service'),
    ('Network/FirewallExceptionEnabled', 'true', 'Tự mở tường lửa cho Veyon'),
    ('Service/Autostart', 'true', 'Veyon Service tự khởi động cùng Windows'),
]
VCFG_RESTART = ['net stop VeyonService >nul 2>&1', 'net start VeyonService >nul 2>&1']


def vcfg_dir():
    d = os.path.join(os.path.dirname(CONFIG_PATH), 'veyon-backups')
    os.makedirs(d, exist_ok=True)
    return d


def vcfg_stamp():
    return time.strftime('%Y%m%d-%H%M%S')


def vcfg_safe(name):
    return re.sub(r'[^A-Za-z0-9.-]', '-', str(name))


def vcfg_remote_dir(cfg):
    return cfg['dist_target'].rstrip('\\/') + '\\vcfg'


def client_cli_path(cfg):
    return (cfg.get('client_veyon_cli') or r'C:\Program Files\Veyon\veyon-cli.exe').strip()


def vcfg_flatten(data):
    out = {}
    if not isinstance(data, dict):
        return out
    for g, sub in data.items():
        if isinstance(sub, dict):
            for k, v in sub.items():
                out['%s/%s' % (g, k)] = v
        else:
            out[str(g)] = sub
    return out


def vcfg_load_file(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        return vcfg_flatten(json.load(f))


def vcfg_diff(a, b):
    rows = []
    for k in sorted(set(a) | set(b)):
        if k not in b:
            rows.append(('-', k, a[k], None))
        elif k not in a:
            rows.append(('+', k, None, b[k]))
        elif a[k] != b[k]:
            rows.append(('~', k, a[k], b[k]))
    return rows


def _short(v, n=90):
    s = json.dumps(v, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + '…'


def _bat(lines):
    return '@echo off\n' + '\n'.join(lines) + '\n'


def vcfg_export_master(cfg, dest):
    cli = find_veyon_cli(cfg['veyon_cli'])
    if not os.path.isfile(cli):
        return False, 'Chưa thấy veyon-cli.exe (đặt đường dẫn ở Cài đặt)'
    rc, out = run_args([cli, 'config', 'export', dest], timeout=60)
    if rc != 0 or not os.path.isfile(dest):
        return False, 'veyon-cli config export lỗi (%s): %s' % (rc, out)
    return True, ''


def client_script_run(host, cfg, bat_name, bat_text, files=None, timeout=90):
    """Chép file .bat (và các file kèm) vào <đích>\\vcfg trên máy học sinh, chạy bằng SYSTEM, đợi xong."""
    rdir = vcfg_remote_dir(cfg)
    tmp = tempfile.mkdtemp(prefix='kvcfg')
    try:
        bp = os.path.join(tmp, bat_name)
        with open(bp, 'w', encoding='utf-8', newline='') as f:
            f.write(bat_text.replace('\r\n', '\n').replace('\n', '\r\n'))
        srcs = [bp]
        for name, src in (files or {}).items():
            dst = os.path.join(tmp, name)
            shutil.copy2(src, dst)
            srcs.append(dst)
        distribute_to_host(host, srcs, rdir)
        return remote_run_wait(host, 'cmd.exe /c %s\\%s <nul' % (rdir, bat_name), timeout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def client_fetch(host, cfg, name, dest):
    src = os.path.join(unc_target(host, vcfg_remote_dir(cfg)), name)
    if not os.path.isfile(src):
        return False
    shutil.copy2(src, dest)
    try:
        os.remove(src)
    except OSError:
        pass
    return True


def vcfg_export_client(cfg, host, dest):
    t, cli = vcfg_remote_dir(cfg), client_cli_path(cfg)
    ok, msg = client_script_run(host, cfg, 'vcfg-export.bat', _bat([
        '"%s" config export "%s\\export.json"' % (cli, t), 'exit /b %errorlevel%']))
    if not ok:
        return False, msg
    if not client_fetch(host, cfg, 'export.json', dest):
        return False, 'chạy xong nhưng không thấy file xuất ra (kiểm tra đường dẫn veyon-cli trên máy học sinh ở khối Cài đặt phía dưới)'
    return True, ''


def vcfg_backup_client(cfg, host):
    dest = os.path.join(vcfg_dir(), '%s_%s.json' % (vcfg_safe(host), vcfg_stamp()))
    ok, msg = vcfg_export_client(cfg, host, dest)
    return ok, ('đã lưu ' + os.path.basename(dest)) if ok else msg


def vcfg_restore_client(cfg, host, path):
    t, cli = vcfg_remote_dir(cfg), client_cli_path(cfg)
    ok, msg = client_script_run(host, cfg, 'vcfg-restore.bat', _bat(
        ['"%s" config export "%s\\before-restore.json"' % (cli, t),
         '"%s" config import "%s\\restore.json"' % (cli, t), 'set R=%errorlevel%'] + VCFG_RESTART + ['exit /b %R%']),
        files={'restore.json': path}, timeout=120)
    got = client_fetch(host, cfg, 'before-restore.json',
                       os.path.join(vcfg_dir(), '%s_truoc-khoi-phuc_%s.json' % (vcfg_safe(host), vcfg_stamp())))
    note = ' (đã sao lưu cấu hình cũ của máy)' if got else ''
    try:
        os.remove(os.path.join(unc_target(host, t), 'restore.json'))
    except OSError:
        pass
    return ok, ('đã khôi phục' + note) if ok else '%s%s' % (msg, note)


def vcfg_check_items(items):
    out = []
    for it in items or []:
        k, v = str(it.get('key', '')).strip(), str(it.get('value', ''))
        if not k and not v.strip():
            continue
        if not VCFG_KEY_RE.match(k):
            raise ApiError('Khóa "%s" không hợp lệ, phải dạng Nhóm/Tên (ví dụ Network/PrimaryServicePort)' % k)
        if '"' in v or '\n' in v or '\r' in v:
            raise ApiError('Giá trị của %s không được chứa dấu " hoặc xuống dòng' % k)
        out.append((k, v))
    if not out:
        raise ApiError('Chưa có khóa cấu hình nào để đẩy')
    return out


def vcfg_push_client(cfg, host, items, restart):
    t, cli = vcfg_remote_dir(cfg), client_cli_path(cfg)
    lines = ['chcp 65001 >nul', '"%s" config export "%s\\before-push.json"' % (cli, t), 'set F=0']
    for k, v in items:
        lines.append('"%s" config set "%s" "%s"' % (cli, k, v.replace('%', '%%')))
        lines.append('if errorlevel 1 set F=1')
    if restart:
        lines += VCFG_RESTART
    lines.append('exit /b %F%')
    ok, msg = client_script_run(host, cfg, 'vcfg-push.bat', _bat(lines), timeout=120)
    got = client_fetch(host, cfg, 'before-push.json',
                       os.path.join(vcfg_dir(), '%s_truoc-khi-day_%s.json' % (vcfg_safe(host), vcfg_stamp())))
    note = ' (đã sao lưu cấu hình cũ)' if got else ''
    return ok, ('đã đẩy %d khóa%s%s' % (len(items), ', đã khởi động lại Veyon Service' if restart else '', note)) if ok else (
        'có khóa bị lỗi hoặc không chạy được: %s%s' % (msg, note))


def vcfg_restore_master(cfg, path):
    cli = find_veyon_cli(cfg['veyon_cli'])
    if not os.path.isfile(cli):
        return False, 'Chưa thấy veyon-cli.exe'
    ok, msg = vcfg_export_master(cfg, os.path.join(vcfg_dir(), 'master_truoc-khoi-phuc_%s.json' % vcfg_stamp()))
    if not ok:
        return False, 'Không sao lưu được cấu hình hiện tại nên dừng: ' + msg
    rc, out = run_args([cli, 'config', 'import', path], timeout=60)
    if rc != 0:
        return False, 'veyon-cli config import lỗi (%s): %s' % (rc, out)
    return True, 'Đã khôi phục cấu hình master (cấu hình cũ đã lưu trong veyon-backups). Hãy mở lại Veyon Master.'


AUTO_LOCATION = 'KhoaVeyon'  # tên nhóm tự tạo khi Veyon Master chưa có nhóm nào và ô tên nhóm để trống


def vcfg_netobj_apply(cfg, hosts, location):
    """Thêm máy vào danh sách máy của Veyon Master bằng veyon-cli networkobject. Máy đã có thì bỏ qua."""
    cli = find_veyon_cli(cfg['veyon_cli'])
    if not os.path.isfile(cli):
        return False, 'Chưa thấy veyon-cli.exe'
    rc, out = run_args([cli, 'networkobjects', 'list'], timeout=30)
    raw_list = out if rc == 0 else ''
    existing = raw_list.lower()
    location = (location or '').strip()
    auto_note = ''
    if not location:
        # Tự động: dùng nhóm có sẵn đầu tiên trong Veyon; chưa có nhóm nào thì tự tạo nhóm mặc định.
        found = parse_locations(raw_list)
        if found:
            location = found[0]
            auto_note = ' Tự chọn nhóm có sẵn \"%s\"%s.' % (location, ' (còn %d nhóm khác)' % (len(found) - 1) if len(found) > 1 else '')
        else:
            location = AUTO_LOCATION
            auto_note = ' Chưa có nhóm nào nên tự tạo nhóm \"%s\".' % location
    # Dùng nhóm có sẵn: chỉ tạo nhóm khi tên đó chưa xuất hiện trong danh sách của Veyon.
    # Nếu lệnh tạo nhóm lỗi (vd. nhóm đã có nhưng danh sách in theo định dạng khác) thì vẫn thử thêm máy vào nhóm đó.
    loc_note = ''
    if location and location.lower() not in existing:
        rc, out = run_args([cli, 'networkobjects', 'add', 'location', location], timeout=30)
        if rc != 0:
            loc_note = ' (không tạo được nhóm "%s" nên coi như nhóm đã có sẵn)' % location
    added = skipped = 0
    errs = []
    for h in hosts:
        if re.search(r'(?<![\w.-])%s(?![\w.-])' % re.escape(h.lower()), existing):
            skipped += 1
            continue
        args = [cli, 'networkobjects', 'add', 'computer', h, h, '']
        if location:
            args.append(location)
        rc, out = run_args(args, timeout=30)
        if rc == 0:
            added += 1
        else:
            errs.append('%s (%s) %s' % (h, rc, out))
    msg = 'Đã thêm %d máy, bỏ qua %d máy đã có trong danh sách%s.' % (added, skipped, loc_note)
    if errs:
        return False, msg + auto_note + ' Lỗi: ' + '; '.join(errs[:5])
    return True, msg + auto_note + ' Hãy mở lại Veyon Master để thấy danh sách mới.'


def _op_authkeys(cfg, a):
    from .authkeys import authkeys_prepare_master  # nhập muộn: authkeys dùng lại các hàm của vcfg
    return authkeys_prepare_master(cfg, a.get('name', ''))


ELEV_OPS = {
    'authkeys': lambda cfg, a: _op_authkeys(cfg, a),
    'netobj': lambda cfg, a: vcfg_netobj_apply(cfg, a.get('hosts') or [], a.get('location', '')),
    'restore': lambda cfg, a: vcfg_restore_master(cfg, a['path']),
}


ELEV_JOB = lambda: os.path.join(os.path.dirname(CONFIG_PATH), 'elevated-job.json')  # noqa


def run_elevated_job():
    """Chế độ phụ chạy bằng quyền quản trị: làm một việc trong ELEV_OPS rồi ghi kết quả cho tiến trình chính."""
    try:
        with open(ELEV_JOB(), 'r', encoding='utf-8') as f:
            job = json.load(f)
        ok, msg = ELEV_OPS[job['op']](CFG, job.get('args') or {})
    except Exception as e:  # noqa
        ok, msg = False, 'Lỗi: %s' % e
    with open(SETUP_RESULT(), 'w', encoding='utf-8') as f:
        json.dump({'ok': ok, 'msg': msg}, f, ensure_ascii=False)
    try:
        os.remove(ELEV_JOB())
    except OSError:
        pass


def elevated_op(op, args):
    cfg = json.loads(json.dumps(CFG))
    if is_admin():
        return ELEV_OPS[op](cfg, args)
    with open(ELEV_JOB(), 'w', encoding='utf-8') as f:
        json.dump({'op': op, 'args': args}, f, ensure_ascii=False)
    try:
        os.remove(SETUP_RESULT())
    except OSError:
        pass
    import ctypes
    params = '"%s" --elevated-job' % ENTRY_SCRIPT
    r = ctypes.windll.shell32.ShellExecuteW(None, 'runas', sys.executable, params, APP_DIR, 0)  # noqa
    if r <= 32:
        return False, 'Bạn đã từ chối quyền quản trị (hoặc không mở được UAC)'
    for _ in range(120):
        time.sleep(0.5)
        if os.path.exists(SETUP_RESULT()):
            time.sleep(0.2)
            try:
                with open(SETUP_RESULT(), 'r', encoding='utf-8') as f:
                    d = json.load(f)
                return bool(d.get('ok')), d.get('msg', '')
            except Exception:  # noqa
                continue
    return False, 'Quá thời gian chờ kết quả từ cửa sổ quản trị'


def vcfg_snapshot(cfg, ref, tmpdir):
    """ref: 'master' | 'host:TÊN' (đọc trực tiếp) | tên file trong veyon-backups. Trả về (dict phẳng, lỗi)."""
    if ref == 'master':
        p = os.path.join(tmpdir, 'master.json')
        ok, msg = vcfg_export_master(cfg, p)
    elif ref.startswith('host:'):
        p = os.path.join(tmpdir, vcfg_safe(ref[5:]) + '.json')
        ok, msg = vcfg_export_client(cfg, ref[5:], p)
    else:
        p, ok, msg = vcfg_backup_path(ref), True, ''
    if not ok:
        return None, msg
    try:
        return vcfg_load_file(p), ''
    except Exception as e:  # noqa
        return None, 'Không đọc được %s: %s' % (ref, e)


def vcfg_backup_path(name):
    name = os.path.basename(str(name or ''))
    p = os.path.join(vcfg_dir(), name)
    if not name.lower().endswith('.json') or not os.path.isfile(p):
        raise ApiError('Không thấy file sao lưu "%s"' % name)
    return p


def job_vcfg_backup(hosts, master):
    cfg = json.loads(json.dumps(CFG))
    log('>>> Sao lưu cấu hình Veyon (%s%s)' % ('master' if master else '', (' + ' if master and hosts else '') + ('%d máy học sinh' % len(hosts) if hosts else '')), 'head')
    if master:
        dest = os.path.join(vcfg_dir(), 'master_%s.json' % vcfg_stamp())
        ok, msg = vcfg_export_master(cfg, dest)
        log('[master] %s' % (('OK đã lưu ' + os.path.basename(dest)) if ok else 'LỖI ' + msg), 'ok' if ok else 'err')
    if hosts:
        pool_run(lambda h: vcfg_backup_client(cfg, h), hosts, 'Sao lưu cấu hình Veyon')


def job_vcfg_restore(target, hosts, path):
    cfg = json.loads(json.dumps(CFG))
    log('>>> Khôi phục cấu hình Veyon từ %s' % os.path.basename(path), 'head')
    if target == 'master':
        ok, msg = elevated_op('restore', {'path': path})
        log('[master] %s %s' % ('OK' if ok else 'LỖI', msg), 'ok' if ok else 'err')
    else:
        pool_run(lambda h: vcfg_restore_client(cfg, h, path), hosts, 'Khôi phục cấu hình Veyon')


def job_vcfg_push(hosts, items, restart):
    cfg = json.loads(json.dumps(CFG))
    log('>>> Đẩy %d khóa cấu hình Veyon xuống %d máy' % (len(items), len(hosts)), 'head')
    for k, v in items:
        log('    %s = %s' % (k, v))
    pool_run(lambda h: vcfg_push_client(cfg, h, items, restart), hosts, 'Đẩy cấu hình Veyon')


DETECTED_LOCS = []  # tên nhóm (location) dò được trong Veyon Master


def parse_locations(out):
    """Lấy tên các nhóm từ kết quả `veyon-cli networkobjects list`. Định dạng chưa kiểm chứng nên thử nhiều cách tách cột."""
    names = []
    for line in (out or '').splitlines():
        line = line.strip().strip('{}[]')
        if not line or 'location' not in line.lower():
            continue
        parts = [x.strip().strip('\'"') for x in re.split(r'[;\t|,]', line)]
        low = [x.lower() for x in parts]
        if 'location' not in low:
            continue
        rest = [x for i, x in enumerate(parts) if low[i] != 'location' and x and not re.fullmatch(r'\{?[0-9a-fA-F-]{32,38}\}?', x)]
        if rest and rest[0] not in names:
            names.append(rest[0])
    return names


def job_vcfg_netobj_scan():
    global DETECTED_LOCS
    cfg = json.loads(json.dumps(CFG))
    log('>>> Dò nhóm có sẵn trong Veyon Master', 'head')
    cli = find_veyon_cli(cfg['veyon_cli'])
    if not os.path.isfile(cli):
        log('[master] LỖI Chưa thấy veyon-cli.exe (đặt đường dẫn ở Cài đặt)', 'err')
        return
    rc, out = run_args([cli, 'networkobjects', 'list'], timeout=30)
    if rc != 0:
        log('[master] LỖI networkobjects list (%s): %s' % (rc, out), 'err')
        return
    DETECTED_LOCS = parse_locations(out)
    log('--- kết quả gốc của veyon-cli ---\n%s' % (out or '(trống)'))
    if DETECTED_LOCS:
        log('[master] OK Tìm thấy %d nhóm: %s. Mở lại trang này để chọn trong ô tên nhóm.' % (len(DETECTED_LOCS), ', '.join(DETECTED_LOCS)), 'ok')
    else:
        log('[master] Không nhận ra nhóm nào từ kết quả trên. Gửi kết quả gốc ở trên để chỉnh lại cách đọc, hoặc gõ tay tên nhóm.', 'err')


def job_vcfg_netobj(hosts, location):
    log('>>> Thêm %d máy vào danh sách máy của Veyon Master' % len(hosts), 'head')
    ok, msg = elevated_op('netobj', {'hosts': hosts, 'location': location})
    log('[master] %s %s' % ('OK' if ok else 'LỖI', msg), 'ok' if ok else 'err')


def job_vcfg_compare(a, b):
    cfg = json.loads(json.dumps(CFG))
    log('>>> So sánh cấu hình Veyon: %s  ↔  %s' % (a, b), 'head')
    tmp = tempfile.mkdtemp(prefix='kvcmp')
    try:
        da, ea = vcfg_snapshot(cfg, a, tmp)
        if da is None:
            log('LỖI bên A: ' + ea, 'err')
            return
        db, eb = vcfg_snapshot(cfg, b, tmp)
        if db is None:
            log('LỖI bên B: ' + eb, 'err')
            return
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    rows = vcfg_diff(da, db)
    if not rows:
        log('Giống nhau hoàn toàn (%d khóa).' % len(da), 'ok')
        return
    for sign, k, va, vb in rows[:300]:
        if sign == '~':
            log('  ~ %s:  A = %s   |   B = %s' % (k, _short(va), _short(vb)), 'warn')
        elif sign == '+':
            log('  + %s chỉ có ở B = %s' % (k, _short(vb)), 'ok')
        else:
            log('  - %s chỉ có ở A = %s' % (k, _short(va)), 'err')
    log('--- %d khác biệt%s ---' % (len(rows), ' (chỉ hiện 300 dòng đầu)' if len(rows) > 300 else ''), 'head')


def api_vcfg_info(_q=None):
    with CFG_LOCK:
        cfg = json.loads(json.dumps(CFG))
    files = []
    for f in sorted(os.listdir(vcfg_dir()), reverse=True):
        p = os.path.join(vcfg_dir(), f)
        if f.lower().endswith('.json') and os.path.isfile(p):
            files.append({'name': f, 'size': os.path.getsize(p), 'time': time.strftime('%d/%m %H:%M', time.localtime(os.path.getmtime(p)))})
    return {'backups': files, 'dir': vcfg_dir(), 'push': cfg.get('vcfg_push') or [], 'restart': bool(cfg.get('vcfg_restart', True)),
            'location': cfg.get('netobj_location', ''), 'locations': list(DETECTED_LOCS), 'client_cli': client_cli_path(cfg),
            'presets': [{'key': k, 'value': v, 'desc': d} for k, v, d in VCFG_PRESETS]}


def api_vcfg_save(b):
    with CFG_LOCK:
        push = []
        for it in (b.get('push') or [])[:60]:
            push.append({'key': str(it.get('key', '')).strip(), 'value': str(it.get('value', ''))})
        CFG['vcfg_push'] = push
        CFG['vcfg_restart'] = bool(b.get('restart', True))
        CFG['netobj_location'] = str(b.get('location', '')).strip()
        CFG['client_veyon_cli'] = str(b.get('client_cli', '')).strip() or DEFAULT_CONFIG['client_veyon_cli']
        save_config(CFG)
    return {'ok': True}


def api_vcfg_run(b):
    step = b.get('step')
    hosts = clean_hosts(b.get('hosts'))
    if step in ('backup_master', 'backup_clients', 'backup_all'):
        if step != 'backup_master' and not hosts:
            raise ApiError('Chưa có máy học sinh nào')
        start_job(job_vcfg_backup, hosts if step != 'backup_master' else [], step != 'backup_clients')
    elif step == 'compare':
        a, c = str(b.get('a', '')), str(b.get('b', ''))
        if not a or not c or a == c:
            raise ApiError('Hãy chọn hai bên khác nhau để so sánh')
        for ref in (a, c):
            if ref != 'master' and not ref.startswith('host:'):
                vcfg_backup_path(ref)
        start_job(job_vcfg_compare, a, c)
    elif step in ('restore_master', 'restore_clients'):
        path = vcfg_backup_path(b.get('file'))
        if step == 'restore_clients' and not hosts:
            raise ApiError('Chưa có máy học sinh nào')
        start_job(job_vcfg_restore, 'master' if step == 'restore_master' else 'clients', hosts, path)
    elif step == 'push':
        if not hosts:
            raise ApiError('Chưa có máy học sinh nào')
        items = vcfg_check_items(b.get('push'))
        start_job(job_vcfg_push, hosts, items, bool(b.get('restart', True)))
    elif step == 'netobj_scan':
        start_job(job_vcfg_netobj_scan)
    elif step == 'netobj':
        if not hosts:
            raise ApiError('Chưa có máy học sinh nào')
        start_job(job_vcfg_netobj, hosts, str(b.get('location', '')).strip())
    else:
        raise ApiError('Bước "%s" không hợp lệ. Nếu vừa chép file mới, hãy tắt KhoaVeyon (Task Manager, pythonw.exe) rồi chạy lại Chay-KhoaVeyon.bat.' % step)
    return {'ok': True}
