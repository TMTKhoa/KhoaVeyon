# -*- coding: utf-8 -*-
"""Nút "Sửa máy tính" của giao diện rút gọn: tự làm lần lượt 3 bước theo đúng thứ tự
   1) QUÉT mạng (nhận lại máy đã đổi IP do DHCP)  ->  2) CHẨN ĐOÁN từng máy + máy giáo viên  ->  3) SỬA lỗi tìm thấy, rồi chẩn đoán lại để báo kết quả."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from .runtime import ApiError, CFG, CFG_LOCK, clean_hosts, log, start_job

STEPS = (('scan', 'Quét mạng (tìm lại IP máy bị đổi)'), ('diag', 'Chẩn đoán từng máy'), ('fix', 'Tự sửa lỗi phát hiện được'))
LOCK = threading.RLock()
REPAIR = {'running': False, 'seq': 0, 'steps': [], 'report': [], 'summary': '', 'started': 0.0, 'finished': 0.0}


def _fresh():
    return [{'id': i, 'label': l, 'state': 'wait', 'detail': ''} for i, l in STEPS]


def _set(step, state, detail=''):
    with LOCK:
        for s in REPAIR['steps']:
            if s['id'] == step:
                s['state'], s['detail'] = state, detail


def plan_fixes(machines, teacher):
    """Hàm thuần: từ kết quả chẩn đoán trả về {'firewall': bool, 'svc': [máy], 'time': [máy], 'off': [máy]}.
    'off' = máy không có Veyon (tắt máy / chưa cài / tường lửa chặn): không sửa từ xa được."""
    plan = {'firewall': False, 'svc': [], 'time': [], 'off': []}
    for r in teacher or []:
        if r.get('fix') == 'firewall' and r.get('state') == 'bad':
            plan['firewall'] = True
    for m in machines or []:
        rows = {r['id']: r for r in m['rows']}
        if rows.get('veyon', {}).get('state') == 'bad':
            plan['off'].append(m['host'])
            continue
        if rows.get('agent', {}).get('state') == 'bad' or rows.get('service', {}).get('state') in ('warn', 'bad'):
            plan['svc'].append(m['host'])
        if rows.get('clock', {}).get('state') in ('warn', 'bad') and m['host'] not in plan['svc']:
            plan['time'].append(m['host'])
    return plan


def _problems(machines, teacher):
    n = 0
    for r in teacher or []:
        if r.get('state') == 'bad':
            n += 1
    for m in machines or []:
        n += sum(1 for r in m['rows'] if r['state'] in ('bad', 'warn'))
    return n


def job_repair(hosts, scan):
    from .agent import agent_firewall_rule
    from .diagnose import api_diagnose
    from .health import job_fix
    try:
        # ---- 1. quét mạng
        moves = []
        if scan:
            _set('scan', 'run', 'Đang quét mạng...')
            from .hostsync import _SCAN_LOCK, scan_and_reconcile
            if _SCAN_LOCK.acquire(timeout=60):
                try:
                    r = scan_and_reconcile()
                finally:
                    _SCAN_LOCK.release()
                if r.get('error'):
                    _set('scan', 'warn', 'Không quét được: %s (vẫn chẩn đoán theo danh sách hiện có)' % r['error'])
                else:
                    moves = r['moves']
                    try:
                        from .setup import refresh_agent_cfg
                        refresh_agent_cfg()
                    except Exception:  # noqa
                        pass
                    _set('scan', 'ok', 'Thấy %d máy chạy Veyon, thêm mới %d, đổi IP %d' % (len(r['found']), r['added'], len(moves)))
            else:
                _set('scan', 'warn', 'Đang có lần quét khác chạy, bỏ qua')
        else:
            _set('scan', 'ok', 'Bỏ qua')
        mp = {old: new for old, new in moves}
        hosts = [mp.get(h, h) for h in hosts]
        if not hosts:
            with CFG_LOCK:
                hosts = list(CFG.get('hosts') or [])
        hosts = clean_hosts(hosts)
        if not hosts:
            _set('diag', 'bad', 'Chưa có máy nào trong danh sách')
            _set('fix', 'wait', '')
            with LOCK:
                REPAIR['summary'] = 'Chưa có máy nào. Hãy thêm máy ở trang Điều khiển lớp hoặc bấm quét mạng.'
            return
        # ---- 2. chẩn đoán
        _set('diag', 'run', 'Đang kiểm tra %d máy...' % len(hosts))
        d = api_diagnose({'hosts': hosts})
        before = _problems(d['machines'], d['teacher'])
        plan = plan_fixes(d['machines'], d['teacher'])
        _set('diag', 'ok' if not before else 'warn', 'Phát hiện %d điểm cần chú ý' % before if before else 'Mọi thứ đều ổn')
        # ---- 3. sửa
        todo = bool(plan['firewall'] or plan['svc'] or plan['time'])
        if not todo:
            _set('fix', 'ok', 'Không có gì cần sửa' if not plan['off'] else 'Không sửa từ xa được máy tắt')
        else:
            _set('fix', 'run', 'Đang sửa...')
            did = []
            if plan['firewall']:
                ok, msg = agent_firewall_rule()
                log(msg, 'ok' if ok else 'err')
                did.append('tường lửa máy giáo viên')
            if plan['svc']:
                job_fix('svc', plan['svc'])
                did.append('cài lại dịch vụ %d máy' % len(plan['svc']))
            if plan['time']:
                job_fix('time', plan['time'])
                did.append('chỉnh giờ %d máy' % len(plan['time']))
            time.sleep(6 if plan['svc'] else 2)   # đợi Agent kết nối lại rồi mới kiểm chứng
            _set('fix', 'ok', 'Đã: ' + ', '.join(did))
        # ---- kết quả: chẩn đoán lại
        d2 = api_diagnose({'hosts': hosts}) if todo else d
        after = _problems(d2['machines'], d2['teacher'])
        report = []
        for m in d2['machines']:
            bad = [r for r in m['rows'] if r['state'] in ('bad', 'warn')]
            report.append({'host': m['host'], 'ok': not bad, 'issues': ['%s: %s' % (r['label'], r['detail']) for r in bad]})
        for r in d2['teacher']:
            if r['state'] == 'bad':
                report.insert(0, {'host': 'Máy giáo viên', 'ok': False, 'issues': ['%s: %s' % (r['label'], r['detail'])]})
        with LOCK:
            REPAIR['report'] = report
            n_ok = sum(1 for x in report if x['ok'] and x['host'] != 'Máy giáo viên')
            REPAIR['summary'] = ('✔ Mọi máy đều hoạt động bình thường (%d máy).' % n_ok) if not after else (
                'Còn %d điểm chưa ổn (%d/%d máy tốt). Máy tắt hoặc chưa cài Veyon cần bật/cài tại chỗ.' % (after, n_ok, len(hosts)))
        log('Sửa máy tính xong: %s' % REPAIR['summary'], 'ok' if not after else 'warn')
    except Exception as e:  # noqa
        log('Sửa máy tính gặp lỗi: %s' % e, 'err')
        with LOCK:
            for s in REPAIR['steps']:
                if s['state'] == 'run':
                    s['state'], s['detail'] = 'bad', str(e)
            REPAIR['summary'] = 'Lỗi: %s' % e
    finally:
        with LOCK:
            REPAIR['running'] = False
            REPAIR['finished'] = time.time()


def api_repair_state(_q=None):
    with LOCK:
        return {k: (list(v) if isinstance(v, list) else v) for k, v in REPAIR.items()}


def api_repair_start(b):
    with LOCK:
        if REPAIR['running']:
            raise ApiError('Đang sửa máy tính, vui lòng đợi')
        REPAIR.update(running=True, seq=REPAIR['seq'] + 1, steps=_fresh(), report=[], summary='', started=time.time(), finished=0.0)
    log('=== SỬA MÁY TÍNH: quét → chẩn đoán → sửa ===', 'head')
    start_job(job_repair, clean_hosts(b.get('hosts')), b.get('scan', True) is not False)
    return api_repair_state()
