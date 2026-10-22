# -*- coding: utf-8 -*-
"""Trang Monitor: bảng theo dõi lớp theo sơ đồ chỗ ngồi. Chỉ ghép dữ liệu đã có sẵn (trạng thái máy, cửa sổ đang ở trước do máy học sinh tự báo,
giơ tay, vi phạm hôm nay); máy giáo viên không quét thêm gì qua mạng phòng máy."""

import json
import time

from .alerts import ALERT_LOCK, ALERTS, hn_of
from .runtime import ApiError, CFG, CFG_LOCK, clean_hosts, split_host_port, start_job
from .school import _cls_norm, LAYOUT_DEFAULT, SCHOOL, SCHOOL_LOCK, school_bells, school_now, school_save
from .seating import att_state, seat_host_map
from .status import api_status
from .student import ACT, HANDS, LOCK, send_message

ACT_FRESH_SEC = 240      # báo cửa sổ cũ hơn thế này thì coi như không biết


def _period_no(start):
    try:
        for no, (st, _en) in school_bells().items():
            if st == start:
                return int(no)
    except Exception:  # noqa
        pass
    return 0


def api_monitor(q):
    base = api_status(q)
    st = {r['host']: r for r in base['hosts']}
    now = time.time()
    n = school_now()
    cur = n['current'] or {}
    nxt = n['next'] or {}
    with SCHOOL_LOCK:
        classes = sorted(SCHOOL['classes'])
    cls = _cls_norm(q.get('cls')) or cur.get('cls') or (classes[0] if classes else '')
    with CFG_LOCK:
        hosts = list(CFG.get('hosts') or [])
        cfg_names = dict(CFG.get('host_names') or {}, **{k: v for k, v in (CFG.get('host_auto_names') or {}).items() if k not in (CFG.get('host_names') or {})})
    today = time.strftime('%Y-%m-%d')
    viol = {}
    with ALERT_LOCK:
        for e in ALERTS:
            if e.get('date') == today:
                v = viol.setdefault(e['host'], {'n': 0, 'last': '', 'ts': 0, 'name': ''})
                v['n'] += 1
                if e.get('ts', 0) >= v['ts']:
                    v.update(ts=e.get('ts', 0), last=e.get('time', ''), name=e.get('name', ''))
    with LOCK:
        hands = {h: v['ts'] for h, v in HANDS.items()}
        act = {h: dict(v) for h, v in ACT.items()}

    def info(h):
        r = st.get(h) or {}
        a = act.get(h)
        return {'host': h, 'pc': cfg_names.get(h) or h, 'online': bool(r.get('online')), 'health': r.get('health', 'wait'), 'user': r.get('user', ''),
                'hand': h in hands, 'viol': viol.get(h), 'watching': bool(r.get('watching')),
                'act': ({'p': a['p'], 'w': a['w'], 'age': int(now - a['ts'])} if a and now - a['ts'] < ACT_FRESH_SEC else None)}
    out = {'ts': now, 'cls': cls, 'classes': classes, 'source': n['source'],
           'current': {'cls': cur.get('cls', ''), 'start': cur.get('start', ''), 'end': cur.get('end', ''), 'period': _period_no(cur.get('start', ''))} if cur else None,
           'next': {'cls': nxt.get('cls', ''), 'start': nxt.get('start', ''), 'day': nxt.get('day')} if nxt else None,
           'online': base['online'], 'total': base['total'], 'hand_enabled': bool(SCHOOL.get('hand_enabled', True)), 'act_enabled': bool(SCHOOL.get('act_enabled', True)),
           'machines': {h: info(h) for h in hosts}, 'lay': None, 'seats': {}, 'shown': cls}
    if cls:
        with SCHOOL_LOCK:
            lay = dict(LAYOUT_DEFAULT, **(SCHOOL['layouts'].get(cls) or {}))
            has_lay = bool(SCHOOL['layouts'].get(cls))
        if has_lay:
            att = att_state(cls)
            hmap = seat_host_map(lay)
            absent_by_seat = {str(k): v for k, v in (lay.get('seats') or {}).items() if v in att['absent']}
            out['lay'] = json.loads(json.dumps(lay))
            out['seats'] = {str(no): {'host': hmap.get(no, ''), 'name': att['seats'].get(str(no), ''), 'absent': absent_by_seat.get(str(no), ''),
                                      'broken': no in set(int(x) for x in lay.get('broken') or [])} for no in range(1, int(lay['cols']) * int(lay['per']) + 1)}
            used = {s['host'] for s in out['seats'].values() if s['host']}
            out['extras'] = [h for h in hosts if h not in used]
    return out


def api_act_option(b):
    on = bool(b.get('enabled'))
    with SCHOOL_LOCK:
        SCHOOL['act_enabled'] = on
    school_save()
    if not on:
        with LOCK:
            ACT.clear()
    hosts = clean_hosts(b.get('hosts'))
    if hosts:
        start_job(send_message, hosts, {'type': 'config', 'act': on})
    return {'ok': True, 'enabled': on}


# ---------------------------------------------------------------- xem màn hình thu nhỏ
THUMBS = {}          # máy -> {'d': base64 JPEG, 'ts', 'seq'}: máy học sinh tự chụp, nén và gửi khi giáo viên bật "Xem màn hình"
THUMB_SEQ = [0]
LIVE_TTL = 120


def thumb_put(host, b64):
    with LOCK:
        THUMB_SEQ[0] += 1
        THUMBS[host] = {'d': b64, 'ts': time.time(), 'seq': THUMB_SEQ[0]}
        old = time.time() - 900
        for h in [h for h, v in THUMBS.items() if v['ts'] < old]:
            del THUMBS[h]


def api_monitor_thumbs(q):
    try:
        since = int(q.get('since') or 0)
    except (TypeError, ValueError):
        since = 0
    with LOCK:
        items = {h: {'d': 'data:image/jpeg;base64,' + v['d'], 'age': int(time.time() - v['ts'])} for h, v in THUMBS.items() if v['seq'] > since}
        last = THUMB_SEQ[0]
    return {'last': last, 'items': items}


def api_monitor_live(b):
    """Bật / gia hạn / tắt xem màn hình thu nhỏ. Giao diện gọi lại mỗi ~40 giây khi đang xem; ngừng gọi thì máy học sinh tự dừng sau LIVE_TTL giây."""
    on = bool(b.get('on'))
    try:
        sec = max(3, min(30, int(b.get('sec') or 5)))
    except (TypeError, ValueError):
        sec = 5
    hosts = clean_hosts(b.get('hosts'))
    if hosts:
        start_job(send_message, hosts, {'type': 'config', 'live': sec if on else 0, 'ttl': LIVE_TTL})
    if not on:
        with LOCK:
            for h in hosts or list(THUMBS):
                THUMBS.pop(h, None)
    return {'ok': True, 'count': len(hosts)}


# ---------------------------------------------------------------- gán máy (tên PC) vào vị trí trong phòng
def api_seat_hostmap(b):
    """Bảng máy -> số vị trí (số máy trên sơ đồ). Dùng khi tên PC không trùng số vị trí (vd. PC11 ngồi ở vị trí 8). Gửi rỗng để xóa hết."""
    raw = b.get('map')
    if not isinstance(raw, dict):
        raise ApiError('Dữ liệu không hợp lệ')
    with CFG_LOCK:
        hosts = [str(h) for h in CFG.get('hosts') or []]
    out, used = {}, {}
    for h, v in raw.items():
        if h not in hosts or v in (None, ''):
            continue
        try:
            no = int(v)
        except (TypeError, ValueError):
            raise ApiError('Số vị trí của máy %s phải là số' % h)
        if not 1 <= no <= 300:
            raise ApiError('Số vị trí từ 1 đến 300 (máy %s)' % h)
        if no in used:
            raise ApiError('Vị trí %d đang gán cho cả %s và %s' % (no, used[no], h))
        used[no] = h
        out[h] = no
    with SCHOOL_LOCK:
        SCHOOL['seat_hostmap'] = out
    school_save()
    return {'ok': True, 'map': out}
