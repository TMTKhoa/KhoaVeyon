# -*- coding: utf-8 -*-
"""Kênh "Veyon Agent": máy giáo viên điều khiển máy học sinh KHÔNG cần tài khoản Windows quản trị, không cần
chia sẻ C$ và không cần Task Scheduler từ xa.

Cách hoạt động: dịch vụ KhoaVeyonAutoLog trên máy học sinh (chạy bằng SYSTEM, cài một lần bằng Setup-MayHocSinh.bat)
chủ động gọi ra máy giáo viên theo kiểu "hỏi việc" (long-poll HTTP). Máy giáo viên đặt việc vào hàng đợi, dịch vụ
nhận về, làm (chạy lệnh, chép file, đọc/xóa file) rồi gửi kết quả lại. Vì máy học sinh là bên gọi ra nên không cần
mở cổng nào trên máy học sinh.

Bảo mật: mọi gói tin đều ký HMAC-SHA256 bằng khóa bí mật chung (chỉ nằm trong thư mục Program Files của máy học sinh,
học sinh không đọc được). Khóa không bao giờ đi qua mạng. Học sinh nghe lén mạng cũng không giả được việc gửi cho dịch vụ.
"""

import base64
import hashlib
import hmac
import http.server
import json
import os
import secrets
import socket
import threading
import time

from .config import save_config
from .runtime import CFG, CFG_LOCK, log

PROTOCOL = 1
POLL_WAIT = 14            # giây giữ yêu cầu hỏi việc khi chưa có việc
ONLINE_SEC = 40           # quá chừng này giây không thấy dịch vụ hỏi việc thì coi là máy ngoại tuyến
CLOCK_SKEW = 900          # lệch đồng hồ cho phép giữa hai máy (giây)
MAX_BODY = 40 * 1024 * 1024
MAX_FILE = 25 * 1024 * 1024
DEFAULT_PORT = 8767

AGENTS = {}               # ip -> {'name', 'user', 'sessions', 'seen', 'ver', 'ip'}
QUEUES = {}               # ip -> list các việc chưa giao
PENDING = {}              # id việc -> {'event', 'result'}
NONCES = {}               # nonce đã dùng (chống phát lại) -> thời điểm
LOCK = threading.Condition()
SERVER = {'srv': None, 'port': 0}
_RES_CACHE = {}


class AgentError(OSError):
    """Lỗi khi nói chuyện với dịch vụ trên máy học sinh."""


def agent_token():
    """Khóa bí mật chung; tạo lần đầu rồi lưu vào file cài đặt (thư mục của máy giáo viên)."""
    with CFG_LOCK:
        t = str(CFG.get('agent_token') or '')
        if len(t) < 32:
            t = secrets.token_hex(32)
            CFG['agent_token'] = t
            try:
                save_config(CFG)
            except Exception:  # noqa
                pass
        return t


def agent_token_renew():
    with CFG_LOCK:
        CFG['agent_token'] = ''
    return agent_token()


def sign(data, token=None):
    return hmac.new((token or agent_token()).encode('ascii'), data, hashlib.sha256).hexdigest()


def lan_ip():
    """IP LAN của máy giáo viên (cái mà máy học sinh gọi tới)."""
    with CFG_LOCK:
        forced = str(CFG.get('agent_host') or '').strip()
    if forced:
        return forced
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        return s.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return '127.0.0.1'
    finally:
        s.close()


def agent_port():
    with CFG_LOCK:
        try:
            p = int(str(CFG.get('agent_port') or DEFAULT_PORT))
        except ValueError:
            p = DEFAULT_PORT
    return p if 1024 <= p <= 65535 else DEFAULT_PORT


def agent_url():
    return 'http://%s:%d' % (lan_ip(), SERVER['port'] or agent_port())


AGENT_CFG_NAME = 'KhoaVeyonAgent.cfg'


def agent_config_text(script_sha=''):
    """Nội dung agent.cfg cài lên máy học sinh (Setup-MayHocSinh.bat chép vào Program Files, chỉ SYSTEM/Admin đọc được).
    sha = mã SHA-256 của KhoaVeyonServices.bat chuẩn, để máy mới cài tải đúng bản từ máy giáo viên."""
    t = 'url=%s\r\ntoken=%s\r\n' % (agent_url(), agent_token())
    if script_sha:
        t += 'sha=%s\r\n' % script_sha
    return t


def agent_firewall_rule():
    """Mở cổng Agent trên tường lửa máy giáo viên (cần quyền quản trị). Trả về (ok, mô tả)."""
    if os.name != 'nt':
        return True, 'bỏ qua (không phải Windows)'
    import subprocess
    port = SERVER['port'] or agent_port()
    rng = '%d-%d' % (agent_port(), agent_port() + 2)   # cổng chính và hai cổng dự phòng
    name = 'KhoaVeyon Agent'
    subprocess.run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule', 'name=' + name], capture_output=True, creationflags=0x08000000)
    r = subprocess.run(['netsh', 'advfirewall', 'firewall', 'add', 'rule', 'name=' + name, 'dir=in', 'action=allow', 'protocol=TCP',
                        'localport=' + rng, 'profile=any'], capture_output=True, text=True, errors='replace', creationflags=0x08000000)
    ok = r.returncode == 0
    return ok, ('đã mở cổng %d trên tường lửa máy giáo viên' % port) if ok else ('chưa mở được cổng %d (cần quyền quản trị): %s' % (port, (r.stdout + r.stderr).strip()[:160]))


# ---------------------------------------------------------------- nhận diện máy

def _resolve(host):
    now = time.time()
    hit = _RES_CACHE.get(host)
    if hit and now - hit[0] < 60:
        return hit[1]
    try:
        ip = socket.gethostbyname(host)
    except OSError:
        ip = ''
    _RES_CACHE[host] = (now, ip)
    return ip


def agent_key(host):
    """Khóa của máy trong bảng AGENTS (IP), hoặc '' nếu chưa có dịch vụ nào của máy này gọi về."""
    h = (host or '').strip()
    if not h:
        return ''
    h = h.rsplit(':', 1)[0] if h.count(':') == 1 and h.rsplit(':', 1)[1].isdigit() else h
    with LOCK:
        if h in AGENTS:
            return h
        low = h.split('.')[0].lower()
        for ip, a in AGENTS.items():
            if str(a.get('name', '')).lower() == low:
                return ip
    ip = _resolve(h)
    with LOCK:
        return ip if ip in AGENTS else ''


def agent_online(host):
    k = agent_key(host)
    if not k:
        return False
    with LOCK:
        a = AGENTS.get(k)
        return bool(a) and time.time() - a['seen'] < ONLINE_SEC


def agent_info(host):
    k = agent_key(host)
    with LOCK:
        a = AGENTS.get(k)
        return dict(a) if a else None


def agent_list():
    now = time.time()
    with LOCK:
        return [dict(a, online=(now - a['seen'] < ONLINE_SEC), age=int(now - a['seen'])) for a in AGENTS.values()]


# ---------------------------------------------------------------- gọi việc

def agent_call(host, job, timeout=60):
    """Đặt một việc cho dịch vụ trên máy `host` rồi chờ kết quả. Trả về dict kết quả; ném AgentError nếu lỗi/quá hạn."""
    k = agent_key(host)
    if not k or not agent_online(host):
        raise AgentError('Dịch vụ KhoaVeyon trên máy này chưa kết nối về máy giáo viên (máy tắt, chưa cài Agent hoặc tường lửa máy giáo viên chặn cổng %d)' % (SERVER['port'] or agent_port()))
    job = dict(job)
    job['id'] = secrets.token_hex(8)
    ev = threading.Event()
    slot = {'event': ev, 'result': None}
    with LOCK:
        PENDING[job['id']] = slot
        QUEUES.setdefault(k, []).append(job)
        LOCK.notify_all()
    if not ev.wait(timeout):
        with LOCK:
            PENDING.pop(job['id'], None)
            q = QUEUES.get(k) or []
            if job in q:
                q.remove(job)
        raise AgentError('Quá thời gian chờ máy học sinh trả lời')
    with LOCK:
        PENDING.pop(job['id'], None)
    return slot['result']


# ---------------------------------------------------------------- máy chủ cho dịch vụ học sinh

def _prune_nonces(now):
    if len(NONCES) > 4000:
        for n in [n for n, t in NONCES.items() if now - t > CLOCK_SKEW * 2]:
            NONCES.pop(n, None)


class AgentHandler(http.server.BaseHTTPRequestHandler):
    server_version = 'KhoaVeyonAgent'
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass

    def _send(self, code, obj, signed=True):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        if signed:
            self.send_header('X-KV-Sig', sign(body))
        self.end_headers()
        self.wfile.write(body)

    def _read_signed(self):
        """Đọc thân yêu cầu, kiểm tra chữ ký, thời gian, nonce. Trả về dict hoặc None (đã trả lỗi)."""
        try:
            n = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            n = -1
        if n < 0 or n > MAX_BODY:
            self._send(413, {'error': 'too big'}, signed=False)
            return None
        raw = self.rfile.read(n)
        if not hmac.compare_digest(self.headers.get('X-KV-Sig') or '', sign(raw)):
            self._send(403, {'error': 'bad signature'}, signed=False)
            return None
        try:
            d = json.loads(raw.decode('utf-8'))
            ts = float(d.get('ts'))
            nonce = str(d.get('nonce') or '')
        except (ValueError, TypeError, AttributeError):
            self._send(400, {'error': 'bad request'}, signed=False)
            return None
        now = time.time()
        if abs(now - ts) > CLOCK_SKEW or len(nonce) < 8:
            self._send(403, {'error': 'bad time'}, signed=False)
            return None
        with LOCK:
            if nonce in NONCES:
                self._send(403, {'error': 'replay'}, signed=False)
                return None
            NONCES[nonce] = now
            _prune_nonces(now)
        return d

    def do_GET(self):
        """Máy học sinh mới cài (chưa có KhoaVeyonServices.bat) tải bản chuẩn từ đây. Không cần khóa vì cấu hình Agent
        đã ghim sẵn mã SHA-256 của file: tải về sai mã thì Setup xóa đi."""
        path = self.path.split('?')[0]
        pre = '/agent/boot/'
        if not path.startswith(pre):
            self._send(404, {'error': 'not found'}, signed=False)
            return
        name = os.path.basename(path[len(pre):])
        from .runtime import PAYLOAD_DIR
        with CFG_LOCK:
            want = os.path.basename((CFG.get('script_path') or '').replace('\\', '/')) or 'KhoaVeyonServices.bat'
        fp = os.path.join(PAYLOAD_DIR, name)
        if name != want or not os.path.isfile(fp):
            self._send(404, {'error': 'not found'}, signed=False)
            return
        with open(fp, 'rb') as f:
            body = f.read()
        self.send_response(200)
        self.send_header('Content-Type', 'application/octet-stream')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        path = self.path.split('?')[0]
        if path not in ('/agent/poll', '/agent/result'):
            self._send(404, {'error': 'not found'}, signed=False)
            return
        d = self._read_signed()
        if d is None:
            return
        ip = self.client_address[0]
        if path == '/agent/result':
            with LOCK:
                slot = PENDING.get(str(d.get('id') or ''))
            if slot:
                slot['result'] = d
                slot['event'].set()
            self._send(200, {'ok': True, 'nonce': d.get('nonce')})
            return
        # ---- poll
        with LOCK:
            info = AGENTS.setdefault(ip, {'ip': ip})
            info.update({'name': str(d.get('host') or '')[:64], 'user': str(d.get('user') or '')[:96],
                         'sessions': d.get('sessions') or [], 'ver': d.get('ver') or 0, 'boot': d.get('boot') or 0,
                         'seen': time.time()})
            end = time.time() + POLL_WAIT
            jobs = []
            while True:
                q = QUEUES.get(ip) or []
                if q:
                    jobs, QUEUES[ip] = q[:4], q[4:]
                    break
                left = end - time.time()
                if left <= 0:
                    break
                LOCK.wait(min(left, 2))
                AGENTS[ip]['seen'] = time.time()
        self._send(200, {'nonce': d.get('nonce'), 'ts': time.time(), 'jobs': jobs})


class AgentServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def agent_start():
    """Mở cổng cho dịch vụ trên máy học sinh gọi về. Lỗi (cổng bận) thì chỉ báo, các chức năng cũ qua C$ vẫn chạy."""
    if SERVER['srv']:
        return True
    agent_token()
    first = agent_port()
    for port in (first, first + 1, first + 2):
        try:
            srv = AgentServer(('0.0.0.0', port), AgentHandler)
        except OSError:
            continue
        SERVER.update({'srv': srv, 'port': port})
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        log('Kênh Agent mở ở cổng %d (dịch vụ trên máy học sinh sẽ tự gọi về đây)' % port, 'ok')
        return True
    log('Không mở được cổng Agent %d: kênh Agent tạm tắt, vẫn dùng được cách cũ qua C$.' % first, 'warn')
    return False


def agent_stop():
    srv = SERVER['srv']
    if srv:
        srv.shutdown()
        srv.server_close()
        SERVER.update({'srv': None, 'port': 0})


# ---------------------------------------------------------------- giao diện

def api_agent(b=None):
    b = b or {}
    act = b.get('action') if isinstance(b, dict) else None
    if act == 'renew':
        agent_token_renew()
        from .setup import refresh_agent_cfg
        refresh_agent_cfg()
        log('Đã đổi khóa Agent: các máy học sinh phải cài lại Agent (Setup-MayHocSinh.bat) để dùng khóa mới.', 'warn')
    return {'url': agent_url(), 'port': SERVER['port'] or agent_port(), 'listening': bool(SERVER['srv']),
            'agents': agent_list(), 'token_tail': agent_token()[-6:]}
