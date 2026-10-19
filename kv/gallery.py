# -*- coding: utf-8 -*-
"""Ảnh vi phạm trên máy giáo viên: đặt tên file (trường, lớp, học sinh, máy, ngày giờ), xếp thư mục theo ngày rồi lớp,
bộ sưu tập có bộ lọc và mở nhanh thư mục ảnh.

Cách xếp:  data\\evidence\\<yyyy-mm-dd>\\<Lớp>\\<Trường>_<Lớp>_<Học sinh>_<Máy>_<yyyy-mm-dd>_<HH-MM-SS>_<Loại>_<trang hoặc ứng dụng>.jpg
Phần nào không biết (chưa đặt tên trường, chưa có lịch dạy, chưa xếp chỗ) thì bỏ khỏi tên file; lớp không biết thì
thư mục là "Chua-ro-lop". Ảnh của bản cũ (data\\evidence\\<máy>\\...) vẫn giữ nguyên chỗ và vẫn hiện trong bộ sưu tập."""

import json
import os
import re
import subprocess

from .evidence import evidence_root
from .runtime import ApiError

NO_CLASS_DIR = 'Chua-ro-lop'
KIND_WORD = {'site': 'Web', 'ai': 'AI', 'app': 'App'}
_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def safe_part(s, n=60):
    """Một phần của tên file/thư mục: bỏ ký tự Windows không cho phép, gộp khoảng trắng, không kết thúc bằng dấu chấm."""
    s = _BAD.sub(' ', str(s or ''))
    s = re.sub(r'\s+', ' ', s).strip().replace('_', '-')
    return s[:n].rstrip(' .')


def evidence_dir_parts(date, cls):
    d = date if _DATE.match(str(date or '')) else 'Khong-ro-ngay'
    return [d, safe_part(cls, 40) or NO_CLASS_DIR]


def evidence_file_name(school, cls, student, host, date, tm, kind, name):
    parts = [safe_part(school, 50), safe_part(cls, 30), safe_part(student, 50), safe_part(host, 40),
             safe_part(date, 10), safe_part(str(tm or '').replace(':', '-'), 8), KIND_WORD.get(kind, 'App'), safe_part(name, 60)]
    base = '_'.join(p for p in parts if p)[:180].rstrip(' .') or 'vi-pham'
    return base + '.jpg'


def evidence_target(cfg, host, date, tm, kind, name, cls, student):
    """(đường dẫn đầy đủ, đường dẫn tương đối dạng a/b/c.jpg) cho ảnh mới; thêm (2), (3)... nếu trùng tên."""
    root = evidence_root()
    parts = evidence_dir_parts(date, cls)
    d = os.path.join(root, *parts)
    os.makedirs(d, exist_ok=True)
    fn = evidence_file_name(cfg.get('school_name', ''), cls, student, host, date, tm, kind, name)
    stem, n = fn[:-4], 1
    while os.path.exists(os.path.join(d, fn)):
        n += 1
        fn = '%s (%d).jpg' % (stem, n)
    return os.path.join(d, fn), '/'.join(parts + [fn])


def evidence_abs(rel):
    """Đường dẫn tương đối (a/b/c.jpg) thành đường dẫn đầy đủ, chỉ nhận đường dẫn nằm trong thư mục ảnh."""
    base = os.path.realpath(evidence_root())
    p = os.path.realpath(os.path.join(base, *[x for x in str(rel or '').split('/') if x not in ('', '.', '..')]))
    try:
        inside = os.path.commonpath([base, p]) == base
    except ValueError:
        inside = False
    return p if inside else None


# ---------------------------------------------------------------- bộ sưu tập
def _records():
    """Mọi bản ghi vi phạm có ảnh (kể cả đã bấm "Xóa danh sách": các file alerts-*.old), mới nhất trước, không trùng."""
    from .alerts import ALERT_FILE
    root = evidence_root()
    files = [os.path.join(root, ALERT_FILE)]
    try:
        files += sorted(os.path.join(root, f) for f in os.listdir(root) if f.startswith('alerts-') and f.endswith('.old'))
    except OSError:
        pass
    out, seen = [], set()
    for fp in files:
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except OSError:
            continue
        for ln in lines:
            try:
                e = json.loads(ln)
            except ValueError:
                continue
            if not isinstance(e, dict) or not e.get('img'):
                continue
            k = (e.get('host'), e.get('file'), e.get('img'))
            if k in seen:
                continue
            seen.add(k)
            out.append(e)
    out.sort(key=lambda e: e.get('ts') or 0, reverse=True)
    return out


def gallery_filter(items, f):
    q = str(f.get('q') or '').strip().lower()
    frm, to = str(f.get('from') or ''), str(f.get('to') or '')
    res = []
    for e in items:
        d = str(e.get('date') or '')
        if frm and d < frm or to and d > to:
            continue
        if f.get('cls') and (e.get('cls') or '') != f['cls'] and not (f['cls'] == '-' and not e.get('cls')):
            continue
        if f.get('host') and e.get('host') != f['host']:
            continue
        if f.get('student') and (e.get('student') or '') != f['student']:
            continue
        if f.get('type') and e.get('type') != f['type']:
            continue
        if q and q not in ' '.join(str(e.get(k) or '') for k in ('name', 'window', 'student', 'user', 'host', 'cls', 'text')).lower():
            continue
        res.append(e)
    return res


def api_gallery(q):
    items = _records()
    try:
        offset = max(0, int(q.get('offset') or 0))
        limit = max(1, min(300, int(q.get('limit') or 120)))
    except ValueError:
        offset, limit = 0, 120
    sel = gallery_filter(items, q)
    page = []
    for e in sel[offset:offset + limit]:
        p = evidence_abs(e['img'])
        it = {k: e.get(k, '') for k in ('host', 'pc', 'user', 'type', 'name', 'window', 'date', 'time', 'ts', 'img', 'text', 'cls', 'student', 'seat')}
        it['exists'] = bool(p and os.path.isfile(p))
        page.append(it)
    facets = {
        'dates': sorted({e.get('date') for e in items if e.get('date')}, reverse=True),
        'classes': sorted({e.get('cls') for e in items if e.get('cls')}),
        'hosts': sorted({e.get('host') for e in items if e.get('host')}),
        'students': sorted({e.get('student') for e in items if e.get('student')}),
        'no_class': any(not e.get('cls') for e in items),
    }
    return {'items': page, 'total': len(sel), 'all': len(items), 'offset': offset, 'facets': facets}


# ---------------------------------------------------------------- mở thư mục
def _open_in_explorer(path, select=False):
    if os.name != 'nt':
        raise ApiError('Chỉ mở được thư mục trên Windows. Đường dẫn: %s' % path)
    if select:
        subprocess.Popen(['explorer.exe', '/select,', path])  # mở thư mục và chọn sẵn file ảnh
    else:
        os.startfile(path)  # noqa


def api_evidence_open(b):
    """{'img': 'a/b/c.jpg'}: mở thư mục chứa ảnh và chọn sẵn ảnh.
    {'date': 'yyyy-mm-dd', 'cls': 'tên lớp'}: mở thư mục ngày (và lớp); chưa có thì mở thư mục gần nhất đang có."""
    root = evidence_root()
    if b.get('img'):
        p = evidence_abs(b['img'])
        if not p or not os.path.isfile(p):
            raise ApiError('Không còn ảnh này (có thể đã bị tự xóa vì quá hạn lưu)')
        _open_in_explorer(p, select=True)
        return {'ok': True, 'path': p}
    p = root
    date = str(b.get('date') or '')
    if _DATE.match(date):
        cand = os.path.join(root, date)
        if os.path.isdir(cand):
            p = cand
            cls = b.get('cls')
            if cls:
                c2 = os.path.join(cand, NO_CLASS_DIR if cls == '-' else (safe_part(cls, 40) or NO_CLASS_DIR))
                if os.path.isdir(c2):
                    p = c2
    _open_in_explorer(p)
    return {'ok': True, 'path': p}
