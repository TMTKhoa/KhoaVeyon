# -*- coding: utf-8 -*-
"""Tương tác với học sinh: nhận sự kiện từ máy học sinh (giơ tay, nộp bài) và gửi tin nhắn / khóa màn hình kèm lời nhắn.

Máy học sinh có trợ lý KhoaVeyonStudent.ps1 (nút nổi "Giơ tay"). Trợ lý ghi sự kiện vào %ProgramData%\\KhoaVeyon\\outbox, dịch vụ
gửi về máy giáo viên (/agent/event). Máy giáo viên gửi tin nhắn bằng cách ghi file JSON vào %ProgramData%\\KhoaVeyon\\inbox."""

import json
import ntpath
import os
import re
import secrets
import threading
import time

from .agent import agent_key, AGENTS, LOCK as AGENT_LOCK
from .examlock import _safe, _walk_remote
from .paths import CONFIG_PATH
from .remote import rfs_read, rfs_remove, rfs_write
from .runtime import ApiError, CFG, CFG_LOCK, clean_hosts, log, pool_run, split_host_port, start_job
from .school import school_now
from .seating import school_student_for

STUDENT_ROOT = 'C:\\ProgramData\\KhoaVeyon'
INBOX = STUDENT_ROOT + '\\inbox'
SUBMIT_ROOT = STUDENT_ROOT + '\\submit'
SUBMIT_MAX_FILE = 25 * 1024 * 1024
SUBMIT_MAX_TOTAL = 220 * 1024 * 1024
SUBMIT_MAX_FILES = 250
ID_RE = re.compile(r'^\d{8}-\d{6}$')

LOCK = threading.RLock()
HANDS = {}        # host -> {'ts', 'name', 'cls', 'no'}
SUBMITS = []      # mới nhất ở đầu
EVENTS = []       # {'seq', 'kind', 'host', 'name', ...}: giao diện hỏi "từ seq nào" để hiện thông báo
SEQ = [0]


def submissions_root():
    d = os.path.join(os.path.dirname(CONFIG_PATH), 'submissions')
    os.makedirs(d, exist_ok=True)
    return d


def host_for_ip(ip):
    """Tên máy trong danh sách máy của giáo viên ứng với IP gọi về (rơi về tên máy do dịch vụ báo, rồi IP)."""
    with CFG_LOCK:
        hosts = list(CFG.get('hosts') or [])
    for h in hosts:
        try:
            if agent_key(h) == ip:
                return h
        except Exception:  # noqa
            continue
    with AGENT_LOCK:
        nm = (AGENTS.get(ip) or {}).get('name')
    return nm or ip


def who(host):
    """(tên học sinh ngồi máy này theo sơ đồ lớp hiện tại, lớp, số máy)."""
    try:
        cls = (school_now().get('current') or {}).get('cls', '')
    except Exception:  # noqa
        cls = ''
    name, no = school_student_for(host, cls) if cls else ('', 0)
    return name, cls, no


def _push(kind, host, **kw):
    with LOCK:
        SEQ[0] += 1
        e = dict(kw, seq=SEQ[0], kind=kind, host=host, ts=time.time())
        EVENTS.append(e)
        del EVENTS[:-200]
    return e


def handle_events(ip, d):
    """Sự kiện từ một máy học sinh (đã qua kiểm tra chữ ký và giờ)."""
    host = host_for_ip(ip)
    name, cls, no = who(host)
    for ev in (d.get('events') or [])[:20]:
        if not isinstance(ev, dict):
            continue
        t = ev.get('t')
        if t == 'hand':
            if ev.get('on'):
                with LOCK:
                    new = host not in HANDS
                    HANDS[host] = {'ts': time.time(), 'name': name, 'cls': cls, 'no': no}
                if new:
                    _push('hand', host, name=name, cls=cls, no=no)
                    log('✋ %s giơ tay (máy %s)' % (name or 'Học sinh', host), 'warn')
            else:
                with LOCK:
                    HANDS.pop(host, None)
        elif t == 'submit':
            sid = str(ev.get('id') or '')
            if not ID_RE.match(sid):
                continue
            try:
                files = max(0, int(ev.get('files') or 0))
                size = max(0, int(ev.get('bytes') or 0))
            except (TypeError, ValueError):
                files = size = 0
            rec = {'id': sid, 'host': host, 'name': name, 'cls': cls, 'ts': time.time(), 'files': files, 'bytes': size, 'status': 'pulling', 'dir': '', 'msg': ''}
            with LOCK:
                SUBMITS.insert(0, rec)
                del SUBMITS[200:]
            _push('submit', host, name=name, cls=cls, files=files)
            log('📤 %s nộp bài (%d tệp, máy %s), đang nhận về máy giáo viên' % (name or 'Học sinh', files, host), 'head')
            start_job(pull_submission, rec)


def pull_submission(rec):
    """Chép bài nộp từ máy học sinh về data\\submissions\\<ngày>\\<lớp>\\<tên>\\<giờ>\\ rồi xóa bản trên máy học sinh."""
    host = rec['host']
    hh, _ = split_host_port(host)
    remote = SUBMIT_ROOT + '\\' + rec['id']
    who_ = _safe(rec['name'] or hh)
    dest = os.path.join(submissions_root(), time.strftime('%Y-%m-%d'), _safe(rec['cls'] or 'chua-ro-lop'), who_ + '_' + rec['id'][9:])
    copied = skipped = total = 0
    try:
        files = _walk_remote(hh, remote)
        for rel, size, _m in files:
            if size > SUBMIT_MAX_FILE or copied >= SUBMIT_MAX_FILES or total + size > SUBMIT_MAX_TOTAL:
                skipped += 1
                continue
            parts = [p for p in rel.replace('/', '\\').split('\\') if p and p not in ('.', '..')]
            if not parts:
                continue
            dst = os.path.join(dest, *[_safe(p) if i < len(parts) - 1 else re.sub(r'[\\/:*?"<>|]+', '_', p) for i, p in enumerate(parts)])
            data = rfs_read(hh, ntpath.join(remote, rel))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as f:
                f.write(data)
            copied += 1
            total += len(data)
        try:
            rfs_remove(hh, remote)
        except OSError:
            pass
        rec.update(status='ok' if copied else 'error', dir=dest if copied else '', files=copied, bytes=total,
                   msg=('' if not skipped else 'bỏ qua %d tệp quá lớn hoặc vượt giới hạn' % skipped) if copied else 'không nhận được tệp nào')
        log('📥 Đã nhận bài của %s: %d tệp (%.1f MB) → %s%s' % (rec['name'] or hh, copied, total / 1048576.0, dest, ('; ' + rec['msg']) if rec['msg'] else ''), 'ok' if copied else 'err')
    except (OSError, ValueError) as e:
        rec.update(status='error', msg=str(e)[:200])
        log('Không nhận được bài nộp của %s: %s' % (rec['name'] or hh, e), 'err')


def student_overview(since=0):
    with LOCK:
        hands = sorted(({'host': h, **v} for h, v in HANDS.items()), key=lambda x: x['ts'])
        subs = [dict(s) for s in SUBMITS[:60]]
        ev = [dict(e) for e in EVENTS if e['seq'] > since]
        last = SEQ[0]
    return {'hands': hands, 'submits': subs, 'events': ev, 'last': last, 'root': submissions_root()}


def api_student(q):
    try:
        since = int(q.get('since') or 0)
    except (TypeError, ValueError):
        since = 0
    return student_overview(since)


def _inbox_write(host, msg):
    name = 'm-%d-%s.json' % (int(time.time() * 1000), secrets.token_hex(3))
    rfs_write(split_host_port(host)[0], INBOX + '\\' + name, json.dumps(msg, ensure_ascii=False).encode('utf-8'))


def send_message(hosts, msg):
    """Ghi tin nhắn vào hộp thư của từng máy (qua Agent). Trả về cho pool_run: (ok, mô tả)."""
    def one(h):
        try:
            _inbox_write(h, msg)
        except Exception as e:  # noqa
            return False, 'không gửi được (máy tắt hoặc chưa có Agent?): %s' % e
        return True, 'đã gửi'
    pool_run(one, hosts, 'Gửi tới máy học sinh')


def api_student_send(b):
    kind = str(b.get('kind') or '')
    if kind not in ('msg', 'block', 'clear', 'collect'):
        raise ApiError('Loại tin nhắn không hợp lệ')
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào để gửi')
    text = str(b.get('text') or '').strip()[:600]
    if kind in ('msg', 'block') and not text:
        raise ApiError('Hãy nhập nội dung')
    try:
        seconds = max(0, min(600, int(b.get('seconds') or 0)))
    except (TypeError, ValueError):
        seconds = 0
    msg = {'type': kind, 'title': str(b.get('title') or 'Thầy/cô nhắn')[:80], 'text': text or 'Hãy nộp bài làm của em.', 'seconds': seconds}
    start_job(send_message, hosts, msg)
    return {'ok': True, 'count': len(hosts)}


def api_hand_clear(b):
    """Hạ tay: một máy (host) hoặc tất cả. Máy học sinh cũng được báo để nút trở lại bình thường."""
    host = str(b.get('host') or '')
    with LOCK:
        targets = [host] if host else list(HANDS)
        for h in targets:
            HANDS.pop(h, None)
    if targets:
        start_job(send_message, targets, {'type': 'handclear'})
    return student_overview(0)
