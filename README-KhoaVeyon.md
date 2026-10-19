<p align="center"><img src="web/assets/logo.svg" width="260" alt="KhoaVeyon"></p>

# KhoaVeyon

Chương trình chạy trên **máy giáo viên (máy chủ Veyon)**, giao diện là một trang web mở trong cửa sổ riêng (Edge hoặc Chrome, không cần Internet):

1. **Điều khiển lớp học:** chọn máy học sinh rồi bấm nút để khóa máy, chặn internet, chặn ứng dụng...
2. **Sửa 4 danh sách Excel** (`KeepAppList.xlsx`, `AllowPage.xlsx`, `BlockAppList.xlsx`, `BlockAIList.xlsx`) bằng bảng, không cần mở Excel. Bấm Lưu thì file tự được gửi xuống máy học sinh.
3. **Phân phối và chạy:** chép file sang máy học sinh rồi chạy ứng dụng bằng một nút.

> Chương trình không thay thế Veyon. Nó dùng Veyon để ra lệnh, và dùng file `KhoaVeyonServices.bat` đã cài trên các máy học sinh.

## Thiết lập ban đầu (tự động)

Lần chạy đầu tiên chương trình tự mở trang **Thiết lập ban đầu**. Bấm **Thiết lập máy giáo viên**, chương trình sẽ làm các bước 1 đến 3 dưới đây. Máy học sinh làm riêng bằng nút **Thiết lập máy học sinh** (bước 4, bỏ qua máy đã thiết lập đủ):

1. Tạo 4 file Excel mẫu trong thư mục danh sách (không ghi đè file đã có).
2. Tạo `payload\Setup-MayHocSinh.bat` và chép `KhoaVeyonServices.bat` vào `payload` nếu tìm thấy (cạnh chương trình, thư mục cha hoặc `C:\cmd`). Chưa thấy thì thêm tay ở trang Phân phối & chạy.
3. Tự thêm 20 mục điều khiển vào Veyon (Programs & websites) bằng `veyon-cli config set`. Cần quyền quản trị nên Windows hiện hộp thoại UAC, bấm Yes. Mục khác của bạn được giữ nguyên, bản sao lưu nằm ở `data\veyon-programs-backup.json`. Sau đó mở lại Veyon Master.
4. Kiểm tra từng máy học sinh (Veyon Service, chia sẻ C$, Task Scheduler từ xa, đã có script chưa) và gửi file xuống các máy chép được.

Sau khi chép file, chương trình tự chạy `KhoaVeyonServices.bat -install` trên các máy chưa có dịch vụ `KhoaVeyonService_*` (chạy bằng SYSTEM qua `schtasks`, nên không hỏi UAC). Không cần cài tay từng máy.

## Bản này thêm (các tính năng mới)

**1. Khóa màn hình ứng dụng giáo viên.** Góc trên có nút **🔒 Khóa**. Bấm để che toàn bộ giao diện sau một mật khẩu, tránh học sinh lên chỉnh cài đặt hay gửi lệnh khi giáo viên rời máy. Mật khẩu mặc định **0000**, đổi ở Cài đặt → *Khóa màn hình ứng dụng* (mật khẩu thường, ít nhất 4 ký tự). Khi đang khóa, máy chủ **từ chối mọi lệnh** cho tới khi nhập đúng mật khẩu, nên chặn cả khi ai đó gọi thẳng API. Có tùy chọn tự khóa khi không thao tác sau N phút. Mật khẩu lưu dạng băm ở `data\applock.json`; quên thì xóa file này để về lại 0000.

**2. Báo cho học sinh khi vi phạm** (công tắc ở khối Giám sát vi phạm, mặc định bật): sau khi máy giáo viên **đã nhận** ảnh, máy học sinh hiện bảng đỏ “ĐÃ GHI NHẬN VI PHẠM” 10 giây (trang/ứng dụng, giờ, đã gửi cho giáo viên). Mỗi lần vi phạm chỉ báo một lần.

**3. Ảnh vi phạm xếp theo ngày và lớp, tên file rõ ràng.** `data\evidence\<ngày>\<lớp>\<Trường>_<Lớp>_<Học sinh>_<Máy>_<ngày>_<giờ>_<loại>_<trang>.jpg`. Tên trường đặt ở trang Vi phạm. Trang Vi phạm có thêm tab **🖼 Bộ sưu tập ảnh** với bộ lọc (ngày, lớp, học sinh, máy, loại, tìm chữ) và các nút mở nhanh thư mục (hôm nay / theo nhóm / theo lọc / chọn sẵn từng ảnh).

**4. Không cho học sinh xóa ảnh vi phạm.** `-install` đặt quyền thư mục ảnh: học sinh (người ngồi tại máy) **thêm được ảnh mới nhưng không xóa/sửa**, còn giáo viên qua mạng vẫn thu và xóa được. Giảm rủi ro học sinh xóa bằng chứng trong vài giây trước khi máy giáo viên lấy về.

**5. Thiết lập máy học sinh so cả nội dung file.** Nút *Thiết lập máy học sinh* và *Trạng thái máy* giờ coi máy là “bản cũ” khi `KhoaVeyonServices.bat` trên máy **khác bản trong payload** (không chỉ khi thiếu dịch vụ), nên khi bạn thêm dịch vụ/tính năng mới thì các máy sẽ tự được chép file mới và chạy lại `-install`.

**6. Tự kiểm tra 1 máy.** Trang **Trạng thái máy** → nút **🧪 Tự kiểm tra 1 máy**: chạy lần lượt các chức năng trên một máy thử (dịch vụ, chặn internet, khóa Task Manager, khóa AI, giám sát, chụp màn hình, thông báo), đọc trạng thái thật rồi báo ✔/✘/▪; mỗi hạn chế bật lên đều tự gỡ lại. Rất hợp để thử nhanh trên phòng máy thật.

**7. Giám sát tự bật lại khi bị tắt.** Dịch vụ `KhoaVeyonAutoLog` nay còn **canh giữ tiến trình giám sát**: đọc `vcfg\kvguard.txt` (do máy giáo viên ghi khi bật giám sát), chạy lại trong phiên học sinh khi đăng nhập và **bật lại trong ~30 giây nếu học sinh tắt bằng Task Manager**. Thay cho tác vụ Task Scheduler `KhoaVeyonWatchLogon` (tự gỡ nếu còn).

**8. Chỉ-trang-cho-phép bằng trình duyệt (gồm miền con + Firebase/MongoDB).** Lệnh mới `-webonly`/`-weboff` (nút **Chỉ trang trong danh sách (trình duyệt...)** ở nhóm Internet, và bước trong Chế độ thi) chặn mọi trang trừ danh sách **bằng chính sách trình duyệt (URLAllowlist)** của Chrome/Edge/Brave/Cốc Cốc/Chromium. Khác với cách tường lửa `-allowpage` (chặn theo IP, không gồm miền con, dễ hỏng khi dịch vụ đám mây đổi IP), cách này khớp **tên miền và mọi miền con**, cho phép cả request XHR/fetch tới các miền đó, không ghim IP — nên ổn cho KhoaQuiz dùng Firebase/MongoDB. Danh sách miền tự thêm cho KhoaQuiz cũng được bổ sung Firestore, Firebase Storage và MongoDB.

**9. Chiếu sơ đồ chỗ ngồi.** Trang **Sơ đồ lớp học** → nút **📽 Chiếu sơ đồ cho lớp**: mở trang toàn màn hình (chiếu lên máy chiếu) hiện sơ đồ phòng máy kèm tên từng em, máy vắng, em được chuyển chỗ, máy hỏng — để đầu giờ học sinh tự tìm máy. Nhấn Esc hoặc ✕ để đóng.

> Các mục trên **chưa được thử trên Windows/phòng máy thật**; hãy thử trên 1 máy trước (dùng nút Tự kiểm tra 1 máy). Phần C# của dịch vụ đã được biên dịch thử, cú pháp PowerShell và toàn bộ kiểm thử Python đều đạt.

**Ghi nhận hoạt động khi đăng nhập là dịch vụ Windows, không còn là tác vụ Task Scheduler.** `-install` biên dịch (bằng `csc.exe` có sẵn của .NET Framework 4) và cài dịch vụ `KhoaVeyonAutoLog` (`%ProgramFiles%\KhoaVeyon\KhoaVeyonAutoLog.exe`, tự khởi động, chạy bằng SYSTEM). Mỗi khi có người đăng nhập, dịch vụ chạy `KhoaVeyonServices.bat -activitylog-start` **trong phiên và bằng quyền của người đó**, ẩn cửa sổ, giống tác vụ cũ; học sinh đã đăng nhập sẵn lúc cài cũng được bật ngay. Tác vụ `KhoaVeyonAutoLog` của bản cũ bị gỡ khi cài. Học sinh không dừng hay sửa được dịch vụ; nếu dịch vụ bị lỗi, Windows tự khởi động lại sau 1 phút. Không cài được thì `-install` trả mã 2 và Nhật ký báo lỗi. `-uninstall` gỡ dịch vụ và file exe. Chưa thử trên Windows thật.

Thư mục `lists` và `payload` đã kèm sẵn 4 file Excel mẫu và `KhoaVeyonServices.bat` của bạn.

Nút **Tìm máy học sinh trong mạng** quét dải /24 của mạng hiện tại, tìm máy đang mở cổng Veyon (11100) rồi thêm vào danh sách.

**Việc duy nhất phải làm tay:** chạy `Setup-MayHocSinh.bat` một lần trên mỗi máy học sinh (chuột phải, Run as administrator). File này mở tường lửa cho chia sẻ file và Task Scheduler từ xa, đặt `LocalAccountTokenFilterPolicy`, tạo `C:\cmd` và bật Veyon Service. Không thể làm từ xa vì chính các quyền này chưa mở.

**Gửi Setup-MayHocSinh.bat qua Veyon (không cần USB):** ở khối "Thiết lập máy học sinh", nút **📨 Gửi Setup-MayHocSinh.bat qua Veyon** dùng tính năng *Start application* của Veyon (`veyon-cli feature start <máy> da9ca56a-b2ad-4fff-8f8a-929b2927b442 {"applications":[...]}`). Nội dung `Setup-MayHocSinh.bat` và khóa `*_public.pem` trong `payload` được nén và nhúng vào một lệnh PowerShell, lệnh này ghi file ra `%TEMP%\KhoaVeyonSetup` trên máy học sinh rồi mở Setup bằng quyền quản trị. Mỗi máy hiện hộp thoại UAC, cần người bấm **Yes** (tài khoản thường thì nhập mật khẩu quản trị); máy phải đang có người đăng nhập Windows. Sau đó chương trình chờ tối đa 5 phút, máy nào mở được chia sẻ C$ thì tự chạy tiếp "Thiết lập máy học sinh". Veyon File Transfer không gọi được bằng `veyon-cli` nên không dùng. `KhoaVeyonServices.bat` không nhúng (quá dài cho dòng lệnh Windows), máy giáo viên gửi sau qua C$. Chưa thử trên Windows và Veyon thật.

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

**Báo cho học sinh khi vi phạm:** công tắc ở khối Giám sát vi phạm (mặc định bật, áp dụng ở lần bấm **Bật giám sát** tiếp theo). Chỉ khi máy giáo viên **đã nhận** ảnh (chương trình ghi biên nhận `<ảnh>.jpg.ok` cạnh ảnh trên máy học sinh), máy học sinh mới hiện bảng đỏ “ĐÃ GHI NHẬN VI PHẠM” ở đầu màn hình trong 10 giây: trang/ứng dụng, giờ chụp, “đã gửi cho giáo viên”. Mỗi lần vi phạm chỉ báo một lần (các ảnh chụp lại không báo nữa, cùng một trang không báo lại trong 60 giây). Máy giáo viên đang tắt thì không có biên nhận nên học sinh không được báo sai là “đã gửi”; học sinh tự xóa ảnh cũng không làm hiện thông báo.

**Thư mục, tên file và bộ sưu tập ảnh:**

- Ảnh vi phạm lưu ở `data\evidence\<ngày>\<lớp>\`, tên file gồm **trường, lớp, học sinh, máy, ngày, giờ, loại, trang/ứng dụng**, ví dụ `2026-10-18\10A1\THPT Nguyễn Du_10A1_Nguyễn Văn An_Máy 07_2026-10-18_09-42-10_Web_youtube.com.jpg`. Tên trường đặt ở trang **Vi phạm**; lớp lấy theo thời khóa biểu, học sinh theo sơ đồ chỗ ngồi; phần nào chưa biết thì bỏ khỏi tên, lớp chưa biết thì vào thư mục `Chua-ro-lop`. Ảnh của bản cũ (`data\evidence\<máy>`) giữ nguyên chỗ và vẫn hiện trong bộ sưu tập.
- Trang **Vi phạm** có thẻ **🖼 Bộ sưu tập ảnh**: mọi ảnh đã lưu (kể cả sau khi bấm “Xóa danh sách”), nhóm theo ngày và lớp. Lọc theo khoảng ngày (Hôm nay, 7 ngày, 30 ngày, Tất cả hoặc chọn ngày), lớp, học sinh, máy, loại vi phạm và ô tìm chữ.
- Mở nhanh thư mục: nút **📂 Thư mục ảnh hôm nay**; nút 📂 ở mỗi nhóm ngày–lớp; nút **Mở thư mục** theo bộ lọc đang chọn; nút 📂 trên từng ảnh mở thư mục và chọn sẵn đúng ảnh đó trong File Explorer.

**Gom báo động trùng (từ bản 1.4.0):**

- Học sinh ở yên một trang thì các ảnh chụp lặp lại được **gộp**: thông báo nổi chỉ có một cái cho mỗi (máy, trang/ứng dụng), tự cập nhật thành “PC07 vi phạm liên tục, 5 ảnh trong 42 giây”; **tiếng bíp chỉ kêu một lần** cho mỗi (máy, trang/ứng dụng) trong khoảng gộp. Trang khác hoặc máy khác thì báo riêng. Khoảng gộp mặc định 60 giây (đổi ở trang **Vi phạm**).
- Ở trang **Vi phạm**, các ảnh liên tiếp cũng gộp thành một thẻ, có dải ảnh nhỏ bên dưới để bấm xem từng ảnh. Ảnh gốc vẫn được giữ đủ.

**Báo cáo cuối buổi:** trang **Báo cáo** thống kê theo khoảng thời gian (hai giờ qua, hôm nay, 7 ngày, tất cả): tổng số lần vi phạm, số máy, máy vi phạm nhiều nhất, trang/ứng dụng bị vào nhiều nhất, giờ cao điểm, bảng theo máy và theo trang. “Một lần vi phạm” là các ảnh liên tiếp trong khoảng gộp nên không bị đếm quá. Trang nào có từ 3 máy trở lên cùng vào sẽ được gợi ý (có thể là trang cần cho bài học). Nút **＋ Cho phép** thêm dòng vào danh sách trang/ứng dụng được phép (vẫn phải mở trang danh sách và bấm Lưu). Nút **Xuất Excel** tạo file trong `data\reports` với 4 sheet: Tổng quan, Theo máy, Theo trang-ứng dụng, Chi tiết.

**Dọn ảnh cũ:** mặc định tự xóa ảnh, bản ghi (`alerts.jsonl`, `violations.csv`, các file `alerts-*.old`) và thư mục ảnh chụp trong `data\screenshots` cũ hơn **30 ngày** trên máy giáo viên, chạy khi mở chương trình rồi mỗi 6 giờ. Đổi số ngày hoặc đặt 0 (không tự xóa) ở trang **Vi phạm**; nút **Dọn ngay** chạy tức thì. Báo cáo Excel đã xuất không bị xóa tự động. Thời hạn lưu nên theo quy định của nhà trường. Từ bản 1.4.0 máy học sinh không còn ghi `evidence.csv`, nên không có dữ liệu cũ tồn lại ở đó.

**Tự chạy lại giám sát khi học sinh đăng nhập (và khi bị tắt):** bật công tắc ở khối Giám sát vi phạm (mặc định bật). Khi bấm **Bật giám sát**, chương trình ghi lệnh giám sát vào `C:\cmd\vcfg\kvguard.txt` trên máy học sinh. Dịch vụ `KhoaVeyonAutoLog` (chạy bằng SYSTEM) chạy lệnh này trong phiên của học sinh mỗi khi có người đăng nhập, **và kiểm tra lại mỗi ~30 giây: nếu học sinh tắt tiến trình giám sát bằng Task Manager thì tự bật lại**. Dịch vụ nhận biết giám sát còn sống qua file `alive.txt` (giám sát ghi mỗi 10 giây) nên không chạy trùng. Máy khởi động lại thì giám sát tự chạy lại, máy giáo viên tự nhận ảnh tiếp khi máy học sinh có mạng. **Tắt giám sát** xóa `kvguard.txt` (dịch vụ ngừng bật lại) và gửi cờ dừng; nếu máy đang tắt lúc bấm thì bấm lại khi máy bật. Cách này thay cho tác vụ Task Scheduler `KhoaVeyonWatchLogon` của bản cũ (được tự gỡ nếu còn). Cần máy đã cài dịch vụ `KhoaVeyonAutoLog` (bản mới của `-install`). Script và file guard nằm trong `C:\cmd\vcfg`, nên khóa thư mục `C:\cmd` ở trang Thiết lập để học sinh không sửa được.

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

> **Từ bản 3.1.0:** sơ đồ chỗ ngồi và điểm danh vắng nằm ở tab riêng **🪑 Sơ đồ lớp học** trên menu trái, không còn nằm trong trang Lớp & lịch dạy. **Từ 3.1.1:** ô máy tự co theo cỡ màn hình để cả lớp (40 máy trở lên) nằm gọn trong một màn hình; phần Điểm danh nằm cột bên phải khi màn hình rộng; Nhật ký tự thu gọn khi vào tab này.

Ở tab **Sơ đồ lớp học** (cần đã nhập danh sách lớp và xếp chỗ ngồi):

**Điểm danh hôm nay.** Bấm tên em để đánh dấu **vắng** (bấm lại để có mặt). Chương trình tự kiểm tra máy nào đang bật (mở cổng Veyon 11100) rồi chuyển các em sau sang **máy trống gần nhất** (gần theo hàng và dãy trên sơ đồ, thường là máy của em vắng):
- em có mặt nhưng máy của em đang tắt hoặc hỏng;
- em chưa có chỗ trong sơ đồ (lớp đông hơn số máy, em mới vào lớp...).

Chỗ đổi chỉ áp dụng cho hôm nay, sơ đồ gốc không bị sửa. Trên sơ đồ, ô xám gạch ngang là máy của em vắng, ô xanh là máy em được chuyển đến. Hết máy trống thì em đó được xếp **ngồi chung** với bạn ở máy dùng được gần nhất (ưu tiên máy ít người ngồi chung); máy của bạn đó hiện bảng "HÔM NAY NGỒI CHUNG MÁY VỚI BẠN: tên em", Nhật ký và trang đều ghi lại. Nếu **không máy nào trả lời** (chưa bật máy, sai tên máy) thì chương trình bỏ qua việc kiểm tra bật/tắt để không dồn chỗ sai; bật máy rồi bấm **Kiểm tra máy và dồn chỗ**. Điểm danh được lưu 60 ngày trong `data\school.json`. Lớp chưa xếp chỗ thì không tự xếp.

**Thông báo vị trí máy.** Nút **Thông báo cho cả lớp** hiện lên màn hình từng em bảng lớn "MÁY NÀY LÀ CỦA: tên em, lớp, số máy" trong N giây (mặc định 15), rồi thu thành nhãn nhỏ ở góc phải trên cùng nếu bật "giữ nhãn nhỏ". Em bấm vào bảng lớn để thu nhỏ. **Gỡ nhãn trên các máy** xóa nhãn. Em được chuyển chỗ tự nhận bảng "BẠN ĐƯỢC CHUYỂN SANG MÁY NÀY" (tắt được bằng công tắc "Tự báo cho em bị chuyển chỗ"). Công tắc **Tự thông báo khi sang tiết mới** gửi cho cả lớp mỗi khi thời khóa biểu chuyển lớp.

- Cách làm: chép `kvseat.ps1` và `kvseat.json` vào `C:\cmd\vcfg`, chạy bằng `schtasks` dưới tài khoản **người đang đăng nhập** (giống chụp màn hình). Máy không có ai đăng nhập thì báo lỗi ở Nhật ký.
- Số máy trên sơ đồ phải ứng với tên máy: điền **Tên máy mẫu** (ví dụ `MAY{n}`) hoặc dựa vào thứ tự danh sách máy ở trang Điều khiển lớp.
- **Chưa kiểm chứng trên Windows thật:** script PowerShell `kvseat.ps1` (cửa sổ luôn ở trên cùng, tác vụ chạy dưới tài khoản người dùng có thể đòi mật khẩu). Phần tính chỗ ngồi và giao diện đã thử trên Linux. Hãy thử nút thông báo trên 1 máy trước.

## Bật/tắt máy hàng loạt, trạng thái máy, tự động theo thời khóa biểu (từ bản 3.4.0)

**Trang Trạng thái máy.** Bảng tự cập nhật vài giây một lần khi trang đang mở: máy đang bật hay tắt (và từ bao lâu), có Veyon không, ai đăng nhập, đang bị hạn chế gì, đã khóa AI chưa, có đang giám sát không, địa chỉ MAC. Cột *Đang hạn chế* là lệnh KhoaVeyon đã gửi gần nhất (lưu ở `data\applied.json`), không đọc trực tiếp từ máy; từ bản 3.8.0 có nút *Kiểm tra hiệu lực* và máy bật lại thì tự áp lại hạn chế (xem mục "Bản 3.8.0"). Cột *Khóa AI* đọc thật qua `\\máy\C$`. Chương trình ghi một dòng vào Nhật ký khi máy vừa bật hoặc vừa tắt.

**Bật, tắt, khởi động lại, đăng xuất.** Các nút ở đầu trang Trạng thái máy, áp dụng cho máy đang tick (không tick = tất cả):
- **Bật máy** gửi gói Wake-on-LAN (UDP cổng 9 và 7) tới địa chỉ broadcast của mạng. Cần biết MAC: chương trình tự đọc MAC từ bảng ARP khi máy đang bật và lưu vào `data\KhoaVeyon.json`; có thể bấm **Lấy MAC** hoặc bấm vào ô MAC để nhập tay. Máy phải bật Wake-on-LAN trong BIOS và card mạng, và máy giáo viên phải cùng mạng LAN.
- **Tắt máy / Khởi động lại** chạy `shutdown /t N /f` bằng SYSTEM qua `schtasks` (cùng cách các lệnh khác), mặc định chờ 30 giây để học sinh thấy thông báo của Windows. **Hủy lệnh tắt máy** chạy `shutdown /a`. Có hộp thoại xác nhận.
- **Đăng xuất học sinh** dùng `query user` và `logoff` (kể cả phiên đã ngắt kết nối).

**Trang Tự động theo tiết.**
1. **Chế độ lớp** là một bộ lệnh *Vào tiết* và *Hết tiết*, ví dụ "Kiểm tra": vào tiết `Chỉ cho phép trang trong danh sách` + `Khóa Task Manager`, hết tiết `Cho phép internet` + `Mở khóa`. Có sẵn 4 chế độ mẫu, sửa hoặc thêm tùy ý. Nút **Chạy thử** chạy ngay trên các máy đang chọn.
2. **Gán chế độ cho lớp**: mỗi lớp (lấy từ thời khóa biểu) một chế độ, dòng "Mọi lớp khác" áp cho lớp còn lại.
3. Khi lớp hiện tại thay đổi, chương trình chạy lệnh *Hết tiết* của chế độ cũ rồi lệnh *Vào tiết* của chế độ mới (hai lớp cùng chế độ thì giữ nguyên, hai tiết liền nhau của một lớp không bị mở khóa giữa chừng). Tiết tính bắt đầu sớm tối đa 5 phút. Lệnh chạy trên các máy đang bật trong danh sách máy, **không hỏi lại**: lệnh có dấu ⚠ (đóng ứng dụng, khóa AI...) có thể làm mất bài chưa lưu. Có tôn trọng công tắc *Chụp màn hình trước khi khóa* và *Khóa AI cùng Khóa toàn bộ*.
4. **Bật máy trước tiết đầu** N phút và **tắt máy sau tiết cuối** N phút (mỗi ngày một lần, chỉ khi ngày đó có tiết và không còn tiết nào đang diễn ra). Mặc định tắt (0).
5. Cài đặt lưu trong `data\school.json`. Công tắc **Bật tự động** mặc định tắt. Chương trình phải đang mở để tự động chạy.

**Chưa kiểm chứng trên Windows thật:** gói Wake-on-LAN trên card mạng thật, `shutdown`/`logoff` từ xa, đọc MAC bằng `arp -a`, `query user` trên nhiều máy. Phần logic (chuyển tiết, hẹn giờ bật/tắt, quét trạng thái, giao diện) đã thử trên Linux bằng cổng giả lập.

**Chặn mạnh hơn (bản mới):** ở trang **Trang AI bị chặn** có thêm thẻ *Khi bấm "Khóa toàn bộ công cụ AI", làm thêm* với 3 công tắc (ghi vào `ai_opts.txt` cạnh các file Excel, gửi xuống máy học sinh, có hiệu lực ở lần khóa AI tiếp theo):
- **Chặn AI Overviews trong Google Search** (mặc định bật): ép công cụ tìm kiếm mặc định của Chrome/Edge về bộ lọc **Web** (`google.com/search?...&udm=14`) — trang kết quả này **không có khung AI Overview / AI Mode**. Áp cho tìm kiếm từ thanh địa chỉ. *Giới hạn: nếu học sinh tự mở google.com rồi gõ tìm thì khung AI vẫn có thể hiện; muốn bỏ hẳn phải dùng “Chỉ trang cho phép”.*
- **Tắt DNS-over-HTTPS** (mặc định bật): tắt DNS mã hóa của trình duyệt, để cách chặn bằng file hosts không bị lách.
- **Chặn mọi extension trình duyệt** (mặc định tắt): đặt `ExtensionInstallBlocklist=*` cho Chrome/Edge/Brave — tắt **toàn bộ** extension (không chỉ extension AI), nên cân nhắc vì tắt cả extension học tập.

Danh sách AI mặc định (`BlockAIList.xlsx` và các nhóm "Thêm nhanh") cũng được mở rộng: thêm AI lập trình (Blackbox, Codeium, Cursor, v0, Bolt...) và AI ít nổi (Dora, Gamma, Tome, ChatPDF, Monica, Sider, FlowGPT...). Vẫn là danh sách chặn nên **AI mới/lạ không có trong danh sách thì không bị chặn** — giờ thi nên dùng “Chỉ trang cho phép (trình duyệt)”.

## Khóa toàn bộ công cụ AI (từ bản 3.2.0)

Ở trang **Điều khiển lớp**, khối **Công cụ AI** có hai nút: **Khóa toàn bộ công cụ AI** (`-blockai`) và **Mở khóa công cụ AI** (`-allowai`). Danh sách trang AI nằm ở trang **Trang AI bị chặn** (`BlockAIList.xlsx`, kèm sẵn khoảng 60 trang phổ biến; thêm, bớt rồi bấm **Lưu và áp dụng**).

Nút này làm bốn việc trên máy học sinh (chạy bằng SYSTEM qua dịch vụ `KhoaVeyonService_blockai`, nên học sinh không bị hỏi UAC):

1. **Chặn trang web AI** trong Chrome, Edge, Brave (chính sách `URLBlocklist`, chặn cả tên miền con) và Firefox (`WebsiteFilter`).
2. **Tắt AI tích hợp trong trình duyệt:**
   - Chrome: Gemini in Chrome, AI Mode, Help me write, Lens overlay, tổ chức tab bằng AI... (`GenAiDefaultSettings` và các chính sách riêng).
   - Edge: Copilot và thanh bên, Copilot đọc nội dung trang, Compose (viết bằng AI).
   - Firefox: chatbot ở thanh bên, tóm tắt link, gom tab bằng AI (`GenerativeAI`, `AIControls`).
   - Brave: Leo.
3. **Chặn bằng file hosts** cho các trình duyệt không hỗ trợ chính sách (Opera, Cốc Cốc...). Chỉ chặn đúng tên miền trong danh sách và bản `www.`. Tắt bằng `AI_USE_HOSTS=0` ở đầu `KhoaVeyonServices.bat`.
4. **Đóng ứng dụng AI trên máy** (ChatGPT, Claude, Copilot, Perplexity, DeepSeek bản cài trên Windows). Muốn chặn bền, thêm thư mục cài đặt vào `BlockAppList.xlsx`.

Lần đầu bấm, chương trình hỏi xác nhận vì **đóng các trình duyệt đang mở** để tab AI đang mở không dùng tiếp được (tắt bằng `AI_CLOSE_BROWSERS=0`). Bấm lại lần sau thì không đóng trình duyệt nữa.

**Mở khóa** trả lại đúng các thiết lập trình duyệt đã có trước khi khóa (bản sao lưu nằm ở `C:\ProgramData\KhoaVeyon`, chỉ SYSTEM và quản trị đọc/ghi được), xóa phần đã thêm vào hosts rồi xóa bộ nhớ đệm DNS. Danh sách chặn có sẵn của nhà trường được giữ nguyên.

Tùy chọn `AI_BLOCK_EXTENSIONS=1` (mặc định tắt) chặn cài và chạy **mọi** tiện ích mở rộng của Chrome và Edge, để chặn các tiện ích AI chèn vào trang. Chỉ bật khi trường không dùng tiện ích nào.

**Máy học sinh cũ cần cài lại dịch vụ một lần:** bấm **Thiết lập máy học sinh** (hoặc **Kiểm tra và gửi file xuống máy**). Chương trình thấy máy chưa có dịch vụ `KhoaVeyonService_blockai` thì chép `KhoaVeyonServices.bat` mới và chạy `-install`. Sau đó vào trang **Thiết lập ban đầu** và bấm lại **Thiết lập máy giáo viên** để thêm hai mục mới vào Veyon (chỉ thêm mục còn thiếu, mục khác giữ nguyên).

**Giới hạn (nên nói rõ với giáo viên):**
- Không chặn được AI nằm trong trang lớn, như Gemini trong Google Docs, Canva Magic, Quizlet, và phần tóm tắt AI trong kết quả tìm kiếm Google. Chặn cả trang đó thì học sinh mất luôn công cụ học.
- Học sinh dùng điện thoại, mạng 4G hoặc máy cá nhân thì nằm ngoài tầm kiểm soát của chương trình.
- Chính sách trình duyệt chỉ có hiệu lực khi học sinh dùng tài khoản thường, không phải quản trị viên.
- Tên và giá trị chính sách thay đổi theo phiên bản trình duyệt. Mở `chrome://policy`, `edge://policy`, `about:policies` (Firefox) sau khi khóa để xem chính sách nào được nhận.
- Windows Defender có thể cảnh báo khi file hosts bị sửa. Nếu gặp, tắt hosts bằng `AI_USE_HOSTS=0`; chính sách trình duyệt vẫn chặn Chrome, Edge, Brave, Firefox.
- **Chưa kiểm chứng trên Windows và trình duyệt thật.** Đã kiểm tra tên chính sách theo tài liệu của Google, Microsoft, Mozilla. Hãy thử trên 1 máy: bấm khóa, mở `chatgpt.com` và xem trang chính sách của trình duyệt, rồi bấm mở khóa và kiểm tra mọi thứ trở lại như cũ.

### Ba tính năng đi kèm nút khóa AI (từ bản 3.3.0)

1. **Báo động khi học sinh cố dùng AI.** Giám sát vi phạm tự nhận ra trang web có trong `BlockAIList.xlsx` (và các ứng dụng AI cài trên máy: ChatGPT, Claude, Copilot, Perplexity, DeepSeek) rồi chụp ảnh, báo động, ghi vào trang **Vi phạm** và **Báo cáo** với nhãn **Công cụ AI** (màu tím). Hoạt động cả khi bạn chưa khóa AI, và cả khi `AllowPage.xlsx` để trống. Khi AI đã bị khóa, học sinh gõ địa chỉ trang AI vẫn bị ghi nhận là một lần cố vào. Không có nút "Cho phép" cho loại này. Đọc URL bằng UI Automation nên cùng giới hạn với giám sát hiện có (trình duyệt toàn màn hình, Firefox).
2. **Kiểm tra máy nào đã khóa AI.** Nút **Kiểm tra máy nào đã khóa AI** (khối Công cụ AI) đọc từ xa qua `\\máy\C$` và báo từng máy: *ĐÃ KHÓA AI*, *CHƯA KHÓA AI* hoặc *KHÓA DỞ* (có hosts nhưng thiếu chính sách trình duyệt). Máy chưa khóa hiện màu đỏ ở Nhật ký để bạn thấy ngay. Cần tài khoản quản trị của máy học sinh (giống chép file).
3. **Khóa AI cùng lúc với Khóa toàn bộ.** Công tắc ở khối Công cụ AI: bật thì bấm **Khóa toàn bộ** sẽ khóa AI trước rồi mới khóa máy, bấm **Mở khóa toàn bộ** sẽ mở máy rồi mở AI. Nếu bật "Tự chụp màn hình trước khi khóa" thì ảnh được chụp trước khi trình duyệt bị đóng. Mặc định tắt.

**Chưa kiểm chứng trên Windows thật:** phần nhận ra trang AI trong script giám sát (PowerShell, đọc thanh địa chỉ) và việc đọc `C:\ProgramData\KhoaVeyon` từ xa. Phần Python đã được thử bằng thư mục giả thay cho `\\máy\C$`.

## Chế độ thi, báo cáo in/PDF và sức khỏe cả lớp (từ bản 3.7.0)

**Chế độ thi (trang 📝 Chế độ thi).** Một nút **Bắt đầu thi** làm lần lượt: chụp màn hình cả lớp, khóa toàn bộ công cụ AI, chỉ cho vào trang trong `AllowPage.xlsx`, (tùy chọn) khóa Task Manager và Settings, bật giám sát, hiện nhãn "Máy này của ai" cho lớp đã chọn. Mỗi bước tick bật hoặc tắt được. Có thể đặt số phút để tự tắt khi hết giờ, nếu không thì bấm **Kết thúc thi**: gỡ nhãn, tắt giám sát (tùy chọn), cho vào lại mọi trang, mở khóa và mở khóa AI. Máy đang tắt lúc bấm thì bị bỏ qua và ghi ở Nhật ký; trạng thái chế độ thi được lưu ở `data\exam.json` nên mở lại chương trình vẫn thấy đang thi.

**Báo cáo.** Trang **Báo cáo** có thêm nút **🖨 Báo cáo in / PDF**: tạo file HTML trong `data\reports` (có ảnh nhúng, tối đa 120 ảnh) và mở ra, bấm **In / Lưu thành PDF**. Nội dung: tổng quan, bảng theo học sinh, từng lần vi phạm kèm giờ, máy, chỗ ngồi và ảnh. Excel có thêm sheet **Theo học sinh** và các cột Học sinh, Lớp ở sheet Chi tiết. Tên học sinh lấy theo sơ đồ chỗ ngồi tại lúc vi phạm; vi phạm cũ hoặc lớp chưa xếp chỗ thì ghi "(chưa biết học sinh)". Nếu máy giáo viên có Pillow thì ảnh được thu nhỏ trước khi nhúng.

**Sức khỏe cả lớp (trang 📡 Trạng thái máy).** Cột **Sức khỏe** có đèn xanh (tốt), vàng (cần chú ý), đỏ (có lỗi), xám (máy tắt) kèm lý do: Veyon chưa chạy, chưa mở chia sẻ C$, dịch vụ KhoaVeyon chưa cài hoặc là bản cũ (so với file trong `payload`), giám sát đã bật mà không chạy, và khi đang thi: máy chưa giám sát hoặc chưa khóa AI. Bấm **Sửa** cạnh từng lý do, hoặc nút 🔧 phía trên bảng để sửa cùng lúc mọi máy bị lỗi đó.
- Script giám sát từ bản này ghi tín hiệu `alive.txt` mỗi 10 giây. Máy đang chạy giám sát bản cũ sẽ báo "không chạy" cho đến khi bấm lại **Bật giám sát** một lần.
- Cần chia sẻ C$ giống các tính năng khác; máy chưa mở được thì đèn đỏ ghi rõ cần chạy `Setup-MayHocSinh.bat`.

**Chưa kiểm chứng trên Windows thật:** chuỗi các bước của chế độ thi (từng bước dùng lại đúng nút đã có, đã thử thứ tự và xử lý máy tắt bằng giả lập), đọc `alive.txt` và so file dịch vụ qua `\\máy\C$`, mở báo cáo HTML bằng `os.startfile`.

## Màn hình chờ khi thao tác chạy lâu

Thao tác nào quá 0,7 giây chưa xong (quét mạng, hỏi Veyon, kết nối KhoaQuiz, đọc file Excel lớn...) thì giữa màn hình hiện khung **"Chương trình vẫn đang chạy, vui lòng chờ một chút"** kèm việc đang làm và số giây đã chờ; khung chặn bấm lặp. Quá 8 giây thì có thêm lời giải thích và nút **Ẩn, làm việc khác** (lệnh vẫn chạy tiếp, kết quả báo khi xong). Nút vừa bấm hiện vòng quay và bị khóa tạm cho tới khi có kết quả. Chuyển trang mà dữ liệu về chậm thì trang hiện "Đang mở trang...". Các việc chạy nền trên nhiều máy (khóa máy, gửi file...) vẫn hiện tiến độ "x/y máy" ở góc trên bên phải như cũ. Các lệnh hỏi ngầm theo hẹn giờ không làm hiện khung chờ.

## Kết nối KhoaQuiz và KhoaTool

> Cần KhoaQuiz bản có "Liên kết KhoaTool / KhoaVeyon" (mã riêng cho từng ứng dụng, `link/rosters`, `link/exams`, số máy `?m=`). Mọi nút dưới đây chỉ gọi mạng khi bấm, có giới hạn thời gian; mất Internet thì chỉ các nút này báo lỗi, việc khóa máy không bị ảnh hưởng.

**1. Liên kết tài khoản KhoaQuiz.** Trong KhoaQuiz: Cài đặt → *Liên kết KhoaTool / KhoaVeyon* → chọn **KhoaVeyon** → Tạo mã. Trong KhoaVeyon: Cài đặt → *Liên kết KhoaQuiz* → dán mã. Mã của KhoaVeyon tách riêng với mã của KhoaTool. Mã lưu trong `data\khoaquiz.json` (trên Windows chỉ tài khoản đang dùng, Administrators và SYSTEM đọc được) và không bao giờ hiện lại trên giao diện.

**2. Danh sách lớp từ KhoaTool hoặc KhoaQuiz.** Trang *Lớp & lịch dạy*:
- Nút *Nhập danh sách lớp* nhận thêm file `.json` xuất từ KhoaTool (Thống kê → Xuất cho KhoaVeyon).
- Nút *☁ Lấy từ KhoaQuiz* lấy danh sách học sinh từ KhoaQuiz (nhiều trường thì hỏi chọn trường).
- Hai cách này **gộp**: chỉ cập nhật các lớp có trong file, lớp khác giữ nguyên; chỗ ngồi của em đã rời lớp bị bỏ. Nhập file Excel của trường vẫn thay toàn bộ như cũ.

**3. Đối chiếu điểm danh với bài làm.** Trang *Sơ đồ lớp học* → *🔎 Đối chiếu KhoaQuiz*: so danh sách lớp, điểm danh vắng và chỗ ngồi hôm nay với bài làm KhoaQuiz trong ngày. Báo: em không làm bài mà đang tính có mặt (gợi ý vắng, bấm một nút để đánh vắng sau khi xác nhận), em có bài làm mà bị đánh vắng, em nộp bài từ máy là chỗ của bạn khác, máy không bật, tên có bài làm mà không có trong danh sách lớp.

**4. Bài kiểm tra KhoaQuiz trong Chế độ thi.** Bước mới *Mở bài kiểm tra KhoaQuiz trên từng máy* (mặc định tắt). Dán link bài kiểm tra hoặc bấm *📋 Chọn từ KhoaQuiz*. Khi bắt đầu thi: tự thêm tên miền KhoaQuiz, Firebase, phông chữ Google vào `AllowPage.xlsx` (nếu thiếu) và gửi xuống máy trước bước "chỉ trang cho phép"; sau bước khóa AI (đóng trình duyệt) thì mở link trên từng máy bằng tính năng *Open website* của Veyon (không được thì thử *Start application* với `explorer.exe`), link có gắn `&m=<tên máy>`. Trong giờ thi có nút *Đối chiếu tên – máy*.

**5. Xuất cho KhoaTool.** Trang *Báo cáo* → *📤 Xuất cho KhoaTool*: file `khoaveyon-<ngày>.json` (lưu cả ở `data\reports`) gồm các lớp điểm danh hôm nay (vắng, em được chuyển chỗ vì máy hỏng/tắt, ngồi chung), máy hỏng (theo sơ đồ) và máy không lên, học sinh vi phạm hôm nay (tên, số lần, trang/ứng dụng), tình trạng Veyon (số máy kết nối). Không có ảnh chụp màn hình. Trong KhoaTool: Báo cáo buổi dạy hoặc Điểm danh → *Nhập từ KhoaVeyon*.

**Chưa kiểm chứng trên Windows và Veyon thật:** tên khóa `websiteUrls` của Veyon Open website (đã có phương án dự phòng `explorer.exe`), việc trang KhoaQuiz tải đủ khi bật "chỉ trang cho phép" (lệnh này chặn theo IP, trang dùng CDN có thể thiếu: hãy thử trên một máy trước giờ thi). Logic, giao diện và luồng gọi KhoaQuiz đã thử bằng KhoaQuiz giả lập (kiểm thử `tests/test_khoalink.py` và thử giao diện bằng trình duyệt).

## Bản 3.9.0: tự chạy khi mở máy

**1. KhoaVeyon tự chạy khi giáo viên đăng nhập Windows.** Cài đặt → thẻ *Tự chạy khi mở máy* → bật công tắc. Chương trình đặt file `KhoaVeyon.vbs` vào thư mục Startup của bạn (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`), file này chạy `Chay-KhoaVeyon.bat --background`: chạy ẩn, không mở cửa sổ. Nhờ vậy hẹn giờ theo thời khóa biểu, giám sát, tự áp lại hạn chế hoạt động từ đầu buổi. Muốn xem giao diện thì chạy `Chay-KhoaVeyon.bat` như mọi khi (nó mở lại cửa sổ của bản đang chạy nền). Bản chạy nền không tự thoát sau 3 phút như bình thường, chỉ dừng khi bấm *Thoát*. Tắt công tắc là xóa file. Không cần quyền quản trị. Nếu thư mục chương trình đổi chỗ, tắt rồi bật lại công tắc.

**2. Máy học sinh tự áp hạn chế khi có người đăng nhập.** Trang *Tự động* → thẻ *Áp khi học sinh đăng nhập*. Chọn lệnh (khóa Task Manager/Control Panel/Registry, chặn mở app ngoài danh sách, tắt tiếng) rồi bấm *Cài lên máy đang chọn*. Trên mỗi máy tạo `vcfg\KhoaVeyonLogon.bat` và tác vụ `KhoaVeyonLogon` (kích hoạt khi đăng nhập, nhóm Users, ẩn, chạy trong phiên của chính học sinh). Máy bật lên là bị hạn chế ngay, kể cả khi máy giáo viên đang tắt. Nút *Kiểm tra* cho biết máy nào đã có tác vụ, *Gỡ* xóa tác vụ.

Giới hạn cần biết:
- Chỉ có các lệnh chạy được trong phiên người dùng, không cần quyền quản trị. Chặn internet, khóa AI, kiosk không nằm trong danh sách này (chặn internet và khóa AI vẫn được tự áp lại bởi tính năng *tự áp lại khi máy bật lại* của bản 3.8.0 khi KhoaVeyon đang mở).
- Mở khóa giữa buổi chỉ có tác dụng đến lần đăng nhập kế tiếp, vì lúc đó chính sách áp lại. Muốn bỏ hẳn thì bấm *Gỡ*.
- Chặn mở app ngoài danh sách dùng `KeepAppList.xlsx` đang có trên máy học sinh; nếu danh sách này chưa được gửi xuống thì cả máy có thể bị chặn quá tay, hãy thử trên một máy trước.
- Chưa được thử trên Windows thật, nên hãy cài thử trên một máy, đăng xuất, đăng nhập lại rồi xem kết quả trước khi cài cho cả phòng.

## Bản 3.8.0: tám tính năng mới

> **Chưa kiểm chứng trên Windows và máy học sinh thật** (giống các tính năng trước): các script PowerShell mới (`kvstate.ps1`, `kvexam.ps1`, `kvclip.ps1`) chưa chạy trên Windows. Logic Python, giao diện và luồng lệnh đã thử bằng giả lập (33 bài kiểm thử, kể cả thử giao diện bằng trình duyệt). Hãy thử trên 1 máy trước. Mỗi lần đẩy lên GitHub, mục **Actions** sẽ chạy kiểm tra cú pháp PowerShell trên Windows thật (xem mục 3).

**1. Tự áp lại hạn chế khi máy bật lại.** Chương trình theo dõi các máy đang có hạn chế (theo `applied.json`). Máy nào chuyển từ tắt sang bật thì đợi có người đăng nhập (tối đa 5 phút) rồi gửi lại đúng các lệnh đang bật, theo thứ tự đã gửi. Công tắc ở trang **Trạng thái máy** (mặc định bật). Giới hạn: chỉ chạy khi KhoaVeyon đang mở; máy khởi động lại nhanh hơn 8 giây giữa hai lần dò có thể không bị phát hiện; lệnh đã gỡ (Mở khóa...) thì không áp lại.

**2. Kiểm tra hiệu lực sau khi khóa.** Hai nút ở trang **Trạng thái máy**: *Kiểm tra hiệu lực* và *Kiểm tra và gửi lại lệnh nếu lệch*. Chương trình chạy script chỉ-đọc `kvstate.ps1` trên máy học sinh (SYSTEM qua `schtasks`), đọc trạng thái thật rồi so với lệnh đã gửi: chặn internet (luật tường lửa `KhoaVeyonBlock`), khóa Task Manager, chặn mở app (`RestrictRun`), khóa toàn bộ, kiosk (tiến trình còn sống không), khóa AI (như cũ). Chặn ứng dụng và tắt tiếng *chưa kiểm được* và được ghi rõ như vậy. Mục đọc từ registry của người dùng cần có người đăng nhập, không thì báo "chưa kiểm được". Chế độ thi có thêm bước tự kiểm tra sau khi bật.

**3. Kiểm tra tự động trên Windows (GitHub Actions).** File `.github/workflows/ci.yml` chạy `pyflakes` và toàn bộ kiểm thử trên Linux, và trên **Windows thật**: kiểm tra cú pháp mọi script PowerShell (cả phần PowerShell nhúng trong `KhoaVeyonServices.bat`, bằng `tests/check_powershell.ps1`) rồi chạy lại kiểm thử Python. Không thay được việc thử trên phòng máy thật, nhưng bắt được lỗi cú pháp và đường dẫn trước khi chép xuống máy học sinh.

**4. Danh sách riêng theo chế độ lớp.** Ở mỗi trang danh sách có thêm *Bản riêng*: **Lưu bảng thành bản riêng...** tạo file `AllowPage--Kiểm tra Văn.xlsx` cạnh bản chính (tên file chỉ gồm chữ, số, dấu cách, gạch ngang). Ở trang **Tự động theo tiết**, mỗi chế độ lớp có dòng **Danh sách riêng**: vào tiết thì chương trình chép bản riêng xuống máy học sinh dưới đúng tên danh sách chính rồi mới chạy lệnh; hết tiết thì chép lại danh sách chính. Nút *Chạy thử* cũng làm như vậy.

**5. Thông báo tùy ý.** Thẻ **Thông báo cho học sinh** ở trang Điều khiển lớp: gõ nội dung (tối đa 160 ký tự) và số giây, bấm gửi. Dùng chung khung `kvseat` với nhãn "Máy này của ai", nên thay nhãn chỗ ngồi đang hiện (chữ tự nhỏ lại khi dài).

**6. Thống kê vi phạm theo thời gian.** Trang **Báo cáo** có thêm khoảng *Tuần này*, *Tháng này*, *30 ngày qua* và các khối: xu hướng theo ngày và theo thứ trong tuần, **học sinh tái phạm** (vi phạm từ 2 ngày khác nhau), **trang/ứng dụng bị vào lặp lại** từ 3 ngày (để cân nhắc cho phép hoặc chặn hẳn). Excel có thêm 3 sheet (*Theo ngày*, *Tái phạm*, *Lặp lại nhiều ngày*); báo cáo in có thêm mục xu hướng và tái phạm.

**7. Chế độ thi mở rộng.** Thêm các bước (mỗi bước tick bật/tắt, mặc định tắt trừ kiểm tra lại):
- **Khóa ổ USB** bằng chính sách "Removable Disks: Deny read/write" và **chặn in** bằng cách dừng Print Spooler (`kvexam.ps1`, SYSTEM). Cả hai nằm trong registry/dịch vụ nên **còn nguyên sau khi khởi động lại**; kết thúc thi tự mở lại. Máy tắt lúc kết thúc thi thì còn bị khóa: dùng nút **Gỡ khóa USB / in / sao chép-dán** ở trang Chế độ thi khi máy bật.
- **Chặn sao chép-dán** bằng script `kvclip.ps1` chạy trong phiên của học sinh, xóa clipboard mỗi 0,4 giây (cách thô: học sinh cũng không dán được trong cùng bài thi; mất khi máy khởi động lại).
- **Thu file bài làm** khi kết thúc thi (hoặc nút *Thu file bài làm ngay*): chép về `data\exam_files\<ngày giờ>\<máy>` các file *mới sửa* trong giờ thi từ các thư mục bạn nhập (mỗi dòng một thư mục, `{user}` = tài khoản học sinh đang đăng nhập, ví dụ `C:\Users\{user}\Documents`). Mỗi file tối đa 50 MB, mỗi máy 500 MB và 1000 file; bỏ qua `~$*`, `.tmp`, `.lnk`.

**8. Quyền riêng tư dữ liệu giám sát.** Ảnh chụp màn hình học sinh là dữ liệu nhạy cảm (có thể thấy tin nhắn, tài khoản cá nhân), nên:
- **Nhãn công khai**: bật giám sát thì máy học sinh hiện nhãn nhỏ "ĐANG GIÁM SÁT" ở góc màn hình, tắt giám sát thì gỡ (công tắc ở khối Giám sát vi phạm, mặc định bật).
- **Mã xem ảnh** (tùy chọn, trang Vi phạm): đặt mã thì ảnh bị khóa, nhập mã mới xem được và tự khóa lại sau 15 phút. Báo cáo in có ảnh cũng cần mở khóa. Mã chỉ lưu dạng băm PBKDF2 trong `data\privacy.json`, sai 5 lần thì khóa tạm 30 giây, **quên mã thì không khôi phục được** (xóa `data\privacy.json` để bỏ, khi đó ảnh vẫn nằm trên đĩa không mã hóa).
- **Giới hạn quyền đọc thư mục ảnh** (Windows, tùy chọn): chỉ tài khoản đang chạy chương trình, quản trị viên và SYSTEM đọc được `data\evidence`.
- **Giữ ảnh ngắn hơn bản ghi:** mặc định ảnh xóa sau **14 ngày** (trước đây 30), bản ghi chữ không kèm ảnh giữ **180 ngày** để thống kê tuần/tháng (cài đặt cũ giữ nguyên số ngày đã chọn). Thời hạn lưu nên theo quy định của nhà trường.
- Mã xem ảnh khóa việc xem qua giao diện này; không mã hóa file ảnh trên đĩa.

## Cấu hình Veyon (trang mới, từ bản 1.1.0)

Trang **Cấu hình Veyon** có 3 khối. Bản sao lưu lưu ở `data\veyon-backups` (file JSON, tên bắt đầu bằng `master_` hoặc tên máy).

1. **Sao lưu, so sánh, khôi phục.** Sao lưu master bằng `veyon-cli config export`. Máy học sinh được đọc từ xa: chương trình chép `vcfg-export.bat` vào `C:\cmd\vcfg`, chạy bằng `schtasks` (SYSTEM), rồi lấy file về. **So sánh** chọn hai bên bất kỳ (master hiện tại, máy học sinh đọc trực tiếp, hoặc file sao lưu), kết quả hiện ở Nhật ký. **Khôi phục** dùng `config import` nên thay toàn bộ cấu hình; cấu hình cũ của máy đó được tự lưu trước.
2. **Đẩy cấu hình Veyon Service xuống máy học sinh.** Bạn nhập danh sách khóa `Nhóm/Tên` và giá trị, chương trình ghi từng khóa bằng `config set` trên máy học sinh (không đụng khóa khác), tùy chọn khởi động lại `VeyonService`, và lưu cấu hình cũ trước khi đẩy. Đường dẫn `veyon-cli.exe` trên máy học sinh đặt ngay trong khối này.
3. **Danh sách máy của Veyon Master.** Thêm các máy đang chọn vào Master bằng `veyon-cli networkobjects add` (nhóm `location` tùy chọn). Máy đã có thì bỏ qua. Cần quyền quản trị nên Windows hiện UAC.

**Chưa kiểm chứng trên Windows và Veyon thật:** định dạng kết quả `networkobjects list` (dùng để nhận biết máy đã có), tên các khóa gợi ý (`Network/PrimaryServicePort`, `Network/FirewallExceptionEnabled`, `Service/Autostart`), và việc `config import` có thay toàn bộ hay gộp tùy phiên bản Veyon. Logic đã thử với `veyon-cli` giả trên Linux. Hãy thử trên 1 máy trước, rồi dùng **So sánh** để kiểm tra kết quả.

## Cấu trúc mã nguồn (từ bản 3.5.0)

Mã trước đây nằm trong một file `KhoaVeyon.py` (hơn 5000 dòng) nay chia theo chức năng. `KhoaVeyon.py` chỉ còn là điểm khởi động; cách chạy, thư mục `data`, `lists`, `payload` và các file `.bat` không đổi.

```
KhoaVeyon.py          điểm khởi động (gọi kv.app.run)
kv/                   mã chương trình (Python), mỗi file một nhóm chức năng
scripts/              script gửi xuống máy học sinh (PowerShell, bat), đọc bằng paths.load_script()
web/                  giao diện: index.html + css/*.css + js/*.js (nạp theo số thứ tự) + assets/
tests/                kiểm thử nhanh: python -m unittest discover tests
```

**Các module trong `kv/`, xếp từ nền tảng lên trên** (module trên chỉ nhập từ module dưới, không có vòng nhập, trừ một chỗ nhập muộn trong `vcfg._op_authkeys`):

| Nhóm | Module | Nội dung |
|---|---|---|
| Nền tảng | `paths`, `actions`, `config`, `excel_lists`, `meta`, `runtime`, `remote` | đường dẫn và phiên bản, danh sách lệnh, cài đặt, 4 file Excel, hằng giao diện, trạng thái chung (CFG, nhật ký, công việc nền), chạy lệnh Veyon và `schtasks` |
| Máy học sinh | `network`, `applied`, `jobs`, `reapply`, `verify`, `setup`, `setup_jobs`, `authkeys`, `vcfg` | dò mạng, MAC, Wake-on-LAN; lệnh đã gửi; chạy lệnh nhiều máy; thiết lập máy giáo viên và máy học sinh; khóa xác thực; cấu hình Veyon |
| Giám sát | `screenshot`, `evidence`, `privacy`, `watch`, `alerts`, `cleanup`, `monitor`, `reports` | chụp màn hình, script giám sát, báo động và gom trùng, dọn dữ liệu cũ, vòng lặp nhận ảnh, báo cáo |
| Lớp học | `school`, `seating`, `attendance`, `announce`, `school_api` | lớp và thời khóa biểu, sơ đồ chỗ ngồi, điểm danh, thông báo "Máy này của ai", API trang lớp |
| Tự động | `power`, `status`, `ai`, `auto`, `examlock` | bật tắt máy, trạng thái máy, khóa AI, tự động theo tiết |
| API và khởi động | `updater`, `api_lists`, `api_core`, `routes`, `server`, `app` | tự cập nhật, các API, bảng đường dẫn, máy chủ HTTP, khởi động |

**Thêm một chức năng mới:** viết hàm xử lý `api_xxx(body)` trong module phù hợp (ném `ApiError` khi người dùng nhập sai), thêm vào `GET_ROUTES` hoặc `POST_ROUTES` trong `kv/routes.py`, rồi thêm file `web/js/NN-xxx.js` và một dòng `<script>` trong `web/index.html`.

**Thay đổi khác so với bản 3.4.x:**

- Các script PowerShell và bat nhúng trong mã (giám sát, chụp màn hình, thông báo chỗ ngồi, thiết lập máy học sinh, khóa `C:\\cmd`) được tách ra `scripts/`; nội dung giữ nguyên từng ký tự.
- `openpyxl` chỉ được nạp khi thật sự đọc hoặc ghi Excel, nên chương trình mở nhanh hơn khoảng 0,2 giây.
- Giao diện tách thành 6 file CSS và 16 file JS theo trang, giữ nguyên thứ tự nạp.
- **Nâng từ 3.4.x:** bản tự cập nhật cũ chỉ chép `KhoaVeyon.py` và `web`, nên máy đang ở 3.4.x sẽ thiếu `kv` và `scripts` sau khi tự cập nhật. `KhoaVeyon.py` mới tự tải bù hai thư mục này từ bản phát hành mới nhất trên GitHub (cần Internet). Nếu không tải được, chương trình báo lỗi và ghi `data\\error.log`; khi đó hãy giải nén bản đầy đủ đè lên thư mục chương trình. Bản 3.5.0 trở đi cập nhật bình thường.

## Tự cập nhật từ GitHub

Trang **Cài đặt**, mục **Cập nhật phần mềm**: điền kho GitHub dạng `chủ-sở-hữu/tên-kho` (kho công khai). Mỗi lần khởi động, chương trình hỏi mục Releases xem có tag lớn hơn phiên bản hiện tại (hằng `VERSION` trong `kv/paths.py`) không. Có thì hiện thanh thông báo, bấm **Cập nhật ngay**.

- Chỉ thay `KhoaVeyon.py`, `Chay-KhoaVeyon.bat`, `Tao-ShortCut.bat`, `README-KhoaVeyon.md`, `requirements.txt` và các thư mục `kv`, `scripts`, `web`. `data`, `lists`, `payload`, `runtime` giữ nguyên. Bản cũ được sao lưu trong `data\backup-<phiên bản>`.
- Chỉ tải qua https từ github.com, từ chối file zip có đường dẫn lạ, và kiểm tra cú pháp `KhoaVeyon.py` cùng mọi file trong `kv` mới trước khi thay (thiếu `kv` cũng bị từ chối). Lỗi thì giữ nguyên bản cũ.
- Cách phát hành bản mới: tăng `VERSION` (ví dụ `1.1.0`), đẩy lên GitHub, tạo Release có tag `v1.1.0` và đính kèm file zip tên có chữ `KhoaVeyon` (không đính kèm thì dùng zip mã nguồn tự sinh của GitHub). Cần tên file zip chứa `KhoaVeyon.py` và thư mục `kv`.
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

Chương trình hỏi GitHub (mục Releases của kho `update_repo` ở trang Cài đặt) khi mở và cứ 6 giờ một lần. Khi có bản mới hơn `VERSION` trong `kv/paths.py`, một hộp thoại hiện ra hỏi **Cập nhật ngay / Để sau / Bỏ qua bản này**. "Để sau" thì 4 giờ sau hỏi lại, "Bỏ qua" thì chỉ hỏi lại khi có bản còn mới hơn nữa. Danh sách, lớp, sơ đồ chỗ ngồi và cài đặt trong `data`, `lists`, `payload` không bị thay.

Để phát hành bản mới: đổi `VERSION` trong `kv/paths.py`, đẩy code lên GitHub, rồi tạo một **Release** có tag lớn hơn (ví dụ `v1.6.0`) và ghi chú thay đổi vào phần mô tả của Release (hộp thoại sẽ hiện phần này).

## Bản 3.7.1

Tối ưu nhỏ, không đổi hành vi: bảng Trạng thái máy dò cổng Veyon và chia sẻ C$ cùng lúc nên mỗi chu kỳ quét máy đang tắt nhanh gấp đôi (0,8 giây thay vì 1,6 giây); dọn vài biến thừa.
