// KhoaVeyon - Lớp, điểm danh vắng, thông báo vị trí máy
/* ---------- trang: lớp và lịch dạy ---------- */
async function loadSchool() {
  S.school = await api('/api/school');
  const cls = S.school.classes || [];
  if (cls.length && (!S.seatCls || !cls.some(c => c.name === S.seatCls))) S.seatCls = (S.school.current && cls.some(c => c.name === S.school.current.cls)) ? S.school.current.cls : cls[0].name;
  if (S.seatCls) { try { await seatNames(); } catch (e) { /* bỏ qua */ } await loadAtt(); }
}

async function loadAtt() {
  if (!S.seatCls) { S.att = null; return; }
  try { S.att = await api('/api/school_attendance?cls=' + encodeURIComponent(S.seatCls)); } catch (e) { S.att = null; }
}

async function attAct(body) {
  try {
    S.att = await api('/api/school_attendance_set', Object.assign({cls: S.seatCls}, body));
    const ch = Object.entries(S.att.changed || {});
    if (ch.length) toast('Đã chuyển chỗ: ' + ch.map(([n, m]) => `${n} → máy ${m}`).join('; '), 'ok');
    const sh = Object.entries(S.att.shares || {});
    if (sh.length) toast('Hết máy trống: ' + sh.map(([n, m]) => `${n} ngồi chung máy ${m} với ${S.att.seats[m] || '?'}`).join('; '), 'warn');
    if ((S.att.unplaced || []).length) toast('Không còn máy nào cho: ' + S.att.unplaced.join(', '), 'warn');
  } catch (err) { toast(err.message, 'err'); }
  render();
}

async function seatAnnounce(clear) {
  const sec = parseInt(($('#annSec') || {}).value) || 15, keep = !!($('#annKeep') || {}).checked;
  try { await api('/api/school_announce', {cls: S.seatCls, seconds: sec, keep, clear: !!clear}); toast(clear ? 'Đang gỡ nhãn chỗ ngồi trên các máy' : 'Đang gửi thông báo chỗ ngồi xuống các máy, xem kết quả ở Nhật ký', 'ok'); }
  catch (err) { toast(err.message, 'err'); }
}

function viewAttendance() {
  const a = S.att; if (!a || a.cls !== S.seatCls) return '';
  const names = S.stu[S.seatCls] || [], ab = new Set(a.absent || []), moves = Object.entries(a.moves || {});
  const info = [];
  if (moves.length) info.push(`<div class="note">Đã tự chuyển sang máy trống gần nhất: ${moves.map(([n, m]) => `<b>${esc(n)}</b> → máy ${m}`).join(', ')}</div>`);
  const sh = Object.entries(a.shares || {});
  if (sh.length) info.push(`<div class="note warn">Hết máy trống, ngồi chung với bạn gần nhất: ${sh.map(([n, m]) => `<b>${esc(n)}</b> → máy ${m} (cùng <b>${esc(a.seats[m] || '?')}</b>)`).join(', ')}</div>`);
  if ((a.unplaced || []).length) info.push(`<div class="note warn">Không còn máy nào cho: <b>${a.unplaced.map(esc).join(', ')}</b></div>`);
  if (a.silent) info.push(`<div class="note warn">Không máy nào trả lời (lúc ${esc(a.checked_at)}), nên chưa dồn chỗ theo máy tắt. Hãy bật máy học sinh và kiểm tra tên máy ở sơ đồ, rồi bấm <b>Kiểm tra máy và dồn chỗ</b>.</div>`);
  if ((a.offline || []).length) info.push(`<div class="muted" style="font-size:12.5px">Máy đang tắt hoặc không kết nối được (kiểm tra lúc ${esc(a.checked_at)}): ${a.offline.join(', ')}</div>`);
  return `<section class="card"><div class="toolbar" style="margin-bottom:10px"><b>Điểm danh hôm nay</b><span class="muted">${esc(a.date.split('-').reverse().join('/'))} · lớp ${esc(a.cls)} · vắng ${ab.size}/${names.length}</span><span class="grow"></span>
      <button class="btn" data-act="attpresent">Cả lớp có mặt</button><button class="btn" data-act="attrecheck" title="Kiểm tra máy nào đang bật rồi dồn chỗ lại">Kiểm tra máy và dồn chỗ</button><button class="btn" data-kq="compare" data-cls="${esc(a.cls)}" title="So điểm danh và chỗ ngồi với bài làm KhoaQuiz hôm nay">🔎 Đối chiếu KhoaQuiz</button><button class="btn" data-kq="live" data-cls="${esc(a.cls)}" title="Danh sách học sinh đã vào phòng chơi KhoaQuiz, ngồi máy nào; bắt đầu chơi thì em chưa vào bị đánh vắng">🎮 Trò chơi KhoaQuiz</button></div>
    <div class="achips">${names.map(n => `<span class="achip ${ab.has(n) ? 'ab' : ''}" data-act="attoggle" data-name="${esc(n)}" title="${ab.has(n) ? 'Đang vắng, bấm để đánh dấu có mặt' : 'Bấm để đánh dấu vắng'}">${esc(n)}</span>`).join('') || '<span class="muted">Chưa có danh sách học sinh</span>'}</div>
    <div class="stack" style="gap:8px;margin-top:10px">${info.join('')}</div>
    <div class="row" style="gap:22px;margin-top:10px;flex-wrap:wrap">
      <label class="switch"><input type="checkbox" data-attset="notify" ${a.notify ? 'checked' : ''}><span class="tr"></span><span>Tự báo cho em bị chuyển chỗ</span></label></div>
    <p class="hint" style="margin-bottom:0">Bấm tên em để đánh dấu <b>vắng</b>. Em có mặt mà máy hỏng, máy đang tắt hoặc chưa có chỗ sẽ được chuyển sang <b>máy trống gần nhất</b> (thường là máy của em vắng), tính theo hàng và dãy trên sơ đồ. Chỗ đổi chỉ áp dụng cho hôm nay, sơ đồ gốc không bị sửa. Máy được biết là tắt khi không mở được cổng Veyon, nên hãy bật máy rồi bấm <b>Kiểm tra máy và dồn chỗ</b>.</p></section>
  <section class="card"><div class="toolbar" style="margin-bottom:10px"><b>Thông báo vị trí máy</b><span class="muted">Hiện trên màn hình từng em: “Máy này của ai”</span></div>
    <div class="row" style="gap:16px;flex-wrap:wrap">
      <label class="row" style="gap:6px"><span class="muted">Hiện lớn</span><input type="number" min="3" max="300" id="annSec" value="15" style="width:70px"><span class="muted">giây</span></label>
      <label class="switch"><input type="checkbox" id="annKeep" checked><span class="tr"></span><span>Sau đó giữ nhãn nhỏ ở góc màn hình</span></label>
      <button class="btn primary" data-act="announce">📢 Thông báo cho cả lớp</button><button class="btn ghost" data-act="announceclear">Gỡ nhãn trên các máy</button></div>
    <div class="row" style="gap:22px;margin-top:10px"><label class="switch"><input type="checkbox" data-attset="auto_announce" ${a.auto_announce ? 'checked' : ''}><span class="tr"></span><span>Tự thông báo khi sang tiết mới (theo thời khóa biểu)</span></label></div>
    <p class="hint" style="margin-bottom:0">Chỉ báo cho máy có người ngồi (em vắng thì không). Cần có người đang đăng nhập trên máy học sinh. Số máy phải khớp tên máy (điền <b>Tên máy mẫu</b> ở sơ đồ, hoặc thứ tự danh sách máy ở trang Điều khiển lớp). Bảng tự đóng nếu chọn không giữ nhãn; học sinh cũng bấm vào bảng lớn để thu nhỏ.</p></section>`;
}

function updClassBadge() {
  const el = $('#classBadge'); if (!el) return;
  const b = S.schoolBrief;
  if (!b || !S.school && !b.current && !b.next[0]) { el.classList.add('hidden'); return; }
  el.classList.remove('hidden');
  if (b.current) { el.className = 'badge clsbadge'; el.textContent = '🏫 Lớp ' + b.current + (b.source === 'manual' ? ' (đặt tay)' : ''); }
  else { el.className = 'badge clsbadge off'; el.textContent = b.next[0] ? `🏫 Ngoài giờ · kế tiếp ${b.next[0]} ${b.next[1]}` : '🏫 Ngoài giờ'; }
}

async function schoolUpload(kind, file) {
  if (!file) return;
  try {
    const sid = slowStart('/api/school_upload');
    const r = await fetch(`/api/school_upload?kind=${kind}&name=${encodeURIComponent(file.name)}`, {method: 'PUT', headers: {'X-Token': TOKEN}, body: file}).finally(() => slowEnd(sid));
    const data = await r.json().catch(() => ({error: 'Phản hồi không hợp lệ'}));
    if (!r.ok || data.error) throw new Error(data.error || ('Lỗi ' + r.status));
    S.school = data; if (kind === 'classes') S.stu = {}; toast(kind === 'classes' ? 'Đã nhập danh sách lớp' : 'Đã nhập thời khóa biểu', 'ok');
  } catch (err) { toast(err.message, 'err'); }
  await refreshBrief(); try { await loadSchool(); } catch (e) { /* bỏ qua */ } render();
}

async function schoolSet(body) {
  try { S.school = await api('/api/school_set', body); } catch (err) { toast(err.message, 'err'); }
  await refreshBrief(); try { await loadSchool(); } catch (e) { /* bỏ qua */ }
  render();
}

async function refreshBrief() {
  try { const r = await api('/api/school'); S.school = r; S.schoolBrief = {current: (r.current || {}).cls || '', source: r.source, next: [(r.next || {}).cls || '', (r.next || {}).start || '']}; } catch (e) { /* bỏ qua */ }
  updClassBadge();
}
