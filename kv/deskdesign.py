# -*- coding: utf-8 -*-
"""Thiết kế Desktop học sinh: giáo viên sắp icon và chọn hình nền trên màn hình giả lập, rồi gửi xuống máy học sinh
(C:\\cmd\\desktop\\layout.json + wallpaper.jpg). Việc dựng icon và đặt vị trí do -desklock-start làm; hình nền và vị trí chỉ đặt MỘT LẦN
cho mỗi bản thiết kế, sau đó học sinh vẫn tự đổi hình nền (tải ảnh về, Set as background) và kéo icon được."""

import json
import os
import re
import threading
import time

from .engage import BG_RE, walls_root
from .paths import CONFIG_PATH
from .remote import rfs_remove, rfs_write
from .runtime import ApiError, CFG, CFG_LOCK, clean_hosts, log, pool_run, start_job

DESK_FILE = os.path.join(os.path.dirname(CONFIG_PATH), 'desktop.json')
DESK_LOCK = threading.RLock()
GRID_COLS, GRID_ROWS = 18, 8            # lưới của màn hình giả lập (mỗi ô ứng với một ô icon thật trên Desktop học sinh)
MAX_ITEMS = 60
DEFAULT = {'wall': '', 'items': [], 'stamp': '', 'cols': GRID_COLS, 'rows': GRID_ROWS}
BAD_NAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
WALL_EXTS = ('jpg', 'jpeg', 'png', 'bmp')


def clean_item(it):
    it = it if isinstance(it, dict) else {}
    kind = 'url' if it.get('kind') == 'url' else 'app'
    name = BAD_NAME.sub('', str(it.get('name') or '')).strip()[:40]
    target = str(it.get('target') or '').strip()[:500]
    if kind == 'url' and target and not re.match(r'^[a-z][a-z0-9+.-]*://', target, re.I):
        target = 'https://' + target
    if kind == 'url' and not re.match(r'^https?://', target, re.I):
        return None   # chỉ nhận http/https, không nhận file:// hay lệnh lạ
    if not name or not target or re.search(r'[\x00-\x1f]', target):
        return None
    try:
        col = max(0, min(60, int(it.get('col', 0))))
        row = max(0, min(40, int(it.get('row', 0))))
    except (TypeError, ValueError):
        col = row = 0
    return {'id': re.sub(r'[^a-z0-9_-]', '', str(it.get('id') or '').lower())[:20] or 'i%d' % int(time.time() * 1000 % 10 ** 9),
            'name': name, 'kind': kind, 'target': target, 'args': str(it.get('args') or '').strip()[:300] if kind == 'app' else '',
            'emoji': str(it.get('emoji') or ('🌐' if kind == 'url' else '📁')).strip()[:4], 'col': col, 'row': row}


def clean_design(d):
    d = d if isinstance(d, dict) else {}
    items, seen, cells = [], set(), set()
    for raw in (d.get('items') or [])[:MAX_ITEMS]:
        it = clean_item(raw)
        if not it or it['name'].lower() in seen:
            continue
        seen.add(it['name'].lower())
        while (it['col'], it['row']) in cells:   # hai icon không chung một ô
            it['row'] += 1
        cells.add((it['col'], it['row']))
        items.append(it)
    wall = str(d.get('wall') or '')
    if not (BG_RE.match(wall) and os.path.isfile(os.path.join(walls_root(), wall + '.jpg'))):
        wall = ''
    return {'wall': wall, 'items': items, 'stamp': str(d.get('stamp') or ''), 'cols': GRID_COLS, 'rows': GRID_ROWS}


def desk_load():
    try:
        with open(DESK_FILE, 'r', encoding='utf-8') as f:
            return clean_design(json.load(f))
    except (OSError, ValueError):
        return dict(DEFAULT)


def api_desk(_q=None):
    with DESK_LOCK:
        d = desk_load()
    with CFG_LOCK:
        d['hosts_n'] = len(CFG.get('hosts') or [])
    return d


def api_desk_save(b):
    d = clean_design(b.get('design'))
    d['stamp'] = time.strftime('%Y%m%d%H%M%S')   # đổi dấu mẫu = các máy sẽ đặt lại hình nền và vị trí icon một lần
    with DESK_LOCK:
        try:
            with open(DESK_FILE, 'w', encoding='utf-8') as f:
                json.dump(d, f, ensure_ascii=False)
        except OSError as e:
            raise ApiError('Không lưu được thiết kế Desktop: %s' % e)
    return d


def layout_bytes(d):
    out = {'stamp': d['stamp'], 'items': [{k: it[k] for k in ('name', 'kind', 'target', 'args', 'col', 'row')} for it in d['items']]}
    return json.dumps(out, ensure_ascii=False).encode('utf-8')


def remote_desk_dir():
    with CFG_LOCK:
        base = (CFG.get('dist_target') or r'C:\cmd').rstrip('\\')
    return base + '\\desktop'


def push_design(hosts, d=None):
    """Chép layout.json và hình nền xuống C:\\cmd\\desktop của từng máy (chưa khóa). Trả về (số máy ok, số lỗi)."""
    d = d or desk_load()
    if not d['stamp']:
        d['stamp'] = time.strftime('%Y%m%d%H%M%S')
    rd = remote_desk_dir()
    wall = None
    if d['wall']:
        with open(os.path.join(walls_root(), d['wall'] + '.jpg'), 'rb') as f:
            wall = f.read()
    lay = layout_bytes(d)

    def one(h):
        try:
            rfs_write(h, rd + '\\layout.json', lay)
            for ext in WALL_EXTS:   # tránh còn hình nền cũ khác đuôi làm script chọn nhầm
                if ext == 'jpg' and wall:
                    continue
                try:
                    rfs_remove(h, rd + '\\wallpaper.' + ext)
                except Exception:  # noqa
                    pass
            if wall:
                rfs_write(h, rd + '\\wallpaper.jpg', wall)
        except Exception as e:  # noqa
            return False, 'không chép được thiết kế Desktop (máy tắt hoặc chưa có Agent?): %s' % e
        return True, 'đã chép thiết kế Desktop (%d icon%s)' % (len(d['items']), ', có hình nền' if wall else '')
    pool_run(one, hosts, 'Gửi thiết kế Desktop')


def job_desk_apply(hosts, lock):
    from .jobs import job_action
    push_design(hosts)
    if lock:
        job_action('desklock-start', hosts)


def api_desk_apply(b):
    """Gửi thiết kế xuống máy học sinh; lock=True thì chạy luôn -desklock-start để icon và hình nền có hiệu lực ngay."""
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào')
    with DESK_LOCK:
        d = desk_load()
    if not d['items'] and not d['wall']:
        raise ApiError('Chưa có icon hay hình nền nào trong thiết kế')
    start_job(job_desk_apply, hosts, b.get('lock', True) is not False)
    return {'ok': True, 'count': len(hosts)}
