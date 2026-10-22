# -*- coding: utf-8 -*-
"""Công cụ trong giờ học: câu đố nhanh (học sinh chọn đáp án trên máy mình), phát tài liệu xuống máy cả lớp, mở một trang web trên máy học sinh."""

import base64
import hashlib
import os
import re
import secrets
import threading
import time

from .paths import CONFIG_PATH
from .remote import rfs_sha, rfs_write
from .runtime import ApiError, clean_hosts, log, pool_run, split_host_port, start_job
from .school import _cls_norm, school_now
from .student import _inbox_write, send_message, STUDENT_ROOT, who

# ---------------------------------------------------------------- câu đố nhanh
QUIZ = {}
QLOCK = threading.RLock()


def api_quiz_start(b):
    q = re.sub(r'\s+', ' ', str(b.get('q') or '')).strip()[:300]
    opts = [re.sub(r'\s+', ' ', str(o or '')).strip()[:100] for o in (b.get('opts') or [])][:4]
    opts = [o for o in opts if o]
    if not q or len(opts) < 2:
        raise ApiError('Cần câu hỏi và ít nhất 2 đáp án')
    try:
        correct = int(b.get('correct', -1))
    except (TypeError, ValueError):
        correct = -1
    if not -1 <= correct < len(opts):
        correct = -1
    try:
        secs = max(0, min(600, int(b.get('secs') or 0)))
    except (TypeError, ValueError):
        secs = 0
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào')
    cls = _cls_norm(b.get('cls')) or (school_now().get('current') or {}).get('cls', '')
    qid = secrets.token_hex(4)
    with QLOCK:
        QUIZ.clear()
        QUIZ.update({'id': qid, 'q': q, 'opts': opts, 'correct': correct, 'secs': secs, 'cls': cls, 'hosts': list(hosts), 'answers': {}, 'closed': False, 'started': time.time()})
    start_job(send_message, hosts, {'type': 'quiz', 'id': qid, 'q': q, 'opts': opts, 'secs': secs})
    log('❓ Câu đố nhanh gửi tới %d máy: %s' % (len(hosts), q[:60]), 'head')
    return api_quiz_state()


def quiz_answer(host, qid, a):
    with QLOCK:
        if not QUIZ or QUIZ.get('closed') or QUIZ['id'] != qid or host not in QUIZ['hosts']:
            return
        if QUIZ['secs'] and time.time() > QUIZ['started'] + QUIZ['secs'] + 8:
            return
        if isinstance(a, int) and 0 <= a < len(QUIZ['opts']):
            QUIZ['answers'][host] = {'a': a, 'ts': time.time()}


def api_quiz_state(_q=None):
    with QLOCK:
        if not QUIZ:
            return {'active': False}
        Q = dict(QUIZ, answers=dict(QUIZ['answers']))
    counts = [0] * len(Q['opts'])
    voters = [[] for _ in Q['opts']]
    label = {}
    for h in Q['hosts']:
        name, _c, no = who(h, Q['cls'])
        label[h] = (name or h) + (' (máy %d)' % no if no else '')
    for h, x in Q['answers'].items():
        counts[x['a']] += 1
        voters[x['a']].append(label.get(h, h))
    pending = [label[h] for h in Q['hosts'] if h not in Q['answers']]
    return {'active': True, 'closed': Q['closed'], 'id': Q['id'], 'q': Q['q'], 'opts': Q['opts'], 'correct': Q['correct'], 'secs': Q['secs'], 'started': Q['started'],
            'total': len(Q['hosts']), 'answered': len(Q['answers']), 'counts': counts, 'voters': voters, 'pending': pending}


def api_quiz_end(b):
    with QLOCK:
        if not QUIZ:
            raise ApiError('Chưa có câu đố nào')
        QUIZ['closed'] = True
        hosts, qid, correct = list(QUIZ['hosts']), QUIZ['id'], QUIZ['correct']
        mine = {h: x['a'] for h, x in QUIZ['answers'].items()}
    reveal = bool(b.get('reveal')) and correct >= 0

    def job(hs):
        def one(h):
            try:
                _inbox_write(h, {'type': 'quizend', 'id': qid, 'reveal': reveal, 'correct': correct, 'mine': mine.get(h, -1)})
            except Exception as e:  # noqa
                return False, 'không gửi được: %s' % e
            return True, 'đã kết thúc câu đố'
        pool_run(one, hs, 'Kết thúc câu đố')
    start_job(job, hosts)
    return api_quiz_state()


# ---------------------------------------------------------------- mở trang web
def api_open_url(b):
    url = str(b.get('url') or '').strip()
    if not re.fullmatch(r'https?://[^\s<>"\']{3,500}', url):
        raise ApiError('Địa chỉ phải bắt đầu bằng http:// hoặc https://')
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào')
    start_job(send_message, hosts, {'type': 'open', 'url': url})
    return {'ok': True, 'count': len(hosts)}


# ---------------------------------------------------------------- phát tài liệu
BAD_EXT = ('.exe', '.bat', '.cmd', '.ps1', '.vbs', '.vbe', '.js', '.jse', '.msi', '.scr', '.com', '.lnk', '.reg', '.hta', '.jar', '.dll', '.pif')
MAX_FILES, MAX_ONE, MAX_TOTAL = 10, 12 * 1024 * 1024, 30 * 1024 * 1024


def handouts_root():
    d = os.path.join(os.path.dirname(CONFIG_PATH), 'handouts')
    os.makedirs(d, exist_ok=True)
    return d


def safe_name(n):
    n = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', '_', os.path.basename(str(n or '').replace('\\', '/'))).strip(' .')[:120]
    return n


def job_handout(hosts, hid, files, label, mode):
    def one(h):
        try:
            hh = split_host_port(h)[0]
            for name, data in files:
                remote = STUDENT_ROOT + '\\handout\\' + hid + '\\' + name
                try:
                    same = rfs_sha(hh, remote) == hashlib.sha256(data).hexdigest()
                except FileNotFoundError:
                    same = False
                if not same:
                    rfs_write(hh, remote, data)
            _inbox_write(h, {'type': 'handout', 'id': hid, 'label': label, 'files': [n for n, _ in files], 'open': mode})
        except Exception as e:  # noqa
            return False, 'không gửi được tài liệu (máy tắt hoặc chưa có Agent?): %s' % e
        return True, 'đã gửi %d tệp' % len(files)
    pool_run(one, hosts, 'Phát tài liệu')


def api_handout_send(b):
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào')
    raw = b.get('files')
    if not isinstance(raw, list) or not raw:
        raise ApiError('Chưa chọn tệp nào')
    if len(raw) > MAX_FILES:
        raise ApiError('Tối đa %d tệp mỗi lần' % MAX_FILES)
    files, total, seen = [], 0, set()
    for f in raw:
        name = safe_name((f or {}).get('name'))
        if not name or name.lower() in seen:
            continue
        if name.lower().endswith(BAD_EXT):
            raise ApiError('Không phát tệp chương trình (%s). Dùng trang "Phân phối & chạy" cho việc đó.' % name)
        try:
            data = base64.b64decode(str((f or {}).get('data') or ''), validate=False)
        except ValueError:
            raise ApiError('Tệp %s không đọc được' % name)
        if not data or len(data) > MAX_ONE:
            raise ApiError('Tệp %s rỗng hoặc lớn hơn %d MB' % (name, MAX_ONE // 1048576))
        total += len(data)
        if total > MAX_TOTAL:
            raise ApiError('Tổng dung lượng tối đa %d MB' % (MAX_TOTAL // 1048576))
        seen.add(name.lower())
        files.append((name, data))
    if not files:
        raise ApiError('Chưa có tệp hợp lệ')
    label = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', ' ', str(b.get('label') or '')).strip()[:40] or 'Tai lieu cua thay co'
    mode = b.get('open') if b.get('open') in ('folder', 'first', 'none') else 'folder'
    hid = time.strftime('%Y%m%d%H%M%S') + secrets.token_hex(2)
    d = os.path.join(handouts_root(), hid)    # giữ bản gốc trên máy giáo viên
    os.makedirs(d, exist_ok=True)
    for name, data in files:
        with open(os.path.join(d, name), 'wb') as f:
            f.write(data)
    start_job(job_handout, hosts, hid, files, label, mode)
    log('📎 Phát %d tệp tới %d máy: %s' % (len(files), len(hosts), ', '.join(n for n, _ in files)[:80]), 'head')
    return {'ok': True, 'count': len(hosts), 'files': [n for n, _ in files]}
