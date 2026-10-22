# -*- coding: utf-8 -*-
"""Vòng lặp nền: cứ vài giây lấy ảnh vi phạm mới từ các máy đang giám sát và định kỳ dọn dữ liệu cũ."""

import json
import time

from concurrent.futures import ThreadPoolExecutor, as_completed

from .alerts import (
    alert_beep, alert_collect_host, ALERT_LOCK, ALERT_SEQ, alert_should_beep, ALERTS, HOST_ONLINE,
    PUSH_CAPABLE, PUSH_FALLBACK_SEC, PUSH_FRESH_SEC,
)
from .cleanup import evidence_cleanup
from .evidence import watch_num
from .runtime import CFG, CFG_LOCK, log


LAST_POLL = {}


def alert_loop():
    """Chạy nền: cứ vài giây lại lấy ảnh vi phạm mới từ các máy đang giám sát."""
    last_clean = 0
    while True:
        wait = 3
        try:
            with CFG_LOCK:
                cfg = json.loads(json.dumps(CFG))
            wait = watch_num(cfg, 'alert_poll', 3, 2, 60)
            hosts = list(cfg.get('watch_hosts') or [])
            # Máy đã có script giám sát mới (tự báo "hello" và đẩy ảnh về ngay khi vi phạm) chỉ cần quét dự phòng thưa,
            # để giảm tải mạng phòng máy; máy chưa báo hello vẫn quét mỗi vài giây như cũ.
            now_t = time.time()
            hosts = [h for h in hosts if not (now_t - PUSH_CAPABLE.get(h, 0) < PUSH_FRESH_SEC and now_t - LAST_POLL.get(h, 0) < PUSH_FALLBACK_SEC)]
            for h in hosts:
                LAST_POLL[h] = now_t
            if hosts:
                before = ALERT_SEQ[0]
                with ThreadPoolExecutor(max_workers=min(16, len(hosts))) as ex:
                    futs = {ex.submit(alert_collect_host, cfg, h): h for h in hosts}
                    for fut in as_completed(futs):
                        h = futs[fut]
                        try:
                            ok, msg = fut.result()[:2]
                        except Exception as e:  # noqa
                            ok, msg = False, str(e)
                        prev = HOST_ONLINE.get(h)
                        if ok != prev:  # chỉ ghi nhật ký khi trạng thái đổi, tránh đầy nhật ký
                            HOST_ONLINE[h] = ok
                            if not ok:
                                log('[%s] không nhận được ảnh vi phạm: %s' % (h, msg), 'warn')
                            elif prev is False:
                                log('[%s] đã kết nối lại, tiếp tục nhận ảnh vi phạm' % h, 'ok')
                with ALERT_LOCK:
                    fresh = [e for e in ALERTS if e['id'] > before]
                if alert_should_beep(fresh, watch_num(cfg, 'alert_group_sec', 60, 10, 3600)):
                    alert_beep()
            if time.time() - last_clean > 6 * 3600:  # dọn ảnh cũ khi mở chương trình rồi mỗi 6 giờ
                last_clean = time.time()
                r = evidence_cleanup(watch_num(cfg, 'keep_days', 14, 0, 3650), watch_num(cfg, 'keep_records_days', 180, 0, 3650))
                if r['images'] or r['records'] or r['shots']:
                    log('Đã dọn dữ liệu vi phạm cũ: %d ảnh, %d bản ghi, %d thư mục ảnh chụp' % (r['images'], r['records'], r['shots']), 'head')
        except Exception as e:  # noqa
            log('Lỗi khi nhận ảnh vi phạm: %s' % e, 'err')
        time.sleep(wait)
