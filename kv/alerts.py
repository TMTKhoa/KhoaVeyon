# -*- coding: utf-8 -*-
"""Báo động vi phạm ở máy giáo viên: nhận ảnh, gom báo động trùng, ghi lịch sử, tiếng bíp."""

import json
import ntpath
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
from .remote import rfs_read, rfs_reachable, rfs_remove, rfs_scan, rfs_write
from .runtime import CFG, CFG_LOCK, log
from .school import _cls_norm, school_class_at
from .school_api import school_brief
from .seating import school_student_for
from .updater import update_brief


# ---------------------------------------------------------------- báo động vi phạm: tự nhận ảnh từ máy học sinh về máy giáo viên
ALERTS = []                 # danh sách vi phạm (cũ -> mới), mỗi mục có 'id' tăng dần
ALERT_LOCK = threading.Lock()
ALERT_SEQ = [0]
ALERT_SEEN = set()          # (máy, tên file) đã xử lý, tránh báo trùng
HOST_ONLINE = {}
PUSH_CAPABLE = {}           # máy -> lúc nhận tín hiệu "hello" gần nhất từ script giám sát (máy đó tự đẩy ảnh về, máy giáo viên chỉ cần quét thưa)
PUSH_FRESH_SEC = 600
PUSH_FALLBACK_SEC = 15      # máy đã báo hello vẫn được quét dự phòng chừng này giây một lần, phòng khi tín hiệu đẩy bị mất (trước đây 60 giây)
_IS_WIN = os.name == 'nt'
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


def alert_class_at(cfg, ts):
    """Lớp ghi vào vi phạm. 'current': lớp đang có tiết tại giờ vi phạm (thời khóa biểu, hoặc lớp giáo viên đặt).
    'manual': luôn là lớp giáo viên chọn riêng cho báo động; chưa chọn lớp thì rơi về 'current'."""
    if cfg.get('alert_cls_mode') == 'manual':
        c = _cls_norm(cfg.get('alert_cls_manual'))
        if c:
            return c
    return school_class_at(ts)


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
    """Xóa file CỤC BỘ (bỏ qua lỗi)."""
    try:
        os.remove(path)
    except OSError:
        pass


def _rrm(host, name):
    """Xóa file trong thư mục ảnh vi phạm trên máy học sinh (bỏ qua lỗi)."""
    try:
        rfs_remove(host, ntpath.join(WATCH_REMOTE_DIR, name))
    except OSError:
        pass


_COLLECT_LOCKS = {}
_COLLECT_GUARD = threading.Lock()


def alert_collect_host(cfg, host):
    """Mỗi máy chỉ một luồng nhận ảnh cùng lúc (vòng nền và tín hiệu đẩy từ máy học sinh có thể trùng nhau)."""
    with _COLLECT_GUARD:
        lk = _COLLECT_LOCKS.setdefault(host, threading.Lock())
    with lk:
        return _alert_collect_host(cfg, host)


def collect_and_beep(cfg, host):
    """Nhận ảnh ngay khi máy học sinh báo (đẩy), rồi bíp như vòng quét nền."""
    before = ALERT_SEQ[0]
    alert_collect_host(cfg, host)
    with ALERT_LOCK:
        fresh = [e for e in ALERTS if e['id'] > before and e['host'] == host]   # chỉ của máy này: vi phạm máy khác do luồng khác lo
    try:
        gap = int(cfg.get('alert_group_sec') or 60)
    except (TypeError, ValueError):
        gap = 60
    if fresh and alert_should_beep(fresh, max(10, min(3600, gap))):
        alert_beep()


def _recent_clean(v):
    """Nhật ký 5 phút do máy học sinh gửi kèm: chỉ giữ dạng danh sách ngắn, chuỗi đã cắt độ dài."""
    out = []
    for x in (v if isinstance(v, list) else [])[-60:]:   # giữ 60 mục MỚI nhất
        if isinstance(x, dict):
            try:
                d = max(0, min(86400, int(x.get('d') or 0)))
            except (TypeError, ValueError):
                d = 0
            out.append({'p': _clip(x.get('p'), 40), 'w': _clip(x.get('w'), 100), 'h': _clip(x.get('h'), 80), 't': _clip(x.get('t'), 8), 'd': d})
    return out


def _alert_collect_host(cfg, host):
    """Lấy ảnh vi phạm mới từ máy học sinh về máy giáo viên rồi tạo báo động. Trả về (ok, mô tả, số vi phạm mới)."""
    if not rfs_reachable(host, tcp_open):
        return False, 'không kết nối được (máy tắt hoặc mạng lỗi)', 0
    try:
        ents = rfs_scan(host, WATCH_REMOTE_DIR)
    except FileNotFoundError:
        return True, 'chưa có ảnh', 0
    except OSError as e:
        return False, str(e), 0
    mt = {e['name']: e['mtime'] for e in ents}
    sz = {e['name']: e['size'] for e in ents}
    names = list(mt)
    jobs = []   # (tên file ảnh, siêu dữ liệu, các file nguồn cần xóa)
    lower = {n.lower(): n for n in names}
    for n in sorted(names):
        low = n.lower()
        if low.endswith('.jpg.ok'):  # biên nhận do máy giáo viên ghi (học sinh không xóa được), dọn cái cũ hơn 2 phút
            if time.time() - mt[n] > 120:
                _rrm(host, n)
            continue
        if low.endswith('.json'):
            try:
                m = json.loads(rfs_read(host, ntpath.join(WATCH_REMOTE_DIR, n)).decode('utf-8-sig'))
                if not isinstance(m, dict):
                    raise ValueError
            except (OSError, ValueError):
                if time.time() - mt[n] > 60:  # chưa ghi xong thì lần sau thử lại; hỏng quá 60 giây thì dọn đi
                    _rrm(host, n)
                continue
            jpg = str(m.get('file') or '')
            if jpg != os.path.basename(jpg) or not SAFE_JPG.match(jpg):  # tên file lạ (đường dẫn, ký tự đặc biệt): bỏ
                _rrm(host, n)
                continue
            jobs.append((jpg, m, [n]))
        elif low.endswith('.jpg') and low[:-4] + '.json' not in lower:
            lm = LEGACY_JPG.match(n)  # ảnh do bản giám sát cũ chụp, không có file .json
            old_enough = time.time() - mt[n] > 20
            if lm and old_enough and SAFE_JPG.match(n):
                d, t = lm.group('d'), lm.group('t')
                jobs.append((n, {'pc': lm.group('pc'), 'type': lm.group('kind'), 'name': lm.group('name'),
                                 'date': '%s-%s-%s' % (d[:4], d[4:6], d[6:]), 'time': '%s:%s:%s' % (t[:2], t[2:4], t[4:]),
                                 'window': ''}, []))
    new = 0
    for jpg, m, extra in jobs[:ALERT_PER_CYCLE]:
        key = (host, jpg)
        if key in ALERT_SEEN:   # đã báo rồi, chỉ dọn file còn sót
            for x in extra + [jpg]:
                _rrm(host, x)
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
        cls_now = alert_class_at(cfg, ts)
        stu, seat = school_student_for(host, cls_now)
        img = ''
        try:
            if jpg in sz and sz[jpg] <= ALERT_MAX_IMG:
                # data\evidence\<ngày>\<lớp>\<Trường>_<Lớp>_<Học sinh>_<Máy>_<ngày>_<giờ>_<loại>_<trang>.jpg
                dest, img = evidence_target(cfg, hn_of(cfg, host), date, tm, kind, name, cls_now, stu)
                with open(dest, 'wb') as f:
                    f.write(rfs_read(host, ntpath.join(WATCH_REMOTE_DIR, jpg)))
        except OSError:
            continue  # chưa chép được, lần sau thử lại
        alert_push({'host': host, 'pc': _clip(m.get('pc'), 64), 'user': _clip(m.get('user'), 64), 'type': kind,
                    'name': name, 'window': _clip(m.get('window'), 300), 'date': date, 'time': tm, 'ts': ts,
                    'file': jpg, 'img': img, 'text': alert_text(kind, name), 'cls': cls_now, 'student': stu, 'seat': seat,
                    'recent': _recent_clean(m.get('recent'))})
        for x in extra + [jpg]:
            _rrm(host, x)
        if cfg.get('watch_notify_student', True):
            write_receipt(host, jpg)
        new += 1
        log('[%s] VI PHẠM: %s (%s %s)' % (host, alert_text(kind, name), date, tm), 'warn')
    return True, 'ok', new


def write_receipt(host, jpg):
    """Biên nhận "máy giáo viên đã nhận ảnh này": file <ảnh>.jpg.ok cạnh chỗ ảnh vừa lấy trên máy học sinh.
    Script giám sát chỉ báo cho học sinh "đã gửi cho giáo viên" khi thấy biên nhận, rồi tự xóa nó."""
    try:
        rfs_write(host, ntpath.join(WATCH_REMOTE_DIR, jpg + '.ok'), time.strftime('%Y-%m-%d %H:%M:%S').encode('ascii'))
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


_BEEP_REQ = threading.Event()
_BEEP_START = threading.Lock()
_BEEP_THREAD = [None]
_BEEP_FAILED = [False]


def _beep_play():
    """Một hồi bíp (4 tiếng, mỗi tiếng 0,2 giây). Loa/thiết bị âm thanh vừa "thức dậy" thường nuốt mất tiếng đầu nên hồi bíp đủ dài.
    Beep lỗi thì thử âm thanh hệ thống. Trả về False nếu cả hai đều lỗi."""
    try:
        import winsound
    except ImportError:
        return False
    try:
        for f in (1100, 1400, 1100, 1400):
            winsound.Beep(f, 200)
        return True
    except Exception:  # noqa
        pass
    try:
        winsound.PlaySound('SystemExclamation', winsound.SND_ALIAS)
        return True
    except Exception:  # noqa
        return False


def _beep_worker():
    # Một luồng duy nhất phát tiếng: hai yêu cầu cùng lúc không còn đè nhau (winsound.Beep lỗi nếu đang có tiếng khác) và không bị nuốt lỗi âm thầm.
    # Yêu cầu đến trong lúc đang kêu thì kêu thêm đúng một hồi sau đó.
    while True:
        _BEEP_REQ.wait()
        _BEEP_REQ.clear()
        try:
            ok = _beep_play()
        except Exception:  # noqa: luồng phát tiếng không bao giờ được chết
            ok = False
        if not ok and not _BEEP_FAILED[0]:
            log('Không phát được tiếng báo động trên máy giáo viên: kiểm tra loa, âm lượng và thiết bị âm thanh mặc định. Bấm “Thử tiếng báo” ở trang Vi phạm để kiểm tra.', 'warn')
        _BEEP_FAILED[0] = not ok
        time.sleep(0.3)


def alert_beep(force=False):
    """Phát tiếng báo động (nếu đang bật; force=True thì phát dù đang tắt, dùng cho nút thử). Trả về False nếu không phát được."""
    if not _IS_WIN:
        return False
    if not force:
        with CFG_LOCK:
            if not bool(CFG.get('alert_sound', True)):
                return False
    with _BEEP_START:
        t = _BEEP_THREAD[0]
        if t is None or not t.is_alive():
            t = threading.Thread(target=_beep_worker, daemon=True)
            t.start()
            _BEEP_THREAD[0] = t
    _BEEP_REQ.set()
    return True


def api_alert_test(_b=None):
    """Nút “Thử tiếng báo”: phát một hồi bíp để giáo viên kiểm tra loa."""
    if not _IS_WIN:
        return {'ok': False, 'msg': 'Tiếng báo chỉ phát được trên Windows (máy này không chạy Windows).'}
    with CFG_LOCK:
        on = bool(CFG.get('alert_sound', True))
    alert_beep(force=True)
    return {'ok': True, 'msg': 'Đang phát tiếng báo thử.' + ('' if on else ' Lưu ý: “Kêu bíp khi có vi phạm” đang TẮT nên khi có vi phạm sẽ không kêu.')}


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
