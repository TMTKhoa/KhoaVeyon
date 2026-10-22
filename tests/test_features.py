# -*- coding: utf-8 -*-
"""Kiểm thử các tính năng bản 3.8.0 và 3.9.0 (không cần Windows hay Veyon): python -m unittest discover tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_smoke import Base, _py  # noqa: E402


class Features38(Base):
    def run_code(self, code):
        r = _py(self.app, code)
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        return r.stdout.strip()

    def test_reapply_after_machine_comes_back(self):
        out = self.run_code('''
import kv.reapply as R, kv.applied as A, kv.runtime as RT
d = {}
assert R.came_back(d, "a", True) is False and R.came_back(d, "a", False) is False and R.came_back(d, "a", True) is True
RT.CFG["hosts"] = ["PC1"]
A.APPLIED.clear()
A.APPLIED["PC1"] = {"net": {"label": "x", "on": True, "ts": 2, "key": "blockall"}, "lock": {"label": "y", "on": True, "ts": 1, "key": "lockall-start"},
                    "ai": {"label": "", "on": False, "ts": 3, "key": "allowai"}}
state = {"PC1": True}; started = []
probe = lambda h, p, t: state[h]; st = lambda fn, *a: started.append(a)
R.reapply_tick(probe, st); state["PC1"] = False; R.reapply_tick(probe, st); state["PC1"] = True; R.reapply_tick(probe, st); R.reapply_tick(probe, st)
calls = []; R.job_action = lambda k, h: calls.append(k); R.logged_on_user = lambda h: "hs"
R.job_reapply("PC1", wait=1, step=0.01)
RT.CFG["reapply_on_boot"] = False; state["PC1"] = False; R.reapply_tick(probe, st); state["PC1"] = True; R.reapply_tick(probe, st)
print(started, calls, len(started))
''')
        self.assertEqual(out, "[('PC1',)] ['lockall-start', 'blockall'] 1")

    def test_verify_compares_real_state_with_commands_sent(self):
        out = self.run_code('''
import json, kv.verify as V
S = lambda **k: V.parse_state(json.dumps(dict({"fw": False, "kiosk": False, "users": []}, **k)))
E = lambda **c: {k: {"on": v[0], "key": v[1]} for k, v in c.items()}
r = lambda e, s, ai=None: {c: x for c, x, _ in V.compare(e, s, ai)}
good = S(fw=True, kiosk=True, users={"user": "u", "taskmgr": True, "restrictrun": True})
a = r(E(net=(True, "blockall"), lockdown=(True, "lockdown"), run=(True, "lockrun-start"), lock=(True, "lockall-start"), kiosk=(True, "lockapp-start"), mute=(True, "mute")), good)
bad = S(fw=False, users=[{"user": "u", "taskmgr": True, "restrictrun": False}])
b = r(E(net=(True, "blockall"), lockdown=(False, "unlock"), lock=(True, "lockall-start")), bad)
c = r(E(net=(False, "allowall"), lockdown=(True, "lockdown")), S(fw=False))
d = r(E(ai=(True, "blockai")), S(), (False, "CHƯA KHÓA AI"))
print(sorted(a.items()), sorted(b.items()), sorted(c.items()), d)
''')
        self.assertIn("('mute', 'unknown')", out)
        self.assertIn("[('lock', 'bad'), ('lockdown', 'bad'), ('net', 'bad')]", out)
        self.assertIn("[('lockdown', 'unknown'), ('net', 'ok')] {'ai': 'bad'}", out)
        self.assertTrue(out.startswith("[('kiosk', 'ok'), ('lock', 'ok'), ('lockdown', 'ok'), ('mute', 'unknown'), ('net', 'ok'), ('run', 'ok')]"), out)

    def test_list_variants_pushed_for_a_class_mode_and_restored(self):
        out = self.run_code('''
import os, tempfile, kv.auto as A, kv.runtime as RT
from kv.excel_lists import write_list, variant_file, read_list
d = tempfile.mkdtemp(); RT.CFG["list_dir"] = d
write_list(os.path.join(d, "AllowPage.xlsx"), "allow", [("main.com", "")])
write_list(os.path.join(d, variant_file("allow", "Kiểm tra Văn")), "allow", [("van.edu.vn", "")])
for bad in ({"allow": "Không có"}, {"zzz": "x"}):
    try: A.auto_clean_lists(bad); print("KHÔNG TỪ CHỐI")
    except A.ApiError: pass
A.AUTO.update(enabled=True, modes={"Thi Văn": {"start": ["allowpage"], "end": ["allowall"], "lists": A.auto_clean_lists({"allow": "Kiểm tra Văn"})}})
log = []; A.tcp_open = lambda h, p, t: True; A.job_run_key = lambda k, h: log.append(k)
def dist(hosts, files, *a): log.append([os.path.basename(f) + ":" + read_list(f)[0][0] for f in files])
A.job_dist = dist
A.job_auto_keys(A.mode_steps("Thi Văn", "start"), ["PC1"], "t"); A.job_auto_keys(A.mode_steps("Thi Văn", "end"), ["PC1"], "t")
print(log)
''')
        self.assertEqual(out, "[['AllowPage.xlsx:van.edu.vn'], 'allowpage', 'allowall', ['AllowPage.xlsx:main.com']]")

    def test_variant_names_cannot_escape_the_list_folder(self):
        out = self.run_code('''
from kv.excel_lists import variant_clean, variant_file
print([variant_clean(x) for x in ("../../etc/passwd", "C:\\\\x", "a--b", "  ", "Ôn tập 12A1")], variant_file("allow", "../x"))
''')
        self.assertEqual(out, "['etcpasswd', 'Cx', 'a-b', '', 'Ôn tập 12A1'] AllowPage--x.xlsx")

    def test_notice_validation_and_payload(self):
        out = self.run_code('''
import kv.announce as N
N.start_job = lambda fn, *a: print("job", a)
for b in ({"text": "  ", "hosts": ["A"]}, {"text": "x" * 200, "hosts": ["A"]}, {"text": "Còn 5 phút", "hosts": []}):
    try: N.api_notice(b); print("KHÔNG TỪ CHỐI")
    except N.ApiError as e: print("từ chối")
N.api_notice({"text": "Còn   5 phút", "hosts": ["A", "A"], "seconds": 999})
p = N.notice_payload("Còn 5 phút", 20)
print(p["title"], p["name"], p["seconds"], p["keep"], p["clear"])
''')
        self.assertEqual(out.splitlines()[:3], ['từ chối'] * 3)
        self.assertIn("job ('Còn 5 phút', 300, ['A'])", out)
        self.assertIn('THÔNG BÁO CỦA GIÁO VIÊN Còn 5 phút 20 False False', out)

    def test_report_trends_repeat_students_and_chronic_items(self):
        out = self.run_code('''
import time, kv.reports as R
day = lambda d: time.mktime((2026, 10, d, 9, 0, 0, 0, 0, -1))
mk = lambda h, t, n, d, s: {"host": h, "type": t, "name": n, "date": "2026-10-%02d" % d, "time": "09:00:00", "ts": day(d), "student": s, "cls": "12A1", "img": "", "file": h + n + str(d)}
ev = [mk("PC1", "site", "game.com", 5, "An"), mk("PC1", "site", "game.com", 6, "An"), mk("PC1", "site", "game.com", 7, "An"), mk("PC2", "site", "game.com", 7, "Bình"), mk("PC3", "site", "x.com", 8, "")]
t = R.report_trend(R.report_episodes(ev, 60))
print([d["count"] for d in t["by_day"]], t["repeat_students"], [(x["name"], x["days"]) for x in t["chronic_items"]], sum(w["count"] for w in t["by_weekday"]))
print(sorted(R.RANGES))
''')
        self.assertIn("[1, 1, 2, 1] [{'student': 'An', 'cls': '12A1', 'days': 3, 'count': 3}] [('game.com', 3)] 5", out)
        self.assertIn("'month'", out)

    def test_exam_runs_new_steps_in_order_and_collects_before_unlocking(self):
        out = self.run_code('''
import time, tempfile, os, kv.exam as X
X.EXAM_FILE = os.path.join(tempfile.mkdtemp(), "e.json"); X.EXAM_VERIFY_DELAY = 0
c = []
X.job_shot = lambda h, t="": c.append("shot"); X.job_action = lambda k, h: c.append(k)
X.job_watch = lambda s, h: c.append("watch-" + s); X.job_announce = lambda *a: c.append("ann-clear" if a[4] else "ann")
X.job_verify = lambda h, f: c.append("verify"); X.tcp_open = lambda h, p, t=1: True
X.job_exam_lock = lambda how, what, h: c.append("lock-%s-%s" % (how, "+".join(what)))
X.job_exam_collect = lambda h, p, s: (c.append("collect:" + ",".join(p)), "/tmp/x")[1]
X.SCHOOL["classes"] = {"10A1": {}}
X.api_exam_start({"hosts": ["A"], "cls": "10A1", "steps": {"usb": True, "print": True, "clip": True, "collect": True, "shot": False, "blockai": False}, "collect_paths": "C:\\\\BaiLam\\nC:\\\\Users\\\\{user}\\\\Documents"})
time.sleep(0.4); X.api_exam_end(); time.sleep(0.4)
print(",".join(c), X.exam_view()["collected"])
''')
        self.assertEqual(out, r"allowpage,lock-on-usb+print+clip,watch-start,ann,verify,collect:C:\BaiLam,C:\Users\{user}\Documents,ann-clear,watch-stop,allowall,lock-off-usb+print+clip /tmp/x")

    def test_exam_collect_copies_only_recent_files_and_respects_limits(self):
        out = self.run_code('''
import os, time, tempfile, kv.examlock as L
root = tempfile.mkdtemp(); share = os.path.join(root, "PC1", "BaiLam"); os.makedirs(os.path.join(share, "sub"))
home = os.path.join(root, "PC1", "Users", "hs01", "Documents"); os.makedirs(home)
new = lambda p, size=10: open(p, "wb").write(b"x" * size)
new(os.path.join(share, "bai.docx")); new(os.path.join(share, "sub", "b.txt")); new(os.path.join(share, "~$lock.docx")); new(os.path.join(share, "to.tmp"))
old = os.path.join(share, "cu.docx"); new(old); os.utime(old, (1, 1))
new(os.path.join(home, "van.docx"))
L.COLLECT_MAX_FILE = 100; new(os.path.join(share, "lon.bin"), 500)
def unc(h, p):
    import re
    return os.path.join(root, h, *[x for x in re.split(r"[\\\\/]+", p[3:]) if x]) if False else os.path.join(root, h, *[x for x in re.split(r"[\\\\/]+", p[3:]) if x])
import kv.remote as RR; RR.unc_target = unc
dest = tempfile.mkdtemp()
ok, msg = L.collect_one("PC1", [r"C:\\BaiLam", r"C:\\Users\\{user}\\Documents", r"C:\\KhongCo"], time.time() - 3600, dest, user_fn=lambda h: "LAB\\\\hs01")
got = sorted(os.path.relpath(os.path.join(d, f), dest).replace(os.sep, "/") for d, _, fs in os.walk(dest) for f in fs)
print(ok, got); print(msg)
try: L.collect_paths_clean(["D:/../x"]); print("KHÔNG TỪ CHỐI")
except L.ApiError: print("từ chối ..")
print(L.collect_paths_clean("C:\\\\a\\n\\n C:\\\\a \\nD:\\\\b"))
''')
        self.assertIn("True ['PC1/C_BaiLam/bai.docx', 'PC1/C_BaiLam/sub/b.txt', 'PC1/C_Users_hs01_Documents/van.docx']", out)
        self.assertIn('đã thu 3 file', out)
        self.assertIn('bỏ qua 2 file', out)
        self.assertIn('từ chối ..', out)
        self.assertIn("['C:\\\\a', 'D:\\\\b']", out)

    def test_pin_protects_evidence_images(self):
        out = self.run_code('''
import kv.privacy as P
P.priv_save = lambda: None
print(P.images_blocked(), P.pin_is_set())
P.api_privacy_pin({"action": "set", "new_pin": "1234"})
print(P.images_blocked())       # vừa đặt xong: còn mở một lúc
P.api_privacy_pin({"action": "lock"}); print(P.images_blocked())
for p in ("0000", ""):
    try: P.api_privacy_pin({"action": "unlock", "pin": p}); print("KHÔNG TỪ CHỐI")
    except P.ApiError as e: print("sai")
P.api_privacy_pin({"action": "unlock", "pin": "1234"}); print(P.images_blocked())
try: P.api_privacy_pin({"action": "set", "pin": "sai", "new_pin": "5678"}); print("KHÔNG TỪ CHỐI")
except P.ApiError: print("đổi mã cần mã cũ")
try: P.api_privacy_pin({"action": "set", "pin": "1234", "new_pin": "12"}); print("KHÔNG TỪ CHỐI")
except P.ApiError: print("mã ngắn bị từ chối")
P.api_privacy_pin({"action": "lock"})
for _ in range(5):
    try: P.api_privacy_pin({"action": "unlock", "pin": "x"})
    except P.ApiError: pass
try: P.api_privacy_pin({"action": "unlock", "pin": "1234"}); print("KHÔNG KHÓA TẠM")
except P.ApiError as e: print("khóa tạm:", "Thử lại sau" in str(e))
P.STATE["locked_until"] = 0
P.api_privacy_pin({"action": "clear", "pin": "1234"}); print(P.images_blocked(), P.pin_is_set())
print("1234" in str(P.PRIV))
''')
        self.assertEqual(out.splitlines(), ['False False', 'False', 'True', 'sai', 'sai', 'False', 'đổi mã cần mã cũ', 'mã ngắn bị từ chối',
                                            'khóa tạm: True', 'False False', 'False'])

    def test_evidence_route_is_locked_and_reports_refuse_images(self):
        out = self.run_code('''
import kv.privacy as P, kv.reports as R
P.priv_save = lambda: None
P.api_privacy_pin({"action": "set", "new_pin": "1234"}); P.api_privacy_pin({"action": "lock"})
try: R.api_report_export({"range": "all", "format": "html"}); print("KHÔNG TỪ CHỐI")
except R.ApiError: print("báo cáo in bị khóa")
import kv.alerts as A
print(A.api_alerts({})["privacy"]["blocked"])
''')
        self.assertEqual(out.splitlines(), ['báo cáo in bị khóa', 'True'])

    def test_retention_keeps_text_records_longer_than_images(self):
        out = self.run_code('''
import os, time, json, tempfile, kv.cleanup as C, kv.alerts as A
root = tempfile.mkdtemp(); C.evidence_root = lambda: root
C.shot_root = lambda: tempfile.mkdtemp()
os.makedirs(os.path.join(root, "PC1"))
now = time.time()
def mk(name, days):
    p = os.path.join(root, "PC1", name); open(p, "wb").write(b"j"); t = now - days * 86400; os.utime(p, (t, t))
mk("old.jpg", 40); mk("mid.jpg", 20); mk("new.jpg", 2)
A.ALERTS[:] = [{"id": i, "ts": now - d * 86400, "host": "PC1", "file": f} for i, (d, f) in enumerate([(200, "a"), (40, "b"), (2, "c")], 1)]
r = C.evidence_cleanup(14, 180)
print(sorted(os.listdir(os.path.join(root, "PC1"))), [e["file"] for e in A.ALERTS], r["images"], r["records"])
r2 = C.evidence_cleanup(30)   # cách gọi cũ: ảnh và bản ghi cùng mốc
print([e["file"] for e in A.ALERTS], C.evidence_cleanup(0, 0)["images"])
''')
        self.assertEqual(out.splitlines(), ["['new.jpg'] ['b', 'c'] 2 1", "['c'] 0"])

    def test_watch_disclosure_label_payloads(self):
        out = self.run_code('''
import kv.watch as W
a, b = W.disclose_payload(), W.disclose_payload(clear=True)
print(a["name"], a["keep"], a["clear"], b["clear"])
''')
        self.assertEqual(out, 'ĐANG GIÁM SÁT True False True')

    def test_exam_lock_batch_quotes_the_what_argument(self):
        out = self.run_code('''
import kv.examlock as L
print(L.lock_bat("C:\\\\cmd\\\\vcfg", "on", ["usb", "print"]).splitlines()[1])
''')
        self.assertEqual(out, r'powershell -NoProfile -ExecutionPolicy Bypass -File "C:\cmd\vcfg\kvexam.ps1" -Mode on -What "usb,print"')

    def test_new_settings_are_saved_with_the_right_type(self):
        out = self.run_code('''
import kv.api_core as C, kv.runtime as RT, kv.config as K
K.save_config = lambda cfg: None
C.save_config = lambda cfg: None
import kv.agent as AG; AG.save_config = lambda cfg: None   # refresh_agent_cfg có thể tạo khóa Agent
C.api_settings({"reapply_on_boot": False, "watch_disclose": False, "keep_days": "7", "keep_records_days": 90})
print(RT.CFG["reapply_on_boot"], RT.CFG["watch_disclose"], repr(RT.CFG["keep_days"]), repr(RT.CFG["keep_records_days"]))
''')
        self.assertEqual(out, "False False '7' '90'")

    def test_new_routes_and_scripts_exist(self):
        out = self.run_code('''
from kv.routes import GET_ROUTES, POST_ROUTES
import kv.paths as P
need_post = ["/api/verify", "/api/notice", "/api/exam_collect", "/api/exam_release", "/api/privacy_pin", "/api/privacy_acl", "/api/list_variant_save", "/api/list_variant_delete"]
need_get = ["/api/privacy", "/api/list_variant"]
print([r for r in need_post if r not in POST_ROUTES], [r for r in need_get if r not in GET_ROUTES])
print([n for n in ("kvstate.ps1", "kvexam.ps1", "kvclip.ps1") if "\\r" in P.load_script(n) or not P.load_script(n).strip()])
''')
        self.assertEqual(out.splitlines(), ['[] []', '[]'])

class Features39(Base):
    def run_code(self, code):
        r = _py(self.app, code)
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        return r.stdout.strip()

    def test_startup_vbs_file_roundtrip(self):
        out = self.run_code('''
import os, tempfile
import kv.startup as S
d = tempfile.mkdtemp(); p = os.path.join(d, "sub", S.STARTUP_NAME)
S.startup_set(True, path=p, app_dir="C:\\\\Lop Tin")
raw = open(p, "rb").read()
txt = raw.decode("utf-16")
print(raw[:2] in (b"\\xff\\xfe", b"\\xfe\\xff"), "--background" in txt, "Lop Tin" in txt, "0, False" in txt)
S.startup_set(False, path=p); S.startup_set(False, path=p)
print(os.path.exists(p))
''')
        self.assertEqual(out.splitlines(), ['True True True True', 'False'])

    def test_background_flag_keeps_server_alive_and_bat_forwards_args(self):
        out = self.run_code('''
import inspect, kv.app as A
src = inspect.getsource(A)
print("--background" in src and "STATE.get('background')" in src)
b = open("Chay-KhoaVeyon.bat", encoding="utf-8").read()
print(b.count("KhoaVeyon.py %*"))
''')
        self.assertEqual(out.splitlines(), ['True', '2'])

    def test_logon_policy_files_and_calls(self):
        out = self.run_code('''
import kv.logonpolicy as L
print(L.logon_modes_clean(["mute", "evil", "lockdown", "mute"]))
t = L.logon_bat_text(r"C:\\cmd\\KhoaVeyonServices.bat", ["mute", "lockdown", "x&calc"])
print(t.count("call "), "-lockdown" in t and "-mute" in t and "calc" not in t)
x = L.logon_task_xml(r"C:\\cmd\\vcfg\\KhoaVeyonLogon.bat")
print("S-1-5-32-545" in x and "LogonTrigger" in x and "LeastPrivilege" in x and "&quot;" not in x or "KhoaVeyonLogon.bat" in x)
calls = []
L.run_args = lambda a, timeout=60: (calls.append(a) or (0, "ok"))
L.distribute_to_host = lambda h, files, d: calls.append(("dist", h, d))
ok, msg = L.logon_install("PC1", {"dist_target": r"C:\\cmd", "script_path": r"C:\\cmd\\KhoaVeyonServices.bat"}, ["lockdown"])
print(ok, calls[0][0], calls[1][:3])
print(L.logon_install("PC1", {"dist_target": "C:\\\\cmd"}, ["bad"])[0])
''')
        lines = out.splitlines()
        self.assertEqual(lines[0], "['lockdown', 'mute']")
        self.assertEqual(lines[1], '2 True')
        self.assertEqual(lines[2], 'True')
        self.assertTrue(lines[3].startswith('True dist'), lines[3])
        self.assertEqual(lines[4], 'False')

    def test_student_notice_receipt_after_teacher_received_the_shot(self):
        out = self.run_code('''
import os, json, tempfile
import kv.alerts as A, kv.watch as W
src = tempfile.mkdtemp(); dest = tempfile.mkdtemp()
A.tcp_open = lambda *a, **k: True
import kv.remote as RR, ntpath, kv.evidence as EV; RR.unc_target = lambda h, p: src if ntpath.normpath(p) == ntpath.normpath(EV.WATCH_REMOTE_DIR) else os.path.join(src, ntpath.basename(p))
A.evidence_root = lambda: dest
def shot(name):
    open(os.path.join(src, name + ".jpg"), "wb").write(b"\\xff\\xd8jpg")
    json.dump({"pc": "PC1", "user": "hs", "type": "site", "name": "youtube.com", "window": "w",
               "date": "2026-10-18", "time": "09:42:10", "file": name + ".jpg"}, open(os.path.join(src, name + ".json"), "w"))
n1 = "PC1_20261018-094210_site_youtube.com"
shot(n1)
print(A.alert_collect_host({"watch_notify_student": True}, "PC1")[2], sorted(os.listdir(src)))
os.remove(os.path.join(src, n1 + ".jpg.ok"))
n2 = "PC1_20261018-094300_site_youtube.com"
shot(n2)
print(A.alert_collect_host({"watch_notify_student": False}, "PC1")[2], sorted(os.listdir(src)))
s = open(os.path.join("scripts", "KhoaVeyonWatch.ps1"), encoding="utf-8").read()
print("[int]$NotifyStudent" in s, "'.ok'" in s, "ĐÃ GHI NHẬN VI PHẠM" in s)
''')
        lines = out.splitlines()
        self.assertEqual(lines[0], "1 ['PC1_20261018-094210_site_youtube.com.jpg.ok']")
        self.assertEqual(lines[1], "1 []")
        self.assertEqual(lines[2], "True True True")

    def test_watch_passes_notify_switch_to_student_script(self):
        out = self.run_code('''
import kv.watch as W
seen = []
W.distribute_to_host = lambda h, files, d: None
W.remote_run = lambda h, cmd, interactive=False, name="": (seen.append(cmd) or (0, "ok"))
W.watch_hosts_set = lambda h, on: None
import kv.remote as RR; RR.unc_target = lambda h, d: __import__("tempfile").mkdtemp()
base = {"dist_target": "C:\\\\cmd", "watch_autostart": False}
W.watch_autostart_remove = lambda h: (True, "")
W.watch_start_one(dict(base), "PC1"); W.watch_start_one(dict(base, watch_notify_student=False), "PC1")
print(seen[0].endswith("-NotifyStudent 1"), seen[1].endswith("-NotifyStudent 0"))
''')
        self.assertEqual(out, "True True")

    def test_evidence_is_filed_by_date_and_class_with_readable_names(self):
        out = self.run_code('''
import os, json, tempfile, time
import kv.alerts as A, kv.gallery as G, kv.evidence as E, kv.cleanup as C
root = tempfile.mkdtemp(); src = tempfile.mkdtemp()
for m in (A, G, C):
    m.evidence_root = lambda: root
A.tcp_open = lambda *a, **k: True
import kv.remote as RR, ntpath, kv.evidence as EV; RR.unc_target = lambda h, p: src if ntpath.normpath(p) == ntpath.normpath(EV.WATCH_REMOTE_DIR) else os.path.join(src, ntpath.basename(p))
A.school_class_at = lambda ts: "10A1"
A.school_student_for = lambda h, c: ("Nguyễn Văn An", 7)
n = "PC07_20261018-094210_site_youtube.com"
open(os.path.join(src, n + ".jpg"), "wb").write(b"jpg")
json.dump({"pc": "PC07", "user": "hs", "type": "site", "name": "youtube.com", "window": "w", "date": "2026-10-18", "time": "09:42:10", "file": n + ".jpg"},
          open(os.path.join(src, n + ".json"), "w"))
cfg = {"school_name": "THPT Nguyễn Du", "host_names": {"10.0.0.7": "Máy 07"}}
print(A.alert_collect_host(cfg, "10.0.0.7")[2])
e = A.ALERTS[-1]
print(e["img"])
print(os.path.isfile(os.path.join(root, *e["img"].split("/"))))
print(G.evidence_file_name("", "", "", "PC1", "2026-10-18", "07:00:01", "app", 'a<b>:c|d?.exe'))
print(G.evidence_dir_parts("2026-10-18", ""), G.evidence_dir_parts("../x", "10/A"))
print(G.evidence_abs("../../etc/passwd") is None or G.evidence_abs("../../etc/passwd").startswith(os.path.realpath(root)))
r = G.api_gallery({"from": "2026-10-18", "to": "2026-10-18", "cls": "10A1"})
print(r["total"], r["items"][0]["exists"], r["facets"]["classes"], r["facets"]["students"])
print(G.api_gallery({"q": "youtube"})["total"], G.api_gallery({"cls": "-"})["total"], G.api_gallery({"from": "2026-10-19"})["total"], G.api_gallery({"type": "app"})["total"])
old = time.time() - 40 * 86400
fp = os.path.join(root, *e["img"].split("/")); os.utime(fp, (old, old))
legacy = os.path.join(root, "PC9"); os.makedirs(legacy); lj = os.path.join(legacy, "x.jpg"); open(lj, "wb").write(b"1"); os.utime(lj, (old, old))
res = C.evidence_cleanup(30, 0)
print(res["images"], os.path.exists(os.path.join(root, "2026-10-18")), os.path.exists(legacy))
''')
        lines = out.splitlines()
        self.assertEqual(lines[0], "1")
        self.assertEqual(lines[1], "2026-10-18/10A1/THPT Nguyễn Du_10A1_Nguyễn Văn An_Máy 07_2026-10-18_09-42-10_Web_youtube.com.jpg")
        self.assertEqual(lines[2], "True")
        self.assertEqual(lines[3], "PC1_2026-10-18_07-00-01_App_a b c d .exe.jpg")
        self.assertEqual(lines[4], "['2026-10-18', 'Chua-ro-lop'] ['Khong-ro-ngay', '10 A']")
        self.assertEqual(lines[5], "True")
        self.assertEqual(lines[6], "1 True ['10A1'] ['Nguyễn Văn An']")
        self.assertEqual(lines[7], "1 0 0 0")
        self.assertEqual(lines[8], "2 False False")

    def test_app_lock_default_password_and_flow(self):
        out = self.run_code('''
import os, tempfile, json
import kv.applock as L, kv.paths as P
d = tempfile.mkdtemp(); P.CONFIG_PATH = os.path.join(d, "KhoaVeyon.json")
L.applock_load()
print(L.applock_status()["locked"], L.applock_status()["is_default"])
print(L.api_applock({"action": "lock"})["locked"], L.applock_is_locked())
try: L.api_applock({"action": "unlock", "pin": "9999"}); print("BAD")
except Exception as e: print("reject")
print(L.api_applock({"action": "unlock", "pin": "0000"})["locked"])
try: L.api_applock({"action": "setpin", "pin": "0000", "new_pin": "abc"}); print("BAD")
except Exception: print("too-short")
try: L.api_applock({"action": "setpin", "pin": "0000", "new_pin": "lophoc1", "confirm": "lophoc2"}); print("BAD")
except Exception: print("mismatch")
print(L.api_applock({"action": "setpin", "pin": "0000", "new_pin": "GiaoVien@2026", "confirm": "GiaoVien@2026"})["is_default"])
L.api_applock({"action": "lock"})
print(L.api_applock({"action": "unlock", "pin": "GiaoVien@2026"})["locked"])
print(L.api_applock({"action": "idle", "idle_min": "500"})["idle_min"])
# nạp lại từ đĩa: mật khẩu mới còn, không khóa sẵn
L.STATE["locked"] = True; L.applock_load()
print(L.applock_is_locked(), L.api_applock({"action": "unlock", "pin": "GiaoVien@2026"})["locked"])
from kv.routes import GET_ROUTES, POST_ROUTES
print("/api/applock" in GET_ROUTES, "/api/applock" in POST_ROUTES)
''')
        self.assertEqual(out.splitlines(), ["False True", "True True", "reject", "False", "too-short", "mismatch", "False", "False", "240", "False False", "True True"])

    def test_webonly_browser_allowlist_wired(self):
        out = self.run_code('''
from kv.actions import ACTION_BY_KEY
print("webonly" in ACTION_BY_KEY, "weboff" in ACTION_BY_KEY)
print(ACTION_BY_KEY["webonly"][2], ACTION_BY_KEY["weboff"][2])
from kv.meta import LOCK_KEYS, FREE_KEYS, GROUPS
print("webonly" in LOCK_KEYS, "weboff" in FREE_KEYS)
print([k for g, ks in GROUPS if g == "Internet" for k in ks])
import kv.exam as E
print("webonly" in E.EXAM_DEFAULT_STEPS, E.EXAM_DEFAULT_STEPS["webonly"])
import inspect
s = inspect.getsource(E)
print("job_action('webonly', on)" in s, "job_action('weboff', on)" in s)
from kv.khoalink import KQ_DOMAINS
print("firestore.googleapis.com" in KQ_DOMAINS, any("mongodb" in d for d in KQ_DOMAINS))
''')
        lines = out.splitlines()
        self.assertEqual(lines[0], "True True")
        self.assertEqual(lines[1], "-webonly -weboff")
        self.assertEqual(lines[2], "True True")
        self.assertEqual(lines[3], "['blockall', 'allowpage', 'webonly', 'weboff', 'allowall']")
        self.assertEqual(lines[4], "True False")
        self.assertEqual(lines[5], "True True")
        self.assertEqual(lines[6], "True True")

    def test_watch_autostart_uses_guard_file_not_schtasks(self):
        out = self.run_code('''
import os, tempfile
import kv.watch as W, kv.runtime as RT
d = tempfile.mkdtemp()
import kv.remote as RR
import ntpath; RR.unc_target = lambda h, path: os.path.join(d, ntpath.basename(path))
W.vcfg_remote_dir = lambda cfg: "C:\\\\cmd\\\\vcfg"
calls = []
RR.run_args = lambda a, timeout=60: (calls.append(a) or (0, "ok"))
W.tcp_open = lambda *a, **k: True
RT.CFG["features"] = {}
ok, msg = W.watch_autostart_install("PC1", "-NoProfile -File x.ps1 -Out C:\\\\Users")
gp = os.path.join(d, "kvguard.txt")
print(ok, os.path.isfile(gp), open(gp).read().startswith("powershell.exe -NoProfile"))
print(any(c[0]=="schtasks" and "/Delete" in c for c in calls))
ok2, _ = W.watch_autostart_remove("PC1")
print(ok2, os.path.exists(gp))
bat = None
''')
        self.assertEqual(out.splitlines(), ["True True True", "True", "True False"])

    def test_ai_opts_file_and_blockai_steps(self):
        out = self.run_code('''
import os, tempfile
import kv.ai as A, kv.runtime as RT
d = tempfile.mkdtemp(); RT.CFG["list_dir"] = d
p = A.ai_opts_write({"ai_block_overviews": True, "ai_disable_doh": True, "ai_block_ext": False})
print(sorted(open(p).read().split()))
p2 = A.ai_opts_write({"ai_block_overviews": False, "ai_disable_doh": True, "ai_block_ext": True})
print(sorted(open(p2).read().split()))
from kv.excel_lists import AI_PRESETS
doms = [x[0] for g in AI_PRESETS.values() for x in g]
print("dora.run" in doms, "blackbox.ai" in doms)
''')
        lines = out.splitlines()
        self.assertEqual(lines[0], "['DOH=1', 'EXT=0', 'OVERVIEW=1']")
        self.assertEqual(lines[1], "['DOH=1', 'EXT=1', 'OVERVIEW=0']")
        self.assertEqual(lines[2], "True True")

    def test_new_routes(self):
        out = self.run_code('''
from kv.routes import POST_ROUTES
print([r for r in ("/api/startup", "/api/logon_policy") if r not in POST_ROUTES])
import kv.paths as P
print(P.VERSION)
''')
        self.assertEqual(out.splitlines(), ['[]', '4.13.0'])


if __name__ == '__main__':
    unittest.main()
