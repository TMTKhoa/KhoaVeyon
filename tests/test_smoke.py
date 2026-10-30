# -*- coding: utf-8 -*-
"""Kiểm thử nhanh, không cần Windows hay Veyon: python -m unittest discover tests

Mỗi lần chạy copy chương trình sang thư mục tạm (không có data/lists/payload của bạn) rồi kiểm tra ở đó,
nên không làm đổi dữ liệu thật.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = shutil.ignore_patterns('data', 'runtime', 'tests', '__pycache__', '*.pyc', 'payload', 'lists')


def _py(cwd, code):
    return subprocess.run([sys.executable, '-c', code], cwd=cwd, capture_output=True, text=True, timeout=60,
                          env=dict(os.environ, KHOAVEYON_NO_DIALOG='1'))


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix='kvtest-')
        cls.app = os.path.join(cls.tmp, 'app')
        shutil.copytree(ROOT, cls.app, ignore=SKIP)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


class ImportTests(Base):
    def test_every_module_imports_alone(self):
        """Mỗi module nhập được trong một tiến trình mới (không phụ thuộc thứ tự nhập, không vòng nhập)."""
        names = sorted(f[:-3] for f in os.listdir(os.path.join(self.app, 'kv')) if f.endswith('.py') and f != '__init__.py')
        self.assertGreater(len(names), 30)
        for n in names:
            r = _py(self.app, 'import kv.%s' % n)
            self.assertEqual(r.returncode, 0, '%s: %s' % (n, r.stderr[-400:]))

    def test_openpyxl_is_lazy(self):
        r = _py(self.app, 'import sys, kv.app; print("openpyxl" in sys.modules)')
        self.assertEqual(r.stdout.strip(), 'False', r.stderr)

    def test_lazy_authkeys_import(self):
        r = _py(self.app, 'import kv.vcfg as v; from kv.authkeys import authkeys_prepare_master; print(callable(v._op_authkeys))')
        self.assertEqual(r.stdout.strip(), 'True', r.stderr)

    def test_routes_are_callable(self):
        code = ('from kv.routes import GET_ROUTES, POST_ROUTES\n'
                'bad=[k for d in (GET_ROUTES, POST_ROUTES) for k,v in d.items() if not callable(v) or not k.startswith("/api/")]\n'
                'print(len(GET_ROUTES), len(POST_ROUTES), bad)')
        r = _py(self.app, code)
        self.assertRegex(r.stdout.strip(), r'^\d+ \d+ \[\]$', r.stderr)


class ScriptTests(Base):
    def test_scripts_load_with_unix_newlines(self):
        code = ('from kv.paths import load_script\n'
                'import json\n'
                'names = ["student-setup.bat", "cmdlock.bat", "kvshot.ps1", "KhoaVeyonWatch.ps1", "kvseat.ps1"]\n'
                'print(json.dumps({n: [len(load_script(n)), "\\r" in load_script(n)] for n in names}))')
        r = _py(self.app, code)
        info = json.loads(r.stdout)
        self.assertEqual(len(info), 5)
        for name, (size, has_cr) in info.items():
            self.assertGreater(size, 300, name)
            self.assertFalse(has_cr, name)


class WebFilesTests(Base):
    def test_index_references_exist(self):
        with open(os.path.join(self.app, 'web', 'index.html'), encoding='utf-8') as f:
            html = f.read()
        refs = re.findall(r'(?:href|src)="/((?:css|js|assets)/[^"]+)"', html)
        self.assertGreater(len(refs), 20)
        for r in refs:
            self.assertTrue(os.path.isfile(os.path.join(self.app, 'web', *r.split('/'))), r)
        self.assertEqual(html.count("'__TOKEN__'"), 1)


class ServerTests(Base):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.p = subprocess.Popen([sys.executable, 'KhoaVeyon.py', '--no-browser'], cwd=cls.app,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        line = cls.p.stdout.readline().strip()
        m = re.match(r'http://127\.0\.0\.1:(\d+)/\?t=(.+)', line)
        if not m:
            cls.p.kill()
            raise RuntimeError('Không khởi động được: %r %s' % (line, cls.p.stderr.read()[:500]))
        cls.port, cls.tok = int(m.group(1)), m.group(2)

    @classmethod
    def tearDownClass(cls):
        cls.p.terminate()
        try:
            cls.p.wait(5)
        except Exception:  # noqa
            cls.p.kill()
        cls.p.stdout.close()
        cls.p.stderr.close()
        super().tearDownClass()

    def get(self, path, token=True, host=None):
        h = {'X-Token': self.tok} if token else {}
        if host:
            h['Host'] = host
        req = urllib.request.Request('http://127.0.0.1:%d%s' % (self.port, path), headers=h)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.headers.get('Content-Type', ''), r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get('Content-Type', ''), e.read()

    def test_page_needs_token_and_injects_it(self):
        self.assertEqual(self.get('/', token=False)[0], 403)
        s, ct, body = self.get('/?t=' + self.tok, token=False)
        self.assertEqual(s, 200)
        self.assertIn("const TOKEN = '%s'" % self.tok, body.decode('utf-8'))

    def test_static_assets(self):
        for path, ctype in (('/css/01-base.css', 'text/css'), ('/js/01-core.js', 'javascript'), ('/assets/icon.svg', 'svg'),
                            ('/favicon.ico', 'icon')):
            s, ct, _ = self.get(path, token=False)
            self.assertEqual(s, 200, path)
            self.assertIn(ctype, ct, path)

    def test_static_blocks_other_files(self):
        for path in ('/js/../kv/app.py', '/js/app.py', '/css/', '/js/', '/assets/../../KhoaVeyon.py', '/kv/app.py'):
            self.assertEqual(self.get(path, token=False)[0], 404, path)

    def test_api_needs_token_and_host(self):
        self.assertEqual(self.get('/api/state', token=False)[0], 403)
        self.assertEqual(self.get('/api/state', host='evil.example')[0], 403)
        s, ct, body = self.get('/api/state')
        self.assertEqual(s, 200)
        self.assertIn('cfg', json.loads(body))

    def test_every_get_route_answers(self):
        from_routes = _py(self.app, 'from kv.routes import GET_ROUTES; print(" ".join(GET_ROUTES))').stdout.split()
        self.assertGreater(len(from_routes), 10)
        for path in from_routes:
            s, _, body = self.get(path)
            self.assertIn(s, (200, 400), '%s -> %s %s' % (path, s, body[:200]))
            json.loads(body)

    def post(self, path, body):
        req = urllib.request.Request('http://127.0.0.1:%d%s' % (self.port, path), data=json.dumps(body).encode('utf-8'),
                                     headers={'X-Token': self.tok, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_evidence_images_need_the_pin_when_one_is_set(self):
        d = os.path.join(self.app, 'data', 'evidence', 'PC1')
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, 'a.jpg'), 'wb') as f:
            f.write(b'\xff\xd8jpeg')
        url = '/evidence/PC1/a.jpg?t=' + self.tok
        self.assertEqual(self.get(url, token=False)[0], 200)
        self.assertEqual(self.post('/api/privacy_pin', {'action': 'set', 'new_pin': 'abcd'})[0], 200)
        self.post('/api/privacy_pin', {'action': 'lock'})
        self.assertEqual(self.get(url, token=False)[0], 403)
        self.assertEqual(self.post('/api/privacy_pin', {'action': 'unlock', 'pin': 'sai'})[0], 400)
        self.assertEqual(self.get(url, token=False)[0], 403)
        self.assertEqual(self.post('/api/privacy_pin', {'action': 'unlock', 'pin': 'abcd'})[0], 200)
        self.assertEqual(self.get(url, token=False)[0], 200)
        with open(os.path.join(self.app, 'data', 'privacy.json'), encoding='utf-8') as f:
            self.assertNotIn('abcd', f.read())   # mã chỉ lưu dạng băm
        self.assertEqual(self.post('/api/privacy_pin', {'action': 'clear', 'pin': 'abcd'})[0], 200)
        self.assertEqual(self.get(url, token=False)[0], 200)

    def test_list_variant_api_roundtrip(self):
        s, r = self.post('/api/list_variant_save', {'kind': 'allow', 'name': 'Kiểm tra Văn', 'rows': [['van.edu.vn', 'trang thi'], ['', '']]})
        self.assertEqual((s, r['count'], r['variants']), (200, 1, ['Kiểm tra Văn']))
        s, _, body = self.get('/api/list_variant?kind=allow&name=' + urllib.parse.quote('Kiểm tra Văn'))
        self.assertEqual((s, json.loads(body)['rows']), (200, [['van.edu.vn', 'trang thi']]))
        s, _, body = self.get('/api/list?kind=allow')
        self.assertIn('Kiểm tra Văn', json.loads(body)['variants'])
        s, r = self.post('/api/list_variant_delete', {'kind': 'allow', 'name': 'Kiểm tra Văn'})
        self.assertEqual((s, r['variants']), (200, []))
        self.assertEqual(self.get('/api/list_variant?kind=allow&name=..%2F..%2Fx')[0], 400)

    def test_unknown_route(self):
        self.assertEqual(self.get('/api/khong-co')[0], 404)


class FeatureTests(Base):
    def test_exam_start_and_end_run_steps_in_order(self):
        code = (
            'import time, tempfile, os, kv.exam as X\n'
            'X.EXAM_FILE = os.path.join(tempfile.mkdtemp(), "e.json")\n'
            'c = []\n'
            'X.job_shot = lambda h, t="": c.append("shot")\n'
            'X.job_action = lambda k, h: c.append(k)\n'
            'X.job_watch = lambda s, h: c.append("watch-" + s)\n'
            'X.job_announce = lambda *a: c.append("ann-clear" if a[4] else "ann")\n'
            'X.job_verify = lambda h, f: c.append("verify")\n'
            'X.EXAM_VERIFY_DELAY = 0\n'
            'X.tcp_open = lambda h, p, t=1: True\n'
            'X.SCHOOL["classes"] = {"10A1": {}}\n'
            'X.api_exam_start({"hosts": ["A"], "cls": "10A1"}); time.sleep(0.4)\n'
            'X.api_exam_end(); time.sleep(0.4)\n'
            'print(",".join(c), X.exam_view()["active"])')
        r = _py(self.app, code)
        self.assertEqual(r.stdout.strip(), 'shot,blockai,allowpage,watch-start,ann,verify,ann-clear,watch-stop,allowall,allowai False', r.stderr)

    def test_health_levels(self):
        code = ('from kv.health import health_of\n'
                'ok = {"online": True, "veyon": True, "smb": True, "svc": "ok"}\n'
                'print(health_of({"online": False})[0], health_of(ok)[0], health_of(dict(ok, svc="old"))[0], '
                'health_of(dict(ok, svc="none"))[0], health_of(dict(ok, watching=True, watch_alive=False))[0], '
                'health_of(dict(ok, ai="open"), {"active": True, "steps": {"blockai": True}})[0])')
        r = _py(self.app, code)
        self.assertEqual(r.stdout.strip(), 'off green yellow red red red', r.stderr)

    def test_report_html_escapes_and_names_students(self):
        code = ('import kv.reports as R\n'
                'ep = {"host": "PC1", "type": "ai", "name": "x.com", "user": "", "window": "<script>", "date": "2026-10-18", "time": "08:00:00", "first_ts": 1, "last_ts": 1, "shots": 1, "student": "An <b>", "cls": "10A1", "seat": 2, "imgs": []}\n'
                'rep = {"label": "Hôm nay", "generated": "t", "episodes": 1, "shots": 1, "machines": 1, "gap": 60, "by_item": [], "_episodes": [ep],\n'
                '       "by_student": [{"student": "An <b>", "cls": "10A1", "hosts": ["PC1"], "count": 1, "shots": 1, "last": "08:00", "top": []}]}\n'
                'import tempfile, os\n'
                'p = os.path.join(tempfile.mkdtemp(), "r.html"); R.report_write_html(rep, p, {})\n'
                'h = open(p, encoding="utf-8").read()\n'
                'print("<script>" not in h, "An &lt;b&gt;" in h)')
        r = _py(self.app, code)
        self.assertEqual(r.stdout.strip(), 'True True', r.stderr)


class MigrationTests(Base):
    def test_launcher_reports_when_kv_is_missing(self):
        """Máy cập nhật bằng bản tự cập nhật cũ (chỉ chép KhoaVeyon.py và web) phải nhận thông báo rõ ràng, không lỗi khó hiểu."""
        old = os.path.join(self.tmp, 'old-style')
        shutil.copytree(self.app, old)
        shutil.rmtree(os.path.join(old, 'kv'))
        shutil.rmtree(os.path.join(old, 'scripts'))
        code = ('import importlib.util, sys\n'
                'spec = importlib.util.spec_from_file_location("launcher", "KhoaVeyon.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n'
                'm._repair = lambda: False\n'
                'try:\n    m._load()\nexcept SystemExit as e:\n    print("EXIT", e.code)\n')
        r = _py(old, code)
        self.assertIn('EXIT 1', r.stdout, r.stderr)
        with open(os.path.join(old, 'data', 'error.log'), encoding='utf-8') as f:
            logged = f.read()
        self.assertIn('Thiếu thư mục kv', r.stderr + logged)

    def test_repair_extracts_kv_and_scripts_from_release_zip(self):
        """_repair() tải bản phát hành (giả lập) và chép kv, scripts, web; từ chối đường dẫn lạ."""
        import io
        import zipfile
        old = os.path.join(self.tmp, 'repair')
        shutil.copytree(self.app, old)
        shutil.rmtree(os.path.join(old, 'kv'))
        shutil.rmtree(os.path.join(old, 'scripts'))
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            for dp, _dn, fn in os.walk(self.app):
                for f in fn:
                    full = os.path.join(dp, f)
                    rel = os.path.relpath(full, self.app).replace(os.sep, '/')
                    if '__pycache__' not in rel:
                        z.write(full, 'KhoaVeyon-main/' + rel)
        zpath = os.path.join(self.tmp, 'release.zip')
        with open(zpath, 'wb') as f:
            f.write(buf.getvalue())
        code = ('import importlib.util, io, json, sys, urllib.request\n'
                'spec = importlib.util.spec_from_file_location("launcher", "KhoaVeyon.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n'
                'class R(io.BytesIO):\n    def __enter__(self): return self\n    def __exit__(self, *a): return False\n'
                'def fake(req, timeout=0):\n'
                '    u = req.full_url\n'
                '    if u.startswith("https://api.github.com/"): return R(json.dumps({"zipball_url": "https://codeload.github.com/x/y/zip/z"}).encode())\n'
                '    return R(open(%r, "rb").read())\n'
                'urllib.request.urlopen = fake\n'
                'print("REPAIRED", m._repair())\n'
                'from kv.app import run\nprint("IMPORT_OK")\n' % zpath)
        r = _py(old, code)
        self.assertIn('REPAIRED True', r.stdout, r.stderr)
        self.assertIn('IMPORT_OK', r.stdout, r.stderr)
        self.assertTrue(os.path.isfile(os.path.join(old, 'scripts', 'kvshot.ps1')))
        self.assertTrue(os.path.isfile(os.path.join(old, 'web', 'js', '99-boot.js')))


    def test_repair_rejects_unsafe_paths(self):
        import io
        import zipfile
        old = os.path.join(self.tmp, 'unsafe')
        shutil.copytree(self.app, old)
        shutil.rmtree(os.path.join(old, 'kv'))
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            z.writestr('KhoaVeyon-main/KhoaVeyon.py', 'x')
            z.writestr('KhoaVeyon-main/kv/app.py', 'x')
            z.writestr('KhoaVeyon-main/../evil.txt', 'x')
        zpath = os.path.join(self.tmp, 'unsafe.zip')
        with open(zpath, 'wb') as f:
            f.write(buf.getvalue())
        code = ('import importlib.util, io, json, urllib.request\n'
                'spec = importlib.util.spec_from_file_location("launcher", "KhoaVeyon.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n'
                'class R(io.BytesIO):\n    def __enter__(self): return self\n    def __exit__(self, *a): return False\n'
                'def fake(req, timeout=0):\n'
                '    if req.full_url.startswith("https://api.github.com/"): return R(json.dumps({"zipball_url": "https://codeload.github.com/x/y/zip/z"}).encode())\n'
                '    return R(open(%r, "rb").read())\n'
                'urllib.request.urlopen = fake\n'
                'print("REPAIRED", m._repair())\n' % zpath)
        r = _py(old, code)
        self.assertIn('REPAIRED False', r.stdout, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(old, 'kv')))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, 'evil.txt')))


if __name__ == '__main__':
    unittest.main()
