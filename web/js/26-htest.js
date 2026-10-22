// Kiểm tra tính năng lớp học (trợ lý PowerShell) trên đúng một máy học sinh.
async function runHelperTest() {
  const sel = S.hosts.filter(h => S.sel.has(h));
  let host;
  if (sel.length === 1) host = sel[0];
  else if (sel.length === 0 && S.hosts.length === 1) host = S.hosts[0];
  else { toast('Hãy chọn đúng MỘT máy để kiểm tra (tick một máy ở bảng dưới)', 'warn'); return; }
  const opt = await modal({title: '🧪 Kiểm tra tính năng lớp học trên ' + hn(host), ok: 'Bắt đầu kiểm tra',
    html: `<p>Lần lượt thử: kênh tệp, trợ lý, thông báo, câu đố, đồng hồ, khóa màn hình, hình nền, chụp màn hình, chiếu bài, nhận tài liệu, ảnh thu nhỏ. Mỗi bước hiện ra trên máy đó rồi tự đóng / tự gỡ (khoảng 1–2 phút). <b>Hãy nhìn màn hình máy thử</b> để thấy từng hộp hiện lên.</p>
      <label class="switch"><input type="checkbox" id="htUrl"><span class="tr"></span><span>Thử cả bước mở trang web (sẽ mở trình duyệt trên máy đó)</span></label>`,
    collect: r => ({url: r.querySelector('#htUrl').checked})});
  if (!opt) return;
  try { await api('/api/ht_start', {hosts: [host], url: opt.url}); } catch (e) { toast(e.message, 'err'); return; }
  openLog();
  modal({title: '🧪 Kết quả trên ' + hn(host), ok: 'Đóng', noCancel: true, html: '<div id="htResult"><p class="muted">Đang chạy...</p></div>'});
  const t0 = Date.now();
  const tick = async () => {
    const box = document.querySelector('#htResult');
    if (!box) return;
    try { const r = await api('/api/ht_state', undefined, {quiet: true}); if (r.result) box.innerHTML = renderHelperTest(r.result); if (r.result && r.result.done) return; } catch (e) { /* tạm thời */ }
    if (Date.now() - t0 < 600000) setTimeout(tick, 1500);
  };
  tick();
}
function renderHelperTest(d) {
  const ic = {ok: '✔', bad: '✘', run: '⏳', wait: '·', skip: '–'}, cl = {ok: '#15803d', bad: '#b91c1c', run: '#b45309', wait: '#94a3b8', skip: '#64748b'};
  const rows = d.steps.map(s => `<tr><td style="color:${cl[s.status]};font-weight:800;font-size:16px">${ic[s.status] || '?'}</td><td><b>${esc(s.name)}</b></td><td class="muted">${esc(s.detail || '')}</td></tr>`).join('');
  const head = d.done ? `<p>Kết quả: đạt <b>${d.ok}/${d.total}</b> bước. ✔ đạt · ✘ lỗi · – bỏ qua.</p>` : '<p class="muted">Đang chạy, xem màn hình máy thử...</p>';
  return head + `<table class="tbl"><tbody>${rows}</tbody></table>${d.done ? '<p class="hint">Bước ✘: chép dòng tương ứng trong Nhật ký (hoặc chụp bảng này) gửi lại để chỉnh. Tệp student.log của trợ lý nằm ở C:\\ProgramData\\KhoaVeyon trên máy học sinh.</p>' : ''}`;
}
