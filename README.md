<p align="center"><img src="web/assets/logo.svg" width="260" alt="KhoaVeyon"></p>

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

**Chưa kiểm chứng trên Windows và Veyon thật:** tên khóa cấu hình `DesktopServices/PredefinedPrograms` và định dạng JSON của mục, mã nhóm tường lửa dạng `@FirewallAPI.dll`. Đã thử logic ghi, gộp và quét mạng bằng `veyon-cli` giả. Nếu `config set` không làm Veyon nhận đủ mục, chương trình tự thử cách 2 (xuất cấu hình, sửa khóa, nhập lại; bản gốc lưu trong `veyon-config-truoc-khi-import.json`). Nếu vẫn thiếu, Nhật ký ghi kết quả đọc lại của Veyon và chương trình tạo sẵn file `veyon-programs-import.json` để đối chiếu. Nút **Thiết lập máy giáo viên** sau khi tạo mục sẽ tự phân phối (kiểm tra, gửi file, cài dịch vụ) xuống các máy học sinh đang có trong danh sách.

**Ưu tiên cấu hình Veyon có sẵn:** chương trình đọc cấu hình Veyon đã cài và thiết lập từ trước qua `veyon-cli`. Mục "Programs & websites" nào đã có (cùng tên hoặc cùng dòng lệnh) thì giữ nguyên, chỉ thêm mục còn thiếu; nếu đã đủ thì không ghi gì. Nhóm trong Veyon Master cũng dùng nhóm có sẵn trước, máy đã có trong danh sách thì bỏ qua.

### Chụp màn hình trước khi khóa

Ở trang **Điều khiển lớp**, khối **Chụp màn hình** có nút chụp các máy đang chọn (không chọn = tất cả) và công tắc **Tự chụp màn hình trước khi bấm nút khóa, chặn hoặc đóng ứng dụng**. Khi bật công tắc, các nút cam (khóa, chặn, đóng ứng dụng, xóa lịch sử) chụp xong mới chạy lệnh; máy nào chụp lỗi vẫn bị khóa và lỗi hiện ở Nhật ký.

- Ảnh JPG (mọi màn hình ghép lại) lưu ở `data\screenshots\<ngày-giờ>\TÊNMÁY.jpg`, nút **Mở thư mục ảnh** mở nhanh.
- Cách làm: chép `kvshot.ps1` vào `C:\cmd\vcfg`, chạy bằng `schtasks` dưới tài khoản **người đang đăng nhập** (cần vì SYSTEM không thấy màn hình của học sinh), ảnh ghi tạm ở `C:\Users\Public\kvshot.jpg` rồi được chép về và xóa trên máy học sinh. Học sinh có thể thấy cửa sổ PowerShell thoáng qua.
- Máy không có ai đăng nhập thì không chụp được.
- **Chưa kiểm chứng trên Windows thật:** tác vụ chạy dưới tài khoản người dùng có thể đòi mật khẩu hoặc bị từ chối (cùng giới hạn với tùy chọn "Hiện cửa sổ cho học sinh"). Thử trên 1 máy trước.
- Chưa có quay video màn hình. Quay cần ffmpeg có mặt trên máy học sinh.

### Giám sát vi phạm: tự chụp ảnh, báo động và gửi ảnh về máy giáo viên (từ bản 1.3.0, mở rộng ở 1.4.0)

Ở trang **Điều khiển lớp**, khối **Giám sát vi phạm** có nút **Bật giám sát**, **Tắt giám sát**, **Xem vi phạm**, **Lấy ảnh ngay**.

- Bật xong, máy học sinh chạy `KhoaVeyonWatch.ps1` (ẩn, trong phiên đăng nhập của học sinh, chép vào `C:\cmd\vcfg`). Cứ 2 giây kiểm tra cửa sổ đang ở trên cùng:
  - Là **trình duyệt** (Chrome, Edge, Firefox, Brave, Opera, Cốc Cốc, Vivaldi): đọc URL từ thanh địa chỉ bằng UI Automation, lấy tên miền, so với `AllowPage.xlsx` (tên miền con tính là khớp, bỏ `www.`). Không có trong danh sách thì chụp.
  - Là **ứng dụng khác**: so tên tiến trình hoặc đường dẫn với `KeepAppList.xlsx` (cùng quy tắc `-keepapp`, bỏ qua tiến trình hệ thống và Veyon). Không có trong danh sách thì chụp.
- Chụp ngay khi chuyển sang trang/ứng dụng vi phạm, sau đó chụp lại mỗi N giây (mặc định 10) nếu học sinh vẫn ở đó, tối đa M ảnh (mặc định 5) cho mỗi lần. Chuyển sang nơi khác rồi quay lại thì tính là lần mới.
- Hai danh sách Excel được đọc lại mỗi 30 giây, nên bấm **Lưu** ở trang danh sách là áp dụng, không cần bật lại. Danh sách rỗng thì phần tương ứng (trang hoặc ứng dụng) không bị giám sát.

**Báo động và tự gửi ảnh về máy giáo viên:**

- Mỗi ảnh vi phạm đi kèm một file `.json` ghi **tên máy, tài khoản học sinh, loại (trang web hoặc ứng dụng), tên trang/ứng dụng, tiêu đề cửa sổ, ngày, giờ**.
- Sau khi bật giám sát, KhoaVeyon trên máy giáo viên cứ vài giây (mặc định 3 giây, đổi ở trang **Vi phạm**) lấy ảnh và file `.json` mới qua `\\máy\C$` (cùng đường chép file đang dùng), **xóa bản trên máy học sinh** rồi báo động ngay:
  - **Kêu bíp** trên máy giáo viên (tắt được ở trang Vi phạm).
  - **Thông báo nổi** góc phải màn hình, có ảnh thu nhỏ, tên máy, nội dung vi phạm, ngày giờ. Bấm vào để mở trang Vi phạm. Tiêu đề cửa sổ nhấp nháy khi bạn đang ở cửa sổ khác.
  - Mục **🚨 Vi phạm** trên menu nhấp nháy kèm số vi phạm chưa xem.
- Trang **Vi phạm** hiện thẻ cho từng vi phạm (mới nhất ở đầu): ảnh (bấm để phóng to), tên máy, tài khoản, nội dung, tiêu đề cửa sổ, giờ, ngày. Lọc theo máy được. Ô viền đỏ là vi phạm mới từ lần xem trước.
- Ảnh lưu ở `data\evidence\TÊNMÁY`. Lịch sử đầy đủ ở `data\evidence\violations.csv` (mở bằng Excel) và `alerts.jsonl` (chương trình nạp lại khi mở lại). **Xóa danh sách** chỉ làm trống màn hình, file lịch sử được đổi tên thành `alerts-<ngày-giờ>.old`.
- Khi đang giám sát, đóng cửa sổ chương trình **không** làm chương trình tự thoát (để không bỏ lỡ báo động). Muốn thoát: bấm **Tắt giám sát** rồi **Thoát chương trình**. Mở lại bằng `Chay-KhoaVeyon.bat` thì chương trình tiếp tục nhận ảnh từ các máy đã bật giám sát.
- Máy học sinh tắt hoặc mất mạng thì tạm dừng nhận từ máy đó, chỉ ghi một dòng ở Nhật ký, có lại mạng thì tự nhận tiếp. Ảnh nằm tạm trên máy học sinh nên trong vài giây trước khi được lấy, học sinh vẫn có thể xóa.
- Chống làm ngập: mỗi máy tối đa 20 vi phạm mỗi lượt nhận, file có tên lạ hoặc ảnh quá 15 MB bị bỏ qua.

**Gom báo động trùng (từ bản 1.4.0):**

- Học sinh ở yên một trang thì các ảnh chụp lặp lại được **gộp**: thông báo nổi chỉ có một cái cho mỗi (máy, trang/ứng dụng), tự cập nhật thành “PC07 vi phạm liên tục, 5 ảnh trong 42 giây”; **tiếng bíp chỉ kêu một lần** cho mỗi (máy, trang/ứng dụng) trong khoảng gộp. Trang khác hoặc máy khác thì báo riêng. Khoảng gộp mặc định 60 giây (đổi ở trang **Vi phạm**).
- Ở trang **Vi phạm**, các ảnh liên tiếp cũng gộp thành một thẻ, có dải ảnh nhỏ bên dưới để bấm xem từng ảnh. Ảnh gốc vẫn được giữ đủ.

**Báo cáo cuối buổi:** trang **Báo cáo** thống kê theo khoảng thời gian (hai giờ qua, hôm nay, 7 ngày, tất cả): tổng số lần vi phạm, số máy, máy vi phạm nhiều nhất, trang/ứng dụng bị vào nhiều nhất, giờ cao điểm, bảng theo máy và theo trang. “Một lần vi phạm” là các ảnh liên tiếp trong khoảng gộp nên không bị đếm quá. Trang nào có từ 3 máy trở lên cùng vào sẽ được gợi ý (có thể là trang cần cho bài học). Nút **＋ Cho phép** thêm dòng vào danh sách trang/ứng dụng được phép (vẫn phải mở trang danh sách và bấm Lưu). Nút **Xuất Excel** tạo file trong `data\reports` với 4 sheet: Tổng quan, Theo máy, Theo trang-ứng dụng, Chi tiết.

**Dọn ảnh cũ:** mặc định tự xóa ảnh, bản ghi (`alerts.jsonl`, `violations.csv`, các file `alerts-*.old`) và thư mục ảnh chụp trong `data\screenshots` cũ hơn **30 ngày** trên máy giáo viên, chạy khi mở chương trình rồi mỗi 6 giờ. Đổi số ngày hoặc đặt 0 (không tự xóa) ở trang **Vi phạm**; nút **Dọn ngay** chạy tức thì. Báo cáo Excel đã xuất không bị xóa tự động. Thời hạn lưu nên theo quy định của nhà trường. Từ bản 1.4.0 máy học sinh không còn ghi `evidence.csv`, nên không có dữ liệu cũ tồn lại ở đó.

**Tự chạy lại giám sát khi học sinh đăng nhập:** bật công tắc ở khối Giám sát vi phạm (mặc định bật). Khi bấm **Bật giám sát**, chương trình tạo thêm tác vụ `KhoaVeyonWatchLogon` trên máy học sinh: chạy mỗi khi bất kỳ người dùng nào đăng nhập (sau 15 giây), trong phiên của người đó, ẩn, bằng đúng lệnh giám sát. Máy khởi động lại thì giám sát tự chạy lại, máy giáo viên tự nhận ảnh tiếp khi máy học sinh có mạng. **Tắt giám sát** gỡ tác vụ này; nếu máy học sinh đang tắt lúc bấm thì Nhật ký báo chưa gỡ được, hãy bấm Tắt giám sát lại khi máy bật, nếu không máy sẽ tự bật giám sát lại. Học sinh dùng tài khoản thường không xóa được tác vụ này. Script nằm trong `C:\cmd\vcfg`, nên khóa thư mục `C:\cmd` ở trang Thiết lập để học sinh không sửa được.

- **Cập nhật từ bản cũ:** nếu máy học sinh đang chạy bản giám sát cũ (từ trước 1.3.0), hãy bấm **Tắt giám sát**, đợi vài giây rồi **Bật giám sát** để chép script mới. Ảnh do bản cũ chụp (không có file `.json`) vẫn được nhận về, nhưng thiếu tài khoản và tiêu đề cửa sổ.
- Không ghi phím gõ hay nội dung trang. Ghi hình học sinh nên được nhà trường đồng ý và thông báo trước.

**Hạn chế, chưa kiểm chứng trên Windows thật:**
- Đọc URL bằng UI Automation có thể sót khi trình duyệt toàn màn hình ẩn thanh địa chỉ, khi dùng trình duyệt lạ hoặc Firefox (cấu trúc thanh địa chỉ khác Chrome/Edge). Trang nội bộ (`chrome://`, `edge://`) bị bỏ qua. Cần thử trên đúng Chrome/Edge của trường.
- Tiến trình giám sát chạy bằng quyền học sinh nên học sinh có thể tắt bằng Task Manager. Dùng **Khóa Task Manager / Settings** để giảm rủi ro. Máy khởi động lại thì phải bật giám sát lại.
- Tác vụ chạy dưới tài khoản người dùng có thể đòi mật khẩu hoặc bị từ chối (cùng giới hạn với chụp màn hình).
- Máy không có ai đăng nhập thì không bật được.
- Tác vụ tự chạy lại (nhóm Users, kích hoạt khi đăng nhập, tạo từ XML qua `schtasks /Create /S máy /XML`) chưa thử trên Windows thật; nếu Nhật ký báo chưa cài được, hãy gửi nội dung lỗi để chỉnh. Thử bằng cách bật giám sát, khởi động lại máy học sinh, đăng nhập rồi mở một trang ngoài danh sách.
- Phần báo động và tự nhận ảnh (1.3.0) đã được thử logic với thư mục giả thay cho `\\máy\C$` và máy chủ HTTP thật trên Linux; chưa thử trên Windows với nhiều máy học sinh thật. Tiếng bíp dùng `winsound` của Windows. Hãy thử trên 1 máy trước, mở một trang web ngoài `AllowPage.xlsx` rồi xem báo động có hiện trong vòng vài giây không.

## Điểm danh vắng, dồn chỗ và thông báo "Máy này của ai" (từ bản 3.0.0)

Ở trang **Lớp & lịch dạy**, dưới thời khóa biểu (cần đã nhập danh sách lớp và xếp chỗ ngồi):

**Điểm danh hôm nay.** Bấm tên em để đánh dấu **vắng** (bấm lại để có mặt). Chương trình tự kiểm tra máy nào đang bật (mở cổng Veyon 11100) rồi chuyển các em sau sang **máy trống gần nhất** (gần theo hàng và dãy trên sơ đồ, thường là máy của em vắng):
- em có mặt nhưng máy của em đang tắt hoặc hỏng;
- em chưa có chỗ trong sơ đồ (lớp đông hơn số máy, em mới vào lớp...).

Chỗ đổi chỉ áp dụng cho hôm nay, sơ đồ gốc không bị sửa. Trên sơ đồ, ô xám gạch ngang là máy của em vắng, ô xanh là máy em được chuyển đến. Hết máy trống thì em đó được xếp **ngồi chung** với bạn ở máy dùng được gần nhất (ưu tiên máy ít người ngồi chung); máy của bạn đó hiện bảng "HÔM NAY NGỒI CHUNG MÁY VỚI BẠN: tên em", Nhật ký và trang đều ghi lại. Nếu **không máy nào trả lời** (chưa bật máy, sai tên máy) thì chương trình bỏ qua việc kiểm tra bật/tắt để không dồn chỗ sai; bật máy rồi bấm **Kiểm tra máy và dồn chỗ**. Điểm danh được lưu 60 ngày trong `data\school.json`. Lớp chưa xếp chỗ thì không tự xếp.

**Thông báo vị trí máy.** Nút **Thông báo cho cả lớp** hiện lên màn hình từng em bảng lớn "MÁY NÀY LÀ CỦA: tên em, lớp, số máy" trong N giây (mặc định 15), rồi thu thành nhãn nhỏ ở góc phải trên cùng nếu bật "giữ nhãn nhỏ". Em bấm vào bảng lớn để thu nhỏ. **Gỡ nhãn trên các máy** xóa nhãn. Em được chuyển chỗ tự nhận bảng "BẠN ĐƯỢC CHUYỂN SANG MÁY NÀY" (tắt được bằng công tắc "Tự báo cho em bị chuyển chỗ"). Công tắc **Tự thông báo khi sang tiết mới** gửi cho cả lớp mỗi khi thời khóa biểu chuyển lớp.

- Cách làm: chép `kvseat.ps1` và `kvseat.json` vào `C:\cmd\vcfg`, chạy bằng `schtasks` dưới tài khoản **người đang đăng nhập** (giống chụp màn hình). Máy không có ai đăng nhập thì báo lỗi ở Nhật ký.
- Số máy trên sơ đồ phải ứng với tên máy: điền **Tên máy mẫu** (ví dụ `MAY{n}`) hoặc dựa vào thứ tự danh sách máy ở trang Điều khiển lớp.
- **Chưa kiểm chứng trên Windows thật:** script PowerShell `kvseat.ps1` (cửa sổ luôn ở trên cùng, tác vụ chạy dưới tài khoản người dùng có thể đòi mật khẩu). Phần tính chỗ ngồi và giao diện đã thử trên Linux. Hãy thử nút thông báo trên 1 máy trước.

## Cấu hình Veyon (trang mới, từ bản 1.1.0)

Trang **Cấu hình Veyon** có 3 khối. Bản sao lưu lưu ở `data\veyon-backups` (file JSON, tên bắt đầu bằng `master_` hoặc tên máy).

1. **Sao lưu, so sánh, khôi phục.** Sao lưu master bằng `veyon-cli config export`. Máy học sinh được đọc từ xa: chương trình chép `vcfg-export.bat` vào `C:\cmd\vcfg`, chạy bằng `schtasks` (SYSTEM), rồi lấy file về. **So sánh** chọn hai bên bất kỳ (master hiện tại, máy học sinh đọc trực tiếp, hoặc file sao lưu), kết quả hiện ở Nhật ký. **Khôi phục** dùng `config import` nên thay toàn bộ cấu hình; cấu hình cũ của máy đó được tự lưu trước.
2. **Đẩy cấu hình Veyon Service xuống máy học sinh.** Bạn nhập danh sách khóa `Nhóm/Tên` và giá trị, chương trình ghi từng khóa bằng `config set` trên máy học sinh (không đụng khóa khác), tùy chọn khởi động lại `VeyonService`, và lưu cấu hình cũ trước khi đẩy. Đường dẫn `veyon-cli.exe` trên máy học sinh đặt ngay trong khối này.
3. **Danh sách máy của Veyon Master.** Thêm các máy đang chọn vào Master bằng `veyon-cli networkobjects add` (nhóm `location` tùy chọn). Máy đã có thì bỏ qua. Cần quyền quản trị nên Windows hiện UAC.

**Chưa kiểm chứng trên Windows và Veyon thật:** định dạng kết quả `networkobjects list` (dùng để nhận biết máy đã có), tên các khóa gợi ý (`Network/PrimaryServicePort`, `Network/FirewallExceptionEnabled`, `Service/Autostart`), và việc `config import` có thay toàn bộ hay gộp tùy phiên bản Veyon. Logic đã thử với `veyon-cli` giả trên Linux. Hãy thử trên 1 máy trước, rồi dùng **So sánh** để kiểm tra kết quả.

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

## Cập nhật từ GitHub

Chương trình hỏi GitHub (mục Releases của kho `update_repo` ở trang Cài đặt) khi mở và cứ 6 giờ một lần. Khi có bản mới hơn `VERSION` trong `KhoaVeyon.py`, một hộp thoại hiện ra hỏi **Cập nhật ngay / Để sau / Bỏ qua bản này**. "Để sau" thì 4 giờ sau hỏi lại, "Bỏ qua" thì chỉ hỏi lại khi có bản còn mới hơn nữa. Danh sách, lớp, sơ đồ chỗ ngồi và cài đặt trong `data`, `lists`, `payload` không bị thay.

Để phát hành bản mới: đổi `VERSION`, đẩy code lên GitHub, rồi tạo một **Release** có tag lớn hơn (ví dụ `v1.6.0`) và ghi chú thay đổi vào phần mô tả của Release (hộp thoại sẽ hiện phần này).
