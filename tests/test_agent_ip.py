# -*- coding: utf-8 -*-
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kv import agent, network
from kv.runtime import CFG


class AgentIp(unittest.TestCase):
    def test_prefers_ip_in_students_subnet(self):
        old = (list(CFG.get('hosts') or []), CFG.get('agent_host'), network.local_ips)
        try:
            CFG['hosts'] = ['192.168.2.5', '192.168.2.6', 'PC9']; CFG['agent_host'] = ''
            network.local_ips = lambda: {'10.0.0.8', '192.168.2.100', '172.20.0.1'}
            self.assertEqual(agent.lan_ip(), '192.168.2.100')
        finally:
            CFG['hosts'], CFG['agent_host'] = old[0], old[1]; network.local_ips = old[2]


if __name__ == '__main__':
    unittest.main()
