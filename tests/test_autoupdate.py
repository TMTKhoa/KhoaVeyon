# -*- coding: utf-8 -*-
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kv import autoupdate as au
from kv.runtime import CFG


class AU(unittest.TestCase):
    def setUp(self):
        self.o = (au.agent_online, au.health_probe, au.job_fix_service, au.exam_snapshot, list(CFG.get('hosts') or []), CFG.get('auto_update_students'))
        self.pushed = []
        au._LAST_CHECK.clear(); au._LAST_TRY.clear()
        CFG['hosts'] = ['10.0.0.%d' % i for i in range(1, 8)]; CFG['auto_update_students'] = True
        au.agent_online = lambda h: h != '10.0.0.2'
        au.health_probe = lambda h: {'svc': 'ok' if h == '10.0.0.3' else 'old'}
        au.job_fix_service = lambda hs: self.pushed.append(list(hs))
        au.exam_snapshot = lambda: {'active': False, 'steps': {}}
        self.o_sync = au.sync_extra_files; au.sync_extra_files = lambda h: []

    def tearDown(self):
        au.agent_online, au.health_probe, au.job_fix_service, au.exam_snapshot = self.o[:4]
        CFG['hosts'] = self.o[4]; CFG['auto_update_students'] = self.o[5]; au.sync_extra_files = self.o_sync

    def test_only_old_online_hosts_limited_per_round(self):
        r = au.autoupdate_round(10**9)
        self.assertEqual(r, ['10.0.0.1', '10.0.0.4', '10.0.0.5', '10.0.0.6'])
        self.assertEqual(self.pushed, [r])

    def test_no_retry_within_window_then_retry(self):
        au.autoupdate_round(10**9); self.pushed.clear()
        self.assertNotIn('10.0.0.1', au.autoupdate_round(10**9 + 700))
        self.assertIn('10.0.0.1', au.autoupdate_round(10**9 + au.RETRY_AFTER + 1))

    def test_off_and_exam_do_nothing(self):
        CFG['auto_update_students'] = False
        self.assertEqual(au.autoupdate_round(10**9), [])
        CFG['auto_update_students'] = True; au.exam_snapshot = lambda: {'active': True, 'steps': {}}
        self.assertEqual(au.autoupdate_round(10**9), []); self.assertEqual(self.pushed, [])


if __name__ == '__main__':
    unittest.main()
