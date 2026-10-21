# -*- coding: utf-8 -*-
"""Sức khỏe từng máy học sinh: gom trạng thái đọc được thành đèn xanh, vàng, đỏ và cách sửa bằng một nút."""

import hashlib
import json
import ntpath
import os
import time

from .evidence import WATCH_REMOTE_DIR
from .exam import EXAM, EXAM_LOCK
from .jobs import job_action
from .remote import distribute_to_host, remote_install, rfs_mtime, rfs_sha
from .runtime import ApiError, CFG, CFG_LOCK, clean_hosts, log, PAYLOAD_DIR, pool_run, split_host_port, start_job
from .watch import job_watch


AGENT_GRACE = 90     # giây sau khi máy bật chưa thấy Agent thì mới báo mất Agent (Agent cần vài chục giây để khởi động)
DISK_WARN = 10       # % ổ đĩa trống: dưới mức này thì báo
BAT_WARN = 15        # % pin
SKEW_WARN = 120      # giây: lệch giờ quá mức này thì báo vàng
ALIVE_MAX_AGE = 45   # giây: script giám sát ghi alive.txt mỗi 10 giây


def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def payload_script_path():
    with CFG_LOCK:
        name = os.path.basename((CFG.get('script_path') or '').replace('\\', '/')) or 'KhoaVeyonServices.bat'
    return os.path.join(PAYLOAD_DIR, name), name


def health_probe(host):
    """Đọc từ xa (Agent hoặc \\\\máy\\C$): giám sát còn chạy không (alive.txt), bản KhoaVeyonServices.bat so với bản trong payload."""
    hh, _ = split_host_port(host)
    out = {'watch_alive': None, 'svc': '?'}
    try:
        with CFG_LOCK:
            sp = CFG.get('script_path') or r'C:\cmd\KhoaVeyonServices.bat'
        local, _n = payload_script_path()
        try:
            remote_sha = rfs_sha(hh, sp)
            out['svc'] = ('ok' if remote_sha == _sha(local) else 'old') if os.path.isfile(local) else '?'
        except FileNotFoundError:
            out['svc'] = 'none'
        try:
            out['watch_alive'] = time.time() - rfs_mtime(hh, ntpath.join(WATCH_REMOTE_DIR, 'alive.txt')) <= ALIVE_MAX_AGE
        except OSError:
            out['watch_alive'] = False
    except (OSError, ValueError):
        pass
    return out


def health_of(r, exam=None):
    """r: một dòng trạng thái (online, veyon, smb, svc, watch_alive, ai, watching...). Trả về (mức, [vấn đề]).
    mức: off (máy tắt), red, yellow, green. Mỗi vấn đề: {'text', 'fix'} (fix rỗng nếu phải làm tay)."""
    if not r.get('online'):
        return 'off', []
    probs = []
    if not r.get('veyon'):
        probs.append({'text': 'Veyon Service chưa chạy hoặc chưa cài', 'fix': '', 'sev': 'red'})
    agent_prob = False
    if 'agent' in r and not r.get('agent'):
        rej = r.get('reject') or {}
        if rej.get('reason') == 'bad time':
            mins = int(abs(rej.get('skew') or 0) // 60)
            probs.append({'id': 'clock', 'text': 'Đồng hồ máy lệch khoảng %s nên Agent bị từ chối (pin CMOS yếu?). Dịch vụ bản mới tự chỉnh giờ, bản cũ thì chỉnh tay' % (('%d phút' % mins) if mins < 120 else ('%.1f giờ' % (mins / 60.0))), 'fix': '', 'sev': 'red'})
            agent_prob = True
        elif rej.get('reason') == 'bad signature':
            probs.append({'id': 'badkey', 'text': 'Agent trên máy gọi về nhưng sai khóa: chạy lại Setup-MayHocSinh.bat mới', 'fix': '', 'sev': 'red'})
            agent_prob = True
        elif r.get('veyon') and r.get('up_for', 999) > AGENT_GRACE:
            probs.append({'id': 'noagent', 'text': 'Agent chưa kết nối về máy giáo viên (chưa cài, dịch vụ dừng, hoặc tường lửa máy giáo viên chặn cổng Agent)', 'fix': '', 'sev': 'red'})
            agent_prob = True
    elif r.get('skew') is not None and abs(r['skew']) > SKEW_WARN:
        probs.append({'id': 'clock', 'text': 'Giờ máy lệch %d giây so với máy giáo viên' % abs(r['skew']), 'fix': 'time', 'sev': 'yellow'})
    if agent_prob:
        pass
    elif not r.get('smb'):
        probs.append({'text': 'Chưa cài Agent / chưa mở chia sẻ C$ (chạy Setup-MayHocSinh.bat một lần)', 'fix': '', 'sev': 'red'})
    elif r.get('svc') == 'none':
        probs.append({'text': 'Chưa cài dịch vụ KhoaVeyon', 'fix': 'svc', 'sev': 'red'})
    elif r.get('svc') == 'old':
        probs.append({'text': 'Dịch vụ KhoaVeyon là bản cũ', 'fix': 'svc', 'sev': 'yellow'})
    ah = r.get('ahealth') or {}   # báo cáo sức khỏe do dịch vụ trên máy học sinh gửi kèm
    if isinstance(ah.get('disk'), int) and ah['disk'] <= DISK_WARN:
        probs.append({'id': 'disk', 'text': 'Ổ đĩa hệ thống sắp đầy: còn %d%% (%s GB)' % (ah['disk'], ah.get('diskgb', '?')), 'fix': '', 'sev': 'red' if ah['disk'] <= 5 else 'yellow'})
    if isinstance(ah.get('bat'), int) and 0 <= ah['bat'] <= BAT_WARN and ah.get('ac') is False:
        probs.append({'id': 'battery', 'text': 'Pin còn %d%% và chưa cắm sạc' % ah['bat'], 'fix': '', 'sev': 'yellow'})
    exam = exam or {}
    steps = exam.get('steps') or {}
    if r.get('smb') and r.get('watching') and r.get('watch_alive') is False:
        probs.append({'text': 'Giám sát đã bật nhưng không chạy trên máy này', 'fix': 'watch', 'sev': 'red'})
    elif exam.get('active') and steps.get('watch') and not r.get('watching'):
        probs.append({'text': 'Đang thi nhưng máy này chưa được giám sát', 'fix': 'watch', 'sev': 'red'})
    if exam.get('active') and steps.get('blockai') and r.get('ai') in ('open', 'half'):
        probs.append({'text': 'Đang thi nhưng chưa khóa AI', 'fix': 'blockai', 'sev': 'red'})
    level = 'red' if any(p['sev'] == 'red' for p in probs) else ('yellow' if probs else 'green')
    return level, probs


def exam_snapshot():
    with EXAM_LOCK:
        return {'active': EXAM['active'], 'steps': dict(EXAM['steps'])}


def job_fix_service(hosts):
    with CFG_LOCK:
        cfg = json.loads(json.dumps(CFG))
    src, name = payload_script_path()
    if not os.path.isfile(src):
        log('Chưa có %s trong thư mục payload nên chưa cài được dịch vụ. Bấm “Thiết lập máy giáo viên” ở trang Thiết lập ban đầu.' % name, 'err')
        return
    log('>>> Cài lại dịch vụ KhoaVeyon (%d máy)' % len(hosts), 'head')

    def one(h):
        try:
            distribute_to_host(h, [src], cfg['dist_target'])
        except Exception as e:  # noqa
            return False, 'không chép được %s: %s' % (name, e)
        ok, msg = remote_install(h, cfg['script_path'])
        return ok, 'đã cài lại dịch vụ' if ok else '-install lỗi: ' + msg
    pool_run(one, hosts, 'Cài lại dịch vụ KhoaVeyon')


TIME_FIX_CMD = ('cmd.exe /c tzutil /s "SE Asia Standard Time" & sc config w32time start= auto & net start w32time & '
                'w32tm /config /manualpeerlist:"time.windows.com,0x9 time.google.com,0x9 pool.ntp.org,0x9" /syncfromflags:manual /reliable:no /update & '
                'w32tm /resync /force')


def job_fix_time(hosts):
    from .remote import remote_run_wait
    log('>>> Đồng bộ giờ %d máy (múi giờ Việt Nam)' % len(hosts), 'head')
    for h in hosts:
        ok, msg = remote_run_wait(h, TIME_FIX_CMD, timeout=60)
        log('[%s] %s' % (h, 'đã đồng bộ giờ' if ok else 'chưa đồng bộ được: ' + msg), 'ok' if ok else 'err')


def job_fix(fix, hosts):
    try:
        if fix == 'time':
            job_fix_time(hosts)
        elif fix == 'svc':
            job_fix_service(hosts)
        elif fix == 'watch':
            job_watch('start', hosts)
        elif fix == 'blockai':
            job_action('blockai', hosts)
    finally:
        from .status import STATUS, STATUS_EVENT, STATUS_LOCK
        with STATUS_LOCK:
            for h in hosts:
                if h in STATUS:
                    STATUS[h]['deep'] = 0
        STATUS_EVENT.set()


def api_health_fix(b):
    fix = b.get('fix')
    if fix not in ('svc', 'watch', 'blockai', 'time'):
        raise ApiError('Cách sửa không hợp lệ')
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào để sửa')
    start_job(job_fix, fix, hosts)
    return {'ok': True}
