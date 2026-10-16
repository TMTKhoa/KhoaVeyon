# KhoaVeyon

Chương trình chạy trên **máy giáo viên (máy chủ Veyon)**, giao diện là một trang web mở trong cửa sổ riêng (Edge hoặc Chrome, không cần Internet):

1. **Điều khiển lớp học:** chọn máy học sinh rồi bấm nút để khóa máy, chặn internet, chặn ứng dụng...
2. **Sửa 3 danh sách Excel** (`KeepAppList.xlsx`, `AllowPage.xlsx`, `BlockAppList.xlsx`) bằng bảng, không cần mở Excel. Bấm Lưu thì file tự được gửi xuống máy học sinh.
3. **Phân phối và chạy:** chép file sang máy học sinh rồi chạy ứng dụng bằng một nút.

> Chương trình không thay thế Veyon. Nó dùng Veyon để ra lệnh, và dùng file `KhoaVeyonServices.bat` đã cài trên các máy học sinh.

## Thiết lập ban đầu (tự động)

Lần chạy đầu tiên chương trình tự mở trang **Thiết lập ban đầu**. Bấm **Thiết lập máy giáo viên**, chương trình sẽ làm các bước 1 đến 3 dưới đây. Máy học sinh làm riêng bằng nút **Thiết lập máy học sinh** (bước 4, bỏ qua máy đã thiết lập đủ):

1. Tạo 3 file Excel mẫu trong thư mục danh sách (không ghi đè file đã có).
2. Tạo `payload\Setup-MayHocSinh.bat` và chép `KhoaVeyonServices.bat` vào `payload` nếu tìm thấy (cạnh chương trình, thư mục cha hoặc `C:\cmd`). Chưa thấy thì thêm tay ở trang Phân phối & chạy.
3. Tự thêm 18 mục điều khiển vào Veyon (Programs & websites) bằng `veyon-cli config set`. Cần quyền quản trị nên Windows hiện hộp thoại UAC, bấm Yes. Mục khác của bạn được giữ nguyên, bản sao lưu nằm ở `data\veyon-programs-backup.json`. Sau đó mở lại Veyon Master.
4. Kiểm tra từng máy học sinh (Veyon Service, chia sẻ C$, Task Scheduler từ xa, đã có script chưa) và gửi file xuống các máy chép được.

Sau khi chép file, chương trình tự chạy `KhoaVeyonServices.bat -install` trên các máy chưa có dịch vụ `KhoaVeyonService_*` (chạy bằng SYSTEM qua `schtasks`, nên không hỏi UAC). Không cần cài tay từng máy.

Thư mục `lists` và `payload` đã kèm sẵn 3 file Excel mẫu và `KhoaVeyonServices.bat` của bạn.

Nút **Tìm máy học sinh trong mạng** quét dải /24 của mạng hiện tại, tìm máy đang mở cổng Veyon (11100) rồi thêm vào danh sách.

**Việc duy nhất phải làm tay:** chạy `Setup-MayHocSinh.bat` một lần trên mỗi máy học sinh (chuột phải, Run as administrator). File này mở tường lửa cho chia sẻ file và Task Scheduler từ xa, đặt `LocalAccountTokenFilterPolicy`, tạo `C:\cmd` và bật Veyon Service. Không thể làm từ xa vì chính các quyền này chưa mở.

**Chưa kiểm chứng trên Windows và Veyon thật:** tên khóa cấu hình `DesktopServices/PredefinedPrograms` và định dạng JSON của mục, mã nhóm tường lửa dạng `@FirewallAPI.dll`. Đã thử logic ghi, gộp và quét mạng bằng `veyon-cli` giả. Nếu Veyon báo thiếu mục sau khi tạo, chương trình ghi cảnh báo ở Nhật ký và bạn tạo thủ công theo mục "Kết nối với Veyon".

### Chụp màn hình trước khi khóa

Ở trang **Điều khiển lớp**, khối **Chụp màn hình** có nút chụp các máy đang chọn (không chọn = tất cả) và công tắc **Tự chụp màn hình trước khi bấm nút khóa, chặn hoặc đóng ứng dụng**. Khi bật công tắc, các nút cam (khóa, chặn, đóng ứng dụng, xóa lịch sử) chụp xong mới chạy lệnh; máy nào chụp lỗi vẫn bị khóa và lỗi hiện ở Nhật ký.

- Ảnh JPG (mọi màn hình ghép lại) lưu ở `data\screenshots\<ngày-giờ>\TÊNMÁY.jpg`, nút **Mở thư mục ảnh** mở nhanh.
- Cách làm: chép `kvshot.ps1` vào `C:\cmd\vcfg`, chạy bằng `schtasks` dưới tài khoản **người đang đăng nhập** (cần vì SYSTEM không thấy màn hình của học sinh), ảnh ghi tạm ở `C:\Users\Public\kvshot.jpg` rồi được chép về và xóa trên máy học sinh. Học sinh có thể thấy cửa sổ PowerShell thoáng qua.
- Máy không có ai đăng nhập thì không chụp được.
- **Chưa kiểm chứng trên Windows thật:** tác vụ chạy dưới tài khoản người dùng có thể đòi mật khẩu hoặc bị từ chối (cùng giới hạn với tùy chọn "Hiện cửa sổ cho học sinh"). Thử trên 1 máy trước.
- Chưa có quay video màn hình. Quay cần ffmpeg có mặt trên máy học sinh.

### Giám sát vi phạm: tự chụp ảnh khi học sinh mở trang hoặc ứng dụng ngoài danh sách

Ở trang **Điều khiển lớp**, khối **Giám sát vi phạm** có nút **Bật giám sát**, **Tắt giám sát**, **Lấy ảnh vi phạm về**.

- Bật xong, máy học sinh chạy `KhoaVeyonWatch.ps1` (ẩn, trong phiên đăng nhập của học sinh, chép vào `C:\cmd\vcfg`). Cứ 2 giây kiểm tra cửa sổ đang ở trên cùng:
  - Là **trình duyệt** (Chrome, Edge, Firefox, Brave, Opera, Cốc Cốc, Vivaldi): đọc URL từ thanh địa chỉ bằng UI Automation, lấy tên miền, so với `AllowPage.xlsx` (tên miền con tính là khớp, bỏ `www.`). Không có trong danh sách thì chụp.
  - Là **ứng dụng khác**: so tên tiến trình hoặc đường dẫn với `KeepAppList.xlsx` (cùng quy tắc `-keepapp`, bỏ qua tiến trình hệ thống và Veyon). Không có trong danh sách thì chụp.
- Chụp ngay khi chuyển sang trang/ứng dụng vi phạm, sau đó chụp lại mỗi N giây (mặc định 10) nếu học sinh vẫn ở đó, tối đa M ảnh (mặc định 5) cho mỗi lần. Chuyển sang nơi khác rồi quay lại thì tính là lần mới.
- Hai danh sách Excel được đọc lại mỗi 30 giây, nên bấm **Lưu** ở trang danh sách là áp dụng, không cần bật lại. Danh sách rỗng thì phần tương ứng (trang hoặc ứng dụng) không bị giám sát.
- Ảnh và `evidence.csv` (giờ, loại, tên trang/ứng dụng, tiêu đề cửa sổ) nằm ở `C:\Users\Public\KhoaVeyonEvidence` trên máy học sinh. **Học sinh có thể xóa**, hãy bấm **Lấy ảnh vi phạm về** thường xuyên. Ảnh về `data\evidence\TÊNMÁY` và bị xóa khỏi máy học sinh.
- Không ghi phím gõ hay nội dung trang. Ghi hình học sinh nên được nhà trường đồng ý và thông báo trước.

**Hạn chế, chưa kiểm chứng trên Windows thật:**
- Đọc URL bằng UI Automation có thể sót khi trình duyệt toàn màn hình ẩn thanh địa chỉ, khi dùng trình duyệt lạ hoặc Firefox (cấu trúc thanh địa chỉ khác Chrome/Edge). Trang nội bộ (`chrome://`, `edge://`) bị bỏ qua. Cần thử trên đúng Chrome/Edge của trường.
- Tiến trình giám sát chạy bằng quyền học sinh nên học sinh có thể tắt bằng Task Manager. Dùng **Khóa Task Manager / Settings** để giảm rủi ro. Máy khởi động lại thì phải bật giám sát lại.
- Tác vụ chạy dưới tài khoản người dùng có thể đòi mật khẩu hoặc bị từ chối (cùng giới hạn với chụp màn hình).
- Máy không có ai đăng nhập thì không bật được.

## Cấu hình Veyon (trang mới, từ bản 1.1.0)

Trang **Cấu hình Veyon** có 3 khối. Bản sao lưu lưu ở `data\veyon-backups` (file JSON, tên bắt đầu bằng `master_` hoặc tên máy).

1. **Sao lưu, so sánh, khôi phục.** Sao lưu master bằng `veyon-cli config export`. Máy học sinh được đọc từ xa: chương trình chép `vcfg-export.bat` vào `C:\cmd\vcfg`, chạy bằng `schtasks` (SYSTEM), rồi lấy file về. **So sánh** chọn hai bên bất kỳ (master hiện tại, máy học sinh đọc trực tiếp, hoặc file sao lưu), kết quả hiện ở Nhật ký. **Khôi phục** dùng `config import` nên thay toàn bộ cấu hình; cấu hình cũ của máy đó được tự lưu trước.
2. **Đẩy cấu hình Veyon Service xuống máy học sinh.** Bạn nhập danh sách khóa `Nhóm/Tên` và giá trị, chương trình ghi từng khóa bằng `config set` trên máy học sinh (không đụng khóa khác), tùy chọn khởi động lại `VeyonService`, và lưu cấu hình cũ trước khi đẩy. Đường dẫn `veyon-cli.exe` trên máy học sinh đặt ngay trong khối này.
3. **Danh sách máy của Veyon Master.** Thêm các máy đang chọn vào Master bằng `veyon-cli networkobject add` (nhóm `location` tùy chọn). Máy đã có thì bỏ qua. Cần quyền quản trị nên Windows hiện UAC.

**Chưa kiểm chứng trên Windows và Veyon thật:** định dạng kết quả `networkobject list` (dùng để nhận biết máy đã có), tên các khóa gợi ý (`Network/PrimaryServicePort`, `Network/FirewallExceptionEnabled`, `Service/Autostart`), và việc `config import` có thay toàn bộ hay gộp tùy phiên bản Veyon. Logic đã thử với `veyon-cli` giả trên Linux. Hãy thử trên 1 máy trước, rồi dùng **So sánh** để kiểm tra kết quả.

## Tự cập nhật từ GitHub

Trang **Cài đặt**, mục **Cập nhật phần mềm**: điền kho GitHub dạng `chủ-sở-hữu/tên-kho` (kho công khai). Mỗi lần khởi động, chương trình hỏi mục Releases xem có tag lớn hơn phiên bản hiện tại (hằng `VERSION` trong `KhoaVeyon.py`) không. Có thì hiện thanh thông báo, bấm **Cập nhật ngay**.

- Chỉ thay `KhoaVeyon.py`, `Chay-KhoaVeyon.bat`, `README-KhoaVeyon.md`, `requirements.txt` và thư mục `web`. `data`, `lists`, `payload`, `runtime` giữ nguyên. Bản cũ được sao lưu trong `data\backup-<phiên bản>`.
- Chỉ tải qua https từ github.com, từ chối file zip có đường dẫn lạ, và kiểm tra cú pháp `KhoaVeyon.py` mới trước khi thay. Lỗi thì giữ nguyên bản cũ.
- Cách phát hành bản mới: tăng `VERSION` (ví dụ `1.1.0`), đẩy lên GitHub, tạo Release có tag `v1.1.0` và đính kèm file zip tên có chữ `KhoaVeyon` (không đính kèm thì dùng zip mã nguồn tự sinh của GitHub). Cần tên file zip chứa `KhoaVeyon.py`.
- Công tắc "Tự cài và khởi động lại" mặc định tắt. Bản cập nhật chạy bằng quyền của giáo viên và có thể ra lệnh xuống máy học sinh, nên chỉ dùng kho của chính bạn và bật xác thực hai bước cho tài khoản GitHub.
- Kho riêng tư chưa được hỗ trợ.

## Chạy chương trình

Bấm đúp `Chay-KhoaVeyon.bat`. Cửa sổ lệnh chỉ hiện thoáng qua rồi cửa sổ KhoaVeyon mở ra.

- Nếu máy đã có Python, file bat dùng luôn và tự cài `openpyxl` nếu thiếu.
- Nếu chưa có, ở **lần chạy đầu tiên** file bat tải Python portable (khoảng 30 MB, cần Internet) vào thư mục `runtime` cạnh chương trình. Không cài gì vào Windows. Các lần sau chạy ngay, không cần Internet.
- Chép cả thư mục (kèm `runtime`, `data`, `lists`, `payload`) sang máy giáo viên khác là dùng được.
- Đóng cửa sổ thì chương trình tự thoát sau khoảng 3 phút, hoặc bấm **Thoát chương trình** ở góc dưới bên trái. Bấm đúp file bat lần nữa khi đang chạy chỉ mở lại cửa sổ cũ.
- Trang web chỉ truy cập được từ chính máy này và có mã bảo vệ ngẫu nhiên mỗi lần chạy, nên trang web khác không ra lệnh được.
- Nếu cửa sổ không mở, xem file `data\error.log`.

Cài đặt nằm trong `data\KhoaVeyon.json` cạnh chương trình (nếu thư mục không ghi được thì dùng `%APPDATA%\KhoaVeyon`).

## Cách dùng

### Điều khiển lớp

1. Thêm máy học sinh (tên máy hoặc IP) ở khung bên trái, có thể dán nhiều máy cách nhau bằng dấu phẩy hoặc dấu cách.
2. Tick các máy cần điều khiển. Không tick máy nào nghĩa là áp dụng cho tất cả (chương trình hỏi lại trước khi chạy).
3. Bấm nút chức năng. Nút cam bật hạn chế, nút xanh lá gỡ hạn chế, nút xám là việc khác. Các lệnh có thể đóng ứng dụng của học sinh sẽ hỏi xác nhận trước.
4. Kết quả từng máy hiện ở khung **Nhật ký** bên dưới (xanh là thành công, đỏ là lỗi).

Mục **Nâng cao** sao chép sẵn dòng lệnh dạng `cmd.exe /c C:\cmd\KhoaVeyonServices.bat -lockall-start` để dán vào **Run program** của Veyon Master khi muốn làm thủ công.

### Ba trang danh sách

- Mỗi dòng gồm nội dung (cột A, script đọc) và ghi chú (cột B, script bỏ qua). Sửa trực tiếp trong bảng; dùng mũi tên để đổi thứ tự, dấu ✕ để xóa.
- **Dán nhiều dòng** dán cả danh sách một lần (từ Notepad hoặc từ Excel). **Thêm nhanh** thêm nhóm dòng có sẵn như Chrome, ONLYOFFICE, Steam. Dòng trùng không bị thêm lại. Ô tìm kiếm lọc dòng.
- Dấu ⚠ báo dòng mà script sẽ bỏ qua hoặc xử lý sai (ví dụ trang web không giống tên miền, đường dẫn thiếu ổ đĩa).
- **Lưu** ghi file Excel đúng định dạng script đọc, rồi **tự gửi file vừa sửa xuống máy học sinh** (các máy đang tick, không tick = tất cả) vào thư mục đích ở trang Phân phối (mặc định `C:\cmd`). Tắt việc này bằng công tắc ở trang Phân phối & chạy.
- **Lưu và áp dụng** làm như Lưu, đợi gửi xong rồi chạy lại lệnh liên quan trên các máy: `-lockall-start` cho danh sách ứng dụng được phép, `-allowpage` cho trang web, `-blockapp` cho ứng dụng bị chặn.
- Nếu file đang mở trong Excel, chương trình báo không ghi được. Đóng Excel rồi lưu lại.

### Phân phối và chạy

1. Chọn nội dung: tick kèm 3 file Excel, và/hoặc file trong thư mục `payload`. Bấm **Thêm file** để tải file lên `payload` (ví dụ `KhoaVeyonServices.bat`), hoặc **Thêm theo đường dẫn** cho file/thư mục ở nơi khác. Đặt thư mục đích trên máy học sinh.
2. Chọn cách chạy: chỉ chép; chạy lệnh Windows (`schtasks`); hoặc kích hoạt một mục Veyon.
3. Bấm **Phân phối rồi chạy** (hoặc chỉ một trong hai bước). Máy nào chép lỗi sẽ bị bỏ qua bước chạy. Nhiều máy được xử lý song song (tối đa 8 máy một lúc).

Điều kiện: chép file đi qua chia sẻ quản trị `\\máy\C$` và `schtasks` gọi từ xa, nên tài khoản Windows đang đăng nhập trên máy giáo viên phải là quản trị viên trên máy học sinh, tường lửa máy học sinh phải cho phép chia sẻ file và quản lý Task Scheduler từ xa (nhóm quy tắc "Remote Scheduled Tasks Management"). Chương trình không lưu mật khẩu.

`schtasks` mặc định chạy bằng SYSTEM nên học sinh không thấy cửa sổ (phù hợp script nền). Muốn mở ứng dụng có giao diện thì bật "Hiện cửa sổ cho học sinh" (chưa kiểm chứng, có thể đòi mật khẩu).

### Khóa thư mục C:\cmd trên máy học sinh

Ở trang **Thiết lập ban đầu**, khối "Thiết lập máy học sinh" có nút **Khóa thư mục C:\cmd** và **Mở khóa**, kèm công tắc tự khóa sau khi thiết lập.

- Học sinh (nhóm Users) chỉ đọc và chạy được trong `C:\cmd`, không sửa hay xóa được `KhoaVeyonServices.bat` và các file Excel.
- SYSTEM và Administrators có toàn quyền, nên giáo viên vẫn chép file bằng KhoaVeyon qua `\\máy\C$` mà không phải nhập UAC. Dịch vụ `KhoaVeyonService_*` chạy như cũ.
- Thư mục `C:\cmd\log` vẫn cho học sinh ghi, vì mọi file ghi nhận hoạt động và file tạm của `-lockapp` nằm ở đó. Theo script hiện tại, `KhoaVeyonService.log` ở thư mục gốc chỉ do SYSTEM hoặc quản trị ghi.
- Dùng SID thay cho tên nhóm nên chạy đúng trên Windows tiếng Việt.
- Chỉ có tác dụng khi học sinh đăng nhập bằng tài khoản người dùng thường. Veyon File transfer ghi file bằng tài khoản học sinh nên không ghi đè được vào thư mục đã khóa. Hãy cập nhật file bằng KhoaVeyon.
- Chưa thử trên Windows thật. Sau khi khóa một máy, hãy thử `-lockall-start` rồi `-lockall-stop` và kiểm tra thư mục `log` vẫn có file mới.

### Cài đặt

Thư mục danh sách (mặc định `lists` cạnh chương trình), đường dẫn `veyon-cli.exe`, mẫu lệnh Veyon, thư mục đồng bộ và tên các mục trong Veyon. `veyon-cli.exe` được tìm theo thứ tự: đường dẫn trong Cài đặt, thư mục `veyon\` cạnh chương trình, PATH, rồi `C:\Program Files\Veyon`. Máy giáo viên vẫn cần có Veyon Master.

## Kết nối với Veyon

Các nút điều khiển gọi `veyon-cli` để kích hoạt một **mục đã cấu hình sẵn** trong Veyon Configurator, mục **Programs & websites**. Vì vậy:

1. Thêm mỗi chức năng một mục trong Veyon, với tên khớp bảng ở trang **Cài đặt**.
2. Ở trang **Cài đặt**, bấm **Kiểm tra kết nối Veyon** để xem Veyon có nhận ra các mục đó không. Kết quả hiện ở Nhật ký.
3. Nếu tên khác, sửa trong bảng cho khớp. Nếu phiên bản Veyon dùng cú pháp khác, sửa **Mẫu lệnh chạy một mục**.

**Chưa được kiểm chứng:** phần gọi `veyon-cli` viết theo cú pháp `veyon-cli feature start <máy> <chức năng>`. Chưa thử với Veyon thật.

## Đồng bộ danh sách qua thư mục chia sẻ (tùy chọn)

Ngoài việc tự gửi file xuống từng máy, bạn có thể dùng thư mục chia sẻ: đặt thư mục danh sách là thư mục chia sẻ trên máy giáo viên (ví dụ `\\MAYGIAOVIEN\cmd`) rồi đổi `LISTDIR` trong `KhoaVeyonServices.bat`, hoặc điền **Thư mục đồng bộ** ở Cài đặt và bật tự đồng bộ. Thư mục chia sẻ chỉ nên cho học sinh quyền đọc.

## Giới hạn

- Danh sách chỉ được script đọc lúc bật chế độ. Sau khi sửa, dùng **Lưu và áp dụng** hoặc chạy lại lệnh khóa tương ứng.
- Máy đang ở chế độ khóa toàn bộ không mở được `cmd`/file `.bat` từ Explorer. Luôn bật và tắt khóa từ chương trình này hoặc từ Run program của Veyon.
- Giao diện web đã được thử trong trình duyệt Chromium trên Linux; phần chép file, `schtasks` và `veyon-cli` cần Windows thật nên chưa được thử.
