# -*- coding: utf-8 -*-
import json, os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kv import student as ST, usage as US
from kv.runtime import ApiError, CFG


class Stu(unittest.TestCase):
    def setUp(self):
        self.saved = (ST.host_for_ip, ST.who, ST.start_job, ST.rfs_write, ST.rfs_read, ST._walk_remote, ST.rfs_remove, ST.submissions_root, list(CFG.get('hosts') or []))
        ST.HANDS.clear(); ST.SUBMITS.clear(); ST.EVENTS.clear()
        ST.host_for_ip = lambda ip: 'PC05'
        ST.who = lambda h: ('Nguyễn An', '10A1', 5)
        self.jobs = []
        ST.start_job = lambda fn, *a: self.jobs.append((fn, a))
        self.tmp = tempfile.mkdtemp(); ST.submissions_root = lambda: self.tmp

    def tearDown(self):
        (ST.host_for_ip, ST.who, ST.start_job, ST.rfs_write, ST.rfs_read, ST._walk_remote, ST.rfs_remove, ST.submissions_root, CFG['hosts']) = self.saved

    def test_hand_up_down_and_single_toast(self):
        ST.handle_events('10.0.0.5', {'events': [{'t': 'hand', 'on': True}, {'t': 'hand', 'on': True}]})
        o = ST.student_overview(0)
        self.assertEqual([(h['host'], h['name'], h['no']) for h in o['hands']], [('PC05', 'Nguyễn An', 5)])
        self.assertEqual(len(o['events']), 1)               # giơ tay hai lần chỉ báo một lần
        ST.handle_events('10.0.0.5', {'events': [{'t': 'hand', 'on': False}]})
        self.assertEqual(ST.student_overview(0)['hands'], [])
        self.assertEqual(ST.student_overview(o['last'])['events'], [])

    def test_junk_events_ignored_and_bad_submit_id_rejected(self):
        ST.handle_events('10.0.0.5', {'events': ['x', 5, {'t': 'submit', 'id': '../../evil'}, {'t': 'nope'}]})
        self.assertEqual(ST.SUBMITS, []); self.assertEqual(self.jobs, [])

    def test_submit_creates_record_and_pull_saves_files_safely(self):
        ST.handle_events('10.0.0.5', {'events': [{'t': 'submit', 'id': '20261021-101500', 'files': 2, 'bytes': 30}]})
        self.assertEqual(len(self.jobs), 1)
        rec = ST.SUBMITS[0]; self.assertEqual(rec['status'], 'pulling')
        files = [('bai.docx', 10, 0), ('sub\\hinh.png', 20, 0), ('..\\..\\evil.txt', 5, 0)]
        ST._walk_remote = lambda hh, root, rel='': files
        ST.rfs_read = lambda hh, p: b'x' * 7
        removed = []; ST.rfs_remove = lambda hh, p: removed.append(p)
        ST.pull_submission(rec)
        self.assertEqual(rec['status'], 'ok')
        got = []
        for dp, _d, fs in os.walk(self.tmp):
            got += [os.path.relpath(os.path.join(dp, f), self.tmp) for f in fs]
        self.assertEqual(len(got), 3)
        self.assertTrue(all(not p.startswith('..') for p in got))          # không thoát khỏi thư mục bài nộp
        self.assertTrue(any('10A1' in p and 'Nguy' in p for p in got))
        self.assertEqual(removed, ['C:\\ProgramData\\KhoaVeyon\\submit\\20261021-101500'])

    def test_send_validation_and_write(self):
        CFG['hosts'] = ['PC01', 'PC02']
        with self.assertRaises(ApiError): ST.api_student_send({'kind': 'x', 'hosts': ['PC01']})
        with self.assertRaises(ApiError): ST.api_student_send({'kind': 'msg', 'hosts': ['PC01'], 'text': '  '})
        self.assertEqual(ST.api_student_send({'kind': 'collect', 'hosts': ['PC01']})['count'], 1)
        written = []
        ST.rfs_write = lambda h, p, d: written.append((h, p, json.loads(d.decode('utf-8'))))
        fn, args = self.jobs[-1]
        ST.pool_run = lambda f, hosts, title='': [f(h) for h in hosts]
        fn(*args)
        self.assertEqual(written[0][0], 'PC01'); self.assertTrue(written[0][1].startswith('C:\\ProgramData\\KhoaVeyon\\inbox\\'))
        self.assertEqual(written[0][2]['type'], 'collect')

    def test_hand_clear_all(self):
        ST.HANDS['PC05'] = {'ts': 1, 'name': 'a', 'cls': 'x', 'no': 1}
        o = ST.api_hand_clear({})
        self.assertEqual(o['hands'], []); self.assertEqual(len(self.jobs), 1)


class Usage(unittest.TestCase):
    CSV = ('Date,Time,PCName,User,Window,Process,Event\n'
           '"2026-10-21","09:00:00","PC1","hs","Word - bai.docx","winword","change"\n'
           '"2026-10-21","09:10:00","PC1","hs","YouTube - Chrome","chrome","change"\n'
           '"2026-10-21","09:10:30","PC1","hs","","","action: lockapp"\n'
           '"2026-10-21","09:12:00","PC1","hs","Word - bai.docx","winword","change"\n')

    def test_durations_cap_and_window(self):
        t = lambda s: time.mktime(time.strptime('2026-10-21 ' + s, '%Y-%m-%d %H:%M:%S'))
        procs, titles = US.parse_activity(self.CSV, t('09:00:00'), t('09:20:00'))
        self.assertEqual(procs['winword'], 180 + 180)        # mỗi dòng tối đa 180 giây
        self.assertEqual(procs['chrome'], 120)
        p2, _ = US.parse_activity(self.CSV, t('09:11:00'), t('09:20:00'))
        self.assertEqual(p2, {'chrome': 60, 'winword': 180})

    def test_ignores_garbage(self):
        self.assertEqual(US.parse_activity('abc\n,,\n', 0, 10 ** 10), ({}, {}))


if __name__ == '__main__':
    unittest.main()
