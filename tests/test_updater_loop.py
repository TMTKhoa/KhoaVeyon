# -*- coding: utf-8 -*-
"""update_loop() phải nhận ngay khi giáo viên bật công tắc "Tự kiểm tra bản mới" (hoặc điền kho GitHub) giữa lúc
chương trình đang chạy, không phải chờ tới UPDATE_EVERY (6 giờ) mới kiểm tra lại."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class Stop(Exception):
    pass


class UpdateLoopPicksUpToggleQuickly(unittest.TestCase):
    def test_toggle_on_mid_run_is_checked_within_one_short_sleep(self):
        from kv import updater
        from kv.runtime import CFG
        orig_check, orig_repo = CFG.get('update_check'), CFG.get('update_repo')
        orig_sleep, orig_once = updater.time.sleep, updater.update_check_once
        calls, checked = [], []

        def fake_sleep(secs):
            calls.append(secs)
            if secs == 8:          # chờ khởi động xong, công tắc đang TẮT lúc này
                CFG['update_check'] = False
                CFG['update_repo'] = 'a/b'
            elif len(calls) == 2:   # giáo viên vừa bật công tắc giữa lúc chương trình đang chạy
                CFG['update_check'] = True
            elif len(calls) >= 3:
                raise Stop()

        updater.time.sleep = fake_sleep
        updater.update_check_once = lambda: checked.append(1)
        try:
            with self.assertRaises(Stop):
                updater.update_loop()
        finally:
            updater.time.sleep, updater.update_check_once = orig_sleep, orig_once
            CFG['update_check'], CFG['update_repo'] = orig_check, orig_repo
        # Sau sleep(8) vòng lặp chỉ ngủ từng đoạn ngắn (không ngủ nguyên 6 giờ một lần)
        self.assertTrue(all(s <= 30 for s in calls[1:]))
        # Bật công tắc xong là được kiểm tra ngay ở vòng kế tiếp, không phải chờ UPDATE_EVERY
        self.assertEqual(checked, [1])


if __name__ == '__main__':
    unittest.main()
