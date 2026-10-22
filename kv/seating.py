# -*- coding: utf-8 -*-
"""Chỗ ngồi: máy ứng với học sinh nào, dồn chỗ khi vắng, điểm danh trong ngày."""

import datetime
import re

from concurrent.futures import ThreadPoolExecutor, as_completed

from .meta import VEYON_PORT
from .network import tcp_open
from .paths import load_script
from .runtime import CFG, CFG_LOCK
from .school import _cls_norm, SCHOOL, SCHOOL_LOCK


def school_seat_no(host, lay):
    """Số máy (số chỗ ngồi) của một tên máy: theo tên máy mẫu (MAY{n}) hoặc theo thứ tự trong danh sách máy ở trang Điều khiển lớp."""
    h = str(host or '').strip().lower()
    pat = (lay.get('pattern') or '').strip().lower()
    if pat and '{n}' in pat:
        pre, post = pat.split('{n}', 1)
        for cand in {h, h.split('.')[0]}:
            m = re.fullmatch(re.escape(pre) + r'0*(\d+)' + re.escape(post), cand)
            if m:
                return int(m.group(1))
        return 0
    with CFG_LOCK:
        hosts = [str(x).strip().lower() for x in CFG.get('hosts') or []]
    for cand in (h, h.split('.')[0]):
        if cand in hosts:
            return hosts.index(cand) + 1
    return 0


def school_student_for(host, cls):
    """(tên học sinh, số máy) ngồi ở máy `host` trong lớp `cls`; rỗng nếu chưa xếp chỗ."""
    if not cls:
        return '', 0
    with SCHOOL_LOCK:
        lay = SCHOOL['layouts'].get(cls)
        if not lay:
            return '', 0
        no = school_seat_no(host, lay)
        # chỗ ngồi thực tế hôm nay (bỏ em vắng, em được chuyển chỗ), giống sơ đồ đang hiện trên màn hình
        e = SCHOOL['attendance'].get('%s|%s' % (att_today(), cls)) or {}
        names = list(SCHOOL['classes'].get(cls, []))
        absent = [n for n in e.get('absent', []) if n in names]
        seats = seats_effective(lay.get('seats'), absent, dict(e.get('moves', {})))
        return seats.get(str(no), ''), no


# ---------------------------------------------------------------- thông báo chỗ ngồi, điểm danh vắng, tự dồn chỗ
SEAT_PS1_NAME = 'kvseat.ps1'
SEAT_JSON_NAME = 'kvseat.json'
SEAT_TASK = 'KhoaVeyonSeat'
SEAT_PS1 = load_script('kvseat.ps1')


def seat_grid(lay):
    """Vị trí (hàng, dãy) của từng số máy, giống cách giao diện đánh số: hàng 0 gần bàn giáo viên, đánh số theo từng dãy."""
    cols, per = int(lay.get('cols', 4)), int(lay.get('per', 10))
    order = list(range(cols))
    if lay.get('first') == 'right':
        order.reverse()
    pos, n = {}, 0
    for c in order:
        rows = list(range(per))
        if lay.get('from') == 'door':
            rows.reverse()
        for r in rows:
            n += 1
            pos[n] = (r, c)
    return pos


def seat_host_map(lay):
    """{số máy: tên máy} theo Tên máy mẫu hoặc thứ tự danh sách máy ở trang Điều khiển lớp."""
    with CFG_LOCK:
        hosts = [str(h).strip() for h in CFG.get('hosts') or [] if str(h).strip()]
    out = {}
    for h in hosts:
        no = school_seat_no(h, lay)
        if no and no not in out:
            out[no] = h
    pat = (lay.get('pattern') or '').strip()
    if pat and '{n}' in pat:
        for no in range(1, int(lay.get('cols', 4)) * int(lay.get('per', 10)) + 1):
            out.setdefault(no, pat.replace('{n}', str(no)))
    return out


def seat_online_map(lay, hmap=None):
    """{số máy: bật/tắt} cho các máy có tên máy. Máy không có tên máy thì không có trong kết quả (coi như dùng được)."""
    hmap = seat_host_map(lay) if hmap is None else hmap
    if not hmap:
        return {}
    out = {}
    with ThreadPoolExecutor(max_workers=32) as ex:
        futs = {ex.submit(tcp_open, h, VEYON_PORT, 0.6): no for no, h in hmap.items()}
        for fut in as_completed(futs):
            try:
                out[futs[fut]] = bool(fut.result())
            except Exception:  # noqa
                out[futs[fut]] = False
    return out


def seats_effective(base, absent, moves):
    """Chỗ ngồi thực tế hôm nay: bỏ em vắng, em được chuyển thì ngồi chỗ mới. {số máy (chuỗi): tên}."""
    gone = set(absent) | set(moves)
    seats = {k: v for k, v in (base or {}).items() if v not in gone}
    for name, no in (moves or {}).items():
        seats[str(no)] = name
    return seats


def plan_moves(lay, class_names, absent, online):
    """Em có mặt mà máy không dùng được (máy hỏng, máy tắt) hoặc chưa có chỗ thì chuyển sang máy trống gần nhất
    (gần theo sơ đồ: hàng và dãy). Máy trống là máy dùng được mà không ai có mặt ngồi, thường là máy của em vắng.
    Trả về ({tên: số máy mới}, [tên không còn máy trống])."""
    cols, per = int(lay.get('cols', 4)), int(lay.get('per', 10))
    total = cols * per
    pos = seat_grid(lay)
    broken = {int(x) for x in lay.get('broken') or []}
    base = {int(k): v for k, v in (lay.get('seats') or {}).items()}
    absent = set(absent)

    def usable(s):
        return s not in broken and online.get(s, True)
    present_at = {s: n for s, n in base.items() if n not in absent}
    free = [s for s in range(1, total + 1) if usable(s) and s not in present_at]
    seated = set(base.values())
    todo = [(s, n) for s, n in sorted(present_at.items()) if not usable(s)]
    todo += [(0, n) for n in class_names if n not in seated and n not in absent]
    moves, unplaced = {}, []
    for s, n in todo:
        if not free:
            unplaced.append(n)
            continue
        ref = pos.get(s) or pos.get(1) or (0, 0)
        best = min(free, key=lambda f: (abs(pos[f][0] - ref[0]) + abs(pos[f][1] - ref[1]), f))
        free.remove(best)
        moves[n] = best
    return moves, unplaced


def plan_shares(lay, unplaced, absent, moves, online):
    """Em hết máy trống thì ngồi chung với bạn ở máy dùng được gần chỗ cũ nhất (ưu tiên máy ít người ngồi chung). {tên: số máy}."""
    broken = {int(x) for x in lay.get('broken') or []}
    pos = seat_grid(lay)
    occ = {int(k): v for k, v in seats_effective(lay.get('seats'), absent, moves).items()}
    occ = {k: v for k, v in occ.items() if k not in broken and online.get(k, True) and k in pos}
    base = {v: int(k) for k, v in (lay.get('seats') or {}).items()}
    count, out = {}, {}
    for n in unplaced:
        if not occ:
            continue
        ref = pos.get(base.get(n)) or pos.get(1) or (0, 0)
        best = min(occ, key=lambda f: (abs(pos[f][0] - ref[0]) + abs(pos[f][1] - ref[1]) + 2 * count.get(f, 0), f))
        count[best] = count.get(best, 0) + 1
        out[n] = best
    return out


def att_today():
    return datetime.date.today().strftime('%Y-%m-%d')


def att_state(cls):
    """Điểm danh hôm nay của một lớp, kèm chỗ ngồi thực tế."""
    cls = _cls_norm(cls)
    with SCHOOL_LOCK:
        e = (SCHOOL['attendance'].get('%s|%s' % (att_today(), cls)) or {})
        lay = SCHOOL['layouts'].get(cls) or {}
        names = list(SCHOOL['classes'].get(cls, []))
        absent = [n for n in e.get('absent', []) if n in names]
        moves = dict(e.get('moves', {}))
        seats = seats_effective(lay.get('seats'), absent, moves)
        return {'cls': cls, 'date': att_today(), 'absent': absent, 'moves': moves, 'seats': seats,
                'offline': list(e.get('offline', [])), 'unplaced': list(e.get('unplaced', [])), 'shares': dict(e.get('shares', {})),
                'checked_at': e.get('checked_at', ''), 'silent': bool(e.get('silent')), 'notify': bool(SCHOOL.get('attend_notify', True)),
                'auto_announce': bool(SCHOOL.get('auto_announce', False))}
