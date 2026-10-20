# -*- coding: utf-8 -*-
import copy, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kv import remote
from kv.config import DEFAULT_CONFIG


class ActionVia(unittest.TestCase):
    def setUp(self):
        self.cfg = copy.deepcopy(DEFAULT_CONFIG)
        self.calls = []
        self._o = (remote.agent_call, remote.agent_online, remote.transport_mode, remote.run_shell)
        remote.agent_online = lambda h: True
        remote.transport_mode = lambda: 'auto'
        remote.run_shell = lambda c, timeout=60: (0, 'veyon:' + c)

    def tearDown(self):
        remote.agent_call, remote.agent_online, remote.transport_mode, remote.run_shell = self._o

    def test_agent_runs_script_switch(self):
        def fake(host, job, timeout=60):
            self.calls.append((host, job)); return {'ok': True, 'rc': 0}
        remote.agent_call = fake
        rc, out = remote.run_action(self.cfg, '192.168.2.5', 'blockai')
        self.assertEqual(rc, 0)
        self.assertIn('-blockai', self.calls[0][1]['cmd'])
        self.assertEqual(self.calls[0][1]['session'], 'user')   # chạy trong phiên học sinh như Veyon Run program

    def test_service_mode_falls_back_to_system_when_nobody_logged_in(self):
        sess = []
        def fake(host, job, timeout=60):
            sess.append(job['session'])
            if job['session'] == 'user':
                raise remote.AgentError('Chưa có ai đăng nhập Windows trên máy này')
            return {'ok': True, 'rc': 0}
        remote.agent_call = fake
        self.assertEqual(remote.run_action(self.cfg, 'h', 'blockai')[0], 0)
        self.assertEqual(sess, ['user', 'system'])
        sess.clear()
        rc, out = remote.run_action(self.cfg, 'h', 'killapp')   # lệnh trong phiên học sinh: không có ai đăng nhập thì báo lỗi
        self.assertNotEqual(rc, 0); self.assertEqual(sess, ['user'])

    def test_auto_falls_back_to_veyon_when_agent_errors(self):
        def boom(host, job, timeout=60):
            raise remote.AgentError('khong ket noi')
        remote.agent_call = boom
        rc, out = remote.run_action(self.cfg, '192.168.2.5', 'blockai')
        self.assertEqual(rc, 0); self.assertTrue(out.startswith('veyon:'))

    def test_agent_only_reports_error(self):
        self.cfg['action_via'] = 'agent'
        def boom(host, job, timeout=60):
            raise remote.AgentError('khong ket noi')
        remote.agent_call = boom
        rc, out = remote.run_action(self.cfg, '192.168.2.5', 'blockai')
        self.assertNotEqual(rc, 0)

    def test_veyon_only_never_uses_agent(self):
        self.cfg['action_via'] = 'veyon'
        remote.agent_call = lambda *a, **k: self.fail('khong duoc goi agent')
        self.assertFalse(remote.action_via_agent(self.cfg, '192.168.2.5'))


if __name__ == '__main__':
    unittest.main()
