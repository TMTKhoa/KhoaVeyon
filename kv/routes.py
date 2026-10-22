# -*- coding: utf-8 -*-
"""Bảng ánh xạ đường dẫn API sang hàm xử lý."""

from .agent import api_agent
from .ai import api_ai_opts, api_ai_status
from .applock import api_applock
from .alerts import api_alerts, api_alerts_clear
from .announce import api_notice, api_school_announce
from .api_core import (
    api_dist, api_log, api_open, api_payload, api_payload_delete, api_ping, api_quit, api_run, api_settings,
    api_setup_done, api_setup_run, api_setup_scan, api_setup_status, api_sync, api_update_apply,
    api_update_check, api_veyon_list,
)
from .api_lists import (
    api_check, api_hosts, api_list_get, api_list_save, api_list_variant_delete, api_list_variant_get,
    api_list_variant_save, api_state,
)
from .attendance import api_school_attendance, api_school_attendance_set
from .auto import api_auto, api_auto_set, api_auto_test
from .cleanup import api_cleanup
from .gallery import api_evidence_open, api_gallery
from .autoupdate import api_update_students
from .health import api_health_fix
from .backup_api import api_backup_preview, api_backup_restore
from .diagnose import api_diagnose, api_diagnose_fix
from .phone import api_phone_start, api_phone_state, api_phone_stop
from .classroom import api_share_clear, api_share_push, api_share_snap, api_share_state, api_handout_send, api_open_url, api_quiz_end, api_quiz_start, api_quiz_state
from .fun import api_quick_notes, api_quick_notes_save, api_countdown, api_groups, api_react_clear, api_star, api_stars, api_stars_reset
from .uiprefs import api_ui_prefs, api_ui_prefs_save
from .board import api_act_option, api_seat_auto, api_seat_hostmap, api_monitor, api_monitor_live, api_monitor_thumbs
from .engage import api_draw, api_hand_option, api_lock_style, api_lock_style_save, api_wall, api_wall_img, api_wall_apply, api_wall_bg, api_wall_preset_delete, api_wall_preset_save, api_wall_restore
from .student import api_hand_clear, api_student, api_student_send
from .usage import api_usage
from .exam import api_exam, api_exam_end, api_exam_start
from .examlock import api_exam_collect, api_exam_release
from .khoalink import (
    api_kq_compare, api_kq_exams, api_kq_live, api_kq_live_open, api_kq_live_set, api_kq_link, api_kq_rosters_import, api_kq_rosters_preview, api_kq_status, api_kq_unlink,
    api_kt_export,
)
from .logonpolicy import api_logon_policy
from .power import api_hostname_set, api_hostnames, api_macs_set, api_power
from .privacy import api_privacy, api_privacy_acl, api_privacy_pin
from .reports import api_report, api_report_export
from .startup import api_startup
from .school_api import api_school, api_school_layout, api_school_set, api_school_students
from .selftest import api_selftest, api_selftest_result
from .screenshot import api_shot
from .status import api_status
from .verify import api_verify
from .vcfg import api_vcfg_info, api_vcfg_run, api_vcfg_save
from .watch import api_watch


GET_ROUTES = {'/api/phone_state': api_phone_state, '/api/share_state': api_share_state, '/api/quiz_state': api_quiz_state, '/api/quick_notes': api_quick_notes, '/api/ui_prefs': api_ui_prefs, '/api/stars': api_stars, '/api/monitor_thumbs': api_monitor_thumbs, '/api/monitor': api_monitor, '/api/lock_style': api_lock_style, '/api/wall': api_wall, '/api/wall_img': api_wall_img, '/api/student': api_student, '/api/update_check': api_update_check, '/api/setup_status': api_setup_status, '/api/state': api_state, '/api/list': api_list_get, '/api/list_variant': api_list_variant_get, '/api/payload': api_payload,
              '/api/log': api_log, '/api/school': api_school, '/api/school_students': api_school_students, '/api/school_attendance': api_school_attendance, '/api/alerts': api_alerts, '/api/report': api_report, '/api/ping': api_ping, '/api/vcfg_info': api_vcfg_info, '/api/status': api_status, '/api/hostnames': api_hostnames, '/api/auto': api_auto, '/api/exam': api_exam, '/api/privacy': api_privacy, '/api/gallery': api_gallery, '/api/applock': api_applock, '/api/agent': api_agent,
              '/api/kq_status': api_kq_status, '/api/kq_rosters_preview': api_kq_rosters_preview, '/api/kq_compare': api_kq_compare, '/api/kq_exams': api_kq_exams, '/api/kq_live': api_kq_live, '/api/selftest_result': api_selftest_result}
POST_ROUTES = {'/api/phone_start': api_phone_start, '/api/phone_stop': api_phone_stop, '/api/share_snap': api_share_snap, '/api/share_push': api_share_push, '/api/share_clear': api_share_clear, '/api/quiz_start': api_quiz_start, '/api/quiz_end': api_quiz_end, '/api/open_url': api_open_url, '/api/handout_send': api_handout_send, '/api/quick_notes_save': api_quick_notes_save, '/api/seat_auto': api_seat_auto, '/api/ui_prefs_save': api_ui_prefs_save, '/api/star': api_star, '/api/stars_reset': api_stars_reset, '/api/countdown': api_countdown, '/api/groups': api_groups, '/api/react_clear': api_react_clear, '/api/seat_hostmap': api_seat_hostmap, '/api/monitor_live': api_monitor_live, '/api/act_option': api_act_option, '/api/lock_style_save': api_lock_style_save, '/api/hand_option': api_hand_option, '/api/draw': api_draw, '/api/wall_apply': api_wall_apply, '/api/wall_restore': api_wall_restore, '/api/wall_bg': api_wall_bg, '/api/wall_preset_save': api_wall_preset_save, '/api/wall_preset_delete': api_wall_preset_delete, '/api/student_send': api_student_send, '/api/hand_clear': api_hand_clear, '/api/usage': api_usage, '/api/diagnose': api_diagnose, '/api/diagnose_fix': api_diagnose_fix, '/api/backup_preview': api_backup_preview, '/api/backup_restore': api_backup_restore, '/api/kq_live_set': api_kq_live_set, '/api/kq_live_open': api_kq_live_open, '/api/kq_link': api_kq_link, '/api/kq_unlink': api_kq_unlink, '/api/kq_rosters_import': api_kq_rosters_import, '/api/kt_export': api_kt_export,
               '/api/school_set': api_school_set, '/api/school_attendance_set': api_school_attendance_set, '/api/school_announce': api_school_announce, '/api/school_layout': api_school_layout, '/api/update_apply': api_update_apply, '/api/setup_run': api_setup_run, '/api/setup_scan': api_setup_scan, '/api/setup_done': api_setup_done,
               '/api/list': api_list_save, '/api/check': api_check, '/api/hosts': api_hosts, '/api/run': api_run,
               '/api/settings': api_settings, '/api/dist': api_dist, '/api/open': api_open,
               '/api/veyon_list': api_veyon_list, '/api/sync': api_sync, '/api/quit': api_quit,
               '/api/payload_delete': api_payload_delete, '/api/vcfg_save': api_vcfg_save, '/api/vcfg_run': api_vcfg_run, '/api/shot': api_shot, '/api/ai_status': api_ai_status, '/api/ai_opts': api_ai_opts, '/api/watch': api_watch, '/api/alerts_clear': api_alerts_clear, '/api/cleanup': api_cleanup, '/api/report_export': api_report_export,
               '/api/power': api_power, '/api/macs_set': api_macs_set, '/api/hostname_set': api_hostname_set, '/api/auto_set': api_auto_set, '/api/auto_test': api_auto_test, '/api/exam_start': api_exam_start, '/api/exam_end': api_exam_end, '/api/health_fix': api_health_fix, '/api/update_students': api_update_students, '/api/verify': api_verify, '/api/notice': api_notice, '/api/privacy_pin': api_privacy_pin, '/api/privacy_acl': api_privacy_acl, '/api/exam_collect': api_exam_collect, '/api/exam_release': api_exam_release, '/api/list_variant_save': api_list_variant_save, '/api/list_variant_delete': api_list_variant_delete, '/api/startup': api_startup, '/api/logon_policy': api_logon_policy, '/api/evidence_open': api_evidence_open, '/api/applock': api_applock, '/api/selftest': api_selftest, '/api/agent': api_agent}
