# -*- coding: utf-8 -*-
"""Hằng số và hàm dùng chung cho giám sát: thư mục bằng chứng, đọc số trong cài đặt."""

import os

from .paths import CONFIG_PATH


# ---------------------------------------------------------------- giám sát vi phạm: tự chụp ảnh khi học sinh mở trang/ứng dụng ngoài danh sách
WATCH_REMOTE_DIR = r'C:\Users\Public\KhoaVeyonEvidence'  # thư mục mà mọi người dùng đều ghi được


def watch_num(cfg, key, default, lo, hi):
    try:
        return max(lo, min(hi, int(str(cfg.get(key) or default).strip())))
    except ValueError:
        return default


def evidence_root():
    d = os.path.join(os.path.dirname(CONFIG_PATH), 'evidence')
    os.makedirs(d, exist_ok=True)
    return d
