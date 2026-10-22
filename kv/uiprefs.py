# -*- coding: utf-8 -*-
"""Tùy chỉnh giao diện chương trình giáo viên (màu, chữ, chế độ tối, ẩn trang...). Lưu trong cấu hình, đi theo file sao lưu."""

import re

from .config import save_config
from .runtime import ApiError, CFG, CFG_LOCK

SIDES = ('navy', 'forest', 'plum', 'slate', 'black', 'accent')
DEFAULTS = {'theme': 'light', 'accent': '#2563eb', 'side': 'navy', 'font': 100, 'zoom': 100, 'radius': 'normal', 'compact_nav': False,
            'dense': False, 'hidden_pages': [], 'brand': '', 'tile': 'normal', 'anim': True}
HEX = re.compile(r'^#[0-9a-fA-F]{6}$')


def ui_clean(raw):
    r = raw if isinstance(raw, dict) else {}
    out = dict(DEFAULTS)
    if r.get('theme') in ('light', 'dark', 'auto'):
        out['theme'] = r['theme']
    if HEX.match(str(r.get('accent') or '')):
        out['accent'] = r['accent'].lower()
    if r.get('side') in SIDES:
        out['side'] = r['side']
    for k, lo, hi in (('font', 80, 140), ('zoom', 70, 150)):
        try:
            out[k] = max(lo, min(hi, int(r.get(k, DEFAULTS[k]))))
        except (TypeError, ValueError):
            pass
    if r.get('radius') in ('sharp', 'normal', 'round'):
        out['radius'] = r['radius']
    if r.get('tile') in ('small', 'normal', 'large'):
        out['tile'] = r['tile']
    for k in ('compact_nav', 'dense'):
        out[k] = bool(r.get(k))
    out['anim'] = bool(r.get('anim', True))
    out['brand'] = re.sub(r'[\x00-\x1f<>]', '', str(r.get('brand') or '')).strip()[:24]
    out['hidden_pages'] = [p for p in dict.fromkeys(str(x) for x in (r.get('hidden_pages') or [])) if re.fullmatch(r'[a-z]{2,12}', p) and p not in ('settings', 'control')][:30]
    return out


def api_ui_prefs(_q=None):
    with CFG_LOCK:
        return {'prefs': ui_clean(CFG.get('ui_prefs')), 'defaults': DEFAULTS}


def api_ui_prefs_save(b):
    if not isinstance(b.get('prefs'), dict):
        raise ApiError('Dữ liệu không hợp lệ')
    p = ui_clean(b['prefs'])
    with CFG_LOCK:
        CFG['ui_prefs'] = p
        save_config(CFG)
    return {'prefs': p}
