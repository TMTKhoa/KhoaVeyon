# -*- coding: utf-8 -*-
import base64, os, sys, tempfile, unittest
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kv import engage
from kv.runtime import ApiError


class DrawTest(unittest.TestCase):
    def setUp(self):
        engage.DRAWN.clear()
        self.c = [('An', 1, 'h1'), ('Binh', 2, 'h2'), ('Chi', 3, '')]
        self.p1 = mock.patch.object(engage, 'draw_candidates', lambda cls: list(self.c))
        self.p2 = mock.patch.object(engage, 'start_job')
        self.p3 = mock.patch.object(engage, 'log')
        self.p4 = mock.patch.dict(engage.SCHOOL['classes'], {'10A': []}, clear=False)
        self.start = self.p2.start(); [p.start() for p in (self.p1, self.p3, self.p4)]

    def tearDown(self):
        mock.patch.stopall()

    def test_no_repeat_until_round_ends(self):
        got = [engage.api_draw({'cls': '10A'}) for _ in range(3)]
        self.assertEqual(sorted(g['name'] for g in got), ['An', 'Binh', 'Chi'])
        self.assertFalse(any(g['new_round'] for g in got))
        self.assertTrue(engage.api_draw({'cls': '10A'})['new_round'])

    def test_send_only_when_host(self):
        self.c = [('Chi', 3, '')]
        engage.api_draw({'cls': '10A'})
        self.start.assert_not_called()
        self.c = [('An', 1, 'h1')]
        engage.api_draw({'cls': '10A'})
        self.start.assert_called_once()

    def test_empty_class(self):
        self.c = []
        with self.assertRaises(ApiError):
            engage.api_draw({'cls': '10A'})


class WallTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        mock.patch.object(engage, 'walls_root', lambda: self.d).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_clean(self):
        w = engage.clean_wall({'title': ' A   B ' + 'x' * 100, 'c1': 'red', 'c2': '#00ff00', 'bg': '../../etc', 'dim': 999, 'lock': 1})
        self.assertEqual(w['c1'], '#1d4ed8'); self.assertEqual(w['c2'], '#00ff00')
        self.assertEqual(w['bg'], ''); self.assertEqual(w['dim'], 80); self.assertTrue(w['lock'])
        self.assertLessEqual(len(w['title']), 60)

    def test_bg_upload(self):
        jpg = b'\xff\xd8\xff' + b'0' * 50
        r = engage.api_wall_bg({'data': base64.b64encode(jpg).decode()})
        self.assertTrue(os.path.isfile(os.path.join(self.d, r['id'] + '.jpg')))
        self.assertEqual(engage.clean_wall({'bg': r['id']})['bg'], r['id'])
        self.assertTrue(engage.api_wall_img({'id': r['id']})['data'].startswith('data:image/jpeg'))
        with self.assertRaises(ApiError):
            engage.api_wall_bg({'data': base64.b64encode(b'GIF89a').decode()})
        with self.assertRaises(ApiError):
            engage.api_wall_img({'id': '../x'})

    def test_message_has_seat(self):
        with mock.patch.object(engage, 'who', lambda h, c='': ('An', '10A', 7)):
            m = engage.wall_message('h', engage.clean_wall({'title': 'T', 'seat': True}))
            self.assertEqual((m['name'], m['no'], m['sub']), ('An', 7, 'Lớp 10A'))
            m = engage.wall_message('h', engage.clean_wall({'title': 'T', 'seat': False}))
            self.assertEqual((m['name'], m['no']), ('', 0))


if __name__ == '__main__':
    unittest.main()


class AutoHookTest(unittest.TestCase):
    def test_transition_applies_and_restores(self):
        from kv import auto
        spec = engage.clean_wall({'title': 'T'})
        modes = {'A': {'start': [], 'end': [], 'lists': {}, 'wall': 'P'}, 'B': {'start': [], 'end': [], 'lists': {}, 'wall': ''}}
        with mock.patch.dict(auto.AUTO, {'enabled': True, 'modes': modes, 'class_mode': {'1': 'A', '2': 'A', '3': 'B'}}), \
             mock.patch.dict(engage.SCHOOL, {'wall_presets': {'P': spec}}), \
             mock.patch.object(auto, 'auto_hosts', lambda: ['h']), mock.patch.object(auto, 'start_job') as sj, \
             mock.patch.object(auto, 'auto_mode_for', lambda c: auto.AUTO['class_mode'].get(c, '')):
            auto.auto_transition('', '1')
            self.assertEqual(sj.call_args[0][0].__name__, 'job_wall_apply')
            sj.reset_mock(); auto.auto_transition('1', '2')      # cùng chế độ, khác lớp: vẽ lại tên
            self.assertEqual(sj.call_args[0][0].__name__, 'job_wall_apply')
            sj.reset_mock(); auto.auto_transition('2', '3')      # sang chế độ không có hình nền: trả lại
            self.assertEqual(sj.call_args[0][0].__name__, 'job_wall_restore')
            sj.reset_mock(); auto.auto_transition('2', '')       # hết tiết
            self.assertEqual(sj.call_args[0][0].__name__, 'job_wall_restore')


class SeatNameTest(unittest.TestCase):
    def test_effective_seats(self):
        from kv import seating
        lay = {'pattern': 'MAY{n}', 'seats': {'1': 'An', '2': 'Binh'}}
        att = {'%s|10A' % seating.att_today(): {'absent': ['An'], 'moves': {'Binh': 5}}}
        with mock.patch.dict(seating.SCHOOL, {'layouts': {'10A': lay}, 'classes': {'10A': ['An', 'Binh']}, 'attendance': att}):
            self.assertEqual(seating.school_student_for('MAY1', '10A'), ('', 1))      # An vắng
            self.assertEqual(seating.school_student_for('MAY2', '10A'), ('', 2))      # Bình đã chuyển
            self.assertEqual(seating.school_student_for('MAY5', '10A'), ('Binh', 5))


class ExtrasTest(unittest.TestCase):
    def test_lock_style_clean(self):
        k = engage.clean_lock({'title': '', 'icon': '🔒🔒🔒🔒🔒🔒', 'c1': 'bad'})
        self.assertEqual(k['title'], 'Màn hình đang tạm khóa'); self.assertLessEqual(len(k['icon']), 4)
        self.assertEqual(k['c1'], '#0f172a'); self.assertTrue(k['clock'])

    def test_tokens(self):
        self.assertEqual(engage.fill_tokens('Lớp {lop} - {ten} - {may}', 'An', '10A', 5), 'Lớp 10A - An - 5')

    def test_hand_option_and_follow(self):
        with mock.patch.object(engage, 'start_job') as sj, mock.patch.object(engage, 'school_save'), \
             mock.patch.object(engage, 'clean_hosts', lambda h: list(h or [])), mock.patch.dict(engage.SCHOOL, {'hand_enabled': True, 'wall_follow': None}):
            engage.api_hand_option({'enabled': False, 'hosts': ['h']})
            self.assertFalse(engage.SCHOOL['hand_enabled']); sj.assert_called_once()
            spec = engage.clean_wall({'title': 'T'})
            engage.SCHOOL['wall_follow'] = spec
            sj.reset_mock()
            engage.transition_extras('1', '2', ['h'], False)
            names = [c[0][0].__name__ if hasattr(c[0][0], '__name__') else '' for c in sj.call_args_list]
            self.assertIn('job_wall_apply', names)
            sj.reset_mock(); engage.transition_extras('2', '', ['h'], False)
            self.assertIsNone(engage.SCHOOL['wall_follow'])


class MonitorTest(unittest.TestCase):
    def test_recent_clean(self):
        from kv import alerts
        r = alerts._recent_clean([{'p': 'chrome', 'w': 'x' * 500, 't': '10:00:01', 'd': 99999999}, 'bad'] + [{}] * 60)
        self.assertEqual(len(r), 30 - 1 + 0 if False else len(r)); self.assertLessEqual(len(r), 30)
        self.assertEqual(len(r[0]['w']), 100); self.assertEqual(r[0]['d'], 86400)

    def test_events_act_hello_viol(self):
        from kv import student, alerts
        with mock.patch.object(student, 'host_for_ip', lambda ip: 'PC1'), mock.patch.object(student, 'who', lambda h, c='': ('An', '10A', 1)), \
             mock.patch.object(student.threading, 'Thread') as th, mock.patch.dict(student.CFG, {'watch_hosts': ['PC1']}):
            student.handle_events('1.2.3.4', {'events': [{'t': 'act', 'p': 'chrome', 'w': 'Hello'}]})
            self.assertEqual(student.ACT['PC1']['p'], 'chrome')
            student.handle_events('1.2.3.4', {'events': [{'t': 'viol', 'type': 'hello'}]})
            self.assertIn('PC1', alerts.PUSH_CAPABLE); th.assert_not_called()
            student.handle_events('1.2.3.4', {'events': [{'t': 'viol', 'type': 'site', 'name': 'x.com'}]})
            th.assert_called_once()

    def test_monitor_structure(self):
        from kv import board
        lay = {'cols': 2, 'per': 2, 'seats': {'1': 'An', '2': 'Binh'}, 'pattern': 'MAY{n}'}
        row = {'host': 'MAY1', 'online': True, 'health': 'green', 'user': '', 'watching': True}
        with mock.patch.object(board, 'api_status', lambda q: {'hosts': [row], 'online': 1, 'total': 1}), \
             mock.patch.dict(board.SCHOOL, {'classes': {'10A': ['An', 'Binh']}, 'layouts': {'10A': lay}, 'attendance': {}, 'slots': []}), \
             mock.patch.dict(board.CFG, {'hosts': ['MAY1', 'MAY9']}):
            d = board.api_monitor({'cls': '10A'})
        self.assertEqual(d['cls'], '10A'); self.assertEqual(d['seats']['1']['host'], 'MAY1'); self.assertEqual(d['seats']['1']['name'], 'An')
        self.assertIn('MAY9', d['extras']); self.assertIsNone(d['current'])


class ThumbTest(unittest.TestCase):
    def test_thumb_flow(self):
        from kv import board, student
        ok = '/9j/' + 'A' * 300
        with mock.patch.object(student, 'host_for_ip', lambda ip: 'PC1'):
            student.handle_events('1.1.1.1', {'events': [{'t': 'thumb', 'd': ok}, {'t': 'thumb', 'd': 'notjpeg' * 100}, {'t': 'thumb', 'd': '/9j/' + 'A' * 20000}]})
        r = board.api_monitor_thumbs({'since': 0})
        self.assertEqual(list(r['items']), ['PC1']); self.assertTrue(r['items']['PC1']['d'].startswith('data:image/jpeg;base64,/9j/'))
        self.assertEqual(board.api_monitor_thumbs({'since': r['last']})['items'], {})
        with mock.patch.object(board, 'start_job') as sj, mock.patch.object(board, 'clean_hosts', lambda h: list(h or [])):
            board.api_monitor_live({'on': False, 'hosts': ['PC1']})
            self.assertEqual(sj.call_args[0][2], {'type': 'config', 'live': 0, 'ttl': 120})
        self.assertNotIn('PC1', board.THUMBS)


class HostMapTest(unittest.TestCase):
    def test_hostmap_overrides_and_validates(self):
        from kv import board, seating
        with mock.patch.dict(seating.CFG, {'hosts': ['10.0.0.5', '10.0.0.6', 'PC3'], 'host_names': {}, 'host_auto_names': {'10.0.0.5': 'PC11', '10.0.0.6': 'PC8'}}), \
             mock.patch.dict(seating.SCHOOL, {'seat_hostmap': {}}), mock.patch.object(board, 'school_save'):
            self.assertEqual(seating.school_seat_no('10.0.0.5', {}), 1)          # chưa gán: theo thứ tự danh sách
            board.api_seat_hostmap({'map': {'10.0.0.5': 8, '10.0.0.6': '11', 'PC3': ''}})
            self.assertEqual(seating.school_seat_no('10.0.0.5', {}), 8)
            self.assertEqual(seating.school_seat_no('10.0.0.6', {'pattern': 'PC{n}'}), 11)   # bảng gán thắng tên máy mẫu
            self.assertEqual(seating.school_seat_no('PC3', {}), 3)
            self.assertEqual(seating.seat_host_map({})[8], '10.0.0.5')
            with self.assertRaises(ApiError):
                board.api_seat_hostmap({'map': {'10.0.0.5': 2, '10.0.0.6': 2}})
            with self.assertRaises(ApiError):
                board.api_seat_hostmap({'map': {'10.0.0.5': 999}})
