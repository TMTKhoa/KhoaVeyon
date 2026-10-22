# -*- coding: utf-8 -*-
"""Tính năng vui cho lớp học: tặng sao, đếm ngược toàn lớp, chia nhóm ngẫu nhiên, phản hồi "em hiểu / chưa hiểu"."""

import secrets
import time

from .runtime import ApiError, clean_hosts, log, start_job
from .school import _cls_norm, SCHOOL, SCHOOL_LOCK, school_now, school_save
from .seating import att_state, seat_host_map
from .student import LOCK, send_message, who

REACT = {}        # máy -> {'v': 'ok' | 'lost', 'ts'}
RNG = secrets.SystemRandom()


def _cls(b):
    c = _cls_norm(b.get('cls')) or (school_now().get('current') or {}).get('cls', '')
    with SCHOOL_LOCK:
        if not c or c not in SCHOOL['classes']:
            raise ApiError('Chọn một lớp có trong danh sách lớp')
    return c


# ---------------------------------------------------------------- tặng sao
def stars_board(cls):
    with SCHOOL_LOCK:
        d = dict((SCHOOL.get('stars') or {}).get(cls) or {})
    return sorted(({'name': n, 'stars': v} for n, v in d.items()), key=lambda x: (-x['stars'], x['name']))


def api_star(b):
    """Tặng sao cho các máy được chọn (mỗi em một sao), hiện lời khen trên máy em đó."""
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa chọn máy nào')
    cls = _cls_norm(b.get('cls')) or (school_now().get('current') or {}).get('cls', '')
    note = str(b.get('text') or '').strip()[:120] or 'Em làm rất tốt!'
    given = []
    for h in hosts:
        name, c, _no = who(h, cls)
        if name:
            with SCHOOL_LOCK:
                d = SCHOOL.setdefault('stars', {}).setdefault(c or cls, {})
                d[name] = d.get(name, 0) + 1
                given.append((name, d[name]))
    school_save()
    start_job(send_message, hosts, {'type': 'msg', 'title': '⭐ Thầy/cô tặng em một ngôi sao!', 'text': note, 'seconds': 8})
    log('⭐ Tặng sao: %s' % (', '.join(n for n, _ in given) or '%d máy chưa có tên em' % len(hosts)), 'head')
    return {'given': [{'name': n, 'stars': s} for n, s in given], 'board': stars_board(cls)}


def api_stars(q):
    return {'board': stars_board(_cls(q or {}))}


def api_stars_reset(b):
    c = _cls(b)
    with SCHOOL_LOCK:
        (SCHOOL.get('stars') or {}).pop(c, None)
    school_save()
    return {'board': []}


# ---------------------------------------------------------------- đếm ngược
def api_countdown(b):
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào')
    if b.get('cancel'):
        start_job(send_message, hosts, {'type': 'timer', 'cancel': True})
        return {'ok': True}
    try:
        secs = int(float(b.get('minutes')) * 60)
    except (TypeError, ValueError):
        raise ApiError('Số phút phải là số')
    if not 5 <= secs <= 10800:
        raise ApiError('Thời gian từ 5 giây đến 180 phút')
    label = str(b.get('label') or '').strip()[:120]
    start_job(send_message, hosts, {'type': 'timer', 'secs': secs, 'label': label})
    return {'ok': True, 'secs': secs}


# ---------------------------------------------------------------- chia nhóm
def api_groups(b):
    cls = _cls(b)
    st = att_state(cls)
    with SCHOOL_LOCK:
        names = [n for n in SCHOOL['classes'].get(cls, []) if n not in set(st['absent'])]
    if len(names) < 2:
        raise ApiError('Lớp %s chưa đủ học sinh có mặt để chia nhóm' % cls)
    try:
        n = int(b.get('n'))
    except (TypeError, ValueError):
        raise ApiError('Số nhóm hoặc số em mỗi nhóm phải là số')
    k = max(1, min(len(names), n if b.get('mode') == 'count' else -(-len(names) // max(1, n))))
    RNG.shuffle(names)
    groups = [names[i::k] for i in range(k)]        # chia đều, nhóm lệch nhau tối đa một em
    out = [{'no': i + 1, 'names': g} for i, g in enumerate(groups)]
    sent = 0
    if b.get('send', True):
        with SCHOOL_LOCK:
            lay = dict(SCHOOL['layouts'].get(cls) or {})
        from .school import LAYOUT_DEFAULT
        hmap = seat_host_map(dict(LAYOUT_DEFAULT, **lay))
        by_name = {nm: no for no, nm in st['seats'].items()}
        for g in out:
            for nm in g['names']:
                host = hmap.get(int(by_name.get(nm, 0) or 0), '')
                if host:
                    start_job(send_message, [host], {'type': 'msg', 'title': '👥 Em ở Nhóm %d' % g['no'], 'text': 'Các bạn trong nhóm: ' + ', '.join(g['names']), 'seconds': 25})
                    sent += 1
    log('👥 Chia lớp %s thành %d nhóm' % (cls, k), 'head')
    return {'cls': cls, 'groups': out, 'sent': sent}


# ---------------------------------------------------------------- phản hồi em hiểu / chưa hiểu
def react_put(host, v):
    if v in ('ok', 'lost'):
        with LOCK:
            REACT[host] = {'v': v, 'ts': time.time()}


def react_snapshot(max_age=1800):
    now = time.time()
    with LOCK:
        return {h: x['v'] for h, x in REACT.items() if now - x['ts'] < max_age}


def api_react_clear(b):
    hosts = clean_hosts(b.get('hosts'))
    with LOCK:
        for h in (hosts or list(REACT)):
            REACT.pop(h, None)
    if hosts:
        start_job(send_message, hosts, {'type': 'reactclear'})
    return {'ok': True}


# ---------------------------------------------------------------- thông báo nhanh (mẫu lời nhắn cho tin nhắn và màn hình khóa)
QUICK_DEFAULT = [
    ('🤫', 'Lớp ổn định', 'Cả lớp giữ trật tự và ổn định chỗ ngồi.'),
    ('👀', 'Nhìn lên bảng', 'Các em tạm dừng và nhìn lên bảng.'),
    ('⏳', 'Còn 5 phút', 'Còn 5 phút nữa. Các em hoàn thành và lưu bài.'),
    ('💾', 'Lưu bài', 'Các em lưu bài làm lại ngay bây giờ.'),
    ('📤', 'Nộp bài', 'Các em nộp bài theo hướng dẫn của thầy/cô.'),
    ('🧹', 'Dọn dẹp', 'Các em sắp xếp ghế, dọn rác và để chỗ ngồi gọn gàng.'),
    ('🔌', 'Tắt máy', 'Các em đóng ứng dụng và tắt máy đúng cách (Start, Shut down).'),
    ('🎒', 'Được phép ra về', 'Các em được phép ra về. Nhớ tắt máy và dọn chỗ ngồi gọn gàng.'),
    ('🙋', 'Cần hỗ trợ', 'Em nào cần hỗ trợ xin giơ tay, thầy/cô sẽ đến.'),
    ('👏', 'Cảm ơn cả lớp', 'Cảm ơn cả lớp. Buổi học hôm nay rất tốt!'),
]


def quick_clean(raw):
    out = []
    for x in (raw if isinstance(raw, list) else [])[:20]:
        if not isinstance(x, dict):
            continue
        ic, lb, tx = (str(x.get(k) or '').strip() for k in ('icon', 'label', 'text'))
        ic, lb, tx = ic[:4], lb[:24], tx[:300]
        if lb and tx:
            out.append({'icon': ic or '💬', 'label': lb, 'text': tx})
    return out


def api_quick_notes(_q=None):
    with SCHOOL_LOCK:
        cur = quick_clean(SCHOOL.get('quick_notes'))
    return {'items': cur or [{'icon': i, 'label': l, 'text': t} for i, l, t in QUICK_DEFAULT], 'custom': bool(cur)}


def api_quick_notes_save(b):
    items = quick_clean(b.get('items'))
    with SCHOOL_LOCK:
        SCHOOL['quick_notes'] = items or None      # rỗng = về mẫu mặc định
    school_save()
    return api_quick_notes()
