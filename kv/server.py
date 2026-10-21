# -*- coding: utf-8 -*-
"""Máy chủ HTTP nội bộ (127.0.0.1) phục vụ giao diện web và API."""

import http.server
import json
import os
import re
import secrets
import tempfile
import urllib.parse

from .alerts import _rm
from .applock import applock_is_locked
from .evidence import evidence_root
from .privacy import images_blocked
from .routes import GET_ROUTES, POST_ROUTES
from .runtime import ApiError, ASSET_TYPES, log, MAX_UPLOAD, PAYLOAD_DIR, STATE, WEB_DIR
from .school_api import api_school, school_import


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = 'KhoaVeyon'
    protocol_version = 'HTTP/1.1'

    def log_message(self, *args):  # không ghi log truy cập
        pass

    def _send(self, code, body, ctype='application/json; charset=utf-8', filename=''):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        elif isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if filename:
            self.send_header('Content-Disposition', "attachment; filename*=UTF-8''" + urllib.parse.quote(filename))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def _host_ok(self):
        h = (self.headers.get('Host') or '').lower()
        return h in ('127.0.0.1:%d' % STATE['port'], 'localhost:%d' % STATE['port'])

    def _locked(self, path):
        """Đang khóa màn hình: chặn mọi API trừ chính /api/applock (xem trạng thái, nhập mật khẩu mở khóa). Trả True nếu đã chặn."""
        if path != '/api/applock' and applock_is_locked():
            self._send(423, {'error': 'Ứng dụng đang khóa', 'locked': True})
            return True
        return False

    def _token_ok(self):
        return secrets.compare_digest(self.headers.get('X-Token') or '', STATE['token'])

    def _guard(self):
        if not self._host_ok():
            self._send(403, {'error': 'Host không hợp lệ'})
            return False
        return True

    def _api(self, fn, arg):
        try:
            self._send(200, fn(arg))
        except ApiError as e:
            self._send(400, {'error': str(e)})
        except Exception as e:  # noqa
            self._send(500, {'error': '%s: %s' % (type(e).__name__, e)})

    def do_GET(self):
        if not self._guard():
            return
        u = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        if u.path == '/':
            if not secrets.compare_digest(q.get('t', ''), STATE['token']):
                self._send(403, '<meta charset="utf-8"><h3>Hãy mở chương trình bằng Chay-KhoaVeyon.bat</h3>',
                           'text/html; charset=utf-8')
                return
            try:
                with open(os.path.join(WEB_DIR, 'index.html'), 'r', encoding='utf-8') as f:
                    html = f.read()
            except OSError:
                self._send(500, '<meta charset="utf-8"><h3>Thiếu thư mục web (web\\index.html)</h3>',
                           'text/html; charset=utf-8')
                return
            self._send(200, html.replace('__TOKEN__', STATE['token']), 'text/html; charset=utf-8')
        elif u.path == '/favicon.ico' or u.path.startswith(('/assets/', '/css/', '/js/')):  # logo, icon, mã giao diện (chỉ file trong web\assets, web\css, web\js)
            sub, name = ('assets', 'icon.ico') if u.path == '/favicon.ico' else (u.path.split('/')[1], os.path.basename(u.path))
            ctype = ASSET_TYPES.get(os.path.splitext(name)[1].lower())
            fp = os.path.join(WEB_DIR, sub, name)
            if not ctype or not os.path.isfile(fp):
                self._send(404, {'error': 'Không có file'})
                return
            with open(fp, 'rb') as f:
                self._send(200, f.read(), ctype)
        elif u.path.startswith('/evidence/'):  # ảnh vi phạm (thẻ <img> không gửi được header nên dùng ?t=mã bảo vệ)
            if not secrets.compare_digest(q.get('t', ''), STATE['token']):
                self._send(403, {'error': 'Sai mã bảo vệ'})
                return
            if applock_is_locked():
                self._send(423, {'error': 'Ứng dụng đang khóa', 'locked': True})
                return
            base = os.path.realpath(evidence_root())
            p = os.path.realpath(os.path.join(base, *urllib.parse.unquote(u.path[len('/evidence/'):]).split('/')))
            try:
                inside = os.path.commonpath([base, p]) == base
            except ValueError:
                inside = False
            if images_blocked():
                self._send(403, {'error': 'Ảnh đang khóa, hãy nhập mã xem ảnh'})
                return
            if not inside or not p.lower().endswith('.jpg') or not os.path.isfile(p):
                self._send(404, {'error': 'Không tìm thấy ảnh'})
                return
            with open(p, 'rb') as f:
                self._send(200, f.read(), 'image/jpeg')
        elif u.path == '/api/download':   # tải file: sao lưu, Excel mẫu (cần X-Token)
            if not self._token_ok():
                self._send(403, {'error': 'Sai mã bảo vệ'})
                return
            if self._locked(u.path):
                return
            try:
                data, name = self._download(q)
            except ApiError as e:
                self._send(400, {'error': str(e)})
                return
            except Exception as e:  # noqa
                self._send(500, {'error': '%s: %s' % (type(e).__name__, e)})
                return
            self._send(200, data, 'application/octet-stream', name)
        elif u.path in GET_ROUTES:
            if not self._token_ok():
                self._send(403, {'error': 'Sai mã bảo vệ'})
                return
            if self._locked(u.path):
                return
            self._api(GET_ROUTES[u.path], q)
        else:
            self._send(404, {'error': 'Không tìm thấy'})

    @staticmethod
    def _download(q):
        what = q.get('what')
        if what == 'backup':
            from .backup import backup_name, make_backup
            return make_backup(q.get('secrets') != '0'), backup_name()
        if what == 'timetable':
            from .school import school_bells
            from .templates import bell_set, timetable_template
            return timetable_template(bell_set(q.get('set', '')) or school_bells()), 'Thoi-khoa-bieu-mau.xlsx'
        if what == 'classes':
            from .templates import classes_template
            return classes_template(), 'Danh-sach-lop-mau.xlsx'
        raise ApiError('Không có file này')

    def do_POST(self):
        if not self._guard():
            return
        u = urllib.parse.urlparse(self.path)
        n = int(self.headers.get('Content-Length') or 0)
        raw = self.rfile.read(n) if n else b''
        if u.path not in POST_ROUTES:
            self._send(404, {'error': 'Không tìm thấy'})
            return
        if not self._token_ok():
            self._send(403, {'error': 'Sai mã bảo vệ'})
            return
        if self._locked(u.path):
            return
        try:
            body = json.loads(raw.decode('utf-8') or '{}')
        except Exception:  # noqa
            self._send(400, {'error': 'Dữ liệu gửi lên không hợp lệ'})
            return
        self._api(POST_ROUTES[u.path], body if isinstance(body, dict) else {})

    def _school_upload(self, u, n):
        """PUT /api/school_upload?kind=classes|timetable&name=...: nhập file Excel, chỉ đọc rồi lưu dữ liệu, không chép xuống máy học sinh."""
        q = dict(urllib.parse.parse_qsl(u.query))
        kind = q.get('kind')
        if kind not in ('classes', 'timetable') or n <= 0 or n > 30 * 1024 * 1024:
            self.rfile.read(min(max(n, 0), MAX_UPLOAD))
            self._send(400, {'error': 'File không hợp lệ (tối đa 30 MB, định dạng .xlsx)'})
            return
        fname = os.path.basename(q.get('name', '')) or 'file.xlsx'
        body = self.rfile.read(n)
        if fname.lower().endswith(('.xls', '.csv')):
            self._send(400, {'error': 'File %s là định dạng cũ/không phải Excel mới. Mở bằng Excel, chọn Lưu thành (Save As) → Excel Workbook (.xlsx) rồi nhập lại.' % os.path.splitext(fname)[1]})
            return
        tmp = ''
        try:
            fd, tmp = tempfile.mkstemp(suffix='.json' if fname.lower().endswith('.json') else '.xlsx')
            with os.fdopen(fd, 'wb') as f:
                f.write(body)
            school_import(kind, tmp, fname)
            self._send(200, api_school())
        except ApiError as e:
            self._send(400, {'error': str(e)})
        except Exception as e:  # noqa
            self._send(400, {'error': 'Không đọc được file (%s). Hãy chọn file .xlsx (hoặc .json xuất từ KhoaTool).' % type(e).__name__})
        finally:
            if tmp:
                _rm(tmp)

    def do_PUT(self):
        """Tải file lên thư mục payload: PUT /api/upload?name=... (nội dung file là phần thân)."""
        if not self._guard():
            return
        u = urllib.parse.urlparse(self.path)
        n = int(self.headers.get('Content-Length') or 0)
        if u.path == '/api/school_upload' and self._token_ok():
            self._school_upload(u, n)
            return
        if u.path != '/api/upload' or not self._token_ok():
            self.rfile.read(min(n, MAX_UPLOAD))
            self._send(403, {'error': 'Không được phép'})
            return
        if n > MAX_UPLOAD:
            self._send(413, {'error': 'File quá lớn (tối đa 500 MB)'})
            return
        name = os.path.basename(urllib.parse.unquote(dict(urllib.parse.parse_qsl(u.query)).get('name', '')))
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip(' .')
        if not name:
            self.rfile.read(n)
            self._send(400, {'error': 'Thiếu tên file'})
            return
        os.makedirs(PAYLOAD_DIR, exist_ok=True)
        dest = os.path.join(PAYLOAD_DIR, name)
        left = n
        with open(dest, 'wb') as f:
            while left > 0:
                chunk = self.rfile.read(min(1024 * 1024, left))
                if not chunk:
                    break
                f.write(chunk)
                left -= len(chunk)
        log('Đã thêm file vào thư mục payload: %s' % name, 'ok')
        self._send(200, {'ok': True, 'name': name})


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False


def make_server():
    for port in (8765, 0):
        try:
            return Server(('127.0.0.1', port), Handler)
        except OSError:
            continue
    raise RuntimeError('Không mở được cổng mạng nội bộ')
