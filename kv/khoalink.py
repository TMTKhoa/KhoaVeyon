# -*- coding: utf-8 -*-
"""Kết nối với KhoaQuiz và KhoaTool (từ bản 3.10.0).

- Liên kết tài khoản KhoaQuiz bằng mã liên kết riêng của ứng dụng KhoaVeyon (KhoaQuiz → Cài đặt → Liên kết, chọn KhoaVeyon).
  Mã lưu trong data\\khoaquiz.json (Windows: chỉ tài khoản đang chạy, Administrators và SYSTEM đọc được), không bao giờ gửi lại giao diện.
- Lấy danh sách lớp từ KhoaQuiz (link/rosters), đối chiếu điểm danh với bài làm trong ngày (link/today),
  mở bài kiểm tra KhoaQuiz trên máy học sinh trong Chế độ thi (gắn số máy ?m=) và phát hiện bài nộp từ máy của bạn khác.
- Xuất file JSON tình hình buổi học để nhập vào Báo cáo buổi dạy / Điểm danh của KhoaTool.

Mọi lời gọi mạng có giới hạn thời gian và chỉ chạy khi giáo viên bấm nút: mất Internet thì báo lỗi, không ảnh hưởng việc khóa máy.
"""

import datetime
import json
import os
import re
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

from .paths import CONFIG_PATH, find_veyon_cli
from .remote import distribute_to_host, run_args
from .runtime import ApiError, CFG, CFG_LOCK, list_path, log, pool_run, split_host_port

KQ_FILE = os.path.join(os.path.dirname(CONFIG_PATH), 'khoaquiz.json')
KQ_DEFAULT_URL = 'https://khoaquiz.netlify.app'
KQ_LOCK = threading.RLock()
KQ = {'url': KQ_DEFAULT_URL, 'code': '', 'name': '', 'at': ''}
KQ_TIMEOUT = 15
# Tên miền trang kiểm tra KhoaQuiz cần (ngoài tên miền site): Firebase, phông chữ Google.
KQ_DOMAINS = ['www.gstatic.com', 'fonts.googleapis.com', 'fonts.gstatic.com',
              # Firebase: Realtime Database, Cloud Firestore, Storage, xác thực
              'firebaseio.com', 'firebasedatabase.app', 'firestore.googleapis.com', 'firebasestorage.googleapis.com',
              'firebaseapp.com', 'identitytoolkit.googleapis.com', 'securetoken.googleapis.com', 'googleapis.com',
              # MongoDB Atlas / Realm (nếu KhoaQuiz dùng)
              'mongodb-api.com', 'data.mongodb-api.com', 'realm.mongodb.com', 'services.cloud.mongodb.com']
OPEN_WEBSITE_UID = '8a11a75d-b3db-48b6-b9cb-f8422ddd5b0c'  # Veyon: "Open website"
START_APP_UID = 'da9ca56a-b2ad-4fff-8f8a-929b2927b442'     # Veyon: "Start application"


# ---------------------------------------------------------------- lưu mã liên kết
def kq_load():
    try:
        with open(KQ_FILE, 'r', encoding='utf-8') as f:
            d = json.load(f)
    except (OSError, ValueError):
        return
    if isinstance(d, dict):
        with KQ_LOCK:
            for k in KQ:
                if isinstance(d.get(k), str):
                    KQ[k] = d[k]


def kq_save():
    with KQ_LOCK:
        snap = dict(KQ)
    os.makedirs(os.path.dirname(KQ_FILE), exist_ok=True)
    new = not os.path.exists(KQ_FILE)
    with open(KQ_FILE, 'w', encoding='utf-8') as f:
        json.dump(snap, f, ensure_ascii=False)
    if new and os.name == 'nt':  # mã liên kết là chìa khóa đọc dữ liệu học sinh: hạn chế quyền đọc file
        user = os.environ.get('USERNAME', '')
        args = ['icacls', KQ_FILE, '/inheritance:r', '/grant:r', '*S-1-5-18:F', '*S-1-5-32-544:F'] + (['%s:F' % user] if user else [])
        run_args(args, 30)


def canon_code(v):
    """KQ-XXXXXX-XXXXXX-XXXXXX-XXXXXX (bỏ khoảng trắng, gạch, chữ thường). Sai dạng thì trả ''."""
    c = re.sub(r'[^A-Z0-9]', '', str(v or '').upper())
    if len(c) != 26 or not c.startswith('KQ'):
        return ''
    return 'KQ-' + '-'.join(c[2 + i:8 + i] for i in range(0, 24, 6))


def clean_url(v):
    t = str(v or '').strip().rstrip('/')
    if t and not re.match(r'^[a-z][a-z0-9+.-]*://', t, re.I):
        t = 'https://' + t
    u = urllib.parse.urlparse(t)
    if u.scheme not in ('http', 'https') or not u.hostname:
        return ''
    return '%s://%s%s' % (u.scheme, u.netloc, u.path.rstrip('/'))


def nk(name):
    return unicodedata.normalize('NFC', re.sub(r'\s+', ' ', str(name or '')).strip()).lower()


# ---------------------------------------------------------------- gọi KhoaQuiz
def kq_get(path, params=None, code=None, url=None, opener=None):
    """GET {url}/api/link/{path} với header x-link-token. Trả về dict; lỗi thì ném ApiError có thông báo dễ hiểu."""
    with KQ_LOCK:
        code = code or KQ['code']
        url = url or KQ['url']
    if not code:
        raise ApiError('Chưa liên kết KhoaQuiz (Cài đặt → Liên kết KhoaQuiz)')
    q = ('?' + urllib.parse.urlencode(params)) if params else ''
    req = urllib.request.Request('%s/api/link/%s%s' % (url, path, q), headers={'x-link-token': code, 'User-Agent': 'KhoaVeyon', 'Accept': 'application/json'})
    try:
        with (opener or urllib.request.urlopen)(req, timeout=KQ_TIMEOUT) as r:
            return json.loads(r.read().decode('utf-8') or '{}')
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode('utf-8')).get('error') or ''
        except Exception:  # noqa
            msg = ''
        if e.code == 404 and not msg:
            msg = 'KhoaQuiz chưa có chức năng này (hãy cập nhật KhoaQuiz lên bản mới)'
        raise ApiError('KhoaQuiz báo lỗi (%s): %s' % (e.code, msg or e.reason))
    except (urllib.error.URLError, OSError) as e:
        raise ApiError('Không kết nối được KhoaQuiz (%s). Máy giáo viên cần có Internet.' % getattr(e, 'reason', e))
    except ValueError:
        raise ApiError('KhoaQuiz trả về dữ liệu không đọc được. Kiểm tra lại địa chỉ KhoaQuiz.')


def api_kq_status(_q=None):
    with KQ_LOCK:
        return {'linked': bool(KQ['code']), 'url': KQ['url'], 'name': KQ['name'], 'at': KQ['at'],
                'hint': KQ['code'][-4:] if KQ['code'] else ''}


def api_kq_link(b):
    url = clean_url(b.get('url') or KQ_DEFAULT_URL)
    if not url:
        raise ApiError('Địa chỉ KhoaQuiz không hợp lệ (ví dụ https://khoaquiz.netlify.app)')
    code = canon_code(b.get('code'))
    if not code:
        raise ApiError('Mã liên kết không đúng dạng KQ-XXXXXX-XXXXXX-XXXXXX-XXXXXX')
    info = kq_get('info', code=code, url=url)
    with KQ_LOCK:
        KQ.update({'url': url, 'code': code, 'name': str(info.get('name') or ''), 'at': time.strftime('%d/%m/%Y %H:%M')})
    kq_save()
    log('Đã liên kết KhoaQuiz: tài khoản %s (%s)' % (KQ['name'], url), 'ok')
    return api_kq_status()


def api_kq_unlink(_b=None):
    with KQ_LOCK:
        KQ.update({'code': '', 'name': '', 'at': ''})
    kq_save()
    log('Đã hủy liên kết KhoaQuiz trên máy này (muốn thu hồi hẳn mã, vào KhoaQuiz → Cài đặt → Liên kết)', 'ok')
    return api_kq_status()


# ---------------------------------------------------------------- danh sách lớp từ KhoaQuiz
def rosters_to_classes(d, sid=''):
    """Kết quả link/rosters → {lớp: [học sinh]}. Nhiều trường trùng tên lớp mà không chọn trường thì báo lỗi."""
    from .school import _cls_norm
    out, owner = {}, {}
    for c in d.get('classes') or []:
        if sid and c.get('sid') != sid:
            continue
        cls = _cls_norm(c.get('cls'))[:20]
        names = [re.sub(r'\s+', ' ', str(n)).strip()[:80] for n in c.get('students') or [] if str(n).strip()]
        if not cls or not names:
            continue
        if cls in owner and owner[cls] != c.get('sid'):
            raise ApiError('Lớp %s có ở nhiều trường trong KhoaQuiz: hãy chọn một trường để lấy danh sách' % cls)
        owner[cls] = c.get('sid')
        out[cls] = names
    if not out:
        raise ApiError('KhoaQuiz chưa có danh sách học sinh nào%s (KhoaQuiz → Cài đặt → danh sách học sinh)' % (' cho trường đã chọn' if sid else ''))
    return out


def api_kq_rosters_preview(_q=None):
    d = kq_get('rosters')
    schools = [{'id': s.get('id'), 'name': s.get('name'),
                'classes': sum(1 for c in d.get('classes') or [] if c.get('sid') == s.get('id'))} for s in d.get('schools') or []]
    return {'schools': [s for s in schools if s['classes']], 'total': len(d.get('classes') or [])}


def api_kq_rosters_import(b):
    from .school_api import school_merge_classes, api_school
    data = rosters_to_classes(kq_get('rosters'), str(b.get('sid') or ''))
    new, upd, n = school_merge_classes(data, 'KhoaQuiz')
    out = api_school()
    out['imported'] = {'new': new, 'updated': upd, 'students': n}
    return out


# ---------------------------------------------------------------- đối chiếu điểm danh với bài làm KhoaQuiz
def compare_rows(roster, att, lay, items, seat_no_of):
    """Thuần dữ liệu (dễ kiểm thử). roster: tên trong KhoaVeyon; att: att_state(); lay: sơ đồ; items: các mục link/today của lớp;
    seat_no_of(host) → số máy. Trả về (rows, extras)."""
    did = {}
    for it in items:
        for st in it.get('students') or []:
            k = nk(st.get('name'))
            if k and (k not in did or (st.get('score') or 0) > (did[k].get('score') or 0)):
                did[k] = dict(st, title=it.get('title') or '')
    seats = att.get('seats') or {}                       # chỗ hôm nay (đã dồn chỗ): {số máy: tên}
    seat_of = {nk(v): int(k) for k, v in seats.items() if str(k).isdigit()}
    absent = {nk(n) for n in att.get('absent') or []}
    offline = {int(x) for x in att.get('offline') or [] if str(x).isdigit()}
    rows = []
    for name in roster:
        k = nk(name)
        q = did.get(k)
        r = {'name': name, 'seat': seat_of.get(k, 0), 'kv_absent': k in absent, 'did': bool(q),
             'score': q.get('score') if q else None, 'title': q.get('title') if q else '', 'm': (q or {}).get('m', ''), 'flags': []}
        if r['seat'] and r['seat'] in offline:
            r['flags'].append({'code': 'offline', 'text': 'máy %d không bật / mất kết nối Veyon' % r['seat']})
        if not q and not r['kv_absent']:
            r['flags'].append({'code': 'suggest_absent', 'text': 'không làm bài KhoaQuiz, đang được tính có mặt'})
        if q and r['kv_absent']:
            r['flags'].append({'code': 'did_but_absent', 'text': 'có bài làm KhoaQuiz nhưng đang bị đánh vắng'})
        if q and r['m']:
            no = seat_no_of(r['m'])
            owner = seats.get(str(no), '') if no else ''
            if owner and nk(owner) != k:
                r['flags'].append({'code': 'other_machine', 'text': 'nộp bài từ máy %d (%s), là chỗ của %s' % (no, r['m'], owner)})
            elif no and r['seat'] and no != r['seat'] and not owner:
                r['flags'].append({'code': 'moved', 'text': 'làm bài ở máy %d thay vì máy %d' % (no, r['seat'])})
        rows.append(r)
    known = {nk(n) for n in roster}
    extras = [dict(v) for kk, v in did.items() if kk not in known]
    return rows, extras


def api_kq_compare(q):
    from .school import _cls_norm, LAYOUT_DEFAULT, SCHOOL, SCHOOL_LOCK
    from .seating import att_state, school_seat_no
    cls = _cls_norm(q.get('cls'))
    date = str(q.get('date') or datetime.date.today().strftime('%Y-%m-%d'))
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise ApiError('Ngày không hợp lệ')
    with SCHOOL_LOCK:
        if cls not in SCHOOL['classes']:
            raise ApiError('Lớp không có trong danh sách lớp')
        roster = list(SCHOOL['classes'][cls])
        lay = dict(LAYOUT_DEFAULT, **(SCHOOL['layouts'].get(cls) or {}))
    d = kq_get('today', {'date': date})
    items = [it for it in d.get('items') or [] if _cls_norm(it.get('cls')) == cls]
    att = att_state(cls)
    rows, extras = compare_rows(roster, att, lay, items, lambda h: school_seat_no(split_host_port(h)[0], lay))
    cnt = {c: sum(1 for r in rows if any(f['code'] == c for f in r['flags'])) for c in ('suggest_absent', 'did_but_absent', 'other_machine', 'moved', 'offline')}
    return {'cls': cls, 'date': date, 'titles': [it.get('title') or '' for it in items], 'rows': rows, 'extras': extras,
            'did': sum(1 for r in rows if r['did']), 'total': len(rows), 'counts': cnt,
            'note': '' if items else 'KhoaQuiz chưa có bài làm nào của lớp %s trong ngày %s' % (cls, date)}


# ---------------------------------------------------------------- trò chơi KhoaQuiz đang diễn ra (phòng chờ, bắt đầu)
LIVE_STATE = {}     # {'pin', 'phase', 'auto': {tên: lớp}}: nhớ lần hỏi trước để biết lúc giáo viên bấm bắt đầu
LIVE_LOCK = threading.RLock()
LIVE_POLL = 6


def live_rows(roster, att, live, seat_no_of):
    """Thuần dữ liệu. live: kết quả link/live (players: [{name, m, online}]). Trả về (rows, extras).
    Mỗi dòng: học sinh trong danh sách lớp, đã vào phòng chưa, máy đang ngồi, có đúng chỗ của em không."""
    players = {}
    for p in live.get('players') or []:
        k = nk(p.get('name'))
        if k and (k not in players or p.get('m')):
            players[k] = p
    seats = att.get('seats') or {}
    base = att.get('base_seats') or {}
    seat_of = {nk(v): int(k) for k, v in seats.items() if str(k).isdigit()}
    own_of = {nk(v): int(k) for k, v in base.items() if str(k).isdigit()}
    absent = {nk(n) for n in att.get('absent') or []}
    rows = []
    for name in roster:
        k = nk(name)
        q = players.get(k)
        r = {'name': name, 'seat': seat_of.get(k, 0), 'own': own_of.get(k, 0), 'kv_absent': k in absent, 'joined': bool(q),
             'online': (q or {}).get('online', True) if q else False, 'm': (q or {}).get('m', ''), 'm_seat': 0, 'flags': []}
        if not q and not r['kv_absent']:
            r['flags'].append({'code': 'not_joined', 'text': 'chưa vào phòng chơi, đang được tính có mặt'})
        if q and r['kv_absent']:
            r['flags'].append({'code': 'joined_but_absent', 'text': 'đã vào phòng chơi nhưng đang bị đánh vắng'})
        if q and r['m']:
            no = seat_no_of(r['m'])
            r['m_seat'] = no or 0
            owner = seats.get(str(no), '') if no else ''
            if owner and nk(owner) != k:
                r['flags'].append({'code': 'other_machine', 'text': 'đang ngồi máy %d (%s), là chỗ của %s' % (no, r['m'], owner)})
            elif no and r['seat'] and no != r['seat'] and not owner:
                r['flags'].append({'code': 'moved', 'text': 'đang ngồi máy %d thay vì máy %d' % (no, r['seat'])})
        rows.append(r)
    known = {nk(n) for n in roster}
    extras = [dict(v) for kk, v in players.items() if kk not in known]
    return rows, extras


def _live_class(live, cls_arg=''):
    from .school import _cls_norm, SCHOOL, SCHOOL_LOCK
    with SCHOOL_LOCK:
        for c in (cls_arg, live.get('cls')):
            c = _cls_norm(c) if c else ''
            if c and c in SCHOOL['classes']:
                return c
    return ''


def _live_machine_seat(host_or_name, lay):
    from .seating import school_seat_no
    return school_seat_no(split_host_port(host_or_name)[0], lay)


def api_kq_live(q):
    from .school import LAYOUT_DEFAULT, SCHOOL, SCHOOL_LOCK
    from .seating import att_state
    live = kq_get('live')
    if not live.get('active'):
        return {'active': False, 'auto': bool(SCHOOL.get('kq_game_absent', True))}
    cls = _live_class(live, str(q.get('cls') or ''))
    out = {'active': True, 'phase': live.get('phase'), 'pin': live.get('pin'), 'title': live.get('title') or '', 'cls': cls,
           'live_cls': live.get('cls') or '', 'age': live.get('ageSec', 0), 'joined_total': len(live.get('players') or []),
           'auto': bool(SCHOOL.get('kq_game_absent', True)), 'rows': [], 'extras': [], 'counts': {}}
    if not cls:
        out['note'] = 'Lớp "%s" của phòng chơi không có trong danh sách lớp KhoaVeyon' % (live.get('cls') or '(không ghi lớp)')
        return out
    with SCHOOL_LOCK:
        roster = list(SCHOOL['classes'][cls])
        lay = dict(LAYOUT_DEFAULT, **(SCHOOL['layouts'].get(cls) or {}))
    att = att_state(cls)
    att['base_seats'] = lay.get('seats') or {}
    rows, extras = live_rows(roster, att, live, lambda h: _live_machine_seat(h, lay))
    out['rows'], out['extras'] = rows, extras
    out['counts'] = {c: sum(1 for r in rows if any(f['code'] == c for f in r['flags'])) for c in ('not_joined', 'joined_but_absent', 'other_machine', 'moved')}
    out['joined'] = sum(1 for r in rows if r['joined'])
    out['total'] = len(rows)
    return out


def live_apply(live, cls, state, set_attendance):
    """Thuần logic của bước tự động (dễ kiểm thử). state: LIVE_STATE. Trả về danh sách thao tác đã làm [(act, [tên])].
    - Lúc phòng chuyển từ "chờ" sang "đã bắt đầu": đánh vắng em chưa vào phòng.
    - Sau đó em nào bị đánh vắng tự động mà vào muộn thì đánh dấu có mặt lại."""
    pin, phase = live.get('pin') or '', live.get('phase') or ''
    prev_pin, prev_phase = state.get('pin'), state.get('phase')
    joined = {nk(p.get('name')) for p in live.get('players') or []}
    done = []
    if pin != prev_pin:
        state['auto'] = {}
    if prev_pin == pin and prev_phase == 'lobby' and phase != 'lobby' and cls:
        from .school import SCHOOL, SCHOOL_LOCK
        with SCHOOL_LOCK:
            roster = list(SCHOOL['classes'].get(cls, []))
        absent_now = {nk(n) for n in (SCHOOL['attendance'].get('%s|%s' % (datetime.date.today().strftime('%Y-%m-%d'), cls)) or {}).get('absent', [])}
        miss = [n for n in roster if nk(n) not in joined and nk(n) not in absent_now]
        if miss and joined:
            set_attendance(cls, 'absent_many', miss)
            state.setdefault('auto', {}).update({n: cls for n in miss})
            done.append(('absent', miss))
    elif phase != 'lobby' and prev_pin == pin:
        back = [n for n in list((state.get('auto') or {}).keys()) if nk(n) in joined]
        if back:
            for n in back:
                set_attendance(cls, 'toggle', [n])
                state['auto'].pop(n, None)
            done.append(('present', back))
    state['pin'], state['phase'] = pin, phase
    return done


def _set_attendance(cls, act, names):
    from .attendance import api_school_attendance_set
    if act == 'absent_many':
        api_school_attendance_set({'cls': cls, 'action': 'absent_many', 'names': names})
    else:
        for n in names:
            api_school_attendance_set({'cls': cls, 'action': 'toggle', 'name': n})


def live_tick():
    from .school import SCHOOL
    with KQ_LOCK:
        if not KQ['code']:
            return
    live = kq_get('live')
    if not live.get('active'):
        with LIVE_LOCK:
            LIVE_STATE.clear()
        return
    cls = _live_class(live)
    with LIVE_LOCK:
        if not SCHOOL.get('kq_game_absent', True):
            LIVE_STATE.update({'pin': live.get('pin'), 'phase': live.get('phase'), 'auto': {}})
            return
        before = live.get('phase')
        done = live_apply(live, cls, LIVE_STATE, _set_attendance)
    for act, names in done:
        if act == 'absent':
            log('Trò chơi KhoaQuiz (lớp %s) đã bắt đầu: đánh vắng %d em chưa vào phòng: %s' % (cls, len(names), ', '.join(names)), 'head')
        else:
            log('Trò chơi KhoaQuiz (lớp %s): %s vào muộn nên đánh dấu có mặt lại' % (cls, ', '.join(names)), 'ok')
    if not cls and before != 'lobby' and not LIVE_STATE.get('warned') == live.get('pin'):
        LIVE_STATE['warned'] = live.get('pin')
        log('Trò chơi KhoaQuiz: lớp "%s" không có trong danh sách lớp nên không tự đánh vắng được' % (live.get('cls') or ''), 'warn')


def live_loop():
    while True:
        try:
            live_tick()
        except Exception:  # noqa: lỗi mạng, chưa liên kết...: bỏ qua, hỏi lại lần sau
            pass
        time.sleep(LIVE_POLL)


def api_kq_live_set(b):
    from .school import SCHOOL, school_save
    SCHOOL['kq_game_absent'] = bool(b.get('auto'))
    school_save()
    with LIVE_LOCK:
        LIVE_STATE.clear()
    return {'ok': True, 'auto': SCHOOL['kq_game_absent']}


def api_kq_live_open(b):
    """Mở trang vào chơi (đã gõ sẵn mã PIN và gắn số máy ?m=) trên các máy học sinh."""
    from .runtime import clean_hosts, start_job
    live = kq_get('live')
    if not live.get('active') or live.get('phase') != 'lobby' or not live.get('pin'):
        raise ApiError('Chưa có phòng chơi nào đang chờ học sinh vào (hãy tạo phòng trong KhoaQuiz trước)')
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào để mở')
    with KQ_LOCK:
        base = KQ['url'].rstrip('/')
    start_job(job_kq_open, hosts, '%s/?pin=%s' % (base, live['pin']))
    return {'ok': True, 'pin': live['pin']}


# ---------------------------------------------------------------- bài kiểm tra KhoaQuiz trong Chế độ thi
def api_kq_exams(_q=None):
    return {'items': kq_get('exams').get('items') or []}


def clean_exam_url(v):
    t = str(v or '').strip()
    if not t:
        return ''
    u = urllib.parse.urlparse(t)
    if u.scheme not in ('http', 'https') or not u.hostname or len(t) > 500:
        raise ApiError('Link bài kiểm tra phải bắt đầu bằng https://')
    return t


def machine_id(host):
    """Số máy gắn vào link (?m=): tên máy hoặc IP, bỏ cổng, chỉ giữ ký tự KhoaQuiz nhận."""
    h = split_host_port(str(host))[0]
    return re.sub(r'[^A-Za-z0-9._-]', '', h)[:40]


def exam_url_for(url, host):
    m = machine_id(host)
    if not m:
        return url
    u = urllib.parse.urlparse(url)
    qs = [(k, v) for k, v in urllib.parse.parse_qsl(u.query, keep_blank_values=True) if k != 'm'] + [('m', m)]
    return urllib.parse.urlunparse(u._replace(query=urllib.parse.urlencode(qs)))


def allow_domains_for(url):
    host = (urllib.parse.urlparse(url).hostname or '').lower()
    return [d for d in [host] + KQ_DOMAINS if d]


def job_kq_allow(hosts, url):
    """Thêm tên miền KhoaQuiz vào AllowPage.xlsx (nếu thiếu) rồi gửi file xuống máy học sinh, trước bước "chỉ trang cho phép"."""
    from .excel_lists import read_list, write_list
    path = list_path('allow')
    rows = read_list(path)
    def norm(d):
        d = d.strip().lower()
        return d[4:] if d.startswith('www.') else d
    have = {norm(r[0]) for r in rows}
    add = [d for d in allow_domains_for(url) if norm(d) not in have]
    if not add:
        log('Chế độ thi: AllowPage.xlsx đã có đủ tên miền KhoaQuiz', 'ok')
        return
    write_list(path, 'allow', rows + [(d, 'KhoaQuiz - tự thêm bởi Chế độ thi') for d in add])
    log('Chế độ thi: đã thêm %s vào AllowPage.xlsx' % ', '.join(add), 'ok')
    with CFG_LOCK:
        target = CFG['dist_target']

    def one(h):
        try:
            distribute_to_host(h, [path], target)
            return True, 'đã gửi AllowPage.xlsx mới'
        except Exception as e:  # noqa
            return False, 'không gửi được AllowPage.xlsx: %s' % e
    pool_run(one, hosts, 'Gửi AllowPage.xlsx (thêm KhoaQuiz)')


def veyon_open_url(cli, host, url, runner=run_args):
    """Mở trang web trên máy học sinh bằng Veyon "Open website"; không được thì thử "Start application" với explorer.exe."""
    rc, out = runner([cli, 'feature', 'start', host, OPEN_WEBSITE_UID, json.dumps({'websiteUrls': url})], 40)
    if rc == 0:
        return True, 'đã mở bài kiểm tra'
    rc2, out2 = runner([cli, 'feature', 'start', host, START_APP_UID, json.dumps({'applications': ['explorer.exe ' + url]})], 40)
    if rc2 == 0:
        return True, 'đã mở bài kiểm tra (qua explorer.exe)'
    return False, 'Veyon không mở được trang: (%s) %s' % (rc, (out or out2)[-200:])


def job_kq_open(hosts, url):
    with CFG_LOCK:
        cli = find_veyon_cli(CFG['veyon_cli'])
    log('>>> Mở bài kiểm tra KhoaQuiz trên %d máy (link gắn số máy ?m=)' % len(hosts), 'head')
    pool_run(lambda h: veyon_open_url(cli, h, exam_url_for(url, h)), hosts, 'Mở bài kiểm tra KhoaQuiz')


# ---------------------------------------------------------------- xuất cho KhoaTool
def build_khoatool_export(date, classes, cfg_hosts, online, report):
    """Thuần dữ liệu. classes: [(lớp, att_state, sơ đồ)], online: {máy: bật?}, report: report_build('today').
    Trả về dict theo định dạng KhoaTool đọc được (app=KhoaVeyon, format=1)."""
    from .school import SCHOOL, SCHOOL_LOCK
    viol = {}
    for r in report.get('by_student') or []:
        if r.get('student') and not r['student'].startswith('('):
            viol.setdefault(r.get('cls') or '', []).append({'name': r['student'], 'count': r['count'],
                                                            'top': ['%s (%d)' % (t['name'], t['count']) for t in r.get('top') or []]})
    out_cls, machines = [], {}
    for cls, att, lay in classes:
        base = {str(k): v for k, v in (lay.get('seats') or {}).items()}
        off = {int(x) for x in att.get('offline') or [] if str(x).isdigit()}
        broken = {int(x) for x in lay.get('broken') or []}
        for no in broken:
            machines.setdefault(no, 'hỏng (sơ đồ KhoaVeyon)')
        moved = []
        for name, to in (att.get('moves') or {}).items():
            frm = next((int(k) for k, v in base.items() if v == name and k.isdigit()), 0)
            reason = 'broken' if frm in broken or frm in off else 'other'
            if frm in off:
                machines.setdefault(frm, 'không bật / mất kết nối Veyon')
            moved.append({'name': name, 'from': frm, 'to': to, 'reason': reason})
        out_cls.append({'cls': cls, 'absent': list(att.get('absent') or []), 'moved': moved,
                        'shares': [{'name': n, 'seat': s} for n, s in (att.get('shares') or {}).items()],
                        'violators': viol.pop(cls, [])})
    for cls, lst in viol.items():  # lớp có vi phạm nhưng hôm nay chưa điểm danh trong KhoaVeyon
        if cls:
            out_cls.append({'cls': cls, 'absent': [], 'moved': [], 'shares': [], 'violators': lst})
    on = [h for h in cfg_hosts if online.get(h)]
    off_hosts = [h for h in cfg_hosts if h in online and not online[h]]
    if cfg_hosts:
        vtext = 'Veyon kết nối %d/%d máy' % (len(on), len(cfg_hosts)) + ('; không kết nối: %s' % ', '.join(off_hosts[:15]) if off_hosts else '')
    else:
        vtext = ''
    with SCHOOL_LOCK:
        teacher, subject = SCHOOL.get('teacher', ''), SCHOOL.get('subject', '')
    return {'app': 'KhoaVeyon', 'format': 1, 'date': date, 'generated': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'teacher': teacher, 'subject': subject, 'veyon': {'total': len(cfg_hosts), 'online': len(on), 'offline': off_hosts, 'text': vtext},
            'machines': [{'no': str(no), 'issue': iss} for no, iss in sorted(machines.items())], 'classes': out_cls,
            'violations_total': report.get('episodes', 0)}


def api_kt_export(_b=None):
    from .network import tcp_open
    from .reports import report_build
    from .school import LAYOUT_DEFAULT, SCHOOL, SCHOOL_LOCK
    from .seating import att_state, att_today
    from concurrent.futures import ThreadPoolExecutor
    date = att_today()
    with SCHOOL_LOCK:
        keys = [k.split('|', 1)[1] for k in SCHOOL['attendance'] if k.startswith(date + '|')]
        layouts = {c: dict(LAYOUT_DEFAULT, **(SCHOOL['layouts'].get(c) or {})) for c in keys}
    classes = [(c, att_state(c), layouts[c]) for c in sorted(set(keys)) if c in layouts]
    with CFG_LOCK:
        hosts = [str(h).strip() for h in CFG.get('hosts') or [] if str(h).strip()]
    with ThreadPoolExecutor(max_workers=32) as ex:
        res = list(ex.map(lambda h: tcp_open(*split_host_port(h), 0.8), hosts))
    online = dict(zip(hosts, res))
    data = build_khoatool_export(date, classes, hosts, online, report_build('today'))
    folder = os.path.join(os.path.dirname(CONFIG_PATH), 'reports')
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, 'khoaveyon-%s.json' % date)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    log('Đã xuất tình hình buổi học cho KhoaTool: %s (%d lớp, %d máy hỏng)' % (path, len(data['classes']), len(data['machines'])), 'ok')
    return {'ok': True, 'path': path, 'name': os.path.basename(path), 'data': data}
