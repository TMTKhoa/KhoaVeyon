# -*- coding: utf-8 -*-
"""Kiểm thử kết nối KhoaQuiz / KhoaTool (không cần Internet, Windows hay Veyon): python -m unittest discover tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_smoke import Base, _py  # noqa: E402


class KhoaLink(Base):
    def run_code(self, code):
        r = _py(self.app, code)
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        return r.stdout.strip()

    def test_code_url_and_exam_link(self):
        out = self.run_code('''
import kv.khoalink as K
print(K.canon_code(" kq-abcdef ghjklm-npqrst-uvwxyz "), K.canon_code("KQ-123"), K.clean_url("khoaquiz.netlify.app/"), K.clean_url("ftp://x"))
print(K.exam_url_for("https://kq.app/kiemtra.html?e=bo1&m=old", "192.168.1.12:11100"), K.exam_url_for("https://kq.app/kiemtra.html?e=bo1", "MAY 7!"))
print(K.allow_domains_for("https://kq.app/kiemtra.html?e=1")[:2])
''')
        l1, l2, l3 = out.splitlines()
        self.assertEqual(l1, 'KQ-ABCDEF-GHJKLM-NPQRST-UVWXYZ  https://khoaquiz.netlify.app ')
        self.assertEqual(l2, 'https://kq.app/kiemtra.html?e=bo1&m=192.168.1.12 https://kq.app/kiemtra.html?e=bo1&m=MAY7')
        self.assertEqual(l3, "['kq.app', 'www.gstatic.com']")

    def test_json_class_list_from_khoatool_is_merged(self):
        out = self.run_code('''
import json, os, tempfile
import kv.school as SC, kv.school_api as SA
p = os.path.join(tempfile.mkdtemp(), "ds.json")
json.dump({"app": "KhoaTool", "format": 1, "classes": [{"cls": "6a1", "students": ["Nguyễn  An", "Trần Bình", "nguyễn an"]}, {"cls": "7A2", "students": []}]}, open(p, "w", encoding="utf-8"), ensure_ascii=False)
SC.SCHOOL["classes"] = {"6A1": ["Nguyễn An", "Lê Cũ"], "8A1": ["Giữ Nguyên"]}
SC.SCHOOL["layouts"] = {"6A1": {"seats": {"1": "Lê Cũ", "2": "Nguyễn An", "3": "Ghi Tay"}}}
SA.school_import("classes", p, "khoatool.json")
print(sorted(SC.SCHOOL["classes"].items()), SC.SCHOOL["layouts"]["6A1"]["seats"])
try:
    json.dump({"classes": []}, open(p, "w")); SC.parse_classes_json(p)
except Exception as e:
    print(type(e).__name__)
''')
        l1, l2 = out.splitlines()
        self.assertEqual(l1, "[('6A1', ['Nguyễn An', 'Trần Bình']), ('8A1', ['Giữ Nguyên'])] {'2': 'Nguyễn An', '3': 'Ghi Tay'}")
        self.assertEqual(l2, 'ApiError')

    def test_kq_get_and_rosters(self):
        out = self.run_code('''
import io, json, urllib.error
import kv.khoalink as K
class R(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False
seen = []
def ok(req, timeout):
    seen.append((req.full_url, req.get_header("X-link-token")))
    return R(json.dumps({"classes": [{"cls": "6A1", "sid": "s1", "students": ["An", " "]}, {"cls": "6A1", "sid": "s2", "students": ["Bình"]}]}).encode())
d = K.kq_get("rosters", code="KQ-AAAAAA-AAAAAA-AAAAAA-AAAAAA", url="https://kq.app", opener=ok)
print(seen[0], K.rosters_to_classes(d, "s2"))
try: K.rosters_to_classes(d)
except Exception as e: print("dup", "nhiều trường" in str(e))
def bad(req, timeout): raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, io.BytesIO(json.dumps({"error": "Mã liên kết không đúng"}).encode()))
try: K.kq_get("info", code="x", url="https://kq.app", opener=bad)
except Exception as e: print(e)
def down(req, timeout): raise urllib.error.URLError("no route")
try: K.kq_get("info", code="x", url="https://kq.app", opener=down)
except Exception as e: print("Internet" in str(e))
''')
        lines = out.splitlines()
        self.assertEqual(lines[0], "('https://kq.app/api/link/rosters', 'KQ-AAAAAA-AAAAAA-AAAAAA-AAAAAA') {'6A1': ['Bình']}")
        self.assertEqual(lines[1], 'dup True')
        self.assertEqual(lines[2], 'KhoaQuiz báo lỗi (403): Mã liên kết không đúng')
        self.assertEqual(lines[3], 'True')

    def test_compare_attendance_with_quiz(self):
        out = self.run_code('''
import kv.khoalink as K
roster = ["Nguyễn An", "Trần Bình", "Lê Chi", "Phạm Dũng"]
att = {"seats": {"1": "Nguyễn An", "2": "Trần Bình", "3": "Lê Chi", "4": "Phạm Dũng"}, "absent": ["Lê Chi"], "offline": [4]}
items = [{"title": "KT", "students": [{"name": "nguyễn an", "score": 8, "m": "MAY2"}, {"name": "Lê Chi", "score": 5}, {"name": "Người Lạ", "score": 1}]}]
rows, extras = K.compare_rows(roster, att, {}, items, lambda h: int(h.replace("MAY", "")))
for r in rows: print(r["name"], r["did"], [f["code"] for f in r["flags"]])
print([x["name"] for x in extras])
''')
        self.assertEqual(out.splitlines(), [
            "Nguyễn An True ['other_machine']",
            "Trần Bình False ['suggest_absent']",
            "Lê Chi True ['did_but_absent']",
            "Phạm Dũng False ['offline', 'suggest_absent']",
            "['Người Lạ']"])

    def test_live_rows_machine_and_absent(self):
        out = self.run_code('''
import kv.khoalink as K
roster = ["Nguyễn An", "Trần Bình", "Lê Chi", "Phạm Dũng"]
att = {"seats": {"1": "Nguyễn An", "2": "Trần Bình", "3": "Lê Chi", "4": "Phạm Dũng"}, "absent": ["Lê Chi"], "base_seats": {}}
live = {"players": [{"name": "nguyễn  an", "m": "MAY2"}, {"name": "Lê Chi", "m": "MAY3"}, {"name": "Khách", "m": "MAY9"}, {"name": "Phạm Dũng", "m": "MAY1", "online": False}]}
rows, extras = K.live_rows(roster, att, live, lambda h: int(h.replace("MAY", "")))
for r in rows: print(r["name"], r["joined"], r["m_seat"], [f["code"] for f in r["flags"]])
print([x["name"] for x in extras])
''')
        self.assertEqual(out.splitlines(), [
            "Nguyễn An True 2 ['other_machine']",
            "Trần Bình False 0 ['not_joined']",
            "Lê Chi True 3 ['joined_but_absent']",
            "Phạm Dũng True 1 ['other_machine']",
            "['Khách']"])

    def test_live_start_marks_absent_and_moves_broken_machine_student(self):
        out = self.run_code('''
import datetime
import kv.school as SC, kv.attendance as ATT, kv.khoalink as K
ATT.start_job = lambda *a, **k: None
SC.SCHOOL["classes"]["10A1"] = ["An", "Bình", "Chi", "Dũng", "Em"]
# 5 máy một dãy; máy 2 hỏng nên Bình chưa có chỗ; Dũng ngồi máy 4
SC.SCHOOL["layouts"]["10A1"] = dict(SC.LAYOUT_DEFAULT, cols=1, per=5, seats={"1": "An", "3": "Chi", "4": "Dũng", "5": "Em"}, broken=[2])
SC.school_save = lambda: None
state = {}
def live(phase, names):
    return {"active": True, "pin": "123456", "phase": phase, "cls": "10A1", "players": [{"name": n} for n in names]}
who = ["An", "Bình", "Chi", "Em"]            # Dũng chưa vào phòng
print(K.live_apply(live("lobby", who), "10A1", state, K._set_attendance))
print(SC.SCHOOL["attendance"])
print(K.live_apply(live("question", who), "10A1", state, K._set_attendance))
st = ATT.att_state("10A1")
print(st["absent"], st["moves"], st["seats"])
# Dũng vào muộn: đánh dấu có mặt lại
print(K.live_apply(live("question", who + ["Dũng"]), "10A1", state, K._set_attendance))
print(ATT.att_state("10A1")["absent"])
# lần hỏi đầu tiên đã ở giữa trò chơi (KhoaVeyon mở sau): không tự đánh vắng
s2 = {}
print(K.live_apply(live("question", ["An"]), "10A1", s2, K._set_attendance))
''')
        lines = out.splitlines()
        self.assertEqual(lines[0], "[]")
        self.assertEqual(lines[1], "{}")
        self.assertEqual(lines[2], "[('absent', ['Dũng'])]")
        self.assertIn("['Dũng'] {'Bình': 4}", lines[3])
        self.assertEqual(lines[4], "[('present', ['Dũng'])]")
        self.assertEqual(lines[5], "[]")
        self.assertEqual(lines[6], "[]")

    def test_open_url_fallback_and_allowpage(self):
        out = self.run_code('''
import json, os, tempfile
import kv.khoalink as K, kv.runtime as RT
from kv.excel_lists import write_list, read_list
calls = []
def runner(args, t):
    calls.append(args[4]); return (1, "lỗi") if args[4] == K.OPEN_WEBSITE_UID else (0, "")
print(K.veyon_open_url("cli", "PC1", "https://kq.app/k?e=1&m=PC1", runner), json.loads(json.dumps(calls)) == [K.OPEN_WEBSITE_UID, K.START_APP_UID])
d = tempfile.mkdtemp(); RT.CFG["list_dir"] = d
write_list(os.path.join(d, "AllowPage.xlsx"), "allow", [("gstatic.com", ""), ("kq.app", "")])
K.job_kq_allow([], "https://kq.app/kiemtra.html?e=1")
v = [r[0] for r in read_list(os.path.join(d, "AllowPage.xlsx"))]
print(v[:3], "www.gstatic.com" in v, len(v))
K.job_kq_allow([], "https://kq.app/kiemtra.html?e=1")
print(len(read_list(os.path.join(d, "AllowPage.xlsx"))))
''')
        l1, l2, l3 = out.splitlines()
        self.assertEqual(l1, "(True, 'đã mở bài kiểm tra (qua explorer.exe)') True")
        # gstatic.com đã có thì không thêm www.gstatic.com (tên miền con tính là khớp)
        self.assertTrue(l2.startswith("['gstatic.com', 'kq.app', 'fonts.googleapis.com'] False"), l2)
        self.assertEqual(l2.split()[-1], l3)

    def test_export_for_khoatool(self):
        out = self.run_code('''
import json, kv.khoalink as K
att = {"absent": ["Lê Chi"], "moves": {"Trần Bình": 5}, "offline": [2], "shares": {}}
lay = {"seats": {"1": "Nguyễn An", "2": "Trần Bình"}, "broken": [7]}
rep = {"episodes": 3, "by_student": [{"student": "Nguyễn An", "cls": "6A1", "count": 2, "top": [{"name": "game.com", "count": 2}]},
                                    {"student": "(chưa biết học sinh)", "cls": "", "count": 1, "top": []},
                                    {"student": "Hà Em", "cls": "7A1", "count": 1, "top": []}]}
d = K.build_khoatool_export("2026-10-18", [("6A1", att, lay)], ["PC1", "PC2"], {"PC1": True, "PC2": False}, rep)
print(d["app"], d["format"], d["machines"], d["veyon"]["text"])
c = {x["cls"]: x for x in d["classes"]}
print(c["6A1"]["moved"], c["6A1"]["violators"][0]["name"], c["7A1"]["violators"][0]["name"], c["6A1"]["absent"])
''')
        l1, l2 = out.splitlines()
        self.assertEqual(l1, "KhoaVeyon 1 [{'no': '2', 'issue': 'không bật / mất kết nối Veyon'}, {'no': '7', 'issue': 'hỏng (sơ đồ KhoaVeyon)'}] Veyon kết nối 1/2 máy; không kết nối: PC2")
        self.assertEqual(l2, "[{'name': 'Trần Bình', 'from': 2, 'to': 5, 'reason': 'broken'}] Nguyễn An Hà Em ['Lê Chi']")


if __name__ == '__main__':
    unittest.main()
