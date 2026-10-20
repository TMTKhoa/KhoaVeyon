# -*- coding: utf-8 -*-
"""Chạy lệnh qua Veyon, chép file sang máy học sinh qua \\\\máy\\C$ và chạy lệnh từ xa bằng schtasks."""

import os
import re
import shutil
import subprocess
import time

import base64
import hashlib
import ntpath

from .agent import agent_call, agent_info, agent_online, AgentError, MAX_FILE
from .excel_lists import LISTS
from .paths import abs_path, CREATE_NO_WINDOW, find_veyon_cli
from .runtime import CFG, CFG_LOCK, split_host_port


def client_command(cfg, switch):
    """Lệnh để dán vào Veyon (Run program)."""
    return 'cmd.exe /c %s %s' % (cfg['script_path'], switch)


def veyon_command(cfg, host, feature, template_key='run_template'):
    if template_key == 'run_template' and feature:
        try:
            from .featres import resolve
            feature = resolve(cfg, feature)   # gọi bằng UID thật của mục nếu tra được (tránh lỗi “Invalid feature name”)
        except Exception:  # noqa
            pass
    return cfg[template_key].format(cli=find_veyon_cli(cfg['veyon_cli']), host=host, feature=feature)


def run_shell(cmdline, timeout=60):
    try:
        p = subprocess.run(cmdline, shell=True, capture_output=True, text=True, errors='replace',
                           timeout=timeout, creationflags=CREATE_NO_WINDOW)
        out = ((p.stdout or '') + (p.stderr or '')).strip()
        return p.returncode, out
    except subprocess.TimeoutExpired:
        return -1, 'Quá thời gian chờ'
    except Exception as e:  # noqa
        return -1, str(e)


def run_args(args, timeout=60):
    """Chạy lệnh dạng danh sách tham số, không cho đọc bàn phím (tránh treo khi lệnh hỏi mật khẩu)."""
    try:
        p = subprocess.run(args, capture_output=True, text=True, errors='replace', timeout=timeout,
                           stdin=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
        return p.returncode, ((p.stdout or '') + (p.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return -1, 'Quá thời gian chờ'
    except Exception as e:  # noqa
        return -1, str(e)


def unc_target(host, target_dir):
    """C:\\cmd trên máy học sinh -> \\\\HOST\\C$\\cmd (chia sẻ quản trị)."""
    m = re.match(r'^([A-Za-z]):[\\/]*(.*)$', (target_dir or '').strip())
    if not m:
        raise ValueError('Thư mục đích phải bắt đầu bằng ổ đĩa, ví dụ C:\\cmd')
    return '\\\\%s\\%s$\\%s' % (host, m.group(1).upper(), m.group(2).replace('/', '\\'))


def transport_mode():
    """auto = dùng Agent khi máy học sinh đã kết nối, không thì dùng C$ như cũ; agent = chỉ Agent; smb = chỉ C$."""
    with CFG_LOCK:
        m = str(CFG.get('transport') or 'auto')
    return m if m in ('auto', 'agent', 'smb') else 'auto'


def use_agent(host):
    hh = split_host_port(host)[0]
    m = transport_mode()
    if m == 'smb':
        return False
    if m == 'agent':
        return True
    return agent_online(hh)


def rfs_reachable(host, tcp_open_fn=None):
    """Máy có đường để chép/đọc file không: Agent đã kết nối hoặc cổng 445 mở."""
    hh = split_host_port(host)[0]
    if agent_online(hh):
        return True
    if transport_mode() == 'agent':
        return False
    if tcp_open_fn is None:
        from .network import tcp_open as tcp_open_fn
    return bool(tcp_open_fn(hh, 445, 1.5))


def _wjoin(a, b):
    return ntpath.join(a, b)


def _agent_ok(res, what):
    if not res.get('ok'):
        raise AgentError('%s: %s' % (what, (res.get('out') or 'lỗi không rõ')[:300]))
    return res


def _agent_put_file(host, dst, data):
    if len(data) > MAX_FILE:
        raise AgentError('File quá lớn để gửi qua Agent (%d MB, tối đa %d MB): %s' % (len(data) >> 20, MAX_FILE >> 20, dst))
    _agent_ok(agent_call(host, {'op': 'put', 'path': dst, 'b64': base64.b64encode(data).decode('ascii'),
                                'sha': hashlib.sha256(data).hexdigest()}, timeout=120), 'không ghi được ' + dst)


def rfs_scan(host, winpath):
    """Liệt kê thư mục trên máy học sinh: [{'name','size','mtime','dir'}]. Thư mục không có thì ném FileNotFoundError."""
    if use_agent(host):
        res = agent_call(host, {'op': 'ls', 'path': winpath}, timeout=60)
        if res.get('exists') is False:
            raise FileNotFoundError(winpath)
        _agent_ok(res, 'không liệt kê được ' + winpath)
        return [{'name': e['n'], 'size': e.get('s', 0), 'mtime': e.get('m', 0), 'dir': bool(e.get('d'))} for e in res.get('entries') or []]
    d = unc_target(split_host_port(host)[0], winpath)
    out = []
    for n in os.listdir(d):
        try:
            st = os.stat(os.path.join(d, n))
            out.append({'name': n, 'size': st.st_size, 'mtime': st.st_mtime, 'dir': os.path.isdir(os.path.join(d, n))})
        except OSError:
            continue
    return out


def rfs_read(host, winpath):
    """Đọc nguyên file từ máy học sinh. Không có file thì FileNotFoundError."""
    if use_agent(host):
        res = agent_call(host, {'op': 'get', 'path': winpath}, timeout=120)
        if res.get('exists') is False:
            raise FileNotFoundError(winpath)
        _agent_ok(res, 'không đọc được ' + winpath)
        data = base64.b64decode(res.get('b64') or '')
        if res.get('sha') and hashlib.sha256(data).hexdigest() != res['sha']:
            raise AgentError('File nhận về bị lỗi (sai mã băm): ' + winpath)
        return data
    with open(unc_target(split_host_port(host)[0], winpath), 'rb') as f:
        return f.read()


def rfs_write(host, winpath, data):
    if use_agent(host):
        _agent_put_file(host, winpath, data)
        return
    p = unc_target(split_host_port(host)[0], winpath)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'wb') as f:
        f.write(data)


def rfs_remove(host, winpath):
    """Xóa file (hoặc thư mục). Không có thì FileNotFoundError."""
    if use_agent(host):
        res = agent_call(host, {'op': 'rm', 'path': winpath}, timeout=60)
        if res.get('exists') is False:
            raise FileNotFoundError(winpath)
        _agent_ok(res, 'không xóa được ' + winpath)
        return
    p = unc_target(split_host_port(host)[0], winpath)
    if os.path.isdir(p):
        shutil.rmtree(p)
    else:
        os.remove(p)


def rfs_exists(host, winpath):
    if use_agent(host):
        res = agent_call(host, {'op': 'stat', 'path': winpath}, timeout=45)
        _agent_ok(res, 'không kiểm tra được ' + winpath)
        return bool(res.get('exists'))
    return os.path.exists(unc_target(split_host_port(host)[0], winpath))


def rfs_sha(host, winpath):
    """SHA-256 của file trên máy học sinh (agent tự tính nên không phải tải cả file về). Không có file thì FileNotFoundError."""
    if use_agent(host):
        res = agent_call(host, {'op': 'stat', 'path': winpath, 'sha': True}, timeout=45)
        _agent_ok(res, 'không kiểm tra được ' + winpath)
        if not res.get('exists'):
            raise FileNotFoundError(winpath)
        return str(res.get('sha') or '')
    h = hashlib.sha256()
    with open(unc_target(split_host_port(host)[0], winpath), 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def rfs_mtime(host, winpath):
    """Thời điểm sửa file (epoch) hoặc FileNotFoundError."""
    if use_agent(host):
        res = agent_call(host, {'op': 'stat', 'path': winpath}, timeout=45)
        _agent_ok(res, 'không kiểm tra được ' + winpath)
        if not res.get('exists'):
            raise FileNotFoundError(winpath)
        return float(res.get('mtime') or 0)
    return os.path.getmtime(unc_target(split_host_port(host)[0], winpath))


def explain_share_error(host, e):
    """Đổi lỗi chép qua \\\\máy\\C$ thành câu tiếng Việt có hướng xử lý."""
    code = getattr(e, 'winerror', None)
    if isinstance(e, AgentError):
        return str(e)
    if code == 5 or isinstance(e, PermissionError):
        return ('Bị từ chối quyền (Access denied) khi vào \\\\%s\\C$. Máy giáo viên không phải quản trị viên của máy HS này. '
                'Cách dễ nhất: cài Agent (Setup-MayHocSinh.bat một lần trên máy HS) rồi dùng kênh Agent, không cần tài khoản trùng.' % host)
    if code in (53, 67, 1203) or isinstance(e, FileNotFoundError):
        return 'Không thấy chia sẻ \\\\%s\\C$ (máy tắt, chưa bật chia sẻ file hoặc tường lửa chặn cổng 445). Cài Agent để khỏi cần chia sẻ này: %s' % (host, e)
    if code == 1326:
        return 'Sai tên/mật khẩu khi vào \\\\%s\\C$ (WinError 1326). Cài Agent để khỏi cần tài khoản.' % host
    return str(e)


def distribute_to_host(host, files, target_dir):
    """Chép file/thư mục sang máy học sinh (qua Agent nếu có, không thì qua C$). Trả về số mục đã chép."""
    hh = split_host_port(host)[0]
    n = 0
    if use_agent(host):
        if not re.match(r'^[A-Za-z]:[\\/]*', (target_dir or '').strip()):
            raise ValueError('Thư mục đích phải bắt đầu bằng ổ đĩa, ví dụ C:\\cmd')
        tgt = (target_dir or '').strip().replace('/', '\\').rstrip('\\')
        for f in files:
            src = abs_path(f)
            if os.path.isdir(src):
                base = os.path.basename(src.rstrip('\\/'))
                for dp, _d, fns in os.walk(src):
                    for fn in fns:
                        sp = os.path.join(dp, fn)
                        rel = os.path.relpath(sp, src).replace('/', '\\')
                        with open(sp, 'rb') as fh:
                            _agent_put_file(hh, _wjoin(_wjoin(tgt, base), rel), fh.read())
            else:
                with open(src, 'rb') as fh:
                    _agent_put_file(hh, _wjoin(tgt, os.path.basename(src)), fh.read())
            n += 1
        return n
    dst = unc_target(hh, target_dir)
    try:
        os.makedirs(dst, exist_ok=True)
        for f in files:
            src = abs_path(f)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(dst, os.path.basename(src.rstrip('\\/'))), dirs_exist_ok=True)
            else:
                shutil.copy2(src, os.path.join(dst, os.path.basename(src)))
            n += 1
    except OSError as e:
        raise OSError(explain_share_error(hh, e)) from e
    return n


def logged_on_user(host):
    info = agent_info(split_host_port(host)[0]) if use_agent(host) else None
    if info is not None:
        return info.get('user') or ''
    rc, out = run_args(['query', 'user', '/server:' + host], timeout=20)
    if rc != 0:
        return ''
    for line in out.splitlines()[1:]:
        t = line.replace('>', ' ').split()
        if t:
            return t[0]
    return ''


def remote_run(host, cmdline, interactive=False, name='KhoaVeyonRun'):
    """Chạy 1 lệnh trên máy học sinh bằng Task Scheduler (schtasks) rồi kích hoạt ngay.
    Mặc định chạy bằng SYSTEM (nền, học sinh không thấy cửa sổ). interactive=True: chạy bằng người đang đăng nhập."""
    if use_agent(host):
        try:
            res = agent_call(split_host_port(host)[0], {'op': 'exec', 'cmd': cmdline, 'session': 'user' if interactive else 'system', 'wait': False}, timeout=45)
        except AgentError as e:
            return -1, str(e)
        return (0, 'ok') if res.get('ok') else (1, (res.get('out') or 'lỗi')[:300])
    ru = 'SYSTEM'
    if interactive:
        ru = logged_on_user(host)
        if not ru:
            return -1, 'Không tìm thấy người đang đăng nhập trên máy này'
    create = ['schtasks', '/Create', '/S', host, '/TN', name, '/TR', cmdline, '/SC', 'ONCE', '/ST', '00:00',
              '/RU', ru, '/F']
    create += ['/IT'] if interactive else ['/RL', 'HIGHEST']
    rc, out = run_args(create)
    if rc != 0:
        return rc, out
    rc2, out2 = run_args(['schtasks', '/Run', '/S', host, '/TN', name])
    return rc2, (out + '\n' + out2).strip()


def remote_install(host, script_path, timeout=120):
    """Chạy `<script> -install` trên máy học sinh. Qua Agent: -install dừng rồi khởi động lại chính dịch vụ Agent nên
    không chờ kết quả được; thay vào đó chờ dịch vụ khởi động lại (mốc 'boot' đổi) rồi báo xong. Trả về (ok, mô tả)."""
    cmd = 'cmd.exe /c %s -install <nul' % script_path
    hh = split_host_port(host)[0]
    if not use_agent(host):
        return remote_run_wait(host, cmd)
    boot0 = (agent_info(hh) or {}).get('boot')
    try:
        res = agent_call(hh, {'op': 'exec', 'cmd': cmd, 'session': 'system', 'wait': False}, timeout=45)
    except AgentError as e:
        return False, str(e)
    if not res.get('ok'):
        return False, (res.get('out') or 'lỗi')[:300]
    end = time.time() + timeout
    while time.time() < end:
        time.sleep(2)
        i = agent_info(hh)
        if i and i.get('boot') and i.get('boot') != boot0 and agent_online(hh):
            return True, 'xong'
    return False, 'đã gửi -install nhưng chưa thấy dịch vụ khởi động lại sau %d giây (xem C:\\cmd\\KhoaVeyonService.log trên máy học sinh)' % timeout


def remote_task_delete(host, name):
    """Xóa tác vụ Task Scheduler cũ trên máy học sinh (dọn bản cài cũ). Bỏ qua lỗi; trả về True nếu lệnh chạy được."""
    if use_agent(host):
        ok, _msg = remote_run_wait(host, 'schtasks.exe /Delete /TN %s /F' % name, 30)
        return ok
    rc, _ = run_args(['schtasks', '/Delete', '/S', split_host_port(host)[0], '/TN', name, '/F'])
    return rc == 0


def sync_lists(cfg):
    """Chép 3 file Excel từ thư mục danh sách sang thư mục đồng bộ. Trả về (số file đã chép, lỗi)."""
    dst = (cfg.get('sync_dir') or '').strip()
    if not dst:
        return 0, 'Chưa đặt thư mục đồng bộ'
    dst = abs_path(dst)
    os.makedirs(dst, exist_ok=True)
    n = 0
    for meta in LISTS.values():
        src = os.path.join(abs_path(cfg['list_dir']), meta['file'])
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dst, meta['file']))
            n += 1
    return n, ''


def parse_task_result(csv_text):
    """Lấy mã 'Last Result' (cột 7) từ kết quả schtasks /Query /FO CSV /V. Trả về số nguyên hoặc None."""
    import csv
    import io
    rows = list(csv.reader(io.StringIO(csv_text)))
    for r in rows[1:] if len(rows) > 1 else []:
        if len(r) > 6:
            try:
                return int(r[6])
            except ValueError:
                return None
    return None


def remote_run_wait(host, cmdline, timeout=60, interactive=False):
    """Như remote_run (mặc định SYSTEM) nhưng đợi lệnh chạy xong và trả về (ok, mô tả)."""
    if use_agent(host):
        try:
            res = agent_call(split_host_port(host)[0], {'op': 'exec', 'cmd': cmdline, 'session': 'user' if interactive else 'system',
                                                      'wait': True, 'timeout': int(timeout)}, timeout=int(timeout) + 30)
        except AgentError as e:
            return False, str(e)
        if not res.get('ok'):
            return False, (res.get('out') or 'lỗi')[:300]
        rc = res.get('rc', 0)
        return rc == 0, 'xong' if rc == 0 else 'mã lỗi %s %s' % (rc, (res.get('out') or '')[-200:].strip())
    rc, out = remote_run(host, cmdline, interactive)
    if rc != 0:
        return False, '(%s) %s' % (rc, out)
    end = time.time() + timeout
    while time.time() < end:
        time.sleep(2)
        rc, out = run_args(['schtasks', '/Query', '/S', host, '/TN', 'KhoaVeyonRun', '/FO', 'CSV', '/V'], timeout=25)
        code = parse_task_result(out) if rc == 0 else None
        if code is not None and code not in (267009, 267011, 267014):  # đang chạy / chưa chạy / bị dừng
            return code == 0, 'xong' if code == 0 else 'mã lỗi %s' % code
    return False, 'quá thời gian chờ'
