# -*- coding: utf-8 -*-
"""Tiếng báo động đáng tin cậy hơn, và máy giáo viên nhận tín hiệu gửi lại từ máy học sinh."""
import os
import re
import sys
import threading
import time
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from kv import alerts, student as ST  # noqa: E402
from kv.runtime import CFG  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class FakeWinsound(types.ModuleType):
    SND_ALIAS = 1

    def __init__(self, beep_fails=False, sound_fails=False):
        super().__init__('winsound')
        self.beep_fails, self.sound_fails = beep_fails, sound_fails
        self.busy = False
        self.overlap = False
        self.beeps = 0
        self.sounds = 0

    def Beep(self, f, d):
        if self.busy:
            self.overlap = True
            raise RuntimeError('Failed to beep')
        self.busy = True
        try:
            if self.beep_fails:
                raise RuntimeError('Failed to beep')
            time.sleep(0.005)
            self.beeps += 1
        finally:
            self.busy = False

    def PlaySound(self, name, flags):
        if self.sound_fails:
            raise RuntimeError('no sound')
        self.sounds += 1


class BeepTest(unittest.TestCase):
    def _idle(self):
        time.sleep(0.6)   # để luồng phát tiếng của test trước chơi xong, không lẫn sang test sau

    def setUp(self):
        self._idle()
        self.saved = (alerts._IS_WIN, sys.modules.get('winsound'), alerts.log, CFG.get('alert_sound'))
        alerts._IS_WIN = True
        alerts._BEEP_FAILED[0] = False
        CFG['alert_sound'] = True
        self.logs = []
        alerts.log = lambda m, k='': self.logs.append((k, m))

    def tearDown(self):
        self._idle()
        alerts._IS_WIN, ws, alerts.log, CFG['alert_sound'] = self.saved
        if ws is None:
            sys.modules.pop('winsound', None)
        else:
            sys.modules['winsound'] = ws

    def _wait(self, cond, sec=3):
        end = time.time() + sec
        while time.time() < end and not cond():
            time.sleep(0.02)
        return cond()

    def test_simultaneous_requests_never_overlap_and_none_lost(self):
        fw = sys.modules['winsound'] = FakeWinsound()
        ts = [threading.Thread(target=alerts.alert_beep) for _ in range(4)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertTrue(self._wait(lambda: fw.beeps >= 8))      # ít nhất hai hồi (4 tiếng mỗi hồi)
        time.sleep(0.5)
        self.assertFalse(fw.overlap)                             # không bao giờ hai tiếng chồng nhau
        self.assertEqual(fw.beeps % 4, 0)                        # hồi bíp nào cũng đủ 4 tiếng

    def test_falls_back_to_system_sound_when_beep_fails(self):
        fw = sys.modules['winsound'] = FakeWinsound(beep_fails=True)
        alerts.alert_beep()
        self.assertTrue(self._wait(lambda: fw.sounds >= 1))
        self.assertEqual(self.logs, [])

    def test_logs_once_when_nothing_can_play(self):
        sys.modules['winsound'] = FakeWinsound(beep_fails=True, sound_fails=True)
        alerts.alert_beep()
        self.assertTrue(self._wait(lambda: len(self.logs) >= 1))
        alerts.alert_beep()
        time.sleep(0.8)
        self.assertEqual(len(self.logs), 1)                      # báo lỗi một lần, không làm đầy nhật ký
        self.assertIn('Thử tiếng báo', self.logs[0][1])

    def test_sound_switch_and_force(self):
        sys.modules['winsound'] = FakeWinsound()
        CFG['alert_sound'] = False
        self.assertFalse(alerts.alert_beep())
        self.assertTrue(alerts.alert_beep(force=True))

    def test_test_button_api(self):
        sys.modules['winsound'] = FakeWinsound()
        r = alerts.api_alert_test({})
        self.assertTrue(r['ok'])
        CFG['alert_sound'] = False
        self.assertIn('TẮT', alerts.api_alert_test({})['msg'])
        alerts._IS_WIN = False
        self.assertFalse(alerts.api_alert_test({})['ok'])


class CollectTest(unittest.TestCase):
    def test_collect_and_beep_only_counts_this_hosts_alerts(self):
        saved = (alerts.alert_collect_host, alerts.alert_beep, list(alerts.ALERTS))
        beeps = []
        alerts.alert_beep = lambda force=False: beeps.append(1)
        alerts.BEEP_LAST.clear()

        def fake_collect(cfg, host):
            for h in ('A', 'B'):   # luồng khác vừa nhận vi phạm của máy B trong lúc máy A đang được lấy
                alerts.ALERT_SEQ[0] += 1
                alerts.ALERTS.append({'id': alerts.ALERT_SEQ[0], 'host': h, 'type': 'site', 'name': 'x.com'})
            return True, 'ok', 2
        alerts.alert_collect_host = fake_collect
        try:
            alerts.collect_and_beep({'alert_group_sec': '60'}, 'A')
        finally:
            alerts.alert_collect_host, alerts.alert_beep = saved[0], saved[1]
            alerts.ALERTS[:] = saved[2]
        self.assertEqual(beeps, [1])
        self.assertEqual(sorted(k[0] for k in alerts.BEEP_LAST), ['A'])   # máy B không bị đánh dấu thay


class RetrySignalTest(unittest.TestCase):
    def test_retry_signal_triggers_collect(self):
        got = []
        saved = (ST.host_for_ip, alerts.collect_and_beep, list(CFG.get('watch_hosts') or []))
        ST.host_for_ip = lambda ip: 'PC05'
        alerts.collect_and_beep = lambda cfg, host: got.append(host)
        CFG['watch_hosts'] = ['PC05']
        try:
            ST.handle_events('10.0.0.5', {'events': [{'t': 'viol', 'type': 'retry', 'name': ''}]})
            end = time.time() + 2
            while not got and time.time() < end:
                time.sleep(0.02)
        finally:
            ST.host_for_ip, alerts.collect_and_beep, CFG['watch_hosts'] = saved
        self.assertEqual(got, ['PC05'])


class StudentScriptTest(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, 'scripts', 'KhoaVeyonWatch.ps1'), encoding='utf-8') as f:
            self.s = f.read()

    def test_script_resends_until_teacher_takes_the_file(self):
        self.assertIn("Push-Signal 'retry'", self.s)
        self.assertIn('Resend-Unsent', self.s)
        self.assertIn('$script:unsent.Add', self.s)

    def test_second_shot_after_two_seconds_and_faster_loop(self):
        self.assertIn('[Math]::Min(2, $RepeatSec)', self.s)
        self.assertIn('Start-Sleep -Milliseconds 300', self.s)

    def test_braces_balanced(self):
        code = re.sub(r"'[^'\n]*'|\"[^\"\n]*\"|#[^\n]*", '', self.s)
        self.assertEqual(code.count('{'), code.count('}'))
        self.assertEqual(code.count('('), code.count(')'))


if __name__ == '__main__':
    unittest.main()
