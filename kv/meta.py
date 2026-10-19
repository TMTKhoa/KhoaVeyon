# -*- coding: utf-8 -*-
"""Hằng số mô tả giao diện và cài đặt: nhóm nút, biểu tượng, danh sách khóa cài đặt, cổng Veyon."""



GROUPS = [
    ('Khóa máy', ['lockall-start', 'lockall-stop', 'lockrun-start', 'lockrun-stop', 'lockapp-start', 'lockapp-stop']),
    ('Ứng dụng', ['killapp', 'keepapp', 'blockapp', 'unblockapp']),
    ('Internet', ['blockall', 'allowpage', 'webonly', 'weboff', 'allowall']),
    ('Công cụ AI', ['blockai', 'allowai']),
    ('Hệ thống và âm thanh', ['lockdown', 'unlock', 'mute', 'unmute', 'clearhistory']),
]
ICONS = {
    'lockall-start': '🔒', 'lockall-stop': '🔓', 'lockrun-start': '⛔', 'lockrun-stop': '✅',
    'lockapp-start': '🖥️', 'lockapp-stop': '🔙', 'killapp': '✖️', 'keepapp': '🧹',
    'blockall': '🚫', 'allowpage': '🌐', 'webonly': '🧭', 'weboff': '🌍', 'allowall': '📶', 'blockapp': '🎮', 'unblockapp': '✅',
    'lockdown': '🛡️', 'unlock': '🗝️', 'mute': '🔇', 'unmute': '🔊', 'clearhistory': '🗑️',
    'blockai': '🤖', 'allowai': '✅',
}
# Nút cam = bật hạn chế, nút xanh lá = gỡ hạn chế, nút xám = việc khác
LOCK_KEYS = {'lockall-start', 'lockrun-start', 'lockapp-start', 'blockall', 'allowpage', 'webonly', 'blockapp',
             'lockdown', 'killapp', 'keepapp', 'clearhistory', 'blockai'}
FREE_KEYS = {'lockall-stop', 'lockrun-stop', 'lockapp-stop', 'allowall', 'weboff', 'unblockapp', 'unlock', 'allowai'}

STR_KEYS = ['list_dir', 'script_path', 'veyon_cli', 'run_template', 'list_template', 'sync_dir',
            'dist_target', 'dist_mode', 'dist_cmd', 'dist_action', 'update_repo', 'update_skip', 'watch_repeat', 'watch_max', 'alert_poll', 'alert_group_sec', 'keep_days', 'keep_records_days', 'school_name']
BOOL_KEYS = ['auto_sync', 'auto_push', 'dist_include_lists', 'dist_interactive', 'setup_done', 'auto_lock', 'update_check', 'update_auto', 'shot_before_lock', 'lock_with_ai', 'alert_sound', 'alert_popup', 'watch_autostart', 'reapply_on_boot', 'watch_disclose', 'watch_notify_student', 'ai_block_overviews', 'ai_disable_doh', 'ai_block_ext']
LIST_KEYS = ['dist_files', 'dist_payload_skip']

VEYON_PORT = 11100
