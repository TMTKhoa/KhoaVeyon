# -*- coding: utf-8 -*-
"""Tự kiểm tra một máy học sinh (A4).

Chạy lần lượt các chức năng chính trên MỘT máy thử, sau mỗi bước đọc trạng thái thật rồi báo ✔ đạt / ✘ chưa đạt /
▪ chưa kiểm được. Mỗi bước bật hạn chế đều tự gỡ lại ngay sau khi kiểm tra, để máy thử về trạng thái cũ.

Rất hợp để thử nhanh trên phòng máy thật (phần lớn tính năng chưa chạy trên Windows thật) rồi gửi lại đúng dòng
lỗi cho tác giả. Trả về danh sách bước, cũng ghi từng dòng vào Nhật ký."""

import json
import time

from .ai import ai_state_one
from .health import health_probe
from .network import tcp_open
from .remote import run_shell, veyon_command
from .runtime import ApiError, CFG, CFG_LOCK, clean_hosts, log, split_host_port, start_job
from .verify import compare, read_remote_state
from .watch import watch_start_one, watch_stop_one


def _apply(cfg, host, key):
    """Gửi một lệnh Veyon (mục 'features') xuống máy, đồng bộ. Trả về (ok, mô tả)."""
    from .actions import ACTION_BY_KEY
    feature = cfg['features'].get(key) or ACTION_BY_KEY[key][3]
    try:
        cmd = veyon_command(cfg, host, feature)
    except Exception as e:  # noqa
        return False, 'lỗi mẫu lệnh: %s' % e
    rc, out = run_shell(cmd, timeout=30)
    return rc == 0, out


def _state(cfg, host):
    st, err = read_remote_state(cfg, host)
    return st, err


def _one_restrict(cfg, host, on_key, off_key, cat):
    """Bật một hạn chế, đọc trạng thái thật để xem có hiệu lực không, rồi gỡ lại. Trả về (status, mô tả)."""
    ok, out = _apply(cfg, host, on_key)
    if not ok:
        return 'bad', 'gửi lệnh lỗi: %s' % (out or '')[:120]
    time.sleep(2)
    try:
        if cat == 'ai':
            ai = ai_state_one(host)
            res = compare({'ai': {'key': on_key, 'on': True}}, {'users': []}, ai)
        else:
            st, err = _state(cfg, host)
            if st is None:
                return 'unknown', 'không đọc được trạng thái thật: %s' % err
            res = compare({cat: {'key': on_key, 'on': True}}, st, None)
        status, detail = res[0][1], res[0][2]
    finally:
        _apply(cfg, host, off_key)   # luôn gỡ lại
    return status, detail


STEP_ICON = {'ok': '✔', 'bad': '✘', 'unknown': '▪', 'skip': '–'}


def selftest_run(host):
    with CFG_LOCK:
        cfg = json.loads(json.dumps(CFG))
    steps = []

    def add(name, status, detail=''):
        steps.append({'name': name, 'status': status, 'detail': detail})
        log('    %s %s%s' % (STEP_ICON.get(status, '?'), name, '  →  ' + detail if detail else ''),
            {'ok': 'ok', 'bad': 'err', 'unknown': 'warn', 'skip': 'muted'}.get(status, ''))

    log('>>> Tự kiểm tra máy %s' % host, 'head')
    hh, pp = split_host_port(host)
    if not tcp_open(hh, pp, 2):
        add('Máy trả lời (Veyon cổng %d)' % pp, 'bad', 'máy không trả lời: đang tắt, sai tên máy, hoặc Veyon chưa chạy')
        return {'host': host, 'steps': steps, 'done': False}
    add('Máy trả lời (Veyon cổng %d)' % pp, 'ok')

    # 1) Dịch vụ KhoaVeyon và bản mới
    h = health_probe(host)
    svc = h.get('svc')
    add('Dịch vụ KhoaVeyon (-install)',
        'ok' if svc == 'ok' else ('unknown' if svc in (None, '?') else 'bad'),
        {'ok': 'đã cài, đúng bản mới', 'old': 'đang là bản cũ, bấm Thiết lập để cài lại',
         'none': 'chưa cài dịch vụ'}.get(svc, 'chưa đọc được'))

    # 2..4) các hạn chế đọc được trạng thái thật
    for name, on, off, cat in [
            ('Chặn internet (tường lửa)', 'blockall', 'allowall', 'net'),
            ('Khóa Task Manager', 'lockdown', 'unlock', 'lockdown'),
            ('Khóa công cụ AI', 'blockai', 'allowai', 'ai')]:
        try:
            status, detail = _one_restrict(cfg, host, on, off, cat)
        except Exception as e:  # noqa
            status, detail = 'bad', 'lỗi: %s' % e
        add(name, status, detail)

    # 5) Giám sát vi phạm: bật rồi xem có tín hiệu "đang chạy" (alive) không, rồi tắt
    try:
        ok, msg = watch_start_one(cfg, host)
        if not ok:
            add('Giám sát vi phạm', 'bad', 'không bật được: %s' % msg[:120])
        else:
            time.sleep(12)
            hp = health_probe(host)
            alive = hp.get('watch_alive')
            add('Giám sát vi phạm', 'ok' if alive else 'bad',
                'đang chạy và gửi tín hiệu' if alive else 'đã bật nhưng chưa thấy tín hiệu (xem watch.log)')
            watch_stop_one(cfg, host)
    except Exception as e:  # noqa
        add('Giám sát vi phạm', 'bad', 'lỗi: %s' % e)

    # 6) Chụp màn hình một máy
    try:
        import tempfile
        from .screenshot import shot_one
        d = tempfile.mkdtemp(prefix='kvselftest')
        ok, msg = shot_one(cfg, host, d)
        add('Chụp màn hình', 'ok' if ok else 'bad', '' if ok else (msg or '')[:120])
    except Exception as e:  # noqa
        add('Chụp màn hình', 'unknown', 'không thử được: %s' % e)

    # 7) Thông báo "Máy này của ai" (chỉ kiểm tra gửi được lệnh hiển thị)
    try:
        from .announce import seat_notice_one
        pl = {'stamp': '%.3f' % time.time(), 'title': 'KHOAVEYON', 'name': 'KIỂM TRA HIỂN THỊ',
              'detail': 'Tự kiểm tra – có thể bỏ qua', 'seconds': 5, 'keep': False, 'clear': False}
        ok, msg = seat_notice_one(cfg, host, pl)
        add('Thông báo lên màn hình học sinh', 'ok' if ok else 'bad', '' if ok else (msg or '')[:120])
    except Exception as e:  # noqa
        add('Thông báo lên màn hình học sinh', 'unknown', 'không thử được: %s' % e)

    good = sum(1 for s in steps if s['status'] == 'ok')
    log('Tự kiểm tra xong: %d/%d bước đạt' % (good, len(steps)), 'head')
    return {'host': host, 'steps': steps, 'done': True, 'ok': good, 'total': len(steps)}


SELFTEST_RESULT = {'data': None}


def job_selftest(host):
    try:
        SELFTEST_RESULT['data'] = selftest_run(host)
    except Exception as e:  # noqa
        log('Tự kiểm tra lỗi: %s' % e, 'err')
        SELFTEST_RESULT['data'] = {'host': host, 'steps': [], 'done': False, 'error': str(e)}


def api_selftest(b):
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chọn đúng một máy để tự kiểm tra')
    if len(hosts) > 1:
        raise ApiError('Chỉ tự kiểm tra một máy mỗi lần (chọn một máy)')
    SELFTEST_RESULT['data'] = None
    start_job(job_selftest, hosts[0])
    return {'ok': True}


def api_selftest_result(_q=None):
    return {'result': SELFTEST_RESULT['data']}
