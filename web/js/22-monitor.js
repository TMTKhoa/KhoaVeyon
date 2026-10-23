// KhoaVeyon - Trang Monitor: bảng theo dõi lớp theo sơ đồ chỗ ngồi, chọn máy và thao tác nhanh
S.mon = null;
S.monCls = '';
S.monTimer = 0;
S.monLive = false; S.monSec = 5; S.thumbs = {}; S.thumbSeq = 0;

/* Nhớ lựa chọn “Xem màn hình học sinh” và số giây cập nhật: rời trang Monitor thì tạm dừng xem (máy học sinh ngừng chụp),
   quay lại Monitor (hoặc mở lại chương trình) thì tự xem tiếp theo lựa chọn đã lưu. */
const MON_LIVE_KEY = 'kv_mon_live', MON_SECS = [3, 5, 10, 20];
function monPrefLoad() {
  try { const v = JSON.parse(localStorage.getItem(MON_LIVE_KEY) || '{}'); return {on: v.on === true, sec: MON_SECS.includes(+v.sec) ? +v.sec : 5}; }
  catch (e) { return {on: false, sec: 5}; }
}
function monPrefSave() { try { localStorage.setItem(MON_LIVE_KEY, JSON.stringify({on: !!S.monLiveWant, sec: S.monSec})); } catch (e) { /* bỏ qua */ } }
{ const p = monPrefLoad(); S.monLiveWant = p.on; S.monSec = p.sec; }
async function monLiveResume() {
  if (!S.monLiveWant || S.monLive || window.KV_VIEW || !S.mon || S.page !== 'monitor') return;
  S.monLive = true; S.thumbs = {}; S.thumbSeq = 0;   // bỏ ảnh cũ từ lần xem trước
  await monLiveSend(true);
}

function monLiveHosts() {
  const M = S.mon; if (!M) return [];
  const sel = Object.values(M.machines).filter(m => m.online && S.sel.has(m.host)).map(m => m.host);
  return sel.length ? sel : Object.values(M.machines).filter(m => m.online).map(m => m.host);
}
async function monLiveSend(on) { try { await api('/api/monitor_live', {on, sec: S.monSec, hosts: on ? monLiveHosts() : (S.mon ? Object.keys(S.mon.machines) : [])}, {quiet: true}); } catch (e) { /* thử lại ở lần gia hạn sau */ } }
setInterval(() => { if (S.monLive && S.page === 'monitor') monLiveSend(true); }, 40000);   // gia hạn: ngừng gia hạn thì máy học sinh tự dừng
setInterval(async () => {
  if (!S.monLive) return;
  if (S.page !== 'monitor' || document.hidden) { if (S.page !== 'monitor') { S.monLive = false; monLiveSend(false); } return; }
  try {
    const r = await api('/api/monitor_thumbs?since=' + S.thumbSeq, undefined, {quiet: true});
    S.thumbSeq = r.last; let needRender = false;
    for (const [h, v] of Object.entries(r.items)) {
      S.thumbs[h] = v.d;
      const im = document.querySelector('.mthumb[data-h="' + CSS.escape(h) + '"]');
      if (im) im.src = v.d; else needRender = true;
    }
    if (needRender && !$('#modalroot').innerHTML) render();
  } catch (e) { /* bỏ qua */ }
}, 2500);

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
  const nm = seat && seat.name ? (seat.stt ? 'HS ' + seat.stt + ' · ' : '') + seat.name : (seat && seat.absent ? seat.absent : (m.user || ''));
  const gone = seat && !seat.name && seat.absent;
  const th = S.monLive && S.thumbs[m.host] ? `<img class="mthumb" data-h="${esc(m.host)}" src="${S.thumbs[m.host]}" alt="">` : (S.monLive && m.online ? `<div class="mthumb ph" data-h="${esc(m.host)}">đang chờ ảnh...</div>` : '');
  const act = m.act ? `<div class="mact" title="${esc(m.act.w)}"><b>${esc(monAppName(m.act))}</b> ${esc(m.act.w.slice(0, 46))}</div>` : (m.online ? '<div class="mact muted">—</div>' : '');
  const v = m.viol ? `<span class="mv" title="${m.viol.n} vi phạm hôm nay, gần nhất ${esc(m.viol.last)}: ${esc(m.viol.name)}">🚨${m.viol.n}</span>` : '';
  return `<button class="mt ${st} ${sel ? 'sel' : ''} ${m.hand ? 'hand' : ''} ${S.monLive ? 'live' : ''}" data-mon="tile" data-h="${esc(m.host)}" title="${esc(m.pc)}${m.viol ? ' · vi phạm gần nhất: ' + m.viol.name : ''}">
    <i class="mn">${no}</i><span class="mdot"></span>${m.hand ? '<em class="mh">✋</em>' : ''}${v}
    ${m.react ? `<span class="mr" title="${m.react === 'ok' ? 'Em hiểu rồi' : 'Em chưa hiểu'}">${m.react === 'ok' ? '😊' : '😕'}</span>` : ''}${th}<div class="mpc">${esc(m.pc)}</div><div class="mnm ${gone ? 'muted' : ''}">${esc(nm || (m.online ? 'Chưa xếp' : ''))}${gone ? ' (vắng)' : ''}</div>${act}</button>`;
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
    board = `<div class="monwrap">${M.lay.flipv ? '' : front}<div class="mgrid" style="grid-template-columns:repeat(${cols},minmax(var(--mtw,140px),1fr))">${head}${cells}</div>${M.lay.flipv ? front : ''}</div>
      ${extras.length ? `<h4 style="margin:14px 0 6px">Máy ngoài sơ đồ</h4><div class="mgrid flat">${extras.map(m => monTile(m, null, '·')).join('')}</div>` : ''}`;
  } else {
    board = `<div class="note" style="margin-bottom:8px">${shown ? `Lớp ${esc(shown)} chưa có sơ đồ chỗ ngồi` : 'Chưa có lớp nào'}: hiện theo danh sách máy. Vào “Sơ đồ lớp học” để xếp chỗ thì Monitor tự bố trí theo phòng.</div>
      <div class="mgrid flat">${all.map((m, i) => monTile(m, null, i + 1)).join('')}</div>`;
  }
  const clsSel = M.classes.length ? `<select id="monCls" class="xsel" style="width:auto"><option value="">(lớp đang có tiết)</option>${M.classes.map(c => `<option ${c === S.monCls ? 'selected' : ''}>${esc(c)}</option>`).join('')}</select>` : '';
  if (window.KV_VIEW) return `<div class="stack">${banner}<section class="card"><div class="row" style="flex-wrap:wrap;gap:8px;align-items:center"><span class="sstat">🟢 <b>${on}</b>/${M.total} bật</span><span class="sstat">✋ <b>${hands}</b></span><span style="flex:1"></span>Sơ đồ lớp ${clsSel}</div></section>
    <section class="card">${board}</section></div>`;
  return `<div class="stack">${banner}
    <section class="card"><div class="row" style="flex-wrap:wrap;gap:8px;align-items:center">
        <span class="sstat">🟢 <b>${on}</b>/${M.total} bật</span><span class="sstat">✋ <b>${hands}</b></span><span class="sstat">🚨 <b>${viol}</b> máy vi phạm hôm nay</span><span class="sstat" title="Học sinh bấm “Em hiểu rồi / chưa hiểu” trên nút nổi">😊 <b>${all.filter(m => m.react === 'ok').length}</b> · 😕 <b>${all.filter(m => m.react === 'lost').length}</b></span>
        <span style="flex:1"></span>Sơ đồ lớp ${clsSel}</div>
      <div class="row" style="flex-wrap:wrap;gap:6px;margin-top:10px;align-items:center"><b>Chọn máy:</b>
        <button class="btn sm" data-mon="selall">Tất cả</button><button class="btn sm" data-mon="selon">Máy đang bật</button><button class="btn sm" data-mon="selviol">Máy vi phạm</button><button class="btn sm" data-mon="selhand">Máy giơ tay</button><button class="btn sm ghost" data-mon="selnone">Bỏ chọn</button><button class="btn sm ghost" data-mon="seatauto" title="HS 1 ngồi Máy 1 (PC1), HS 2 ngồi Máy 2...">🪑 Xếp HS k → Máy k</button><button class="btn sm ghost" data-mon="hostmap" title="Tên PC không trùng số vị trí? Gán lại cho đúng">🔗 Gán máy vào vị trí</button>
        <span class="muted">Đã chọn <b>${selN}</b> máy${selN ? '' : ' (không chọn = áp dụng tất cả, có hỏi lại)'} · bấm vào ô máy để chọn / bỏ chọn</span></div>
      <div class="row" style="flex-wrap:wrap;gap:6px;margin-top:10px;align-items:center"><b>Thao tác nhanh:</b>
        <button class="btn sm danger" data-mon="lockscr">🔒 Khóa màn hình</button><button class="btn sm" data-mon="unlockscr">🔓 Mở màn hình</button><button class="btn sm" data-mon="msg">💬 Nhắn tin</button>
        <button class="btn sm danger" data-mon="act" data-k="lockall-start">⛔ Khóa toàn bộ</button><button class="btn sm" data-mon="act" data-k="lockall-stop">✅ Mở khóa toàn bộ</button>
        <button class="btn sm" data-mon="act" data-k="blockall">🌐 Chặn internet</button><button class="btn sm" data-mon="act" data-k="allowall">🌐 Cho internet</button>
        <button class="btn sm" data-mon="act" data-k="mute">🔇 Tắt tiếng</button><button class="btn sm" data-mon="shot">📷 Chụp màn hình</button>
        <button class="btn sm" data-mon="star">⭐ Tặng sao</button><button class="btn sm" data-mon="guide" title="Gửi ảnh động hướng dẫn thao tác (Ctrl + lăn chuột...)">📘 Gửi hướng dẫn</button><button class="btn sm" data-mon="share" title="Chọn đúng 1 máy: chụp màn hình em đó, xem trước rồi chiếu cho cả lớp">📽 Chiếu bài em này</button><button class="btn sm ghost" data-mon="shareoff">⏹ Tắt chiếu bài</button><button class="btn sm" data-mon="timer">⏱ Đếm ngược</button><button class="btn sm" data-mon="reactclr">🔄 Làm mới 😊😕</button><button class="btn sm" data-mon="handdown">✋ Hạ tay</button><button class="btn sm" data-mon="power" data-a="shutdown">⏻ Tắt máy</button></div></section>
    <section class="card">${board}
      <div class="row" style="margin-top:12px;gap:14px;flex-wrap:wrap"><span class="muted"><span class="mdot on"></span> bật</span><span class="muted"><span class="mdot warn"></span> cần chú ý</span><span class="muted"><span class="mdot bad"></span> có lỗi</span><span class="muted"><span class="mdot off"></span> tắt</span>
        <label class="switch"><input type="checkbox" data-mon="live" ${S.monLive ? 'checked' : ''}><span class="tr"></span><span>📺 Xem màn hình học sinh</span></label>
        <select id="monSec" class="xsel" style="width:auto" title="Cứ bao nhiêu giây cập nhật một ảnh">${MON_SECS.map(n => `<option value="${n}" ${S.monSec === n ? 'selected' : ''}>cập nhật ${n} giây</option>`).join('')}</select>
        <label class="switch" style="margin-left:auto"><input type="checkbox" data-mon="actopt" ${M.act_enabled ? 'checked' : ''}><span class="tr"></span><span>Máy học sinh báo ứng dụng / cửa sổ đang mở (chỉ gửi khi đổi, không tốn mạng)</span></label></div>
    </section></div>`;
}

function monSelect(pred) { S.sel = new Set(Object.values(S.mon.machines).filter(pred).map(m => m.host)); render(); }

document.addEventListener('change', async e => {
  const t = e.target;
  if (t.dataset && t.dataset.mon === 'live') {
    S.monLive = t.checked; S.monLiveWant = t.checked; monPrefSave();
    if (t.checked) { S.thumbs = {}; S.thumbSeq = 0; await monLiveSend(true); toast('Đang xem màn hình: học sinh thấy chấm ● trên nút nổi. Ảnh thu nhỏ, máy học sinh tự chụp và nén.', 'ok'); }
    else { await monLiveSend(false); S.thumbs = {}; }
    render(); return;
  }
  if (t.id === 'monSec') { S.monSec = +t.value; monPrefSave(); if (S.monLive) await monLiveSend(true); return; }
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
    if (a === 'hostmap') await hostMapDialog();
    else if (a === 'seatauto') {
      if (!await modal({title: 'Xếp lại theo danh sách lớp ' + S.mon.cls + '?', ok: 'Xếp lại', html: 'Học sinh số 1 trong danh sách ngồi Máy 1 (PC1), số 2 ngồi Máy 2... (bỏ qua máy hỏng). Chỗ ngồi hiện tại của lớp này sẽ bị thay.'})) return;
      const r = await api('/api/seat_auto', {cls: S.mon.cls}); S.school = await api('/api/school'); S.stu = {}; await loadMonitor(); render();
      toast('Đã xếp ' + r.placed + ' học sinh' + (r.left ? ', còn ' + r.left + ' em chưa có máy' : ''), r.left ? 'warn' : 'ok');
    }
    else if (a === 'star') await funStar();
    else if (a === 'guide') await monGuide();
    else if (a === 'share') await funShare();
    else if (a === 'shareoff') { const hs = S.hosts.slice(); await api('/api/share_clear', {hosts: hs}); toast('Đã tắt chiếu bài trên ' + hs.length + ' máy', 'ok'); }
    else if (a === 'timer') await funTimer();
    else if (a === 'reactclr') { const hs = await resolveTargets(); if (!hs) return; await api('/api/react_clear', {hosts: hs}); await loadMonitor(); render(); }
    else if (a === 'tile') {
      if (e.detail > 1 && S.monLive && S.thumbs[el.dataset.h]) { const m = S.mon.machines[el.dataset.h]; await modal({title: m.pc, ok: 'Đóng', noCancel: true, html: `<img src="${S.thumbs[el.dataset.h]}" style="width:100%;border-radius:8px"><div class="muted" style="margin-top:6px">${m.act ? esc(m.act.p + ' · ' + m.act.w) : ''}</div>`}); return; } const h = el.dataset.h; S.sel.has(h) ? S.sel.delete(h) : S.sel.add(h); render(); }
    else if (a === 'selall') monSelect(() => true);
    else if (a === 'selon') monSelect(m => m.online);
    else if (a === 'selviol') monSelect(m => m.viol);
    else if (a === 'selhand') monSelect(m => m.hand);
    else if (a === 'selnone') monSelect(() => false);
    else if (a === 'act') await runAction(el.dataset.k);
    else if (a === 'lockscr' || a === 'msg') {
      if (!S.qn) await loadQuick();
      const text = await modal({title: a === 'msg' ? 'Gửi tin nhắn' : 'Khóa màn hình kèm lời nhắn', ok: a === 'msg' ? 'Gửi' : 'Khóa', danger: a !== 'msg',
        html: quickChips('#monTxt') + '<textarea id="monTxt" rows="3" style="width:100%;box-sizing:border-box" placeholder="Nội dung hiện giữa màn hình học sinh"></textarea>', collect: r => r.querySelector('#monTxt').value.trim()});
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


/* ---------- Gán máy vào vị trí: dùng khi tên PC không trùng số vị trí trên sơ đồ (vd. PC11 ngồi ở vị trí 8) ---------- */
async function hostMapDialog() {
  const names = await api('/api/hostnames'); const nm = h => (names.manual || {})[h] || (names.auto || {})[h] || '';
  const cur = (S.school || {}).seat_hostmap || {};
  const rows = S.hosts.map((h, i) => `<tr><td><b>${esc(nm(h) || h)}</b>${nm(h) ? `<div class="muted" style="font-size:11.5px">${esc(h)}</div>` : ''}</td><td><input type="number" min="1" max="300" data-hm="${esc(h)}" value="${cur[h] || ''}" placeholder="tự động" style="width:90px"></td></tr>`).join('');
  const byName = (S.school || {}).seat_by_name !== false;
  const v = await modal({title: '🔗 Gán máy vào vị trí trong phòng', ok: 'Lưu', html: `<label class="switch" style="margin-bottom:8px"><input type="checkbox" id="hmByName" ${byName ? 'checked' : ''}><span class="tr"></span><span><b>Số vị trí = số cuối tên PC</b> (PC1 luôn ở vị trí 1, PC07 ở vị trí 7). Khuyên dùng: máy cố định, chỉ học sinh đổi chỗ. Tắt thì dùng bảng bên dưới.</span></label><p class="muted" style="margin-top:0">Nhập <b>số vị trí trên sơ đồ</b> cho từng máy. Để trống = tự động (theo “Tên máy mẫu” hoặc thứ tự danh sách). Áp dụng cho mọi lớp vì đây là vị trí thật của máy trong phòng.</p>
      <div class="row" style="gap:6px;margin-bottom:6px"><button class="btn sm ghost" data-hmfill="order">Điền theo thứ tự danh sách</button><button class="btn sm ghost" data-hmfill="digits">Điền theo số trong tên PC</button><button class="btn sm ghost" data-hmfill="clear">Xóa hết</button></div>
      <div style="max-height:50vh;overflow:auto"><table class="tbl"><thead><tr><th>Máy</th><th>Vị trí (số máy trên sơ đồ)</th></tr></thead><tbody>${rows}</tbody></table></div>`,
    collect: r => ({by_name: r.querySelector('#hmByName').checked, map: Object.fromEntries([...r.querySelectorAll('[data-hm]')].map(i => [i.dataset.hm, i.value]))})});
  if (!v) return;
  try { S.school = await api('/api/seat_hostmap', v).then(() => api('/api/school')); toast('Đã lưu vị trí các máy', 'ok'); if (S.page === 'monitor') { await loadMonitor(); } render(); } catch (err) { toast(err.message, 'err'); }
}
document.addEventListener('click', e => {
  const b = e.target.closest('[data-hmfill]'); if (!b) return;
  e.preventDefault();
  const ins = [...document.querySelectorAll('[data-hm]')];
  ins.forEach((i, k) => {
    if (b.dataset.hmfill === 'clear') i.value = '';
    else if (b.dataset.hmfill === 'order') i.value = k + 1;
    else { const m = (i.closest('tr').querySelector('b').textContent.match(/(\d+)\s*$/)); i.value = m ? +m[1] : ''; }
  });
});
