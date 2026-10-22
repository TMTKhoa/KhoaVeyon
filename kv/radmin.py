# -*- coding: utf-8 -*-
"""Quản trị lớp từ laptop riêng của giáo viên: máy chủ trung gian (reverse proxy) trên mạng LAN, đăng nhập bằng mã PIN 6 số ngẫu nhiên.
Mã bảo vệ thật của chương trình không bao giờ rời khỏi máy giáo viên: laptop chỉ có phiên đăng nhập riêng, máy chủ trung gian đổi sang mã thật khi chuyển tiếp."""

import http.client
import http.server
import ipaddress
import json
import secrets
import threading
import time
import urllib.parse

from .agent import lan_ip
from .phone import _student_ips
from .runtime import ApiError, log, STATE

RA = {'on': False, 'pin': '', 'vpin': '', 'exp': 0.0, 'port': 0, 'srv': None, 'url': '', 'full': False, 'sessions': {}, 'fails': {}, 'gfails': 0}
RLOCK = threading.RLock()
PORTS = (8769, 0)
MAX_IP_FAILS, IP_LOCK_SEC, MAX_GLOBAL_FAILS = 5, 900, 30
# Vai trò "chỉ xem" (PIN riêng): chỉ đọc sơ đồ lớp / Monitor, dùng được cả trên máy trong phòng
VIEW_GET = ('/api/monitor', '/api/school', '/api/school_attendance', '/api/school_students', '/api/ui_prefs', '/api/ping')
MAX_BODY = 48 * 1024 * 1024
SESSION_SEC = 8 * 3600

# Không bao giờ cho đi qua laptop (kể cả "toàn quyền"): xem/đổi PIN, mã QR điện thoại, thoát chương trình, mở thư mục trên máy giáo viên, khóa ứng dụng, mã xem ảnh
ALWAYS_PREFIX = ('/api/radmin', '/api/phone')
ALWAYS_DENY = ('/api/quit', '/api/open', '/api/evidence_open', '/api/applock', '/api/privacy_pin', '/api/privacy_acl', '/api/startup')
# Chế độ "Quản trị lớp" (mặc định) còn chặn thêm: chạy lệnh/cài đặt lên máy học sinh, khôi phục, cập nhật, tải tệp, đổi cài đặt hệ thống
CLASS_DENY = ('/api/run', '/api/dist', '/api/payload_delete', '/api/upload', '/api/backup_restore', '/api/update_apply', '/api/update_students', '/api/setup_run', '/api/setup_scan',
              '/api/setup_done', '/api/vcfg_run', '/api/vcfg_save', '/api/settings', '/api/logon_policy', '/api/health_fix', '/api/diagnose_fix', '/api/cleanup', '/api/agent', '/api/watch',
              '/api/sync', '/api/hosts', '/api/macs_set', '/api/hostname_set', '/api/selftest', '/api/payload')

LOGIN_HTML = '''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>KhoaVeyon - Đăng nhập</title>
<style>body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#0f172a;font:16px system-ui,sans-serif;color:#0f172a}
.b{background:#fff;border-radius:16px;padding:28px 32px;width:min(360px,90vw);text-align:center}h2{margin:0 0 6px}p{color:#64748b;margin:0 0 16px;font-size:14px}
input{font:700 30px ui-monospace,monospace;letter-spacing:.4em;text-align:center;width:100%;padding:10px;border:2px solid #cbd5e1;border-radius:12px;box-sizing:border-box}
button{margin-top:14px;width:100%;padding:12px;font:600 16px inherit;border:0;border-radius:12px;background:#2563eb;color:#fff}#e{color:#dc2626;min-height:22px;margin-top:10px;font-size:14px}</style></head>
<body><div class="b"><h2>🔐 Quản trị lớp</h2><p>Nhập mã PIN 6 số hiển thị trên máy giáo viên (PIN quản trị hoặc PIN chỉ xem sơ đồ)</p>
<input id="p" inputmode="numeric" maxlength="6" autocomplete="one-time-code" autofocus placeholder="••••••"><button id="g">Đăng nhập</button><div id="e"></div></div>
<script>const p=document.getElementById('p'),e=document.getElementById('e');
async function go(){e.textContent='';try{const r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pin:p.value})});const j=await r.json().catch(()=>({}));
if(r.ok){location.href='/?t=remote'}else{e.textContent=j.error||('Lỗi '+r.status);p.value='';p.focus()}}catch(x){e.textContent='Không kết nối được'}}
document.getElementById('g').onclick=go;p.addEventListener('keydown',ev=>{if(ev.key==='Enter')go()});p.addEventListener('input',()=>{p.value=p.value.replace(/\\D/g,'');if(p.value.length===6)go()});</script></body></html>'''


def ip_ok(ip):
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return a.is_private or a.is_loopback


def view_denied(path, method='GET'):
    return method != 'GET' or path.split('?')[0] not in VIEW_GET


def denied(path, method='GET'):
    p = path.split('?')[0]
    if p in ALWAYS_DENY or p.startswith(ALWAYS_PREFIX):
        return True
    with RLOCK:
        full = RA['full']
    return (not full) and p in CLASS_DENY


def _live():
    return RA['on'] and time.time() < RA['exp']


def _new_pin():
    return '%06d' % secrets.randbelow(10 ** 6)


def login(ip, pin):
    """Trả (mã, nội dung, sid hoặc None)."""
    now = time.time()
    with RLOCK:
        if not _live():
            return 403, {'error': 'Quản trị từ xa đang tắt'}, None
        n, t0 = RA['fails'].get(ip, (0, now))
        if now - t0 > IP_LOCK_SEC:
            n, t0 = 0, now
        if n >= MAX_IP_FAILS:
            return 429, {'error': 'Sai quá nhiều lần. Thiết bị này bị khóa %d phút.' % (IP_LOCK_SEC // 60)}, None
        pin = str(pin or '').strip()
        is_admin_ok = ip not in _student_ips() and secrets.compare_digest(pin, RA['pin'])   # máy học sinh không bao giờ vào được PIN quản trị
        is_view_ok = secrets.compare_digest(pin, RA['vpin'])
        if is_admin_ok or is_view_ok:
            role = 'admin' if is_admin_ok else 'view'
            RA['fails'].pop(ip, None)
            sid = secrets.token_urlsafe(32)
            RA['sessions'][sid] = {'ip': ip, 'exp': now + SESSION_SEC, 'fake': secrets.token_urlsafe(18), 'since': now, 'last': now, 'role': role}
            log('💻 Máy %s đăng nhập %s' % (ip, 'quản trị từ xa' if role == 'admin' else 'xem sơ đồ'), 'head')
            return 200, {'ok': True, 'role': role}, sid
        RA['fails'][ip] = (n + 1, t0)
        RA['gfails'] += 1
        if RA['gfails'] >= MAX_GLOBAL_FAILS:    # bị đoán PIN dồn dập từ nhiều nơi: tự tắt, giáo viên phải bật lại để có PIN mới
            _stop_locked()
            log('⚠ Quản trị từ xa tự tắt vì có quá nhiều lần nhập sai PIN', 'err')
            return 403, {'error': 'Quản trị từ xa đã tự tắt vì nhập sai quá nhiều'}, None
        return 403, {'error': 'PIN không đúng (còn %d lần thử)' % (MAX_IP_FAILS - n - 1)}, None


def session_for(ip, sid):
    with RLOCK:
        s = RA['sessions'].get(sid or '')
        if not s or not _live() or s['ip'] != ip or time.time() > s['exp']:
            return None
        s['last'] = time.time()
        return dict(s)


def forward(sess, method, path, body, headers):
    """Chuyển tiếp tới máy chủ nội bộ, thay mã bảo vệ giả của phiên bằng mã thật."""
    u = urllib.parse.urlsplit(path)
    q = urllib.parse.parse_qsl(u.query, keep_blank_values=True)
    real, fake = STATE['token'], sess['fake']
    is_index = u.path == '/'
    q = [(k, (real if (k == 't' and (v == fake or (is_index and v == 'remote'))) else v)) for k, v in q if not (k == 't' and v not in (fake, 'remote'))]
    target = u.path + ('?' + urllib.parse.urlencode(q) if q else '')
    h = {'Host': '127.0.0.1:%d' % STATE['port'], 'Content-Type': headers.get('Content-Type') or 'application/json'}
    if headers.get('X-Token') == fake:
        h['X-Token'] = real
    if body is not None:
        h['Content-Length'] = str(len(body))
    c = http.client.HTTPConnection('127.0.0.1', STATE['port'], timeout=130)
    try:
        c.request(method, target, body=body, headers=h)
        r = c.getresponse()
        data = r.read()
        ct = r.getheader('Content-Type') or 'application/octet-stream'
        cd = r.getheader('Content-Disposition')
    finally:
        c.close()
    if is_index and r.status == 200:
        data = data.replace(real.encode(), fake.encode())
        if sess.get('role') == 'view':
            data = data.replace(b'const TOKEN =', b'window.KV_VIEW = true; const TOKEN =', 1)
    return r.status, data, ct, cd


class RHandler(http.server.BaseHTTPRequestHandler):
    server_version = 'KhoaVeyonAdmin'
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass

    def _out(self, code, data, ct='application/json; charset=utf-8', extra=None):
        if isinstance(data, (dict, list)):
            data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        elif isinstance(data, str):
            data = data.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ct)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(data)

    def _cookie(self):
        for part in (self.headers.get('Cookie') or '').split(';'):
            k, _, v = part.strip().partition('=')
            if k == 'kvs':
                return v
        return ''

    def _origin_ok(self):
        o = self.headers.get('Origin')
        return not o or urllib.parse.urlsplit(o).netloc == (self.headers.get('Host') or '')

    def _go(self, method):
        ip = self.client_address[0]
        if not ip_ok(ip):
            return self._out(403, {'error': 'Thiết bị này không được phép'})
        path = self.path
        p = urllib.parse.urlsplit(path).path
        if p == '/login':
            if method == 'GET':
                return self._out(200, LOGIN_HTML, 'text/html; charset=utf-8')
            if not self._origin_ok():
                return self._out(403, {'error': 'Nguồn không hợp lệ'})
            try:
                n = int(self.headers.get('Content-Length') or 0)
                pin = (json.loads(self.rfile.read(min(n, 512)).decode('utf-8') or '{}') or {}).get('pin', '')
            except (ValueError, OSError, AttributeError):
                pin = ''
            code, out, sid = login(ip, pin)
            extra = {'Set-Cookie': 'kvs=%s; HttpOnly; SameSite=Strict; Path=/; Max-Age=%d' % (sid, SESSION_SEC)} if sid else None
            return self._out(code, out, extra=extra)
        if p == '/logout':
            with RLOCK:
                RA['sessions'].pop(self._cookie(), None)
            return self._out(200, '<meta charset="utf-8"><meta http-equiv="refresh" content="0;url=/login">Đã đăng xuất', 'text/html; charset=utf-8', {'Set-Cookie': 'kvs=; Max-Age=0; Path=/'})
        sess = session_for(ip, self._cookie())
        if not sess:
            if method == 'GET' and not p.startswith('/api/'):
                return self._out(302, '', extra={'Location': '/login'})
            return self._out(401, {'error': 'Chưa đăng nhập hoặc phiên đã hết hạn', 'login': True})
        if method == 'POST' and not self._origin_ok():
            return self._out(403, {'error': 'Nguồn không hợp lệ'})
        if sess.get('role') == 'view':
            if view_denied(path, method) and urllib.parse.urlsplit(path).path.startswith('/api/'):
                return self._out(403, {'error': 'Tài khoản chỉ xem'})
            if method != 'GET':
                return self._out(403, {'error': 'Tài khoản chỉ xem'})
        elif denied(path, method):
            return self._out(403, {'error': 'Chức năng này không mở cho quản trị từ xa' + ('' if RA['full'] else ' (bật "Toàn quyền" trên máy giáo viên nếu thật sự cần)')})
        body = None
        if method == 'POST':
            try:
                n = int(self.headers.get('Content-Length') or 0)
            except ValueError:
                n = 0
            if n > MAX_BODY:
                return self._out(413, {'error': 'Dữ liệu quá lớn'})
            body = self.rfile.read(n) if n else b''
        try:
            code, data, ct, cd = forward(sess, method, path, body, self.headers)
        except OSError as e:
            return self._out(502, {'error': 'Không nối được chương trình trên máy giáo viên: %s' % e})
        self._out(code, data, ct, {'Content-Disposition': cd} if cd else None)

    def do_GET(self):
        self._go('GET')

    def do_POST(self):
        self._go('POST')


class RServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False


def _stop_locked():
    srv = RA.get('srv')
    RA.update(on=False, pin='', vpin='', exp=0.0, srv=None, url='', sessions={}, fails={}, gfails=0)
    if srv:
        threading.Thread(target=lambda: (srv.shutdown(), srv.server_close()), daemon=True).start()


def _watch(pin):
    while True:
        time.sleep(15)
        with RLOCK:
            if RA['pin'] != pin or not RA['on']:
                return
            if time.time() >= RA['exp']:
                _stop_locked()
                log('💻 Quản trị từ xa đã hết hạn và tự tắt', 'head')
                return


def api_radmin_state(_q=None):
    with RLOCK:
        if RA['on'] and time.time() >= RA['exp']:
            _stop_locked()
        now = time.time()
        return {'on': RA['on'], 'pin': RA['pin'], 'vpin': RA['vpin'], 'url': RA['url'], 'full': RA['full'], 'left': max(0, int(RA['exp'] - now)) if RA['on'] else 0,
                'sessions': [{'ip': s['ip'], 'role': s.get('role', 'admin'), 'since': int(now - s['since']), 'last': int(now - s['last'])} for s in RA['sessions'].values()]}


def api_radmin_start(b):
    try:
        hours = max(1, min(12, int(b.get('hours') or 4)))
    except (TypeError, ValueError):
        hours = 4
    with RLOCK:
        keep_full = bool(b.get('full'))
        _stop_locked()
        srv = None
        for port in PORTS:
            try:
                srv = RServer(('0.0.0.0', port), RHandler)
                break
            except OSError:
                continue
        if not srv:
            raise ApiError('Không mở được cổng quản trị từ xa (cổng 8769 đang bận hoặc tường lửa chặn)')
        pin, vpin = _new_pin(), _new_pin()
        while vpin == pin:
            vpin = _new_pin()
        port = srv.server_address[1]
        RA.update(on=True, pin=pin, vpin=vpin, exp=time.time() + hours * 3600, port=port, srv=srv, full=keep_full, sessions={}, fails={}, gfails=0,
                  url='http://%s:%d/' % (lan_ip(), port))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        threading.Thread(target=_watch, args=(pin,), daemon=True).start()
    log('💻 Bật quản trị từ xa (%d giờ, %s), cổng %d' % (hours, 'toàn quyền' if keep_full else 'quản trị lớp', port), 'head')
    return api_radmin_state()


def api_radmin_newpin(_b=None):
    with RLOCK:
        if not _live():
            raise ApiError('Quản trị từ xa đang tắt')
        pin, vpin = _new_pin(), _new_pin()
        while vpin == pin:
            vpin = _new_pin()
        RA.update(pin=pin, vpin=vpin, sessions={}, fails={}, gfails=0)
    log('💻 Đã đổi PIN quản trị từ xa, các phiên cũ bị đăng xuất', 'head')
    return api_radmin_state()


def api_radmin_stop(_b=None):
    with RLOCK:
        _stop_locked()
    log('💻 Đã tắt quản trị từ xa', 'head')
    return api_radmin_state()
