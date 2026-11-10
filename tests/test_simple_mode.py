# -*- coding: utf-8 -*-
"""Giao diện rút gọn: kế hoạch sửa máy, làm sạch thiết kế Desktop, nối giao diện - máy chủ - script (không cần Windows)."""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _row(i, state, fix=''):
    return {'id': i, 'label': i, 'state': state, 'detail': '', 'fix': fix}


class RepairPlan(unittest.TestCase):
    def test_plan_from_diagnosis(self):
        from kv.repair import plan_fixes
        machines = [
            {'host': 'A', 'rows': [_row('veyon', 'ok'), _row('agent', 'ok'), _row('clock', 'ok'), _row('service', 'ok')]},
            {'host': 'B', 'rows': [_row('veyon', 'ok'), _row('agent', 'bad'), _row('clock', 'na'), _row('service', 'na')]},
            {'host': 'C', 'rows': [_row('veyon', 'ok'), _row('agent', 'ok'), _row('clock', 'bad', 'time'), _row('service', 'ok')]},
            {'host': 'D', 'rows': [_row('veyon', 'bad'), _row('agent', 'bad')]},
            {'host': 'E', 'rows': [_row('veyon', 'ok'), _row('agent', 'ok'), _row('clock', 'warn', 'time'), _row('service', 'old', 'service')]},
        ]
        machines[4]['rows'][3]['state'] = 'warn'
        p = plan_fixes(machines, [_row('listen', 'ok'), _row('firewall', 'bad', 'firewall')])
        self.assertTrue(p['firewall'])
        self.assertEqual(p['svc'], ['B', 'E'])      # E: dịch vụ cũ (đã gồm cài lại, không chỉnh giờ riêng)
        self.assertEqual(p['time'], ['C'])
        self.assertEqual(p['off'], ['D'])           # máy tắt: không sửa từ xa được

    def test_nothing_to_fix(self):
        from kv.repair import plan_fixes
        p = plan_fixes([{'host': 'A', 'rows': [_row('veyon', 'ok'), _row('agent', 'ok')]}], [_row('firewall', 'ok', '')])
        self.assertEqual(p, {'firewall': False, 'svc': [], 'time': [], 'off': []})

    def test_steps_run_in_scan_diagnose_fix_order(self):
        from kv.repair import STEPS
        self.assertEqual([s[0] for s in STEPS], ['scan', 'diag', 'fix'])


class DeskDesign(unittest.TestCase):
    def test_clean_design(self):
        from kv.deskdesign import clean_design
        d = clean_design({'wall': 'zz', 'items': [
            {'name': 'Web/1', 'kind': 'url', 'target': 'khoaquiz.com', 'col': 1, 'row': 1},
            {'name': 'web1', 'kind': 'url', 'target': 'https://x.com'},                       # trùng tên (sau khi bỏ ký tự cấm)
            {'name': 'Hack', 'kind': 'url', 'target': 'file:///c:/windows/system32/cmd.exe'},  # chỉ nhận http/https
            {'name': 'Word', 'kind': 'app', 'target': '%ProgramFiles%\\w.exe', 'col': 1, 'row': 1},
            {'name': '', 'kind': 'app', 'target': 'x.exe'},
        ]})
        names = [i['name'] for i in d['items']]
        self.assertEqual(names, ['Web1', 'Word'])
        self.assertEqual(d['items'][0]['target'], 'https://khoaquiz.com')
        self.assertEqual(d['wall'], '')
        cells = {(i['col'], i['row']) for i in d['items']}
        self.assertEqual(len(cells), 2)   # không có hai icon chung một ô

    def test_layout_json_for_script(self):
        import json
        from kv.deskdesign import clean_design, layout_bytes
        d = clean_design({'items': [{'name': 'A', 'kind': 'app', 'target': 'notepad.exe', 'col': 3, 'row': 2}]})
        d['stamp'] = '20250101000000'
        lay = json.loads(layout_bytes(d).decode('utf-8'))
        self.assertEqual(lay['stamp'], '20250101000000')
        self.assertEqual(lay['items'][0], {'name': 'A', 'kind': 'app', 'target': 'notepad.exe', 'args': '', 'col': 3, 'row': 2})


class Wiring(unittest.TestCase):
    def test_routes_and_ui_pref(self):
        from kv.routes import GET_ROUTES, POST_ROUTES
        for r in ('/api/simple', '/api/repair_state', '/api/desk'):
            self.assertIn(r, GET_ROUTES)
        for r in ('/api/simple_lock', '/api/repair_start', '/api/desk_save', '/api/desk_apply'):
            self.assertIn(r, POST_ROUTES)
        from kv.uiprefs import ui_clean
        self.assertEqual(ui_clean({'mode': 'simple'})['mode'], 'simple')
        self.assertEqual(ui_clean({'mode': 'xyz'})['mode'], 'full')

    def test_lock_steps_use_existing_actions(self):
        from kv.actions import ACTION_BY_KEY
        from kv.simple import LOCK_STEPS, UNLOCK_STEPS
        for k in LOCK_STEPS + UNLOCK_STEPS:
            self.assertIn(k, ACTION_BY_KEY)
        self.assertIn('webonly', LOCK_STEPS)          # chính sách trình duyệt: gồm tên miền con
        self.assertIn('desklock-start', LOCK_STEPS)
        self.assertEqual(UNLOCK_STEPS[0], 'desklock-stop')

    def test_desklock_script_lets_students_change_wallpaper_and_move_icons(self):
        with open(os.path.join(ROOT, 'payload', 'KhoaVeyonServices.bat'), encoding='utf-8') as f:
            bat = f.read()
        i = bat.index("'desklock-start' {")
        j = bat.index("'desklock-stop' {")
        start = bat[i:j]
        self.assertNotIn('New-ItemProperty -Path "$pol\\ActiveDesktop" -Name NoChangingWallPaper', start)   # không còn khóa hình nền
        self.assertIn('Remove-ItemProperty -Path "$pol\\ActiveDesktop" -Name NoChangingWallPaper', start)   # gỡ khóa của bản cũ
        self.assertIn('layout.json', start)
        guard = start[start.index("$guardSrc = @'"):]
        self.assertIn('Placed.Contains', guard)                       # mỗi icon chỉ đặt một lần
        self.assertIn('deskstamp.txt', guard)                         # và chỉ một lần cho mỗi bản thiết kế
        self.assertNotIn('Arrange()', guard.split('$tick = 0')[1])    # vòng lặp không kéo icon về chỗ cũ mỗi giây

    def test_front_end_hooks(self):
        def rd(p):
            with open(os.path.join(ROOT, 'web', p), encoding='utf-8') as f:
                return f.read()
        html = rd('index.html')
        self.assertIn('id="modeBtn"', html)
        self.assertIn('/js/28-simple.js', html)
        self.assertIn('/css/08-simple.css', html)
        self.assertIn("SIMPLE_NAV", rd('js/28-simple.js'))
        core = rd('js/01-core.js')
        for pid in ('home', 'desk'):
            self.assertTrue(re.search(r"\{id:'%s'" % pid, core))
        app = rd('js/13-app.js')
        self.assertIn('viewHome()', app)
        self.assertIn('viewDesk()', app)


if __name__ == '__main__':
    unittest.main()
