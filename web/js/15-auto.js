// KhoaVeyon - Trang Tự động theo tiết
/* ---------- Tự động theo thời khóa biểu (3.4.0) ---------- */
async function loadAuto() {
  const d = await api('/api/auto');
  S.auto = d;
  const a = d.auto;
  Object.values(a.modes).forEach(m => { m.lists = Object.fromEntries(Object.entries(m.lists || {}).filter(([k, v]) => ((d.variants || {})[k] || []).includes(v))); });   // bản riêng đã bị xóa thì quay về danh sách chính
  S.autoDraft = {enabled: a.enabled, wake_min: a.wake_min, shutdown_min: a.shutdown_min, shutdown_delay: a.shutdown_delay, cleanup: (a.cleanup || []).slice(),
    modes: Object.entries(a.modes).map(([name, m]) => ({name, start: m.start.slice(), end: m.end.slice(), lists: Object.assign({}, m.lists || {}), wall: m.wall || ''})), class_mode: Object.assign({}, a.class_mode)};
  S.autoDirty = false;
  S.logonModes = (await api('/api/logon_policy', {step: 'modes'})).modes;
  if (!S.lpSel) S.lpSel = ['lockdown'];
}
function autoActLabel(k) { const a = (S.auto.actions || []).find(x => x.key === k); return a || {label: k, confirm: false}; }
function viewAuto() {
  if (!S.auto || !S.autoDraft) return '<div class="empty">Đang tải...</div>';
  const d = S.autoDraft, acts = S.auto.actions;
  const phase = (mi, ph, title) => {
    const chips = d.modes[mi][ph].map((k, ki) => { const a = autoActLabel(k); return `<span class="cmdchip ${a.confirm ? 'warn' : ''}" title="${a.confirm ? 'Lệnh này có thể làm mất bài chưa lưu của học sinh' : ''}">${ki + 1}. ${esc(a.label)}${a.confirm ? ' ⚠' : ''}<button data-xa="cmddel" data-m="${mi}" data-ph="${ph}" data-k="${ki}">×</button></span>`; }).join('') || '<span class="muted">chưa có lệnh</span>';
    return `<div class="ph"><b>${title}</b>${chips}<select class="xsel" data-xc="cmdadd" data-m="${mi}" data-ph="${ph}"><option value="">+ Thêm lệnh...</option>${acts.map(a => `<option value="${esc(a.key)}">${esc(a.label)}${a.confirm ? ' ⚠' : ''}</option>`).join('')}</select></div>`;
  };
  const lst = mi => {
    const vars = S.auto.variants || {}, cur = d.modes[mi].lists || {};
    const parts = Object.keys(S.auto.list_titles || {}).map(k => {
      const vs = vars[k] || []; if (!vs.length && !cur[k]) return '';
      return `<label class="muted">${esc(S.auto.list_titles[k])} <select class="xsel" data-xc="modelist" data-m="${mi}" data-k="${esc(k)}"><option value="">(dùng danh sách chính)</option>${vs.map(v => `<option value="${esc(v)}" ${v === cur[k] ? 'selected' : ''}>${esc(v)}</option>`).join('')}</select></label>`;
    }).join('');
    return `<div class="ph"><b>Danh sách riêng</b>${parts || '<span class="muted">chưa có bản riêng nào (tạo ở các trang danh sách bằng nút “Lưu bảng thành bản riêng”)</span>'}</div>`;
  };
  const wallSel = mi => { const ws = S.auto.walls || [], cur = d.modes[mi].wall || '';
    return `<div class="ph"><b>Hình nền máy học sinh</b><select class="xsel" data-xc="modewall" data-m="${mi}"><option value="">(không đổi hình nền)</option>${ws.map(w => `<option ${w === cur ? 'selected' : ''}>${esc(w)}</option>`).join('')}</select><span class="muted">${ws.length ? 'Vào tiết: vẽ số máy + tên em ngồi; hết tiết: trả lại hình nền cũ.' : 'Chưa có mẫu nào, tạo ở trang Tương tác → Hình nền.'}</span></div>`; };
  const modes = d.modes.map((m, i) => `<div class="modeblock"><div class="row" style="flex-wrap:wrap">
      <input type="text" data-xc="modename" data-m="${i}" value="${esc(m.name)}" style="flex:1;min-width:200px;font-weight:700">
      <button class="btn sm ghost" data-xa="modetest" data-m="${i}" data-ph="start">▶ Chạy thử vào tiết</button>
      <button class="btn sm ghost" data-xa="modetest" data-m="${i}" data-ph="end">▶ Chạy thử hết tiết</button>
      <button class="btn sm ghost" data-xa="modedel" data-m="${i}">Xóa</button></div>
      ${lst(i)}${wallSel(i)}${phase(i, 'start', 'Vào tiết')}${phase(i, 'end', 'Hết tiết')}</div>`).join('');
  const sel = cur => `<option value="">(không làm gì)</option>${d.modes.map(m => `<option value="${esc(m.name)}" ${m.name === cur ? 'selected' : ''}>${esc(m.name)}</option>`).join('')}`;
  const clsRows = ['*', ...S.auto.classes].map(c => `<tr><td><b>${c === '*' ? 'Mọi lớp khác' : 'Lớp ' + esc(c)}</b></td><td><select class="xsel" data-xc="clsmode" data-c="${esc(c)}">${sel(d.class_mode[c] || '')}</select></td></tr>`).join('');
  const today = S.auto.today.length ? S.auto.today.map(s => `<tr><td>${esc(s.start)}–${esc(s.end)}</td><td>Lớp ${esc(s.cls)}</td><td>${s.mode ? esc(s.mode) : '<span class="muted">không làm gì</span>'}</td></tr>`).join('') : '<tr><td colspan="3" class="muted">Hôm nay không có tiết nào.</td></tr>';
  return `<div class="stack">
    <section class="card"><h3>Tự động theo thời khóa biểu</h3>
      <label class="switch"><input type="checkbox" data-xc="autoon" ${d.enabled ? 'checked' : ''}><span class="tr"></span><span><b>Bật tự động</b></span></label>
      <p class="hint">Khi chuyển sang tiết của một lớp, chương trình chạy các lệnh “Vào tiết” của chế độ gán cho lớp đó. Khi hết tiết hoặc sang lớp khác, chạy các lệnh “Hết tiết” của chế độ cũ. Lệnh chạy trên các máy đang bật trong danh sách máy, <b>không hỏi lại</b>, nên lệnh có dấu ⚠ (đóng ứng dụng, khóa AI...) có thể làm học sinh mất bài chưa lưu. Chương trình phải đang mở. Tiết được tính bắt đầu sớm tối đa 5 phút.</p>
      ${S.auto.has_timetable ? '' : '<div class="note warn">Chưa nhập thời khóa biểu. Vào trang “Lớp &amp; lịch dạy” để nhập.</div>'}
    </section>
    <section class="card"><h3>Chế độ lớp</h3>${modes}<div class="row"><button class="btn" data-xa="modeadd">＋ Thêm chế độ</button></div></section>
    <section class="card"><h3>Gán chế độ cho lớp</h3><table class="tbl"><thead><tr><th>Lớp</th><th>Chế độ</th></tr></thead><tbody>${clsRows}</tbody></table>
      <p class="hint" style="margin-bottom:0">Lớp không có dòng riêng dùng dòng “Mọi lớp khác”. Lớp lấy từ thời khóa biểu và danh sách lớp.</p></section>
    <section class="card"><h3>Dọn máy sau mỗi tiết</h3>
      <p class="sub">Hết tiết thì tự chạy các lệnh dưới đây để máy sạch cho lớp sau (chạy sau các lệnh “khi hết tiết” của chế độ lớp). Không có lệnh đóng ứng dụng vì có thể làm mất bài chưa lưu của học sinh.</p>
      <div class="row" style="flex-wrap:wrap;gap:14px">${['clearhistory', 'unmute', 'unlock', 'allowall', 'allowai', 'unblockapp', 'lockall-stop', 'lockapp-stop', 'lockrun-stop', 'weboff'].filter(k => (S.auto.actions || []).some(x => x.key === k)).map(k => `<label class="switch"><input type="checkbox" data-xc="cleanup" data-k="${esc(k)}" ${(d.cleanup || []).includes(k) ? 'checked' : ''}><span class="tr"></span><span>${esc(autoActLabel(k).label)}</span></label>`).join('')}</div></section>
    <section class="card"><h3>Bật và tắt máy theo giờ</h3>
      <div class="autogrid">
        <label>Bật máy trước tiết đầu (phút, 0 = tắt)<input type="number" min="0" max="120" data-xc="num" data-f="wake_min" value="${esc(d.wake_min)}"></label>
        <label>Tắt máy sau tiết cuối (phút, 0 = tắt)<input type="number" min="0" max="240" data-xc="num" data-f="shutdown_min" value="${esc(d.shutdown_min)}"></label>
        <label>Chờ trước khi tắt (giây)<input type="number" min="10" max="600" data-xc="num" data-f="shutdown_delay" value="${esc(d.shutdown_delay)}"></label>
      </div>
      <p class="hint" style="margin-bottom:0">Mỗi ngày chỉ làm một lần, chỉ khi ngày đó có tiết. Bật máy dùng Wake-on-LAN, xem trang “Trạng thái máy”. Chỉ tắt khi không còn tiết nào đang diễn ra.</p></section>
    <section class="card"><h3>Áp khi học sinh đăng nhập (không cần mở KhoaVeyon)</h3>
      <p class="sub">Cài lên máy học sinh một tác vụ chạy mỗi lần có người đăng nhập, trong phiên của chính học sinh. Nhờ đó máy bật lên là bị hạn chế ngay, kể cả khi máy giáo viên đang tắt.</p>
      <div style="display:flex;flex-direction:column;gap:10px;margin:10px 0">${(S.logonModes || []).map(m => `<label class="switch"><input type="checkbox" data-xc="lpmode" data-id="${esc(m.id)}" ${S.lpSel.includes(m.id) ? 'checked' : ''}><span class="tr"></span><span>${esc(m.label)}</span></label>`).join('')}</div>
      <div class="row"><button class="btn" data-xa="lpinstall">Cài lên máy đang chọn</button><button class="btn ghost" data-xa="lpcheck">Kiểm tra</button><button class="btn ghost" data-xa="lpremove">Gỡ</button></div>
      <p class="hint" style="margin-bottom:0">Chặn mở app ngoài danh sách dùng danh sách KeepAppList.xlsx có sẵn trên máy học sinh. Lưu ý: nút Mở khóa giữa buổi chỉ có tác dụng đến lần đăng nhập kế tiếp, vì lúc đó chính sách này áp lại. Muốn bỏ hẳn thì bấm Gỡ.</p></section>
    <section class="card"><h3>Hôm nay</h3><table class="tbl"><tbody>${today}</tbody></table></section>
    <div class="row"><button class="btn primary" data-xa="autosave" ${S.autoDirty ? '' : 'disabled'}>Lưu cài đặt tự động</button>${S.autoDirty ? '<span class="muted">Có thay đổi chưa lưu</span>' : ''}</div>
  </div>`;
}
function autoTouch() { S.autoDirty = true; render(); }
document.addEventListener('click', async e => {
  const el = e.target.closest('[data-xa]');
  if (!el || S.page !== 'auto') return;
  const a = el.dataset.xa, d = S.autoDraft, mi = +el.dataset.m;
  try {
    if (a === 'cmddel') { d.modes[mi][el.dataset.ph].splice(+el.dataset.k, 1); autoTouch(); }
    else if (a === 'modedel') { const n = d.modes[mi].name; d.modes.splice(mi, 1); Object.keys(d.class_mode).forEach(c => { if (d.class_mode[c] === n) delete d.class_mode[c]; }); autoTouch(); }
    else if (a === 'modeadd') {
      const v = await modal({title: 'Chế độ mới', ok: 'Thêm', collect: r => r.querySelector('input').value.trim(), html: '<input type="text" class="xsel" style="width:100%" placeholder="Ví dụ: Kiểm 15 phút">'});
      if (!v) return;
      if (d.modes.some(m => m.name === v)) { toast('Đã có chế độ tên này', 'warn'); return; }
      d.modes.push({name: v, start: [], end: [], lists: {}, wall: ''}); autoTouch();
    }
    else if (a === 'modetest') {
      if (S.autoDirty) { toast('Hãy lưu cài đặt trước khi chạy thử', 'warn'); return; }
      const hs = await resolveTargets(); if (!hs) return;
      const ph = el.dataset.ph;
      const ok = await modal({title: 'Chạy thử trên ' + hs.length + ' máy?', ok: 'Chạy', html: 'Các lệnh sẽ chạy ngay trên các máy này, như khi đến giờ.'}); if (!ok) return;
      await api('/api/auto_test', {mode: d.modes[mi].name, phase: ph, hosts: hs});
      openLog(); L.pending++; updBusy(); pollSoon(); setTimeout(() => { L.pending = Math.max(0, L.pending - 1); updBusy(); }, 4000);
    }
    else if (a === 'lpinstall' || a === 'lpremove' || a === 'lpcheck') {
      const step = a.slice(2);
      if (step === 'install' && !S.lpSel.length) { toast('Chọn ít nhất một lệnh', 'warn'); return; }
      const hs = await resolveTargets(); if (!hs) return;
      if (step !== 'check') { const ok = await modal({title: (step === 'install' ? 'Cài' : 'Gỡ') + ' chính sách đăng nhập trên ' + hs.length + ' máy?', ok: step === 'install' ? 'Cài' : 'Gỡ', html: step === 'install' ? 'Từ nay mỗi lần học sinh đăng nhập, máy tự áp các hạn chế đã chọn.' : 'Máy sẽ không tự áp hạn chế khi đăng nhập nữa. Hạn chế đang bật giữ nguyên đến khi bạn mở khóa.'}); if (!ok) return; }
      await api('/api/logon_policy', {step, hosts: hs, modes: S.lpSel});
      openLog(); L.pending++; updBusy(); pollSoon(); setTimeout(() => { L.pending = Math.max(0, L.pending - 1); updBusy(); }, 4000);
    }
    else if (a === 'autosave') {
      const modes = {};
      for (const m of d.modes) { if (!m.name.trim()) throw new Error('Có chế độ chưa đặt tên'); if (modes[m.name]) throw new Error('Trùng tên chế độ: ' + m.name); modes[m.name] = {start: m.start, end: m.end, lists: m.lists || {}, wall: m.wall || ''}; }
      await api('/api/auto_set', {enabled: d.enabled, modes, class_mode: d.class_mode, wake_min: d.wake_min, shutdown_min: d.shutdown_min, shutdown_delay: d.shutdown_delay, cleanup: d.cleanup || []});
      await loadAuto(); render(); toast('Đã lưu cài đặt tự động', 'ok');
    }
  } catch (err) { toast(err.message, 'err'); }
});
document.addEventListener('change', e => {
  const t = e.target, c = t.dataset.xc;
  if (!c || S.page !== 'auto') return;
  const d = S.autoDraft, mi = +t.dataset.m;
  if (c === 'lpmode') { const id = t.dataset.id; S.lpSel = S.lpSel.filter(x => x !== id); if (t.checked) S.lpSel.push(id); return; }
  if (c === 'autoon') d.enabled = t.checked;
  else if (c === 'cleanup') { d.cleanup = (d.cleanup || []).filter(x => x !== t.dataset.k); if (t.checked) d.cleanup.push(t.dataset.k); }
  else if (c === 'num') d[t.dataset.f] = Math.max(0, parseInt(t.value || '0', 10) || 0);
  else if (c === 'cmdadd') { if (!t.value) return; d.modes[mi][t.dataset.ph].push(t.value); }
  else if (c === 'modelist') { const L2 = d.modes[mi].lists = d.modes[mi].lists || {}; t.value ? L2[t.dataset.k] = t.value : delete L2[t.dataset.k]; }
  else if (c === 'modewall') { d.modes[mi].wall = t.value; }
  else if (c === 'clsmode') { t.value ? d.class_mode[t.dataset.c] = t.value : delete d.class_mode[t.dataset.c]; }
  else if (c === 'modename') {
    const nv = t.value.trim(), old = d.modes[mi].name;
    if (!nv) { t.value = old; return; }
    if (d.modes.some((m, i) => i !== mi && m.name === nv)) { toast('Đã có chế độ tên này', 'warn'); t.value = old; return; }
    d.modes[mi].name = nv; Object.keys(d.class_mode).forEach(k => { if (d.class_mode[k] === old) d.class_mode[k] = nv; });
  }
  autoTouch();
});
