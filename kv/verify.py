# -*- coding: utf-8 -*-
"""Kiểm tra hiệu lực sau khi khóa (từ bản 3.8.0).

KhoaVeyon chỉ biết lệnh đã gửi (applied.json), không biết lệnh có thật sự có hiệu lực trên máy hay không.
Nút này chạy script chỉ-đọc kvstate.ps1 trên máy học sinh (qua schtasks, SYSTEM), lấy trạng thái thật rồi
so với lệnh đã gửi và báo máy nào lệch. Có tùy chọn gửi lại lệnh cho các máy lệch."""

import json
import os
import shutil
import tempfile

from .ai import ai_state_one
from .applied import APPLIED, APPLIED_LOCK
from .jobs import job_action
from .network import tcp_open
from .paths import load_script
from .runtime import ApiError, CFG, CFG_LOCK, clean_hosts, log, pool_run, split_host_port, start_job
from .vcfg import client_fetch, client_script_run, vcfg_remote_dir


STATE_PS1_NAME = 'kvstate.ps1'
STATE_JSON_NAME = 'kvstate.json'
STATE_PS1 = load_script('kvstate.ps1')
CAT_LABEL = {'net': 'Internet', 'lockdown': 'Khóa Task Manager', 'run': 'Chặn mở app ngoài danh sách',
             'lock': 'Khóa toàn bộ', 'kiosk': 'Kiosk', 'ai': 'Khóa AI', 'blockapp': 'Chặn ứng dụng', 'mute': 'Tắt tiếng'}
NO_CHECK = ('blockapp', 'mute')   # chưa có cách đọc đáng tin: báo "chưa kiểm được", không báo sai


def parse_state(text):
    """Đọc kvstate.json (chấp nhận BOM). users có thể là object khi chỉ có một người dùng."""
    d = json.loads((text or '').lstrip('\ufeff'))
    u = d.get('users')
    d['users'] = [u] if isinstance(u, dict) else list(u or [])
    return d


def compare(expected, state, ai=None):
    """expected: {nhóm: {'key','on'}} lấy từ applied.json. state: kết quả parse_state. ai: (đã khóa?, mô tả) hoặc None.
    Trả về danh sách (nhóm, kết quả, mô tả); kết quả: ok, bad, unknown."""
    users = state.get('users') or []
    any_u = lambda f: any(bool(x.get(f)) for x in users)          # noqa: E731
    out = []
    for cat, e in sorted(expected.items()):
        on = bool(e.get('on'))
        label = CAT_LABEL.get(cat, cat)
        if cat in NO_CHECK:
            out.append((cat, 'unknown', '%s: chưa kiểm được' % label))
            continue
        if cat == 'ai':
            if ai is None:
                out.append((cat, 'unknown', '%s: không đọc được' % label))
            else:
                locked = bool(ai[0])
                out.append((cat, 'ok' if locked == on else 'bad', '%s: %s' % (label, ai[1])))
            continue
        if cat == 'net':
            fw = bool(state.get('fw'))
            out.append((cat, 'ok' if fw == on else 'bad', '%s: %s' % (label, 'đang chặn' if fw else 'không chặn')))
            continue
        if cat == 'kiosk':
            k = bool(state.get('kiosk'))
            out.append((cat, 'ok' if k == on else 'bad', '%s: %s' % (label, 'đang chạy' if k else 'không chạy')))
            continue
        # các nhóm đọc từ registry của người dùng: cần có người đăng nhập
        if not users:
            out.append((cat, 'unknown', '%s: chưa có ai đăng nhập nên không đọc được' % label))
            continue
        if cat == 'lockdown':
            now = any_u('taskmgr')
        elif cat == 'run':
            now = any_u('restrictrun')
        else:  # lock: khóa toàn bộ = chặn mở app + khóa Task Manager; mở khóa thì cả hai phải gỡ
            now = (any_u('restrictrun') and any_u('taskmgr')) if on else (any_u('restrictrun') or any_u('taskmgr'))
        out.append((cat, 'ok' if now == on else 'bad', '%s: %s' % (label, 'đang bật' if now else 'đang tắt')))
    return out


def expected_for(host):
    hh, _ = split_host_port(host)
    with APPLIED_LOCK:
        return {c: dict(v) for c, v in (APPLIED.get(hh) or {}).items()}


def read_remote_state(cfg, host):
    tmp = tempfile.mkdtemp(prefix='kvstate')
    try:
        sp = os.path.join(tmp, STATE_PS1_NAME)
        with open(sp, 'w', encoding='utf-8-sig', newline='') as f:
            f.write(STATE_PS1.replace('\r\n', '\n').replace('\n', '\r\n'))
        rdir = vcfg_remote_dir(cfg)
        bat = '@echo off\npowershell -NoProfile -ExecutionPolicy Bypass -File "%s\\%s" -Out "%s\\%s"\nexit /b %%errorlevel%%\n' % (
            rdir, STATE_PS1_NAME, rdir, STATE_JSON_NAME)
        ok, msg = client_script_run(host, cfg, 'kvstate.bat', bat, files={STATE_PS1_NAME: sp}, timeout=60)
        if not ok:
            return None, msg
        dest = os.path.join(tmp, STATE_JSON_NAME)
        if not client_fetch(host, cfg, STATE_JSON_NAME, dest):
            return None, 'chạy xong nhưng không thấy file trạng thái'
        with open(dest, 'r', encoding='utf-8-sig') as f:
            return parse_state(f.read()), ''
    except (OSError, ValueError) as e:
        return None, 'không đọc được trạng thái: %s' % e
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def verify_one(host, cfg=None, reader=read_remote_state, ai_reader=ai_state_one):
    """Trả về (ok, mô tả, danh sách khóa lệnh cần gửi lại)."""
    exp = expected_for(host)
    if not exp:
        return True, 'chưa gửi lệnh hạn chế nào cho máy này, không có gì để kiểm tra', []
    hh, pp = split_host_port(host)
    if not tcp_open(hh, pp, 1.5):
        return False, 'máy không trả lời (đang tắt?)', []
    if cfg is None:
        with CFG_LOCK:
            cfg = json.loads(json.dumps(CFG))
    state, err = reader(cfg, host)
    if state is None:
        return False, err, []
    ai = ai_reader(host) if 'ai' in exp else None
    res = compare(exp, state, ai)
    bad = [r for r in res if r[1] == 'bad']
    unk = [r for r in res if r[1] == 'unknown']
    fix = [exp[r[0]]['key'] for r in bad]
    parts = ['%s' % r[2] for r in bad] or ['mọi hạn chế kiểm được đều khớp (%d mục)' % sum(1 for r in res if r[1] == 'ok')]
    if unk:
        parts.append('chưa kiểm được: ' + '; '.join(r[2].split(':')[0] for r in unk))
    return (not bad), 'LỆCH: ' + ' | '.join(parts) if bad else '; '.join(parts), fix


def job_verify(hosts, fix):
    log('>>> Kiểm tra hiệu lực hạn chế (%d máy)' % len(hosts), 'head')
    to_fix = {}

    def one(h):
        ok, msg, keys = verify_one(h)
        if keys:
            to_fix[h] = keys
        return ok, msg
    pool_run(one, hosts, 'Kiểm tra hiệu lực hạn chế')
    if fix and to_fix:
        log('Gửi lại lệnh cho %d máy bị lệch' % len(to_fix), 'head')
        for h, keys in to_fix.items():
            for k in keys:
                job_action(k, [h])
    elif to_fix:
        log('%d máy bị lệch. Bấm “Kiểm tra và gửi lại lệnh” để áp lại.' % len(to_fix), 'warn')


def api_verify(b):
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào để kiểm tra')
    start_job(job_verify, hosts, bool(b.get('fix')))
    return {'ok': True}
