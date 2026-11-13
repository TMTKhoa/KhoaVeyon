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


class QuickLockOptions(unittest.TestCase):
    def test_opts_choose_the_lock_steps(self):
        from kv.simple import clean_opts, lock_steps_for
        self.assertEqual(lock_steps_for(clean_opts({})), ('lockall-start', 'webonly', 'desklock-start'))
        self.assertEqual(lock_steps_for(clean_opts({'apps': False, 'desk': False})), ('webonly',))
        self.assertEqual(lock_steps_for(clean_opts({'web': False})), ('lockall-start', 'desklock-start'))
        self.assertEqual(clean_opts('junk'), {'apps': True, 'web': True, 'desk': True})

    def test_lock_needs_at_least_one_option(self):
        from kv.runtime import ApiError
        from kv.simple import api_simple_lock
        with self.assertRaises(ApiError):
            api_simple_lock({'lock': True, 'hosts': ['10.0.0.5'], 'opts': {'apps': False, 'web': False, 'desk': False}})

    def test_teacher_pc_is_never_a_target(self):
        import socket
        from kv.network import is_this_pc, local_ips
        self.assertTrue(is_this_pc(socket.gethostname()))
        for ip in local_ips():
            self.assertTrue(is_this_pc(ip))
            self.assertTrue(is_this_pc(ip + ':11100'))
        self.assertFalse(is_this_pc('127.0.0.1'))
        self.assertFalse(is_this_pc('may-hoc-sinh-khong-ton-tai-xyz'))

    def test_class_lock_flag_is_not_mistaken_for_app_lock_screen(self):
        """Lỗi cũ: /api/simple trả locked:true khi lớp đang khóa, giao diện tưởng là khóa màn hình ứng dụng và bắt nhập mật khẩu liên tục."""
        with open(os.path.join(ROOT, 'web', 'js', '01-core.js'), encoding='utf-8') as f:
            core = f.read()
        self.assertNotIn('r.status === 423 || data.locked)', core)
        self.assertIn("'/api/applock'", core)


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

    def test_desklock_script_locks_wallpaper_and_icon_positions(self):
        with open(os.path.join(ROOT, 'payload', 'KhoaVeyonServices.bat'), encoding='utf-8') as f:
            bat = f.read()
        i = bat.index("'desklock-start' {")
        j = bat.index("'desklock-stop' {")
        start = bat[i:j]
        self.assertIn('layout.json', start)
        guard = start[start.index("$guardSrc = @'"):]
        loop = guard.split('$tick = 0')[1]
        self.assertIn('Fixed.TryGetValue', guard)                     # vị trí đã khóa của từng icon
        self.assertIn('LVM_GETITEMPOSITION', guard)                   # đọc vị trí để phát hiện học sinh kéo icon
        self.assertIn('NoChangingWallPaper', guard)                   # chặn đổi hình nền bằng chính sách (theo từng học sinh, không đụng quản trị viên)
        self.assertIn('NoViewContextMenu', guard)                     # tắt chuột phải Desktop (Set as background, Auto arrange)
        self.assertIn("[KvDesk]::Wall()", loop)                       # hình nền bị đổi thì đặt lại
        self.assertIn('Clear-Pol', loop)                              # mở khóa thì trả lại như cũ
        self.assertIn('Fix-IconSize', guard)                          # Ctrl + lăn chuột / View > Large icons bị đưa về cỡ cố định
        self.assertNotIn('Placed.Contains', guard)                    # không còn "đặt một lần rồi mặc kệ"
        stop = bat[j:bat.index("'blockai' {")]
        self.assertIn('KVTMPHIVE', stop)                              # mở khóa dọn cả chính sách của tài khoản đã đăng xuất

    def test_interact_wallpaper_and_design_wallpaper_do_not_fight(self):
        with open(os.path.join(ROOT, 'payload', 'KhoaVeyonServices.bat'), encoding='utf-8') as f:
            bat = f.read()
        guard = bat[bat.index("$guardSrc = @'"):bat.index("'desklock-stop' {")]
        self.assertIn('wall-orig.txt', guard)     # hình nền theo tiết của trang Tương tác đang dùng thì guard giữ đúng hình đó
        self.assertIn('$wantWall', guard)

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
