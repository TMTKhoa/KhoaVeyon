// KhoaVeyon - Vui lớp học: tặng sao, đếm ngược, chia nhóm ngẫu nhiên
S.fun = {cls: '', groups: null, board: null, boardCls: ''};

function funClasses() { return ((S.school || {}).classes || []).map(c => c.name || c); }
function funCls() { const cl = funClasses(); if (!S.fun.cls || !cl.includes(S.fun.cls)) S.fun.cls = (S.school && S.school.current && cl.includes(S.school.current.cls)) ? S.school.current.cls : (cl[0] || ''); return S.fun.cls; }

function viewFun() {
  const cl = funClasses(); if (!cl.length) return '';
  const c = funCls(), F = S.fun;
  if (F.boardCls !== c) { F.boardCls = c; F.board = null; api('/api/stars?cls=' + encodeURIComponent(c), undefined, {quiet: true}).then(r => { F.board = r.board; if (S.page === 'interact') render(); }).catch(() => {}); }
  const board = (F.board || []).length ? `<ol style="margin:6px 0 0;padding-left:22px">${F.board.slice(0, 8).map(x => `<li>${esc(x.name)} <b>${'⭐'.repeat(Math.min(x.stars, 10))}${x.stars > 10 ? ' ×' + x.stars : ''}</b></li>`).join('')}</ol>` : '<div class="muted">Chưa có em nào được sao. Ở trang Monitor, chọn máy rồi bấm “⭐ Tặng sao”.</div>';
  const groups = F.groups ? `<div class="grpbox">${F.groups.map(g => `<div class="grpcard"><b>Nhóm ${g.no} (${g.names.length})</b>${g.names.map(n => `<div>${esc(n)}</div>`).join('')}</div>`).join('')}</div>` : '';
  return `<section class="card"><h3>🎉 Vui lớp học</h3>
      <div class="row" style="flex-wrap:wrap;gap:8px;align-items:center">Lớp <select id="funCls" class="xsel" style="width:auto">${cl.map(x => `<option ${x === c ? 'selected' : ''}>${esc(x)}</option>`).join('')}</select>
        <button class="btn" data-fun="timer">⏱ Đếm ngược cả lớp</button><button class="btn ghost" data-fun="timerstop">Dừng đếm ngược</button></div>
      <h4 style="margin:14px 0 4px">👥 Chia nhóm ngẫu nhiên</h4>
      <div class="row" style="flex-wrap:wrap;gap:8px;align-items:center"><select id="grpMode" class="xsel" style="width:auto"><option value="size">Mỗi nhóm</option><option value="count">Chia thành</option></select>
        <input type="number" id="grpN" min="1" max="40" value="4" style="width:70px"> <span class="muted" id="grpUnit">em</span>
        <label class="switch"><input type="checkbox" id="grpSend" checked><span class="tr"></span><span>Hiện nhóm trên máy từng em</span></label>
        <button class="btn primary" data-fun="groups">🎲 Chia nhóm</button></div>${groups}
      <h4 style="margin:14px 0 4px">⭐ Bảng sao lớp ${esc(c)} <button class="btn sm ghost" data-fun="starreset" style="margin-left:8px">Xóa bảng</button></h4>${board}</section>`;
}

async function funTimer() {
  const v = await modal({title: '⏱ Đếm ngược cả lớp', ok: 'Bắt đầu', html: `<div style="display:grid;gap:8px"><label>Số phút <input type="number" id="tmMin" min="0.1" max="180" step="0.5" value="5" style="width:90px"></label>
      <input type="text" id="tmLab" maxlength="120" placeholder="Lời nhắn khi hết giờ, ví dụ: Dừng bút, lưu bài và nộp."></div>`,
    collect: r => ({minutes: r.querySelector('#tmMin').value, label: r.querySelector('#tmLab').value})});
  if (!v) return;
  const hs = await resolveTargets(); if (!hs) return;
  await api('/api/countdown', Object.assign({hosts: hs}, v)); openLog(); toast('Đã bật đồng hồ đếm ngược trên ' + hs.length + ' máy', 'ok');
}
async function funStar() {
  const v = await modal({title: '⭐ Tặng sao', ok: 'Tặng', html: '<input type="text" id="stTxt" maxlength="120" style="width:100%" placeholder="Lời khen (tùy chọn): Em làm rất tốt!">', collect: r => r.querySelector('#stTxt').value.trim()});
  if (v === null) return;
  const hs = await resolveTargets(); if (!hs) return;
  const r = await api('/api/star', {hosts: hs, text: v, cls: S.mon ? S.mon.cls : ''});
  S.fun.board = null; S.fun.boardCls = ''; toast(r.given.length ? '⭐ Đã tặng sao cho ' + r.given.map(x => x.name).join(', ') : 'Đã gửi lời khen (máy chưa có tên học sinh nên chưa tính sao)', 'ok');
}

document.addEventListener('change', e => {
  const t = e.target;
  if (t.id === 'funCls') { S.fun.cls = t.value; S.fun.groups = null; S.fun.boardCls = ''; render(); }
  else if (t.id === 'grpMode') { const u = $('#grpUnit'); if (u) u.textContent = t.value === 'size' ? 'em' : 'nhóm'; }
});
document.addEventListener('click', async e => {
  const el = e.target.closest('[data-fun]'); if (!el) return;
  e.preventDefault();
  const a = el.dataset.fun;
  try {
    if (a === 'timer') await funTimer();
    else if (a === 'timerstop') { const hs = await resolveTargets(); if (!hs) return; await api('/api/countdown', {hosts: hs, cancel: true}); toast('Đã dừng đồng hồ', 'ok'); }
    else if (a === 'groups') {
      const r = await api('/api/groups', {cls: funCls(), mode: $('#grpMode').value, n: +$('#grpN').value, send: $('#grpSend').checked});
      S.fun.groups = r.groups; render(); toast('Đã chia ' + r.groups.length + ' nhóm' + (r.sent ? ', gửi tới ' + r.sent + ' máy' : ''), 'ok');
    }
    else if (a === 'starreset') {
      if (!await modal({title: 'Xóa bảng sao lớp ' + funCls() + '?', ok: 'Xóa', danger: true, html: 'Số sao của cả lớp về 0.'})) return;
      await api('/api/stars_reset', {cls: funCls()}); S.fun.board = []; render();
    }
  } catch (err) { toast(err.message, 'err'); }
});
