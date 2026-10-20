# -*- coding: utf-8 -*-
"""Mục Veyon bị hỏng tên (đọc UTF-8 bằng bảng mã Windows rồi ghi lại nhiều lần) phải được sửa và bỏ trùng."""
import copy, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kv import setup
from kv.config import DEFAULT_CONFIG


def garble(s):
    return s.encode('utf-8').decode('cp1252', errors='replace')


class RepairPrograms(unittest.TestCase):
    def setUp(self):
        self.cfg = copy.deepcopy(DEFAULT_CONFIG)
        self.want = setup.desired_programs(self.cfg)

    def _layers(self, n):
        items, uid = [], 0
        cur = [{'Name': nm, 'Path': p} for nm, p in self.want[:20]]
        for _ in range(n):
            for x in cur:
                uid += 1
                x['Uid'] = '{u%d}' % uid
            items = [dict(x, Name=garble(x['Name'])) for x in items] + [dict(x) for x in cur]
        return items

    def test_demojibake_roundtrip(self):
        self.assertEqual(setup._demojibake(garble('Khóa toàn bộ'))[0], 'Khóa toàn bộ')
        self.assertEqual(setup._demojibake(garble(garble('Mở khóa')))[0], 'Mở khóa')
        self.assertFalse(setup._demojibake('Khóa toàn bộ AI')[1])

    def test_repair_dedups_and_renames(self):
        items = self._layers(5)
        self.assertGreater(len(items), 20)
        fixed, changed = setup._repair_programs(items, self.want)
        self.assertTrue(changed)
        paths = [setup._path_key(x['Path']) for x in fixed]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual({x['Name'] for x in fixed}, {n for n, _p in self.want[:20]})
        self.assertEqual(setup._programs_missing(fixed, self.want), [n for n, _p in self.want[20:]])

    def test_clean_items_and_custom_untouched(self):
        items = [{'Name': n, 'Path': p, 'Uid': '{x%d}' % i} for i, (n, p) in enumerate(self.want)]
        items.append({'Name': 'Mở Calc', 'Path': 'calc.exe', 'Uid': '{custom}'})
        fixed, changed = setup._repair_programs(copy.deepcopy(items), self.want)
        self.assertFalse(changed)
        self.assertEqual(fixed, items)

    def test_clean_item_wins_over_garbled_duplicate(self):
        n, p = self.want[0]
        items = [{'Name': garble(n), 'Path': p, 'Uid': '{old}'}, {'Name': n, 'Path': p, 'Uid': '{new}'}]
        fixed, changed = setup._repair_programs(items, self.want)
        self.assertTrue(changed)
        self.assertEqual([x['Uid'] for x in fixed], ['{new}'])


if __name__ == '__main__':
    unittest.main()
