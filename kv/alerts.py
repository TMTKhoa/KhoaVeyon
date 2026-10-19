# -*- coding: utf-8 -*-
"""Báo động vi phạm ở máy giáo viên: nhận ảnh, gom báo động trùng, ghi lịch sử, tiếng bíp."""

import json
import os
import re
import shutil
import threading
import time

from .config import save_config
from .evidence import evidence_root, WATCH_REMOTE_DIR
from .gallery import evidence_target
from .network import tcp_open
from .privacy import privacy_status
from .remote import unc_target
from .runtime import CFG, CFG_LOCK, log
from .school import school_class_at
from .school_api import school_brief
from .seating import school_student_for
from .updater import update_brief


# ---------------------------------------------------------------- báo động vi phạm: tự nhận ảnh từ máy học sinh về máy giáo viên
ALERTS = []                 # danh sách vi phạm (cũ -> mới), mỗi mục có 'id' tăng dần
ALERT_LOCK = threading.Lock()
ALERT_SEQ = [0]
ALERT_SEEN = set()          # (máy, tên file) đã xử lý, tránh báo trùng
HOST_ONLINE = {}
ALERT_FILE = 'alerts.jsonl'
ALERT_CSV = 'violations.csv'
ALERT_MAX = 500
ALERT_PER_CYCLE = 20        # tối đa số vi phạm nhận từ một máy trong một lượt (chống bị học sinh làm ngập)
ALERT_MAX_IMG = 15 * 1024 * 1024
LEGACY_JPG = re.compile(r'^(?P<pc>[^_]+)_(?P<d>\d{8})-(?P<t>\d{6})_(?P<kind>site|app)_(?P<name>.+)\.jpg$')
SAFE_JPG = re.compile(r'^[\w.\-]{1,200}\.jpg$')


def watch_hosts_set(host, on):
    with CFG_LOCK:
        cur = [h for h in (CFG.get('watch_hosts') or []) if h != host]
        if on:
            cur.append(host)
        if cur != (CFG.get('watch_hosts') or []):
            CFG['watch_hosts'] = cur
            save_config(CFG)
    HOST_ONLINE.pop(host, None)


def hn_of(cfg, host):
    """Tên máy để ghi vào tên file ảnh: tên giáo viên tự đặt, không có thì tên PC dò được, không có nữa thì IP."""
    return (cfg.get('host_names') or {}).get(host) or (cfg.get('host_auto_names') or {}).get(host) or host


def _clip(v, n):
    return re.sub(r'[\x00-\x1f]', ' ', str(v or ''))[:n].strip()


def alert_text(kind, name):
    if kind == 'ai':
        return 'Cố dùng công cụ AI: %s' % name
    return ('Truy cập trang web ngoài danh sách: %s' if kind == 'site' else 'Mở ứng dụng ngoài danh sách: %s') % name


def alerts_load():
    try:
        with open(os.path.join(evidence_root(), ALERT_FILE), 'r', encoding='utf-8') as f:
            lines = f.readlines()[-ALERT_MAX:]
    except OSError:
        return
    for ln in lines:
        try:
            e = json.loads(ln)
        except ValueError:
            continue
        if not isinstance(e, dict):
            continue
        ALERT_SEQ[0] += 1
        e['id'] = ALERT_SEQ[0]
        ALERTS.append(e)
        ALERT_SEEN.add((e.get('host'), e.get('file')))


def _csv_cell(v):
    v = str(v)
    if v[:1] in ('=', '+', '-', '@'):  # tránh Excel hiểu nhầm là công thức
        v = "'" + v
    return '"%s"' % v.replace('"', '""')


def alert_push(e):
    with ALERT_LOCK:
        ALERT_SEQ[0] += 1
        e['id'] = ALERT_SEQ[0]
        ALERTS.append(e)
        if len(ALERTS) > ALERT_MAX:
            del ALERTS[:len(ALERTS) - ALERT_MAX]
        ALERT_SEEN.add((e['host'], e['file']))
        root = evidence_root()
        try:
            rec = {k: v for k, v in e.items() if k != 'id'}
            with open(os.path.join(root, ALERT_FILE), 'a', encoding='utf-8') as f:
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            csv_path = os.path.join(root, ALERT_CSV)
            new = not os.path.exists(csv_path)
            with open(csv_path, 'a', encoding='utf-8-sig', newline='') as f:
                if new:
                    f.write('Date,Time,PCName,User,Type,Name,Window,File\r\n')
                f.write(','.join(_csv_cell(x) for x in (e['date'], e['time'], e['host'], e['user'], e['type'], e['name'], e['window'], e['img'])) + '\r\n')
        except OSError:
            pass


def _rm(path):
    try:
        os.remove(path)
    except OSError:
        pass


def alert_collect_host(cfg, host):
    """Lấy ảnh vi phạm mới từ máy học sinh về máy giáo viên rồi tạo báo động. Trả về (ok, mô tả, số vi phạm mới)."""
    if not tcp_open(host, 445, 1.5):
        return False, 'không kết nối được (máy tắt hoặc mạng lỗi)', 0
    src = unc_target(host, WATCH_REMOTE_DIR)
    try:
        names = os.listdir(src)
    except FileNotFoundError:
        return True, 'chưa có ảnh', 0
    except OSError as e:
        return False, str(e), 0
    jobs = []   # (tên file ảnh, siêu dữ liệu, các file nguồn cần xóa)
    lower = {n.lower(): n for n in names}
    for n in sorted(names):
        low = n.lower()
        if low.endswith('.jpg.ok'):  # biên nhận do máy giáo viên ghi (học sinh không xóa được), dọn cái cũ hơn 2 phút
            try:
                if time.time() - os.path.getmtime(os.path.join(src, n)) > 120:
                    _rm(os.path.join(src, n))
            except OSError:
                pass
            continue
        if low.endswith('.json'):
            try:
                with open(os.path.join(src, n), 'r', encoding='utf-8-sig') as f:
                    m = json.load(f)
                if not isinstance(m, dict):
                    raise ValueError
            except (OSError, ValueError):
                try:  # chưa ghi xong thì lần sau thử lại; hỏng quá 60 giây thì dọn đi
                    if time.time() - os.path.getmtime(os.path.join(src, n)) > 60:
                        _rm(os.path.join(src, n))
                except OSError:
                    pass
                continue
            jpg = str(m.get('file') or '')
            if jpg != os.path.basename(jpg) or not SAFE_JPG.match(jpg):  # tên file lạ (đường dẫn, ký tự đặc biệt): bỏ
                _rm(os.path.join(src, n))
                continue
            jobs.append((jpg, m, [n]))
        elif low.endswith('.jpg') and low[:-4] + '.json' not in lower:
            lm = LEGACY_JPG.match(n)  # ảnh do bản giám sát cũ chụp, không có file .json
            try:
                old_enough = time.time() - os.path.getmtime(os.path.join(src, n)) > 20
            except OSError:
                continue
            if lm and old_enough and SAFE_JPG.match(n):
                d, t = lm.group('d'), lm.group('t')
                jobs.append((n, {'pc': lm.group('pc'), 'type': lm.group('kind'), 'name': lm.group('name'),
                                 'date': '%s-%s-%s' % (d[:4], d[4:6], d[6:]), 'time': '%s:%s:%s' % (t[:2], t[2:4], t[4:]),
                                 'window': ''}, []))
    new = 0
    for jpg, m, extra in jobs[:ALERT_PER_CYCLE]:
        key = (host, jpg)
        jfile = [os.path.join(src, x) for x in extra]
        if key in ALERT_SEEN:   # đã báo rồi, chỉ dọn file còn sót
            for x in jfile + [os.path.join(src, jpg)]:
                _rm(x)
            continue
        kind = m.get('type') if m.get('type') in ('site', 'ai') else 'app'
        name = _clip(m.get('name'), 200)
        date = _clip(m.get('date'), 10)
        tm = _clip(m.get('time'), 8)
        try:
            ts = time.mktime(time.strptime(date + ' ' + tm, '%Y-%m-%d %H:%M:%S'))
        except ValueError:
            ts = time.time()
            date, tm = time.strftime('%Y-%m-%d'), time.strftime('%H:%M:%S')
        cls_now = school_class_at(ts)
        stu, seat = school_student_for(host, cls_now)
        img = ''
        sp = os.path.join(src, jpg)
        try:
            if os.path.isfile(sp) and os.path.getsize(sp) <= ALERT_MAX_IMG:
                # data\evidence\<ngày>\<lớp>\<Trường>_<Lớp>_<Học sinh>_<Máy>_<ngày>_<giờ>_<loại>_<trang>.jpg
                dest, img = evidence_target(cfg, hn_of(cfg, host), date, tm, kind, name, cls_now, stu)
                shutil.copy2(sp, dest)
        except OSError:
            continue  # chưa chép được, lần sau thử lại
        alert_push({'host': host, 'pc': _clip(m.get('pc'), 64), 'user': _clip(m.get('user'), 64), 'type': kind,
                    'name': name, 'window': _clip(m.get('window'), 300), 'date': date, 'time': tm, 'ts': ts,
                    'file': jpg, 'img': img, 'text': alert_text(kind, name), 'cls': cls_now, 'student': stu, 'seat': seat})
        for x in jfile + [sp]:
            _rm(x)
        if cfg.get('watch_notify_student', True):
            write_receipt(src, jpg)
        new += 1
        log('[%s] VI PHẠM: %s (%s %s)' % (host, alert_text(kind, name), date, tm), 'warn')
    return True, 'ok', new


def write_receipt(src, jpg):
    """Biên nhận "máy giáo viên đã nhận ảnh này": file <ảnh>.jpg.ok cạnh chỗ ảnh vừa lấy trên máy học sinh.
    Script giám sát chỉ báo cho học sinh "đã gửi cho giáo viên" khi thấy biên nhận, rồi tự xóa nó."""
    try:
        with open(os.path.join(src, jpg + '.ok'), 'w', encoding='ascii') as f:
            f.write(time.strftime('%Y-%m-%d %H:%M:%S'))
    except OSError:
        pass


BEEP_LAST = {}


def alert_should_beep(events, gap):
    """Một học sinh mở cùng một trang liên tục chỉ bíp một lần trong `gap` giây; trang khác hoặc máy khác thì bíp riêng."""
    now = time.time()
    beep = False
    for e in events:
        k = (e['host'], e['type'], e['name'])
        if now - BEEP_LAST.get(k, 0) >= gap:
            beep = True
        BEEP_LAST[k] = now
    return beep


def alert_beep():
    with CFG_LOCK:
        on = bool(CFG.get('alert_sound', True))
    if not on or os.name != 'nt':
        return

    def run():
        try:
            import winsound
            for f in (1100, 1400, 1100):
                winsound.Beep(f, 160)
        except Exception:  # noqa
            pass
    threading.Thread(target=run, daemon=True).start()


def api_alerts(q):
    try:
        since = int(q.get('since') or 0)
    except ValueError:
        since = 0
    with ALERT_LOCK:
        items = [e for e in ALERTS if e['id'] > since]
        last = ALERT_SEQ[0]
    with CFG_LOCK:
        watching = len(CFG.get('watch_hosts') or [])
    return {'items': items[-200:], 'last': last, 'watching': watching, 'school': school_brief(), 'update': update_brief(), 'privacy': privacy_status()}


def api_alerts_clear(_b=None):
    with ALERT_LOCK:
        ALERTS.clear()
        p = os.path.join(evidence_root(), ALERT_FILE)
        try:
            if os.path.exists(p):
                os.replace(p, os.path.join(evidence_root(), 'alerts-%s.old' % time.strftime('%Y%m%d-%H%M%S')))
        except OSError:
            pass
    return {'ok': True}
