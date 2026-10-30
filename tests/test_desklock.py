# -*- coding: utf-8 -*-
"""Khóa hình nền + icon Desktop (-desklock-start/-stop): kiểm tra chỗ nối giữa giao diện giáo viên và KhoaVeyonServices.bat (không cần Windows)."""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class DeskLock(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, 'payload', 'KhoaVeyonServices.bat'), encoding='utf-8') as f:
            self.bat = f.read()

    def test_actions_registered_and_run_by_system_service(self):
        from kv.actions import ACTION_BY_KEY
        from kv.meta import GROUPS, LOCK_KEYS, FREE_KEYS
        from kv.remote import SERVICE_MODES
        for k in ('desklock-start', 'desklock-stop'):
            self.assertIn(k, ACTION_BY_KEY)
            self.assertIn(k, SERVICE_MODES)          # ghi HKLM và Program Files nên phải chạy bằng SYSTEM
            self.assertTrue(any(k in keys for _, keys in GROUPS))
            self.assertIn('%%M in (' , self.bat)
        self.assertIn('desklock-start', LOCK_KEYS)
        self.assertIn('desklock-stop', FREE_KEYS)

    def test_bat_wires_both_modes_and_service(self):
        for m in ('desklock-start', 'desklock-stop'):
            self.assertIn('set "MODE=%s"' % m, self.bat)
            self.assertIn("'%s' {" % m, self.bat)
        lists = re.findall(r'for %%M in \(([^)]*)\) do \(', self.bat)
        self.assertEqual(sum('desklock-start desklock-stop' in x for x in lists), 2)   # -install và -uninstall
        self.assertIn('call "%SELF%" -desklock-stop', self.bat)
        self.assertIn('DeskGuardCmd()', self.bat)

    def test_embedded_guard_script_is_intact(self):
        i = self.bat.index("$guardSrc = @'")
        j = self.bat.index("\n'@", i)
        guard = self.bat[i + len("$guardSrc = @'"):j]
        self.assertFalse(re.search(r"^'@", guard, re.M))        # here-string không bị cắt giữa chừng
        self.assertEqual(guard.count('{'), guard.count('}'))
        self.assertEqual(guard.count('('), guard.count(')'))
        self.assertIn('LVM_SETITEMPOSITION', guard)
        self.assertIn('NoChangingWallPaper', self.bat)


if __name__ == '__main__':
    unittest.main()
