# -*- coding: utf-8 -*-
"""Tự cập nhật từ GitHub cũng phải cập nhật payload (Services.bat, Student.ps1) nhưng giữ KhoaVeyonAgent.cfg."""
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class UpdatePayload(unittest.TestCase):
    def test_payload_updated_cfg_kept(self):
        from kv import updater
        tmp = tempfile.mkdtemp()
        try:
            app = os.path.join(tmp, 'app')
            for rel, txt in [('payload/KhoaVeyonServices.bat', 'OLD'), ('payload/KhoaVeyonStudent.ps1', 'OLD'),
                             ('payload/KhoaVeyonAgent.cfg', 'MYKEY')]:
                p = os.path.join(app, rel)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, 'w').write(txt)
            zp = os.path.join(tmp, 'new.zip')
            with zipfile.ZipFile(zp, 'w') as z:
                for f in ('KhoaVeyon.py',):
                    z.write(os.path.join(ROOT, f), 'KhoaVeyon-main/' + f)
                for dp, _d, fn in os.walk(os.path.join(ROOT, 'kv')):
                    for f in fn:
                        if f.endswith('.py'):
                            full = os.path.join(dp, f)
                            z.write(full, 'KhoaVeyon-main/kv/' + os.path.relpath(full, os.path.join(ROOT, 'kv')))
                z.writestr('KhoaVeyon-main/payload/KhoaVeyonServices.bat', 'NEW')
                z.writestr('KhoaVeyon-main/payload/KhoaVeyonStudent.ps1', 'NEW')
                z.writestr('KhoaVeyon-main/payload/KhoaVeyonAgent.cfg', 'OVERWRITTEN')
            orig = updater._http_get
            updater._http_get = lambda *a, **k: open(zp, 'rb').read()
            try:
                files = updater.apply_update('https://github.com/x/y.zip', app_dir=app)
            finally:
                updater._http_get = orig
            rd = lambda r: open(os.path.join(app, r)).read()
            self.assertEqual(rd('payload/KhoaVeyonServices.bat'), 'NEW')
            self.assertEqual(rd('payload/KhoaVeyonStudent.ps1'), 'NEW')
            self.assertEqual(rd('payload/KhoaVeyonAgent.cfg'), 'MYKEY')
            self.assertTrue(any(f.replace('\\', '/') == 'payload/KhoaVeyonServices.bat' for f in files))
            bk = [d for d in os.listdir(os.path.join(app, 'data')) if d.startswith('backup-')]
            self.assertTrue(os.path.isfile(os.path.join(app, 'data', bk[0], 'payload', 'KhoaVeyonServices.bat')))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()


class UpdateStudentsButton(unittest.TestCase):
    def test_update_one_cases(self):
        from kv import autoupdate as au
        saved = (au.agent_online, au.health_probe, au.job_fix_service, au.sync_extra_files)
        fixed = []
        try:
            au.sync_extra_files = lambda h: []
            au.job_fix_service = lambda hs: fixed.extend(hs)
            au.agent_online = lambda h: False
            ok, msg = au.update_one('10.0.0.5')
            self.assertFalse(ok)
            au.agent_online = lambda h: True
            au.health_probe = lambda h: {'svc': 'ok'}
            self.assertEqual(au.update_one('10.0.0.5')[0], True)
            self.assertEqual(fixed, [])
            au.health_probe = lambda h: {'svc': 'old'}
            self.assertTrue(au.update_one('10.0.0.5')[0])
            self.assertEqual(fixed, ['10.0.0.5'])
            au.health_probe = lambda h: {'svc': '?'}
            self.assertFalse(au.update_one('10.0.0.6')[0])
        finally:
            au.agent_online, au.health_probe, au.job_fix_service, au.sync_extra_files = saved

    def test_api_blocked_during_exam_and_route(self):
        from kv import autoupdate as au, routes
        from kv.runtime import ApiError
        saved = au.exam_snapshot
        try:
            au.exam_snapshot = lambda: {'active': True}
            with self.assertRaises(ApiError):
                au.api_update_students({'hosts': ['10.0.0.5']})
        finally:
            au.exam_snapshot = saved
        self.assertTrue(open(os.path.join(ROOT, 'kv', 'routes.py'), encoding='utf-8').read().count('/api/update_students') >= 1)


class HostsRemoveAndMerge(unittest.TestCase):
    def test_api_hosts_prunes_removed_machine(self):
        from kv import api_lists
        from kv.runtime import CFG, CFG_LOCK
        saved = {k: CFG.get(k) for k in ('hosts', 'macs', 'host_names', 'host_auto_names')}
        orig_save = api_lists.save_config
        api_lists.save_config = lambda c: None
        try:
            with CFG_LOCK:
                CFG['hosts'] = ['10.0.0.5', '10.0.0.6']
                CFG['macs'] = {'10.0.0.5': 'AA:BB:CC:DD:EE:01', '10.0.0.6': 'AA:BB:CC:DD:EE:02'}
                CFG['host_names'] = {'10.0.0.5': 'May 5'}
                CFG['host_auto_names'] = {'10.0.0.5': 'PC5', '10.0.0.6': 'PC6'}
            r = api_lists.api_hosts({'hosts': ['10.0.0.6']})
            self.assertEqual(r['removed'], 1)
            self.assertEqual(CFG['hosts'], ['10.0.0.6'])
            self.assertNotIn('10.0.0.5', CFG['macs'])
            self.assertNotIn('10.0.0.5', CFG['host_names'])
            self.assertNotIn('10.0.0.5', CFG['host_auto_names'])
            self.assertIn('10.0.0.6', CFG['macs'])
        finally:
            api_lists.save_config = orig_save
            with CFG_LOCK:
                for k, v in saved.items():
                    CFG[k] = v

    def test_diag_page_merged_into_status(self):
        core = open(os.path.join(ROOT, 'web', 'js', '01-core.js'), encoding='utf-8').read()
        self.assertNotIn("{id:'diag'", core)
        st = open(os.path.join(ROOT, 'web', 'js', '14-status.js'), encoding='utf-8').read()
        for key in ('data-tl="dgrun"', 'data-xa="rmhost"', 'data-xa="rmsel"', 'diagExtraHtml()'):
            self.assertIn(key, st)

    def test_version_is_4_4(self):
        from kv.paths import VERSION
        self.assertTrue(VERSION.startswith('4.4.'))
