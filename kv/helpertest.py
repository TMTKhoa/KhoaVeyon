# -*- coding: utf-8 -*-
"""Kiểm tra các tính năng chạy bằng trợ lý PowerShell trên MỘT máy học sinh (câu đố, chiếu bài, phát tài liệu, đồng hồ, khóa màn hình, hình nền, ảnh thu nhỏ...).
Mỗi bước gửi một tác vụ thử kèm mã `tid`/`step`; trợ lý trên máy học sinh báo lại (ack) thành công hoặc lỗi cụ thể. Hộp hiện trên màn hình máy thử rồi tự đóng / tự gỡ."""

import re
import secrets
import threading
import time

from .remote import rfs_read, rfs_remove, rfs_write
from .runtime import ApiError, clean_hosts, log, split_host_port
from .student import _inbox_write, STUDENT_ROOT

def pause(sec):
    time.sleep(sec)


HT = {'data': None}
ACKS = {}
HLOCK = threading.RLock()
TID_RE = re.compile(r'^[0-9a-f]{8}$')
ACK_WAIT = 25


def ack_put(host, tid, step, ok, err, info):
    if not TID_RE.match(tid or ''):
        return
    with HLOCK:
        for k in [k for k, v in ACKS.items() if time.time() - v['ts'] > 900]:
            ACKS.pop(k, None)
        ACKS[(tid, str(step)[:20])] = {'host': host, 'ok': bool(ok), 'err': str(err or '')[:200], 'info': str(info or '')[:200], 'ts': time.time()}


def wait_ack(tid, step, host, timeout=None):
    end = time.time() + (ACK_WAIT if timeout is None else timeout)
    while time.time() < end:
        with HLOCK:
            a = ACKS.get((tid, step))
        if a and a['host'] == host:
            return a
        time.sleep(0.2)
    return None


def _send(host, tid, step, msg):
    _inbox_write(host, dict(msg, tid=tid, step=step))
    return wait_ack(tid, step, host)


def _show_ack(a, what):
    """Đổi ack thành (trạng thái, mô tả)."""
    if a is None:
        return 'bad', 'máy học sinh không phản hồi trong %d giây (trợ lý chưa chạy hoặc bản cũ chưa có tính năng này: chạy lại "Bật giám sát" / "Cập nhật máy học sinh")' % ACK_WAIT
    if not a['ok']:
        return 'bad', 'trợ lý báo lỗi: %s' % (a['err'] or 'không rõ')
    return 'ok', what + (' · ' + a['info'] if a['info'] else '')


def st_link(h, tid, ctx):
    path = STUDENT_ROOT + '\\ft\\' + tid + '.txt'
    data = ('khoaveyon-' + tid).encode()
    rfs_write(split_host_port(h)[0], path, data)
    back = rfs_read(split_host_port(h)[0], path)
    try:
        rfs_remove(split_host_port(h)[0], path)
    except Exception:  # noqa
        pass
    return ('ok', 'ghi và đọc lại tệp trên máy học sinh thành công (kênh Agent hoạt động)') if back == data else ('bad', 'tệp đọc lại không khớp')


def st_helper(h, tid, ctx):
    a = wait_helper(h, tid)
    s, d = _show_ack(a, 'trợ lý đang chạy')
    ctx['helper'] = (s == 'ok')
    return s, d


def wait_helper(h, tid):
    return _send(h, tid, 'helper', {'type': 'selftest'})


def st_msg(h, tid, ctx):
    return _show_ack(_send(h, tid, 'msg', {'type': 'msg', 'title': 'Kiểm tra KhoaVeyon', 'text': 'Đây là thông báo thử, tự đóng sau 5 giây.', 'seconds': 5}), 'hộp thông báo đã hiện (tự đóng sau 5 giây)')


def st_quiz(h, tid, ctx):
    qid = secrets.token_hex(4)
    r = _show_ack(_send(h, tid, 'quiz', {'type': 'quiz', 'id': qid, 'q': 'Câu hỏi thử: 1 + 1 = ?', 'opts': ['1', '2', '3'], 'secs': 0}), 'hộp câu đố đã hiện')
    pause(3)
    _inbox_write(h, {'type': 'quizend', 'id': qid, 'reveal': False, 'correct': -1, 'mine': -1})
    return r


def st_timer(h, tid, ctx):
    r = _show_ack(_send(h, tid, 'timer', {'type': 'timer', 'secs': 8, 'label': 'Thử đồng hồ'}), 'đồng hồ đếm ngược đã hiện ở trên giữa màn hình')
    pause(3)
    _inbox_write(h, {'type': 'timer', 'cancel': True})
    return r


def st_block(h, tid, ctx):
    from .engage import _ensure_bg, api_lock_style
    st = api_lock_style()['style']
    if st['bg']:
        _ensure_bg(h, st['bg'])
    msg = dict(st, type='block', text='Kiểm tra khóa màn hình, tự mở sau 4 giây.', name='', no=0, title=st['title'].replace('{', '').replace('}', '')[:60] or 'Kiểm tra')
    r = _show_ack(_send(h, tid, 'block', msg), 'màn hình khóa đã hiện')
    pause(4)
    _inbox_write(h, {'type': 'clear'})
    return r


def st_wall(h, tid, ctx):
    from .engage import _ensure_bg, clean_wall, wall_message
    spec = clean_wall({})
    if spec['bg']:
        _ensure_bg(h, spec['bg'])
    r = _show_ack(_send(h, tid, 'wall', wall_message(h, spec)), 'đã vẽ và đặt hình nền (kiểm tra màn hình nền, sắp trả lại)')
    pause(3)
    _inbox_write(h, {'type': 'wallpaper', 'restore': True})
    return r


def st_snap(h, tid, ctx):
    sid = secrets.token_hex(4)
    ctx['sid'] = sid
    a = _send(h, tid, 'snap', {'type': 'snap', 'id': sid})
    s, d = _show_ack(a, 'đã chụp màn hình')
    if s != 'ok':
        return s, d
    data = rfs_read(split_host_port(h)[0], STUDENT_ROOT + '\\share\\' + sid + '.jpg')
    if not data.startswith(b'\xff\xd8') or len(data) < 2000:
        return 'bad', 'tệp ảnh chụp không hợp lệ (%d byte)' % len(data)
    ctx['jpg'] = data
    return 'ok', 'chụp xong, giáo viên đọc được ảnh (%d KB)' % (len(data) // 1024)


def st_show(h, tid, ctx):
    if not ctx.get('jpg'):
        return 'skip', 'bỏ qua vì bước chụp màn hình chưa đạt'
    sid = ctx['sid']
    rfs_write(split_host_port(h)[0], STUDENT_ROOT + '\\show\\' + sid + '.jpg', ctx['jpg'])
    r = _show_ack(_send(h, tid, 'show', {'type': 'show', 'id': sid, 'secs': 4, 'cap': 'Kiểm tra chiếu bài'}), 'ảnh đã hiện toàn màn hình (tự tắt sau 4 giây)')
    pause(3)
    _inbox_write(h, {'type': 'showclear'})
    return r


def st_handout(h, tid, ctx):
    hid = secrets.token_hex(6)
    rfs_write(split_host_port(h)[0], STUDENT_ROOT + '\\handout\\' + hid + '\\kiemtra.txt', 'Tệp thử của KhoaVeyon, có thể xóa.'.encode('utf-8'))
    return _show_ack(_send(h, tid, 'handout', {'type': 'handout', 'id': hid, 'label': 'Kiem tra KhoaVeyon', 'files': ['kiemtra.txt'], 'open': 'none'}), 'đã chép tệp vào thư mục "Kiem tra KhoaVeyon" trên màn hình nền (xóa được)')


def st_thumb(h, tid, ctx):
    from .board import THUMBS
    from .student import LOCK
    t0 = time.time()
    a = _send(h, tid, 'thumb', {'type': 'config', 'live': 3, 'ttl': 60})
    s, d = _show_ack(a, 'đã bật ảnh thu nhỏ')
    if s == 'ok':
        got = 0
        end = time.time() + 20
        while time.time() < end:
            with LOCK:
                v = THUMBS.get(h)
            if v and v['ts'] > t0:
                got = round(v['ts'] - t0, 1)
                break
            time.sleep(0.5)
        s, d = ('ok', 'nhận được ảnh thu nhỏ sau %s giây' % got) if got else ('bad', 'đã bật nhưng chưa nhận ảnh thu nhỏ nào sau 20 giây')
    try:
        _inbox_write(h, {'type': 'config', 'live': 0, 'ttl': 60})
    except Exception:  # noqa
        pass
    return s, d


def st_url(h, tid, ctx):
    return _show_ack(_send(h, tid, 'url', {'type': 'open', 'url': 'https://example.com/'}), 'đã mở trang example.com trên máy học sinh (đóng trang đó đi)')


STEPS = [('link', 'Kênh tệp (Agent): ghi/đọc tệp trên máy học sinh', st_link, False),
         ('helper', 'Trợ lý PowerShell đang chạy và phản hồi', st_helper, False),
         ('msg', 'Hộp thông báo', st_msg, True), ('quiz', 'Câu đố nhanh', st_quiz, True), ('timer', 'Đồng hồ đếm ngược', st_timer, True),
         ('block', 'Màn hình khóa', st_block, True), ('wall', 'Hình nền', st_wall, True), ('snap', 'Chụp màn hình một lần', st_snap, True),
         ('show', 'Chiếu bài toàn màn hình', st_show, True), ('handout', 'Nhận tài liệu', st_handout, True), ('thumb', 'Ảnh thu nhỏ cho Monitor', st_thumb, True),
         ('url', 'Mở trang web (tùy chọn)', st_url, True)]


def run(host, tid, with_url):
    ctx = {}
    D = HT['data']
    for key, name, fn, needs_helper in STEPS:
        row = next(r for r in D['steps'] if r['key'] == key)
        if key == 'url' and not with_url:
            row.update(status='skip', detail='không chọn kiểm tra bước này')
            continue
        if needs_helper and ctx.get('helper') is False:
            row.update(status='skip', detail='bỏ qua vì trợ lý PowerShell không phản hồi')
            continue
        row['status'] = 'run'
        try:
            s, d = fn(host, tid, ctx)
        except Exception as e:  # noqa
            s, d = 'bad', 'lỗi: %s' % e
        row.update(status=s, detail=d)
        log('🧪 Kiểm tra %s: %s - %s' % (name, s, d), 'ok' if s == 'ok' else 'err')
    D['done'] = True
    D['ok'] = sum(1 for r in D['steps'] if r['status'] == 'ok')
    D['total'] = sum(1 for r in D['steps'] if r['status'] != 'skip')


def api_ht_start(b):
    hosts = clean_hosts(b.get('hosts'))
    if len(hosts) != 1:
        raise ApiError('Chọn đúng một máy để kiểm tra')
    if HT['data'] and not HT['data'].get('done') and time.time() - HT['data']['ts'] < 600:
        raise ApiError('Đang có một lần kiểm tra chạy, hãy chờ xong')
    tid = secrets.token_hex(4)
    HT['data'] = {'tid': tid, 'host': hosts[0], 'ts': time.time(), 'done': False, 'ok': None, 'total': None,
                  'steps': [{'key': k, 'name': n, 'status': 'wait', 'detail': ''} for k, n, _f, _h in STEPS]}
    threading.Thread(target=run, args=(hosts[0], tid, bool(b.get('url'))), daemon=True).start()
    return {'ok': True, 'tid': tid}


def api_ht_state(_q=None):
    return {'result': HT['data']}
