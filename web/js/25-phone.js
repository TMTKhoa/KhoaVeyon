// Điều khiển bằng điện thoại (quét QR). Trạng thái lấy từ /api/phone_state.
S.phone = S.phone || {st: null, hours: 4, timer: null};

function viewPhone() {
  const P = S.phone.st;
  if (!P) { phoneRefresh(); return `<section class="card"><h3>📱 Điều khiển bằng điện thoại</h3><p class="sub">Đang tải...</p></section>`; }
  const body = P.on ? `<div style="display:flex;gap:16px;flex-wrap:wrap;align-items:center"><div style="width:190px;background:#fff;padding:6px;border-radius:10px">${P.qr}</div>
      <div style="flex:1;min-width:220px"><div>Dùng điện thoại <b>cùng mạng Wi-Fi/LAN</b> với máy giáo viên, mở camera và quét mã.</div>
      <div class="muted" style="word-break:break-all;margin:6px 0">${esc(P.url.replace(/\?k=.*/, '?k=••••'))}</div>
      <div class="muted">Còn ${Math.floor(P.left / 3600)} giờ ${Math.floor(P.left % 3600 / 60)} phút · ${P.devices.length ? 'đang có ' + P.devices.length + ' thiết bị: ' + esc(P.devices.map(d => d.ip).join(', ')) : 'chưa có điện thoại nào kết nối'}</div>
      <div class="row" style="margin-top:8px"><button class="btn" data-ph="start">🔄 Đổi mã (thu hồi mã cũ)</button><button class="btn danger" data-ph="stop">⏹ Tắt</button></div></div></div>`
    : `<p class="sub">Tắt. Bật để quét mã QR bằng điện thoại: bốc thăm, tin nhắn nhanh, khóa/mở màn hình, đếm ngược, hạ tay/tặng sao ngay từ bục giảng.</p>
      <div class="row" style="flex-wrap:wrap"><label class="muted">Hiệu lực <select id="phHours" class="xsel"><option value="1">1 giờ</option><option value="4" selected>4 giờ</option><option value="8">8 giờ</option><option value="12">12 giờ</option></select></label><button class="btn primary" data-ph="start">📱 Bật và hiện mã QR</button></div>`;
  return `<section class="card"><h3>📱 Điều khiển bằng điện thoại</h3>${body}
    <p class="sub">An toàn: mặc định tắt; mã phiên ngẫu nhiên và tự hết hạn; chỉ nhận các lệnh cơ bản (không mở được cài đặt hay xóa dữ liệu); các máy học sinh bị chặn. Lần đầu bật, Windows có thể hỏi cho phép tường lửa: chọn mạng riêng (Private).</p></section>`;
}
async function phoneRefresh() {
  try { S.phone.st = await api('/api/phone_state', undefined, {quiet: true}); } catch (e) { S.phone.st = {on: false, qr: '', url: '', left: 0, devices: []}; }
  if (S.page === 'interact') render();
  if (S.phone.st.on && !S.phone.timer) S.phone.timer = setInterval(() => { if (S.page !== 'interact' || !(S.phone.st && S.phone.st.on)) return; if (!document.activeElement.matches('input,textarea,select')) phoneRefresh(); }, 8000);
}
document.addEventListener('click', async e => {
  const el = e.target.closest('[data-ph]'); if (!el) return;
  e.preventDefault();
  try {
    if (el.dataset.ph === 'start') { const h = $('#phHours'); S.phone.st = await api('/api/phone_start', {hours: h ? +h.value : 4}); render(); phoneRefresh(); toast('Đã bật. Quét mã QR bằng điện thoại.', 'ok'); }
    else if (el.dataset.ph === 'stop') { S.phone.st = await api('/api/phone_stop', {}); render(); toast('Đã tắt điều khiển bằng điện thoại', 'ok'); }
  } catch (err) { toast(err.message, 'err'); }
});

// ---- quản trị từ laptop riêng (đăng nhập bằng PIN 6 số)
S.radmin = S.radmin || {st: null, timer: null};
function viewRadmin() {
  const R = S.radmin.st;
  if (!R) { radminRefresh(); return `<section class="card"><h3>💻 Quản trị từ laptop riêng</h3><p class="sub">Đang tải...</p></section>`; }
  const body = R.on ? `<div style="display:flex;gap:24px;flex-wrap:wrap;align-items:center"><div style="text-align:center"><div class="muted">PIN quản trị</div><div style="font:800 40px ui-monospace,monospace;letter-spacing:.2em">${esc(R.pin)}</div></div>
      <div style="text-align:center"><div class="muted">PIN chỉ xem sơ đồ</div><div style="font:800 40px ui-monospace,monospace;letter-spacing:.2em">${esc(R.vpin)}</div></div>
      <div style="flex:1;min-width:240px"><div>Trên laptop (cùng mạng) mở: <b style="word-break:break-all">${esc(R.url)}</b> rồi nhập PIN. <b>PIN chỉ xem</b> dùng cho các máy khác (kể cả máy trong phòng) để chiếu sơ đồ lớp: cùng giao diện Monitor nhưng không có nút điều khiển.</div>
      <div class="muted" style="margin:6px 0">Chế độ: <b>${R.full ? 'Toàn quyền' : 'Quản trị lớp'}</b> · còn ${Math.floor(R.left / 3600)} giờ ${Math.floor(R.left % 3600 / 60)} phút · ${R.sessions.length ? 'đang đăng nhập: ' + esc(R.sessions.map(s => s.ip + (s.role === 'view' ? ' (xem)' : '')).join(', ')) : 'chưa có laptop nào đăng nhập'}</div>
      <div class="row" style="flex-wrap:wrap;gap:8px"><button class="btn" data-ra="newpin">🔄 Đổi PIN (đăng xuất mọi laptop)</button><button class="btn danger" data-ra="stop">⏹ Tắt</button></div></div></div>`
    : `<p class="sub">Tắt. Bật để vào giao diện quản trị đầy đủ này từ laptop riêng của bạn, đăng nhập bằng PIN 6 số ngẫu nhiên (mỗi lần bật là một PIN mới).</p>
      <div class="row" style="flex-wrap:wrap;gap:12px"><label class="muted">Hiệu lực <select id="raHours" class="xsel"><option value="1">1 giờ</option><option value="4">4 giờ</option><option value="8" selected>8 giờ</option><option value="12">12 giờ</option></select></label>
      <label class="switch"><input type="checkbox" id="raFull"><span class="tr"></span><span>Toàn quyền (kể cả chạy lệnh, phân phối, cài đặt)</span></label>
      <button class="btn primary" data-ra="start">💻 Bật và tạo PIN</button></div>`;
  return `<section class="card"><h3>💻 Quản trị từ laptop riêng</h3>${body}
    <p class="sub">Chế độ "Quản trị lớp" (mặc định) dùng được: giám sát, tương tác, sơ đồ, điểm danh, báo cáo, thông báo, khóa màn hình... Không cho chạy lệnh/cài đặt lên máy học sinh, khôi phục, cập nhật, đổi cài đặt hệ thống. Xem PIN, thoát chương trình, mở thư mục trên máy này luôn bị chặn từ xa. Sai PIN 5 lần thì khóa thiết bị 15 phút; sai dồn dập từ nhiều nơi sẽ tự tắt. Kết nối HTTP trong LAN (không mã hóa): chỉ bật khi cần.</p></section>`;
}
async function radminRefresh() {
  try { S.radmin.st = await api('/api/radmin_state', undefined, {quiet: true}); } catch (e) { S.radmin.st = {on: false, pin: '', url: '', left: 0, full: false, sessions: []}; }
  if (S.page === 'interact') render();
  if (S.radmin.st.on && !S.radmin.timer) S.radmin.timer = setInterval(() => { if (S.page !== 'interact' || !(S.radmin.st && S.radmin.st.on)) return; if (!document.activeElement.matches('input,textarea,select')) radminRefresh(); }, 8000);
}
document.addEventListener('click', async e => {
  const el = e.target.closest('[data-ra]'); if (!el) return;
  e.preventDefault();
  try {
    const a = el.dataset.ra;
    if (a === 'start') { const full = $('#raFull').checked; if (full && !await modal({title: 'Bật toàn quyền?', ok: 'Bật toàn quyền', danger: true, html: 'Laptop đăng nhập được sẽ chạy lệnh, phân phối tệp, đổi cài đặt trên các máy học sinh. Chỉ bật nếu laptop này là của riêng bạn.'})) return;
      S.radmin.st = await api('/api/radmin_start', {hours: +$('#raHours').value, full}); render(); toast('Đã bật. PIN hiện ở khung này.', 'ok'); radminRefresh(); }
    else if (a === 'newpin') { S.radmin.st = await api('/api/radmin_newpin', {}); render(); toast('Đã đổi PIN', 'ok'); }
    else if (a === 'stop') { S.radmin.st = await api('/api/radmin_stop', {}); render(); toast('Đã tắt quản trị từ xa', 'ok'); }
  } catch (err) { toast(err.message, 'err'); }
});
