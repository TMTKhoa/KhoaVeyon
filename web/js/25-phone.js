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
