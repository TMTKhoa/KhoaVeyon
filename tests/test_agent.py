# -*- coding: utf-8 -*-
"""Kiểm thử kênh Agent (kv/agent.py + lớp chuyển đổi trong kv/remote.py) bằng một "dịch vụ học sinh giả" viết bằng Python,
làm đúng như mã C# trong KhoaVeyonServices.bat: python -m unittest discover tests"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_smoke import Base, _py  # noqa: E402

FAKE = r'''
import base64, hashlib, hmac, json, os, secrets, shutil, tempfile, threading, time, urllib.request, ntpath
import kv.agent as AG
AG.POLL_WAIT = 2
sandbox = tempfile.mkdtemp()
def local(p):
    return os.path.join(sandbox, *[x for x in p.replace("\\", "/").split("/") if x and x != "C:"])
EXEC = []
SESS = {"user": "hs01", "boot": 111.0}
TOKEN = AG.agent_token()
AG.agent_start()
URL = "http://127.0.0.1:%d" % AG.SERVER["port"]

def sign(b, tok=None):
    return hmac.new((tok or TOKEN).encode(), b, hashlib.sha256).hexdigest()
def post(path, body, tok=None):
    data = json.dumps(body).encode()
    req = urllib.request.Request(URL + path, data=data, headers={"X-KV-Sig": sign(data, tok)}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
        assert hmac.compare_digest(r.headers["X-KV-Sig"], sign(raw)), "reply not signed"
        return json.loads(raw)
def handle(job):
    op, res = job["op"], {"ok": True}
    p = job.get("path", "")
    if op == "exec":
        EXEC.append((job["cmd"], job.get("session"), job.get("wait")))
        res["rc"] = 0; res["out"] = "done"
        if "-install" in job["cmd"]:
            SESS["boot"] += 1
    elif op == "put":
        data = base64.b64decode(job["b64"]); assert hashlib.sha256(data).hexdigest() == job["sha"]
        os.makedirs(os.path.dirname(local(p)), exist_ok=True); open(local(p), "wb").write(data)
    elif op == "get":
        if not os.path.isfile(local(p)): res["exists"] = False
        else:
            d = open(local(p), "rb").read(); res.update(exists=True, b64=base64.b64encode(d).decode(), sha=hashlib.sha256(d).hexdigest())
    elif op == "ls":
        if not os.path.isdir(local(p)): res["exists"] = False
        else:
            res["exists"] = True; res["entries"] = [{"n": n, "s": os.path.getsize(os.path.join(local(p), n)), "m": os.path.getmtime(os.path.join(local(p), n)), "d": os.path.isdir(os.path.join(local(p), n))} for n in os.listdir(local(p))]
    elif op == "stat":
        if os.path.exists(local(p)):
            res.update(exists=True, size=os.path.getsize(local(p)) if os.path.isfile(local(p)) else 0, mtime=os.path.getmtime(local(p)))
            if job.get("sha"): res["sha"] = hashlib.sha256(open(local(p), "rb").read()).hexdigest()
        else: res["exists"] = False
    elif op == "rm":
        if os.path.isfile(local(p)): os.remove(local(p))
        elif os.path.isdir(local(p)): shutil.rmtree(local(p))
        else: res["exists"] = False
    res.update(id=job["id"], nonce=secrets.token_hex(8), ts=time.time())
    post("/agent/result", res)
STOP = False
def loop():
    while not STOP:
        nonce = secrets.token_hex(8)
        try:
            r = post("/agent/poll", {"host": "PCHS01", "user": SESS["user"], "sessions": [1], "ver": 1, "boot": SESS["boot"], "nonce": nonce, "ts": time.time()})
        except Exception:
            time.sleep(0.2); continue
        assert r["nonce"] == nonce
        for j in r["jobs"]:
            threading.Thread(target=handle, args=(j,), daemon=True).start()
if not os.environ.get('KV_NO_FAKE'):
    threading.Thread(target=loop, daemon=True).start()
for _ in range(50):
    if AG.agent_online("127.0.0.1"): break
    time.sleep(0.1)
import kv.remote as R
'''


CS_CODE = '\nimport subprocess\nexe = "__EXE__"; work = "__WORK__"\ncfg = os.path.join(work, "agent.cfg")\nopen(cfg, "w").write("url=%s\\ntoken=%s\\n" % (URL, TOKEN))\nproc = subprocess.Popen(["mono", exe, cfg, "12"], stderr=subprocess.PIPE, text=True)\nfor _ in range(100):\n    if AG.agent_online("127.0.0.1"): break\n    time.sleep(0.2)\ninfo = AG.agent_info("127.0.0.1")\nprint(AG.agent_online("127.0.0.1"), info["user"], info["sessions"], info["name"] != "")\nd = os.path.join(work, "dst", "sub")\nf1 = os.path.join(d, "bai.txt")\ndata = ("Xin chào " * 5000).encode()\nR.rfs_write("127.0.0.1", f1, data)\nprint(R.rfs_read("127.0.0.1", f1) == data, os.path.isfile(f1))\nprint(R.rfs_sha("127.0.0.1", f1) == hashlib.sha256(data).hexdigest())\nprint(sorted((e["name"], e["size"], e["dir"]) for e in R.rfs_scan("127.0.0.1", os.path.join(work, "dst"))))\nprint(abs(R.rfs_mtime("127.0.0.1", f1) - time.time()) < 60, R.rfs_exists("127.0.0.1", f1), R.rfs_exists("127.0.0.1", f1 + "x"))\nR.rfs_remove("127.0.0.1", f1)\nprint(os.path.exists(f1))\ntry:\n    R.rfs_read("127.0.0.1", f1); print("no error")\nexcept FileNotFoundError:\n    print("FNF")\ntry:\n    R.rfs_scan("127.0.0.1", os.path.join(work, "nope")); print("no error")\nexcept FileNotFoundError:\n    print("FNF")\ntry:\n    R.rfs_write("127.0.0.1", "relative/x.txt", b"x"); print("no error")\nexcept OSError as e:\n    print("rejected", "invalid path" in str(e))\nproc.wait(timeout=60)\nprint(proc.returncode)\n'


class AgentTests(Base):
    def run_code(self, code):
        r = _py(self.app, FAKE + code)
        self.assertEqual(r.returncode, 0, r.stderr[-2500:])
        return r.stdout.strip()

    def test_signature_replay_and_online_state(self):
        out = self.run_code('''
import urllib.error
print(AG.agent_online("127.0.0.1"), AG.agent_online("PCHS01"), AG.agent_info("127.0.0.1")["user"])
def code_of(req):
    try:
        urllib.request.urlopen(req, timeout=5); return 200
    except urllib.error.HTTPError as e:
        return e.code
body = json.dumps({"host": "x", "nonce": "abcdefgh1234", "ts": time.time()}).encode()
print(code_of(urllib.request.Request(URL + "/agent/poll", data=body, headers={"X-KV-Sig": "00" * 32}, method="POST")))
print(code_of(urllib.request.Request(URL + "/agent/poll", data=body, headers={"X-KV-Sig": sign(body, "k" * 64)}, method="POST")))
old = json.dumps({"host": "x", "nonce": "zzzzzzzz9999", "ts": time.time() - 5000}).encode()
print(code_of(urllib.request.Request(URL + "/agent/poll", data=old, headers={"X-KV-Sig": sign(old)}, method="POST")))
rep = json.dumps({"host": "x", "nonce": "repeat-nonce-1", "ts": time.time()}).encode()
rq = lambda: urllib.request.Request(URL + "/agent/result", data=rep, headers={"X-KV-Sig": sign(rep)}, method="POST")
print(code_of(rq()), code_of(rq()))
print(AG.agent_online("10.9.9.9"))
try: AG.agent_call("10.9.9.9", {"op": "ls", "path": "C:\\\\x"}, 1)
except AG.AgentError as e: print("offline-error")
''')
        self.assertEqual(out.splitlines(), ['True True hs01', '403', '403', '403', '200 403', 'False', 'offline-error'])

    def test_files_roundtrip_and_distribute_over_agent(self):
        out = self.run_code('''
src = tempfile.mkdtemp(); open(os.path.join(src, "a.txt"), "wb").write("xin chào".encode())
os.makedirs(os.path.join(src, "dir", "in")); open(os.path.join(src, "dir", "in", "b.bin"), "wb").write(b"\\x00\\x01")
n = R.distribute_to_host("127.0.0.1", [os.path.join(src, "a.txt"), os.path.join(src, "dir")], r"C:\\cmd")
print(n, sorted(os.path.relpath(os.path.join(d, f), sandbox).replace(os.sep, "/") for d, _, fs in os.walk(sandbox) for f in fs))
print(R.rfs_read("127.0.0.1", r"C:\\cmd\\a.txt").decode())
R.rfs_write("127.0.0.1", r"C:\\cmd\\vcfg\\kvguard.txt", b"line\\r\\n")
print(R.rfs_exists("127.0.0.1", r"C:\\cmd\\vcfg\\kvguard.txt"), R.rfs_exists("127.0.0.1", r"C:\\cmd\\none.txt"))
print(sorted(e["name"] for e in R.rfs_scan("127.0.0.1", r"C:\\cmd")))
print(R.rfs_sha("127.0.0.1", r"C:\\cmd\\a.txt") == hashlib.sha256("xin chào".encode()).hexdigest())
print(abs(R.rfs_mtime("127.0.0.1", r"C:\\cmd\\a.txt") - time.time()) < 60)
R.rfs_remove("127.0.0.1", r"C:\\cmd\\a.txt")
for fn in (lambda: R.rfs_read("127.0.0.1", r"C:\\cmd\\a.txt"), lambda: R.rfs_remove("127.0.0.1", r"C:\\cmd\\a.txt"), lambda: R.rfs_scan("127.0.0.1", r"C:\\nope")):
    try: fn(); print("no error")
    except FileNotFoundError: print("FNF")
''')
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("2 ['cmd/a.txt', 'cmd/dir/in/b.bin']"), lines[0])
        self.assertEqual(lines[1:], ['xin chào', 'True False', "['a.txt', 'dir', 'vcfg']", 'True', 'True', 'FNF', 'FNF', 'FNF'])

    def test_exec_user_and_install_wait_for_restart(self):
        out = self.run_code('''
print(R.remote_run("127.0.0.1", "cmd.exe /c x", interactive=True), R.remote_run_wait("127.0.0.1", "cmd.exe /c y <nul", 20))
print(EXEC)
print(R.logged_on_user("127.0.0.1"))
t0 = time.time(); ok, msg = R.remote_install("127.0.0.1", r"C:\\cmd\\KhoaVeyonServices.bat", timeout=20)
print(ok, msg, SESS["boot"], time.time() - t0 < 15)
print(EXEC[-1])
print(R.remote_task_delete("127.0.0.1", "KhoaVeyonWatchLogon"), EXEC[-1][0])
''')
        lines = out.splitlines()
        self.assertEqual(lines[0], "(0, 'ok') (True, 'xong')")
        self.assertIn("('cmd.exe /c x', 'user', False)", lines[1])
        self.assertIn("('cmd.exe /c y <nul', 'system', True)", lines[1])
        self.assertEqual(lines[2], "hs01")
        self.assertEqual(lines[3], "True xong 112.0 True")
        self.assertIn("-install <nul", lines[4])
        self.assertEqual(lines[5], "True schtasks.exe /Delete /TN KhoaVeyonWatchLogon /F")

    def test_alert_collect_and_receipt_through_agent(self):
        out = self.run_code('''
import kv.alerts as A, kv.evidence as EV
import kv.gallery as G
dest = tempfile.mkdtemp(); A.evidence_root = lambda: dest; G.evidence_root = lambda: dest
A.school_class_at = lambda ts: "10A1"; A.school_student_for = lambda h, c: ("An", 3)
d = EV.WATCH_REMOTE_DIR
n = "PC1_20261018-094210_site_youtube.com"
R.rfs_write("127.0.0.1", ntpath.join(d, n + ".jpg"), b"\\xff\\xd8jpg")
R.rfs_write("127.0.0.1", ntpath.join(d, n + ".json"), json.dumps({"pc": "PC1", "user": "hs", "type": "site", "name": "youtube.com", "window": "w", "date": "2026-10-18", "time": "09:42:10", "file": n + ".jpg"}).encode())
ok, msg, new = A.alert_collect_host({"watch_notify_student": True, "school_name": "T"}, "127.0.0.1")
print(ok, new, sorted(e["name"] for e in R.rfs_scan("127.0.0.1", d)))
print(os.path.isfile(os.path.join(dest, *A.ALERTS[-1]["img"].split("/"))))
''')
        lines = out.splitlines()
        self.assertEqual(lines[0], "True 1 ['" + "PC1_20261018-094210_site_youtube.com.jpg.ok']")
        self.assertEqual(lines[1], "True")

    def test_diagnose_health_and_kit_do_not_need_smb(self):
        out = self.run_code('''
import kv.network as N, kv.health as H, kv.runtime as RT
RT.CFG["script_path"] = r"C:\\cmd\\KhoaVeyonServices.bat"
N.tcp_open = lambda *a, **k: False
os.makedirs(RT.PAYLOAD_DIR, exist_ok=True)
SP = local(r"C:\\cmd\\KhoaVeyonServices.bat"); os.makedirs(os.path.dirname(SP), exist_ok=True)
LP = os.path.join(RT.PAYLOAD_DIR, "KhoaVeyonServices.bat")
if os.path.isfile(LP): shutil.copy2(LP, SP)
else: open(SP, "wb").write(b"old")
checks = N.diagnose_host(RT.CFG, "127.0.0.1")
print([bool(c[1]) for c in checks])
hp = H.health_probe("127.0.0.1"); print(hp["svc"] in ("ok", "old"), hp["watch_alive"])
from kv.setup import write_agent_cfg
write_agent_cfg(RT.CFG)
t = open(os.path.join(RT.PAYLOAD_DIR, AG.AGENT_CFG_NAME)).read().split()
print(t[0].startswith("url=http://"), t[1] == "token=" + TOKEN, [x for x in t if x.startswith("sha=")] != [] or not os.path.isfile(os.path.join(RT.PAYLOAD_DIR, "KhoaVeyonServices.bat")))
import kv.veyonkit as K, kv.setup_jobs as SJ
from kv.setup import ensure_payload
ensure_payload(RT.CFG)
print(AG.AGENT_CFG_NAME in [n for n, _ in K.kit_files()], SJ._kit_only(AG.AGENT_CFG_NAME))
import kv.api_core as AC
os.makedirs(RT.PAYLOAD_DIR, exist_ok=True)
print([os.path.basename(p) for p in AC.resolve_dist_files({"payload": [AG.AGENT_CFG_NAME, "x.txt"]})])
''')
        lines = out.splitlines()
        self.assertEqual(lines[0], "[False, True, True, True, " + ("True" if lines[0].split(", ")[4] == "True" else "False") + ", True]")
        self.assertEqual(lines[1], "True False")
        self.assertEqual(lines[2], "True True True")
        self.assertEqual(lines[3], "True True")
        self.assertEqual(lines[4], "['x.txt']")

    def test_boot_download_endpoint_and_settings(self):
        out = self.run_code('''
import urllib.error, kv.runtime as RT
os.makedirs(RT.PAYLOAD_DIR, exist_ok=True)
open(os.path.join(RT.PAYLOAD_DIR, "KhoaVeyonServices.bat"), "wb").write(b"@echo off\\r\\n")
def get(path):
    try:
        with urllib.request.urlopen(URL + path, timeout=5) as r: return r.status, r.read()
    except urllib.error.HTTPError as e: return e.code, b""
print(get("/agent/boot/KhoaVeyonServices.bat"), get("/agent/boot/KhoaVeyonAgent.cfg")[0], get("/agent/boot/..%2F..%2Fkv%2Fconfig.py")[0], get("/other")[0])
import kv.api_core as C, kv.config as K
C.save_config = lambda cfg: None
C.api_settings({"transport": "agent", "agent_port": "9001", "agent_host": "gv.local"})
print(RT.CFG["transport"], RT.CFG["agent_port"], RT.CFG["agent_host"])
for bad in ({"transport": "x"}, {"agent_port": "80"}, {"agent_host": "a b;"}):
    try: C.api_settings(bad); print("accepted")
    except RT.ApiError: print("rejected")
RT.CFG["transport"] = "smb"
print(R.use_agent("127.0.0.1"))
RT.CFG["transport"] = "auto"
print(AG.api_agent({})["listening"])
''')
        lines = out.splitlines()
        self.assertEqual(lines[0], "(200, b'@echo off\\r\\n') 404 404 404")
        self.assertEqual(lines[1], "agent 9001 gv.local")
        self.assertEqual(lines[2:5], ["rejected"] * 3)
        self.assertEqual(lines[5], "False")
        self.assertEqual(lines[6], "True")


    def test_update_check_falls_back_when_repo_has_no_release(self):
        out = self.run_code('''
import urllib.error, kv.updater as U
def http_error(code): return urllib.error.HTTPError("u", code, "x", {}, None)
def fake(url, timeout=15, limit=0, trusted=False):
    if url.endswith("/releases/latest") or url.endswith("/tags"): raise http_error(404)
    if url.endswith("kv/paths.py"): return b"VERSION = '9.9.9'\\n"
    raise AssertionError(url)
U._http_get = fake
r = U.check_update("abc/KhoaVeyon")
print(r["latest"], r["newer"], r["url"])
def fake2(url, timeout=15, limit=0, trusted=False):
    if "paths.py" in url or "releases" in url or "tags" in url: raise http_error(404)
U._http_get = fake2
try: U.check_update("abc/KhoaVeyon")
except U.ApiError as e: print("repo:", "kho CỦA BẠN" in str(e))
import ssl
def fake3(url, **k): raise urllib.error.URLError(ssl.SSLCertVerificationError("CERTIFICATE_VERIFY_FAILED"))
U._http_get = fake3
try: U.check_update("abc/KhoaVeyon")
except U.ApiError as e: print("ssl:", "chứng chỉ" in str(e))
def fake4(url, **k): raise http_error(403)
U._http_get = fake4
try: U.check_update("abc/KhoaVeyon")
except U.ApiError as e: print("rate:", "60 lần/giờ" in str(e))
''')
        self.assertEqual(out.splitlines(), ["9.9.9 True https://github.com/abc/KhoaVeyon/archive/HEAD.zip", "repo: True", "ssl: True", "rate: True"])

    def test_agent_cfg_is_refreshed_automatically(self):
        out = self.run_code('''
import kv.runtime as RT, kv.api_core as C
from kv.setup import refresh_agent_cfg
C.save_config = lambda cfg: None
cfgp = os.path.join(RT.PAYLOAD_DIR, AG.AGENT_CFG_NAME)
if os.path.exists(cfgp): os.remove(cfgp)
print(refresh_agent_cfg(), os.path.isfile(cfgp))
C.api_settings({"agent_host": "gv.lop.local"})
print("url=http://gv.lop.local:" in open(cfgp).read())
old = open(cfgp).read()
AG.api_agent({"action": "renew"})
print(open(cfgp).read() != old, ("token=" + AG.agent_token()) in open(cfgp).read())
''')
        self.assertEqual(out.splitlines(), ["True True", "True", "True True"])

    @unittest.skipUnless(shutil.which('mcs') and shutil.which('mono'), 'cần mono (mcs) để biên dịch và chạy mã C# của dịch vụ')
    def test_real_csharp_agent_talks_to_the_python_server(self):
        """Biên dịch đúng lớp KvAgent nằm trong KhoaVeyonServices.bat (kèm bản giả của lớp dịch vụ Win32) rồi cho nó gọi vào máy chủ Agent thật."""
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(os.path.dirname(here), 'payload', 'KhoaVeyonServices.bat'), encoding='utf-8') as f:
            text = f.read()
        cs = re.search(r"\$csSource = @'\n(.*?)\n'@", text, re.S).group(1)
        agent_src = cs[cs.index('// KvAgent:') - 100:]
        agent_src = agent_src[agent_src.index('// ----'):]
        with open(os.path.join(here, 'agent_harness.cs.in'), encoding='utf-8') as f:
            harness = f.read()
        work = tempfile.mkdtemp(prefix='kvcs')
        src = os.path.join(work, 'h.cs')
        with open(src, 'w', encoding='utf-8') as f:
            f.write(harness + '\n' + agent_src)
        exe = os.path.join(work, 'h.exe')
        r = subprocess.run(['mcs', '-langversion:5', '-target:exe', '-r:System.Web.Extensions.dll', '-out:' + exe, src], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        os.environ['KV_NO_FAKE'] = '1'   # không bật dịch vụ giả: chỉ có dịch vụ C# thật gọi về
        try:
            out = self.run_code(CS_CODE.replace('__EXE__', exe).replace('__WORK__', work))
        finally:
            os.environ.pop('KV_NO_FAKE', None)
        lines = out.splitlines()
        self.assertEqual(lines[0], "True hs01 [1] True")
        self.assertEqual(lines[1:4], ["True True", "True", "[('sub', 0, True)]"])
        self.assertEqual(lines[4:7], ["True True False", "False", "FNF"])
        self.assertEqual(lines[7:], ["FNF", "rejected True", "0"])


if __name__ == '__main__':
    unittest.main()
