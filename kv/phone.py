# -*- coding: utf-8 -*-
"""Điều khiển nhanh bằng điện thoại: giáo viên bật, quét mã QR, điện thoại (cùng mạng LAN) mở trang điều khiển rút gọn.
Máy chủ riêng, mặc định TẮT; chỉ nhận các lệnh trong danh sách cho phép, có mã phiên ngẫu nhiên, hết hạn, chặn đoán mã và chặn máy học sinh."""

import http.server
import ipaddress
import json
import os
import secrets
import socket
import threading
import time
import urllib.parse

from .agent import lan_ip
from .runtime import ApiError, CFG, CFG_LOCK, log, split_host_port, WEB_DIR

PH = {'on': False, 'token': '', 'exp': 0.0, 'port': 0, 'srv': None, 'thread': None, 'url': '', 'devices': {}, 'fails': {}, 'stu_ips': set(), 'stu_ts': 0.0}
PLOCK = threading.RLock()
MAX_FAILS, FAIL_WINDOW = 8, 300
PORTS = (8768, 0)


def _qr_svg(url):
    from .vendor import segno
    return segno.make(url, error='m').svg_inline(scale=5, border=2, dark='#0f172a')


def _student_ips():
    """IP của các máy học sinh (để chặn: học sinh có bắt gói tin cũng không dùng được trang này)."""
    now = time.time()
    with PLOCK:
        if now - PH['stu_ts'] < 120:
            return PH['stu_ips']
        PH['stu_ts'] = now
    with CFG_LOCK:
        hosts = list(CFG.get('hosts') or [])

    def work():
        ips = set()
        for h in hosts:
            name = split_host_port(h)[0]
            try:
                ipaddress.ip_address(name)
                ips.add(name)
            except ValueError:
                try:
                    ips.add(socket.gethostbyname(name))
                except OSError:
                    pass
        with PLOCK:
            PH['stu_ips'] = ips
    threading.Thread(target=work, daemon=True).start()
    return PH['stu_ips']


def client_allowed(ip):
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return (a.is_private or a.is_loopback) and ip not in _student_ips()


def _all_hosts():
    with CFG_LOCK:
        return list(CFG.get('hosts') or [])


# ---------------------------------------------------------------- lệnh cho phép từ điện thoại
def phone_state():
    from .board import api_monitor
    from .fun import api_quick_notes
    m = api_monitor({})
    names = {s['host']: s['name'] for s in (m.get('seats') or {}).values() if s.get('host')}
    seat_no = {s['host']: int(no) for no, s in (m.get('seats') or {}).items() if s.get('host')}
    mach = m.get('machines') or {}
    hands = [{'host': h, 'pc': x['pc'], 'name': names.get(h, ''), 'no': seat_no.get(h, 0)} for h, x in mach.items() if x.get('hand')]
    viol = sum(1 for x in mach.values() if x.get('viol'))
    return {'cls': m.get('cls', ''), 'current': m.get('current'), 'online': m.get('online', 0), 'total': m.get('total', 0), 'hands': hands, 'viol': viol,
            'notes': api_quick_notes()['items'], 'ts': int(time.time())}


def phone_do(b):
    from .engage import api_draw
    from .fun import api_countdown, api_star
    from .student import api_hand_clear, api_student_send
    op = str(b.get('op') or '')
    hosts = _all_hosts()
    if op in ('msg', 'block', 'clear', 'timer', 'timerstop') and not hosts:
        raise ApiError('Chưa có máy học sinh nào trong danh sách')
    if op == 'msg':
        text = str(b.get('text') or '').strip()[:200]
        return api_student_send({'kind': 'msg', 'hosts': hosts, 'text': text, 'title': 'Thầy/cô nhắn', 'seconds': 12})
    if op == 'block':
        text = str(b.get('text') or '').strip()[:200] or 'Các em tạm dừng và chú ý lên bảng.'
        return api_student_send({'kind': 'block', 'hosts': hosts, 'text': text})
    if op == 'clear':
        return api_student_send({'kind': 'clear', 'hosts': hosts})
    if op == 'timer':
        return api_countdown({'hosts': hosts, 'minutes': b.get('minutes'), 'label': str(b.get('label') or '')[:80]})
    if op == 'timerstop':
        return api_countdown({'hosts': hosts, 'cancel': True})
    if op == 'handdown':
        api_hand_clear({'host': str(b.get('host') or '')})
        return {'ok': True}
    if op == 'star':
        h = str(b.get('host') or '')
        if h not in hosts:
            raise ApiError('Máy không có trong danh sách')
        return {'ok': True, 'given': api_star({'hosts': [h]})['given']}
    if op == 'draw':
        r = api_draw({'announce': True, 'hide_name': bool(b.get('hide'))})
        return {'ok': True, 'name': r['name'], 'no': r['no'], 'cls': r['cls'], 'left': r['left']}
    raise ApiError('Lệnh không được hỗ trợ')


# ---------------------------------------------------------------- xử lý yêu cầu (tách khỏi socket để dễ kiểm thử)
def _key_ok(k):
    with PLOCK:
        return PH['on'] and time.time() < PH['exp'] and bool(k) and secrets.compare_digest(str(k), PH['token'])


def handle(ip, method, path, key, body=None):
    """Trả (mã, nội dung, kiểu). Mọi đường đều cần đúng mã phiên."""
    if not client_allowed(ip):
        return 403, {'error': 'Thiết bị này không được phép'}, 'json'
    now = time.time()
    with PLOCK:
        n, t0 = PH['fails'].get(ip, (0, now))
        if now - t0 > FAIL_WINDOW:
            n, t0 = 0, now
        if n >= MAX_FAILS:
            return 429, {'error': 'Thử sai quá nhiều lần, chờ vài phút'}, 'json'
    if not _key_ok(key):
        with PLOCK:
            PH['fails'][ip] = (n + 1, t0)
        return 403, {'error': 'Mã không đúng hoặc đã hết hạn. Hãy quét lại mã QR trên máy giáo viên.'}, 'json'
    with PLOCK:
        PH['fails'].pop(ip, None)
        d = PH['devices'].setdefault(ip, {'first': now, 'n': 0})
        d['last'] = now
        d['n'] += 1
    try:
        if method == 'GET' and path in ('/', '/index.html'):
            with open(os.path.join(WEB_DIR, 'phone.html'), 'r', encoding='utf-8') as f:
                return 200, f.read(), 'html'
        if method == 'GET' and path == '/state':
            return 200, phone_state(), 'json'
        if method == 'POST' and path == '/do':
            if not isinstance(body, dict):
                raise ApiError('Dữ liệu không hợp lệ')
            res = phone_do(body)
            log('📱 Điện thoại: %s' % body.get('op'), 'head')
            return 200, res, 'json'
    except ApiError as e:
        return 400, {'error': str(e)}, 'json'
    except Exception as e:  # noqa
        return 500, {'error': '%s: %s' % (type(e).__name__, e)}, 'json'
    return 404, {'error': 'Không tìm thấy'}, 'json'


class PHandler(http.server.BaseHTTPRequestHandler):
    server_version = 'KhoaVeyonPhone'
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass

    def _go(self, method):
        u = urllib.parse.urlparse(self.path)
        key = self.headers.get('X-Pk') or (urllib.parse.parse_qs(u.query).get('k') or [''])[0]
        body = None
        if method == 'POST':
            try:
                n = int(self.headers.get('Content-Length') or 0)
                body = json.loads(self.rfile.read(min(n, 8192)).decode('utf-8') or '{}') if n else {}
            except (ValueError, OSError):
                body = None
        code, payload, kind = handle(self.client_address[0], method, u.path, key, body)
        if kind == 'json':
            data, ct = json.dumps(payload, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8'
        else:
            data, ct = payload.encode('utf-8'), 'text/html; charset=utf-8'
        self.send_response(code)
        self.send_header('Content-Type', ct)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._go('GET')

    def do_POST(self):
        self._go('POST')


class PServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False


# ---------------------------------------------------------------- bật / tắt (giao diện giáo viên)
def _stop_locked():
    srv = PH.get('srv')
    PH.update(on=False, token='', exp=0.0, srv=None, url='')
    if srv:
        threading.Thread(target=lambda: (srv.shutdown(), srv.server_close()), daemon=True).start()


def _watch_expiry(token):
    while True:
        time.sleep(15)
        with PLOCK:
            if PH['token'] != token or not PH['on']:
                return
            if time.time() >= PH['exp']:
                _stop_locked()
                log('📱 Điều khiển bằng điện thoại đã hết hạn và tự tắt', 'head')
                return


def api_phone_state(_q=None):
    with PLOCK:
        if PH['on'] and time.time() >= PH['exp']:
            _stop_locked()
        on = PH['on']
        out = {'on': on, 'url': PH['url'], 'left': max(0, int(PH['exp'] - time.time())) if on else 0, 'port': PH['port'],
               'devices': [{'ip': ip, 'last': int(time.time() - d.get('last', 0)), 'n': d['n']} for ip, d in PH['devices'].items()]}
    out['qr'] = _qr_svg(out['url']) if on else ''
    return out


def api_phone_start(b):
    try:
        hours = max(1, min(12, int(b.get('hours') or 4)))
    except (TypeError, ValueError):
        hours = 4
    with PLOCK:
        _stop_locked()
        srv = None
        for port in PORTS:
            try:
                srv = PServer(('0.0.0.0', port), PHandler)
                break
            except OSError:
                continue
        if not srv:
            raise ApiError('Không mở được cổng cho điện thoại (cổng 8768 đang bận hoặc tường lửa chặn)')
        tok = secrets.token_urlsafe(16)
        port = srv.server_address[1]
        PH.update(on=True, token=tok, exp=time.time() + hours * 3600, port=port, srv=srv, devices={}, fails={},
                  url='http://%s:%d/?k=%s' % (lan_ip(), port, tok))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        threading.Thread(target=_watch_expiry, args=(tok,), daemon=True).start()
    log('📱 Bật điều khiển bằng điện thoại (%d giờ), cổng %d' % (hours, port), 'head')
    return api_phone_state()


def api_phone_stop(_b=None):
    with PLOCK:
        _stop_locked()
    log('📱 Đã tắt điều khiển bằng điện thoại', 'head')
    return api_phone_state()
