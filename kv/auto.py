# -*- coding: utf-8 -*-
"""Tự động theo thời khóa biểu: chế độ lớp, vào tiết, hết tiết, bật và tắt máy theo giờ."""

import datetime
import json
import os
import re
import shutil
import tempfile
import threading
import time

from .actions import ACTION_BY_KEY, ACTIONS, CONFIRM_KEYS
from .ai import job_lock_with_ai
from .excel_lists import list_variants, LISTS, variant_file
from .jobs import job_action, job_dist
from .meta import LOCK_KEYS
from .network import tcp_open
from .power import job_power
from .runtime import ApiError, CFG, CFG_LOCK, clean_hosts, list_path, log, split_host_port, start_job
from .school import _mins, SCHOOL, school_active_slot, SCHOOL_LOCK, school_now, school_save
from .screenshot import job_shot_then_action


# ---------------------------------------------------------------- tự động theo thời khóa biểu (từ bản 3.4.0)
AUTO_DEFAULT_MODES = {
    'Học bình thường': {'start': [], 'end': []},
    'Kiểm tra (chỉ trang cho phép)': {'start': ['allowpage', 'lockdown'], 'end': ['allowall', 'unlock']},
    'Thực hành (chặn app ngoài danh sách)': {'start': ['lockrun-start'], 'end': ['lockrun-stop']},
    'Không dùng AI': {'start': ['blockai'], 'end': ['allowai']},
}
AUTO_LOCK = threading.RLock()
AUTO = {'enabled': False, 'modes': {}, 'class_mode': {}, 'wake_min': 0, 'shutdown_min': 0, 'shutdown_delay': 60, 'cleanup': [], 'done': {}}


def auto_load():
    with SCHOOL_LOCK:
        d = SCHOOL.get('automation')
    with AUTO_LOCK:
        if isinstance(d, dict):
            AUTO.update({k: d[k] for k in AUTO if k in d})
        if not AUTO['modes']:
            AUTO['modes'] = json.loads(json.dumps(AUTO_DEFAULT_MODES))


def auto_save():
    with AUTO_LOCK:
        snap = json.loads(json.dumps(AUTO))
    with SCHOOL_LOCK:
        SCHOOL['automation'] = snap
    school_save()


def auto_mode_for(cls):
    with AUTO_LOCK:
        cm, modes = AUTO['class_mode'], AUTO['modes']
        name = cm.get(cls) or cm.get('*') or ''
        return name if name in modes else ''


def auto_hosts():
    with CFG_LOCK:
        return list(CFG.get('hosts') or [])


def job_run_key(key, hosts):
    """Chạy một lệnh như nút bấm trên trang Điều khiển lớp (tôn trọng công tắc chụp ảnh trước khi khóa và khóa kèm AI)."""
    with CFG_LOCK:
        shot = bool(CFG.get('shot_before_lock'))
        with_ai = bool(CFG.get('lock_with_ai'))
    if with_ai and key in ('lockall-start', 'lockall-stop'):
        job_lock_with_ai(key, hosts, shot)
    elif shot and key in LOCK_KEYS:
        job_shot_then_action(key, hosts)
    else:
        job_action(key, hosts)


def step_label(step):
    if isinstance(step, tuple):
        return 'đẩy danh sách riêng' if step[0] == 'push' else 'trả danh sách chính'
    return ACTION_BY_KEY[step][1]


def lists_target():
    with CFG_LOCK:
        return (CFG.get('dist_target') or r'C:\cmd').strip()


def job_mode_lists(how, lists, hosts):
    """Danh sách riêng theo chế độ lớp. push: chép bản riêng xuống máy học sinh dưới đúng tên danh sách chính
    (script trên máy đọc theo tên đó). restore: chép lại danh sách chính."""
    target = lists_target()
    base_dir = os.path.dirname(list_path('allow'))
    tmp = tempfile.mkdtemp(prefix='kvmode')
    try:
        files = []
        for kind, name in sorted(lists.items()):
            if kind not in LISTS:
                continue
            if how == 'push':
                src = os.path.join(base_dir, variant_file(kind, name))
                if not os.path.isfile(src):
                    log('Không thấy bản riêng "%s" của %s, dùng danh sách chính' % (name, LISTS[kind]['file']), 'warn')
                    continue
                dst = os.path.join(tmp, LISTS[kind]['file'])
                shutil.copy2(src, dst)
                files.append(dst)
            elif os.path.isfile(list_path(kind)):
                files.append(list_path(kind))
        if files:
            title = ('Đẩy danh sách riêng: ' if how == 'push' else 'Trả danh sách chính: ') + ', '.join(sorted(lists.values() if how == 'push' else [LISTS[k]['file'] for k in lists if k in LISTS]))
            job_dist(hosts, files, 'none', '', '', False, target, title)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def job_auto_keys(steps, hosts, reason):
    """steps: lệnh (chuỗi) hoặc ('push'|'restore', {loại danh sách: tên bản riêng}) chạy lần lượt trên các máy đang bật."""
    online = [h for h in hosts if tcp_open(*split_host_port(h), 1.5)]
    if not online:
        log('Tự động (%s): không có máy nào đang bật, bỏ qua' % reason, 'warn')
        return
    log('Tự động (%s): %d máy đang bật, các bước: %s' % (reason, len(online), ', '.join(step_label(s) for s in steps)), 'head')
    for s in steps:
        if isinstance(s, tuple):
            job_mode_lists(s[0], s[1], online)
        else:
            job_run_key(s, online)


def mode_steps(name, phase):
    """Các bước của một chế độ: vào tiết = đẩy danh sách riêng rồi chạy lệnh; hết tiết = chạy lệnh rồi trả danh sách chính."""
    with AUTO_LOCK:
        m = AUTO['modes'].get(name) or {}
        keys = [k for k in m.get(phase, []) if k in ACTION_BY_KEY]
        lists = dict(m.get('lists') or {})
    if phase == 'start':
        return ([('push', lists)] if lists else []) + keys
    return keys + ([('restore', lists)] if lists else [])


def auto_transition(old, new):
    with AUTO_LOCK:
        if not AUTO['enabled']:
            return
        om, nm = auto_mode_for(old) if old else '', auto_mode_for(new) if new else ''
    keys = []
    if om and om != nm:
        keys += mode_steps(om, 'end')
    if old and new != old:   # hết một tiết: dọn máy cho lớp sau (các lệnh giáo viên chọn ở trang Tự động)
        with AUTO_LOCK:
            keys += [k for k in AUTO.get('cleanup', []) if k in ACTION_BY_KEY and k not in keys]
    if nm and nm != om:
        keys += mode_steps(nm, 'start')
    from .engage import job_wall_apply, job_wall_restore, wall_for_mode
    wall_new = wall_for_mode(nm) if (new and nm) else None   # hình nền có tên em ngồi nên đổi lớp là vẽ lại, dù cùng chế độ
    wall_back = bool(old and om and wall_for_mode(om) and not wall_new)
    if not keys and not wall_new and not wall_back:
        return
    hosts = auto_hosts()
    if not hosts:
        log('Tự động: chưa có máy học sinh nào trong danh sách', 'warn')
        return
    if wall_new:
        start_job(job_wall_apply, hosts, wall_new)
    elif wall_back:
        start_job(job_wall_restore, hosts)
    if not keys:
        return
    reason = ('hết tiết %s' % old if old and not new else ('vào tiết %s' % new if new and not old else 'đổi từ %s sang %s' % (old, new)))
    start_job(job_auto_keys, keys, hosts, reason)


def auto_day_slots(dt):
    with SCHOOL_LOCK:
        frm, slots = SCHOOL.get('from') or '', list(SCHOOL.get('slots') or [])
    if frm and dt.strftime('%Y-%m-%d') < frm:
        return []
    return sorted([s for s in slots if s['day'] == dt.weekday()], key=lambda s: s['start'])


def auto_power_tick(dt):
    """Tự bật máy trước tiết đầu và tự tắt máy sau tiết cuối (mỗi ngày một lần)."""
    with AUTO_LOCK:
        if not AUTO['enabled']:
            return
        wake, down, delay = int(AUTO['wake_min'] or 0), int(AUTO['shutdown_min'] or 0), int(AUTO['shutdown_delay'] or 60)
        done = AUTO['done']
        for k in [k for k in done if k[:10] != dt.strftime('%Y-%m-%d')]:
            del done[k]
    slots = auto_day_slots(dt)
    if not slots:
        return
    today = dt.strftime('%Y-%m-%d')
    m = dt.hour * 60 + dt.minute
    first, last = _mins(slots[0]['start']), max(_mins(s['end']) for s in slots)
    hosts = auto_hosts()
    if wake > 0 and today + '|wake' not in done and first - wake <= m < first:
        with AUTO_LOCK:
            AUTO['done'][today + '|wake'] = 1
        auto_save()
        if hosts:
            log('Tự động: sắp đến tiết đầu (%s), đánh thức các máy' % slots[0]['start'], 'head')
            start_job(job_power, 'wake', hosts, 0)
    if down > 0 and today + '|down' not in done and last + down <= m < last + down + 30:
        with AUTO_LOCK:
            AUTO['done'][today + '|down'] = 1
        auto_save()
        if hosts and not school_active_slot(dt):
            log('Tự động: hết tiết cuối (%s), tắt các máy sau %d giây' % (slots[-1]['end'], delay), 'head')
            start_job(job_power, 'shutdown', hosts, delay)


def auto_loop():
    last = None
    while True:
        try:
            cur = (school_now()['current'] or {}).get('cls', '')
            if last is not None and cur != last:
                auto_transition(last, cur)
            last = cur
            auto_power_tick(datetime.datetime.now())
        except Exception as e:  # noqa
            log('Lỗi tự động theo thời khóa biểu: %s' % e, 'err')
        time.sleep(10)


def auto_view():
    with AUTO_LOCK:
        a = json.loads(json.dumps({k: AUTO[k] for k in ('enabled', 'modes', 'class_mode', 'wake_min', 'shutdown_min', 'shutdown_delay', 'cleanup')}))
    with SCHOOL_LOCK:
        classes = sorted(set(SCHOOL['classes']) | {s['cls'] for s in SCHOOL.get('slots') or []})
    today = [dict(s, mode=auto_mode_for(s['cls'])) for s in auto_day_slots(datetime.datetime.now())]
    return {'auto': a, 'classes': classes, 'today': today, 'has_timetable': bool(SCHOOL.get('slots')), 'walls': sorted(SCHOOL.get('wall_presets') or {}),
            'variants': list_variants(os.path.dirname(list_path('allow'))), 'list_titles': {k: m['file'] for k, m in LISTS.items()},
            'actions': [{'key': k, 'label': lbl, 'confirm': k in CONFIRM_KEYS} for k, lbl, _s, _d in ACTIONS]}


def api_auto(_q=None):
    return auto_view()


def auto_clean_lists(raw):
    """lists của một chế độ: {loại danh sách: tên bản riêng}. Chỉ nhận bản riêng đang có trong thư mục danh sách."""
    out = {}
    if not isinstance(raw, dict):
        return out
    have = list_variants(os.path.dirname(list_path('allow')))
    for kind, name in raw.items():
        if not name:
            continue
        if kind not in LISTS:
            raise ApiError('Loại danh sách không hợp lệ: %s' % kind)
        if name not in have.get(kind, []):
            raise ApiError('Không thấy bản riêng "%s" của %s' % (name, LISTS[kind]['file']))
        out[kind] = name
    return out


def api_auto_set(b):
    with AUTO_LOCK:
        new = {'enabled': bool(b.get('enabled')), 'modes': {}, 'class_mode': {}}
        modes = b.get('modes')
        if not isinstance(modes, dict) or not modes:
            raise ApiError('Cần ít nhất một chế độ lớp')
        for name, m in modes.items():
            name = re.sub(r'\s+', ' ', str(name)).strip()[:60]
            if not name:
                raise ApiError('Tên chế độ không được để trống')
            ent = {}
            ent['lists'] = auto_clean_lists((m or {}).get('lists'))
            wn = str((m or {}).get('wall') or '')
            with SCHOOL_LOCK:
                ent['wall'] = wn if wn in (SCHOOL.get('wall_presets') or {}) else ''
            for ph in ('start', 'end'):
                keys = [str(k) for k in ((m or {}).get(ph) or [])]
                bad = [k for k in keys if k not in ACTION_BY_KEY]
                if bad:
                    raise ApiError('Lệnh không tồn tại: %s' % ', '.join(bad))
                ent[ph] = keys
            new['modes'][name] = ent
        new['cleanup'] = [k for k in dict.fromkeys(str(k) for k in (b.get('cleanup') or [])) if k in ACTION_BY_KEY and k not in ('killapp', 'keepapp')][:10]
        cm = b.get('class_mode') or {}
        for cls, name in cm.items():
            if name and name in new['modes']:
                new['class_mode'][str(cls)] = name
        for k, lo, hi in (('wake_min', 0, 120), ('shutdown_min', 0, 240), ('shutdown_delay', 10, 600)):
            try:
                new[k] = max(lo, min(hi, int(b.get(k) or (60 if k == 'shutdown_delay' else 0))))
            except (TypeError, ValueError):
                raise ApiError('Giá trị "%s" phải là số' % k)
        AUTO.update(new)
    auto_save()
    return {'ok': True}


def api_auto_test(b):
    """Chạy thử một chế độ ngay: phase = start hoặc end, trên các máy đang chọn."""
    name, phase = str(b.get('mode') or ''), b.get('phase')
    with AUTO_LOCK:
        m = AUTO['modes'].get(name)
    if not m or phase not in ('start', 'end'):
        raise ApiError('Chế độ hoặc bước chạy không hợp lệ (cần lưu cài đặt trước khi chạy thử)')
    keys = mode_steps(name, phase)
    if not keys:
        raise ApiError('Bước này chưa có lệnh hoặc danh sách riêng nào')
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào để chạy')
    start_job(job_auto_keys, keys, hosts, 'chạy thử "%s" - %s' % (name, 'vào tiết' if phase == 'start' else 'hết tiết'))
    return {'ok': True}
