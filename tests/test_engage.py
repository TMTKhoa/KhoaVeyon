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
        with mock.patch.object(engage, 'who', lambda h: ('An', '10A', 7)):
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
