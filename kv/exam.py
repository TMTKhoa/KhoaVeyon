# -*- coding: utf-8 -*-
"""Chế độ thi một nút: gom các bước (chụp ảnh, khóa AI, chỉ trang cho phép, giám sát, nhãn chỗ ngồi) thành bật/tắt một lần."""

import json
import os
import threading
import time

from .announce import job_announce
from .examlock import collect_paths_clean, DEFAULT_COLLECT_PATHS, job_exam_collect, job_exam_lock
from .jobs import job_action
from .khoalink import clean_exam_url, job_kq_allow, job_kq_open
from .network import tcp_open
from .paths import CONFIG_PATH
from .runtime import ApiError, clean_hosts, log, split_host_port, start_job
from .school import _cls_norm, SCHOOL, SCHOOL_LOCK
from .screenshot import job_shot
from .verify import job_verify
from .watch import job_watch


EXAM_FILE = os.path.join(os.path.dirname(CONFIG_PATH), 'exam.json')
EXAM_LOCK = threading.RLock()
# thứ tự chạy khi bật; khi tắt chạy ngược lại phần có bật
EXAM_STEPS = [
    ('shot', 'Chụp màn hình cả lớp trước khi khóa'),
    ('blockai', 'Khóa toàn bộ công cụ AI (đóng trình duyệt đang mở)'),
    ('allowpage', 'Chỉ cho vào các trang được phép bằng TƯỜNG LỬA (chặn theo IP; không gồm miền con)'),
    ('webonly', 'Chỉ cho vào các trang được phép bằng CHÍNH SÁCH TRÌNH DUYỆT (gồm miền con và request Firebase/MongoDB; nên dùng cho KhoaQuiz)'),
    ('lockdown', 'Khóa Task Manager và Settings'),
    ('usb', 'Khóa ổ USB và thẻ nhớ (tự mở lại khi kết thúc thi)'),
    ('print', 'Chặn in ấn: tắt Print Spooler (tự bật lại khi kết thúc thi)'),
    ('clip', 'Chặn sao chép-dán: xóa clipboard liên tục (mất khi máy khởi động lại)'),
    ('watch', 'Bật giám sát vi phạm (tự chụp ảnh, báo động)'),
    ('announce', 'Hiện nhãn "Máy này của ai" trên từng máy'),
    ('kq', 'Mở bài kiểm tra KhoaQuiz trên từng máy (link ở bên dưới; tự thêm KhoaQuiz vào trang được phép, gắn số máy để đối chiếu tên)'),
    ('verify', 'Kiểm tra lại hiệu lực các hạn chế sau khi bật, báo máy nào chưa khóa'),
    ('collect', 'Khi kết thúc thi: thu file bài làm mới sửa về máy giáo viên (thư mục ở bên dưới)'),
]
EXAM_DEFAULT_STEPS = {'shot': True, 'blockai': True, 'allowpage': True, 'webonly': False, 'lockdown': False, 'usb': False, 'print': False, 'clip': False,
                      'watch': True, 'announce': True, 'kq': False, 'verify': True, 'collect': False}
EXAM_VERIFY_DELAY = 6      # giây đợi cho các hạn chế kịp có hiệu lực (kiosk, chính sách) rồi mới kiểm tra
EXAM_COLLECT_MARGIN = 300  # thu cả file sửa sớm hơn giờ bấm bắt đầu thi chừng này giây
EXAM = {'active': False, 'since': 0.0, 'end_at': 0.0, 'cls': '', 'hosts': [], 'steps': dict(EXAM_DEFAULT_STEPS), 'busy': '', 'stop_watch': True,
        'last': '', 'collect_paths': list(DEFAULT_COLLECT_PATHS), 'collected': '', 'kq_url': ''}


def exam_save():
    with EXAM_LOCK:
        snap = {k: EXAM[k] for k in ('active', 'since', 'end_at', 'cls', 'hosts', 'steps', 'stop_watch', 'last', 'collect_paths', 'collected', 'kq_url')}
    try:
        with open(EXAM_FILE, 'w', encoding='utf-8') as f:
            json.dump(snap, f, ensure_ascii=False)
    except OSError:
        pass


def exam_load():
    try:
        with open(EXAM_FILE, 'r', encoding='utf-8') as f:
            d = json.load(f)
    except (OSError, ValueError):
        return
    with EXAM_LOCK:
        if isinstance(d, dict):
            for k in ('active', 'since', 'end_at', 'cls', 'hosts', 'stop_watch', 'last', 'collect_paths', 'collected', 'kq_url'):
                if k in d:
                    EXAM[k] = d[k]
            if isinstance(d.get('steps'), dict):
                EXAM['steps'] = {k: bool(d['steps'].get(k, v)) for k, v in EXAM_DEFAULT_STEPS.items()}


def _online(hosts, what):
    on = [h for h in hosts if tcp_open(*split_host_port(h), 1.5)]
    off = [h for h in hosts if h not in on]
    if off:
        log('Chế độ thi (%s): %d máy đang tắt hoặc không trả lời, bỏ qua: %s' % (what, len(off), ', '.join(off)), 'warn')
    return on


def job_exam_start(hosts, steps, cls, kq_url=''):
    with EXAM_LOCK:
        EXAM['busy'] = 'start'
    try:
        log('=== BẬT CHẾ ĐỘ THI (%d máy) ===' % len(hosts), 'head')
        on = _online(hosts, 'bật')
        if not on:
            log('Chế độ thi: không có máy nào đang bật, chưa làm gì (chế độ thi không được bật)', 'err')
            with EXAM_LOCK:
                EXAM['active'] = False
            return
        if steps.get('shot'):
            job_shot(on, 'Chụp màn hình trước khi thi')
        if steps.get('blockai'):
            job_action('blockai', on)
        if steps.get('kq') and kq_url and (steps.get('allowpage') or steps.get('webonly')):
            try:
                job_kq_allow(on, kq_url)
            except Exception as e:  # noqa
                log('Chế độ thi: không thêm được KhoaQuiz vào AllowPage.xlsx: %s' % e, 'err')
        if steps.get('allowpage'):
            job_action('allowpage', on)
        if steps.get('webonly'):
            job_action('webonly', on)
        if steps.get('lockdown'):
            job_action('lockdown', on)
        locks = [w for w in ('usb', 'print', 'clip') if steps.get(w)]
        if locks:
            job_exam_lock('on', locks, on)
        if steps.get('watch'):
            job_watch('start', on)
        if steps.get('announce'):
            if cls:
                job_announce(cls, [], 20, True, False)
            else:
                log('Chế độ thi: chưa chọn lớp nên không hiện nhãn chỗ ngồi', 'warn')
        if steps.get('kq'):
            if kq_url:
                job_kq_open(on, kq_url)
            else:
                log('Chế độ thi: chưa có link bài kiểm tra KhoaQuiz nên không mở', 'warn')
        if steps.get('verify'):
            time.sleep(EXAM_VERIFY_DELAY)
            job_verify(on, False)
        with EXAM_LOCK:
            EXAM['last'] = time.strftime('%Y-%m-%d %H:%M:%S')
        log('=== xong bật chế độ thi ===', 'head')
    finally:
        with EXAM_LOCK:
            EXAM['busy'] = ''
        exam_save()


def job_exam_end(hosts, steps, cls, stop_watch, paths=None, since=0.0):
    with EXAM_LOCK:
        EXAM['busy'] = 'end'
    try:
        log('=== TẮT CHẾ ĐỘ THI (%d máy) ===' % len(hosts), 'head')
        on = _online(hosts, 'tắt')
        if not on:
            log('Chế độ thi: không có máy nào đang bật. Chế độ đã được tắt trên máy giáo viên; máy tắt sẽ còn bị hạn chế đến khi bấm mở khóa thủ công '
                '(khóa USB và chặn in còn nguyên sau khi khởi động lại: dùng nút “Gỡ khóa USB / in / sao chép-dán” ở trang Chế độ thi khi máy bật).', 'warn')
            return
        if steps.get('collect') and paths:
            dest = job_exam_collect(on, paths, max(0.0, since - EXAM_COLLECT_MARGIN))
            with EXAM_LOCK:
                EXAM['collected'] = dest
        if steps.get('announce'):
            job_announce(cls or '', [], 3, False, True)
        if steps.get('watch') and stop_watch:
            job_watch('stop', on)
        if steps.get('allowpage'):
            job_action('allowall', on)
        if steps.get('webonly'):
            job_action('weboff', on)
        if steps.get('lockdown'):
            job_action('unlock', on)
        if steps.get('blockai'):
            job_action('allowai', on)
        locks = [w for w in ('usb', 'print', 'clip') if steps.get(w)]
        if locks:
            job_exam_lock('off', locks, on)
        log('=== xong tắt chế độ thi ===', 'head')
    finally:
        with EXAM_LOCK:
            EXAM['busy'] = ''
        exam_save()


def exam_view():
    with EXAM_LOCK:
        d = {k: EXAM[k] for k in ('active', 'since', 'end_at', 'cls', 'hosts', 'steps', 'busy', 'stop_watch', 'last', 'collect_paths', 'collected', 'kq_url')}
    with SCHOOL_LOCK:
        d['classes'] = sorted(SCHOOL['classes'])
    d['all_steps'] = [{'key': k, 'label': l} for k, l in EXAM_STEPS]
    d['now'] = time.time()
    return d


def api_exam(_q=None):
    return exam_view()


def _clean_steps(raw):
    raw = raw if isinstance(raw, dict) else {}
    return {k: bool(raw.get(k, v)) for k, v in EXAM_DEFAULT_STEPS.items()}


def api_exam_start(b):
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào để bật chế độ thi')
    with EXAM_LOCK:
        if EXAM['busy']:
            raise ApiError('Đang chạy bước khác, hãy đợi xong')
        if EXAM['active']:
            raise ApiError('Chế độ thi đang bật')
        steps = _clean_steps(b.get('steps'))
        cls = ''
        if b.get('cls'):
            cls = _cls_norm(b.get('cls'))
            with SCHOOL_LOCK:
                if cls not in SCHOOL['classes']:
                    raise ApiError('Lớp không có trong danh sách lớp')
        paths = collect_paths_clean(b['collect_paths']) if 'collect_paths' in b else list(EXAM['collect_paths'])
        kq_url = clean_exam_url(b['kq_url']) if 'kq_url' in b else EXAM.get('kq_url', '')
        if steps.get('kq') and not kq_url:
            raise ApiError('Đã chọn mở bài kiểm tra KhoaQuiz nhưng chưa có link')
        if steps.get('collect') and not paths:
            raise ApiError('Đã chọn thu file bài làm nhưng chưa nhập thư mục nào')
        try:
            minutes = max(0, min(600, int(b.get('minutes') or 0)))
        except (TypeError, ValueError):
            raise ApiError('Số phút phải là số')
        now = time.time()
        EXAM.update({'active': True, 'since': now, 'end_at': now + minutes * 60 if minutes else 0.0, 'cls': cls, 'hosts': hosts,
                     'steps': steps, 'stop_watch': bool(b.get('stop_watch', True)), 'busy': 'start', 'collect_paths': paths, 'collected': '',
                     'kq_url': kq_url})
    exam_save()
    start_job(job_exam_start, hosts, steps, cls, kq_url)
    return {'ok': True}


def api_exam_end(_b=None):
    with EXAM_LOCK:
        if EXAM['busy']:
            raise ApiError('Đang chạy bước khác, hãy đợi xong')
        if not EXAM['active']:
            raise ApiError('Chế độ thi chưa bật')
        hosts, steps, cls, sw = list(EXAM['hosts']), dict(EXAM['steps']), EXAM['cls'], EXAM['stop_watch']
        paths, since = list(EXAM['collect_paths']), EXAM['since']
        EXAM.update({'active': False, 'end_at': 0.0, 'busy': 'end'})
    exam_save()
    start_job(job_exam_end, hosts, steps, cls, sw, paths, since)
    return {'ok': True}


def exam_loop():
    """Chạy nền: hết giờ đặt trước thì tự tắt chế độ thi."""
    while True:
        time.sleep(15)
        try:
            with EXAM_LOCK:
                due = EXAM['active'] and EXAM['end_at'] and time.time() >= EXAM['end_at'] and not EXAM['busy']
            if due:
                log('Chế độ thi: hết giờ, tự tắt', 'head')
                api_exam_end()
        except Exception as e:  # noqa
            log('Lỗi chế độ thi: %s' % e, 'err')
