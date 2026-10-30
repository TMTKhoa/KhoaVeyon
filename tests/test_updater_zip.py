# -*- coding: utf-8 -*-
"""Cập nhật thủ công bằng 1 file zip: chỉ nhận bản mới hơn, giữ nguyên data/ và KhoaVeyonAgent.cfg."""
import io
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def build_zip(version):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.write(os.path.join(ROOT, 'KhoaVeyon.py'), 'KhoaVeyon-main/KhoaVeyon.py')
        for dp, _d, fn in os.walk(os.path.join(ROOT, 'kv')):
            for f in fn:
                if f.endswith('.py'):
                    full = os.path.join(dp, f)
                    rel = os.path.relpath(full, os.path.join(ROOT, 'kv'))
                    if rel == 'paths.py':
                        with open(full, encoding='utf-8') as fh:
                            txt = fh.read().replace("VERSION = '%s'" % __import__('kv.paths').paths.VERSION, "VERSION = '%s'" % version)
                        z.writestr('KhoaVeyon-main/kv/paths.py', txt)
                    else:
                        z.write(full, 'KhoaVeyon-main/kv/' + rel)
        z.writestr('KhoaVeyon-main/payload/KhoaVeyonAgent.cfg', 'OVERWRITTEN')
    return buf.getvalue()


class LocalZip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, 'payload'))
        os.makedirs(os.path.join(self.tmp, 'data'))
        with open(os.path.join(self.tmp, 'payload', 'KhoaVeyonAgent.cfg'), 'w') as f:
            f.write('MYKEY')
        with open(os.path.join(self.tmp, 'data', 'config.json'), 'w') as f:
            f.write('MYDATA')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_newer_zip_updates_and_keeps_data_and_agent_cfg(self):
        from kv import updater
        info, files = updater.apply_local_zip(build_zip('99.0.0'), 'KhoaVeyon-99.0.0.zip', self.tmp)
        self.assertEqual(info['latest'], '99.0.0')
        self.assertTrue(files)
        with open(os.path.join(self.tmp, 'payload', 'KhoaVeyonAgent.cfg')) as f:
            self.assertEqual(f.read(), 'MYKEY')
        with open(os.path.join(self.tmp, 'data', 'config.json')) as f:
            self.assertEqual(f.read(), 'MYDATA')

    def test_same_or_older_zip_rejected_and_nothing_changed(self):
        from kv import updater
        from kv.runtime import ApiError
        with self.assertRaises(ApiError):
            updater.apply_local_zip(build_zip(updater.VERSION), 'same.zip', self.tmp)
        self.assertFalse(os.path.isdir(os.path.join(self.tmp, 'kv')))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, 'update', 'same.zip')))

    def test_non_zip_and_garbage_rejected(self):
        from kv import updater
        from kv.runtime import ApiError
        with self.assertRaises(ApiError):
            updater.apply_local_zip(b'x', 'a.exe', self.tmp)
        with self.assertRaises(ApiError):
            updater.apply_local_zip(b'not a zip', 'a.zip', self.tmp)


if __name__ == '__main__':
    unittest.main()
