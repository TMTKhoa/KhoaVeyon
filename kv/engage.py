# -*- coding: utf-8 -*-
"""Bốc thăm gọi tên và hình nền máy học sinh (theo chế độ / tiết, kèm số máy và tên em ngồi)."""

import base64
import hashlib
import json
import os
import re
import secrets
import threading
import time

from .paths import CONFIG_PATH
from .remote import rfs_sha, rfs_write
from .runtime import ApiError, clean_hosts, log, pool_run, split_host_port, start_job
from .school import _cls_norm, LAYOUT_DEFAULT, SCHOOL, SCHOOL_LOCK, school_now, school_save
from .seating import att_state, seat_host_map
from .student import send_message, STUDENT_ROOT, who

# ---------------------------------------------------------------- bốc thăm
DRAWN = {}            # lớp -> tên các em đã được gọi trong vòng này
DRAW_LOCK = threading.Lock()


def draw_candidates(cls):
    """[(tên, số máy, tên máy)] các em có mặt (không vắng, máy không tắt)."""
    st = att_state(cls)
    with SCHOOL_LOCK:
        lay = dict(LAYOUT_DEFAULT, **(SCHOOL['layouts'].get(cls) or {}))
    hmap = seat_host_map(lay)
    off = {str(x) for x in st['offline']}
    out = []
    for no, name in sorted(st['seats'].items(), key=lambda kv: int(kv[0])):
        if name and str(no) not in off:
            out.append((name, int(no), hmap.get(int(no), '')))
    return out


def api_draw(b):
    """Bốc thăm một em. repeat: cho phép gọi lại em đã được gọi; reset: bắt đầu vòng mới; send: báo lên máy em đó."""
    cls = _cls_norm(b.get('cls')) or (school_now().get('current') or {}).get('cls', '')
    with SCHOOL_LOCK:
        if not cls or cls not in SCHOOL['classes']:
            raise ApiError('Chọn một lớp có trong danh sách lớp')
    cands = draw_candidates(cls)
    if not cands:
        raise ApiError('Lớp %s chưa có em nào trong sơ đồ chỗ ngồi (hoặc cả lớp vắng/máy tắt)' % cls)
    with DRAW_LOCK:
        if b.get('reset'):
            DRAWN.pop(cls, None)
        done = DRAWN.setdefault(cls, set())
        pool = cands if b.get('repeat') else [c for c in cands if c[0] not in done]
        new_round = False
        if not pool:
            done.clear()
            pool, new_round = cands, True
        name, no, host = secrets.choice(pool)
        done.add(name)
        left = len([c for c in cands if c[0] not in done])
    if b.get('send', True) and host:
        start_job(send_message, [host], {'type': 'msg', 'title': 'Mời em trả lời!', 'text': '%s ơi, thầy/cô mời em!' % name, 'seconds': 8})
    log('🎲 Bốc thăm lớp %s: %s (máy %d)' % (cls, name, no), 'head')
    return {'name': name, 'no': no, 'host': host, 'cls': cls, 'left': left, 'new_round': new_round, 'names': [c[0] for c in cands]}


# ---------------------------------------------------------------- hình nền
HEX_RE = re.compile(r'^#[0-9a-fA-F]{6}$')
BG_RE = re.compile(r'^[0-9a-f]{16}$')
WALL_DIR_REMOTE = STUDENT_ROOT + '\\wall'
MAX_BG = 3 * 1024 * 1024


def walls_root():
    d = os.path.join(os.path.dirname(CONFIG_PATH), 'walls')
    os.makedirs(d, exist_ok=True)
    return d


def clean_wall(spec):
    s = spec if isinstance(spec, dict) else {}
    bg = str(s.get('bg') or '')
    try:
        dim = max(0, min(80, int(s.get('dim', 35))))
    except (TypeError, ValueError):
        dim = 35
    return {'title': re.sub(r'\s+', ' ', str(s.get('title') or '')).strip()[:60], 'sub': re.sub(r'\s+', ' ', str(s.get('sub') or '')).strip()[:80],
            'c1': s['c1'] if HEX_RE.match(str(s.get('c1') or '')) else '#1d4ed8', 'c2': s['c2'] if HEX_RE.match(str(s.get('c2') or '')) else '#0ea5e9',
            'bg': bg if BG_RE.match(bg) and os.path.isfile(os.path.join(walls_root(), bg + '.jpg')) else '',
            'seat': bool(s.get('seat', True)), 'lock': bool(s.get('lock')), 'dim': dim}


def api_wall_bg(b):
    """Nhận ảnh nền (JPEG đã thu nhỏ ở trình duyệt), lưu data\\walls\\<mã>.jpg, trả về mã."""
    try:
        data = base64.b64decode(str(b.get('data') or ''), validate=False)
    except ValueError:
        raise ApiError('Ảnh không đọc được')
    if len(data) > MAX_BG or not data.startswith(b'\xff\xd8'):
        raise ApiError('Chỉ nhận ảnh JPEG tối đa 3 MB (trình duyệt đã tự thu nhỏ, hãy thử ảnh khác)')
    bid = hashlib.sha256(data).hexdigest()[:16]
    with open(os.path.join(walls_root(), bid + '.jpg'), 'wb') as f:
        f.write(data)
    return {'id': bid}


def api_wall(_q=None):
    with SCHOOL_LOCK:
        presets = json.loads(json.dumps(SCHOOL.get('wall_presets') or {}))
    return {'presets': presets, 'bgs': sorted(f[:-4] for f in os.listdir(walls_root()) if f.endswith('.jpg'))}


def api_wall_img(q):
    bid = str((q or {}).get('id') or '')
    if not BG_RE.match(bid):
        raise ApiError('Mã ảnh không hợp lệ')
    try:
        with open(os.path.join(walls_root(), bid + '.jpg'), 'rb') as f:
            return {'data': 'data:image/jpeg;base64,' + base64.b64encode(f.read()).decode()}
    except OSError:
        raise ApiError('Không thấy ảnh nền')


def api_wall_preset_save(b):
    name = re.sub(r'\s+', ' ', str(b.get('name') or '')).strip()[:40]
    if not name:
        raise ApiError('Hãy đặt tên cho mẫu hình nền')
    with SCHOOL_LOCK:
        SCHOOL.setdefault('wall_presets', {})[name] = clean_wall(b.get('spec'))
    school_save()
    return api_wall()


def api_wall_preset_delete(b):
    name = str(b.get('name') or '')
    with SCHOOL_LOCK:
        (SCHOOL.get('wall_presets') or {}).pop(name, None)
        # chế độ tự động đang dùng mẫu này thì bỏ liên kết
        for m in ((SCHOOL.get('automation') or {}).get('modes') or {}).values():
            if m.get('wall') == name:
                m['wall'] = ''
    from .auto import AUTO, AUTO_LOCK
    with AUTO_LOCK:
        for m in AUTO['modes'].values():
            if m.get('wall') == name:
                m['wall'] = ''
    school_save()
    return api_wall()


def _ensure_bg(host, bg):
    local = os.path.join(walls_root(), bg + '.jpg')
    with open(local, 'rb') as f:
        data = f.read()
    hh = split_host_port(host)[0]
    remote = WALL_DIR_REMOTE + '\\' + bg + '.jpg'
    try:
        same = rfs_sha(hh, remote) == hashlib.sha256(data).hexdigest()
    except FileNotFoundError:
        same = False
    if not same:
        rfs_write(hh, remote, data)


def wall_message(host, spec):
    name, cls, no = who(host)
    msg = {'type': 'wallpaper', 'title': spec['title'], 'sub': spec['sub'] or (('Lớp ' + cls) if cls else ''), 'c1': spec['c1'], 'c2': spec['c2'],
           'bg': spec['bg'], 'dim': spec['dim'], 'lock': spec['lock'], 'name': name if spec['seat'] else '', 'no': no if spec['seat'] else 0}
    return msg


def job_wall_apply(hosts, spec):
    from .student import _inbox_write

    def one(h):
        try:
            if spec['bg']:
                _ensure_bg(h, spec['bg'])
            _inbox_write(h, wall_message(h, spec))
        except Exception as e:  # noqa
            return False, 'không đổi được hình nền (máy tắt hoặc chưa có Agent?): %s' % e
        return True, 'đã gửi hình nền'
    pool_run(one, hosts, 'Đổi hình nền máy học sinh')


def job_wall_restore(hosts):
    send_message(hosts, {'type': 'wallpaper', 'restore': True})


def api_wall_apply(b):
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào')
    spec = b.get('spec')
    if b.get('preset'):
        with SCHOOL_LOCK:
            spec = (SCHOOL.get('wall_presets') or {}).get(str(b['preset']))
        if spec is None:
            raise ApiError('Mẫu hình nền không tồn tại')
    start_job(job_wall_apply, hosts, clean_wall(spec))
    return {'ok': True, 'count': len(hosts)}


def api_wall_restore(b):
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào')
    start_job(job_wall_restore, hosts)
    return {'ok': True, 'count': len(hosts)}


def wall_for_mode(mode):
    """Mẫu hình nền gắn với một chế độ lớp (spec đã làm sạch) hoặc None."""
    from .auto import AUTO, AUTO_LOCK
    with AUTO_LOCK:
        name = (AUTO['modes'].get(mode) or {}).get('wall') or ''
    if not name:
        return None
    with SCHOOL_LOCK:
        spec = (SCHOOL.get('wall_presets') or {}).get(name)
    return clean_wall(spec) if spec else None
