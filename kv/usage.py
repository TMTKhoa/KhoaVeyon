# -*- coding: utf-8 -*-
"""Thống kê dùng máy trong một khoảng thời gian, đọc từ nhật ký hoạt động có sẵn trên máy học sinh
(C:\\cmd\\log\\activity_<máy>_<ngày>.csv: cửa sổ nào đang ở trước, không ghi phím)."""

import csv
import io
import ntpath
import time

from .remote import rfs_read, rfs_scan
from .runtime import ApiError, clean_hosts, split_host_port
from .student import who

LOG_DIR = 'C:\\cmd\\log'
CAP = 180        # giây: một dòng tính tối đa chừng này (nhật ký tự lưu mỗi 3 phút)


def parse_activity(text, since, until, cap=CAP):
    """Từ nội dung CSV trả về ({tiến trình: giây}, {tiêu đề cửa sổ: giây}). Mỗi dòng kéo dài đến dòng kế tiếp (tối đa cap giây)."""
    rows = []
    for r in csv.reader(io.StringIO(text.lstrip('\ufeff'))):
        if len(r) < 7 or r[0] == 'Date' or r[6].startswith('action'):
            continue
        try:
            ts = time.mktime(time.strptime(r[0] + ' ' + r[1], '%Y-%m-%d %H:%M:%S'))
        except ValueError:
            continue
        rows.append((ts, r[4], r[5].lower()))
    rows.sort()
    procs, titles = {}, {}
    for i, (ts, title, proc) in enumerate(rows):
        end = rows[i + 1][0] if i + 1 < len(rows) else until
        a, b = max(ts, since), min(end, ts + cap, until)
        if b <= a or not proc:
            continue
        procs[proc] = procs.get(proc, 0) + (b - a)
        if title:
            titles[title] = titles.get(title, 0) + (b - a)
    return procs, titles


def usage_one(host, since, until):
    hh, _ = split_host_port(host)
    day = time.strftime('%Y-%m-%d', time.localtime(until))
    names = [e['name'] for e in rfs_scan(hh, LOG_DIR) if not e['dir'] and e['name'].startswith('activity_') and e['name'].endswith('_%s.csv' % day)]
    if not names:
        raise FileNotFoundError('chưa có nhật ký hôm nay')
    text = rfs_read(hh, ntpath.join(LOG_DIR, names[0])).decode('utf-8', 'replace')
    procs, titles = parse_activity(text, since, until)
    top = sorted(procs.items(), key=lambda x: -x[1])[:6]
    tt = sorted(titles.items(), key=lambda x: -x[1])[:5]
    return {'procs': [{'name': k, 'sec': int(v)} for k, v in top], 'titles': [{'name': k, 'sec': int(v)} for k, v in tt], 'total': int(sum(procs.values()))}


def api_usage(b):
    hosts = clean_hosts(b.get('hosts'))
    if not hosts:
        raise ApiError('Chưa có máy nào')
    try:
        minutes = max(0, min(600, int(b.get('minutes') if b.get('minutes') is not None else 45)))
    except (TypeError, ValueError):
        minutes = 45
    until = time.time()
    since = until - minutes * 60 if minutes else time.mktime(time.strptime(time.strftime('%Y-%m-%d'), '%Y-%m-%d'))
    out = []
    from concurrent.futures import ThreadPoolExecutor

    def one(h):
        name, cls, no = who(h)
        try:
            r = usage_one(h, since, until)
        except (OSError, ValueError) as e:
            return {'host': h, 'name': name, 'error': str(e)[:160]}
        return dict(r, host=h, name=name)
    with ThreadPoolExecutor(max_workers=min(12, len(hosts))) as ex:
        out = list(ex.map(one, hosts[:80]))
    return {'rows': out, 'minutes': minutes, 'since': since, 'until': until}
