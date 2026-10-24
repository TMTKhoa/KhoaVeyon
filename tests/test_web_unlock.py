# -*- coding: utf-8 -*-
"""Mở khóa web sau khi khóa "chỉ trang cho phép", và nhật ký 5 phút đi kèm ảnh vi phạm."""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from kv import alerts, reports  # noqa: E402
from kv.applied import APPLY_CATS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bat():
    with open(os.path.join(ROOT, 'payload', 'KhoaVeyonServices.bat'), encoding='utf-8') as f:
        return f.read()


def _block(s, start, end):
    i = s.index(start)
    return s[i:s.index(end, i)]


class WebOnlyUnlockTest(unittest.TestCase):
    def setUp(self):
        self.s = _bat()

    def test_allowall_also_lifts_browser_policy(self):
        b = _block(self.s, "    'allowall' {", "    'allowpage' {")
        self.assertIn('Remove-Rules', b)
        self.assertIn('Test-Path -LiteralPath $pageBackup', b)   # chỉ gỡ khi chính KhoaVeyon đã khóa (có file sao lưu)
        self.assertIn('Page-Stop', b)

    def test_second_lock_keeps_original_backup(self):
        b = _block(self.s, 'function Page-Start', 'function Page-Stop')
        # đọc lại bản sao lưu gốc trước khi tạo bản mới, và dùng giá trị gốc thay vì trạng thái đã khóa
        self.assertLess(b.index('ConvertFrom-Json'), b.index('$rec.Add('))
        self.assertIn('$o.Block', b)
        self.assertIn('StarWasThere', b)

    def test_unlock_always_removes_star_added_by_us(self):
        b = _block(self.s, 'function Page-Stop', '# ---------- modes ----------')
        self.assertIn("-ne '*'", b)
        self.assertIn('StarWasThere', b)

    def test_teacher_tracks_webonly_state(self):
        self.assertEqual(APPLY_CATS['webonly'][2], True)
        self.assertEqual(APPLY_CATS['weboff'][2], False)
        self.assertEqual(APPLY_CATS['webonly'][0], APPLY_CATS['allowall'][0])   # cùng nhóm "net": Cho internet xóa nhãn

    def test_powershell_part_balanced(self):
        seg = _block(self.s, 'function Page-Start', '# ---------- modes ----------')
        code = re.sub(r"'[^'\n]*'|\"[^\"\n]*\"|#[^\n]*", '', seg)
        self.assertEqual(code.count('{'), code.count('}'))
        self.assertEqual(code.count('('), code.count(')'))


class RecentLogTest(unittest.TestCase):
    def test_recent_clean_keeps_newest_60_and_site(self):
        rows = [{'p': 'chrome', 'w': 'tab %d' % i, 'h': 'youtube.com', 't': '09:%02d:00' % (i % 60), 'd': 5} for i in range(80)]
        out = alerts._recent_clean(rows)
        self.assertEqual(len(out), 60)
        self.assertEqual(out[-1]['w'], 'tab 79')           # giữ các mục mới nhất, không phải cũ nhất
        self.assertEqual(out[0]['w'], 'tab 20')
        self.assertEqual(out[0]['h'], 'youtube.com')

    def test_recent_text(self):
        t = reports.recent_text([{'t': '09:01:02', 'p': 'chrome', 'h': 'youtube.com', 'w': 'Video', 'd': 30},
                                 {'t': '09:01:32', 'p': 'winword', 'h': '', 'w': 'Bai 1', 'd': 120}])
        self.assertEqual(t, '09:01:02 chrome [youtube.com] Video (30s) | 09:01:32 winword Bai 1 (2 phút)')
        self.assertEqual(reports.recent_text(None), '')

    def test_episode_carries_recent_log(self):
        rec = [{'t': '09:00:00', 'p': 'chrome', 'h': '', 'w': 'x', 'd': 9}]
        ev = [{'host': 'M1', 'type': 'site', 'name': 'x.com', 'date': 'd', 'time': 't', 'ts': 100, 'student': 'An', 'cls': '3A4', 'seat': 1, 'recent': rec}]
        self.assertEqual(reports.report_episodes(ev, 60)[0]['recent'], rec)


if __name__ == '__main__':
    unittest.main()


class ChromeFalseAlarmTest(unittest.TestCase):
    """Thao tác bình thường trong Chrome (hộp thoại lưu tệp, ô nhập của trang, đang gõ địa chỉ) không được tính là vi phạm."""

    def setUp(self):
        with open(os.path.join(ROOT, 'scripts', 'KhoaVeyonWatch.ps1'), encoding='utf-8') as f:
            s = f.read()
        i = s.index('function Get-BrowserHost')
        self.f = s[i:s.index('# Nhat ky 5 phut', i)]
        self.s = s

    def test_reads_only_the_address_bar_on_chromium(self):
        self.assertIn("'OmniboxViewViews'", self.f)
        self.assertIn('FindFirst', self.f)

    def test_system_dialogs_are_not_web_pages(self):
        self.assertIn("'#32770'", self.f)

    def test_typing_does_not_count_as_a_page(self):
        self.assertIn('HasKeyboardFocus', self.f)
        self.assertIn("'*keep*'", self.f)
        self.assertIn("'*keep*'", self.s[self.s.index('$bk = "$h|$title"'):])   # nơi gọi giữ kết quả cũ, không ghi đè

    def test_regex_not_doubled_backslash(self):
        self.assertNotIn('\\\\.', self.f)                 # '\.' đúng, '\\.' là lỗi gõ
        self.assertEqual(self.f.count('{'), self.f.count('}'))
        self.assertEqual(self.f.count('('), self.f.count(')'))

    def test_domain_regex_still_matches_real_sites_and_keeps_old_false_positive_in_mind(self):
        rx = re.compile(r'^(https?://)?([a-z0-9-]+\.)+[a-z0-9-]{2,}(:\d+)?([/?#].*)?$')
        self.assertTrue(rx.match('wikipedia.org/wiki/x'))
        self.assertTrue(rx.match('bai-tap.docx') and rx.match('3.14'))    # chính vì thế không được áp regex lên mọi ô nhập
