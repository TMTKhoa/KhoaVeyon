# -*- coding: utf-8 -*-
"""
KhoaVeyon - công cụ trên máy giáo viên (giao diện web chạy ngay trên máy này).

Chạy: python KhoaVeyon.py     (cần: pip install openpyxl)

File này chỉ là điểm khởi động. Mã chương trình nằm trong thư mục kv/ (xem README-KhoaVeyon.md, mục
"Cấu trúc mã nguồn"), script gửi xuống máy học sinh nằm trong scripts/, giao diện trong web/.
"""
import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)


def _repair():
    """Bản cập nhật tự động đời cũ (trước 3.5.0) chỉ chép KhoaVeyon.py và web/, nên thiếu kv/ và scripts/.
    Tải bản phát hành mới nhất của kho GitHub (https, chỉ github.com) để bổ sung hai thư mục đó.
    Trả về True nếu đã bổ sung được."""
    import io
    import json
    import shutil
    import urllib.request
    import zipfile
    repo = 'TMTKhoa/KhoaVeyon'
    try:
        with open(os.path.join(APP_DIR, 'data', 'KhoaVeyon.json'), 'r', encoding='utf-8') as f:
            repo = json.load(f).get('update_repo') or repo
    except (OSError, ValueError):
        pass

    def get(url):
        if not url.startswith('https://') or url.split('/')[2].split(':')[0] not in (
                'api.github.com', 'github.com', 'codeload.github.com', 'objects.githubusercontent.com'):
            raise ValueError('Địa chỉ không hợp lệ: ' + url)
        req = urllib.request.Request(url, headers={'User-Agent': 'KhoaVeyon-repair'})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read(80 * 1024 * 1024)

    def extract(z):
        for n in z.namelist():
            parts = n.replace('\\', '/').split('/')
            if n.startswith(('/', '\\')) or '..' in parts or ':' in parts[0]:
                return False
        mains = [n for n in z.namelist() if n.replace('\\', '/').split('/')[-1] == 'KhoaVeyon.py']
        root = min(mains, key=len)[:-len('KhoaVeyon.py')] if mains else ''
        if not any(n.startswith(root + 'kv/') for n in z.namelist()):
            return False
        for n in z.namelist():
            rel_path = n[len(root):] if n.startswith(root) else ''
            if rel_path.endswith('/') or not rel_path.startswith(('kv/', 'scripts/', 'web/')):
                continue
            dst = os.path.join(APP_DIR, *rel_path.split('/'))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with z.open(n) as src, open(dst + '.new', 'wb') as out:
                shutil.copyfileobj(src, out)
            os.replace(dst + '.new', dst)
        return True

    # Có sẵn file KhoaVeyon-x.y.z.zip trong thư mục update/ thì dùng luôn (không cần Internet/GitHub)
    try:
        updir = os.path.join(APP_DIR, 'update')
        for name in sorted(os.listdir(updir), reverse=True):
            if name.lower().endswith('.zip'):
                try:
                    with zipfile.ZipFile(os.path.join(updir, name)) as z:
                        if extract(z):
                            return True
                except (OSError, zipfile.BadZipFile):
                    continue
    except OSError:
        pass
    try:
        rel = json.loads(get('https://api.github.com/repos/%s/releases/latest' % repo).decode('utf-8'))
        return extract(zipfile.ZipFile(io.BytesIO(get(rel['zipball_url']))))
    except Exception:  # noqa
        return False


def _fail(msg):
    """pythonw không có cửa sổ lệnh nên báo lỗi bằng hộp thoại Windows và ghi vào data\\error.log."""
    try:
        os.makedirs(os.path.join(APP_DIR, 'data'), exist_ok=True)
        with open(os.path.join(APP_DIR, 'data', 'error.log'), 'a', encoding='utf-8') as f:
            f.write(msg + '\n')
    except OSError:
        pass
    if os.name == 'nt' and not os.environ.get('KHOAVEYON_NO_DIALOG'):
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, msg, 'KhoaVeyon', 0x10)  # noqa
        except Exception:  # noqa
            pass
    else:
        print(msg, file=sys.stderr)
    sys.exit(1)


def _load():
    try:
        from kv.app import run
        return run
    except ModuleNotFoundError as e:
        if (e.name or '').split('.')[0] != 'kv':
            raise
    if not _repair():
        _fail('Thiếu thư mục kv (bản cập nhật cũ chỉ chép KhoaVeyon.py).\n'
              'Hãy tải bản KhoaVeyon mới nhất từ GitHub, giải nén đè lên thư mục chương trình '
              '(data, lists, payload giữ nguyên) rồi chạy lại. Máy không có Internet: chép file KhoaVeyon-x.y.z.zip '
              'vào thư mục update\\ cạnh chương trình rồi chạy lại, chương trình tự bổ sung.')
    from kv.app import run
    return run


if __name__ == '__main__':
    _load()()
