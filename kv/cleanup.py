# -*- coding: utf-8 -*-
"""Dọn ảnh, bản ghi vi phạm và thư mục ảnh chụp cũ."""

import json
import os
import shutil
import time

from .alerts import _csv_cell, ALERT_CSV, ALERT_FILE, ALERT_LOCK, ALERTS
from .evidence import evidence_root, watch_num
from .runtime import ApiError, CFG, CFG_LOCK
from .screenshot import shot_root


# ---------------------------------------------------------------- dọn ảnh cũ
def evidence_cleanup(days, record_days=None):
    """Xóa ảnh vi phạm và ảnh chụp cũ hơn `days` ngày, bản ghi văn bản (không có ảnh) cũ hơn `record_days` ngày
    (mặc định bằng `days`). Số ngày <= 0: không xóa loại đó. Ảnh nhạy cảm nên giữ ngắn hơn bản ghi dùng cho thống kê."""
    res = {'images': 0, 'records': 0, 'shots': 0, 'cutoff': 0}
    record_days = days if record_days is None else record_days
    if days <= 0 and record_days <= 0:
        return res
    now = time.time()
    img_cutoff = now - days * 86400 if days > 0 else 0
    cutoff = now - record_days * 86400 if record_days > 0 else 0   # mốc xóa bản ghi
    res['cutoff'] = cutoff
    root = evidence_root()
    # Ảnh nằm trong <ngày>\<lớp>\ (bản mới) hoặc <máy>\ (bản cũ): duyệt mọi thư mục con, từ trong ra ngoài
    for dp, _dirs, files in os.walk(root, topdown=False):
        if os.path.realpath(dp) == os.path.realpath(root):
            continue
        for f in files:
            fp = os.path.join(dp, f)
            try:
                if img_cutoff and f.lower().endswith('.jpg') and os.path.getmtime(fp) < img_cutoff:
                    os.remove(fp)
                    res['images'] += 1
            except OSError:
                pass
        try:
            os.rmdir(dp)  # chỉ xóa được khi thư mục rỗng
        except OSError:
            pass
    sr = shot_root()
    for d in os.listdir(sr):
        dp = os.path.join(sr, d)
        try:
            if img_cutoff and os.path.isdir(dp) and os.path.getmtime(dp) < img_cutoff:
                shutil.rmtree(dp)
                res['shots'] += 1
        except OSError:
            pass
    for f in os.listdir(root):  # các file lịch sử đã đổi tên khi bấm "Xóa danh sách"
        fp = os.path.join(root, f)
        try:
            if cutoff and f.startswith('alerts-') and f.endswith('.old') and os.path.getmtime(fp) < cutoff:
                os.remove(fp)
        except OSError:
            pass
    if not cutoff:   # không xóa bản ghi: chỉ dọn ảnh
        return res
    with ALERT_LOCK:
        keep = [e for e in ALERTS if e.get('ts', 0) >= cutoff]
        res['records'] += len(ALERTS) - len(keep)
        ALERTS[:] = keep
        jp = os.path.join(root, ALERT_FILE)
        try:
            if os.path.exists(jp):
                with open(jp, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                out = []
                for ln in lines:
                    try:
                        if float(json.loads(ln).get('ts', 0)) >= cutoff:
                            out.append(ln)
                    except (ValueError, AttributeError, TypeError):
                        pass
                if len(out) != len(lines):
                    with open(jp + '.tmp', 'w', encoding='utf-8') as f:
                        f.writelines(out)
                    os.replace(jp + '.tmp', jp)
            cp = os.path.join(root, ALERT_CSV)
            if os.path.exists(cp):
                import csv
                lim = time.strftime('%Y-%m-%d', time.localtime(cutoff))
                with open(cp, 'r', encoding='utf-8-sig', newline='') as f:
                    rows = list(csv.reader(f))
                kept = [rows[0]] + [r for r in rows[1:] if r and r[0] >= lim] if rows else []
                if len(kept) != len(rows):
                    with open(cp + '.tmp', 'w', encoding='utf-8-sig', newline='') as f:
                        f.write('\r\n'.join(','.join(_csv_cell(x) for x in r) for r in kept[:1]) + '\r\n')
                        f.write(''.join(','.join(_csv_cell(x) for x in r) + '\r\n' for r in kept[1:]))
                    os.replace(cp + '.tmp', cp)
        except OSError:
            pass
    return res


def api_cleanup(_b=None):
    with CFG_LOCK:
        days = watch_num(CFG, 'keep_days', 14, 0, 3650)
        rdays = watch_num(CFG, 'keep_records_days', 180, 0, 3650)
    if days <= 0 and rdays <= 0:
        raise ApiError('Đang để 0 ngày (không tự xóa). Hãy nhập số ngày muốn giữ ảnh.')
    return evidence_cleanup(days, rdays)
