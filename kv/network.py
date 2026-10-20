# -*- coding: utf-8 -*-
"""Mạng: dò máy học sinh, kiểm tra cổng Veyon, địa chỉ MAC và Wake-on-LAN."""

import hashlib
import os
import re
import socket
import threading
import time

from concurrent.futures import ThreadPoolExecutor

from .config import save_config
from .meta import VEYON_PORT
from .remote import run_args, unc_target
from .runtime import CFG, CFG_LOCK, PAYLOAD_DIR, split_host_port
from .setup import STUDENT_SETUP_BAT


def local_ips():
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:  # noqa
        pass
    try:
        ips.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except Exception:  # noqa
        pass
    return {i for i in ips if i and not i.startswith('127.')}


_TCP_CACHE = {}          # (host, port) -> (thời điểm, kết quả); máy tắt chỉ phải chờ một lần mỗi vài giây
_TCP_CACHE_LOCK = threading.Lock()
TCP_NEG_TTL = 8          # giây nhớ kết quả "không kết nối được"
TCP_POS_TTL = 3          # giây nhớ kết quả "kết nối được"


def _resolve(host, timeout=2.0):
    """Phân giải tên máy có giới hạn thời gian. Trên Windows, tên máy đã tắt có thể làm getaddrinfo chờ nhiều giây
    (DNS rồi LLMNR rồi NetBIOS) và tham số timeout của socket không áp dụng cho bước này."""
    if re.match(r'^\d{1,3}(\.\d{1,3}){3}$', host):
        return host
    box = []

    def run():
        try:
            box.append(socket.getaddrinfo(host, None, socket.AF_INET)[0][4][0])
        except OSError:
            box.append('')
    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout)
    return box[0] if box else ''


def tcp_forget(host, port):
    with _TCP_CACHE_LOCK:
        _TCP_CACHE.pop((host, port), None)


def tcp_open(host, port, timeout=0.5):
    key = (host, port)
    now = time.time()
    with _TCP_CACHE_LOCK:
        hit = _TCP_CACHE.get(key)
    if hit and now - hit[0] < (TCP_POS_TTL if hit[1] else TCP_NEG_TTL):
        return hit[1]
    ok = False
    ip = _resolve(host)
    if ip:
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                ok = True
        except OSError:
            ok = False
    with _TCP_CACHE_LOCK:
        if len(_TCP_CACHE) > 2000:
            _TCP_CACHE.clear()
        _TCP_CACHE[key] = (time.time(), ok)
    return ok


def scan_veyon_hosts(prefix=None, timeout=0.5):
    """Quét dải /24 của mạng hiện tại tìm máy đang mở cổng Veyon (11100). Trả về danh sách tên (hoặc IP)."""
    mine = local_ips()
    if prefix is None:
        if not mine:
            return [], {}, 'Không xác định được địa chỉ mạng của máy này'
        prefix = sorted(mine)[0].rsplit('.', 1)[0]
    found = []

    def probe(i):
        ip = '%s.%d' % (prefix, i)
        return ip if ip not in mine and tcp_open(ip, VEYON_PORT, timeout) else None
    with ThreadPoolExecutor(max_workers=96) as ex:
        for ip in ex.map(probe, range(1, 255)):
            if ip:
                found.append(ip)
    # Trả về IP (kết nối luôn đúng); tên PC dò được trả riêng để hiển thị thay cho IP
    names = {}
    if found:
        with ThreadPoolExecutor(max_workers=32) as ex:
            for ip, n in zip(found, ex.map(lambda i: pc_name_lookup(i, 2.0), found)):
                if n:
                    names[ip] = n
    return found, names, ''


def diagnose_host(cfg, host):
    """Kiểm tra từng điều kiện để KhoaVeyon dùng được với máy này. Trả về danh sách (nhãn, đạt, gợi ý).
    Thứ tự cố định (setup_jobs đọc theo chỉ số): 0 Veyon, 1 chép file, 2 chạy lệnh, 3 đã có script, 4 dịch vụ đúng bản, 5 Agent."""
    from .agent import agent_online
    checks = []
    veyon_ok = tcp_open(host, VEYON_PORT, 2)
    checks.append(('Veyon Service (cổng %d)' % VEYON_PORT, veyon_ok, 'Cài/bật Veyon Service trên máy học sinh, kiểm tra tường lửa'))
    agent_ok = agent_online(host)
    sname = os.path.basename((cfg.get('script_path') or '').replace('\\', '/'))
    spath = (cfg.get('script_path') or '').strip()
    unc = ''
    share_ok = False
    if agent_ok:
        share_ok = True
    else:
        try:
            unc = unc_target(host, cfg['dist_target'])
            share_ok = os.path.isdir(unc) or os.path.isdir(os.path.dirname(unc.rstrip('\\')))
        except Exception:  # noqa
            unc, share_ok = '', False
    checks.append(('Chép file xuống máy (Agent hoặc C$)', share_ok,
                   'Chạy %s trên máy học sinh một lần (quyền quản trị) để cài Agent: sau đó máy giáo viên không cần tài khoản quản trị của máy học sinh' % STUDENT_SETUP_BAT))
    if agent_ok:
        run_ok = True
    else:
        rc, _ = run_args(['schtasks', '/Query', '/S', host, '/FO', 'LIST'], timeout=25)
        run_ok = rc == 0
    checks.append(('Chạy lệnh từ xa (Agent hoặc Task Scheduler)', run_ok, 'Cài Agent bằng %s (khuyên dùng), hoặc bật nhóm tường lửa "Remote Scheduled Tasks Management"' % STUDENT_SETUP_BAT))
    local_script = os.path.join(PAYLOAD_DIR, sname)
    has, same = False, False
    if agent_ok:
        from .remote import rfs_sha
        try:
            rs = rfs_sha(host, spath)
            has = True
            ls = _file_sha(local_script)
            same = ls is not None and rs == ls
        except OSError:
            pass
    else:
        remote_script = os.path.join(unc, sname) if unc else ''
        has = bool(remote_script) and os.path.isfile(remote_script)
        if has and os.path.isfile(local_script):
            rs, ls = _file_sha(remote_script), _file_sha(local_script)
            same = rs is not None and ls is not None and rs == ls
    checks.append(('Đã có %s trên máy' % sname, has, 'Bấm "Kiểm tra và gửi file xuống máy" để chép'))
    if agent_ok:
        svc_ok = has and same   # Agent đang chạy tức là -install đã chạy; chỉ cần đúng bản
    else:
        rc, _ = run_args(['sc', '\\\\' + host, 'query', 'KhoaVeyonService_blockai'], timeout=20)
        # Dịch vụ coi là "đạt" chỉ khi đã cài VÀ bản .bat trên máy giống hệt bản trong payload.
        svc_ok = rc == 0 and has and (same or not os.path.isfile(local_script))
    checks.append(('Đã cài dịch vụ, đúng bản mới nhất', svc_ok,
                   'Sẽ tự chép bản mới và chạy lại -install'))
    checks.append(('Agent đã kết nối về máy giáo viên', agent_ok,
                   'Cài Agent: chạy %s trên máy học sinh (hoặc bấm "Gửi Setup qua Veyon"). Máy giáo viên cần cho phép cổng Agent qua tường lửa' % STUDENT_SETUP_BAT))
    return checks


def _file_sha(path):
    try:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None   # đọc lỗi: ở trên coi là "khác" nên sẽ cài lại cho chắc


# ---------------------------------------------------------------- bật/tắt máy hàng loạt (từ bản 3.4.0)
MAC_BAD = {'000000000000', 'FFFFFFFFFFFF'}


def valid_pcname(n):
    """Tên PC hợp lệ: không rỗng, không phải toàn số (vd. “192” cắt ra từ chuỗi IP) và không phải dạng IP."""
    n = str(n or '').strip()
    return bool(n) and not n.isdigit() and not re.match(r'^\d{1,3}([-.]\d{1,3}){1,3}$', n)


def _nbstat_name(ip, timeout=1.5):
    """Hỏi tên NetBIOS của máy bằng gói UDP 137 (NBSTAT), chạy được trên mọi hệ điều hành, không cần lệnh nbtstat."""
    q = b'\x4b\x42\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00' + b'\x20' + b'CK' + b'AA' * 15 + b'\x00' + b'\x00\x21\x00\x01'
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(timeout)
            s.sendto(q, (ip, 137))
            d, _a = s.recvfrom(1024)
        i = 12 + 34 + 10
        n = d[i]
        i += 1
        first = ''
        for _ in range(n):
            nm, suf, fl = d[i:i + 15], d[i + 15], (d[i + 16] << 8) | d[i + 17]
            i += 18
            if suf == 0 and not fl & 0x8000:   # tên máy (UNIQUE), không phải tên nhóm làm việc
                first = nm.decode('cp1258', 'ignore').strip().upper()
                break
        return first
    except Exception:  # noqa
        return ''


def pc_name_lookup(ip, timeout=2.5):
    """Dò tên PC từ IP: Agent (nếu máy đã kết nối), DNS ngược, NetBIOS (gói NBSTAT rồi nbtstat). Không dò được thì trả ''."""
    try:
        from .agent import agent_info
        i = agent_info(ip)
        if i and valid_pcname(i.get('name')):
            return str(i['name']).upper()
    except Exception:  # noqa
        pass
    box = []

    def dns():
        try:
            full = socket.gethostbyaddr(ip)[0].strip()
            n = '' if re.match(r'^\d{1,3}(\.\d{1,3}){3}$', full) else full.split('.')[0]   # DNS trả về chính IP thì coi như không có tên
            box.append(n.upper() if valid_pcname(n) else '')
        except Exception:  # noqa
            box.append('')
    t = threading.Thread(target=dns, daemon=True)
    t.start()
    t.join(timeout)
    if box and box[0]:
        return box[0]
    n = _nbstat_name(ip)
    if valid_pcname(n):
        return n
    if os.name == 'nt':
        rc, out = run_args(['nbtstat', '-A', ip], timeout=6)
        for line in (out or '').splitlines():
            m = re.match(r'^\s*(\S+)\s+<00>\s+UNIQUE', line)
            if m and valid_pcname(m.group(1)):
                return m.group(1).upper()
    return ''


def mac_norm(v):
    """Địa chỉ MAC bất kỳ dạng -> 'AA:BB:CC:DD:EE:FF'; không hợp lệ thì trả về ''."""
    h = re.sub(r'[^0-9A-Fa-f]', '', str(v or '')).upper()
    if len(h) != 12 or h in MAC_BAD:
        return ''
    return ':'.join(h[i:i + 2] for i in range(0, 12, 2))


def tcp_probe(host, port, timeout=0.8):
    """Thử kết nối thật, không dùng bộ nhớ đệm (bảng trạng thái cần số liệu mới)."""
    ip = _resolve(host)
    if not ip:
        return False
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def arp_mac(host):
    """MAC của máy cùng mạng LAN, đọc từ bảng ARP (máy phải vừa được kết nối để có trong bảng)."""
    ip = _resolve(host)
    if not ip:
        return ''
    rc, out = run_args(['arp', '-a', ip] if os.name == 'nt' else ['arp', '-n', ip], timeout=8)
    for line in out.splitlines():
        t = line.split()
        if t and t[0] == ip:
            m = re.search(r'(?:[0-9A-Fa-f]{2}[-:]){5}[0-9A-Fa-f]{2}', line)
            if m:
                return mac_norm(m.group(0))
    return ''


def mac_known(host):
    hh, _ = split_host_port(host)
    with CFG_LOCK:
        macs = CFG.get('macs') or {}
        return mac_norm(macs.get(host) or macs.get(hh))


def mac_store(host, mac):
    hh, _ = split_host_port(host)
    mac = mac_norm(mac)
    if not mac:
        return False
    with CFG_LOCK:
        macs = CFG.setdefault('macs', {})
        if macs.get(hh) == mac:
            return False
        macs[hh] = mac
        try:
            save_config(CFG)
        except OSError:
            pass
    return True


def mac_learn(host):
    """Máy đang bật thì đọc MAC và nhớ lại để lần sau đánh thức được."""
    hh, _ = split_host_port(host)
    mac = arp_mac(hh)
    if mac:
        mac_store(host, mac)
    return mac


def wol_targets(host):
    t = {'255.255.255.255'}
    ips = set(local_ips())
    ip = _resolve(host) if host else ''
    if ip:
        ips.add(ip)
    for i in ips:
        p = i.split('.')
        if len(p) == 4:
            t.add('%s.%s.%s.255' % (p[0], p[1], p[2]))
    return sorted(t)


def wol_send(mac, host=''):
    mac = mac_norm(mac)
    if not mac:
        raise ValueError('MAC không hợp lệ')
    raw = bytes.fromhex(mac.replace(':', ''))
    pkt = b'\xff' * 6 + raw * 16
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for t in wol_targets(host):
            for port in (9, 7):
                try:
                    s.sendto(pkt, (t, port))
                except OSError:
                    pass
    finally:
        s.close()
