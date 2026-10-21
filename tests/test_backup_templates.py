# -*- coding: utf-8 -*-
import io, os, sys, tempfile, unittest, zipfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kv import school, templates, backup
from kv.runtime import ApiError, CFG


def tmp_xlsx(data):
    fd, p = tempfile.mkstemp(suffix='.xlsx'); os.close(fd)
    open(p, 'wb').write(data); return p


class Tpl(unittest.TestCase):
    def test_bells_default_matches(self):
        b = templates.build_bells()
        self.assertEqual(b[1], ('07:00', '07:45')); self.assertEqual(b[2], ('07:50', '08:35'))
        self.assertEqual(b[6], ('13:30', '14:15')); self.assertEqual(len(b), 10)

    def test_timetable_template_roundtrip(self):
        p = tmp_xlsx(templates.timetable_template(templates.build_bells(am='07:15')))
        try: d = school.parse_timetable_xlsx(p)
        finally: os.remove(p)
        self.assertEqual(len(d['slots']), 5)
        s = [x for x in d['slots'] if x['cls'] == '10A1' and x['day'] == 0]
        self.assertEqual(s[0]['start'], '07:15')

    def test_classes_template_roundtrip(self):
        p = tmp_xlsx(templates.classes_template())
        try: d = school.parse_classes_xlsx(p)
        finally: os.remove(p)
        self.assertEqual(sorted(d), ['10A1', '10A2']); self.assertEqual(len(d['10A1']), 3)

    def test_custom_bells_used_for_period_numbers(self):
        school.SCHOOL['bells'] = {'1': ['06:00', '06:40']}
        try:
            self.assertEqual(school.school_bells()[1], ('06:00', '06:40'))
            self.assertEqual(school.school_bells()[2], school.DEFAULT_BELLS[2])
        finally: school.SCHOOL['bells'] = {}


class Bk(unittest.TestCase):
    def test_backup_roundtrip_and_safety(self):
        data = backup.make_backup(True)
        z = zipfile.ZipFile(io.BytesIO(data)); names = z.namelist()
        self.assertIn('manifest.json', names); self.assertIn('config.json', names)
        pv = backup.preview_backup(data); self.assertTrue(pv['secrets'])
        self.assertNotIn('agent_token', json.loads(zipfile.ZipFile(io.BytesIO(backup.make_backup(False))).read('config.json')))

    def test_rejects_garbage_and_zip_slip(self):
        with self.assertRaises(ApiError): backup.preview_backup(b'not a zip')
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            z.writestr('manifest.json', json.dumps({'magic': backup.MAGIC}))
            z.writestr('lists/../../evil.xlsx', b'x')
        before = set(os.listdir('.'))
        d = tempfile.mkdtemp(); old = CFG['list_dir']; CFG['list_dir'] = d
        try: backup.restore_backup(buf.getvalue(), ['lists'])
        finally: CFG['list_dir'] = old
        self.assertEqual(os.listdir(d), ['evil.xlsx']); self.assertEqual(set(os.listdir('.')), before)
        self.assertFalse(os.path.exists(os.path.join(d, '..', 'evil.xlsx')))


if __name__ == '__main__':
    unittest.main()
