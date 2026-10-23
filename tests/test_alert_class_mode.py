# -*- coding: utf-8 -*-
"""Chế độ chọn lớp cho vi phạm: theo lớp hiện tại hoặc thủ công."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from kv import alerts, reports  # noqa: E402
from kv.api_core import api_settings  # noqa: E402
from kv.school import SCHOOL, SCHOOL_LOCK  # noqa: E402
from kv.runtime import ApiError  # noqa: E402


class AlertClassModeTest(unittest.TestCase):
    def setUp(self):
        self._orig = alerts.school_class_at
        alerts.school_class_at = lambda ts: '3A4'   # lớp hiện tại theo thời khóa biểu

    def tearDown(self):
        alerts.school_class_at = self._orig

    def test_current_follows_timetable(self):
        self.assertEqual(alerts.alert_class_at({'alert_cls_mode': 'current', 'alert_cls_manual': '5A4'}, 0), '3A4')
        self.assertEqual(alerts.alert_class_at({}, 0), '3A4')

    def test_manual_uses_chosen_class(self):
        self.assertEqual(alerts.alert_class_at({'alert_cls_mode': 'manual', 'alert_cls_manual': ' 5a4 '}, 0), '5A4')

    def test_manual_without_class_falls_back(self):
        self.assertEqual(alerts.alert_class_at({'alert_cls_mode': 'manual', 'alert_cls_manual': ''}, 0), '3A4')

    def test_report_keeps_classes_apart(self):
        ev = [{'host': 'M5', 'type': 'site', 'name': 'x.com', 'date': 'd', 'time': 't', 'ts': 10 * i, 'student': s, 'cls': c, 'seat': 5}
              for i, (s, c) in enumerate([('An', '3A4'), ('An', '3A4'), ('Binh', '5A4'), ('Binh', '5A4')])]
        eps = reports.report_episodes(ev, 60)
        self.assertEqual([(g['cls'], g['student'], g['shots']) for g in eps], [('3A4', 'An', 2), ('5A4', 'Binh', 2)])

    def test_settings_validation(self):
        with self.assertRaises(ApiError):
            api_settings({'alert_cls_mode': 'abc'})
        with SCHOOL_LOCK:
            old = dict(SCHOOL.get('classes') or {})
            SCHOOL['classes'] = {'5A4': ['Binh']}
        try:
            with self.assertRaises(ApiError):
                api_settings({'alert_cls_manual': '9Z9'})
        finally:
            with SCHOOL_LOCK:
                SCHOOL['classes'] = old


if __name__ == '__main__':
    unittest.main()
