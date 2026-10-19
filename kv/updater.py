# -*- coding: utf-8 -*-
"""Tự cập nhật từ GitHub Releases (kiểm tra bản mới, tải, thay file chương trình, chạy lại)."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from .paths import APP_DIR, ENTRY_SCRIPT, VERSION
from .runtime import ApiError, CFG, CFG_LOCK, log, STATE


UPDATE_FILES = ('KhoaVeyon.py', 'Chay-KhoaVeyon.bat', 'Tao-ShortCut.bat', 'README-KhoaVeyon.md', 'requirements.txt')
UPDATE_DIRS = ('web', 'kv', 'scripts')          # chỉ ghi đè mã chương trình; data, lists, payload, runtime của bạn không bị đụng tới
UPDATE_MAX = 60 * 1024 * 1024
UPDATE_HOSTS = ('github.com', 'githubusercontent.com')


def _ver(text):
    nums = re.findall(r'\d+', str(text))
    return tuple(int(x) for x in nums[:4]) or (0,)


def _host_ok(url):
    h = (urllib.parse.urlparse(url).hostname or '').lower()
    return urllib.parse.urlparse(url).scheme == 'https' and any(h == d or h.endswith('.' + d) for d in UPDATE_HOSTS)


def _http_get(url, timeout=15, limit=UPDATE_MAX, trusted=False):
    if not trusted and not _host_ok(url):
        raise ApiError('Địa chỉ cập nhật không hợp lệ (chỉ chấp nhận https của GitHub)')
    req = urllib.request.Request(url, headers={'User-Agent': 'KhoaVeyon/' + VERSION, 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read(limit + 1)
    if len(data) > limit:
        raise ApiError('File cập nhật quá lớn')
    return data


def _net_reason(e):
    """Giải thích lỗi mạng bằng tiếng Việt, tách rõ: mất mạng / DNS / chứng chỉ (antivirus, proxy trường) / quá hạn."""
    import socket
    import ssl
    r = getattr(e, 'reason', e)
    if isinstance(r, ssl.SSLError) or 'CERTIFICATE' in str(r).upper():
        return 'chứng chỉ HTTPS bị từ chối (thường do antivirus hoặc proxy/tường lửa của trường chặn kiểm tra SSL): %s' % r
    if isinstance(r, socket.gaierror):
        return 'không phân giải được tên github.com (kiểm tra DNS / mạng): %s' % r
    if isinstance(r, (socket.timeout, TimeoutError)):
        return 'quá thời gian chờ GitHub (mạng chậm hoặc bị chặn)'
    return str(r)


def _from_branch(repo):
    """Kho chưa tạo Release/tag: lấy số bản từ kv/paths.py của nhánh mặc định và tải zip của nhánh đó."""
    raw = _http_get('https://raw.githubusercontent.com/%s/HEAD/kv/paths.py' % repo).decode('utf-8', 'replace')
    m = re.search(r"VERSION\s*=\s*['\"]([^'\"]+)['\"]", raw)
    if not m:
        raise ApiError('Kho %s không có kv/paths.py với dòng VERSION: có đúng kho KhoaVeyon không?' % repo)
    tag = m.group(1)
    return {'current': VERSION, 'latest': tag, 'newer': _ver(tag) > _ver(VERSION),
            'url': 'https://github.com/%s/archive/HEAD.zip' % repo,
            'notes': 'Kho chưa có Release: so sánh số VERSION trong mã nguồn nhánh chính (HEAD).', 'page': 'https://github.com/%s' % repo}


def check_update(repo, api_base='https://api.github.com', trusted=False):
    """Hỏi GitHub xem có bản mới hơn VERSION không (Release mới nhất; không có thì tag; không có nữa thì VERSION trong nhánh chính). Không tải gì về."""
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo or ''):
        raise ApiError('Chưa điền kho GitHub (dạng chủ-sở-hữu/tên-kho) ở trang Cài đặt')
    try:
        data = json.loads(_http_get('%s/repos/%s/releases/latest' % (api_base, repo), trusted=trusted).decode('utf-8'))
    except ApiError:
        raise
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Chưa có Release: thử tag, rồi thử đọc thẳng VERSION trong nhánh chính (kho công khai)
            try:
                tags = json.loads(_http_get('%s/repos/%s/tags' % (api_base, repo), trusted=trusted).decode('utf-8'))
                if tags:
                    tg = str(tags[0].get('name') or '')
                    return {'current': VERSION, 'latest': tg, 'newer': _ver(tg) > _ver(VERSION),
                            'url': 'https://github.com/%s/archive/refs/tags/%s.zip' % (repo, tg) if not trusted else '',
                            'notes': '', 'page': 'https://github.com/%s/releases/tag/%s' % (repo, tg)}
            except Exception:  # noqa
                pass
            if api_base == 'https://api.github.com':
                try:
                    return _from_branch(repo)
                except urllib.error.HTTPError as e2:
                    raise ApiError('Không thấy kho %s trên GitHub (mã %s). Kiểm tra tên kho ở trang Cài đặt (mặc định TMTKhoa/KhoaVeyon là kho của tác giả, hãy điền kho CỦA BẠN) và kho phải ở chế độ Public.' % (repo, e2.code))
                except ApiError:
                    raise
                except Exception as e2:  # noqa
                    raise ApiError('Không kiểm tra được bản mới: %s' % _net_reason(e2))
            raise ApiError('Kho %s chưa có Release nào (hoặc là kho riêng tư).' % repo)
        if e.code in (403, 429):
            raise ApiError('GitHub giới hạn số lần hỏi của địa chỉ IP này (60 lần/giờ khi chưa đăng nhập, mạng trường dùng chung một IP nên dễ hết). Thử lại sau ít phút.')
        raise ApiError('GitHub trả lỗi %s khi kiểm tra bản mới' % e.code)
    except Exception as e:  # noqa
        raise ApiError('Không kiểm tra được bản mới, không phải lỗi kho: %s' % _net_reason(e))
    tag = str(data.get('tag_name') or '')
    url = ''
    for a in data.get('assets') or []:
        n = str(a.get('name', ''))
        if n.lower().endswith('.zip') and 'khoaveyon' in n.lower():
            url = a.get('browser_download_url', '')
            break
    url = url or data.get('zipball_url', '')
    return {'current': VERSION, 'latest': tag, 'newer': _ver(tag) > _ver(VERSION), 'url': url,
            'notes': str(data.get('body') or '')[:1500], 'page': data.get('html_url', '')}


def apply_update(url, app_dir=None, trusted=False):
    """Tải bản mới, chỉ thay file chương trình (có sao lưu bản cũ). Trả về danh sách file đã thay."""
    app_dir = app_dir or APP_DIR
    blob = _http_get(url, timeout=60, trusted=trusted)
    tmp = tempfile.mkdtemp(prefix='khoaveyon-upd-')
    try:
        zp = os.path.join(tmp, 'u.zip')
        with open(zp, 'wb') as f:
            f.write(blob)
        with zipfile.ZipFile(zp) as z:
            names = z.namelist()
            for n in names:
                parts = n.replace('\\', '/').split('/')
                if n.startswith(('/', '\\')) or '..' in parts or ':' in parts[0]:
                    raise ApiError('File cập nhật có đường dẫn không an toàn, đã dừng')
            mains = [n for n in names if n.replace('\\', '/').split('/')[-1] == 'KhoaVeyon.py']
            if not mains:
                raise ApiError('File cập nhật không phải bản KhoaVeyon (thiếu KhoaVeyon.py)')
            root = min(mains, key=len)[:-len('KhoaVeyon.py')]
            z.extractall(os.path.join(tmp, 'x'))
        base = os.path.join(tmp, 'x', root.replace('/', os.sep))
        src_py = os.path.join(base, 'KhoaVeyon.py')
        try:
            compile(open(src_py, 'r', encoding='utf-8').read(), src_py, 'exec')
        except SyntaxError as e:
            raise ApiError('Bản cập nhật bị lỗi cú pháp, giữ nguyên bản hiện tại: %s' % e)
        pkg = os.path.join(base, 'kv')
        if not os.path.isfile(os.path.join(pkg, 'app.py')):
            raise ApiError('File cập nhật thiếu thư mục kv (mã chương trình), giữ nguyên bản hiện tại')
        for fn in sorted(os.listdir(pkg)):
            if fn.endswith('.py'):
                fp = os.path.join(pkg, fn)
                try:
                    with open(fp, 'r', encoding='utf-8') as f:
                        compile(f.read(), fp, 'exec')
                except SyntaxError as e:
                    raise ApiError('Bản cập nhật bị lỗi cú pháp ở kv/%s, giữ nguyên bản hiện tại: %s' % (fn, e))
        todo = []
        for f in UPDATE_FILES:
            if os.path.isfile(os.path.join(base, f)):
                todo.append(f)
        for d in UPDATE_DIRS:
            for dp, _dn, fn in os.walk(os.path.join(base, d)):
                for f in fn:
                    todo.append(os.path.relpath(os.path.join(dp, f), base))
        bk = os.path.join(app_dir, 'data', 'backup-' + VERSION)
        for rel in todo:
            dst = os.path.join(app_dir, rel)
            if os.path.isfile(dst):
                os.makedirs(os.path.dirname(os.path.join(bk, rel)), exist_ok=True)
                shutil.copy2(dst, os.path.join(bk, rel))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(base, rel), dst + '.new')
            os.replace(dst + '.new', dst)
        return todo
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def restart_self():
    """Mở bản mới (đợi bản này tắt xong) rồi tắt máy chủ hiện tại."""
    flags = (0x00000008 | 0x00000200) if os.name == 'nt' else 0   # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([sys.executable, ENTRY_SCRIPT, '--after-update'], cwd=APP_DIR, close_fds=True,
                     creationflags=flags)
    srv = STATE.get('server')
    if srv:
        threading.Timer(0.8, srv.shutdown).start()


UPDATE_EVERY = 6 * 3600   # hỏi GitHub lại mỗi 6 giờ khi chương trình chạy lâu (không tải gì về, chỉ hỏi số bản mới nhất)


def update_check_once():
    """Hỏi GitHub một lần. Có bản mới thì ghi vào STATE['update'] để giao diện hiện hộp thoại hỏi giáo viên."""
    with CFG_LOCK:
        repo, auto = CFG.get('update_repo', ''), CFG.get('update_auto')
    try:
        info = check_update(repo)
    except Exception as e:  # noqa
        log('Kiểm tra bản mới lỗi: %s' % e, 'warn')
        return
    old = STATE.get('update') or {}
    STATE['update'] = info
    if not info['newer']:
        return
    if old.get('latest') != info['latest']:
        log('Có bản mới %s (đang dùng %s).' % (info['latest'], info['current']), 'warn')
    if auto and info['url']:
        try:
            files = apply_update(info['url'])
            log('Đã tự cập nhật %d file lên %s, đang khởi động lại...' % (len(files), info['latest']), 'ok')
            restart_self()
        except Exception as e:  # noqa
            log('Tự cập nhật lỗi, giữ nguyên bản cũ: %s' % e, 'err')


def update_loop():
    """Chạy nền: kiểm tra khi mở chương trình, rồi định kỳ nếu bật \"Tự kiểm tra bản mới\" và đã điền kho GitHub."""
    time.sleep(8)
    while True:
        with CFG_LOCK:
            on = CFG.get('update_check') and (CFG.get('update_repo') or '').strip()
        if on:
            try:
                update_check_once()
            except Exception:  # noqa
                pass
        time.sleep(UPDATE_EVERY)


def update_brief():
    """Thông tin bản mới gửi cho giao diện (rỗng nếu không có hoặc giáo viên đã bỏ qua đúng bản này)."""
    u = STATE.get('update') or {}
    with CFG_LOCK:
        skip = CFG.get('update_skip', '')
    if not u.get('newer'):
        return None
    return {'latest': u['latest'], 'current': u['current'], 'notes': u.get('notes', ''), 'page': u.get('page', ''),
            'skipped': bool(skip) and skip == u['latest'], 'can_apply': bool(u.get('url'))}
