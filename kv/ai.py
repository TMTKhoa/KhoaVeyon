# -*- coding: utf-8 -*-
"""Khóa công cụ AI trên máy học sinh: lệnh khóa kèm chụp ảnh và đọc trạng thái."""

import os

from .jobs import job_action
from .network import tcp_open
from .remote import unc_target
from .runtime import ApiError, clean_hosts, log, pool_run, split_host_port, start_job
from .screenshot import job_shot_then_action


def job_lock_with_ai(key, hosts, shot):
    """Khóa/mở toàn bộ kèm khóa/mở AI. Khi khóa: chụp màn hình (nếu bật) rồi khóa AI trước, sau đó khóa máy,
    để ảnh chụp còn thấy trang AI đang mở. Khi mở: mở máy rồi mở AI."""
    if key == 'lockall-start':
        (job_shot_then_action if shot else job_action)('blockai', hosts)
        job_action('lockall-start', hosts)
    else:
        job_action(key, hosts)
        job_action('allowai', hosts)


AI_STATE_DIR = r'C:\ProgramData\KhoaVeyon'
AI_HOSTS_DIR = r'C:\Windows\System32\drivers\etc'


def ai_hosts_count(text):
    """Số tên miền KhoaVeyon đã chặn trong file hosts (các dòng '0.0.0.0 ten' nằm giữa hai dấu BEGIN/END)."""
    n, inside = 0, False
    for line in (text or '').splitlines():
        t = line.strip()
        if t == '# KhoaVeyon-AI-BEGIN':
            inside = True
        elif t == '# KhoaVeyon-AI-END':
            inside = False
        elif inside and t.startswith('0.0.0.0 '):
            n += 1
    return n


def ai_classify(has_backup, hosts_n):
    """Trả về (đã khóa đủ?, nội dung báo cáo)."""
    if has_backup and hosts_n > 0:
        return True, 'ĐÃ KHÓA AI (chính sách trình duyệt và hosts, %d tên miền)' % hosts_n
    if has_backup:
        return True, 'ĐÃ KHÓA AI bằng chính sách trình duyệt (hosts không dùng hoặc không ghi được)'
    if hosts_n > 0:
        return False, 'KHÓA DỞ: có hosts (%d tên miền) nhưng chưa có chính sách trình duyệt. Bấm Khóa lại' % hosts_n
    return False, 'CHƯA KHÓA AI'


def ai_state_one(host):
    hh, _ = split_host_port(host)
    if not tcp_open(hh, 445, 1.5):
        return False, 'không kết nối được chia sẻ C$ (máy tắt hoặc chưa mở chia sẻ file)'
    try:
        backup = os.path.join(unc_target(hh, AI_STATE_DIR), 'ai_backup.json')
        hosts_path = os.path.join(unc_target(hh, AI_HOSTS_DIR), 'hosts')
        try:
            os.stat(backup)
            has_backup = True
        except FileNotFoundError:
            has_backup = False
        with open(hosts_path, 'r', encoding='utf-8', errors='replace') as f:
            n = ai_hosts_count(f.read())
    except PermissionError:
        return False, 'không đủ quyền đọc, hãy đăng nhập máy này bằng tài khoản quản trị của máy học sinh'
    except OSError as e:
        return False, 'không đọc được trạng thái: %s' % e
    return ai_classify(has_backup, n)


def job_ai_status(hosts):
    log('>>> Kiểm tra trạng thái khóa AI (%d máy)' % len(hosts), 'head')
    pool_run(ai_state_one, hosts, 'Kiểm tra trạng thái khóa AI')


def api_ai_status(b):
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào để kiểm tra')
    start_job(job_ai_status, hosts)
    return {'ok': True}


# ---------------------------------------------------------------- tùy chọn khóa AI (ai_opts.txt)
AI_OPTS_NAME = 'ai_opts.txt'


def ai_opts_path():
    from .runtime import abs_path, CFG as _CFG, CFG_LOCK as _LK
    with _LK:
        return os.path.join(abs_path(_CFG['list_dir']), AI_OPTS_NAME)


def ai_opts_write(cfg):
    """Ghi ai_opts.txt (cùng thư mục các file Excel) để lệnh -blockai đọc: chặn AI Overviews, tắt DNS-over-HTTPS,
    chặn mọi extension. Thiếu file thì -blockai dùng mặc định (Overview + DoH bật, Extension tắt)."""
    lines = [
        'OVERVIEW=%d' % (0 if cfg.get('ai_block_overviews', True) is False else 1),
        'DOH=%d' % (0 if cfg.get('ai_disable_doh', True) is False else 1),
        'EXT=%d' % (1 if cfg.get('ai_block_ext') else 0),
    ]
    p = ai_opts_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='ascii', newline='') as f:
        f.write('\r\n'.join(lines) + '\r\n')
    return p


def api_ai_opts(b):
    """Lưu 3 tùy chọn khóa AI, ghi ai_opts.txt rồi gửi xuống các máy đang có."""
    from .runtime import CFG, CFG_LOCK
    from .config import save_config
    with CFG_LOCK:
        for k in ('ai_block_overviews', 'ai_disable_doh', 'ai_block_ext'):
            if k in b:
                CFG[k] = bool(b[k])
        save_config(CFG)
        cfg = {k: CFG.get(k) for k in ('ai_block_overviews', 'ai_disable_doh', 'ai_block_ext')}
        cfg['dist_target'] = CFG['dist_target']
        hosts = list(CFG.get('hosts') or [])
    try:
        p = ai_opts_write(cfg)
    except OSError as e:
        raise ApiError('Không ghi được ai_opts.txt: %s' % e)
    if hosts:
        from .jobs import job_dist
        start_job(job_dist, hosts, [p], 'none', '', '', False, cfg['dist_target'], 'Gửi tùy chọn khóa AI xuống %d máy' % len(hosts))
    log('Đã lưu tùy chọn khóa AI (AI Overviews, DNS-over-HTTPS, extension)' + ('' if hosts else ' — chưa có máy để gửi'), 'ok')
    return dict(cfg, pushed=bool(hosts))
