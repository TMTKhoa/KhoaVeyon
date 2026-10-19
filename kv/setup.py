# -*- coding: utf-8 -*-
"""Thiết lập máy giáo viên: file mẫu, thư mục payload, 20 mục điều khiển trong Veyon (Programs & websites)."""

import json
import os
import re
import shutil
import sys
import time
import uuid

from .actions import ACTIONS
from .excel_lists import AI_PRESETS, LISTS, write_list
from .paths import abs_path, APP_DIR, CONFIG_PATH, ENTRY_SCRIPT, find_veyon_cli, load_script
from .remote import run_args
from .runtime import PAYLOAD_DIR


STUDENT_SETUP_BAT = 'Setup-MayHocSinh.bat'
SETUP_RESULT = lambda: os.path.join(os.path.dirname(CONFIG_PATH), 'setup-result.json')  # noqa
DEFAULT_PRESETS = {  # danh sách mẫu tạo sẵn ở lần đầu (chỉ khi file chưa tồn tại)
    'keep': ['Google Chrome', 'ONLYOFFICE', 'Microsoft Paint'],
    'allow': ['Bộ trang học tập mẫu'],
    'block': ['Steam', 'Epic Games', 'Roblox', 'Thư mục game C:\\Games'],
    'ai': list(AI_PRESETS.keys()),
}

STUDENT_BAT = load_script('student-setup.bat')


def is_admin():
    if os.name != 'nt':
        return True
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # noqa
    except Exception:  # noqa
        return False


def find_script_file(cfg):
    """Tìm KhoaVeyonServices.bat để tự chép vào payload (thư mục payload, cạnh chương trình, thư mục cha, C:\\cmd)."""
    name = os.path.basename((cfg.get('script_path') or '').replace('\\', '/')) or 'KhoaVeyonServices.bat'
    cands = [os.path.join(PAYLOAD_DIR, name), os.path.join(APP_DIR, name), os.path.join(os.path.dirname(APP_DIR), name),
             os.path.join(os.path.dirname(os.path.dirname(APP_DIR)), name), cfg.get('script_path') or '',
             os.path.join('C:\\cmd', name)]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return ''


def seed_default_lists(cfg):
    """Tạo 4 file Excel mẫu nếu chưa có. Trả về số file đã tạo."""
    made = 0
    for kind, names in DEFAULT_PRESETS.items():
        path = os.path.join(abs_path(cfg['list_dir']), LISTS[kind]['file'])
        if os.path.exists(path):
            continue
        rows = []
        for n in names:
            rows += LISTS[kind]['presets'].get(n, [])
        write_list(path, kind, rows)
        made += 1
    return made


def write_agent_cfg(cfg):
    """Ghi payload\\KhoaVeyonAgent.cfg (địa chỉ máy giáo viên + khóa Agent + SHA-256 của KhoaVeyonServices.bat) cho Setup-MayHocSinh.bat.
    File này chứa khóa bí mật nên KHÔNG được gửi hàng loạt xuống C:\\cmd (xem _kit_only / resolve_dist_files)."""
    import hashlib
    from .agent import agent_config_text, AGENT_CFG_NAME
    os.makedirs(PAYLOAD_DIR, exist_ok=True)
    name = os.path.basename((cfg.get('script_path') or '').replace('\\', '/')) or 'KhoaVeyonServices.bat'
    sp = os.path.join(PAYLOAD_DIR, name)
    sha = ''
    if os.path.isfile(sp):
        with open(sp, 'rb') as f:
            sha = hashlib.sha256(f.read()).hexdigest()
    with open(os.path.join(PAYLOAD_DIR, AGENT_CFG_NAME), 'w', encoding='ascii', newline='') as f:
        f.write(agent_config_text(sha))
    return AGENT_CFG_NAME


def refresh_agent_cfg():
    """Giữ payload\\KhoaVeyonAgent.cfg luôn khớp với địa chỉ, cổng, khóa và bản KhoaVeyonServices.bat hiện tại.
    Gọi khi khởi động và mỗi khi đổi cài đặt / khóa Agent, nên không cần bấm nút nào. Lỗi thì bỏ qua."""
    try:
        from .runtime import CFG, CFG_LOCK
        import json as _j
        with CFG_LOCK:
            cfg = _j.loads(_j.dumps(CFG))
        write_agent_cfg(cfg)
        return True
    except Exception:  # noqa
        return False


def ensure_payload(cfg):
    """Tạo Setup-MayHocSinh.bat trong payload và chép KhoaVeyonServices.bat vào payload nếu tìm thấy. Trả về (đã tạo, thiếu)."""
    os.makedirs(PAYLOAD_DIR, exist_ok=True)
    with open(os.path.join(PAYLOAD_DIR, STUDENT_SETUP_BAT), 'w', encoding='utf-8', newline='') as f:
        f.write(STUDENT_BAT.replace('\r\n', '\n').replace('\n', '\r\n'))
    name = os.path.basename((cfg.get('script_path') or '').replace('\\', '/')) or 'KhoaVeyonServices.bat'
    dst = os.path.join(PAYLOAD_DIR, name)
    got = []
    if not os.path.isfile(dst):
        src = find_script_file(cfg)
        if src:
            shutil.copy2(src, dst)
            got.append(name)
    write_agent_cfg(cfg)
    return got, ([] if os.path.isfile(dst) else [name])


def desired_programs(cfg):
    """Các mục 'Programs & websites' cần có trong Veyon: (tên mục, dòng lệnh)."""
    return [(cfg['features'].get(a[0]) or a[3], 'cmd.exe /c %s %s' % (cfg['script_path'], a[2])) for a in ACTIONS]


PROGRAMS_KEY = 'DesktopServices/PredefinedPrograms'


def _norm_programs(data):
    """Mỗi mục có thể trả về dạng object hoặc chuỗi JSON: đưa hết về dict."""
    out = []
    for x in data:
        if isinstance(x, str):
            try:
                x = json.loads(x)
            except Exception:  # noqa
                continue
        if isinstance(x, dict):
            out.append(x)
    return out


def _veyon_get_programs(cli):
    rc, out = run_args([cli, 'config', 'get', 'DesktopServices/PredefinedPrograms'], timeout=30)
    if rc != 0:
        # Veyon mới cài chưa có mục nào thì khóa này chưa tồn tại: coi như danh sách rỗng để còn tạo mới
        if 'does not exist' in out.lower() or 'not exist' in out.lower():
            return [], ''
        return None, out
    out = out.strip()
    if not out:
        return [], ''
    try:
        data = json.loads(out)
        if isinstance(data, str):
            data = json.loads(data)
        return (_norm_programs(data) if isinstance(data, list) else []), ''
    except Exception as e:  # noqa
        return None, 'Không đọc được kết quả veyon-cli: %s' % e


def _path_key(p):
    return re.sub(r'\s+', ' ', str(p or '')).strip().lower()


def _programs_missing(cur, want):
    """Mục còn thiếu so với cấu hình Veyon hiện có. Mục đã có sẵn (cùng tên HOẶC cùng dòng lệnh) coi như đủ, không đụng tới."""
    names = {str(x.get('Name', '')) for x in cur if isinstance(x, dict)}
    paths = {_path_key(x.get('Path')) for x in cur if isinstance(x, dict)}
    return [n for n, c in want if n not in names and _path_key(c) not in paths]


def veyon_items_status(cfg):
    """Trả về (số mục đã có, tổng, lỗi). Không ghi gì."""
    cli = find_veyon_cli(cfg['veyon_cli'])
    if not os.path.isfile(cli):
        return 0, len(ACTIONS), 'Chưa thấy veyon-cli'
    cur, err = _veyon_get_programs(cli)
    if cur is None:
        return 0, len(ACTIONS), err
    ok = len(desired_programs(cfg)) - len(_programs_missing(cur, desired_programs(cfg)))
    return ok, len(ACTIONS), ''


def apply_veyon_items(cfg):
    """Ghi các mục vào cấu hình Veyon (giữ nguyên mục khác, cập nhật mục trùng tên). Cần quyền quản trị. Trả về (ok, thông báo)."""
    cli = find_veyon_cli(cfg['veyon_cli'])
    if not os.path.isfile(cli):
        return False, 'Chưa thấy veyon-cli.exe (đặt đường dẫn ở Cài đặt)'
    cur, err = _veyon_get_programs(cli)
    if cur is None:
        return False, 'Không đọc được cấu hình Veyon hiện tại: %s' % err
    try:  # sao lưu trước khi sửa
        bk = os.path.join(os.path.dirname(CONFIG_PATH), 'veyon-programs-backup.json')
        with open(bk, 'w', encoding='utf-8') as f:
            json.dump(cur, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
    items = [x for x in cur if isinstance(x, dict)]
    want = desired_programs(cfg)
    todo = set(_programs_missing(items, want))
    kept = len(want) - len(todo)
    if not todo:  # Veyon đã được thiết lập sẵn đủ: dùng nguyên, không ghi gì
        return True, 'Veyon đã có sẵn đủ %d mục, giữ nguyên cấu hình hiện có (không ghi gì).' % len(want)
    extra = {}  # khóa phụ (vd. Type) lấy theo mục có sẵn để mục mới cùng dạng
    for x in items:
        extra = {k: v for k, v in x.items() if k not in ('Name', 'Path', 'Uid')}
        if extra:
            break
    added = 0
    for name, path in want:
        if name in todo:
            it = {'Name': name, 'Path': path, 'Uid': '{%s}' % uuid.uuid4()}
            it.update(extra)
            items.append(it)
            added += 1

    def missing():
        again, _e = _veyon_get_programs(cli)
        return _programs_missing(again or [], want)

    value = json.dumps(items, ensure_ascii=False, separators=(',', ':'))
    notes = []
    rc, out = run_args([cli, 'config', 'set', PROGRAMS_KEY, value], timeout=60)  # cách 1
    if rc != 0:
        notes.append('config set lỗi (%s): %s' % (rc, out[:200]))
    miss = missing()
    method = 'config set'
    if miss:  # cách 2, tự động: xuất cấu hình -> sửa file -> nhập lại
        ok2, note2 = _apply_programs_via_import(cli, items)
        notes.append(note2)
        miss = missing()
        method = 'export/import'
    if miss:
        pth = os.path.join(os.path.dirname(CONFIG_PATH), 'veyon-programs-import.json')
        try:
            with open(pth, 'w', encoding='utf-8') as f:
                json.dump({'DesktopServices': {'PredefinedPrograms': items}}, f, ensure_ascii=False, indent=2)
        except OSError:
            pth = '(không ghi được file)'
        rc3, raw = run_args([cli, 'config', 'get', PROGRAMS_KEY], timeout=30)
        return False, ('Đã tự thử 2 cách (config set, rồi export/import) nhưng Veyon vẫn thiếu %d/%d mục. %s '
                       'Kết quả đọc lại (mã %s): %s. Đã tạo sẵn file %s để đối chiếu.'
                       % (len(miss), len(want), ' | '.join(notes), rc3, (raw or '(trống)')[:300].replace('\n', ' '), pth))
    return True, 'Giữ nguyên %d mục có sẵn, thêm %d mục còn thiếu (bằng %s). Hãy mở lại Veyon Master để thấy các mục mới.' % (kept, added, method)


def _apply_programs_via_import(cli, items):
    """Xuất toàn bộ cấu hình Veyon, sửa khóa PredefinedPrograms rồi nhập lại. Có sao lưu bản xuất gốc."""
    base = os.path.dirname(CONFIG_PATH)
    tmp = os.path.join(base, 'veyon-export-tmp.json')
    rc, out = run_args([cli, 'config', 'export', tmp], timeout=60)
    if rc != 0 or not os.path.isfile(tmp):
        return False, 'config export lỗi (%s): %s' % (rc, out[:200])
    try:
        with open(tmp, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
        with open(os.path.join(base, 'veyon-config-truoc-khi-import.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if PROGRAMS_KEY in data:
            data[PROGRAMS_KEY] = items
        else:
            if not isinstance(data.get('DesktopServices'), dict):
                data['DesktopServices'] = {}
            data['DesktopServices']['PredefinedPrograms'] = items
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:  # noqa
        return False, 'không sửa được file xuất: %s' % e
    rc, out = run_args([cli, 'config', 'import', tmp], timeout=60)
    try:
        os.remove(tmp)
    except OSError:
        pass
    if rc != 0:
        return False, 'config import lỗi (%s): %s' % (rc, out[:200])
    return True, 'đã thử export/import'


def _apply_with_firewall(cfg):
    """Chạy bằng quyền quản trị: mở cổng Agent trên tường lửa máy giáo viên rồi áp các mục Veyon."""
    from .agent import agent_firewall_rule
    try:
        fw_ok, fw_msg = agent_firewall_rule()
    except Exception as e:  # noqa
        fw_ok, fw_msg = False, str(e)
    ok, msg = apply_veyon_items(cfg)
    return ok, '%s | Agent: %s' % (msg, fw_msg)


def elevated_apply_veyon_items(cfg):
    """Gọi apply_veyon_items với quyền quản trị: nếu chưa là admin thì bật hộp thoại UAC chạy lại chương trình ở chế độ riêng."""
    if is_admin():
        return _apply_with_firewall(cfg)
    try:
        os.remove(SETUP_RESULT())
    except OSError:
        pass
    import ctypes
    exe = sys.executable
    params = '"%s" --apply-veyon-items' % ENTRY_SCRIPT
    r = ctypes.windll.shell32.ShellExecuteW(None, 'runas', exe, params, APP_DIR, 0)  # noqa
    if r <= 32:
        return False, 'Bạn đã từ chối quyền quản trị (hoặc không mở được UAC)'
    for _ in range(120):
        time.sleep(0.5)
        if os.path.exists(SETUP_RESULT()):
            time.sleep(0.2)
            try:
                with open(SETUP_RESULT(), 'r', encoding='utf-8') as f:
                    d = json.load(f)
                return bool(d.get('ok')), d.get('msg', '')
            except Exception:  # noqa
                continue
    return False, 'Quá thời gian chờ kết quả từ cửa sổ quản trị'
