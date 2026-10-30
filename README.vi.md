<p align="center"><img src="web/assets/logo.svg" width="150" alt="KhoaVeyon"></p>

<h1 align="center">KhoaVeyon</h1>

<p align="center">
  <a href="README.md">English</a> · <b>Tiếng Việt</b><br>
  Bảng điều khiển lớp học cho <a href="https://veyon.io">Veyon</a>: khóa máy, chặn web/ứng dụng/AI, tổ chức thi, điểm danh, theo dõi vi phạm — ngay trên một trang web ở máy giáo viên.
</p>

<p align="center"><img src="docs/img/control.jpg" alt="Trang điều khiển lớp" width="860"></p>

> KhoaVeyon không thay thế Veyon. Nó điều khiển Veyon (và Agent nhỏ của riêng mình) qua giao diện dễ dùng hơn.

**Phiên bản hiện tại: 5.5.0** (xem [kv/paths.py](kv/paths.py), biến `VERSION`, là nguồn số bản chính thức)

## Tính năng

| | |
|---|---|
| 🎛️ **Điều khiển lớp** | Một nút để khóa, kiosk, chặn internet / ứng dụng / **công cụ AI**, tắt tiếng, đóng ứng dụng, xóa lịch sử trình duyệt |
| 📝 **Chế độ thi** | Chụp màn hình → khóa AI → chỉ cho trang được phép → khóa cài đặt, gộp trong một công tắc |
| 📡 **Trạng thái & nguồn** | Máy nào bật, ai đăng nhập, đang hạn chế gì; bật / tắt / khởi động lại / đăng xuất |
| 📅 **Tự động theo tiết** | Nhập thời khóa biểu từ Excel; vào tiết tự khóa, hết tiết tự mở |
| 🪑 **Sơ đồ & điểm danh** | Sơ đồ chỗ ngồi theo lớp, học sinh vắng, liên kết KhoaQuiz |
| 🚨 **Giám sát vi phạm** | Tự chụp ảnh khi mở trang/ứng dụng cấm, thư viện bằng chứng, báo cáo |
| 📋 **Danh sách Excel** | Sửa ứng dụng/trang được phép, bị chặn, trang AI bằng bảng; tự gửi xuống máy học sinh |
| 🩺 **Chẩn đoán** (nằm trong *Trạng thái máy*) | Bảng xanh/đỏ từng máy (Veyon, Agent, giờ máy, bản dịch vụ, tường lửa) kèm nút sửa; có nút xóa máy IP cũ |
| 💾 **Sao lưu** | Một file .zip chứa máy, lớp, thời khóa biểu, sơ đồ, danh sách; chuyển sang máy giáo viên khác một thao tác |
| 🙋 **Tương tác** | Học sinh giơ tay / nộp bài từ máy; nhắn tin, khóa màn hình kèm lời nhắn, thống kê dùng máy |
| 🔌 **Agent** | Máy giáo viên điều khiển máy học sinh không cần tài khoản quản trị, chia sẻ C$ hay Task Scheduler từ xa |

## Cách hoạt động

```
Máy giáo viên ── KhoaVeyon (giao diện web, Python) ──┬─ veyon-cli ───────────► Veyon Service ┐
                                                     └─ Agent (HTTP, cổng 8767) ◄─ dịch vụ KhoaVeyonAutoLog ┤ Máy học sinh
                                                        chạy KhoaVeyonServices.bat bằng SYSTEM / trong phiên học sinh ┘
```

## Bắt đầu nhanh

1. **Máy giáo viên (Windows, đã cài Veyon Master):** chạy `Chay-KhoaVeyon.bat`. Lần đầu sẽ tự tải Python portable nếu máy chưa có.
2. Vào **Thiết lập ban đầu** → **Thiết lập máy giáo viên**, rồi **🔎 Tìm máy học sinh trong mạng**.
3. **Mỗi máy học sinh, một lần:** chép thư mục `payload`, chuột phải `Setup-MayHocSinh.bat` → *Run as administrator*. File này cài Agent, đồng bộ giờ và in bảng `[OK]/[LOI]` (lưu thêm ở `C:\cmd\KhoaVeyonSetup.log`).

Xong: chọn máy ở **Điều khiển lớp** và bấm nút.

## Hình ảnh

| Lớp & thời khóa biểu | Sơ đồ lớp |
|:--:|:--:|
| <img src="docs/img/school.jpg" width="420"> | <img src="docs/img/seats.jpg" width="420"> |
| **Chế độ thi** | **Trạng thái máy** |
| <img src="docs/img/exam.jpg" width="420"> | <img src="docs/img/status.jpg" width="420"> |

## Xử lý sự cố

| Sự cố | Cách xử lý |
|---|---|
| `Invalid feature name or UID` | **Cài đặt → "Nút điều khiển lớp chạy bằng"** chọn *Agent*; không cần mục "Programs & websites" trong Veyon |
| Máy học sinh không có Agent | Kiểm tra giờ/múi giờ máy học sinh (lệch > 15 phút bị từ chối), tường lửa cổng 8767 máy giáo viên, rồi chạy lại `Setup-MayHocSinh.bat`. Lý do hiện ở **Nhật ký** |
| Máy được bật bằng Wake-on-LAN nhưng kẹt ở màn hình `PXE ... DHCP...` | BIOS đang ưu tiên khởi động mạng. Vào BIOS (HP: F10, máy khác: Del/F2), tắt **Network/PXE Boot** (hoặc đưa ổ cứng / Windows Boot Manager lên đầu), **giữ bật** Wake on LAN / Power On by PCI-E |
| Máy hiện IP thay vì tên | Cần Agent, DNS ngược hoặc NetBIOS; quét lại sau khi cài |
| Nhập thời khóa biểu lỗi | Cần hàng tiêu đề các thứ (`THỨ HAI`, `T2`…) + giờ hoặc số tiết; lỗi hiện ngay trên trang |

## Cập nhật chương trình và máy học sinh

- **Tự cập nhật từ GitHub** nay cũng thay `payload\KhoaVeyonServices.bat` và `payload\KhoaVeyonStudent.ps1` (bản cũ sao lưu ở `data\backup-<phiên bản>`). Không đụng `KhoaVeyonAgent.cfg`, `*.pem`. Máy học sinh sau đó tự nhận bản mới (cần bật *Tự cập nhật dịch vụ trên máy học sinh*).
- **Nút ⬆ Cập nhật máy học sinh** (trang *Trạng thái máy*): cập nhật ngay các máy đã chọn khi hệ thống không tự làm (tắt tự cập nhật, máy vừa bật...). Máy cần bật và có Agent; không dùng được khi đang thi.

## Yêu cầu

Máy giáo viên: Windows 10/11 + [Veyon](https://veyon.io) (Master). Máy học sinh: Windows + Veyon Service + .NET Framework 4. Python đã kèm trong bộ chạy.

## Phát triển

```
python -m unittest discover -s tests
```

Chi tiết: [docs/HUONG-DAN-CHI-TIET.vi.md](docs/HUONG-DAN-CHI-TIET.vi.md) · [README-KhoaVeyon.md](README-KhoaVeyon.md) (lịch sử thay đổi, cấu trúc mã).

> Đã kiểm thử bằng bộ test tự động và giao diện mô phỏng; hoạt động trên máy học sinh thật còn phụ thuộc cài đặt Veyon và mạng của bạn.

## Khóa hình nền và icon Desktop (`-desklock-start` / `-desklock-stop`)

Nút **Khóa hình nền và icon Desktop** (nhóm "Màn hình Desktop"). Tài khoản quản trị (giáo viên, IT) không bị ảnh hưởng.

**Chuẩn bị trên mỗi máy học sinh** (hoặc chép qua trang Phân phối):

- `C:\cmd\desktop\wallpaper.jpg` (hoặc `.png`, `.bmp`): hình nền bắt buộc.
- `C:\cmd\desktop\icons\`: các shortcut (`.lnk`, `.url`) sẽ là bộ icon chung. Máy nào cũng hiện đúng bộ này, xếp cùng thứ tự theo tên.

**Cách hoạt động**

- Hình nền: chính sách Windows (HKLM) cấm đổi, cộng một tiến trình giữ trong phiên học sinh: ai đổi bằng cách nào (Settings, chuột phải "Set as desktop background", Paint, sửa registry) cũng bị đặt lại trong khoảng 1 giây.
- Icon: shortcut chung nằm ở `C:\Users\Public\Desktop`; thư mục Desktop riêng của học sinh được dọn sạch (file cũ chuyển vào `Documents\Desktop-cu`) và không cho thêm, xóa, đổi tên. Kéo icon sang chỗ khác thì bị kéo về.
- Cần chạy lại `-install` trên máy học sinh một lần (cập nhật dịch vụ KhoaVeyonAutoLog); sau khi bấm khóa, tiến trình giữ khởi động trong khoảng 30 giây.
- Tính năng "hình nền theo tiết" (số máy, tên em) sẽ bị ghi đè khi đang khóa; bấm Mở khóa trước nếu muốn dùng.

**Chưa kiểm chứng trên Windows thật:** chính sách HKLM trên các bản Windows khác nhau, và việc kéo icon về chỗ cũ bằng thông điệp ListView của Explorer (có thể không hiệu quả khi Explorer đang bật "Auto arrange icons").
