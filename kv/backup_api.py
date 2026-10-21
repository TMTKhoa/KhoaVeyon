# -*- coding: utf-8 -*-
"""API sao lưu/khôi phục: file sao lưu gửi lên dạng base64 trong JSON (giao diện đọc file rồi gửi)."""

import base64

from .backup import preview_backup, restore_backup
from .runtime import ApiError


def _data(b):
    try:
        return base64.b64decode(str(b.get('data') or ''), validate=False)
    except ValueError:
        raise ApiError('File sao lưu không đọc được')


def api_backup_preview(b):
    return preview_backup(_data(b))


def api_backup_restore(b):
    parts = [p for p in (b.get('parts') or []) if p in ('config', 'school', 'lists')]
    done = restore_backup(_data(b), parts or None)
    if not done:
        raise ApiError('File sao lưu không có gì để khôi phục với các mục đã chọn')
    return {'done': done, 'restart': True}
