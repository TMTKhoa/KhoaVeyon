# -*- coding: utf-8 -*-
"""Trang Chẩn đoán: bảng xanh/đỏ cho từng máy học sinh (Veyon, Agent, giờ máy, dịch vụ) kèm nút sửa; tường lửa kiểm ở máy giáo viên."""

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

from .agent import agent_firewall_rule, agent_info, agent_online, agent_port, CLOCK_SKEW, SERVER
from .health import health_probe, job_fix, SKEW_WARN
from .meta import VEYON_PORT
from .network import tcp_open
from .runtime import ApiError, clean_hosts, log, split_host_port, start_job


def firewall_rule_exists():
    """Có luật tường lửa 'KhoaVeyon Agent' ở máy giáo viên không (True/False; None nếu không phải Windows hoặc không đọc được)."""
    if os.name != 'nt':
        return None
    try:
        r = subprocess.run(['netsh', 'advfirewall', 'firewall', 'show', 'rule', 'name=KhoaVeyon Agent'], capture_output=True, text=True,
                           errors='replace', timeout=15, creationflags=0x08000000)
        return r.returncode == 0 and 'KhoaVeyon Agent' in r.stdout
    except (OSError, subprocess.SubprocessError):
        return None


def _row(cid, label, state, detail='', fix=''):
    """state: ok (xanh), warn (vàng), bad (đỏ), na (không kiểm được)."""
    return {'id': cid, 'label': label, 'state': state, 'detail': detail, 'fix': fix}


def diagnose_machine(host):
    hh, _ = split_host_port(host)
    rows = []
    v = tcp_open(hh, VEYON_PORT, 2)
    rows.append(_row('veyon', 'Veyon Service', 'ok' if v else 'bad',
                     'cổng %d đang mở' % VEYON_PORT if v else 'không kết nối được cổng %d: máy tắt, chưa cài Veyon Service, hoặc tường lửa chặn' % VEYON_PORT))
    on = agent_online(hh)
    inf = agent_info(hh) or {}
    if on:
        rows.append(_row('agent', 'Agent (dịch vụ KhoaVeyon)', 'ok', 'đang kết nối · tài khoản: %s · phiên bản dịch vụ %s' % (inf.get('user') or 'chưa ai đăng nhập', inf.get('ver') or '?')))
    elif inf:
        rows.append(_row('agent', 'Agent (dịch vụ KhoaVeyon)', 'bad', 'từng kết nối nhưng đã mất (máy tắt hoặc dịch vụ dừng); xem thêm mục tường lửa và giờ máy'))
    else:
        rows.append(_row('agent', 'Agent (dịch vụ KhoaVeyon)', 'bad', 'chưa kết nối: chạy Setup-MayHocSinh.bat trên máy này một lần (quyền quản trị)'))
    if on and inf.get('skew') is not None:
        sk = abs(inf['skew'])
        st = 'ok' if sk <= SKEW_WARN else 'warn' if sk < CLOCK_SKEW else 'bad'
        rows.append(_row('clock', 'Giờ máy khớp máy giáo viên', st, 'lệch %d giây' % sk if sk >= 1 else 'khớp', 'time' if st != 'ok' else ''))
    elif v and not on:
        rows.append(_row('clock', 'Giờ máy khớp máy giáo viên', 'na', 'chưa đọc được vì Agent chưa kết nối. Nếu đồng hồ máy lệch hơn %d phút thì Agent bị từ chối (xem Nhật ký), hãy chỉnh giờ máy đó' % (CLOCK_SKEW // 60)))
    else:
        rows.append(_row('clock', 'Giờ máy khớp máy giáo viên', 'na', 'cần Agent đang kết nối'))
    if on:
        p = health_probe(hh)
        svc = p.get('svc')
        rows.append(_row('service', 'Bản dịch vụ KhoaVeyonServices.bat', {'ok': 'ok', 'old': 'warn', 'none': 'bad'}.get(svc, 'na'),
                         {'ok': 'đúng bản mới nhất', 'old': 'là bản cũ', 'none': 'chưa có trên máy'}.get(svc, 'không kiểm được (không có bản chuẩn trong payload)'),
                         'service' if svc in ('old', 'none') else ''))
    else:
        rows.append(_row('service', 'Bản dịch vụ KhoaVeyonServices.bat', 'na', 'cần Agent đang kết nối'))
    return {'host': host, 'rows': rows}


def api_diagnose(b):
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào để chẩn đoán')
    with ThreadPoolExecutor(max_workers=min(12, len(hosts))) as ex:
        machines = list(ex.map(diagnose_machine, hosts[:80]))
    fw = firewall_rule_exists()
    port = SERVER['port'] or agent_port()
    teacher = [
        _row('listen', 'Cổng Agent ở máy giáo viên', 'ok' if SERVER['srv'] else 'bad',
             'đang lắng nghe cổng %d' % port if SERVER['srv'] else 'chưa mở được cổng Agent (cổng bận?), đổi cổng ở Cài đặt'),
        _row('firewall', 'Tường lửa máy giáo viên cho phép Agent', 'na' if fw is None else ('ok' if fw else 'bad'),
             'không kiểm được trên hệ điều hành này' if fw is None else ('đã có luật cho cổng %d-%d' % (agent_port(), agent_port() + 2) if fw else 'chưa có luật: máy học sinh không gọi về được'),
             'firewall' if fw is False else ''),
    ]
    return {'machines': machines, 'teacher': teacher}


def api_diagnose_fix(b):
    fix = b.get('fix')
    if fix == 'firewall':
        ok, msg = agent_firewall_rule()
        log(msg, 'ok' if ok else 'err')
        return {'ok': ok, 'msg': msg}
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào để sửa')
    if fix == 'service':
        start_job(job_fix, 'svc', hosts)
        return {'ok': True, 'msg': 'Đang cài lại dịch vụ trên %d máy, xem Nhật ký' % len(hosts)}
    if fix == 'time':
        start_job(job_fix, 'time', hosts)
        return {'ok': True, 'msg': 'Đang đồng bộ giờ %d máy, xem Nhật ký' % len(hosts)}
    raise ApiError('Cách sửa không hợp lệ')
