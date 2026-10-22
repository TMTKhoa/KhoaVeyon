// KhoaVeyon - Trang Monitor: bảng theo dõi lớp theo sơ đồ chỗ ngồi, chọn máy và thao tác nhanh
S.mon = null;
S.monCls = '';
S.monTimer = 0;

async function loadMonitor() {
  try { S.mon = await api('/api/monitor?cls=' + encodeURIComponent(S.monCls || ''), undefined, {quiet: true}); } catch (e) { if (!S.mon) throw e; }
}
setInterval(async () => {
  if (S.page !== 'monitor' || document.hidden) return;
  const before = S.mon ? JSON.stringify(S.mon.machines) + JSON.stringify(S.mon.seats) + S.mon.cls + JSON.stringify(S.mon.current) : '';
  await loadMonitor();
  const ae = document.activeElement;
  if (S.page === 'monitor' && !$('#modalroot').innerHTML && !(ae && /^(INPUT|TEXTAREA|SELECT)$/.test(ae.tagName)) &&
      before !== (S.mon ? JSON.stringify(S.mon.machines) + JSON.stringify(S.mon.seats) + S.mon.cls + JSON.stringify(S.mon.current) : '')) render();
}, 4000);

function monAppName(a) {
  const n = {chrome: 'Chrome', msedge: 'Edge', firefox: 'Firefox', winword: 'Word', excel: 'Excel', powerpnt: 'PowerPoint', code: 'VS Code', notepad: 'Notepad', explorer: 'Explorer'}[a.p];
  return n || a.p;
}
function monTile(hostInfo, seat, no) {
  const m = hostInfo, sel = m && S.sel.has(m.host);
  if (!m) return `<div class="mt none"><i class="mn">${no}</i><div class="mnm muted">${seat && seat.broken ? 'Máy hỏng' : 'Chưa gán máy'}</div></div>`;
  const st = !m.online ? 'off' : m.health === 'red' ? 'bad' : m.health === 'yellow' ? 'warn' : 'on';
  const nm = seat && seat.name ? seat.name : (seat && seat.absent ? seat.absent : (m.user || ''));
  const gone = seat && !seat.name && seat.absent;
  const act = m.act ? `<div class="mact" title="${esc(m.act.w)}"><b>${esc(monAppName(m.act))}</b> ${esc(m.act.w.slice(0, 46))}</div>` : (m.online ? '<div class="mact muted">—</div>' : '');
  const v = m.viol ? `<span class="mv" title="${m.viol.n} vi phạm hôm nay, gần nhất ${esc(m.viol.last)}: ${esc(m.viol.name)}">🚨${m.viol.n}</span>` : '';
  return `<button class="mt ${st} ${sel ? 'sel' : ''} ${m.hand ? 'hand' : ''}" data-mon="tile" data-h="${esc(m.host)}" title="${esc(m.pc)}${m.viol ? ' · vi phạm gần nhất: ' + m.viol.name : ''}">
    <i class="mn">${no}</i><span class="mdot"></span>${m.hand ? '<em class="mh">✋</em>' : ''}${v}
    <div class="mpc">${esc(m.pc)}</div><div class="mnm ${gone ? 'muted' : ''}">${esc(nm || (m.online ? 'Chưa xếp' : ''))}${gone ? ' (vắng)' : ''}</div>${act}</button>`;
}

function viewMonitor() {
  const M = S.mon; if (!M) return '<div class="empty">Đang tải...</div>';
  const cur = M.current, shown = M.cls, other = cur && shown !== cur.cls;
  const banner = cur
    ? `<div class="monbar ${other ? 'other' : ''}">📚 Đang là <b>tiết ${cur.period || ''} của lớp ${esc(cur.cls)}</b> (${esc(cur.start)}–${esc(cur.end)})${M.source === 'manual' ? ' · đặt tay' : ''}${other ? ` · đang xem sơ đồ lớp <b>${esc(shown)}</b>` : ''}</div>`
    : `<div class="monbar idle">Hiện không có tiết nào${M.next ? ` · tiết kế tiếp: lớp <b>${esc(M.next.cls)}</b> lúc ${esc(M.next.start)}` : ''}</div>`;
  const all = Object.values(M.machines);
  const on = all.filter(m => m.online).length, hands = all.filter(m => m.hand).length, viol = all.filter(m => m.viol).length;
  const selN = all.filter(m => S.sel.has(m.host)).length;
  let board;
  if (M.lay) {
    const {num, dayNo, side} = seatOrient(M.lay), cols = +M.lay.cols;
    const slot = {left: '', center: '', right: ''}; slot[side(M.lay.gv)] = '<div class="tdesk">🖥 Bàn giáo viên</div>';
    const front = `<div class="frontrow ${M.lay.flipv ? 'fv' : ''}" style="width:100%"><div>${slot.left}</div><div>${slot.center}</div><div>${slot.right}</div></div>`;
    const head = num[0].map((_, c) => `<div class="dayhead">Dãy ${dayNo(c)}</div>`).join('');
    const cells = num.map(row => row.map(n => { const s = M.seats[n] || {}; return monTile(s.host ? M.machines[s.host] : null, s, n); }).join('')).join('');
    const extras = (M.extras || []).map(h => M.machines[h]).filter(Boolean);
    board = `<div class="monwrap">${M.lay.flipv ? '' : front}<div class="mgrid" style="grid-template-columns:repeat(${cols},minmax(140px,1fr))">${head}${cells}</div>${M.lay.flipv ? front : ''}</div>
      ${extras.length ? `<h4 style="margin:14px 0 6px">Máy ngoài sơ đồ</h4><div class="mgrid flat">${extras.map(m => monTile(m, null, '·')).join('')}</div>` : ''}`;
  } else {
    board = `<div class="note" style="margin-bottom:8px">${shown ? `Lớp ${esc(shown)} chưa có sơ đồ chỗ ngồi` : 'Chưa có lớp nào'}: hiện theo danh sách máy. Vào “Sơ đồ lớp học” để xếp chỗ thì Monitor tự bố trí theo phòng.</div>
      <div class="mgrid flat">${all.map((m, i) => monTile(m, null, i + 1)).join('')}</div>`;
  }
  const clsSel = M.classes.length ? `<select id="monCls" class="xsel" style="width:auto"><option value="">(lớp đang có tiết)</option>${M.classes.map(c => `<option ${c === S.monCls ? 'selected' : ''}>${esc(c)}</option>`).join('')}</select>` : '';
  return `<div class="stack">${banner}
    <section class="card"><div class="row" style="flex-wrap:wrap;gap:8px;align-items:center">
        <span class="sstat">🟢 <b>${on}</b>/${M.total} bật</span><span class="sstat">✋ <b>${hands}</b></span><span class="sstat">🚨 <b>${viol}</b> máy vi phạm hôm nay</span>
        <span style="flex:1"></span>Sơ đồ lớp ${clsSel}</div>
      <div class="row" style="flex-wrap:wrap;gap:6px;margin-top:10px;align-items:center"><b>Chọn máy:</b>
        <button class="btn sm" data-mon="selall">Tất cả</button><button class="btn sm" data-mon="selon">Máy đang bật</button><button class="btn sm" data-mon="selviol">Máy vi phạm</button><button class="btn sm" data-mon="selhand">Máy giơ tay</button><button class="btn sm ghost" data-mon="selnone">Bỏ chọn</button>
        <span class="muted">Đã chọn <b>${selN}</b> máy${selN ? '' : ' (không chọn = áp dụng tất cả, có hỏi lại)'} · bấm vào ô máy để chọn / bỏ chọn</span></div>
      <div class="row" style="flex-wrap:wrap;gap:6px;margin-top:10px;align-items:center"><b>Thao tác nhanh:</b>
        <button class="btn sm danger" data-mon="lockscr">🔒 Khóa màn hình</button><button class="btn sm" data-mon="unlockscr">🔓 Mở màn hình</button><button class="btn sm" data-mon="msg">💬 Nhắn tin</button>
        <button class="btn sm danger" data-mon="act" data-k="lockall-start">⛔ Khóa toàn bộ</button><button class="btn sm" data-mon="act" data-k="lockall-stop">✅ Mở khóa toàn bộ</button>
        <button class="btn sm" data-mon="act" data-k="blockall">🌐 Chặn internet</button><button class="btn sm" data-mon="act" data-k="allowall">🌐 Cho internet</button>
        <button class="btn sm" data-mon="act" data-k="mute">🔇 Tắt tiếng</button><button class="btn sm" data-mon="shot">📷 Chụp màn hình</button>
        <button class="btn sm" data-mon="handdown">✋ Hạ tay</button><button class="btn sm" data-mon="power" data-a="shutdown">⏻ Tắt máy</button></div></section>
    <section class="card">${board}
      <div class="row" style="margin-top:12px;gap:14px;flex-wrap:wrap"><span class="muted"><span class="mdot on"></span> bật</span><span class="muted"><span class="mdot warn"></span> cần chú ý</span><span class="muted"><span class="mdot bad"></span> có lỗi</span><span class="muted"><span class="mdot off"></span> tắt</span>
        <label class="switch" style="margin-left:auto"><input type="checkbox" data-mon="actopt" ${M.act_enabled ? 'checked' : ''}><span class="tr"></span><span>Máy học sinh báo ứng dụng / cửa sổ đang mở (chỉ gửi khi đổi, không tốn mạng)</span></label></div>
    </section></div>`;
}

function monSelect(pred) { S.sel = new Set(Object.values(S.mon.machines).filter(pred).map(m => m.host)); render(); }

document.addEventListener('change', async e => {
  const t = e.target;
  if (t.id === 'monCls') { S.monCls = t.value; await loadMonitor(); render(); }
  else if (t.dataset && t.dataset.mon === 'actopt') {
    try { await api('/api/act_option', {enabled: t.checked, hosts: S.hosts.slice()}); S.mon.act_enabled = t.checked; toast(t.checked ? 'Đã bật báo cửa sổ đang mở' : 'Đã tắt báo cửa sổ đang mở', 'ok'); } catch (err) { toast(err.message, 'err'); }
  }
});
document.addEventListener('click', async e => {
  const el = e.target.closest('[data-mon]'); if (!el || el.type === 'checkbox') return;
  e.preventDefault();
  const a = el.dataset.mon;
  try {
    if (a === 'tile') { const h = el.dataset.h; S.sel.has(h) ? S.sel.delete(h) : S.sel.add(h); render(); }
    else if (a === 'selall') monSelect(() => true);
    else if (a === 'selon') monSelect(m => m.online);
    else if (a === 'selviol') monSelect(m => m.viol);
    else if (a === 'selhand') monSelect(m => m.hand);
    else if (a === 'selnone') monSelect(() => false);
    else if (a === 'act') await runAction(el.dataset.k);
    else if (a === 'lockscr' || a === 'msg') {
      const text = await modal({title: a === 'msg' ? 'Gửi tin nhắn' : 'Khóa màn hình kèm lời nhắn', ok: a === 'msg' ? 'Gửi' : 'Khóa', danger: a !== 'msg',
        html: '<textarea id="monTxt" rows="3" style="width:100%;box-sizing:border-box" placeholder="Nội dung hiện giữa màn hình học sinh"></textarea>', collect: r => r.querySelector('#monTxt').value.trim()});
      if (!text) return;
      const hs = await resolveTargets(); if (!hs) return;
      await api('/api/student_send', {kind: a === 'msg' ? 'msg' : 'block', hosts: hs, text, cls: S.mon.cls, seconds: a === 'msg' ? 0 : 0}); openLog(); toast('Đã gửi tới ' + hs.length + ' máy', 'ok');
    }
    else if (a === 'unlockscr') { const hs = await resolveTargets(); if (!hs) return; await api('/api/student_send', {kind: 'clear', hosts: hs, text: ''}); openLog(); toast('Đã mở màn hình ' + hs.length + ' máy', 'ok'); }
    else if (a === 'shot') { const hs = await resolveTargets(); if (!hs) return; await api('/api/shot', {hosts: hs}); openLog(); }
    else if (a === 'handdown') { const hs = await resolveTargets(); if (!hs) return; for (const h of hs) await api('/api/hand_clear', {host: h}); await loadMonitor(); render(); }
    else if (a === 'power') {
      const hs = await resolveTargets(); if (!hs) return;
      if (!await modal({title: `Tắt ${hs.length} máy?`, ok: 'Tắt máy', danger: true, html: 'Máy sẽ tắt sau 30 giây. Bài chưa lưu của học sinh sẽ mất.'})) return;
      await api('/api/power', {action: 'shutdown', hosts: hs, delay: 30}); openLog();
    }
  } catch (err) { toast(err.message, 'err'); }
});
