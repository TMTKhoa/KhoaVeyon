# -*- coding: utf-8 -*-
"""Khởi động: chỉ chạy một bản, mở cửa sổ giao diện, bật các luồng nền, tự thoát khi không dùng."""

import json
import os
import secrets
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser

from .alerts import alerts_load
from .applied import applied_load
from .auto import auto_load, auto_loop
from .exam import exam_load, exam_loop
from .khoalink import kq_load
from .monitor import alert_loop
from .paths import abs_path, CONFIG_PATH
from .applock import applock_load
from .privacy import priv_load
from .reapply import reapply_loop
from .runtime import CFG, IDLE_EXIT_SECONDS, log, PAYLOAD_DIR, STATE
from .school import school_load
from .school_api import school_loop
from .server import make_server
from .setup_jobs import run_apply_mode
from .status import status_loop
from .updater import update_loop
from .vcfg import run_elevated_job


def _info_path():
    return os.path.join(os.path.dirname(CONFIG_PATH), 'server.json')


def existing_instance():
    """Nếu KhoaVeyon đã chạy sẵn thì trả về địa chỉ của nó để mở lại cửa sổ thay vì chạy bản thứ hai."""
    try:
        with open(_info_path(), 'r', encoding='utf-8') as f:
            info = json.load(f)
        req = urllib.request.Request('http://127.0.0.1:%d/api/ping' % info['port'], headers={'X-Token': info['token']})
        with urllib.request.urlopen(req, timeout=1.5) as r:
            if r.status == 200:
                return 'http://127.0.0.1:%d/?t=%s' % (info['port'], info['token'])
    except Exception:  # noqa
        pass
    return ''


def browser_exe():
    for env in ('ProgramFiles(x86)', 'ProgramFiles', 'LOCALAPPDATA'):
        base = os.environ.get(env)
        if not base:
            continue
        for rel in (('Microsoft', 'Edge', 'Application', 'msedge.exe'),
                    ('Google', 'Chrome', 'Application', 'chrome.exe')):
            p = os.path.join(base, *rel)
            if os.path.isfile(p):
                return p
    return ''


def open_ui(url):
    """Mở như một cửa sổ ứng dụng (Edge/Chrome --app, không có thanh địa chỉ); không có thì mở trình duyệt mặc định."""
    exe = browser_exe() if os.name == 'nt' else ''
    if exe:
        try:
            subprocess.Popen([exe, '--app=' + url, '--window-size=1360,900'])
            return
        except Exception:  # noqa
            pass
    webbrowser.open(url)


def watchdog(srv):
    while True:
        time.sleep(5)
        watching = bool(CFG.get('watch_hosts')) or STATE.get('background')  # giám sát hoặc chạy nền khi khởi động Windows thì không tự thoát
        if STATE['pinged'] and STATE['busy'] == 0 and not watching and time.time() - STATE['last_ping'] > IDLE_EXIT_SECONDS:
            srv.shutdown()
            return


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if '--after-update' in argv:  # bản cũ đang tắt, đợi nó nhả cổng rồi chạy bản mới
        for _ in range(40):
            if not existing_instance():
                break
            time.sleep(0.5)
    if '--apply-veyon-items' in argv:
        run_apply_mode()
        return
    if '--elevated-job' in argv:
        run_elevated_job()
        return
    os.makedirs(PAYLOAD_DIR, exist_ok=True)
    inst = existing_instance()
    if inst:
        if '--no-browser' not in argv and '--background' not in argv:
            open_ui(inst)
        return
    srv = make_server()
    STATE['server'] = srv
    STATE['background'] = '--background' in argv   # khởi động cùng Windows: chạy ẩn, không tự thoát cho tới khi bấm Thoát
    STATE['port'] = srv.server_address[1]
    STATE['token'] = secrets.token_urlsafe(18)
    url = 'http://127.0.0.1:%d/?t=%s' % (STATE['port'], STATE['token'])
    try:
        with open(_info_path(), 'w', encoding='utf-8') as f:
            json.dump({'port': STATE['port'], 'token': STATE['token']}, f)
    except OSError:
        pass
    log('Sẵn sàng. Thư mục danh sách: %s' % abs_path(CFG['list_dir']), 'head')
    log('Cài đặt lưu tại: %s' % CONFIG_PATH)
    alerts_load()
    school_load()
    auto_load()
    applied_load()
    priv_load()
    applock_load()
    try:
        from .ai import ai_opts_write
        ai_opts_write(CFG)
    except OSError:
        pass
    from .agent import agent_start
    agent_start()   # cổng cho dịch vụ trên máy học sinh gọi về (kênh Agent)
    from .setup import refresh_agent_cfg
    refresh_agent_cfg()   # tự tạo/cập nhật payload\\KhoaVeyonAgent.cfg, không cần bấm nút
    threading.Thread(target=school_loop, daemon=True).start()
    exam_load()
    kq_load()
    from .khoalink import live_loop
    threading.Thread(target=live_loop, daemon=True).start()
    threading.Thread(target=auto_loop, daemon=True).start()
    threading.Thread(target=exam_loop, daemon=True).start()
    threading.Thread(target=reapply_loop, daemon=True).start()
    threading.Thread(target=status_loop, daemon=True).start()
    threading.Thread(target=alert_loop, daemon=True).start()
    threading.Thread(target=watchdog, args=(srv,), daemon=True).start()
    threading.Thread(target=update_loop, daemon=True).start()
    if '--background' in argv:
        log('Đang chạy nền (khởi động cùng Windows). Mở lại bằng Chay-KhoaVeyon.bat.', 'head')
    elif '--no-browser' in argv:
        if sys.stdout:
            print(url, flush=True)
    else:
        open_ui(url)
    try:
        srv.serve_forever()
    finally:
        try:
            os.remove(_info_path())
        except OSError:
            pass


def run():
    """Điểm vào của KhoaVeyon.py: chạy main, lỗi không bắt được thì ghi vào error.log (thư mục data) rồi báo lỗi tiếp."""
    try:
        main()
    except Exception:  # noqa
        try:
            with open(os.path.join(os.path.dirname(CONFIG_PATH), 'error.log'), 'a', encoding='utf-8') as f:
                f.write(time.strftime('%Y-%m-%d %H:%M:%S') + '\n' + traceback.format_exc() + '\n')
        except OSError:
            pass
        raise
