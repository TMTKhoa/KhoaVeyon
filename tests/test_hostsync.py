# -*- coding: utf-8 -*-
"""Máy đổi IP do DHCP: IP cũ được nối sang IP mới theo MAC (hoặc tên PC), không để IP cũ."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from kv.hostsync import reconcile_hosts  # noqa: E402

M1, M2, M3 = 'AA:BB:CC:00:00:01', 'AA:BB:CC:00:00:02', 'AA:BB:CC:00:00:03'


class Reconcile(unittest.TestCase):
    def test_move_by_mac_keeps_name_and_position(self):
        hosts, macs, hn, auto, moves = reconcile_hosts(
            ['10.0.0.5', '10.0.0.6'], ['10.0.0.20', '10.0.0.6'], {}, {'10.0.0.20': M1, '10.0.0.6': M2},
            {'10.0.0.5': M1, '10.0.0.6': M2}, {'10.0.0.5': 'May 1'}, {})
        self.assertEqual(hosts, ['10.0.0.20', '10.0.0.6'])
        self.assertEqual(moves, [('10.0.0.5', '10.0.0.20')])
        self.assertEqual(hn, {'10.0.0.20': 'May 1'})
        self.assertNotIn('10.0.0.5', macs)
        self.assertEqual(macs['10.0.0.20'], M1)

    def test_offline_machine_without_match_is_kept(self):
        hosts, *_rest, moves = reconcile_hosts(['10.0.0.5', '10.0.0.6'], ['10.0.0.6'], {}, {'10.0.0.6': M2},
                                               {'10.0.0.5': M1, '10.0.0.6': M2}, {}, {})
        self.assertEqual(hosts, ['10.0.0.5', '10.0.0.6'])
        self.assertEqual(moves, [])

    def test_new_ip_already_listed_drops_old(self):
        hosts, macs, hn, auto, moves = reconcile_hosts(
            ['10.0.0.5', '10.0.0.20'], ['10.0.0.20'], {}, {'10.0.0.20': M1}, {'10.0.0.5': M1}, {'10.0.0.5': 'May 1'}, {})
        self.assertEqual(hosts, ['10.0.0.20'])
        self.assertEqual(hn, {'10.0.0.20': 'May 1'})

    def test_swap_ips_names_follow_the_machine(self):
        hosts, macs, hn, auto, moves = reconcile_hosts(
            ['10.0.0.5', '10.0.0.6'], ['10.0.0.5', '10.0.0.6'], {}, {'10.0.0.5': M2, '10.0.0.6': M1},
            {'10.0.0.5': M1, '10.0.0.6': M2}, {'10.0.0.5': 'May A', '10.0.0.6': 'May B'}, {})
        self.assertEqual(hosts, ['10.0.0.5', '10.0.0.6'])
        self.assertEqual(hn, {'10.0.0.5': 'May B', '10.0.0.6': 'May A'})

    def test_ip_reused_by_other_machine_drops_old_label(self):
        hosts, macs, hn, auto, moves = reconcile_hosts(
            ['10.0.0.5'], ['10.0.0.5'], {}, {'10.0.0.5': M3}, {'10.0.0.5': M1}, {'10.0.0.5': 'May 1'}, {})
        self.assertNotIn('10.0.0.5', hn)
        self.assertEqual(macs['10.0.0.5'], M3)

    def test_match_by_pc_name_when_no_mac_known(self):
        hosts, macs, hn, auto, moves = reconcile_hosts(
            ['10.0.0.5'], ['10.0.0.30'], {'10.0.0.30': 'PC-LAB-05'}, {'10.0.0.30': M1}, {}, {}, {'10.0.0.5': 'PC-LAB-05'})
        self.assertEqual(hosts, ['10.0.0.30'])
        self.assertEqual(moves, [('10.0.0.5', '10.0.0.30')])

    def test_two_same_names_not_guessed(self):
        hosts, *_r, moves = reconcile_hosts(['10.0.0.5'], ['10.0.0.30', '10.0.0.31'],
                                            {'10.0.0.30': 'PC', '10.0.0.31': 'PC'}, {}, {}, {}, {'10.0.0.5': 'PC'})
        self.assertEqual(hosts, ['10.0.0.5'])
        self.assertEqual(moves, [])

    def test_hostname_entries_untouched(self):
        hosts, *_r, moves = reconcile_hosts(['LAB-01'], ['10.0.0.30'], {}, {'10.0.0.30': M1}, {'LAB-01': M1}, {}, {})
        self.assertEqual(hosts, ['LAB-01'])


class ScanApi(unittest.TestCase):
    def test_scan_and_reconcile_end_to_end(self):
        from kv import hostsync
        from kv.runtime import CFG, CFG_LOCK
        keys = ('hosts', 'macs', 'host_names', 'host_auto_names')
        saved = {k: CFG.get(k) for k in keys}
        o = (hostsync.scan_veyon_hosts, hostsync.arp_mac, hostsync.save_config)
        try:
            hostsync.scan_veyon_hosts = lambda: (['10.0.0.20', '10.0.0.7'], {'10.0.0.20': 'PC1'}, '')
            hostsync.arp_mac = lambda ip: {'10.0.0.20': M1, '10.0.0.7': M3}[ip]
            hostsync.save_config = lambda c: None
            with CFG_LOCK:
                CFG['hosts'] = ['10.0.0.5']; CFG['macs'] = {'10.0.0.5': M1}
                CFG['host_names'] = {'10.0.0.5': 'May 1'}; CFG['host_auto_names'] = {}
            r = hostsync.scan_and_reconcile()
            self.assertEqual(r['hosts'], ['10.0.0.20', '10.0.0.7'])
            self.assertEqual(r['moves'], [('10.0.0.5', '10.0.0.20')])
            self.assertEqual(r['added'], 1)
            self.assertEqual(r['manual']['10.0.0.20'], 'May 1')
        finally:
            hostsync.scan_veyon_hosts, hostsync.arp_mac, hostsync.save_config = o
            with CFG_LOCK:
                for k, v in saved.items():
                    CFG[k] = v


if __name__ == '__main__':
    unittest.main()


class StatusSortUi(unittest.TestCase):
    def test_sort_options_present(self):
        s = open(os.path.join(ROOT, 'web', 'js', '14-status.js'), encoding='utf-8').read()
        for k in ('statusOrder()', 'data-xa-sort', "'name'", "'ip'", "'list'"):
            self.assertIn(k, s)
