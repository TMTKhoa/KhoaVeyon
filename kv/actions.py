# -*- coding: utf-8 -*-
"""Danh sách lệnh điều khiển lớp: nút trên giao diện, tham số của KhoaVeyonServices.bat, tên mục trong Veyon."""



# (khóa, nhãn nút, tham số của script, tên mục mặc định trong Veyon "Programs & websites")
ACTIONS = [
    ('lockall-start', 'Khóa toàn bộ (chỉ app trong danh sách)', '-lockall-start', 'Khóa toàn bộ (chỉ app trong danh sách)'),
    ('lockall-stop', 'Mở khóa toàn bộ', '-lockall-stop', 'Mở khóa toàn bộ'),
    ('lockrun-start', 'Chỉ chặn mở app ngoài danh sách', '-lockrun-start', 'Chỉ chặn mở app ngoài danh sách'),
    ('lockrun-stop', 'Gỡ chặn mở app', '-lockrun-stop', 'Gỡ chặn mở app'),
    ('lockapp-start', 'Bật chế độ kiosk', '-lockapp-start', 'Bật chế độ kiosk'),
    ('lockapp-stop', 'Tắt chế độ kiosk', '-lockapp-stop', 'Tắt chế độ kiosk'),
    ('killapp', 'Đóng tất cả ứng dụng', '-killapp', 'Đóng tất cả ứng dụng'),
    ('keepapp', 'Đóng tất cả trừ danh sách', '-keepapp', 'Đóng tất cả trừ danh sách'),
    ('blockall', 'Chặn internet', '-blockall', 'Chặn internet'),
    ('allowpage', 'Chỉ trang trong danh sách (tường lửa IP)', '-allowpage', 'Chỉ cho phép các trang trong danh sách'),
    ('webonly', 'Chỉ trang trong danh sách (trình duyệt, gồm miền con)', '-webonly', 'Chỉ trang cho phép (trình duyệt)'),
    ('weboff', 'Bỏ chỉ-trang-cho-phép (trình duyệt)', '-weboff', 'Bỏ chỉ trang cho phép (trình duyệt)'),
    ('allowall', 'Cho phép internet', '-allowall', 'Cho phép internet'),
    ('blockapp', 'Chặn ứng dụng trong danh sách', '-blockapp', 'Chặn ứng dụng'),
    ('unblockapp', 'Bỏ chặn ứng dụng', '-unblockapp', 'Bỏ chặn ứng dụng'),
    ('lockdown', 'Khóa Task Manager / Settings', '-lockdown', 'Khóa (Lockdown)'),
    ('unlock', 'Mở khóa Task Manager / Settings', '-unlock', 'Mở khóa (Unlock)'),
    ('desklock-start', 'Khóa hình nền và icon Desktop', '-desklock-start', 'Khóa hình nền và icon Desktop'),
    ('desklock-stop', 'Mở khóa hình nền và icon Desktop', '-desklock-stop', 'Mở khóa hình nền và icon Desktop'),
    ('mute', 'Tắt tiếng loa', '-mute', 'Tắt tiếng'),
    ('unmute', 'Bật tiếng loa', '-unmute', 'Bật tiếng'),
    ('clearhistory', 'Xóa lịch sử Chrome/Firefox', '-clearhistory', 'Xóa lịch sử trình duyệt'),
    ('blockai', 'Khóa toàn bộ công cụ AI', '-blockai', 'Khóa toàn bộ AI'),
    ('allowai', 'Mở khóa công cụ AI', '-allowai', 'Mở khóa AI'),
]
ACTION_BY_KEY = {a[0]: a for a in ACTIONS}
# Các lệnh có thể làm mất bài chưa lưu của học sinh, nên hỏi lại trước khi chạy
CONFIRM_KEYS = {'desklock-start', 'lockall-start', 'lockrun-start', 'lockapp-start', 'killapp', 'keepapp', 'clearhistory', 'blockai'}
