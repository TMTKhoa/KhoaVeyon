# -*- coding: utf-8 -*-
"""Máy học sinh tự áp hạn chế mỗi khi có người đăng nhập, không cần KhoaVeyon đang mở (từ bản 3.9.0).

Tạo KhoaVeyonLogon.bat trong <đích>\\vcfg trên máy học sinh và một tác vụ KhoaVeyonLogon (LogonTrigger, nhóm Users,
chạy trong phiên của chính học sinh, ẩn). Chỉ cho chọn các lệnh chạy được trong phiên người dùng và không cần quyền
quản trị: khóa Task Manager, chặn mở app ngoài danh sách, tắt tiếng.

Lưu ý: nút Mở khóa giữa buổi chỉ có tác dụng đến lần đăng nhập tiếp theo, vì lúc đó chính sách này áp lại. Muốn bỏ hẳn
thì gỡ chính sách (nút Gỡ)."""

import ntpath
import os
import shutil
import tempfile

from .remote import distribute_to_host, remote_task_delete, rfs_exists, rfs_remove, rfs_write, run_args, use_agent
from .runtime import ApiError, CFG, clean_hosts, log, pool_run, start_job
from .vcfg import vcfg_remote_dir


LOGON_TASK = 'KhoaVeyonLogon'
LOGON_BAT = 'KhoaVeyonLogon.bat'
LOGON_LIST = 'kvlogon.txt'   # vcfg\kvlogon.txt: dịch vụ KhoaVeyonAutoLog chạy mỗi dòng trong phiên học sinh khi đăng nhập (thay Task Scheduler)
LOGON_MODES = {   # tham số của KhoaVeyonServices.bat -> nhãn trên giao diện
    'lockdown': 'Khóa Task Manager, Control Panel, Registry',
    'lockrun-start': 'Chặn mở app ngoài danh sách',
    'mute': 'Tắt tiếng',
}


def logon_modes_clean(modes):
    return [m for m in LOGON_MODES if m in (modes or [])]   # giữ thứ tự cố định, bỏ giá trị lạ


def logon_bat_text(script_path, modes):
    lines = ['@echo off', 'REM KhoaVeyon: tu ap han che khi hoc sinh dang nhap (tao boi KhoaVeyon, dung sua tay)']
    for m in logon_modes_clean(modes):
        lines.append('call "%s" -%s' % (script_path, m))
    lines.append('exit /b 0')
    return '\r\n'.join(lines) + '\r\n'


def logon_task_xml(bat_path):
    from xml.sax.saxutils import escape
    return (
        '<?xml version="1.0" encoding="UTF-16"?>\r\n'
        '<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\r\n'
        '  <RegistrationInfo><Description>KhoaVeyon: ap han che khi hoc sinh dang nhap</Description></RegistrationInfo>\r\n'
        '  <Triggers><LogonTrigger><Enabled>true</Enabled><Delay>PT10S</Delay></LogonTrigger></Triggers>\r\n'
        '  <Principals><Principal id="Author"><GroupId>S-1-5-32-545</GroupId><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>\r\n'
        '  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>'
        '<StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><AllowStartOnDemand>true</AllowStartOnDemand><Enabled>true</Enabled>'
        '<Hidden>true</Hidden><ExecutionTimeLimit>PT10M</ExecutionTimeLimit></Settings>\r\n'
        '  <Actions Context="Author"><Exec><Command>cmd.exe</Command><Arguments>%s</Arguments></Exec></Actions>\r\n'
        '</Task>\r\n' % escape('/c "%s"' % bat_path))


def logon_install(host, cfg, modes):
    modes = logon_modes_clean(modes)
    if not modes:
        return False, 'chưa chọn lệnh nào'
    rdir = vcfg_remote_dir(cfg)
    bat_remote = rdir + '\\' + LOGON_BAT
    script = (cfg.get('script_path') or r'C:\cmd\KhoaVeyonServices.bat').strip()
    tmp = tempfile.mkdtemp(prefix='kvlogon')
    try:
        bp = os.path.join(tmp, LOGON_BAT)
        with open(bp, 'w', encoding='utf-8', newline='') as f:
            f.write(logon_bat_text(script, modes))
        distribute_to_host(host, [bp], rdir)
        if use_agent(host):   # dịch vụ KhoaVeyonAutoLog chạy file này mỗi lần học sinh đăng nhập, không cần Task Scheduler
            rfs_write(host, ntpath.join(rdir, LOGON_LIST), ('cmd.exe /c "%s"\r\n' % bat_remote).encode('utf-8'))
            remote_task_delete(host, LOGON_TASK)   # gỡ tác vụ cũ của bản trước nếu còn
            return True, 'đã cài, áp %d lệnh mỗi lần học sinh đăng nhập (qua dịch vụ KhoaVeyon)' % len(modes)
        xp = os.path.join(tmp, 'task.xml')
        with open(xp, 'w', encoding='utf-16', newline='') as f:   # schtasks cần UTF-16
            f.write(logon_task_xml(bat_remote))
        rc, out = run_args(['schtasks', '/Create', '/S', host, '/TN', LOGON_TASK, '/XML', xp, '/F'])
        if rc != 0:
            return False, out[:200]
        return True, 'đã cài, áp %d lệnh mỗi lần học sinh đăng nhập' % len(modes)
    except Exception as e:  # noqa
        return False, str(e)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def logon_remove(host, cfg):
    if use_agent(host):
        try:
            rfs_remove(host, ntpath.join(vcfg_remote_dir(cfg), LOGON_LIST))
        except FileNotFoundError:
            pass
        except OSError as e:
            return False, str(e)[:200]
        remote_task_delete(host, LOGON_TASK)
        return True, 'đã gỡ'
    rc, out = run_args(['schtasks', '/Delete', '/S', host, '/TN', LOGON_TASK, '/F'])
    if rc == 0:
        return True, 'đã gỡ'
    rc2, _ = run_args(['schtasks', '/Query', '/S', host, '/TN', LOGON_TASK])
    if rc2 != 0:
        return True, 'không có chính sách để gỡ'
    return False, out[:200]


def logon_check(host, cfg):
    if use_agent(host):
        try:
            return True, 'đang cài' if rfs_exists(host, ntpath.join(vcfg_remote_dir(cfg), LOGON_LIST)) else 'chưa cài'
        except OSError as e:
            return False, str(e)[:200]
    rc, _ = run_args(['schtasks', '/Query', '/S', host, '/TN', LOGON_TASK])
    return True, 'đang cài' if rc == 0 else 'chưa cài'


def job_logon(step, hosts, modes):
    with_cfg = dict(CFG)
    fn = {'install': lambda h: logon_install(h, with_cfg, modes),
          'remove': lambda h: logon_remove(h, with_cfg),
          'check': lambda h: logon_check(h, with_cfg)}[step]
    title = {'install': 'Cài chính sách khi đăng nhập', 'remove': 'Gỡ chính sách khi đăng nhập', 'check': 'Kiểm tra chính sách khi đăng nhập'}[step]
    log('=== %s (%d máy) ===' % (title, len(hosts)), 'head')
    pool_run(fn, hosts, title)


def api_logon_policy(b):
    step = b.get('step')
    if step == 'modes':
        return {'modes': [{'id': k, 'label': v} for k, v in LOGON_MODES.items()]}
    if step not in ('install', 'remove', 'check'):
        raise ApiError('Bước không hợp lệ')
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào')
    modes = logon_modes_clean(b.get('modes'))
    if step == 'install' and not modes:
        raise ApiError('Chọn ít nhất một lệnh')
    start_job(job_logon, step, hosts, modes)
    return {'ok': True}
