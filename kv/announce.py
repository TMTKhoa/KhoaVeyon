# -*- coding: utf-8 -*-
"""Thông báo \"Máy này của ai\" xuống màn hình học sinh (script kvseat)."""

import json
import os
import shutil
import tempfile
import time

from .remote import distribute_to_host, remote_run
from .runtime import ApiError, CFG, CFG_LOCK, clean_hosts, log, pool_run, start_job
from .school import _cls_norm, LAYOUT_DEFAULT, SCHOOL, SCHOOL_LOCK
from .screenshot import _q
from .seating import att_state, seat_host_map, SEAT_JSON_NAME, SEAT_PS1, SEAT_PS1_NAME, SEAT_TASK
from .vcfg import vcfg_remote_dir


def seat_notice_payload(cls, name, no, moved, seconds, keep):
    title = 'BẠN ĐƯỢC CHUYỂN SANG MÁY NÀY' if moved else 'MÁY NÀY LÀ CỦA'
    return {'stamp': '%.3f' % time.time(), 'title': title, 'name': name,
            'detail': 'Lớp %s · Máy %d' % (cls, no), 'seconds': int(seconds), 'keep': bool(keep), 'clear': False}


def seat_notice_one(cfg, host, payload):
    rdir = vcfg_remote_dir(cfg)
    tmp = tempfile.mkdtemp(prefix='kvseat')
    try:
        jp = os.path.join(tmp, SEAT_JSON_NAME)
        with open(jp, 'w', encoding='utf-8', newline='') as f:
            json.dump(payload, f, ensure_ascii=False)
        files = [jp]
        if not payload.get('clear'):
            sp = os.path.join(tmp, SEAT_PS1_NAME)
            with open(sp, 'w', encoding='utf-8-sig', newline='') as f:  # BOM để PowerShell 5 đọc đúng
                f.write(SEAT_PS1.replace('\r\n', '\n').replace('\n', '\r\n'))
            files.append(sp)
        distribute_to_host(host, files, rdir)
    except Exception as e:  # noqa
        return False, 'không chép được thông báo: %s' % e
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if payload.get('clear'):
        return True, 'đã gỡ nhãn chỗ ngồi'
    cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File %s -Json %s' % (
        _q(rdir + '\\' + SEAT_PS1_NAME), _q(rdir + '\\' + SEAT_JSON_NAME))
    rc, out = remote_run(host, cmd, interactive=True, name=SEAT_TASK)
    if rc != 0:
        return False, out
    return True, 'đã báo: %s (%s)' % (payload['name'], payload['detail'])


def job_announce(cls, only, seconds, keep, clear, moved=False):
    """Hiện bảng "Máy này của ai" trên từng máy học sinh. only: chỉ các em này (rỗng = cả lớp có mặt). clear: gỡ nhãn trên mọi máy."""
    with CFG_LOCK:
        cfg = json.loads(json.dumps(CFG))
    if clear:
        hosts = clean_hosts(cfg.get('hosts') or [])
        log('>>> Gỡ nhãn chỗ ngồi (%d máy)' % len(hosts), 'head')
        pool_run(lambda h: seat_notice_one(cfg, h, {'stamp': '%.3f' % time.time(), 'clear': True}), hosts, 'Gỡ nhãn chỗ ngồi')
        return
    st = att_state(cls)
    with SCHOOL_LOCK:
        lay = dict(LAYOUT_DEFAULT, **(SCHOOL['layouts'].get(cls) or {}))
    hmap = seat_host_map(lay)
    items = {}
    sharers = {}
    for n, no in st.get('shares', {}).items():
        sharers.setdefault(str(no), []).append(n)
    for no, name in st['seats'].items():
        mates = sharers.get(no, [])
        if only and name not in only and not any(m in only for m in mates):
            continue
        h = hmap.get(int(no))
        if not h:
            continue
        pl = seat_notice_payload(cls, name, int(no), moved and not mates, seconds, keep)
        if mates:  # máy này có bạn ngồi chung
            pl['title'] = 'HÔM NAY NGỒI CHUNG MÁY VỚI BẠN'
            pl['name'] = ' & '.join(mates)
            pl['detail'] = 'Máy của %s · Lớp %s · Máy %d' % (name, cls, int(no))
        items[h] = pl
    if not items:
        log('Không có máy nào để thông báo: lớp %s chưa xếp chỗ, hoặc số máy chưa khớp tên máy (xem Tên máy mẫu ở sơ đồ chỗ ngồi)' % cls, 'warn')
        return
    log('>>> Thông báo chỗ ngồi lớp %s (%d máy)' % (cls, len(items)), 'head')
    pool_run(lambda h: seat_notice_one(cfg, h, items[h]), sorted(items), 'Thông báo chỗ ngồi')


def api_school_announce(b):
    cls = _cls_norm(b.get('cls'))
    with SCHOOL_LOCK:
        if cls not in SCHOOL['classes']:
            raise ApiError('Lớp không có trong danh sách lớp')
    try:
        seconds = max(3, min(300, int(b.get('seconds') or 15)))
    except (TypeError, ValueError):
        raise ApiError('Số giây phải là số')
    start_job(job_announce, cls, [], seconds, bool(b.get('keep', True)), bool(b.get('clear')), False)
    return {'ok': True}


NOTICE_MAX = 160


def notice_payload(text, seconds, keep=False):
    """Bảng thông báo tùy ý của giáo viên: dùng chung script kvseat (tiêu đề, nội dung lớn, dòng giờ)."""
    return {'stamp': '%.3f' % time.time(), 'title': 'THÔNG BÁO CỦA GIÁO VIÊN', 'name': text,
            'detail': time.strftime('%H:%M'), 'seconds': int(seconds), 'keep': bool(keep), 'clear': False}


def job_notice(text, seconds, hosts):
    with CFG_LOCK:
        cfg = json.loads(json.dumps(CFG))
    pl = notice_payload(text, seconds)
    log('>>> Gửi thông báo tới %d máy: %s' % (len(hosts), text), 'head')
    pool_run(lambda h: seat_notice_one(cfg, h, pl), hosts, 'Gửi thông báo')


def api_notice(b):
    text = ' '.join(str(b.get('text') or '').split())
    if not text:
        raise ApiError('Chưa nhập nội dung thông báo')
    if len(text) > NOTICE_MAX:
        raise ApiError('Thông báo tối đa %d ký tự (đang %d)' % (NOTICE_MAX, len(text)))
    try:
        seconds = max(3, min(300, int(b.get('seconds') or 20)))
    except (TypeError, ValueError):
        raise ApiError('Số giây phải là số')
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào để gửi')
    start_job(job_notice, text, seconds, hosts)
    return {'ok': True}
