# -*- coding: utf-8 -*-
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kv import network


class PcName(unittest.TestCase):
    def test_valid(self):
        for ok in ('PC07', 'HS-04', 'PC4', '10A'):
            self.assertTrue(network.valid_pcname(ok), ok)
        for bad in ('192', '192-168-2-6', '192.168.2.6', '', None):
            self.assertFalse(network.valid_pcname(bad), bad)

    def test_dns_returning_ip_is_not_a_name(self):
        net_gha = network.socket.gethostbyaddr
        network.socket.gethostbyaddr = lambda ip: ('192.168.2.6', [], [ip])
        nb = network._nbstat_name
        network._nbstat_name = lambda ip, timeout=1.5: ''
        try:
            self.assertEqual(network.pc_name_lookup('192.168.2.6', 1), '')
        finally:
            network.socket.gethostbyaddr = net_gha
            network._nbstat_name = nb


if __name__ == '__main__':
    unittest.main()
