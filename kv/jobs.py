# -*- coding: utf-8 -*-
"""Công việc nền cơ bản: chạy một lệnh trên nhiều máy, phân phối file, đồng bộ sau khi lưu danh sách."""

import os

from .actions import ACTION_BY_KEY
from .applied import applied_record
from .network import tcp_open
from .remote import distribute_to_host, remote_run, run_shell, veyon_command
from .runtime import CFG, CFG_LOCK, log, pool_run, split_host_port


# ---------------------------------------------------------------- các công việc chạy nền
def veyon_feature(key):
    with CFG_LOCK:
        return CFG['features'].get(key) or ACTION_BY_KEY[key][3]


def job_action(key, hosts):
    label = ACTION_BY_KEY[key][1]
    feature = veyon_feature(key)
    log('>>> %s  (mục Veyon: "%s", %d máy)' % (label, feature, len(hosts)), 'head')

    def one(h):
        try:
            with CFG_LOCK:
                cmd = veyon_command(CFG, h, feature)
        except Exception as e:  # noqa
            return False, 'Lỗi mẫu lệnh: %s' % e
        hh, pp = split_host_port(h)
        if not tcp_open(hh, pp, 1.5):  # máy tắt: báo lỗi sau vài giây thay vì chờ veyon-cli hết 60 giây
            return False, 'máy không trả lời (đang tắt, sai tên máy hoặc Veyon Service chưa chạy)'
        rc, out = run_shell(cmd, timeout=30)
        if rc == 0:
            applied_record(h, key)
        if rc == 0:
            return True, out
        if 'invalid feature' in (out or '').lower():
            out += ('\n   → Veyon trên máy giáo viên chưa có mục "%s". Vào Thiết lập → “Mục điều khiển trong Veyon” để tạo lại, '
                    'hoặc kiểm tra tên mục ở Cài đặt (phải trùng tên trong Veyon Master → Programs & websites).' % feature)
        return False, '(%s) %s' % (rc, out)
    pool_run(one, hosts, label)


def job_dist(hosts, files, mode, cmd, feature, interactive, target, title):
    log('>>> %s  (%d máy)' % (title, len(hosts)), 'head')

    def one(h):
        msgs = []
        if files:
            try:
                n = distribute_to_host(h, files, target)
                msgs.append('đã chép %d mục' % n)
            except Exception as e:  # noqa
                hint = ''
                es = str(e)
                if 'WinError 53' in es or 'WinError 67' in es:
                    hint = ' -> máy học sinh chưa mở chia sẻ C$ (cổng 445): bật File and Printer Sharing / tường lửa, hoặc dùng Setup-MayHocSinh.bat'
                elif 'WinError 5]' in es or 'WinError 1326' in es:
                    hint = ' -> bị từ chối quyền: chạy chương trình bằng tài khoản quản trị của máy học sinh, hoặc dùng Setup-MayHocSinh.bat'
                return False, 'lỗi chép file: %s%s%s' % (e, hint, ' (bỏ qua bước chạy)' if mode != 'none' else '')
        if mode == 'schtasks':
            rc, out = remote_run(h, cmd, interactive)
            if rc != 0:
                return False, '%schạy lệnh lỗi (%s) %s' % (', '.join(msgs) + ', ' if msgs else '', rc, out)
            msgs.append('đã chạy lệnh')
        elif mode == 'veyon':
            try:
                with CFG_LOCK:
                    c = veyon_command(CFG, h, feature)
            except Exception as e:  # noqa
                return False, 'Lỗi mẫu lệnh: %s' % e
            rc, out = run_shell(c)
            if rc != 0:
                return False, '%schạy mục Veyon lỗi (%s) %s' % (', '.join(msgs) + ', ' if msgs else '', rc, out)
            msgs.append('đã kích hoạt mục Veyon')
        return True, ', '.join(msgs)
    pool_run(one, hosts, title)


def job_after_save(hosts, path, push, apply_key, target):
    """Sau khi lưu danh sách: gửi file xuống máy học sinh (nếu bật), xong mới áp dụng lệnh để máy đọc đúng bản mới."""
    if push:
        job_dist(hosts, [path], 'none', '', '', False, target, 'Gửi %s xuống máy học sinh' % os.path.basename(path))
    if apply_key:
        job_action(apply_key, hosts)
