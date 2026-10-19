# -*- coding: utf-8 -*-
"""Bảng ánh xạ đường dẫn API sang hàm xử lý."""

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
from .health import api_health_fix
from .exam import api_exam, api_exam_end, api_exam_start
from .examlock import api_exam_collect, api_exam_release
from .khoalink import (
    api_kq_compare, api_kq_exams, api_kq_link, api_kq_rosters_import, api_kq_rosters_preview, api_kq_status, api_kq_unlink,
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


GET_ROUTES = {'/api/update_check': api_update_check, '/api/setup_status': api_setup_status, '/api/state': api_state, '/api/list': api_list_get, '/api/list_variant': api_list_variant_get, '/api/payload': api_payload,
              '/api/log': api_log, '/api/school': api_school, '/api/school_students': api_school_students, '/api/school_attendance': api_school_attendance, '/api/alerts': api_alerts, '/api/report': api_report, '/api/ping': api_ping, '/api/vcfg_info': api_vcfg_info, '/api/status': api_status, '/api/hostnames': api_hostnames, '/api/auto': api_auto, '/api/exam': api_exam, '/api/privacy': api_privacy, '/api/gallery': api_gallery, '/api/applock': api_applock,
              '/api/kq_status': api_kq_status, '/api/kq_rosters_preview': api_kq_rosters_preview, '/api/kq_compare': api_kq_compare, '/api/kq_exams': api_kq_exams, '/api/selftest_result': api_selftest_result}
POST_ROUTES = {'/api/kq_link': api_kq_link, '/api/kq_unlink': api_kq_unlink, '/api/kq_rosters_import': api_kq_rosters_import, '/api/kt_export': api_kt_export,
               '/api/school_set': api_school_set, '/api/school_attendance_set': api_school_attendance_set, '/api/school_announce': api_school_announce, '/api/school_layout': api_school_layout, '/api/update_apply': api_update_apply, '/api/setup_run': api_setup_run, '/api/setup_scan': api_setup_scan, '/api/setup_done': api_setup_done,
               '/api/list': api_list_save, '/api/check': api_check, '/api/hosts': api_hosts, '/api/run': api_run,
               '/api/settings': api_settings, '/api/dist': api_dist, '/api/open': api_open,
               '/api/veyon_list': api_veyon_list, '/api/sync': api_sync, '/api/quit': api_quit,
               '/api/payload_delete': api_payload_delete, '/api/vcfg_save': api_vcfg_save, '/api/vcfg_run': api_vcfg_run, '/api/shot': api_shot, '/api/ai_status': api_ai_status, '/api/ai_opts': api_ai_opts, '/api/watch': api_watch, '/api/alerts_clear': api_alerts_clear, '/api/cleanup': api_cleanup, '/api/report_export': api_report_export,
               '/api/power': api_power, '/api/macs_set': api_macs_set, '/api/hostname_set': api_hostname_set, '/api/auto_set': api_auto_set, '/api/auto_test': api_auto_test, '/api/exam_start': api_exam_start, '/api/exam_end': api_exam_end, '/api/health_fix': api_health_fix, '/api/verify': api_verify, '/api/notice': api_notice, '/api/privacy_pin': api_privacy_pin, '/api/privacy_acl': api_privacy_acl, '/api/exam_collect': api_exam_collect, '/api/exam_release': api_exam_release, '/api/list_variant_save': api_list_variant_save, '/api/list_variant_delete': api_list_variant_delete, '/api/startup': api_startup, '/api/logon_policy': api_logon_policy, '/api/evidence_open': api_evidence_open, '/api/applock': api_applock, '/api/selftest': api_selftest}
