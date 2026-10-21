# -*- coding: utf-8 -*-
import os, sys, unittest, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kv.health import health_of
from kv import agent


def ids(r):
    lvl, probs = health_of(r)
    return lvl, [p.get('id') for p in probs]


class State(unittest.TestCase):
    base = {'online': True, 'veyon': True, 'smb': False, 'agent': False, 'svc': '?', 'up_for': 500}

    def test_no_agent(self):
        self.assertEqual(ids(self.base), ('red', ['noagent']))

    def test_just_booted_gets_grace(self):
        self.assertNotIn('noagent', ids(dict(self.base, up_for=20))[1])

    def test_bad_time_is_clock_problem(self):
        lvl, i = ids(dict(self.base, reject={'reason': 'bad time', 'skew': -3600 * 24}))
        self.assertEqual((lvl, i), ('red', ['clock']))

    def test_bad_signature(self):
        self.assertEqual(ids(dict(self.base, reject={'reason': 'bad signature'})), ('red', ['badkey']))

    def test_skewed_but_connected_is_yellow_with_fix(self):
        lvl, probs = health_of(dict(self.base, smb=True, agent=True, skew=400))
        self.assertEqual(lvl, 'yellow'); self.assertEqual(probs[0]['fix'], 'time')

    def test_good(self):
        self.assertEqual(health_of(dict(self.base, smb=True, agent=True, skew=3))[0], 'green')

    def test_reject_info_expires(self):
        agent.agent_reject('203.0.113.9', 'bad time', skew=5000)
        self.assertEqual(agent.agent_reject_info('203.0.113.9')['reason'], 'bad time')
        agent.REJECTED['203.0.113.9']['at'] -= 400
        self.assertIsNone(agent.agent_reject_info('203.0.113.9'))


if __name__ == '__main__':
    unittest.main()
