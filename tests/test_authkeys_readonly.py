# -*- coding: utf-8 -*-
"""Windows không cho xóa file chỉ-đọc bằng os.remove: khóa public xuất lần trước phải xóa được để xuất lại."""
import os, stat, sys, tempfile, unittest
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kv import authkeys, setup_jobs


class ReadOnlyKey(unittest.TestCase):
    def _ro_file(self, d, name='avs_public.pem'):
        p = os.path.join(d, name)
        with open(p, 'w') as f:
            f.write('KEY')
        os.chmod(p, stat.S_IREAD)
        return p

    def _windows_remove(self):
        real = os.remove

        def rm(p):  # giả lập Windows: file chỉ-đọc thì không xóa được
            if not os.access(p, os.W_OK) or not (os.stat(p).st_mode & stat.S_IWRITE):
                raise PermissionError(13, 'Access is denied', p)
            real(p)
        return mock.patch('os.remove', rm)

    def test_force_remove_readonly(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._ro_file(d)
            with self._windows_remove():
                with self.assertRaises(PermissionError):
                    os.remove(p)
                self.assertTrue(authkeys.force_remove(p))
            self.assertFalse(os.path.exists(p))

    def test_force_remove_missing(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(authkeys.force_remove(os.path.join(d, 'none.pem')))

    def test_kit_copy_key_overwrites_readonly_payload(self):
        with tempfile.TemporaryDirectory() as d:
            ak, pay = os.path.join(d, 'ak'), os.path.join(d, 'payload')
            os.makedirs(ak); os.makedirs(pay)
            with open(os.path.join(ak, 'current.txt'), 'w') as f:
                f.write('avs')
            src = os.path.join(ak, 'avs_public.pem')
            with open(src, 'w') as f:
                f.write('NEW')
            self._ro_file(pay)
            with mock.patch.object(setup_jobs, 'PAYLOAD_DIR', pay), mock.patch('kv.authkeys.authkeys_dir', lambda: ak), \
                    self._windows_remove():
                self.assertEqual(setup_jobs.kit_copy_key(), 'avs_public.pem')
            with open(os.path.join(pay, 'avs_public.pem')) as f:
                self.assertEqual(f.read(), 'NEW')

    def test_client_script_uses_forced_delete(self):
        src = open(os.path.join(os.path.dirname(authkeys.__file__), 'authkeys.py'), encoding='utf-8').read()
        self.assertNotIn("'del \"%s\" >nul", src)
        self.assertGreaterEqual(src.count('del /f /q'), 3)


if __name__ == '__main__':
    unittest.main()
