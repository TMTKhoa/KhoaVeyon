# -*- coding: utf-8 -*-
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kv import featres
from kv.config import DEFAULT_CONFIG
import copy


class FeatRes(unittest.TestCase):
    def test_pick_by_name_ignores_case_and_spaces(self):
        items = [{'Name': 'Khóa  toàn bộ AI', 'Path': 'x', 'Uid': '{u1}'}]
        self.assertEqual(featres.pick_uid(items, ' khóa toàn bộ ai'), '{u1}')

    def test_pick_by_path_when_name_differs(self):
        items = [{'Name': 'Khóa AI', 'Path': 'cmd.exe /c C:\\cmd\\KhoaVeyonServices.bat -blockai', 'Uid': '{u2}'}]
        self.assertEqual(featres.pick_uid(items, 'Khóa toàn bộ AI', 'cmd.exe /c C:\\cmd\\KhoaVeyonServices.bat -blockai'), '{u2}')

    def test_resolve_uses_uid_and_falls_back_to_name(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        path = 'cmd.exe /c %s -blockai' % cfg['script_path']
        featres._items = lambda c: [{'Name': 'Khóa AI', 'Path': path, 'Uid': '{u3}'}]
        self.assertEqual(featres.resolve(cfg, 'Khóa toàn bộ AI'), '{u3}')
        featres._items = lambda c: None
        self.assertEqual(featres.resolve(cfg, 'Khóa toàn bộ AI'), 'Khóa toàn bộ AI')
        self.assertEqual(featres.resolve(cfg, '{abc}'), '{abc}')


if __name__ == '__main__':
    unittest.main()
