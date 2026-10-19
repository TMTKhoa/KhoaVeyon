# -*- coding: utf-8 -*-
"""API trang Lớp & lịch dạy: xem, sửa, nhập Excel và vòng lặp nền theo thời khóa biểu."""

import json
import time

from .announce import job_announce
from .runtime import ApiError, log, start_job
from .school import (
    _cls_norm, layout_clean, parse_classes_json, parse_classes_xlsx, parse_timetable_xlsx, SCHOOL, SCHOOL_LOCK,
    SCHOOL_MANUAL_MIN, school_now, school_save,
)


def api_school_layout(b):
    """Lưu sơ đồ chỗ ngồi của một lớp. apply_all: chép kiểu phòng (số dãy, số máy, cách đánh số) sang mọi lớp, giữ nguyên chỗ ngồi."""
    c = _cls_norm(b.get('cls'))
    with SCHOOL_LOCK:
        if not c or c not in SCHOOL['classes']:
            raise ApiError('Lớp không có trong danh sách lớp')
        oldl = SCHOOL['layouts'].get(c) or {}
        lay = layout_clean(b, oldl.get('seats'), oldl.get('broken'))
        SCHOOL['layouts'][c] = lay
        if b.get('apply_all'):
            for other in SCHOOL['classes']:
                if other != c:
                    old = (SCHOOL['layouts'].get(other) or {}).get('seats', {})
                    SCHOOL['layouts'][other] = layout_clean(dict(lay, seats=old))
    school_save()
    return api_school()


def school_brief():
    n = school_now()
    return {'current': (n['current'] or {}).get('cls', ''), 'source': n['source'],
            'next': ((n['next'] or {}).get('cls', ''), (n['next'] or {}).get('start', ''))}


def api_school(_q=None):
    with SCHOOL_LOCK:
        d = {k: SCHOOL[k] for k in ('slots', 'from', 'auto', 'manual', 'classes_file', 'classes_at', 'timetable_file',
                                   'timetable_at', 'teacher', 'subject', 'attend_notify', 'auto_announce')}
        d['classes'] = [{'name': n, 'count': len(v)} for n, v in sorted(SCHOOL['classes'].items())]
        d['layouts'] = json.loads(json.dumps(SCHOOL['layouts']))
        known = set(SCHOOL['classes'])
    d['unknown'] = sorted({s['cls'] for s in d['slots'] if known and s['cls'] not in known})
    d.update(school_now())
    d['server_ts'] = time.time()
    return d


def api_school_students(q):
    with SCHOOL_LOCK:
        names = list(SCHOOL['classes'].get(_cls_norm(q.get('cls')), []))
    return {'names': names}


def api_school_set(b):
    act = str(b.get('action') or '')
    with SCHOOL_LOCK:
        if act == 'auto':
            SCHOOL['auto'] = bool(b.get('value'))
            SCHOOL['override'] = None
        elif act == 'set':
            c = _cls_norm(b.get('cls'))
            if not c:
                raise ApiError('Thiếu tên lớp')
            if SCHOOL.get('auto', True):
                now = time.time()
                SCHOOL['override'] = {'cls': c, 'since': now, 'until': now + SCHOOL_MANUAL_MIN * 60}
            else:
                SCHOOL['manual'] = c
            log('Đã đặt lớp hiện tại: %s' % c, 'head')
        elif act == 'clear':
            SCHOOL['override'] = None
            SCHOOL['manual'] = ''
        else:
            raise ApiError('Thao tác không hợp lệ')
    school_save()
    return api_school()


def school_merge_classes(data, source):
    """Gộp danh sách lớp (từ KhoaTool hoặc KhoaQuiz) vào danh sách hiện có: lớp trong `data` được thay danh sách học sinh,
    lớp khác giữ nguyên (khác nhập Excel của trường là thay toàn bộ). Trả về (số lớp mới, số lớp cập nhật, số học sinh)."""
    stamp = time.strftime('%d/%m/%Y %H:%M')
    new = upd = 0
    with SCHOOL_LOCK:
        for cls, names in data.items():
            old = list(SCHOOL['classes'].get(cls, []))
            if cls in SCHOOL['classes']:
                upd += 1
            else:
                new += 1
            SCHOOL['classes'][cls] = list(names)
            lay = SCHOOL['layouts'].get(cls)
            if lay:  # bỏ chỗ của học sinh đã rời lớp; giữ tên ghi tay (học sinh ngoài danh sách)
                lay['seats'] = {k: v for k, v in (lay.get('seats') or {}).items() if v in names or v not in old}
        SCHOOL.update({'classes_file': source, 'classes_at': stamp})
    school_save()
    n = sum(len(v) for v in data.values())
    log('Đã gộp danh sách lớp từ %s: %d lớp mới, %d lớp cập nhật, %d học sinh (lớp khác giữ nguyên)' % (source, new, upd, n), 'ok')
    return new, upd, n


def school_import(kind, path, filename):
    stamp = time.strftime('%d/%m/%Y %H:%M')
    if kind == 'classes' and filename.lower().endswith('.json'):
        school_merge_classes(parse_classes_json(path), filename)
        return
    if kind == 'classes':
        data = parse_classes_xlsx(path)
        with SCHOOL_LOCK:
            prev = {k: set(v) for k, v in SCHOOL['classes'].items()}
            SCHOOL.update({'classes': data, 'classes_file': filename, 'classes_at': stamp})
            for k in list(SCHOOL['layouts']):
                if k not in data:
                    del SCHOOL['layouts'][k]
                else:  # bỏ chỗ của học sinh đã rời lớp; giữ tên ghi tay (học sinh ngoài danh sách)
                    keep = SCHOOL['layouts'][k].get('seats', {})
                    SCHOOL['layouts'][k]['seats'] = {n: v for n, v in keep.items() if v in data[k] or v not in prev.get(k, set())}
        log('Đã nhập danh sách lớp: %d lớp, %d học sinh' % (len(data), sum(len(v) for v in data.values())), 'ok')
    else:
        data = parse_timetable_xlsx(path)
        with SCHOOL_LOCK:
            SCHOOL.update({'slots': data['slots'], 'from': data['from'], 'teacher': data['teacher'], 'subject': data['subject'],
                           'timetable_file': filename, 'timetable_at': stamp, 'override': None})
        log('Đã nhập thời khóa biểu: %d tiết mỗi tuần%s' % (len(data['slots']), (', bắt đầu từ ' + data['from']) if data['from'] else ''), 'ok')
    school_save()


def school_loop():
    """Chạy nền: ghi nhật ký khi sang lớp mới."""
    last = None
    while True:
        try:
            c = (school_now()['current'] or {}).get('cls', '')
            if last is not None and c != last:
                log('Chuyển lớp: %s' % (('đang dạy lớp ' + c) if c else 'hết tiết'), 'head')
                if c and SCHOOL.get('auto_announce') and c in SCHOOL['classes']:
                    start_job(job_announce, c, [], 15, True, False, False)
            last = c
        except Exception:  # noqa
            pass
        time.sleep(15)
