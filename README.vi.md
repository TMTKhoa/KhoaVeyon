# KhoaVeyonService

[English](README.md) | **Tiếng Việt**

Một file batch duy nhất cho Windows, bổ sung các chức năng quản lý lớp học cho [Veyon](https://veyon.io): đóng cưỡng bức ứng dụng, chặn internet (vẫn giữ mạng LAN), chỉ cho phép một số trang web, chặn ứng dụng, khóa Task Manager và Settings, và tắt tiếng loa.

Mỗi chức năng là một tham số (switch) dòng lệnh, nên có thể chạy riêng từng chức năng bằng tính năng **Run program** của Veyon.

```
C:\cmd\KhoaVeyonService.bat -blockall
```

> Đây là một script độc lập, không do Veyon tạo ra và không liên kết với Veyon. Nó **không phải** add-on *Internet Access Control* trả phí của veyon.io; đây là giải pháp miễn phí dựa trên luật của Windows Firewall.

---

## Mục lục

- [Tính năng](#tính-năng)
- [Yêu cầu](#yêu-cầu)
- [Cài đặt](#cài-đặt)
- [Các tham số](#các-tham-số)
- [File danh sách Excel](#file-danh-sách-excel)
- [Thêm chức năng vào Veyon](#thêm-chức-năng-vào-veyon)
- [Cách hoạt động](#cách-hoạt-động)
- [Hạn chế](#hạn-chế)
- [Khắc phục sự cố](#khắc-phục-sự-cố)
- [Gỡ cài đặt](#gỡ-cài-đặt)
- [Lưu ý bảo mật](#lưu-ý-bảo-mật)

---

## Tính năng

| Tính năng | Tham số |
|---|---|
| Đóng cưỡng bức tất cả ứng dụng đang mở | `-killapp` |
| Đóng cưỡng bức tất cả, trừ các ứng dụng trong danh sách | `-keepapp` |
| Chặn toàn bộ internet, vẫn giữ LAN và Veyon hoạt động | `-blockall` |
| Chặn internet, trừ các trang trong file Excel | `-allowpage` |
| Cho phép internet trở lại | `-allowall` |
| Chặn ứng dụng hoặc thư mục trong file Excel | `-blockapp` |
| Bỏ chặn các ứng dụng đó | `-unblockapp` |
| Tắt Task Manager và Settings/Control Panel | `-lockdown` |
| Bật lại chúng | `-unlock` |
| Tắt tiếng / bật tiếng loa | `-mute`, `-unmute` |

Điểm khác:

- Chỉ một file, không cần biên dịch, không cần công cụ bên thứ ba.
- **Không cần** cài Excel trên các máy. Các danh sách `.xlsx` được đọc trực tiếp.
- Không lưu mật khẩu admin trong script.
- Thiết kế cho lớp học dùng tài khoản học sinh thường (không phải admin).

## Yêu cầu

- Windows 10 hoặc 11 trên các máy học sinh (dùng Windows PowerShell 5.1 có sẵn).
- Veyon đã cài trên máy giáo viên và các máy học sinh. Các chức năng được chạy bằng tính năng **Run program** của Veyon.
- **Windows Defender Firewall phải bật**, và dịch vụ của nó (`mpssvc`) phải đang chạy. Việc chặn internet hoạt động bằng cách thêm luật tường lửa, nên nếu tường lửa tắt thì không có tác dụng.
- Tài khoản học sinh không có quyền quản trị.
- Script phải được cài trong thư mục `C:\cmd` trên mọi máy học sinh.
- Cổng 11100 phải mở trên mọi máy học sinh (chạy `firewall-setup.bat` trên từng máy trước).
- Cần quản trị viên cho phép một lần trên mỗi máy (xem [Cài đặt](#cài-đặt)).

## Cài đặt

**Thứ tự rất quan trọng: thiết lập tường lửa trên từng máy học sinh trước.** Veyon Master chỉ kết nối được với máy học sinh khi cổng 11100 đã mở trên máy đó. Sau đó, phần còn lại làm từ máy chủ (máy giáo viên, nơi chạy Veyon Master).

Các file trong dự án:

| File | Công dụng |
|---|---|
| `firewall-setup.bat` | Bật tường lửa và mở cổng 11100 của Veyon. Chạy trên mọi máy học sinh **trước tiên**. |
| `KhoaVeyonService.bat` | Script chính chứa tất cả chức năng. |
| `AllowPage.xlsx`, `BlockAppList.xlsx`, `KeepAppList.xlsx` | Các danh sách tùy chọn (xem [File danh sách Excel](#file-danh-sách-excel)). |

### Bước 1: Tường lửa trên từng máy học sinh (làm trước)

Chép `firewall-setup.bat` sang máy học sinh (USB hoặc thư mục chia sẻ) rồi chạy. Windows sẽ hỏi tên và mật khẩu admin của máy (UAC). File chỉ chạy đúng hai lệnh này:

```
netsh advfirewall set allprofiles state on
netsh advfirewall firewall add rule name="Veyon Server" dir=in action=allow protocol=TCP localport=11100 profile=any
```

Việc này cần quyền admin nên Veyon không làm thay được. Làm một lần cho mỗi máy. Sau đó kiểm tra máy có hiện trong Veyon Master không.

Trên **máy giáo viên**, mở thêm cổng `11400` cho tính năng Demo của Veyon. Đây là cổng mặc định của Veyon; nếu bạn đã đổi thì dùng cổng của bạn. Không cần chuyển tiếp cổng (port forwarding).

### Bước 2: Phân phối file từ máy chủ

Trên máy giáo viên, mở Veyon Master, chọn các máy học sinh và dùng tính năng phân phối file của Veyon (tính năng **File transfer**) để gửi:

- `KhoaVeyonService.bat`
- các file danh sách Excel bạn cần

Veyon lưu file vào thư mục đích đã đặt cho tính năng chuyển file, thư mục này có thể không phải `C:\cmd`. Nếu phiên bản Veyon của bạn có tùy chọn thư mục đích, hãy đặt là `C:\cmd`. Nếu không, gửi file xong thì xem trên một máy học sinh xem file nằm ở đâu và chuyển vào `C:\cmd`. Script phải nằm trong `C:\cmd`.

### Bước 3: Cài đặt trên từng máy học sinh (một lần)

Chạy lệnh này trên mỗi máy với quyền admin:

```
C:\cmd\KhoaVeyonService.bat -install
```

Windows sẽ hỏi tên và mật khẩu admin (UAC). Khi thấy `Install done` là xong. Veyon cũng không làm được bước này, vì chương trình do Veyon chạy dùng quyền của học sinh, không có quyền admin.

`-install` làm hai việc:

- Tạo một dịch vụ Windows nhỏ cho mỗi chức năng cần quyền admin (`KhoaVeyonService_blockall`, `_allowpage`, `_allowall`, `_blockapp`, `_unblockapp`). Người dùng thường được phép **khởi động** các dịch vụ này nhưng không được sửa chúng.
- `C:\cmd` **không bị khóa**: người dùng thường (học sinh) đọc, chạy và cũng **sửa được** mọi thứ trong đó, kể cả chính file `KhoaVeyonService.bat`. Xem [Lưu ý bảo mật](#lưu-ý-bảo-mật) để biết ý nghĩa của việc này.
- Đăng ký một tác vụ theo lịch (`KhoaVeyonAutoLog`), tự bắt đầu ghi log hoạt động cho bất kỳ học sinh nào đăng nhập (xem [Log hoạt động và xuất dữ liệu](#log-hoạt-động-và-xuất-dữ-liệu)).

### Bước 4: Khởi chạy ứng dụng từ máy chủ

Từ giờ mọi việc làm từ Veyon Master trên máy chủ. Thêm mỗi chức năng một mục trong Veyon (xem [Thêm chức năng vào Veyon](#thêm-chức-năng-vào-veyon)), chọn các máy học sinh và dùng **Run program** (ở một số phiên bản gọi là **Start application**) để chạy `C:\cmd\KhoaVeyonService.bat` kèm một tham số như `-blockall`.

Khi cần cập nhật script hoặc danh sách, lặp lại Bước 2 từ máy chủ.

## Các tham số

| Tham số | Cần `-install`? | Chức năng |
|---|---|---|
| `-install` | - | Cài đặt một lần (cần quyền admin). |
| `-uninstall` | - | Gỡ các dịch vụ, luật tường lửa và các chặn ứng dụng. |
| `-killapp` | Không | Đóng cưỡng bức mọi ứng dụng trong phiên của người dùng đang đăng nhập. Không bao giờ đóng giao diện Windows, Veyon, cmd và PowerShell. |
| `-keepapp` | Không | Giống `-killapp` nhưng giữ lại các ứng dụng trong `KeepAppList.xlsx`. |
| `-blockall` | Có | Chặn toàn bộ internet. LAN, localhost và Veyon vẫn hoạt động. Cũng chặn internet IPv6. |
| `-allowpage` | Có | Chặn internet, trừ các trang trong `AllowPage.xlsx` (và máy chủ DNS của máy). |
| `-allowall` | Có | Gỡ chặn internet. |
| `-blockapp` | Có | Chặn không cho chạy các file hoặc thư mục trong `BlockAppList.xlsx`, và đóng các bản đang mở. |
| `-unblockapp` | Có | Gỡ các chặn đó. |
| `-lockdown` | Không | Tắt Task Manager và Settings/Control Panel cho người dùng đang đăng nhập. |
| `-unlock` | Không | Hoàn tác `-lockdown`. `-unlockdown` cũng dùng được. |
| `-mute` | Không | Tắt tiếng loa mặc định. |
| `-unmute` | Không | Bật tiếng lại. |
| `-activitylog-start` | Không | Bắt đầu ghi lại tên cửa sổ/ứng dụng đang hoạt động, kèm ngày, giờ, tên người dùng và mã máy, vào file CSV. **Không ghi phím bấm, chữ gõ hay mật khẩu.** |
| `-activitylog-stop` | Không | Dừng ghi. |
| `-exportlog` | Không | Gộp log hoạt động và log hành động của máy này thành một file CSV, sẵn sàng thu thập và mở bằng Excel. |
| `-lockapp-start` | Không | **Chế độ kiosk.** Chỉ cho phép dùng các ứng dụng trong `KeepAppList.xlsx`, liên tục giám sát; mọi ứng dụng khác sẽ bị đóng trong vòng vài giây sau khi mở. |
| `-lockapp-stop` | Không | Tắt chế độ kiosk. |
| `-clearhistory` | Không | Đóng Chrome và Firefox, sau đó xóa lịch sử duyệt web. **Với Firefox, việc này cũng xóa luôn bookmark** (xem bên dưới). |

> **Về `-activitylog-start`:** chức năng này cố tình chỉ giới hạn ở *cửa sổ/ứng dụng nào đang hoạt động và vào lúc nào*, không ghi nội dung gõ. Ghi phím bấm trên máy tính của trẻ em là rủi ro quyền riêng tư nghiêm trọng, nên dự án này không có chức năng đó. Hãy thông báo cho học sinh và phụ huynh rằng hoạt động được ghi lại, phù hợp với quy định của nhà trường.

Chạy không có tham số (hoặc tham số sai) sẽ in ra dòng hướng dẫn cách dùng.

Việc chặn internet vẫn còn sau khi khởi động lại máy, cho đến khi bạn chạy `-allowall`.

## Ghi log đầy đủ, từ học sinh đến admin

Mọi tham số giờ đều ghi log, từ hành động do học sinh kích hoạt (`-killapp`, `-keepapp`, `-lockdown`, `-mute`...) đến hành động ở mức admin (`-blockall`, `-blockapp`...) và cả `-install` / `-uninstall`. Không có hành động nào chạy âm thầm nữa.

Mỗi dòng log ghi:

```
<ngày> <giờ>  PC=<tên máy>  Student=<học sinh đang đăng nhập>  RunAs=<tài khoản thực thi>  [<tham số>]  <nội dung>
```

- **`Student`** luôn là người đang thực sự ngồi trước máy, lấy từ phiên đăng nhập trên màn hình — kể cả khi chính hành động đó chạy dưới quyền SYSTEM (các tham số mức admin) hoặc dưới một tài khoản admin khác (`-install` / `-uninstall`).
- **`RunAs`** là tài khoản mà đoạn mã thực sự chạy dưới quyền đó (tài khoản học sinh với các tham số chạy trong phiên người dùng, `SYSTEM` với các tham số mức admin chạy qua dịch vụ, hoặc tài khoản admin dùng khi `-install`/`-uninstall`).

Nhờ vậy, chỉ một dòng log đã cho biết đủ: *máy nào*, *học sinh nào đang ở đó*, *ai/cái gì đã thực thi*, và *chuyện gì đã xảy ra* — đầy đủ chuỗi từ thao tác của học sinh đến hành động ở mức admin mà nó kích hoạt.

## Chế độ kiosk (`-lockapp-start` / `-lockapp-stop`)

`-keepapp` (đã nói ở trên) chỉ đóng các ứng dụng ngoài danh sách **một lần**, tại đúng thời điểm bạn chạy lệnh. `-lockapp-start` làm việc tương tự nhưng **liên tục**: chạy nền và đóng ngay bất kỳ ứng dụng nào không có trong `KeepAppList.xlsx` ngay khi nó xuất hiện, cho đến khi bạn tắt chế độ này. Dùng chung danh sách loại trừ (Explorer, Veyon, cmd, PowerShell...) và đúng định dạng `KeepAppList.xlsx` đã mô tả ở trên.

- Thêm vào Veyon: `C:\cmd\KhoaVeyonService.bat -lockapp-start` và `C:\cmd\KhoaVeyonService.bat -lockapp-stop`.
- Không cần quyền admin, không cần `-install`, giống `-activitylog-start`.
- **Danh sách chỉ được đọc một lần, lúc bật chế độ kiosk**, không tự đọc lại mỗi lần kiểm tra. Nếu sửa `KeepAppList.xlsx` trong lúc chế độ kiosk đang chạy, hãy chạy `-lockapp-stop` rồi `-lockapp-start` lại để áp dụng thay đổi.
- Chạy độc lập với log hoạt động; bật/tắt cái này không ảnh hưởng tới cái kia.
- Học sinh mở một ứng dụng ngoài danh sách sẽ thấy nó hiện ra rồi tự đóng trong vài giây, chứ không bị chặn mở ngay từ đầu. Nếu muốn chặn mở ngay lập tức, dùng `-blockapp` (xem [File danh sách Excel](#file-danh-sách-excel)), vì nó chặn chương trình chạy từ đầu.
- Mỗi ứng dụng bị đóng đều được ghi log, nên cũng xuất hiện trong file CSV hằng ngày (xem bên dưới).

## Xóa lịch sử duyệt web (`-clearhistory`)

```
C:\cmd\KhoaVeyonService.bat -clearhistory
```

- **Đóng Chrome và Firefox trước**, vì file lịch sử bị khóa khi trình duyệt đang chạy. Mọi tab đang mở hoặc việc chưa lưu trong trình duyệt sẽ mất — coi như `-killapp` áp dụng riêng cho 2 app này.
- **Chrome:** chỉ xóa file `History` (và file journal của nó) trong từng thư mục hồ sơ (`Default`, `Profile 1`, `Profile 2`...). Bookmark nằm ở file `Bookmarks` riêng, **không** bị ảnh hưởng.
- **Firefox:** lịch sử và bookmark cùng nằm trong 1 file `places.sqlite`, và Windows/PowerShell không có sẵn công cụ SQLite để chỉ xóa riêng các dòng lịch sử. Vì vậy tham số này xóa hẳn `places.sqlite`, **cũng xóa luôn bookmark Firefox**. Nếu học sinh có lưu bookmark Firefox quan trọng, hãy sao lưu trước (menu Firefox → Bookmarks → Manage Bookmarks → Export) hoặc tránh chạy lệnh này trên các hồ sơ Firefox còn bookmark cần giữ.
- Mật khẩu đã lưu trong trình duyệt, cookie và dữ liệu trang web **không** bị ảnh hưởng, chỉ xóa lịch sử (và với Firefox là cả bookmark).
- Chạy trong phiên của học sinh, không cần quyền admin.

## Log hoạt động và xuất dữ liệu

Tất cả nằm trong `C:\cmd\log` trên mỗi máy, **mỗi máy mỗi ngày một file CSV**:

```
C:\cmd\log\activity_<PCNAME>_<yyyy-MM-dd>.csv
```

Các cột: `Date, Time, PCName, User, Window, Process, Event`. `Event` có 3 loại:

- `change` — cửa sổ/ứng dụng đang hoạt động thay đổi.
- `autosave` — dòng tự động ghi mỗi 3 phút, để file không bao giờ cũ quá 3 phút, kể cả khi không có gì thay đổi.
- `action` — sự kiện chặn/cho phép mạng, chặn ứng dụng... được gộp từ log hành động, cột `Window` để trống, nội dung nằm trong `Event` (ví dụ `action: Internet BLOCKED`).

Các dòng chỉ được **thêm vào**, không bao giờ ghi đè, nên file lưu lũy tiến suốt cả ngày. Đến nửa đêm, tiến trình ghi tự chuyển sang file của ngày mới, không cần khởi động lại.

### Tự động chạy khi mở máy

`-install` đăng ký một tác vụ theo lịch (`KhoaVeyonAutoLog`), chạy mỗi khi có người đăng nhập, với bất kỳ tài khoản học sinh nào, và tự chạy `-activitylog-start`. Bạn không cần thêm gì vào Veyon cho việc này; nó tự chạy ngay khi học sinh đăng nhập. `-activitylog-start` sẽ không làm gì nếu đã đang chạy sẵn trên máy đó, nên đăng nhập lại hoặc chạy tay thêm lần nữa cũng không sao.

### `-exportlog` (tùy chọn, chạy tay)

Các dòng `autosave` mỗi 3 phút đã tự giữ file của hôm nay luôn mới. `-exportlog` chỉ hữu ích khi bạn muốn gộp ngay các sự kiện chặn/cho phép mới nhất vào file **ngay lúc đó**, không cần chờ tới 3 phút. Chạy lại nhiều lần vẫn an toàn, vì nó chỉ thêm những dòng chưa được gộp.

### Thu thập file

Dùng tính năng chuyển file của Veyon (chiều tải xuống, nếu phiên bản của bạn hỗ trợ) hoặc chép tay các file `C:\cmd\log\activity_*.csv` từ mỗi máy. Mọi file đều mở trực tiếp bằng Excel, không cần chuyển sang `.xlsx`.

## File danh sách Excel

Tạo các file này trong `C:\cmd`. Dùng **cột A của sheet đầu tiên**, mỗi dòng một mục. Có thể có dòng tiêu đề (sẽ bị bỏ qua nếu không giống một trang web hoặc đường dẫn). Chỉ đọc file `.xlsx`.

### `AllowPage.xlsx`

Các trang được phép khi dùng `-allowpage`:

```
Site
wikipedia.org
vietjack.vn
```

Script tự xử lý `https://`, đường dẫn phía sau và `www.`.

### `BlockAppList.xlsx`

Đường dẫn đầy đủ của chương trình hoặc thư mục cần chặn bằng `-blockapp`. Hỗ trợ ký tự đại diện và biến môi trường:

```
Path
C:\Program Files\Google\Chrome\Application\chrome.exe
C:\Games\*.exe
C:\Users\Public\Games
```

Mọi thứ trong `C:\Windows`, thư mục Veyon, `C:\cmd` và ổ đĩa gốc sẽ bị bỏ qua có chủ ý, để gõ nhầm cũng không làm hỏng máy.

### `KeepAppList.xlsx`

Các ứng dụng mà `-keepapp` giữ lại. Dùng tên chương trình (có hoặc không có `.exe`) hoặc đường dẫn đầy đủ:

```
App
chrome
mathgame.exe
C:\Games\KidsLearning
```

### Đổi thư mục chứa danh sách

Mặc định các danh sách được đọc từ `C:\cmd\`. Để dùng chung một bản cho mọi máy, hãy đổi `LISTDIR` ở đầu script thành đường dẫn mạng (giữ dấu `\` ở cuối). Thư mục chia sẻ phải đọc được bởi tài khoản máy tính (với các chức năng cần admin) và bởi tài khoản học sinh (với `-keepapp`).

Vì `C:\cmd` không bị khóa, bạn có thể cập nhật danh sách bằng bất kỳ tài khoản nào truy cập được thư mục — nhưng học sinh cũng làm được như vậy, nên hãy coi như danh sách có thể bị học sinh sửa.

## Thêm chức năng vào Veyon

1. Mở **Veyon Configurator** và vào **Programs & websites** (tên mục tùy phiên bản; ở bản cũ nằm trong **Master**).
2. Thêm mỗi chức năng một mục. Lệnh là đường dẫn script cộng với tham số:

| Tên | Lệnh |
|---|---|
| Đóng tất cả ứng dụng | `C:\cmd\KhoaVeyonService.bat -killapp` |
| Đóng tất cả trừ danh sách | `C:\cmd\KhoaVeyonService.bat -keepapp` |
| Chặn internet | `C:\cmd\KhoaVeyonService.bat -blockall` |
| Chỉ cho phép các trang trong danh sách | `C:\cmd\KhoaVeyonService.bat -allowpage` |
| Cho phép internet | `C:\cmd\KhoaVeyonService.bat -allowall` |
| Chặn ứng dụng | `C:\cmd\KhoaVeyonService.bat -blockapp` |
| Bỏ chặn ứng dụng | `C:\cmd\KhoaVeyonService.bat -unblockapp` |
| Khóa (Lockdown) | `C:\cmd\KhoaVeyonService.bat -lockdown` |
| Mở khóa (Unlock) | `C:\cmd\KhoaVeyonService.bat -unlock` |
| Tắt tiếng | `C:\cmd\KhoaVeyonService.bat -mute` |
| Bật tiếng | `C:\cmd\KhoaVeyonService.bat -unmute` |

3. Bấm **Apply**.
4. Trong **Veyon Master**, chọn các máy học sinh, bấm **Run program** (ở một số phiên bản gọi là **Start application**) và chọn mục cần dùng.

## Cách hoạt động

**Run program** của Veyon chạy lệnh dưới quyền học sinh đang đăng nhập, và học sinh không có quyền admin. Thay đổi tường lửa cần quyền admin, nên script dùng hai đường:

- **Chức năng cần quyền admin** (`-blockall`, `-allowpage`, `-allowall`, `-blockapp`, `-unblockapp`): khi học sinh chạy, script nhờ dịch vụ SYSTEM tương ứng chạy. Dịch vụ khởi động chính script đó với quyền admin và thực hiện công việc bằng PowerShell.
- **Chức năng ở mức người dùng** (`-killapp`, `-keepapp`, `-lockdown`, `-unlock`, `-mute`, `-unmute`): chạy trực tiếp trong phiên của học sinh, không cần quyền admin hay dịch vụ.

Chi tiết:

- **Chặn internet** thêm hai luật tường lửa chiều đi ra là `KhoaVeyonBlock` và `KhoaVeyonBlock6`. Chúng chặn mọi địa chỉ, trừ các dải mạng LAN riêng (`10.x`, `172.16-31.x`, `192.168.x`), localhost, link-local, multicast và broadcast.
- **`-allowpage`** tra cứu địa chỉ IP của từng trang trong danh sách và loại chúng khỏi các dải bị chặn. Máy chủ DNS của máy cũng được cho phép.
- **`-blockapp`** thêm quyền *từ chối Execute* cho nhóm Users trên từng file hoặc thư mục, và ghi đường dẫn vào `blocked.txt` để `-unblockapp` hoàn tác.
- **`-lockdown`** đặt chính sách `DisableTaskMgr` và `NoControlPanel` cho người dùng hiện tại.
- **`-mute`** dùng Windows Core Audio API để tắt tiếng thiết bị phát mặc định.

Mã PowerShell nằm ở cuối file `.bat`, sau dấu hiệu `#PS1START`. Không viết đoạn chữ đó ở chỗ nào khác trong file.

## Hạn chế

- **`-allowpage` hoạt động theo địa chỉ IP, không theo tên miền.** Các trang lớn dùng nhiều tên miền hoặc CDN (ví dụ YouTube, Google) có thể chỉ tải được một phần, và địa chỉ IP thay đổi theo thời gian. Chạy lại `-allowpage` để làm mới. Nếu cần lọc trang web đáng tin cậy, hãy dùng bộ lọc DNS ở router.
- **Máy chủ proxy trong mạng LAN sẽ vô hiệu hóa việc chặn.** Nếu các máy ra internet qua proxy có địa chỉ LAN, lưu lượng đó trông như lưu lượng LAN và được cho phép. Kiểm tra bằng `netsh winhttp show proxy`.
- **Tường lửa hoặc phần mềm diệt virus của bên thứ ba** quản lý Windows Firewall có thể ghi đè các luật này.
- **Kết nối đang mở** có thể còn tồn tại một lúc. Đóng hẳn rồi mở lại trình duyệt để thấy việc chặn có hiệu lực ngay.
- **`-blockapp`** cũng ảnh hưởng đến quản trị viên cho đến khi bạn chạy `-unblockapp`. Nó không chặn ứng dụng Microsoft Store (UWP). Học sinh vẫn có thể chép chương trình bị chặn sang vị trí khác.
- **`-lockdown` và `-mute`** chỉ áp dụng cho tài khoản đang đăng nhập. Học sinh vẫn có thể bật tiếng bằng phím âm lượng.
- **Windows có thể ghi nhật ký "service did not respond" (lỗi 1053)** cho các dịch vụ. Điều này là bình thường: các dịch vụ này không phải chương trình dịch vụ thật, nhưng lệnh vẫn chạy.
- Chỉ xử lý sheet đầu tiên của file Excel.

## Khắc phục sự cố

**Không có gì xảy ra.**
Xem file nhật ký. Các chức năng cần admin ghi vào `C:\cmd\KhoaVeyonService.log`; các chức năng mức người dùng ghi vào `%TEMP%\KhoaVeyonService.log` của học sinh đang đăng nhập. Nhật ký ghi lại từng hành động, file danh sách bị thiếu và đường dẫn bị bỏ qua.

**Báo `Service not installed`.**
Chạy `-install` bằng tài khoản quản trị của máy.

**Vẫn vào được internet sau `-blockall`.**
Kiểm tra theo thứ tự:
1. Tường lửa đang bật: `netsh advfirewall show allprofiles state`
2. Luật đã tồn tại: `netsh advfirewall firewall show rule name="KhoaVeyonBlock"`
3. Không có proxy: `netsh winhttp show proxy`
4. `ping 8.8.8.8` thất bại sau khi chặn, còn `ping <IP máy giáo viên>` vẫn thông.

**Máy biến mất khỏi Veyon Master sau khi bật tường lửa.**
Thêm luật cho phép cổng 11100 chiều đi vào (xem [Bước 1](#bước-1-tường-lửa-trên-từng-máy-học-sinh-làm-trước)).

**`-mute` không có tác dụng.**
Đảm bảo máy có thiết bị phát âm thanh đang hoạt động. Xem nhật ký để biết nội dung lỗi.

## Gỡ cài đặt

Chạy bằng quyền quản trị trên mỗi máy:

```
C:\cmd\KhoaVeyonService.bat -uninstall
```

Lệnh này gỡ việc chặn internet, các chặn ứng dụng và các dịch vụ. Sau đó bạn có thể xóa `C:\cmd`. `-lockdown` và `-mute` là thiết lập theo từng người dùng, nên nếu còn đang bật hãy chạy `-unlock` và `-unmute` dưới tài khoản học sinh.

## Lưu ý bảo mật

- Script **không chứa mật khẩu**. Quyền admin được cấp một lần khi cài đặt, qua hộp thoại UAC của Windows.
- **`C:\cmd` ghi được với người dùng thường, và các dịch vụ mức admin chạy `KhoaVeyonService.bat` dưới quyền SYSTEM.** Nghĩa là bất kỳ ai sửa được một file trong `C:\cmd` — kể cả học sinh — đều có thể khiến các dịch vụ SYSTEM chạy mã tùy ý ở lần khởi động tiếp theo, đây là lỗ hổng leo thang quyền thực sự. Trước đây dự án khóa thư mục này chỉ đọc chính vì lý do đó; việc khóa đã được gỡ theo yêu cầu. Nếu muốn khôi phục bảo vệ, chạy lại trên từng máy:
  ```
  icacls "C:\cmd" /inheritance:r /grant:r "SYSTEM:(OI)(CI)F" "Administrators:(OI)(CI)F" "Users:(OI)(CI)RX" /T
  ```
  (chạy với quyền admin; lệnh này cũng xóa quyền ghi hiện có của học sinh, kể cả vào `C:\cmd\log`, nên thêm lại ngoại lệ ghi được cho thư mục đó nếu vẫn muốn dùng log hoạt động: `icacls "C:\cmd\log" /inheritance:r /grant:r "SYSTEM:(OI)(CI)F" "Administrators:(OI)(CI)F" "Users:(OI)(CI)M"`).
- Hãy thông báo cho học sinh và phụ huynh rằng các công cụ lớp học có thể hạn chế máy tính, phù hợp với quy định của nhà trường.

## Giấy phép

Hãy thêm giấy phép bạn chọn (ví dụ MIT) trước khi đăng lên.