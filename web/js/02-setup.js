// KhoaVeyon - Trang Thiết lập ban đầu
/* ---------- trang: Thiết lập ban đầu ---------- */
async function loadSetup(quiet) {
  S.setup = await api('/api/setup_status', undefined, {quiet: !!quiet});
  try { S.agent = await api('/api/agent', undefined, {quiet: true}); } catch (e) { S.agent = null; }
}

function agentCard() {
  const a = S.agent;
  if (!a) return '';
  const rows = (a.agents || []).slice().sort((x, y) => (x.name || x.ip).localeCompare(y.name || y.ip)).map(x =>
    `<tr><td>${x.online ? '🟢' : '⚪'} ${esc(x.name || '?')}</td><td>${esc(x.ip)}</td><td>${esc(x.user || '—')}</td><td>${x.online ? 'đang kết nối' : 'mất kết nối ' + x.age + ' giây'}</td></tr>`).join('');
  const on = (a.agents || []).filter(x => x.online).length;
  return `<section class="card">
    <h3>Kênh Agent: điều khiển máy học sinh không cần tài khoản quản trị</h3>
    <p class="sub">Dịch vụ KhoaVeyon trên máy học sinh (chạy bằng SYSTEM) tự gọi về máy giáo viên để nhận việc: chạy lệnh, chép và đọc file. Nhờ vậy <b>không cần</b> tài khoản Windows trùng tên, chia sẻ C$ hay Task Scheduler từ xa. Mọi gói tin đều được ký bằng khóa bí mật chung, học sinh không giả lệnh được.</p>
    <div class="note ${a.listening ? '' : 'warn'}" style="margin-bottom:10px">${a.listening ? 'Đang nhận kết nối ở' : 'KHÔNG mở được cổng'} <code>${esc(a.url)}</code>. ${on} máy đang kết nối.
      Lần đầu bấm <b>Thiết lập máy giáo viên</b> để Windows mở cổng này trên tường lửa. Nên đặt IP cố định (DHCP reservation) cho máy giáo viên, vì địa chỉ này được ghi vào cấu hình Agent của máy học sinh.</div>
    ${rows ? `<table class="tbl"><thead><tr><th>Máy</th><th>IP</th><th>Đang đăng nhập</th><th>Trạng thái</th></tr></thead><tbody>${rows}</tbody></table>` : '<p class="hint" style="margin:0">Chưa máy nào kết nối. Cài Agent bằng Setup-MayHocSinh.bat (nút bên dưới gửi qua Veyon).</p>'}
    <div class="row" style="margin-top:12px"><button class="btn ghost" data-act="renewagent">🔑 Đổi khóa Agent</button></div>
    <p class="hint">Cài Agent lên máy học sinh: chạy <code>Setup-MayHocSinh.bat</code> từ thư mục payload (đã kèm <code>KhoaVeyonAgent.cfg</code>) hoặc dùng nút “Gửi Setup-MayHocSinh.bat qua Veyon”. Khóa Agent là bí mật: không chép file <code>.cfg</code> cho học sinh; nghi lộ thì bấm Đổi khóa rồi cài lại.</p>
  </section>`;
}

function viewSetup() {
  const u = S.setup, c = S.st.cfg;
  const row = (ok, title, desc, btn) => `<div class="file" style="align-items:flex-start;gap:14px">
    <span style="font-size:20px;line-height:1.3">${ok === true ? '✅' : ok === false ? '⚠️' : '⏳'}</span>
    <div class="nm" style="font-weight:600">${title}<div class="hint" style="font-weight:400">${desc}</div></div>${btn || ''}</div>`;
  const b = (act, text, extra = '') => `<button class="btn sm" data-act="${act}" ${extra}>${text}</button>`;
  const itemsOk = u.items_have === u.items_total;
  const scriptOk = u.script_in_payload || u.script_found;
  return `<div class="steps">
    <section class="card">
      <h3>Thiết lập máy giáo viên</h3>
      <p class="sub">Tạo sẵn 4 file danh sách mẫu (không ghi đè file có sẵn), tạo file thiết lập cho máy học sinh và tự thêm ${u.items_total} mục điều khiển vào Veyon. Không động tới máy học sinh.</p>
      <div class="row"><button class="btn primary" data-act="setupall">🚀 Thiết lập máy giáo viên</button>
        <button class="btn" data-act="scan">🔎 Tìm máy học sinh trong mạng</button>
        ${u.done ? '<span class="badge" style="background:var(--ok-l);color:var(--ok)">Đã thiết lập</span>' : ''}</div>
      ${u.windows ? '' : '<div class="note warn" style="margin-top:12px">Bạn đang không chạy trên Windows nên các bước Veyon, chép file và schtasks chỉ chạy được trên máy giáo viên Windows.</div>'}
    </section>
    <section class="card">
      <h3>Trạng thái từng bước</h3>
      <div class="files">
        ${row(u.cli, 'Tìm thấy veyon-cli', u.cli ? esc(u.cli_path) : 'Chưa thấy. Cài Veyon (Master) trên máy này hoặc đặt đường dẫn ở trang Cài đặt.', u.cli ? '' : b('gosettings', 'Mở Cài đặt'))}
        ${row(itemsOk, `Mục điều khiển trong Veyon (${u.items_have}/${u.items_total})`, itemsOk ? 'Đã đủ. Các nút ở trang Điều khiển lớp dùng được.' : (u.items_err ? 'Chưa đọc được: ' + esc(u.items_err) : 'Chưa đủ. Bấm tạo tự động, Windows sẽ hỏi quyền quản trị' + (u.admin ? '' : ' (hộp thoại UAC)') + '.'), b('setupveyon', itemsOk ? 'Cập nhật lại' : 'Tạo mục trong Veyon'))}
        ${row((u.auth_names || []).length ? true : null, 'Khóa xác thực Veyon', (u.auth_names || []).length ? 'Đang dùng cặp khóa có sẵn: <b>' + esc(u.auth_names.join(', ')) + '</b>. Bấm để chép khóa public xuống các máy học sinh (máy đã có đúng khóa thì bỏ qua).' : 'Chưa thấy cặp khóa nào. Bấm để tự tạo cặp khóa rồi chép khóa public xuống các máy học sinh.', b('setupkeys', 'Chép khóa xuống máy học sinh'))}
        ${row(u.lists_ok === u.lists_total, `Danh sách Excel (${u.lists_ok}/${u.lists_total} file)`, 'Tạo file mẫu (Chrome, ONLYOFFICE, Paint cho ứng dụng được phép; vài trang học tập; game phổ biến để chặn; các trang AI phổ biến để chặn). Không ghi đè file đã có.', u.lists_ok === u.lists_total ? '' : b('setuplists', 'Tạo file mẫu'))}
        ${row(scriptOk, esc(u.script_name) + ' để gửi cho máy học sinh', scriptOk ? (u.script_in_payload ? 'Đã có trong thư mục payload.' : 'Tìm thấy trên máy này, sẽ tự chép vào payload.') : 'Chưa tìm thấy. Thêm file này vào thư mục payload (trang Phân phối &amp; chạy, nút Thêm file).', b('setuppayload', 'Chuẩn bị file'))}
        ${row(u.student_bat, 'Setup-MayHocSinh.bat cho máy học sinh', 'Bộ cài một lần cho mỗi máy: <b>bấm đúp</b> là tự xin quyền quản trị, rồi làm hết: tạo C:\\cmd, mở tường lửa, cài Veyon (nếu có <code>veyon-*-setup.exe</code> trong cùng thư mục), nhập khóa xác thực (<code>*_public.pem</code>), bật Veyon Service, cài Agent (khóa bí mật nằm trong <code>KhoaVeyonAgent.cfg</code>) và dịch vụ KhoaVeyon. Chép cả thư mục payload bằng USB hoặc thư mục chia sẻ. Sau bước này mọi thứ còn lại làm từ máy giáo viên bằng một nút.', b('openpayload', 'Mở thư mục payload'))}
        ${row(u.hosts > 0, `Danh sách máy học sinh (${u.hosts} máy)`, u.hosts ? 'Có thể thêm bớt ở trang Điều khiển lớp.' : 'Bấm "Tìm máy học sinh trong mạng" (tìm máy đang mở cổng Veyon) hoặc nhập thủ công.', '')}
      </div>
      <div class="row" style="margin-top:14px"><button class="btn ghost" data-act="refreshsetup">↻ Làm mới trạng thái</button></div>
    </section>
    ${agentCard()}
    <section class="card">
      <h3>Thiết lập máy học sinh</h3>
      <p class="sub">Áp dụng cho <b>${targets().all ? 'tất cả ' + targets().hosts.length : targets().hosts.length}</b> máy ${targets().all ? '(chưa tick máy nào ở Điều khiển lớp)' : 'đã tick'}. Máy nào đã thiết lập đủ thì được bỏ qua, nên bấm lại nhiều lần không sao.</p>
      <div class="row"><button class="btn primary" data-act="pushsetup">▶ Thiết lập máy học sinh</button>
        <button class="btn" data-act="diagnose">🩺 Chỉ kiểm tra</button></div>
      <div class="row" style="margin-top:12px"><button class="btn" data-act="veyonkit">📨 Gửi Setup-MayHocSinh.bat qua Veyon</button></div>
      <p class="hint">Dành cho máy mới chưa mở chia sẻ: dùng Veyon mở Setup-MayHocSinh.bat trên máy học sinh, không cần USB. Mỗi máy hiện hộp thoại UAC, cần người <b>bấm Yes</b> (tài khoản thường thì nhập mật khẩu quản trị), máy phải đang có người đăng nhập Windows. Máy nào xong thì chương trình tự thiết lập tiếp.</p>
      <div class="row" style="margin-top:12px"><button class="btn" data-act="lockcmd">🔒 Khóa thư mục C:\\cmd</button><button class="btn ghost" data-act="unlockcmd">🔓 Mở khóa</button></div>
      <label class="switch" style="margin-top:12px"><input type="checkbox" data-cfg="auto_lock" ${S.st.cfg.auto_lock ? 'checked' : ''}><span class="tr"></span><span>Tự khóa C:\\cmd sau khi thiết lập máy học sinh</span></label>
      <p class="hint">Khóa: học sinh chỉ đọc và chạy được trong <code>C:\\cmd</code>, giáo viên vẫn chép và sửa file bằng quyền quản trị, thư mục <code>log</code> vẫn cho ghi để nhật ký hoạt động chạy tiếp. Mở khóa trả quyền về mặc định.</p>
      <p class="hint">Mỗi máy được kiểm tra Veyon Service, Agent (hoặc chia sẻ C$ và Task Scheduler từ xa), script và dịch vụ. Máy thiếu thì tự chép file vào <code>C:\\cmd</code> và chạy <code>-install</code>. Máy chưa kết nối Agent và chưa mở được chia sẻ (máy mới chưa từng cấu hình) cần chạy <code>Setup-MayHocSinh.bat</code> một lần bằng quyền quản trị, kết quả từng máy xem ở Nhật ký.</p>
    </section>
  </div>`;
}

async function refreshSetup() { try { await loadSetup(true); if (S.page === 'setup') render(); } catch (e) { toast(e.message, 'err'); } }

async function setupStep(step, needHosts) {
  let hosts = [];
  if (needHosts) { hosts = await resolveTargets(); if (!hosts) return; }
  else hosts = targets().hosts;
  try {
    await api('/api/setup_run', {step, hosts});
    openLog();
    if (step === 'all') toast('Đang thiết lập máy giáo viên. Nếu Windows hỏi quyền quản trị, bấm Yes.', 'ok');
    setTimeout(refreshSetup, step === 'all' || step === 'veyon' ? 6000 : 700);
    if (step === 'all' || step === 'veyon') setTimeout(refreshSetup, 20000);
  } catch (e) { toast(e.message, 'err'); }
}

async function scanHosts() {
  toast('Đang quét mạng, mất vài giây...', '');
  try {
    const r = await api('/api/setup_scan', {});
    S.hosts = r.hosts.slice(); r.found.forEach(h => S.sel.add(h));
    if (r.auto) S.st.cfg.host_auto_names = r.auto;
    S.st.cfg.hosts = S.hosts.slice();
    toast(r.found.length ? `Thấy ${r.found.length} máy chạy Veyon, thêm mới ${r.added}` : 'Không thấy máy nào mở cổng Veyon (11100). Kiểm tra Veyon Service và tường lửa trên máy học sinh.', r.found.length ? 'ok' : 'warn');
    await refreshSetup();
  } catch (e) { toast(e.message, 'err'); }
}
