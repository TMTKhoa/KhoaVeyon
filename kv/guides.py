# -*- coding: utf-8 -*-
"""Hướng dẫn thao tác cho học sinh: thư viện sẵn (ảnh động GIF: phóng to/thu nhỏ bằng Ctrl + lăn chuột, sao chép/dán, hoàn tác...) và hướng dẫn tự tạo
(tiêu đề, các bước, ảnh/GIF của giáo viên). Gửi tới máy học sinh: hiện cửa sổ có ảnh động, học sinh xem lại được từ menu nút nổi."""

import base64
import hashlib
import json
import os
import re
import secrets
import threading

from .paths import CONFIG_PATH
from .remote import rfs_sha, rfs_write
from .runtime import ApiError, clean_hosts, log, pool_run, split_host_port, start_job, WEB_DIR
from .student import _inbox_write, STUDENT_ROOT

BUILTIN = [
    {'id': 'zoom', 'title': 'Phóng to / thu nhỏ bằng Ctrl + con lăn chuột', 'keys': 'Ctrl + lăn chuột',
     'steps': ['Giữ phím Ctrl (góc dưới bên trái bàn phím).', 'Lăn con lăn chuột LÊN để phóng to, lăn XUỐNG để thu nhỏ.', 'Muốn về cỡ ban đầu: nhấn Ctrl + 0.'], 'tip': 'Dùng được trên trình duyệt, Word, PowerPoint, Excel...'},
    {'id': 'copy', 'title': 'Sao chép và dán', 'keys': 'Ctrl + C, Ctrl + V',
     'steps': ['Bôi đen phần cần chép.', 'Nhấn Ctrl + C để sao chép (Ctrl + X nếu muốn cắt).', 'Bấm vào chỗ cần dán rồi nhấn Ctrl + V.'], 'tip': 'Tiết kiệm thời gian hơn gõ lại.'},
    {'id': 'undo', 'title': 'Hoàn tác khi lỡ tay', 'keys': 'Ctrl + Z',
     'steps': ['Lỡ gõ nhầm, xóa nhầm hoặc kéo nhầm?', 'Nhấn Ctrl + Z để lùi lại một bước, nhấn nhiều lần để lùi nhiều bước.', 'Muốn làm lại: Ctrl + Y.'], 'tip': 'Đừng hoảng, hầu hết thao tác đều lùi lại được.'},
    {'id': 'save', 'title': 'Lưu bài làm', 'keys': 'Ctrl + S',
     'steps': ['Thấy dấu * cạnh tên tệp nghĩa là chưa lưu.', 'Nhấn Ctrl + S để lưu.', 'Nhớ lưu thường xuyên và lưu trước khi nộp bài.'], 'tip': 'Mất điện hay treo máy cũng không mất bài đã lưu.'},
    {'id': 'alttab', 'title': 'Chuyển qua lại giữa các cửa sổ', 'keys': 'Alt + Tab',
     'steps': ['Giữ phím Alt.', 'Gõ Tab để chọn cửa sổ khác.', 'Thả phím để chuyển sang cửa sổ đó.'], 'tip': 'Nhanh hơn việc bấm tìm trên thanh tác vụ.'},
    {'id': 'snip', 'title': 'Chụp một vùng màn hình', 'keys': 'Windows + Shift + S',
     'steps': ['Nhấn đồng thời phím Windows + Shift + S.', 'Kéo chuột để chọn vùng cần chụp.', 'Nhấn Ctrl + V để dán ảnh vào bài làm.'], 'tip': 'Chỉ chụp khi giáo viên cho phép.'},
    {'id': 'selectall', 'title': 'Chọn toàn bộ nội dung', 'keys': 'Ctrl + A',
     'steps': ['Bấm vào trong văn bản hoặc trang cần chọn.', 'Nhấn Ctrl + A để chọn tất cả.', 'Sau đó có thể Ctrl + C để chép hoặc đổi cỡ chữ, kiểu chữ cho cả bài.'], 'tip': ''},
    {'id': 'find', 'title': 'Tìm chữ trong trang', 'keys': 'Ctrl + F',
     'steps': ['Nhấn Ctrl + F, ô tìm kiếm hiện ra.', 'Gõ từ cần tìm.', 'Các chỗ tìm thấy được tô màu, bấm Enter để nhảy tới chỗ kế tiếp.'], 'tip': 'Hữu ích khi đọc trang dài.'},
]
# Bản cho học sinh lớp nhỏ (lớp 1-3): câu ngắn, từ dễ hiểu, "bấm" thay cho "nhấn", chữ to
KID = {
    'zoom': {'title': 'Làm chữ TO và NHỎ', 'keys': 'Ctrl + Bánh xe chuột', 'steps': ['Dùng một ngón tay giữ phím Ctrl.', 'Lăn bánh xe chuột LÊN: chữ TO ra.', 'Lăn bánh xe chuột XUỐNG: chữ NHỎ lại.'], 'tip': 'Em thử xem nào!'},
    'copy': {'title': 'Chép chữ sang chỗ khác', 'keys': 'Ctrl + C, Ctrl + V', 'steps': ['Dùng chuột tô xanh chữ cần chép.', 'Bấm phím Ctrl và phím C cùng lúc.', 'Bấm vào chỗ muốn để chữ.', 'Bấm phím Ctrl và phím V cùng lúc.'], 'tip': 'Không cần viết lại, rất nhanh!'},
    'undo': {'title': 'Làm nhầm? Quay lại!', 'keys': 'Ctrl + Z', 'steps': ['Em lỡ làm nhầm?', 'Bấm phím Ctrl và phím Z cùng lúc.', 'Mọi thứ quay về như lúc trước.'], 'tip': 'Đừng lo, em sửa được!'},
    'save': {'title': 'Cất bài làm của em', 'keys': 'Ctrl + S', 'steps': ['Nhìn tên bài: có dấu * là chưa cất.', 'Bấm phím Ctrl và phím S cùng lúc.', 'Dấu * biến mất là bài đã được cất.'], 'tip': 'Nhớ cất bài trước khi tắt máy nhé!'},
    'alttab': {'title': 'Đổi sang cửa sổ khác', 'keys': 'Alt + Tab', 'steps': ['Giữ phím Alt.', 'Bấm phím Tab một lần.', 'Thả tay ra: cửa sổ mới hiện lên.'], 'tip': 'Bấm Tab nhiều lần để chọn cửa sổ khác.'},
    'snip': {'title': 'Chụp hình màn hình', 'keys': 'Windows + Shift + S', 'steps': ['Bấm ba phím Windows, Shift và S cùng lúc.', 'Kéo chuột để chọn hình cần chụp.', 'Bấm phím Ctrl và phím V để dán hình vào bài.'], 'tip': 'Chỉ chụp khi cô cho phép nhé!'},
    'selectall': {'title': 'Chọn hết các chữ', 'keys': 'Ctrl + A', 'steps': ['Bấm vào trong bài viết.', 'Bấm phím Ctrl và phím A cùng lúc.', 'Tất cả chữ được tô xanh.'], 'tip': 'Giờ em có thể chép hết hoặc đổi chữ cho cả bài.'},
    'find': {'title': 'Tìm chữ trong trang', 'keys': 'Ctrl + F', 'steps': ['Bấm phím Ctrl và phím F cùng lúc.', 'Gõ chữ em muốn tìm.', 'Chữ tìm thấy được tô vàng.'], 'tip': 'Giúp em tìm nhanh trong trang dài.'},
}
BUILTIN_BY_ID = {g['id']: g for g in BUILTIN}
GLOCK = threading.RLock()
ID_RE = re.compile(r'^[a-z0-9]{2,16}$')
MAX_IMG = 3 * 1024 * 1024
MAGIC = ((b'GIF8', '.gif'), (b'\x89PNG', '.png'), (b'\xff\xd8\xff', '.jpg'))


def gdir():
    d = os.path.join(os.path.dirname(CONFIG_PATH), 'guides')
    os.makedirs(d, exist_ok=True)
    return d


def _index_path():
    return os.path.join(gdir(), 'custom.json')


def _load_custom():
    try:
        with open(_index_path(), 'r', encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def _save_custom(items):
    tmp = _index_path() + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    os.replace(tmp, _index_path())


def _clean_steps(v):
    return [re.sub(r'\s+', ' ', str(x)).strip()[:200] for x in (v or [])][:8] if isinstance(v, list) else []


def _kid_of(g, builtin):
    """Bản cho lớp nhỏ: có sẵn cho hướng dẫn mặc định; hướng dẫn riêng dùng các bước 'kid_steps' nếu giáo viên nhập, không thì dùng bản thường."""
    if builtin:
        k = KID.get(g['id'])
        return dict(k) if k else None
    ks = _clean_steps(g.get('kid_steps')) if g.get('kid_steps') else []
    return {'title': g.get('kid_title') or g['title'], 'keys': g.get('keys', ''), 'steps': [x for x in ks if x] or g['steps'], 'tip': g.get('kid_tip') or g.get('tip', '')}


def _item_view(g, builtin):
    k = _kid_of(g, builtin)
    return {'id': g['id'], 'title': g['title'], 'keys': g.get('keys', ''), 'steps': g['steps'], 'tip': g.get('tip', ''), 'builtin': builtin, 'kid': k,
            'img': ('/assets/guide-%s.gif' % g['id']) if builtin else (g.get('file') and '/api/guide_img?id=' + g['id'] or '')}


def api_guides(_q=None):
    with GLOCK:
        custom = _load_custom()
    return {'items': [_item_view(g, True) for g in BUILTIN] + [_item_view(g, False) for g in custom]}


def api_guide_img(q):
    gid = str((q or {}).get('id') or '')
    with GLOCK:
        g = next((x for x in _load_custom() if x['id'] == gid), None)
    if not g or not g.get('file'):
        raise ApiError('Không có ảnh')
    with open(os.path.join(gdir(), os.path.basename(g['file'])), 'rb') as f:
        data = f.read()
    mime = {'.gif': 'image/gif', '.png': 'image/png', '.jpg': 'image/jpeg'}[os.path.splitext(g['file'])[1]]
    return {'data': 'data:%s;base64,%s' % (mime, base64.b64encode(data).decode())}


def api_guide_save(b):
    title = re.sub(r'\s+', ' ', str(b.get('title') or '')).strip()[:80]
    steps = [s for s in _clean_steps(b.get('steps')) if s]
    if not title or not steps:
        raise ApiError('Cần tiêu đề và ít nhất một bước')
    gid = str(b.get('id') or '')
    entry = {'kid_title': re.sub(r'\s+', ' ', str(b.get('kid_title') or '')).strip()[:80], 'kid_steps': [x for x in _clean_steps(b.get('kid_steps')) if x], 'kid_tip': re.sub(r'\s+', ' ', str(b.get('kid_tip') or '')).strip()[:200],
             'title': title, 'steps': steps, 'tip': re.sub(r'\s+', ' ', str(b.get('tip') or '')).strip()[:200], 'keys': re.sub(r'\s+', ' ', str(b.get('keys') or '')).strip()[:60]}
    raw = b.get('image')
    data, ext = None, ''
    if raw:
        try:
            data = base64.b64decode(str(raw).split(',')[-1], validate=False)
        except ValueError:
            raise ApiError('Ảnh không đọc được')
        ext = next((e for m, e in MAGIC if data.startswith(m)), '')
        if not ext or len(data) > MAX_IMG:
            raise ApiError('Ảnh phải là GIF/PNG/JPG và nhỏ hơn 3 MB')
    with GLOCK:
        items = _load_custom()
        old = next((x for x in items if x['id'] == gid), None) if gid else None
        if old:
            entry['id'], entry['file'] = old['id'], old.get('file', '')
            items[items.index(old)] = entry
        else:
            if len(items) >= 40:
                raise ApiError('Tối đa 40 hướng dẫn riêng, hãy xóa bớt')
            entry['id'], entry['file'] = 'c' + secrets.token_hex(4), ''
            items.append(entry)
        if data:
            if entry['file']:
                try:
                    os.remove(os.path.join(gdir(), os.path.basename(entry['file'])))
                except OSError:
                    pass
            entry['file'] = entry['id'] + ext
            with open(os.path.join(gdir(), entry['file']), 'wb') as f:
                f.write(data)
        _save_custom(items)
    return api_guides()


def api_guide_delete(b):
    gid = str(b.get('id') or '')
    with GLOCK:
        items = _load_custom()
        g = next((x for x in items if x['id'] == gid), None)
        if not g:
            raise ApiError('Không tìm thấy hướng dẫn')
        items.remove(g)
        if g.get('file'):
            try:
                os.remove(os.path.join(gdir(), os.path.basename(g['file'])))
            except OSError:
                pass
        _save_custom(items)
    return api_guides()


def _guide_bytes(gid, kidmode=False):
    """(thông tin, nội dung ảnh hoặc b'', phần mở rộng)."""
    if gid in BUILTIN_BY_ID:
        p = os.path.join(WEB_DIR, 'assets', 'guide-%s%s.gif' % (gid, 'kid' if kidmode else ''))
        if kidmode and not os.path.isfile(p):
            p = os.path.join(WEB_DIR, 'assets', 'guide-%s.gif' % gid)
        try:
            with open(p, 'rb') as f:
                return BUILTIN_BY_ID[gid], f.read(), '.gif'
        except OSError:
            return BUILTIN_BY_ID[gid], b'', ''
    with GLOCK:
        g = next((x for x in _load_custom() if x['id'] == gid), None)
    if not g:
        raise ApiError('Không tìm thấy hướng dẫn')
    if not g.get('file'):
        return g, b'', ''
    with open(os.path.join(gdir(), os.path.basename(g['file'])), 'rb') as f:
        return g, f.read(), os.path.splitext(g['file'])[1]


def job_guide(hosts, msg, data, ext):
    def one(h):
        try:
            hh = split_host_port(h)[0]
            if data:
                remote = STUDENT_ROOT + '\\guide\\' + msg['gid'] + ext
                try:
                    same = rfs_sha(hh, remote) == hashlib.sha256(data).hexdigest()
                except FileNotFoundError:
                    same = False
                if not same:
                    rfs_write(hh, remote, data)
            _inbox_write(h, msg)
        except Exception as e:  # noqa
            return False, 'không gửi được hướng dẫn (máy tắt hoặc chưa có Agent?): %s' % e
        return True, 'đã gửi hướng dẫn'
    pool_run(one, hosts, 'Gửi hướng dẫn thao tác')


def api_guide_send(b):
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào')
    gid = str(b.get('id') or '')
    if not ID_RE.match(gid):
        raise ApiError('Hướng dẫn không hợp lệ')
    kidmode = bool(b.get('kid'))
    g, data, ext = _guide_bytes(gid, kidmode)
    try:
        secs = max(0, min(900, int(b.get('secs') or 0)))
    except (TypeError, ValueError):
        secs = 0
    k = _kid_of(g, gid in BUILTIN_BY_ID) if kidmode else None
    src = dict(g, **k) if k else g
    send_gid = (gid + 'kid')[:16] if k else gid       # bản lớp nhỏ lưu riêng trên máy học sinh
    msg = {'type': 'guide', 'gid': send_gid, 'title': src['title'], 'keys': src.get('keys', ''), 'steps': src['steps'], 'tip': src.get('tip', ''), 'img': (send_gid + ext) if data else '', 'secs': secs, 'kid': bool(k)}
    start_job(job_guide, hosts, msg, data, ext)
    log('📘 Gửi hướng dẫn "%s" tới %d máy' % (g['title'], len(hosts)), 'head')
    return {'ok': True, 'count': len(hosts)}
