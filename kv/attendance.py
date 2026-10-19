# -*- coding: utf-8 -*-
"""API điểm danh vắng và tự dồn chỗ ngồi."""

import datetime
import json
import time

from .announce import job_announce
from .runtime import ApiError, log, start_job
from .school import _cls_norm, LAYOUT_DEFAULT, SCHOOL, SCHOOL_LOCK, school_save
from .seating import att_state, att_today, plan_moves, plan_shares, seat_host_map, seat_online_map


def api_school_attendance(q):
    cls = _cls_norm(q.get('cls'))
    with SCHOOL_LOCK:
        if cls not in SCHOOL['classes']:
            raise ApiError('Lớp không có trong danh sách lớp')
    return att_state(cls)


def att_recompute(cls):
    """Kiểm tra máy nào đang bật rồi tính lại chỗ ngồi hôm nay. Trả về {tên: số máy} của các em bị đổi chỗ so với lần trước."""
    key = '%s|%s' % (att_today(), cls)
    with SCHOOL_LOCK:
        lay = json.loads(json.dumps(SCHOOL['layouts'].get(cls) or dict(LAYOUT_DEFAULT)))
        names = list(SCHOOL['classes'].get(cls, []))
        e = SCHOOL['attendance'].get(key) or {}
        absent, prev = list(e.get('absent', [])), dict(e.get('moves', {}))
        prev_sh = dict(e.get('shares', {}))
    lay = dict(LAYOUT_DEFAULT, **lay)
    hmap = seat_host_map(lay)
    online = seat_online_map(lay, hmap)  # chạy ngoài khóa vì có chờ mạng
    silent = bool(online) and not any(online.values())  # không máy nào trả lời: nhiều khả năng chưa bật máy hoặc sai tên máy, không dồn chỗ theo trạng thái bật/tắt
    if silent:
        online = {}
    if lay.get('seats'):
        moves, unplaced = plan_moves(lay, names, absent, online)
    else:  # lớp chưa xếp chỗ thì không tự xếp
        moves, unplaced = {}, []
    shares = plan_shares(lay, unplaced, absent, moves, online) if unplaced else {}
    unplaced = [n for n in unplaced if n not in shares]
    with SCHOOL_LOCK:
        ent = SCHOOL['attendance'].setdefault(key, {})
        ent.update({'absent': absent, 'moves': moves, 'unplaced': unplaced, 'shares': shares,
                    'offline': sorted(s for s, ok in online.items() if not ok), 'silent': silent, 'checked_at': time.strftime('%H:%M:%S')})
        old = (datetime.date.today() - datetime.timedelta(days=60)).strftime('%Y-%m-%d')
        for k in [k for k in SCHOOL['attendance'] if k.split('|', 1)[0] < old]:
            del SCHOOL['attendance'][k]
    school_save()
    return {n: s for n, s in moves.items() if prev.get(n) != s}, {n: s for n, s in shares.items() if prev_sh.get(n) != s}


def api_school_attendance_set(b):
    """action: toggle (đổi vắng/có mặt của một em), present (cả lớp có mặt), recheck (kiểm tra lại máy và dồn chỗ),
    setting (bật tắt: notify, auto_announce)."""
    cls = _cls_norm(b.get('cls'))
    act = str(b.get('action') or '')
    key = '%s|%s' % (att_today(), cls)
    with SCHOOL_LOCK:
        if cls not in SCHOOL['classes']:
            raise ApiError('Lớp không có trong danh sách lớp')
        names = SCHOOL['classes'][cls]
        ent = SCHOOL['attendance'].setdefault(key, {})
        if act == 'toggle':
            n = str(b.get('name') or '')
            if n not in names:
                raise ApiError('Học sinh không có trong lớp')
            ab = list(ent.get('absent', []))
            if n in ab:
                ab.remove(n)
            else:
                ab.append(n)
            ent['absent'] = ab
        elif act == 'present':
            ent['absent'] = []
        elif act == 'absent_many':  # đánh vắng nhiều em một lần (gợi ý từ KhoaQuiz)
            add = [n for n in (b.get('names') or []) if isinstance(n, str) and n in names]
            ent['absent'] = list(ent.get('absent', [])) + [n for n in add if n not in ent.get('absent', [])]
        elif act == 'setting':
            if 'notify' in b:
                SCHOOL['attend_notify'] = bool(b.get('notify'))
            if 'auto_announce' in b:
                SCHOOL['auto_announce'] = bool(b.get('auto_announce'))
        elif act != 'recheck':
            raise ApiError('Thao tác không hợp lệ')
    if act == 'setting':
        school_save()
        return att_state(cls)
    changed, ch_sh = att_recompute(cls)
    st = att_state(cls)
    if act == 'absent_many':
        log('Điểm danh lớp %s: đánh vắng theo gợi ý KhoaQuiz: %s' % (cls, ', '.join(n for n in (b.get('names') or []) if n in st['absent']) or '(không có)'), 'head')
    if act == 'toggle':
        n = str(b.get('name') or '')
        log('Điểm danh lớp %s: %s %s' % (cls, n, 'VẮNG' if n in st['absent'] else 'có mặt'), 'head')
    for n, s in changed.items():
        log('Chuyển chỗ lớp %s: %s -> máy %d (máy trống gần nhất)' % (cls, n, s), 'head')
    for n, s in st['shares'].items():
        log('Hết máy trống: %s ngồi chung máy %d với %s' % (n, s, st['seats'].get(str(s), '?')), 'warn')
    if st['unplaced']:
        log('Lớp %s: không còn máy nào cho %s' % (cls, ', '.join(st['unplaced'])), 'warn')
    if (changed or ch_sh) and st['notify']:
        start_job(job_announce, cls, list(changed) + list(ch_sh), 15, True, False, True)
    st['changed'] = changed
    return st
