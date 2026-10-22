// KhoaVeyon - Trang Tương tác: giơ tay, nhắn tin / khóa màn hình, bài nộp, thống kê dùng máy
S.interact = {hands: [], submits: [], last: 0};
S.istat = null;
S.imin = 45;

function fmtDur(sec) { sec = Math.round(sec || 0); return sec < 60 ? sec + ' giây' : sec < 3600 ? Math.round(sec / 60) + ' phút' : Math.floor(sec / 3600) + ' giờ ' + Math.round((sec % 3600) / 60) + ' phút'; }
function fmtClock(ts) { const d = new Date(ts * 1000); return d.toLocaleTimeString('vi-VN', {hour: '2-digit', minute: '2-digit'}); }
function fmtBytes(b) { return b < 1048576 ? Math.max(1, Math.round(b / 1024)) + ' KB' : (b / 1048576).toFixed(1) + ' MB'; }
function handLabel(h) { return (h.name || 'Học sinh') + (h.no ? ` (máy ${h.no})` : '') + (h.name ? '' : ' · ' + h.host); }

let interactBeep = null;
function ding() {
  try { interactBeep = interactBeep || new (window.AudioContext || window.webkitAudioContext)(); const o = interactBeep.createOscillator(), g = interactBeep.createGain(); o.frequency.value = 880; g.gain.value = 0.08; o.connect(g); g.connect(interactBeep.destination); o.start(); o.stop(interactBeep.currentTime + 0.18); } catch (e) { /* bỏ qua */ }
}

async function pollInteract() {
  try {
    const r = await api('/api/student?since=' + S.interact.last, undefined, {quiet: true});
    const first = S.interact.last === 0 && !S.interact.init;
    S.interact.init = true;
    for (const e of r.events) {
      if (first) break;
      if (e.kind === 'hand') { toast(`✋ ${e.name || 'Học sinh'} giơ tay${e.no ? ' (máy ' + e.no + ')' : ''}`, 'warn'); ding(); }
      else if (e.kind === 'submit') toast(`📤 ${e.name || 'Học sinh'} nộp bài (${e.files} tệp)`, 'ok');
    }
    const handsChanged = JSON.stringify(r.hands.map(h => h.host)) !== JSON.stringify(S.interact.hands.map(h => h.host));
    const subsChanged = JSON.stringify(r.submits.map(s => [s.id, s.status])) !== JSON.stringify(S.interact.submits.map(s => [s.id, s.status]));
    S.interact = Object.assign(r, {init: true, last: r.last});
    const n = r.hands.length;
    if (n !== S.handCount) { S.handCount = n; buildNav(); }
    if ((handsChanged || subsChanged) && ['interact', 'seats'].includes(S.page)) {
      const ae = document.activeElement;
      if (!(ae && /^(INPUT|TEXTAREA|SELECT)$/.test(ae.tagName))) render();
    }
  } catch (e) { /* bỏ qua lỗi tạm thời */ }
}
setInterval(pollInteract, 2500);

function viewInteract() {
  const I = S.interact, u = S.istat;
  const hands = I.hands.length
    ? `<table class="tbl"><tbody>${I.hands.map(h => `<tr><td>✋</td><td><b>${esc(handLabel(h))}</b>${h.cls ? ` <span class="muted">· lớp ${esc(h.cls)}</span>` : ''}</td><td class="muted">${esc(fmtClock(h.ts))}</td><td><button class="btn sm" data-ix="handdown" data-h="${esc(h.host)}">Hạ tay</button></td></tr>`).join('')}</tbody></table>
       <div class="row" style="margin-top:8px"><button class="btn ghost sm" data-ix="handdownall">Hạ tất cả</button></div>`
    : '<div class="empty">Chưa có em nào giơ tay. Học sinh bấm nút “✋ Giơ tay” ở góc màn hình máy của em.</div>';
  const subs = I.submits.length
    ? `<table class="tbl"><thead><tr><th>Giờ</th><th>Học sinh</th><th>Lớp</th><th>Tệp</th><th>Trạng thái</th></tr></thead><tbody>${I.submits.map(s => `<tr><td>${esc(fmtClock(s.ts))}</td><td><b>${esc(s.name || s.host)}</b></td><td>${esc(s.cls || '')}</td><td>${s.files} · ${esc(fmtBytes(s.bytes || 0))}</td><td>${s.status === 'ok' ? '<span class="rchip ok">Đã nhận</span>' : s.status === 'pulling' ? '<span class="rchip">Đang nhận...</span>' : `<span class="rchip" style="color:#b91c1c">Lỗi</span> <span class="muted">${esc(s.msg || '')}</span>`}${s.status === 'ok' && s.msg ? ` <span class="muted">${esc(s.msg)}</span>` : ''}</td></tr>`).join('')}</tbody></table>`
    : '<div class="empty">Chưa có bài nộp nào.</div>';
  let usage = '';
  if (u) {
    usage = `<table class="tbl"><thead><tr><th>Học sinh / máy</th><th>Tổng</th><th>Ứng dụng dùng nhiều nhất</th><th>Cửa sổ / trang</th></tr></thead><tbody>${u.rows.map(r => r.error
      ? `<tr><td><b>${esc(r.name || r.host)}</b></td><td colspan="3" class="muted">${esc(r.error)}</td></tr>`
      : `<tr><td><b>${esc(r.name || r.host)}</b>${r.name ? `<div class="muted" style="font-size:12px">${esc(r.host)}</div>` : ''}</td><td>${esc(fmtDur(r.total))}</td><td>${r.procs.map(p => `${esc(p.name)} <span class="muted">${esc(fmtDur(p.sec))}</span>`).join('<br>')}</td><td style="font-size:12.5px">${r.titles.slice(0, 3).map(p => `${esc(p.name.slice(0, 70))} <span class="muted">${esc(fmtDur(p.sec))}</span>`).join('<br>')}</td></tr>`).join('')}</tbody></table>
      <div class="row" style="margin-top:8px"><button class="btn ghost sm" data-ix="usagecsv">⬇ Xuất CSV</button></div>`;
  }
  return `<div class="stack">
    <section class="card"><h3>✋ Học sinh giơ tay <span class="badge">${I.hands.length}</span></h3>
      <label class="switch" style="margin-bottom:8px"><input type="checkbox" data-ev="handopt" ${I.hand_enabled === false ? '' : 'checked'}><span class="tr"></span><span>Cho phép học sinh giơ tay (tắt thì nút “Giơ tay” biến mất trên máy học sinh, chỉ còn “Nộp bài”)</span></label>${hands}</section>
    <section class="card"><h3>Nhắn tin và khóa màn hình</h3>
      <p class="sub">Gửi tới các máy đang chọn (không chọn = tất cả). Tin nhắn hiện giữa màn hình học sinh. “Khóa màn hình” phủ kín màn hình kèm lời nhắn cho đến khi bạn bấm “Mở màn hình”; đây là khóa mềm (học sinh có thể tắt bằng Task Manager), cần khóa chắc thì dùng thêm “Khóa toàn bộ” ở trang Điều khiển.</p>
      ${quickChips('#ixText')}
      <textarea id="ixText" rows="3" style="width:100%;box-sizing:border-box" placeholder="Nội dung, ví dụ: Còn 5 phút, các em lưu bài lại.">${esc(S.ixText || '')}</textarea>
      <div class="row" style="flex-wrap:wrap;margin-top:8px">
        <label class="muted">Tự tắt sau <select id="ixSec" class="xsel"><option value="0">khi học sinh bấm Đã hiểu</option><option value="10">10 giây</option><option value="30">30 giây</option><option value="60">1 phút</option></select></label>
        <button class="btn primary" data-ix="msg">💬 Gửi tin nhắn</button>
        <button class="btn danger" data-ix="block">🔒 Khóa màn hình kèm lời nhắn</button>
        <button class="btn ghost" data-ev="lockstyle" title="Đổi màu, ảnh nền, tiêu đề của màn hình khóa">🎨 Giao diện màn hình khóa</button>
        <button class="btn" data-ix="clear">🔓 Mở màn hình</button>
        <button class="btn" data-ix="collect">📤 Yêu cầu nộp bài</button>
      </div></section>
    ${viewEngage()}
    ${viewFun()}
    ${viewClassroom()}
    ${viewPhone()}
    <section class="card"><h3>📥 Bài nộp</h3>
      <p class="sub">Học sinh bấm nút nổi → Nộp tệp / Nộp thư mục. Bài được chép về máy giáo viên, xếp theo ngày, lớp và tên học sinh.</p>${subs}
      <div class="row" style="margin-top:8px"><button class="btn" data-act="openfolder" data-what="submissions">📂 Mở thư mục bài nộp</button></div></section>
    <section class="card"><h3>📊 Thống kê dùng máy</h3>
      <p class="sub">Đọc từ nhật ký hoạt động trên máy học sinh (cửa sổ nào đang ở trước, không ghi phím). Cần đã bật ghi nhật ký hoạt động.</p>
      <div class="row" style="flex-wrap:wrap"><label class="muted">Khoảng thời gian <select id="ixMin" class="xsel">${[[15, '15 phút qua'], [45, '45 phút qua (1 tiết)'], [90, '90 phút qua'], [0, 'Cả ngày hôm nay']].map(([v, t]) => `<option value="${v}" ${S.imin === v ? 'selected' : ''}>${t}</option>`).join('')}</select></label>
        <button class="btn" data-ix="usage">📊 Xem thống kê</button></div>${usage}</section></div>`;
}

document.addEventListener('click', async e => {
  const el = e.target.closest('[data-ix]'); if (!el) return;
  e.preventDefault();
  const a = el.dataset.ix;
  try {
    if (a === 'handdown') { S.interact = Object.assign(await api('/api/hand_clear', {host: el.dataset.h}), {init: true}); S.handCount = S.interact.hands.length; buildNav(); render(); }
    else if (a === 'handdownall') { S.interact = Object.assign(await api('/api/hand_clear', {}), {init: true}); S.handCount = 0; buildNav(); render(); }
    else if (['msg', 'block', 'clear', 'collect'].includes(a)) {
      const text = ($('#ixText') || {}).value || ''; S.ixText = text;
      if ((a === 'msg' || a === 'block') && !text.trim()) { toast('Hãy nhập nội dung', 'warn'); return; }
      const hs = await resolveTargets(); if (!hs) return;
      if (a === 'block' && !await modal({title: `Khóa màn hình ${hs.length} máy?`, ok: 'Khóa', danger: true, html: 'Màn hình học sinh bị phủ kín kèm lời nhắn. Bài chưa lưu vẫn còn nguyên. Bấm “Mở màn hình” để mở.'})) return;
      await api('/api/student_send', {kind: a, hosts: hs, text, cls: S.wcls || '', seconds: +($('#ixSec') || {value: 0}).value});
      openLog(); toast('Đã gửi tới ' + hs.length + ' máy', 'ok');
    }
    else if (a === 'usage') {
      S.imin = +$('#ixMin').value;
      const hs = S.hosts.filter(h => S.sel.has(h)); const hosts = hs.length ? hs : S.hosts;
      if (!hosts.length) { toast('Chưa có máy học sinh', 'warn'); return; }
      S.istat = await api('/api/usage', {hosts, minutes: S.imin}); render();
    }
    else if (a === 'usagecsv' && S.istat) {
      const rows = [['Máy', 'Học sinh', 'Tổng (giây)', 'Ứng dụng', 'Giây']];
      S.istat.rows.forEach(r => { if (r.error) rows.push([r.host, r.name || '', 0, r.error, '']); else r.procs.forEach(p => rows.push([r.host, r.name || '', r.total, p.name, p.sec])); });
      const csv = '﻿' + rows.map(r => r.map(c => '"' + String(c).replace(/"/g, '""') + '"').join(',')).join('\r\n');
      const url = URL.createObjectURL(new Blob([csv], {type: 'text/csv;charset=utf-8'}));
      const x = document.createElement('a'); x.href = url; x.download = 'thong-ke-dung-may.csv'; document.body.appendChild(x); x.click(); setTimeout(() => { x.remove(); URL.revokeObjectURL(url); }, 800);
    }
  } catch (err) { toast(err.message, 'err'); }
});
