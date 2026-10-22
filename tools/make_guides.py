# -*- coding: utf-8 -*-
"""Tạo các ảnh động hướng dẫn thao tác (GIF) cho học sinh: python tools/make_guides.py  ->  web/assets/guide-*.gif
Chỉ cần chạy lại khi muốn đổi hình; các tệp GIF đã được đóng gói sẵn trong web/assets."""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 560, 315
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web', 'assets')
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FR = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BG, PANEL, INK, MUT, BLUE, GREEN, ORANGE, RED, KEY, KEYSH = '#f1f5f9', '#ffffff', '#0f172a', '#64748b', '#2563eb', '#16a34a', '#ea580c', '#dc2626', '#e2e8f0', '#94a3b8'


SC = 2          # vẽ gấp đôi rồi thu nhỏ cho nét mịn
OUTW, OUTH = 720, 405


def font(sz, bold=True):
    return ImageFont.truetype(FB if bold else FR, int(sz * SC))


def _s(v):
    if isinstance(v, (tuple, list)):
        return tuple(_s(x) for x in v)
    return v * SC if isinstance(v, (int, float)) else v


class Dr:
    """Bọc ImageDraw: nhận toạ độ logic (560x315) và tự nhân lên SC lần."""
    def __init__(self, im):
        self.d = ImageDraw.Draw(im)

    def rounded_rectangle(self, xy, r=0, width=1, **kw):
        self.d.rounded_rectangle(_s(xy), _s(r), width=int(width * SC) if kw.get('outline') else width, **kw)

    def rectangle(self, xy, width=1, **kw):
        self.d.rectangle(_s(xy), width=int(width * SC), **kw)

    def ellipse(self, xy, width=1, **kw):
        self.d.ellipse(_s(xy), width=int(width * SC), **kw)

    def pieslice(self, xy, a, b, **kw):
        self.d.pieslice(_s(xy), a, b, **kw)

    def line(self, xy, fill=None, width=1):
        self.d.line(_s(xy), fill=fill, width=int(width * SC))

    def polygon(self, pts, **kw):
        self.d.polygon(_s(pts), **kw)

    def text(self, xy, s, font=None, fill=None, anchor='la'):
        self.d.text(_s(xy), s, font=font, fill=fill, anchor=anchor)


def txt(d, xy, s, sz=18, fill=INK, bold=True, anchor='la'):
    d.text(xy, s, font=font(sz, bold), fill=fill, anchor=anchor)


def gradient():
    top, bot = (233, 240, 255), (248, 250, 252)
    im = Image.new('RGB', (W * SC, H * SC))
    px = ImageDraw.Draw(im)
    for y in range(H * SC):
        t = y / (H * SC - 1)
        px.line((0, y, W * SC, y), fill=tuple(int(top[k] + (bot[k] - top[k]) * t) for k in range(3)))
    return im


def keycap(d, x, y, label, pressed=False, w=None, sz=20):
    w = w or max(64, 24 + 13 * len(label))
    h = 52
    off = 4 if pressed else 0
    if not pressed:
        d.rounded_rectangle((x, y + 5, x + w, y + h + 5), 10, fill=KEYSH)
    d.rounded_rectangle((x, y + off, x + w, y + h + off), 10, fill=BLUE if pressed else KEY, outline='#94a3b8')
    txt(d, (x + w / 2, y + off + h / 2), label, sz, 'white' if pressed else INK, anchor='mm')
    return w


def keys_row(d, y, combo, active):
    """combo: danh sách phím; active: tập chỉ số phím đang được nhấn."""
    widths = [max(64, 24 + 13 * len(k)) for k in combo]
    total = sum(widths) + 34 * (len(combo) - 1)
    x = 20
    for i, k in enumerate(combo):
        keycap(d, x, y, k, i in active, widths[i])
        x += widths[i]
        if i < len(combo) - 1:
            txt(d, (x + 17, y + 26), '+', 24, MUT, anchor='mm')
            x += 34
    return total


def mouse(d, cx, cy, wheel=0, click=False):
    d.rounded_rectangle((cx - 30, cy - 48, cx + 30, cy + 48), 28, fill='white', outline='#475569', width=3)
    d.line((cx - 30, cy - 8, cx + 30, cy - 8), fill='#475569', width=2)
    d.line((cx, cy - 48, cx, cy - 8), fill='#475569', width=2)
    d.rounded_rectangle((cx - 7, cy - 38, cx + 7, cy - 14), 6, fill=ORANGE if wheel else '#cbd5e1')
    if click:
        d.pieslice((cx - 30, cy - 48, cx, cy - 8), 180, 270, fill=BLUE)
    if wheel:
        ay = cy - 62 if wheel > 0 else cy + 8
        pts = [(cx, ay - 12), (cx - 12, ay + 4), (cx + 12, ay + 4)] if wheel > 0 else [(cx, ay + 12), (cx - 12, ay - 4), (cx + 12, ay - 4)]
        d.polygon(pts, fill=ORANGE)


def window(d, x, y, w, h, title=''):
    d.rounded_rectangle((x, y, x + w, y + h), 10, fill=PANEL, outline='#94a3b8')
    d.rounded_rectangle((x, y, x + w, y + 24), 10, fill='#cbd5e1')
    d.rectangle((x, y + 14, x + w, y + 24), fill='#cbd5e1')
    for i, c in enumerate((RED, '#f59e0b', GREEN)):
        d.ellipse((x + 10 + i * 16, y + 8, x + 18 + i * 16, y + 16), fill=c)
    if title:
        txt(d, (x + w / 2, y + 12), title, 11, MUT, anchor='mm')


KID = [False]      # bản cho lớp nhỏ: chữ to, câu ngắn, từ dễ hiểu
KID_TEXT = {
    'Phóng to / thu nhỏ': 'Làm chữ TO và NHỎ', 'Sao chép và dán': 'Chép chữ sang chỗ khác', 'Hoàn tác (quay lại bước trước)': 'Làm nhầm? Quay lại!',
    'Lưu bài': 'Cất bài làm của em', 'Chuyển qua lại giữa các cửa sổ': 'Đổi sang cửa sổ khác', 'Chụp một vùng màn hình': 'Chụp hình màn hình',
    'Chọn toàn bộ nội dung': 'Chọn hết các chữ', 'Tìm chữ trong trang': 'Tìm chữ trong trang',
    'Giữ Ctrl + lăn con lăn LÊN: PHÓNG TO': 'Giữ Ctrl, lăn LÊN: chữ TO ra!', 'Giữ Ctrl + lăn con lăn XUỐNG: THU NHỎ': 'Giữ Ctrl, lăn XUỐNG: chữ NHỎ lại!',
    'Bôi đen nội dung cần chép': 'Tô xanh chữ cần chép', 'Nhấn Ctrl + C (sao chép)': 'Bấm Ctrl và C cùng lúc', 'Bấm vào chỗ cần dán': 'Bấm vào chỗ muốn để chữ',
    'Nhấn Ctrl + V (dán)': 'Bấm Ctrl và V: xong rồi!',
    'Lỡ gõ nhầm hoặc xóa nhầm?': 'Em làm nhầm rồi?', 'Nhấn Ctrl + Z: lùi lại một bước': 'Bấm Ctrl và Z: quay lại!', 'Nhấn thêm lần nữa để lùi tiếp': 'Bấm thêm để quay lại nữa',
    'Dấu * nghĩa là CHƯA lưu': 'Dấu * là chưa cất bài', 'Nhấn Ctrl + S để lưu': 'Bấm Ctrl và S để cất', 'Đã lưu! Nhớ lưu thường xuyên': 'Đã cất bài. Giỏi lắm!',
    'Giữ phím Alt': 'Giữ phím Alt', 'Gõ Tab để chọn cửa sổ khác': 'Bấm Tab để đổi cửa sổ', 'Thả phím: cửa sổ được chọn hiện lên': 'Thả tay ra: cửa sổ mới hiện lên',
    'Nhấn Win + Shift + S': 'Bấm Win, Shift và S', 'Kéo chuột chọn vùng cần chụp': 'Kéo chuột chọn hình cần chụp', 'Xong! Nhấn Ctrl + V để dán ảnh vào bài': 'Xong! Bấm Ctrl và V để dán hình',
    'Nhiều dòng chữ cần chọn hết?': 'Muốn chọn hết các chữ?', 'Nhấn Ctrl + A: chọn tất cả': 'Bấm Ctrl và A: chọn hết!', 'Giờ có thể Ctrl + C để chép hết': 'Giờ em có thể chép hết',
    'Nhấn Ctrl + F để mở ô tìm kiếm': 'Bấm Ctrl và F cùng lúc', 'Gõ từ cần tìm': 'Gõ chữ cần tìm', 'Các chỗ tìm thấy được tô vàng': 'Chữ tìm thấy được tô vàng!',
}


def kid(s):
    return KID_TEXT.get(s, s) if KID[0] else s


def caption(d, s, color=INK):
    sz = 22 if KID[0] else 17
    d.rounded_rectangle((12, H - 52, W - 12, H - 8), 22, fill=color)
    txt(d, (W / 2, H - 30), kid(s), sz, 'white', anchor='mm')


def base(title):
    im = gradient()
    d = Dr(im)
    d.rounded_rectangle((0, 0, W, 44), 0, fill=BLUE)
    txt(d, (20, 22), kid(title), 21 if KID[0] else 19, 'white', anchor='lm')
    return im, d


def ease(t):
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ các cảnh
def g_zoom():
    frames = []
    for i in range(24):
        im, d = base('Phóng to / thu nhỏ')
        zin = i < 12
        t = ease((i % 12) / 11) if zin else ease((i - 12) / 11)
        size = 22 + 38 * (t if zin else 1 - t)
        keys_row(d, 62, ['Ctrl'], {0})
        mouse(d, 100, 190, wheel=1 if zin else -1)
        window(d, 230, 56, 310, 190, 'Bai-viet.docx')
        txt(d, (385, 150), 'Chữ A', int(size), INK, anchor='mm')
        caption(d, 'Giữ Ctrl + lăn con lăn LÊN: PHÓNG TO' if zin else 'Giữ Ctrl + lăn con lăn XUỐNG: THU NHỎ', GREEN if zin else ORANGE)
        frames.append(im)
    return frames


def g_copy():
    frames = []
    for i in range(24):
        im, d = base('Sao chép và dán')
        phase = 0 if i < 8 else (1 if i < 12 else (2 if i < 20 else 3))
        keys_row(d, 62, ['Ctrl', 'C'] if phase < 2 else ['Ctrl', 'V'], {0, 1} if phase in (1, 3) else ({0, 1} if phase == 3 else set()))
        window(d, 20, 140, 240, 110, 'Nguồn')
        sel = phase >= 0
        d.rectangle((40, 176, 150, 204), fill='#bfdbfe' if phase >= 0 else PANEL)
        txt(d, (45, 180), 'Hà Nội', 20, INK)
        window(d, 300, 140, 240, 110, 'Đích')
        if phase >= 2:
            txt(d, (320, 180), 'Hà Nội', 20, INK)
        if phase == 3:
            d.ellipse((470, 178, 496, 204), fill=GREEN); txt(d, (483, 191), '✓', 16, 'white', anchor='mm')
        caption(d, ['Bôi đen nội dung cần chép', 'Nhấn Ctrl + C (sao chép)', 'Bấm vào chỗ cần dán', 'Nhấn Ctrl + V (dán)'][phase], BLUE if phase != 3 else GREEN)
        frames.append(im)
    return frames


def g_undo():
    frames = []
    word = 'Xin chào!'
    for i in range(20):
        im, d = base('Hoàn tác (quay lại bước trước)')
        phase = 0 if i < 8 else (1 if i < 12 else 2)
        keys_row(d, 62, ['Ctrl', 'Z'], {0, 1} if phase == 1 else set())
        window(d, 120, 140, 320, 110, 'Bai-viet.docx')
        s = word if phase == 0 else (word if i == 8 else (word[:max(0, 9 - (i - 8) * 3)] if phase == 1 else ''))
        txt(d, (140, 180), s + ('|' if i % 2 == 0 else ''), 26, INK)
        caption(d, ['Lỡ gõ nhầm hoặc xóa nhầm?', 'Nhấn Ctrl + Z: lùi lại một bước', 'Nhấn thêm lần nữa để lùi tiếp'][phase], RED if phase == 0 else BLUE)
        frames.append(im)
    return frames


def g_save():
    frames = []
    for i in range(20):
        im, d = base('Lưu bài')
        phase = 0 if i < 8 else (1 if i < 12 else 2)
        keys_row(d, 62, ['Ctrl', 'S'], {0, 1} if phase == 1 else set())
        saved = phase == 2
        window(d, 120, 140, 320, 110, 'Bai-1.docx' + ('' if saved else ' *'))
        txt(d, (140, 180), 'Bài làm của em...', 22, INK)
        if saved:
            d.ellipse((380, 190, 416, 226), fill=GREEN); txt(d, (398, 208), '✓', 22, 'white', anchor='mm')
            txt(d, (330, 206), 'Đã lưu', 18, GREEN, anchor='ra')
        caption(d, ['Dấu * nghĩa là CHƯA lưu', 'Nhấn Ctrl + S để lưu', 'Đã lưu! Nhớ lưu thường xuyên'][phase], ORANGE if phase == 0 else (BLUE if phase == 1 else GREEN))
        frames.append(im)
    return frames


def g_alttab():
    frames = []
    for i in range(24):
        im, d = base('Chuyển qua lại giữa các cửa sổ')
        phase = 0 if i < 6 else (1 if i < 16 else 2)
        keys_row(d, 62, ['Alt', 'Tab'], {0} if phase == 0 else ({0, 1} if (i // 3) % 2 == 0 else {0}) if phase == 1 else set())
        which = 0 if i < 10 else 1
        for k, (x, col, name) in enumerate(((60, '#dbeafe', 'Word'), (320, '#dcfce7', 'Chrome'))):
            window(d, x, 140, 200, 110, name)
            d.rectangle((x + 8, 170, x + 192, 240), fill=col)
            if (phase == 1 and k == which) or (phase == 2 and k == 1):
                d.rounded_rectangle((x - 4, 136, x + 204, 254), 12, outline=ORANGE, width=4)
        caption(d, ['Giữ phím Alt', 'Gõ Tab để chọn cửa sổ khác', 'Thả phím: cửa sổ được chọn hiện lên'][phase], BLUE)
        frames.append(im)
    return frames


def g_snip():
    frames = []
    for i in range(24):
        im, d = base('Chụp một vùng màn hình')
        phase = 0 if i < 6 else (1 if i < 18 else 2)
        keys_row(d, 62, ['Win', 'Shift', 'S'], {0, 1, 2} if phase == 0 else set())
        window(d, 120, 130, 320, 130, 'Màn hình')
        d.rectangle((140, 164, 260, 244), fill='#dbeafe'); d.ellipse((300, 170, 400, 240), fill='#fde68a')
        if phase >= 1:
            t = ease(min(1, (i - 6) / 8))
            x2, y2 = 150 + 220 * t, 160 + 80 * t
            for a in range(int(150), int(x2), 12):
                d.line((a, 160, min(a + 6, x2), 160), fill=INK, width=2); d.line((a, y2, min(a + 6, x2), y2), fill=INK, width=2)
            for b in range(160, int(y2), 12):
                d.line((150, b, 150, min(b + 6, y2)), fill=INK, width=2); d.line((x2, b, x2, min(b + 6, y2)), fill=INK, width=2)
        if phase == 2:
            d.rounded_rectangle((330, 250, 440, 270), 6, fill=INK); txt(d, (385, 260), 'Đã chép ảnh', 11, 'white', anchor='mm')
        caption(d, ['Nhấn Win + Shift + S', 'Kéo chuột chọn vùng cần chụp', 'Xong! Nhấn Ctrl + V để dán ảnh vào bài'][phase], BLUE if phase < 2 else GREEN)
        frames.append(im)
    return frames


def g_selectall():
    frames = []
    for i in range(20):
        im, d = base('Chọn toàn bộ nội dung')
        phase = 0 if i < 6 else (1 if i < 10 else 2)
        keys_row(d, 62, ['Ctrl', 'A'], {0, 1} if phase == 1 else set())
        window(d, 120, 130, 320, 130, 'Bai-viet.docx')
        for k in range(4):
            y = 164 + k * 22
            if phase >= 1:
                d.rectangle((136, y - 2, 136 + 250 - k * 30, y + 16), fill='#bfdbfe')
            d.rectangle((140, y + 2, 140 + 240 - k * 30, y + 10), fill='#94a3b8')
        caption(d, ['Nhiều dòng chữ cần chọn hết?', 'Nhấn Ctrl + A: chọn tất cả', 'Giờ có thể Ctrl + C để chép hết'][phase], BLUE)
        frames.append(im)
    return frames


def g_find():
    frames = []
    for i in range(24):
        im, d = base('Tìm chữ trong trang')
        phase = 0 if i < 6 else (1 if i < 12 else 2)
        keys_row(d, 62, ['Ctrl', 'F'], {0, 1} if phase == 0 else set())
        window(d, 120, 130, 320, 130, 'Trang web')
        if phase >= 1:
            d.rounded_rectangle((300, 150, 436, 176), 6, fill='white', outline=BLUE, width=2)
            txt(d, (308, 154), 'máy tính'[:min(8, 2 + (i - 6))] if phase == 1 else 'máy tính', 15, INK)
        for k in range(4):
            y = 190 + k * 16
            d.rectangle((140, y, 140 + 220 - k * 25, y + 8), fill='#94a3b8')
        if phase == 2:
            d.rectangle((150, 205, 214, 218), fill='#fde047'); d.rectangle((260, 237, 324, 250), fill='#fde047')
        caption(d, ['Nhấn Ctrl + F để mở ô tìm kiếm', 'Gõ từ cần tìm', 'Các chỗ tìm thấy được tô vàng'][phase], BLUE if phase < 2 else GREEN)
        frames.append(im)
    return frames


GUIDES = {'zoom': g_zoom, 'copy': g_copy, 'undo': g_undo, 'save': g_save, 'alttab': g_alttab, 'snip': g_snip, 'selectall': g_selectall, 'find': g_find}


def main():
    os.makedirs(OUT, exist_ok=True)
    for kidmode in (False, True):
        KID[0] = kidmode
        for name, fn in GUIDES.items():
            fr = [f.resize((OUTW, OUTH), Image.LANCZOS) for f in fn()]
            pal = [f.convert('P', palette=Image.ADAPTIVE, colors=96, dither=Image.Dither.NONE) for f in fr]
            fname = name + ('kid' if kidmode else '')
            path = os.path.join(OUT, 'guide-%s.gif' % fname)
            pal[0].save(path, save_all=True, append_images=pal[1:], duration=120 if not kidmode else 150, loop=0, optimize=True, disposal=2)
            fr[len(fr) // 2].save('/tmp/guide-prev-%s.png' % fname)
            print(fname, len(fr), os.path.getsize(path) // 1024, 'KB')


if __name__ == '__main__':
    main()
