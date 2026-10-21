# -*- coding: utf-8 -*-
"""Cài đặt mặc định, đọc và ghi file cài đặt KhoaVeyon.json."""

import json
import os

from .actions import ACTIONS
from .paths import _appdata_config_path, CONFIG_PATH, LEGACY_CONFIG_PATH


DEFAULT_CONFIG = {
    'list_dir': 'lists',  # tương đối so với thư mục chương trình (portable); có thể đặt C:\\cmd
    'script_path': r'C:\cmd\KhoaVeyonServices.bat',
    'veyon_cli': r'C:\Program Files\Veyon\veyon-cli.exe',
    # Lệnh chạy một mục Veyon trên 1 máy. {cli} {host} {feature} sẽ được thay thế.
    'run_template': '"{cli}" feature start {host} "{feature}"',
    'list_template': '"{cli}" feature list {host}',
    'hosts': [],
    'sync_dir': '',
    'auto_sync': False,
    # Phân phối & chạy
    'dist_files': [],
    'dist_include_lists': True,
    'dist_target': r'C:\cmd',
    'action_via': 'auto',     # auto | agent | veyon: nút điều khiển lớp chạy qua Agent (khuyên dùng) hay mục Veyon "Programs & websites"
    'transport': 'auto',      # auto | agent | smb: cách chép file / chạy lệnh trên máy học sinh (xem kv/agent.py)
    'agent_token': '',        # khóa bí mật chung với dịch vụ trên máy học sinh (tự tạo)
    'agent_port': '8767',     # cổng máy giáo viên mở cho dịch vụ trên máy học sinh gọi về
    'agent_host': '',         # để trống = tự lấy IP LAN của máy giáo viên; điền nếu máy có nhiều card mạng
    'dist_mode': 'schtasks',   # none | schtasks | veyon
    'dist_cmd': r'cmd.exe /c C:\cmd\KhoaVeyonServices.bat -lockall-start',
    'dist_action': 'lockall-start',
    'dist_interactive': False,
    'dist_payload_skip': [],   # file trong thư mục payload bị bỏ chọn khi phân phối
    'auto_push': True,   # bấm Lưu ở tab danh sách thì gửi file vừa sửa xuống máy học sinh
    'update_repo': 'TMTKhoa/KhoaVeyon',  # GitHub, dạng chủ-sở-hữu/tên-kho
    'update_check': True,  # tự kiểm tra bản mới mỗi lần khởi động (khi đã điền kho GitHub)
    'update_skip': '',   # bản mới mà giáo viên chọn "Bỏ qua bản này" (không hỏi lại cho đến khi có bản mới hơn)
    'update_auto': False,  # tự cài và khởi động lại khi có bản mới (mặc định tắt, nên xem trước rồi bấm cập nhật)
    'auto_lock': False,  # sau khi thiết lập máy học sinh thì khóa C:\\cmd (học sinh chỉ đọc)
    'client_veyon_cli': r'C:\Program Files\Veyon\veyon-cli.exe',  # đường dẫn veyon-cli trên máy học sinh
    'vcfg_push': [],      # các khóa cấu hình Veyon đẩy xuống máy học sinh: [{'key','value'}]
    'vcfg_restart': True,  # khởi động lại Veyon Service sau khi đẩy cấu hình
    'auth_key_name': '',  # tên cặp khóa xác thực có sẵn trong Veyon; để trống = tự chọn cặp có sẵn, chưa có thì tạo mới
    'netobj_location': '',  # tên nhóm (location) CÓ SẴN trong Veyon Master; để trống = tự chọn nhóm có sẵn, chưa có thì tự tạo
    'shot_before_lock': False,  # chụp màn hình các máy trước khi chạy lệnh khóa / đóng ứng dụng
    'watch_repeat': '10',  # giây giữa hai lần chụp khi học sinh vẫn ở trang/ứng dụng vi phạm
    'watch_max': '5',      # số ảnh tối đa cho mỗi lần vi phạm
    'watch_hosts': [],     # các máy đang được giám sát (chương trình tự nhận ảnh vi phạm từ các máy này)
    'alert_poll': '3',     # giây giữa hai lần nhận ảnh vi phạm từ máy học sinh
    'alert_sound': True,   # kêu bíp trên máy giáo viên khi có vi phạm mới
    'alert_popup': True,   # hiện thông báo nổi (kèm ảnh) khi có vi phạm mới
    'alert_group_sec': '60',  # các vi phạm giống nhau (cùng máy, cùng trang/ứng dụng) cách nhau không quá chừng này giây thì gộp thành một báo động
    'keep_days': '14',     # tự xóa ảnh chụp màn hình cũ hơn chừng này ngày (0 = không tự xóa). Ảnh là dữ liệu nhạy cảm nên giữ ngắn
    'keep_records_days': '180',  # tự xóa bản ghi vi phạm dạng chữ (không có ảnh) cũ hơn chừng này ngày; dùng cho thống kê tuần/tháng
    'school_name': '',      # tên trường, ghi vào đầu tên file ảnh vi phạm
    'ai_block_overviews': True,  # khóa AI: chặn AI Overviews trong Google Search (ép default search udm=14)
    'ai_disable_doh': True,      # khóa AI: tắt DNS-over-HTTPS để chặn bằng hosts không bị lách
    'ai_block_ext': False,       # khóa AI: chặn MỌI extension trình duyệt (tắt hết, không chỉ AI)
    'watch_notify_student': True,  # sau khi máy giáo viên nhận ảnh vi phạm, báo cho học sinh biết mình vừa vi phạm và đã được báo cho giáo viên
    'watch_disclose': True,  # bật giám sát thì hiện nhãn nhỏ “Đang giám sát” trên màn hình học sinh (công khai việc giám sát)
    'auto_update_students': True,   # máy học sinh có Agent mà dịch vụ là bản cũ thì tự chép bản mới và chạy -install
    'reapply_on_boot': True,  # máy học sinh khởi động lại hoặc bật lại thì tự gửi lại các hạn chế đang bật
    'lock_with_ai': False,  # bấm "Khóa toàn bộ" thì khóa luôn AI, bấm "Mở khóa toàn bộ" thì mở AI
    'watch_autostart': True,  # máy học sinh tự chạy lại giám sát mỗi khi có người đăng nhập (kể cả sau khi khởi động lại)
    'host_names': {},     # tên hiển thị do giáo viên đặt cho từng máy: {IP hoặc tên máy: tên hiển thị}; chỉ để nhìn, không đổi tên thật của máy
    'host_auto_names': {},  # tên PC tự dò được từ IP (DNS hoặc NetBIOS): {IP: tên PC}; tên giáo viên đặt (host_names) được ưu tiên
    'macs': {},           # địa chỉ MAC từng máy để bật máy bằng Wake-on-LAN (tự đọc khi máy đang bật)
    'setup_done': False,  # đã chạy thiết lập ban đầu chưa (chưa thì mở trang Thiết lập khi khởi động)
    'features': {a[0]: a[3] for a in ACTIONS},
}


# ---------------------------------------------------------------- cấu hình và lệnh
def load_config():
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    path = CONFIG_PATH
    old_json = os.path.join(os.path.dirname(CONFIG_PATH), 'VeyonHelper.json')  # tên cũ của chương trình
    if not os.path.exists(path) and os.path.exists(old_json):
        path = old_json
    if not os.path.exists(path):
        old = _appdata_config_path()
        path = old if old and os.path.exists(old) else LEGACY_CONFIG_PATH
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for k, v in data.items():
            if k == 'features' and isinstance(v, dict):
                cfg['features'].update(v)
            else:
                cfg[k] = v
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
