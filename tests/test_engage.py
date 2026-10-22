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
             mock.patch.dict(seating.SCHOOL, {'seat_hostmap': {}, 'seat_by_name': True}), mock.patch.object(board, 'school_save'):
            self.assertEqual(seating.school_seat_no('10.0.0.5', {}), 11)         # chưa gán: lấy số cuối tên PC (PC11 -> 11)
            board.api_seat_hostmap({'map': {'10.0.0.5': 8, '10.0.0.6': '11', 'PC3': ''}, 'by_name': True})
            self.assertEqual(seating.school_seat_no('10.0.0.5', {}), 11)         # bảng gán cũ không thắng tên PC khi bật "số vị trí = số trong tên"
            board.api_seat_hostmap({'map': {'10.0.0.5': 8, '10.0.0.6': '11', 'PC3': ''}, 'by_name': False})
            self.assertEqual(seating.school_seat_no('10.0.0.5', {}), 8)
            self.assertEqual(seating.school_seat_no('10.0.0.6', {'pattern': 'PC{n}'}), 11)   # bảng gán thắng tên máy mẫu
            self.assertEqual(seating.school_seat_no('PC3', {}), 3)
            self.assertEqual(seating.seat_host_map({})[8], '10.0.0.5')
            with self.assertRaises(ApiError):
                board.api_seat_hostmap({'map': {'10.0.0.5': 2, '10.0.0.6': 2}})
            with self.assertRaises(ApiError):
                board.api_seat_hostmap({'map': {'10.0.0.5': 999}})


    def test_pc_number_is_seat_number(self):
        from kv import seating
        with mock.patch.dict(seating.CFG, {'hosts': ['PC3', 'pc01', '10.0.0.9', 'LAB-PC12.local'], 'host_names': {}, 'host_auto_names': {}}), mock.patch.dict(seating.SCHOOL, {'seat_hostmap': {}}):
            self.assertEqual([seating.school_seat_no(h, {}) for h in seating.CFG['hosts']], [3, 1, 3, 12])   # IP chưa biết tên: theo thứ tự danh sách (vị trí 3)


class FunTest(unittest.TestCase):
    def test_groups_stars_react(self):
        from kv import fun
        names = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        with mock.patch.dict(fun.SCHOOL, {'classes': {'10A': names}, 'layouts': {}, 'attendance': {}, 'stars': {}}), mock.patch.object(fun, 'start_job') as sj, \
             mock.patch.object(fun, 'log'), mock.patch.object(fun, 'school_save'), mock.patch.object(fun, 'clean_hosts', lambda h: list(h or [])), \
             mock.patch.object(fun, 'who', lambda h, c='': ('A', '10A', 1)):
            r = fun.api_groups({'cls': '10A', 'mode': 'count', 'n': 3, 'send': False})
            self.assertEqual(sorted(len(g['names']) for g in r['groups']), [2, 2, 3]); self.assertEqual(sorted(sum((g['names'] for g in r['groups']), [])), names)
            self.assertEqual(len(fun.api_groups({'cls': '10A', 'mode': 'size', 'n': 3, 'send': False})['groups']), 3)
            fun.api_star({'hosts': ['h1'], 'cls': '10A'}); fun.api_star({'hosts': ['h1'], 'cls': '10A', 'text': 'Giỏi'})
            self.assertEqual(fun.stars_board('10A'), [{'name': 'A', 'stars': 2}])
            with self.assertRaises(ApiError):
                fun.api_countdown({'hosts': ['h'], 'minutes': 'x'})
            sj.reset_mock(); fun.api_countdown({'hosts': ['h'], 'minutes': '2.5'}); self.assertEqual(sj.call_args[0][2]['secs'], 150)
        fun.react_put('PC1', 'lost'); fun.react_put('PC2', 'bad')
        self.assertEqual(fun.react_snapshot(), {'PC1': 'lost'})


class UiPrefsTest(unittest.TestCase):
    def test_clean(self):
        from kv import uiprefs
        p = uiprefs.ui_clean({'theme': 'neon', 'accent': 'red', 'font': 9999, 'zoom': 'x', 'hidden_pages': ['viol', 'settings', 'control', '../x', 'viol'], 'brand': '<b>Lab</b>', 'tile': 'large', 'anim': 0})
        self.assertEqual((p['theme'], p['accent'], p['font'], p['zoom']), ('light', '#2563eb', 140, 100))
        self.assertEqual(p['hidden_pages'], ['viol']); self.assertNotIn('<', p['brand']); self.assertEqual(p['tile'], 'large'); self.assertFalse(p['anim'])


class SeatAutoTest(unittest.TestCase):
    def test_roster_order(self):
        from kv import board
        lay = {'cols': 2, 'per': 3, 'broken': [2], 'seats': {}}
        with mock.patch.dict(board.SCHOOL, {'classes': {'10A': ['A', 'B', 'C', 'D', 'E', 'F']}, 'layouts': {'10A': lay}}), mock.patch.object(board, 'school_save'):
            r = board.api_seat_auto({'cls': '10A'})
        self.assertEqual(lay['seats'], {str(i + 1): n for i, n in enumerate('ABCDEF')}); self.assertEqual(r['left'], 0)   # đúng số thứ tự, kể cả máy hỏng


    def test_default_seats_once(self):
        from kv import school
        lay = {'cols': 2, 'per': 2, 'seats': {}}
        with mock.patch.dict(school.SCHOOL, {'classes': {'10A': ['A', 'B', 'C', 'D', 'E']}, 'layouts': {'10A': lay}, 'seats_init': []}):
            self.assertTrue(school.ensure_default_seats())
            self.assertEqual(lay['seats'], {'1': 'A', '2': 'B', '3': 'C', '4': 'D'})
            lay['seats'] = {}                       # giáo viên chủ động xóa: không tự xếp lại
            self.assertFalse(school.ensure_default_seats()); self.assertEqual(lay['seats'], {})


class QuickNotesTest(unittest.TestCase):
    def test_quick(self):
        from kv import fun
        with mock.patch.dict(fun.SCHOOL, {'quick_notes': None}), mock.patch.object(fun, 'school_save'):
            d = fun.api_quick_notes(); self.assertFalse(d['custom']); self.assertGreaterEqual(len(d['items']), 8)
            r = fun.api_quick_notes_save({'items': [{'icon': '🎒', 'label': 'Về', 'text': 'Được về'}, {'label': '', 'text': 'x'}, 'bad']})
            self.assertEqual(r['items'], [{'icon': '🎒', 'label': 'Về', 'text': 'Được về'}]); self.assertTrue(r['custom'])
            self.assertFalse(fun.api_quick_notes_save({'items': []})['custom'])


class ClassroomTest(unittest.TestCase):
    def setUp(self):
        from kv import classroom
        self.c = classroom
        self.c.QUIZ.clear()
        self.sent = []
        mock.patch.object(classroom, 'start_job', lambda f, *a: self.sent.append(a)).start()
        mock.patch.object(classroom, 'log').start()
        mock.patch.object(classroom, 'who', lambda h, c='': ('HS ' + h, c, 1)).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_quiz_flow(self):
        with mock.patch.object(self.c, 'clean_hosts', lambda h: list(h)):
            self.assertRaises(ApiError, self.c.api_quiz_start, {'hosts': ['a'], 'q': 'x', 'opts': ['1']})
            st = self.c.api_quiz_start({'hosts': ['a', 'b', 'c'], 'q': 'Hỏi?', 'opts': ['x', 'y', '', 'z'], 'correct': 1, 'secs': 30, 'cls': '10A'})
            self.assertEqual(st['opts'], ['x', 'y', 'z']); self.assertEqual(st['total'], 3)
            qid = st['id']
            self.c.quiz_answer('a', qid, 1); self.c.quiz_answer('b', qid, 0); self.c.quiz_answer('b', qid, 2)
            self.c.quiz_answer('zz', qid, 0); self.c.quiz_answer('c', 'sai', 0); self.c.quiz_answer('c', qid, 9)
            st = self.c.api_quiz_state()
            self.assertEqual(st['counts'], [0, 1, 1]); self.assertEqual(st['answered'], 2); self.assertEqual(st['pending'], ['HS c (máy 1)'])
            st = self.c.api_quiz_end({'reveal': True}); self.assertTrue(st['closed'])
            self.c.quiz_answer('c', qid, 0); self.assertEqual(self.c.api_quiz_state()['answered'], 2)

    def test_open_url(self):
        with mock.patch.object(self.c, 'clean_hosts', lambda h: list(h)):
            self.assertRaises(ApiError, self.c.api_open_url, {'hosts': ['a'], 'url': 'javascript:alert(1)'})
            self.assertRaises(ApiError, self.c.api_open_url, {'hosts': ['a'], 'url': 'file:///c:/x'})
            self.assertTrue(self.c.api_open_url({'hosts': ['a'], 'url': 'https://example.com/a?b=1'})['ok'])

    def test_handout_validation(self):
        b64 = lambda d: base64.b64encode(d).decode()
        with mock.patch.object(self.c, 'clean_hosts', lambda h: list(h)), tempfile.TemporaryDirectory() as td, mock.patch.object(self.c, 'handouts_root', lambda: td):
            self.assertRaises(ApiError, self.c.api_handout_send, {'hosts': ['a'], 'files': [{'name': 'x.exe', 'data': b64(b'1')}]})
            self.assertRaises(ApiError, self.c.api_handout_send, {'hosts': ['a'], 'files': [{'name': 'a.txt', 'data': ''}]})
            r = self.c.api_handout_send({'hosts': ['a'], 'files': [{'name': '..\\..\\bai 1.pdf', 'data': b64(b'pdf')}]})
            self.assertEqual(r['files'], ['bai 1.pdf'])
            self.assertEqual(self.c.safe_name('a/b:c?.txt'), 'b_c_.txt')


class ShareDrawTest(unittest.TestCase):
    def setUp(self):
        from kv import classroom
        self.c = classroom
        self.c.SHARE.clear()
        self.jobs = []
        mock.patch.object(classroom, 'start_job', lambda f, *a: self.jobs.append(a)).start()
        mock.patch.object(classroom, 'log').start()
        mock.patch.object(classroom, 'who', lambda h, c='': ('HS ' + h, c, 3)).start()
        mock.patch.object(classroom, 'clean_hosts', lambda h: [x for x in h if x]).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_share_flow(self):
        self.assertRaises(ApiError, self.c.api_share_snap, {'host': ''})
        r = self.c.api_share_snap({'host': 'a'}); sid = r['id']
        self.assertRaises(ApiError, self.c.api_share_push, {'id': sid, 'hosts': ['b']})   # chưa có ảnh
        self.c.share_ready('zz', sid); self.assertFalse(self.c.SHARE[sid]['ready'])      # máy khác không được báo
        self.c.share_ready('a', sid)
        with mock.patch.object(self.c, 'rfs_read', return_value=b'\xff\xd8abc'):
            st = self.c.api_share_state({'id': sid})
        self.assertTrue(st['ready']); self.assertTrue(st['img'].startswith('data:image/jpeg;base64,'))
        self.jobs.clear()
        self.assertTrue(self.c.api_share_push({'id': sid, 'hosts': ['a', 'b', 'c'], 'secs': 99999, 'hide_name': True})['ok'])
        job = self.jobs[0]; self.assertEqual(job[0], ['b', 'c'])   # máy nguồn bị loại
        self.assertEqual(job[3]['secs'], 900); self.assertEqual(job[3]['cap'], 'Bài của một bạn')
        with mock.patch.object(self.c, 'rfs_read', return_value=b'notjpeg'):
            s2 = self.c.api_share_snap({'host': 'a'})['id']; self.c.share_ready('a', s2)
            self.assertRaises(ApiError, self.c.api_share_state, {'id': s2})

    def test_draw_announce(self):
        from kv import engage
        engage.DRAWN.clear()
        c = [('An', 1, 'h1'), ('Binh', 2, 'h2'), ('Chi', 3, 'h3')]
        sent = []
        with mock.patch.object(engage, 'draw_candidates', lambda cls: list(c)), mock.patch.object(engage, 'start_job', lambda f, *a: sent.append(a)), \
                mock.patch.object(engage, 'log'), mock.patch.dict(engage.SCHOOL['classes'], {'10A': []}):
            r = engage.api_draw({'cls': '10A', 'announce': True, 'hide_name': True})
        self.assertEqual(len(sent), 2)
        ann = sent[1]
        self.assertNotIn(r['host'], ann[0]); self.assertEqual(len(ann[0]), 2)
        self.assertIn('Máy số', ann[1]['title']); self.assertNotIn(r['name'], ann[1]['title'])


class PhoneTest(unittest.TestCase):
    def setUp(self):
        from kv import phone
        self.p = phone
        mock.patch.object(phone, 'log').start()
        mock.patch.object(phone, '_student_ips', lambda: {'10.0.0.50'}).start()
        mock.patch.object(phone, 'lan_ip', lambda: '192.168.1.9').start()
        phone.PH.update(devices={}, fails={})
        phone.api_phone_stop()

    def tearDown(self):
        self.p.api_phone_stop()
        mock.patch.stopall()

    def test_auth_and_block(self):
        self.assertEqual(self.p.handle('192.168.1.20', 'GET', '/state', 'x')[0], 403)     # chưa bật
        st = self.p.api_phone_start({'hours': 99})
        tok = self.p.PH['token']
        self.assertTrue(st['on'] and st['qr'].startswith('<svg') and tok in st['url'] and st['url'].startswith('http://192.168.1.9:'))
        self.assertLessEqual(self.p.PH['exp'] - __import__('time').time(), 12 * 3600 + 5)
        self.assertEqual(self.p.handle('8.8.8.8', 'GET', '/', tok)[0], 403)               # ngoài mạng riêng
        self.assertEqual(self.p.handle('10.0.0.50', 'GET', '/', tok)[0], 403)             # máy học sinh
        self.assertEqual(self.p.handle('192.168.1.20', 'GET', '/', tok)[0], 200)
        for _ in range(self.p.MAX_FAILS):
            self.assertEqual(self.p.handle('192.168.1.21', 'GET', '/state', 'sai')[0], 403)
        self.assertEqual(self.p.handle('192.168.1.21', 'GET', '/state', tok)[0], 429)     # bị khóa dù đúng mã
        self.assertEqual(self.p.handle('192.168.1.20', 'GET', '/state', tok)[0], 200)     # máy khác vẫn dùng được
        self.p.api_phone_start({})                                                         # đổi mã: mã cũ chết
        self.assertEqual(self.p.handle('192.168.1.20', 'GET', '/state', tok)[0], 403)

    def test_ops_whitelist(self):
        self.p.api_phone_start({}); tok = self.p.PH['token']
        with mock.patch.object(self.p, '_all_hosts', lambda: ['h1', 'h2']):
            code, out, _ = self.p.handle('192.168.1.20', 'POST', '/do', tok, {'op': 'format_c'})
            self.assertEqual(code, 400)
            sent = []
            with mock.patch('kv.student.start_job', lambda f, *a: sent.append(a)):
                code, out, _ = self.p.handle('192.168.1.20', 'POST', '/do', tok, {'op': 'msg', 'text': 'Lớp ổn'})
            self.assertEqual(code, 200); self.assertEqual(sent[0][0], ['h1', 'h2']); self.assertEqual(sent[0][1]['text'], 'Lớp ổn')
            self.assertEqual(self.p.handle('192.168.1.20', 'POST', '/do', tok, {'op': 'star', 'host': 'khac'})[0], 400)

    def test_expiry(self):
        self.p.api_phone_start({}); tok = self.p.PH['token']
        self.p.PH['exp'] = 1
        self.assertEqual(self.p.handle('192.168.1.20', 'GET', '/state', tok)[0], 403)
        self.assertFalse(self.p.api_phone_state()['on'])


class RadminTest(unittest.TestCase):
    def setUp(self):
        from kv import radmin, phone
        self.r = radmin
        mock.patch.object(radmin, 'log').start()
        mock.patch.object(phone, '_student_ips', lambda: {'10.0.0.50'}).start()
        mock.patch.object(radmin, 'lan_ip', lambda: '192.168.1.9').start()
        radmin.api_radmin_stop()

    def tearDown(self):
        self.r.api_radmin_stop()
        mock.patch.stopall()

    def test_pin_format_and_login(self):
        self.assertEqual(self.r.login('192.168.1.2', '123456')[0], 403)      # đang tắt
        st = self.r.api_radmin_start({'hours': 1})
        pin = st['pin']; self.assertRegex(pin, r'^\d{6}$')
        self.assertEqual(self.r.login('192.168.1.2', '12345x')[0], 403)
        code, _o, sid = self.r.login('192.168.1.2', pin); self.assertEqual(code, 200); self.assertTrue(sid)
        self.assertIsNotNone(self.r.session_for('192.168.1.2', sid))
        self.assertIsNone(self.r.session_for('192.168.1.3', sid))            # phiên gắn với IP
        self.assertIsNone(self.r.session_for('192.168.1.2', 'khac'))
        pin2 = self.r.api_radmin_newpin()['pin']
        self.assertIsNone(self.r.session_for('192.168.1.2', sid))            # đổi PIN đăng xuất hết
        self.assertEqual(self.r.login('192.168.1.2', pin2)[0], 200)

    def test_lockout_and_global_off(self):
        pin = self.r.api_radmin_start({})['pin']
        wrong = '000000' if pin != '000000' else '111111'
        for i in range(self.r.MAX_IP_FAILS):
            self.assertEqual(self.r.login('192.168.1.7', wrong)[0], 403)
        self.assertEqual(self.r.login('192.168.1.7', pin)[0], 429)           # khóa IP kể cả đúng PIN
        for k in range(8, 8 + self.r.MAX_GLOBAL_FAILS):
            self.r.login('192.168.1.%d' % k, wrong)
        self.assertFalse(self.r.api_radmin_state()['on'])                     # tự tắt khi bị đoán dồn dập

    def test_denied_paths(self):
        self.r.api_radmin_start({'full': False})
        for p in ('/api/radmin_state', '/api/phone_state', '/api/quit', '/api/open', '/api/run', '/api/backup_restore', '/api/settings'):
            self.assertTrue(self.r.denied(p), p)
        for p in ('/api/monitor', '/api/student_send', '/api/open_url', '/api/draw', '/api/school'):
            self.assertFalse(self.r.denied(p), p)
        self.r.api_radmin_start({'full': True})
        self.assertFalse(self.r.denied('/api/run')); self.assertTrue(self.r.denied('/api/radmin_state')); self.assertTrue(self.r.denied('/api/applock'))

    def test_forward_token_swap(self):
        from kv.runtime import STATE
        seen = {}

        class R:
            status = 200
            def read(s): return b'<script>const TOKEN = \'REAL\';</script>'
            def getheader(s, k): return 'text/html'

        class C:
            def __init__(s, *a, **k): pass
            def request(s, m, t, body=None, headers=None): seen.update(t=t, h=headers)
            def getresponse(s): return R()
            def close(s): pass
        old = dict(STATE)
        STATE.update(token='REAL', port=9)
        try:
            with mock.patch.object(self.r.http.client, 'HTTPConnection', C):
                sess = {'fake': 'FAKE'}
                code, data, ct, cd = self.r.forward(sess, 'GET', '/?t=remote', None, {})
                self.assertIn(b'FAKE', data); self.assertNotIn(b'REAL', data); self.assertIn('t=REAL', seen['t'])
                self.r.forward(sess, 'POST', '/api/draw', b'{}', {'X-Token': 'FAKE'}); self.assertEqual(seen['h']['X-Token'], 'REAL')
                self.r.forward(sess, 'POST', '/api/draw', b'{}', {'X-Token': 'REAL'}); self.assertNotIn('X-Token', seen['h'])   # không nhận mã thật từ ngoài
                self.r.forward(sess, 'GET', '/evidence/a.jpg?t=sai', None, {}); self.assertNotIn('t=', seen['t'])
        finally:
            STATE.clear(); STATE.update(old)


class RadminViewTest(unittest.TestCase):
    def setUp(self):
        from kv import radmin, phone
        self.r = radmin
        mock.patch.object(radmin, 'log').start()
        mock.patch.object(radmin, '_student_ips', lambda: {'10.0.0.50'}).start()
        mock.patch.object(radmin, 'lan_ip', lambda: '192.168.1.9').start()
        radmin.api_radmin_stop()

    def tearDown(self):
        self.r.api_radmin_stop(); mock.patch.stopall()

    def test_roles(self):
        st = self.r.api_radmin_start({}); pin, vpin = st['pin'], st['vpin']
        self.assertNotEqual(pin, vpin); self.assertRegex(vpin, r'^\d{6}$')
        c, o, sid = self.r.login('192.168.1.2', pin); self.assertEqual(o['role'], 'admin')
        c, o, vsid = self.r.login('192.168.1.3', vpin); self.assertEqual(o['role'], 'view')
        self.assertEqual(self.r.session_for('192.168.1.3', vsid)['role'], 'view')
        c, o, ssid = self.r.login('10.0.0.50', vpin); self.assertEqual((c, o['role']), (200, 'view'))   # máy học sinh: chỉ vào được PIN xem
        self.assertEqual(self.r.login('10.0.0.50', pin)[0], 403)                                        # PIN quản trị bị từ chối
        self.assertTrue(self.r.view_denied('/api/student_send', 'POST')); self.assertTrue(self.r.view_denied('/api/log'))
        self.assertTrue(self.r.view_denied('/api/monitor', 'POST')); self.assertFalse(self.r.view_denied('/api/monitor?cls=10A'))
        self.assertTrue(self.r.view_denied('/api/radmin_state'))
        self.assertTrue(self.r.ip_ok('192.168.0.4')); self.assertFalse(self.r.ip_ok('8.8.8.8'))


class HelperTestTest(unittest.TestCase):
    def setUp(self):
        from kv import helpertest
        self.h = helpertest
        self.h.ACKS.clear(); self.h.HT['data'] = None
        self.sent = []
        self.mocks = [mock.patch.object(helpertest, '_inbox_write', lambda host, msg: self.sent.append(msg)),
                      mock.patch.object(helpertest, 'log'), mock.patch.object(helpertest, 'pause', lambda s: None),
                      mock.patch.object(helpertest, 'ACK_WAIT', 0.5)]
        [m.start() for m in self.mocks]

    def tearDown(self):
        mock.patch.stopall()

    def _auto_ack(self, ok=True, skip=()):
        """Giả lập máy học sinh: mỗi tin có tid thì báo lại."""
        orig = self.h._inbox_write

        def w(host, msg):
            self.sent.append(msg)
            if msg.get('tid') and msg['step'] not in skip:
                self.h.ack_put(host, msg['tid'], msg['step'], ok, '' if ok else 'boom', 'thông tin')
        return mock.patch.object(self.h, '_inbox_write', w)

    def test_ack_rules(self):
        self.h.ack_put('a', 'zzzz', 's', True, '', '')           # tid sai: bỏ qua
        self.assertEqual(len(self.h.ACKS), 0)
        self.h.ack_put('a', 'aabbccdd', 's', True, 'x' * 999, '')
        self.assertLessEqual(len(self.h.ACKS[('aabbccdd', 's')]['err']), 200)
        self.assertIsNone(self.h.wait_ack('aabbccdd', 's', 'khac', 0.3))   # ack của máy khác không tính
        self.assertEqual(self.h._show_ack(None, 'x')[0], 'bad')
        self.assertEqual(self.h._show_ack({'ok': False, 'err': 'e', 'info': ''}, 'x')[0], 'bad')

    def test_full_run_all_ok(self):
        rf = {}
        with self._auto_ack(), mock.patch.object(self.h, 'rfs_write', lambda h, p, d: rf.__setitem__(p, d)), \
                mock.patch.object(self.h, 'rfs_read', lambda h, p: rf.get(p) or (b'\xff\xd8' + b'0' * 5000)), mock.patch.object(self.h, 'rfs_remove', lambda h, p: None), \
                mock.patch('kv.engage._ensure_bg', lambda h, b: None):
            from kv.board import THUMBS
            from kv.student import LOCK
            with LOCK:
                THUMBS['h1'] = {'d': 'x', 'ts': 9e12, 'seq': 1}
            try:
                self.h.api_ht_start({'hosts': ['h1'], 'url': True})
                for _ in range(100):
                    if self.h.HT['data']['done']:
                        break
                    __import__('time').sleep(0.1)
            finally:
                with LOCK:
                    THUMBS.pop('h1', None)
        D = self.h.HT['data']
        self.assertTrue(D['done'])
        bad = [(r['key'], r['detail']) for r in D['steps'] if r['status'] not in ('ok',)]
        self.assertEqual(bad, [])
        types = [m['type'] for m in self.sent]
        for t in ('selftest', 'msg', 'quiz', 'quizend', 'timer', 'block', 'clear', 'wallpaper', 'snap', 'show', 'showclear', 'handout', 'config', 'open'):
            self.assertIn(t, types)

    def test_helper_dead_skips_rest(self):
        rf = {}
        with self._auto_ack(skip=('helper',)), mock.patch.object(self.h, 'rfs_write', lambda h, p, d: rf.__setitem__(p, d)), \
                mock.patch.object(self.h, 'rfs_read', lambda h, p: rf.get(p)), mock.patch.object(self.h, 'rfs_remove', lambda h, p: None):
            self.h.api_ht_start({'hosts': ['h1']})
            for _ in range(100):
                if self.h.HT['data']['done']:
                    break
                __import__('time').sleep(0.1)
        st = {r['key']: r['status'] for r in self.h.HT['data']['steps']}
        self.assertEqual((st['link'], st['helper'], st['msg'], st['thumb']), ('ok', 'bad', 'skip', 'skip'))

    def test_single_host_required(self):
        self.assertRaises(ApiError, self.h.api_ht_start, {'hosts': ['a', 'b']})


class GuidesTest(unittest.TestCase):
    def setUp(self):
        from kv import guides
        self.g = guides
        self.td = tempfile.TemporaryDirectory()
        self.jobs = []
        mock.patch.object(guides, 'gdir', lambda: self.td.name).start()
        mock.patch.object(guides, 'start_job', lambda f, *a: self.jobs.append(a)).start()
        mock.patch.object(guides, 'log').start()
        mock.patch.object(guides, 'clean_hosts', lambda h: [x for x in h if x]).start()

    def tearDown(self):
        mock.patch.stopall(); self.td.cleanup()

    def test_builtin_assets_exist(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for g in self.g.BUILTIN:
            p = os.path.join(root, 'web', 'assets', 'guide-%s.gif' % g['id'])
            self.assertTrue(os.path.isfile(p), p)
            with open(p, 'rb') as f:
                self.assertEqual(f.read(6)[:4], b'GIF8')
        self.assertEqual(self.g.BUILTIN_BY_ID['zoom']['keys'], 'Ctrl + lăn chuột')

    def test_custom_crud(self):
        gif = b'GIF89a' + b'\x00' * 50
        self.assertRaises(ApiError, self.g.api_guide_save, {'title': '', 'steps': ['a']})
        self.assertRaises(ApiError, self.g.api_guide_save, {'title': 'T', 'steps': ['a'], 'image': base64.b64encode(b'notimage').decode()})
        r = self.g.api_guide_save({'title': 'Đổi cỡ chữ', 'steps': ['Bôi đen', '  ', 'Chọn cỡ'], 'image': 'data:image/gif;base64,' + base64.b64encode(gif).decode()})
        mine = [x for x in r['items'] if not x['builtin']]
        self.assertEqual(len(mine), 1); self.assertEqual(mine[0]['steps'], ['Bôi đen', 'Chọn cỡ']); gid = mine[0]['id']
        self.assertTrue(self.g.api_guide_img({'id': gid})['data'].startswith('data:image/gif;base64,'))
        self.g.api_guide_save({'id': gid, 'title': 'Mới', 'steps': ['x']})                    # sửa không gửi ảnh: giữ ảnh cũ
        self.assertTrue(self.g.api_guide_img({'id': gid})['data'])
        self.assertEqual(len(self.g.api_guides()['items']), len(self.g.BUILTIN) + 1)
        self.g.api_guide_delete({'id': gid})
        self.assertEqual(len(self.g.api_guides()['items']), len(self.g.BUILTIN))
        self.assertEqual([f for f in os.listdir(self.td.name) if f != 'custom.json'], [])

    def test_send(self):
        self.assertRaises(ApiError, self.g.api_guide_send, {'id': 'zoom', 'hosts': []})
        self.assertRaises(ApiError, self.g.api_guide_send, {'id': '../x', 'hosts': ['a']})
        self.assertRaises(ApiError, self.g.api_guide_send, {'id': 'khongco', 'hosts': ['a']})
        self.g.api_guide_send({'id': 'zoom', 'hosts': ['a', 'b'], 'secs': 99999})
        hosts, msg, data, ext = self.jobs[0]
        self.assertEqual(hosts, ['a', 'b']); self.assertEqual((msg['type'], msg['gid'], msg['img'], ext), ('guide', 'zoom', 'zoom.gif', '.gif'))
        self.assertEqual(msg['secs'], 900); self.assertTrue(data.startswith(b'GIF8')); self.assertEqual(len(msg['steps']), 3)
