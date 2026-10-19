# -*- coding: utf-8 -*-
"""Giám sát vi phạm trên máy học sinh: script KhoaVeyonWatch, bật, tắt, tự chạy khi đăng nhập, lấy ảnh."""

import json
import os
import shutil
import tempfile
import time

from .alerts import alert_collect_host, watch_hosts_set
from .announce import seat_notice_one
from .evidence import evidence_root, watch_num, WATCH_REMOTE_DIR
from .network import tcp_open
from .paths import load_script
from .remote import distribute_to_host, remote_run, run_args, unc_target
from .runtime import ApiError, CFG, CFG_LOCK, clean_hosts, log, pool_run, start_job
from .screenshot import _q
from .vcfg import vcfg_remote_dir, vcfg_safe


WATCH_PS1_NAME = 'KhoaVeyonWatch.ps1'
WATCH_TASK = 'KhoaVeyonWatch'
WATCH_PS1 = load_script('KhoaVeyonWatch.ps1')


def watch_start_one(cfg, host):
    rdir = vcfg_remote_dir(cfg)
    tmp = tempfile.mkdtemp(prefix='kvwatch')
    try:
        sp = os.path.join(tmp, WATCH_PS1_NAME)
        with open(sp, 'w', encoding='utf-8-sig', newline='') as f:
            f.write(WATCH_PS1.replace('\r\n', '\n').replace('\n', '\r\n'))
        distribute_to_host(host, [sp], rdir)
    except Exception as e:  # noqa
        return False, 'không chép được script giám sát: %s' % e
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    ev = unc_target(host, WATCH_REMOTE_DIR)
    try:
        os.makedirs(ev, exist_ok=True)
        os.remove(os.path.join(ev, 'stop.flag'))
    except OSError:
        pass
    ps_args = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File %s -ListDir %s -Out %s -RepeatSec %d -MaxShots %d -NotifyStudent %d' % (
        _q(rdir + '\\' + WATCH_PS1_NAME), _q(cfg['dist_target'].rstrip('\\/')), _q(WATCH_REMOTE_DIR),
        watch_num(cfg, 'watch_repeat', 10, 3, 300), watch_num(cfg, 'watch_max', 5, 1, 50),
        1 if cfg.get('watch_notify_student', True) else 0)
    rc, out = remote_run(host, 'powershell.exe ' + ps_args, interactive=True, name=WATCH_TASK)
    if rc != 0:
        return False, out
    watch_hosts_set(host, True)  # từ giờ máy giáo viên tự nhận ảnh và báo động
    msg = 'đã bật giám sát, ảnh vi phạm sẽ tự gửi về máy này'
    if cfg.get('watch_autostart', True):
        ok, why = watch_autostart_install(host, ps_args)
        msg += '; tự chạy lại khi học sinh đăng nhập' if ok else '; CHƯA cài được tác vụ tự chạy lại (%s)' % why[:160]
    else:
        watch_autostart_remove(host)
    return True, msg


WATCH_LOGON_TASK = 'KhoaVeyonWatchLogon'
GUARD_FILE = 'kvguard.txt'   # vcfg\kvguard.txt: mỗi dòng là một lệnh dịch vụ KhoaVeyonAutoLog giữ chạy trong phiên học sinh


def guard_unc(cfg, host):
    return os.path.join(unc_target(host, vcfg_remote_dir(cfg)), GUARD_FILE)


def watch_autostart_install(host, ps_args):
    """Tự chạy lại giám sát: ghi lệnh vào vcfg\\kvguard.txt. Dịch vụ KhoaVeyonAutoLog (chạy bằng SYSTEM) sẽ chạy
    lệnh này trong phiên học sinh khi đăng nhập VÀ bật lại trong ~30 giây nếu học sinh tắt bằng Task Manager.
    Không dùng Task Scheduler nữa; gỡ luôn tác vụ cũ KhoaVeyonWatchLogon nếu còn."""
    with CFG_LOCK:
        cfg = json.loads(json.dumps(CFG))
    line = 'powershell.exe ' + ps_args
    try:
        gp = guard_unc(cfg, host)
        os.makedirs(os.path.dirname(gp), exist_ok=True)
        with open(gp, 'w', encoding='utf-8', newline='') as f:  # chỉ một guard: ghi đè
            f.write(line + '\r\n')
    except OSError as e:
        return False, 'không ghi được %s: %s' % (GUARD_FILE, e)
    run_args(['schtasks', '/Delete', '/S', host, '/TN', WATCH_LOGON_TASK, '/F'])  # dọn tác vụ cũ, bỏ qua lỗi
    return True, ''


def watch_autostart_remove(host):
    with CFG_LOCK:
        cfg = json.loads(json.dumps(CFG))
    ok = True
    try:
        gp = guard_unc(cfg, host)
        if os.path.exists(gp):
            os.remove(gp)
    except OSError as e:
        if tcp_open(host, 445, 1.5):   # máy bật mà vẫn không xóa được: báo lỗi
            return False, 'không xóa được %s: %s' % (GUARD_FILE, e)
        ok = False
    run_args(['schtasks', '/Delete', '/S', host, '/TN', WATCH_LOGON_TASK, '/F'])  # dọn tác vụ cũ nếu còn
    if ok:
        return True, ''
    return False, 'máy đang tắt nên chưa gỡ được tự-chạy-lại; bấm Tắt giám sát lại khi máy bật'


def watch_stop_one(cfg, host):
    ev = unc_target(host, WATCH_REMOTE_DIR)
    os.makedirs(ev, exist_ok=True)
    with open(os.path.join(ev, 'stop.flag'), 'w') as f:
        f.write('stop')
    try:
        alert_collect_host(cfg, host)  # nhận nốt ảnh còn lại
    except Exception:  # noqa
        pass
    watch_hosts_set(host, False)
    ok, why = watch_autostart_remove(host)  # gỡ tác vụ tự chạy lại, nếu không máy khởi động lại sẽ bật giám sát lại
    if not ok:
        return False, 'đã gửi lệnh dừng nhưng CHƯA gỡ được tác vụ tự chạy lại (%s). Bấm Tắt giám sát lại khi máy có mạng.' % why[:160]
    return True, 'đã gửi lệnh dừng (dừng sau vài giây)'


def watch_fetch_one(cfg, host):
    ok, msg, n = alert_collect_host(cfg, host)
    if not ok:
        return False, msg
    src = unc_target(host, WATCH_REMOTE_DIR)
    dest = os.path.join(evidence_root(), vcfg_safe(host))
    try:  # nhật ký chạy của script giám sát, để xem khi cần tìm lỗi
        os.makedirs(dest, exist_ok=True)
        shutil.copy2(os.path.join(src, 'watch.log'), os.path.join(dest, 'watch.log'))
    except OSError:
        pass
    return True, 'đã lấy %d ảnh vi phạm mới về %s' % (n, dest) if n else 'chưa có ảnh vi phạm mới'


def job_watch(step, hosts):
    with CFG_LOCK:
        cfg = json.loads(json.dumps(CFG))
    fn = {'start': watch_start_one, 'stop': watch_stop_one, 'fetch': watch_fetch_one}[step]
    log('>>> %s giám sát vi phạm (%d máy)' % ({'start': 'Bật', 'stop': 'Tắt', 'fetch': 'Lấy ảnh'}[step], len(hosts)), 'head')
    pool_run(lambda h: fn(cfg, h), hosts, 'Giám sát vi phạm')
    if step in ('start', 'stop') and cfg.get('watch_disclose', True):
        job_watch_disclose(cfg, step, hosts)


def disclose_payload(clear=False):
    """Nhãn nhỏ ở góc màn hình học sinh: công khai máy đang được giám sát (dùng chung khung với nhãn chỗ ngồi)."""
    if clear:
        return {'stamp': '%.3f' % time.time(), 'clear': True}
    return {'stamp': '%.3f' % time.time(), 'title': 'KHOAVEYON', 'name': 'ĐANG GIÁM SÁT', 'detail': 'Ảnh vi phạm gửi về máy giáo viên',
            'seconds': 8, 'keep': True, 'clear': False}


def job_watch_disclose(cfg, step, hosts):
    """Bật giám sát thì hiện nhãn “Đang giám sát”, tắt thì gỡ nhãn. Máy không có ai đăng nhập chỉ báo lỗi ở Nhật ký, không ảnh hưởng giám sát."""
    pl = disclose_payload(clear=(step == 'stop'))
    pool_run(lambda h: seat_notice_one(cfg, h, pl), hosts, 'Nhãn đang giám sát' if step == 'start' else 'Gỡ nhãn giám sát')


def api_watch(b):
    step = b.get('step')
    hosts = clean_hosts(b.get('hosts'))
    if step not in ('start', 'stop', 'fetch'):
        raise ApiError('Bước không hợp lệ')
    if not hosts:
        raise ApiError('Chưa có máy nào')
    start_job(job_watch, step, hosts)
    return {'ok': True}
