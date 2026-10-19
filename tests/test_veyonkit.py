# -*- coding: utf-8 -*-
"""Kiểm thử lệnh gửi Setup-MayHocSinh.bat qua Veyon (không cần Windows hay Veyon)."""
import base64
import gzip
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kv.veyonkit import build_kit_command, MAX_CMDLINE  # noqa: E402


class VeyonKitTest(unittest.TestCase):
    def test_command_roundtrip(self):
        files = [('Setup-MayHocSinh.bat', b'@echo off\r\necho xin chao\r\n' * 50), ('ab_public.pem', b'KEY')]
        cmd = build_kit_command(files)
        parts = cmd.split(' ')  # Veyon tách tham số theo dấu cách
        self.assertEqual(parts[-2], '-EncodedCommand')
        self.assertLess(len(cmd), MAX_CMDLINE)
        ps = base64.b64decode(parts[-1]).decode('utf-16-le')
        got = dict(re.findall(r"W '([^']+)' '([A-Za-z0-9+/=]+)'", ps))
        for name, data in files:
            self.assertEqual(gzip.decompress(base64.b64decode(got[name])), data)
        self.assertIn('-Verb RunAs', ps)


if __name__ == '__main__':
    unittest.main()
