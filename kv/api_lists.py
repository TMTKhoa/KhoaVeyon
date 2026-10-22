# -*- coding: utf-8 -*-
"""API danh sách Excel và danh sách máy: kiểm tra, lưu, cảnh báo."""

import json
import os

from .actions import ACTION_BY_KEY, ACTIONS, CONFIRM_KEYS
from .config import save_config
from .excel_lists import list_variants, LISTS, read_list, variant_clean, variant_file, write_list
from .jobs import job_after_save
from .meta import FREE_KEYS, GROUPS, ICONS, LOCK_KEYS
from .paths import abs_path, APP_DIR, CONFIG_PATH, find_veyon_cli, VERSION
from .remote import sync_lists, unc_target
from .runtime import (
    ApiError, CFG, CFG_LOCK, clean_hosts, list_path, log, PAYLOAD_DIR, start_job, STATE, warnings_for,
)


def api_state(_q=None):
    with CFG_LOCK:
        cfg = json.loads(json.dumps(CFG))
    cli = find_veyon_cli(cfg['veyon_cli'])
    actions = []
    for key, label, switch, _d in ACTIONS:
        actions.append({'key': key, 'label': label, 'switch': switch, 'feature': cfg['features'].get(key, ''),
                        'icon': ICONS.get(key, '▶'), 'confirm': key in CONFIRM_KEYS,
                        'kind': 'lock' if key in LOCK_KEYS else ('free' if key in FREE_KEYS else 'other')})
    lists = {}
    for k, m in LISTS.items():
        lists[k] = {'file': m['file'], 'title': m['title'], 'col_a': m['col_a'], 'hint': m['hint'],
                    'apply': m['apply'], 'apply_label': ACTION_BY_KEY[m['apply']][1],
                    'presets': {n: [list(r) for r in rows] for n, rows in m['presets'].items()}}
    return {'cfg': cfg, 'config_path': CONFIG_PATH, 'app_dir': APP_DIR, 'list_dir': abs_path(cfg['list_dir']),
            'payload_dir': PAYLOAD_DIR, 'veyon_cli_path': cli, 'veyon_cli_found': os.path.isfile(cli),
            'actions': actions, 'groups': [{'title': t, 'keys': k} for t, k in GROUPS], 'lists': lists,
            'windows': os.name == 'nt', 'version': VERSION, 'update': STATE.get('update')}


def api_list_get(q):
    kind = q.get('kind')
    if kind not in LISTS:
        raise ApiError('Danh sách không tồn tại')
    path = list_path(kind)
    try:
        rows = read_list(path)
    except Exception as e:  # noqa
        raise ApiError('Không đọc được %s: %s' % (path, e))
    return {'rows': [list(r) for r in rows], 'path': path, 'exists': os.path.exists(path),
            'warnings': warnings_for(kind, rows), 'variants': list_variants(os.path.dirname(path)).get(kind, [])}


def _variant_path(kind, name):
    if kind not in LISTS:
        raise ApiError('Danh sách không tồn tại')
    try:
        return os.path.join(os.path.dirname(list_path(kind)), variant_file(kind, name))
    except ValueError as e:
        raise ApiError(str(e))


def api_list_variant_get(q):
    path = _variant_path(q.get('kind'), q.get('name'))
    if not os.path.exists(path):
        raise ApiError('Không thấy bản riêng này')
    try:
        rows = read_list(path)
    except Exception as e:  # noqa
        raise ApiError('Không đọc được %s: %s' % (path, e))
    return {'rows': [list(r) for r in rows], 'path': path, 'warnings': warnings_for(q.get('kind'), rows)}


def api_list_variant_save(b):
    """Lưu các dòng đang soạn thành một bản riêng. Không gửi xuống máy học sinh (chỉ đẩy khi chế độ lớp dùng nó)."""
    kind = b.get('kind')
    name = variant_clean(b.get('name'))
    path = _variant_path(kind, name)
    rows = [(str(r[0]).strip(), str(r[1] if len(r) > 1 else '').strip()) for r in (b.get('rows') or [])
            if str(r[0]).strip()]
    try:
        write_list(path, kind, rows)
    except PermissionError:
        raise ApiError('Không ghi được %s. Nếu file đang mở trong Excel, hãy đóng lại rồi lưu.' % path)
    except Exception as e:  # noqa
        raise ApiError('Không ghi được %s: %s' % (path, e))
    log('Đã lưu bản riêng "%s" (%d dòng): %s' % (name, len(rows), path), 'ok')
    return {'ok': True, 'name': name, 'count': len(rows), 'variants': list_variants(os.path.dirname(path)).get(kind, [])}


def api_list_variant_delete(b):
    kind = b.get('kind')
    path = _variant_path(kind, b.get('name'))
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError as e:
        raise ApiError('Không xóa được %s: %s' % (path, e))
    return {'ok': True, 'variants': list_variants(os.path.dirname(path)).get(kind, [])}


def api_check(b):
    kind = b.get('kind')
    if kind not in LISTS:
        raise ApiError('Danh sách không tồn tại')
    return {'warnings': warnings_for(kind, b.get('rows') or [])}


def api_list_save(b):
    kind = b.get('kind')
    if kind not in LISTS:
        raise ApiError('Danh sách không tồn tại')
    rows = [(str(r[0]).strip(), str(r[1] if len(r) > 1 else '').strip()) for r in (b.get('rows') or [])
            if str(r[0]).strip()]
    path = list_path(kind)
    try:
        write_list(path, kind, rows)
    except PermissionError:
        raise ApiError('Không ghi được %s. Nếu file đang mở trong Excel, hãy đóng lại rồi lưu.' % path)
    except Exception as e:  # noqa
        raise ApiError('Không ghi được %s: %s' % (path, e))
    log('Đã lưu %d dòng vào %s' % (len(rows), path), 'ok')
    with CFG_LOCK:
        if CFG.get('auto_sync') and (CFG.get('sync_dir') or '').strip():
            try:
                n, err = sync_lists(CFG)
            except Exception as e:  # noqa
                n, err = 0, str(e)
            log('Đồng bộ lỗi: %s' % err if err else 'Đã đồng bộ %d file sang %s' % (n, CFG['sync_dir']),
                'err' if err else 'ok')
        push = bool(CFG.get('auto_push', True))
        target = (CFG.get('dist_target') or '').strip()
    hosts = clean_hosts(b.get('hosts'))
    apply_key = LISTS[kind]['apply'] if b.get('apply') else ''
    pushed = 0
    if push and hosts:
        try:
            unc_target('x', target)
        except ValueError as e:
            log('Lỗi thư mục đích, chưa gửi file xuống máy học sinh: %s' % e, 'err')
            push = False
    if push and hosts:
        pushed = len(hosts)
    elif push and not hosts:
        log('Chưa có máy học sinh nào nên chưa gửi %s xuống máy học sinh.' % os.path.basename(path), 'warn')
    if hosts and (pushed or apply_key):
        start_job(job_after_save, hosts, path, bool(pushed), apply_key, target)
    return {'ok': True, 'count': len(rows), 'warnings': warnings_for(kind, rows), 'pushed': pushed,
            'applied': bool(apply_key and hosts)}


def api_hosts(b):
    with CFG_LOCK:
        old = list(CFG.get('hosts') or [])
        CFG['hosts'] = clean_hosts(b.get('hosts'))
        gone = [h for h in old if h not in CFG['hosts']]
        for key in ('macs', 'host_names', 'host_auto_names'):   # máy đã xóa (vd. IP cũ do DHCP đổi) thì bỏ luôn MAC và tên đã nhớ
            d = CFG.get(key)
            if isinstance(d, dict):
                for h in gone:
                    d.pop(h, None)
                    d.pop(h.rsplit(':', 1)[0] if h.count(':') == 1 else h, None)
        save_config(CFG)
    try:
        from .status import STATUS, STATUS_LOCK
        with STATUS_LOCK:
            for h in gone:
                STATUS.pop(h, None)
    except Exception:  # noqa
        pass
    return {'ok': True, 'removed': len(gone)}
