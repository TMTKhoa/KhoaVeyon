// KhoaVeyon - Sơ đồ chỗ ngồi
/* ---------- sơ đồ chỗ ngồi ---------- */
const LAY_DEFAULT = {cols: 4, per: 10, from: 'teacher', first: 'left', pattern: '', seats: {}, broken: [], gv: 'center', door: 'back', flipv: false, fliph: false};
function curLay() { return Object.assign({}, LAY_DEFAULT, (S.school.layouts || {})[S.seatCls] || {}); }

/* số máy ở từng ô: hàng 0 gần bàn giáo viên, hàng cuối gần cửa; đánh số theo từng dãy */
function seatNumbers(lay) {
  const cols = +lay.cols, per = +lay.per, num = Array.from({length: per}, () => Array(cols).fill(0));
  const order = [...Array(cols).keys()]; if (lay.first === 'right') order.reverse();
  let n = 0;
  for (const c of order) {
    const rows = [...Array(per).keys()]; if (lay.from === 'door') rows.reverse();
    for (const r of rows) num[r][c] = ++n;
  }
  return num;
}

async function seatSave(patch, all) {
  const lay = Object.assign(curLay(), patch);
  for (const k of ['cols', 'per']) lay[k] = Math.max(1, Math.min(k === 'cols' ? 12 : 20, parseInt(lay[k]) || 1));
  try { S.school = await api('/api/school_layout', Object.assign({cls: S.seatCls, apply_all: !!all}, lay)); } catch (err) { toast(err.message, 'err'); }
  await loadAtt();   // sơ đồ đang hiện chỗ ngồi từ bản điểm danh đã lưu tạm: phải lấy lại, không thì giao diện vẫn là sơ đồ cũ
  render();
}

async function seatNames() {
  if (!S.stu[S.seatCls]) S.stu[S.seatCls] = (await api('/api/school_students?cls=' + encodeURIComponent(S.seatCls))).names;
  return S.stu[S.seatCls];
}

async function seatAuto() {
  const names = await seatNames(), lay = curLay(), seats = {}, bad = new Set(lay.broken || []);
  const slots = [...Array(lay.cols * lay.per).keys()].map(i => i + 1).filter(n => !bad.has(n)), total = slots.length;
  names.slice(0, total).forEach((n, i) => { seats[slots[i]] = n; });
  if (Object.keys(lay.seats).length && !(await modal({title: 'Xếp lại từ đầu?', html: 'Chỗ ngồi hiện tại của lớp này sẽ được thay bằng thứ tự trong danh sách lớp (học sinh số 1 ngồi máy 1...), bỏ qua các máy hỏng.', ok: 'Xếp lại'}))) return;
  if (names.length > total) toast(`Lớp có ${names.length} học sinh nhưng chỉ có ${total} máy dùng được, ${names.length - total} em chưa có chỗ`, 'warn');
  await seatSave({seats});
}

async function seatPick(n) {
  const names = await seatNames(), lay = curLay(), seats = Object.assign({}, lay.seats), cur = seats[n] || '';
  const isBad = (lay.broken || []).includes(n), inList = names.includes(cur);
  const used = {}; Object.values(seats).forEach(v => { used[v] = (used[v] || 0) + 1; });
  const free = names.filter(x => !used[x] || x === cur);
  const v = await modal({title: `Máy ${n}`, ok: 'Lưu',
    html: `<label class="switch"><input type="checkbox" id="seatBad" ${isBad ? 'checked' : ''}><span class="tr"></span><span>Máy hỏng</span></label>
      <div style="margin-top:14px"><div class="muted" style="margin-bottom:4px">Học sinh ngồi máy này</div>
      <select id="seatSel" style="width:100%"><option value="__none__">— Bỏ trống —</option>${free.map(x => `<option ${x === cur ? 'selected' : ''}>${esc(x)}</option>`).join('')}</select>
      <div class="muted" style="margin:10px 0 4px">Hoặc ghi tên bạn ngoài danh sách lớp</div>
      <input type="text" id="seatOther" style="width:100%" value="${cur && !inList ? esc(cur) : ''}" placeholder="Ví dụ: bạn lớp khác ngồi nhờ"></div>
      <p class="hint">Danh sách chỉ hiện học sinh chưa có chỗ${cur && inList ? ' và em đang ngồi máy này' : ''}. Máy hỏng thì không có người ngồi.</p>`,
    collect: r => ({bad: r.querySelector('#seatBad').checked, sel: r.querySelector('#seatSel').value, other: r.querySelector('#seatOther').value.trim()})});
  if (!v) return;
  const broken = new Set(lay.broken || []);
  if (v.bad) { broken.add(n); delete seats[n]; }
  else {
    broken.delete(n);
    if (v.other) seats[n] = v.other; else if (v.sel !== '__none__') seats[n] = v.sel; else delete seats[n];
  }
  await seatSave({seats, broken: [...broken]});
}

/* đảo chiều chỉ để nhìn cho khớp phòng thật: flipv = bàn giáo viên ở dưới cùng, fliph = đổi trái phải.
   Trả về các hàng đã sắp theo thứ tự hiển thị, cùng hàm đổi vị trí trái/phải và số dãy của từng cột hiển thị */
function seatOrient(lay) {
  let num = seatNumbers(lay);
  if (lay.fliph) num = num.map(r => r.slice().reverse());
  if (lay.flipv) num = num.slice().reverse();
  const cols = +lay.cols;
  const dayNo = j => { const c = lay.fliph ? cols - 1 - j : j; return lay.first === 'left' ? c + 1 : cols - c; };
  const side = k => lay.fliph ? ({left: 'right', right: 'left'}[k] || k) : k;
  return {num, dayNo, side};
}

function seatInit(name) {
  const w = String(name || '').trim().split(/\s+/).filter(Boolean);
  if (!w.length) return '＋';
  return (w.length > 1 ? w[0][0] + w[w.length - 1][0] : w[0].slice(0, 2)).toUpperCase();
}

function viewSeats() {
  const sc = S.school, cls = (sc.classes || []);
  if (!cls.length) return '';
  if (!S.seatCls || !cls.some(c => c.name === S.seatCls)) S.seatCls = (sc.current && cls.some(c => c.name === sc.current.cls)) ? sc.current.cls : cls[0].name;
  const lay = curLay(), {num, dayNo, side} = seatOrient(lay), cnt = (cls.find(c => c.name === S.seatCls) || {}).count || 0;
  const by = lay.seats, inCls = new Set(S.stu[S.seatCls] || []), filled = Object.values(by).filter(v => !inCls.size || inCls.has(v)).length;
  const bad = new Set(lay.broken || []);
  const att = (S.att && S.att.cls === S.seatCls) ? S.att : null, eff = att ? att.seats : by, off = new Set(att ? att.offline : []);
  const shareAt = {}; if (att) Object.entries(att.shares || {}).forEach(([n, m]) => { (shareAt[m] = shareAt[m] || []).push(n); });
  const head = num[0].map((_, c) => `<div class="dayhead">Dãy ${dayNo(c)}</div>`).join('');
  const cells = num.map(row => row.map(n => {
    const isBad = bad.has(n), shown = eff[n] || '', guest = shown && inCls.size && !inCls.has(shown);
    const moved = att && shown && att.moves[shown] === n, gone = att && !moved && by[n] && att.absent.includes(by[n]);
    const mates = shareAt[n] || [];
    const cl = isBad ? 'bad' : moved ? 'moved' : gone ? 'absent' : guest ? 'guest' : shown ? 'full' : 'empty';
    const nm = isBad ? 'Máy hỏng' : gone ? by[n] : shown || 'Trống';
    const av = isBad ? '✕' : gone ? seatInit(by[n]) : shown ? seatInit(shown) : '＋';
    const tag = isBad ? '' : gone ? '<em class="tg">vắng</em>' : mates.length ? `<em class="tg">+${mates.length} chung</em>` : moved ? '<em class="tg">mới</em>' : '';
    const tip = isBad ? 'Máy hỏng' : gone ? 'Vắng: ' + by[n] : moved ? shown + ' (được chuyển đến)' : (shown || 'Chưa xếp') + (mates.length ? ' · ngồi chung với ' + mates.join(', ') : '') + (off.has(n) ? ' · máy đang tắt' : '');
    return `<button class="seat ${cl} ${mates.length ? 'shared' : ''} ${off.has(n) && !isBad ? 'off' : ''}" data-act="seatpick" data-n="${n}" title="${esc(tip)}"><i class="sn">${n}</i>${tag}<span class="av">${esc(av)}</span><span class="nm">${esc(nm)}</span></button>`; }).join('')).join('');
  const slot = {left: [], center: [], right: []};
  slot[side(lay.gv)].push('<div class="tdesk">🖥 Bàn giáo viên</div>');
  if (lay.door === 'tl') slot[side('left')].push('<div class="tdoor2">🚪 Cửa ra vào</div>');
  if (lay.door === 'tr') slot[side('right')].push('<div class="tdoor2">🚪 Cửa ra vào</div>');
  const gw = 'calc(' + lay.cols + ' * var(--sw,132px) + ' + (lay.cols - 1) + ' * var(--cg,22px))';
  const front = `<div class="frontrow ${lay.flipv ? 'fv' : ''}" style="width:${gw}">${['left', 'center', 'right'].map(k => `<div>${slot[k].join('')}</div>`).join('')}</div>`;
  const opt = (v, cur, t) => `<option value="${v}" ${cur === v ? 'selected' : ''}>${t}</option>`;
  const settings = S.layOpen ? `<div class="lgrid">
      <label>Số dãy<input type="number" min="1" max="12" data-lay="cols" value="${lay.cols}"></label>
      <label>Máy mỗi dãy<input type="number" min="1" max="20" data-lay="per" value="${lay.per}"></label>
      <label>Đánh số từ<select data-lay="from">${opt('teacher', lay.from, 'Bàn giáo viên (đầu dãy)')}${opt('door', lay.from, 'Cửa ra vào (cuối dãy)')}</select></label>
      <label>Dãy số 1 ở bên<select data-lay="first">${opt('left', lay.first, 'Trái')}${opt('right', lay.first, 'Phải')}</select></label>
      <label>Tên máy mẫu<input type="text" data-lay="pattern" value="${esc(lay.pattern)}" placeholder="MAY{n}"></label>
      <label>Bàn giáo viên<select data-lay="gv">${opt('left', lay.gv, 'Góc trái')}${opt('center', lay.gv, 'Giữa')}${opt('right', lay.gv, 'Góc phải')}</select></label>
      <label>Cửa ra vào<select data-lay="door">${opt('back', lay.door, 'Cuối lớp')}${opt('tl', lay.door, 'Cùng hàng bàn giáo viên, bên trái')}${opt('tr', lay.door, 'Cùng hàng bàn giáo viên, bên phải')}</select></label>
      <label>&nbsp;<button class="btn ghost sm" data-act="seatall" title="Chép số dãy, số máy và cách đánh số sang tất cả các lớp">Áp dụng kiểu phòng cho mọi lớp</button></label>
      <p class="hint" style="grid-column:1/-1;margin:0">Số máy tăng dần dọc theo từng dãy, ${lay.from === 'teacher' ? 'bắt đầu từ máy gần bàn giáo viên' : 'bắt đầu từ máy gần cửa'}, dãy số 1 ở bên ${lay.first === 'left' ? 'trái' : 'phải'} (nhìn từ bàn giáo viên xuống lớp). Số máy đổi thành tên máy bằng <b>Tên máy mẫu</b> (ví dụ <code>MAY{n}</code> khớp MAY1, MAY01, MAY12); để trống thì theo thứ tự danh sách máy ở trang Điều khiển lớp.</p></div>` : '';
  const lg = (bg, bd, t) => `<span><i style="background:${bg};border-color:${bd}"></i>${t}</span>`;
  return `<div class="seatpage"><div class="seatmain"><section class="card"><div class="toolbar" style="margin-bottom:12px"><b>Sơ đồ chỗ ngồi</b>
      <select id="seatClsSel">${cls.map(c => `<option value="${esc(c.name)}" ${c.name === S.seatCls ? 'selected' : ''}>Lớp ${esc(c.name)}</option>`).join('')}</select><span class="grow"></span>
      <button class="btn primary" data-act="seatproject">📽 Chiếu sơ đồ cho lớp</button><button class="btn" data-act="seatauto">Tự xếp theo danh sách</button><button class="btn ghost" data-act="seatclear">Xóa chỗ ngồi</button><button class="btn ghost ${lay.flipv ? 'on' : ''}" data-act="seatflipv" title="Đảo trên dưới: đưa bàn giáo viên xuống dưới cùng của sơ đồ">⇅ Đảo dọc</button><button class="btn ghost ${lay.fliph ? 'on' : ''}" data-act="seatfliph" title="Đảo trái phải: đổi vị trí bàn giáo viên, cửa và thứ tự các dãy">⇄ Đảo ngang</button><button class="btn ghost" data-act="layopen">⚙ ${S.layOpen ? 'Ẩn cài đặt phòng' : 'Cài đặt phòng'}</button></div>
    <div class="sstats" style="margin-bottom:12px"><span class="sstat"><b>${filled}/${cnt}</b> học sinh đã có chỗ</span><span class="sstat"><b>${lay.cols * lay.per - bad.size}</b> máy dùng được</span>${bad.size ? `<span class="sstat" style="background:#fdecec;color:#b91c1c"><b>${bad.size}</b> máy hỏng</span>` : ''}${att && att.absent.length ? `<span class="sstat"><b>${att.absent.length}</b> vắng hôm nay</span>` : ''}<span class="muted" style="font-size:12.5px">Bấm vào một máy để xếp chỗ hoặc báo máy hỏng</span></div>
    ${settings}
    <div class="room"><div class="inner">${lay.flipv ? '' : front}${lay.flipv && lay.door === 'back' ? '<div class="tdoor fv">🚪 Cửa ra vào</div>' : ''}<div class="seats" style="grid-template-columns:repeat(${lay.cols},var(--sw,132px))">${lay.flipv ? cells + head : head + cells}</div>${!lay.flipv && lay.door === 'back' ? '<div class="tdoor">🚪 Cửa ra vào</div>' : ''}${lay.flipv ? front : ''}</div></div>
    <div class="legend">${lg('#eaf1ff', '#a9c3f7', 'Có người ngồi')}${lg('transparent', '#b9c4dc', 'Trống')}${lg('#f2f3f6', '#cfd3dd', 'Vắng')}${lg('#e7f7ed', '#8fd0a8', 'Được chuyển đến')}${lg('#fff6e5', '#f2cf8e', 'Ngoài danh sách lớp')}${lg('#fdecec', '#f0a8a8', 'Máy hỏng')}<span><i style="background:#f59e0b;border-color:#f59e0b;border-radius:50%"></i>Máy đang tắt</span></div></section></div><div class="seataside">${viewAttendance()}</div></div>`;
}

/* tự co ô máy để cả sơ đồ nằm gọn trong một màn hình (40 máy trở lên vẫn thấy hết) */
function fitSeats() {
  const room = document.querySelector('.room'); if (!room || S.page !== 'seats') return;
  const lay = curLay(), cols = +lay.cols, per = +lay.per;
  const cg = cols > 6 ? 8 : 14, rg = 6, top = room.getBoundingClientRect().top, dock = document.querySelector('#logdock'), bottom = Math.min(window.innerHeight, dock ? dock.getBoundingClientRect().top : 1e9);
  const availW = room.clientWidth - 24, availH = bottom - top - 62 - (lay.door === 'back' ? 26 : 0);
  const sw = Math.max(70, Math.min(132, Math.floor((availW - (cols - 1) * cg) / cols)));
  const sh = Math.max(34, Math.min(84, Math.floor((availH - 62 - (per - 1) * rg) / per)));
  const tiny = sh < 72;
  room.classList.toggle('tiny', tiny);
  room.style.setProperty('--sw', sw + 'px'); room.style.setProperty('--sh', sh + 'px');
  room.style.setProperty('--cg', (tiny ? cg : 22) + 'px'); room.style.setProperty('--rg', (tiny ? rg : 10) + 'px');
  room.style.setProperty('--fs', (tiny ? Math.max(10.5, Math.min(12.5, sh * 0.3)) : 12.5).toFixed(1) + 'px');
}
window.addEventListener('resize', () => { clearTimeout(fitSeats.t); fitSeats.t = setTimeout(fitSeats, 120); });

function viewSeatsPage() {
  const v = viewSeats();
  return v || `<section class="card"><div class="empty">Chưa có danh sách lớp nên chưa vẽ được sơ đồ. Vào <b>Lớp &amp; lịch dạy</b>, bấm “Nhập danh sách lớp” rồi quay lại đây.</div><div class="row" style="margin-top:12px"><button class="btn primary" data-page="school">Đi tới Lớp &amp; lịch dạy</button></div></section>`;
}

/* ---------- B1: chiếu sơ đồ chỗ ngồi toàn màn hình (cho học sinh tự tìm máy) ---------- */
function projectSeats() {
  if (!S.school || !S.seatCls) { toast('Chưa có lớp để chiếu', 'warn'); return; }
  const lay = curLay(), {num, dayNo, side} = seatOrient(lay);
  const by = lay.seats, inCls = new Set(S.stu[S.seatCls] || []);
  const bad = new Set(lay.broken || []);
  const att = (S.att && S.att.cls === S.seatCls) ? S.att : null, eff = att ? att.seats : by;
  const shareAt = {}; if (att) Object.entries(att.shares || {}).forEach(([n, m]) => { (shareAt[m] = shareAt[m] || []).push(n); });
  const head = num[0].map((_, c) => `<div class="pday">Dãy ${dayNo(c)}</div>`).join('');
  const cells = num.map(row => row.map(n => {
    const isBad = bad.has(n), shown = eff[n] || '', guest = shown && inCls.size && !inCls.has(shown);
    const moved = att && shown && att.moves[shown] === n, gone = att && !moved && by[n] && att.absent.includes(by[n]);
    const mates = shareAt[n] || [];
    const cl = isBad ? 'bad' : moved ? 'moved' : gone ? 'absent' : guest ? 'guest' : shown ? 'full' : 'empty';
    const nm = isBad ? 'Máy hỏng' : gone ? by[n] : shown || 'Trống';
    const tag = gone ? 'vắng' : mates.length ? ('+' + mates.length + ' chung') : moved ? 'mới' : '';
    return `<div class="pseat ${cl}"><i class="pn">${n}</i><span class="pnm">${esc(nm)}</span>${tag ? `<em>${esc(tag)}</em>` : ''}</div>`;
  }).join('')).join('');
  const slot = {left: [], center: [], right: []}; slot[side(lay.gv)].push('<div class="ptdesk">🖥 Bàn giáo viên</div>');
  if (lay.door === 'tl') slot[side('left')].push('<div class="ptdoor">🚪 Cửa</div>');
  if (lay.door === 'tr') slot[side('right')].push('<div class="ptdoor">🚪 Cửa</div>');
  const front = `<div class="pfront">${['left', 'center', 'right'].map(k => `<div>${slot[k].join('')}</div>`).join('')}</div>`;
  const absent = att && att.absent.length ? `<div class="pabs">Vắng hôm nay: <b>${att.absent.map(esc).join(', ')}</b></div>` : '';
  const el = document.createElement('div'); el.id = 'seatproject'; el.className = 'seatproject';
  el.style.setProperty('--pcols', lay.cols); el.style.setProperty('--prows', (+lay.per) + 1);
  el.innerHTML = `<div class="phead"><b>Sơ đồ lớp ${esc(S.seatCls)}</b><span class="muted">Tìm tên mình để biết ngồi máy số mấy</span><button class="pclose" title="Đóng (Esc)">✕ Đóng</button></div>
    <div class="proom"><div class="pinner">${lay.flipv ? (lay.door === 'back' ? '<div class="ptdoor pback">🚪 Cửa ra vào</div>' : '') : front}<div class="pseats">${lay.flipv ? cells + head : head + cells}</div>${lay.flipv ? front : (lay.door === 'back' ? '<div class="ptdoor pback">🚪 Cửa ra vào</div>' : '')}</div></div>
    ${absent}
    <div class="pleg"><span><i class="full"></i>Có người</span><span><i class="empty"></i>Trống</span><span><i class="absent"></i>Vắng</span><span><i class="moved"></i>Được chuyển đến</span><span><i class="guest"></i>Ngoài danh sách</span><span><i class="bad"></i>Máy hỏng</span></div>`;
  document.body.appendChild(el);
  const close = () => { el.remove(); document.removeEventListener('keydown', onKey); try { if (document.fullscreenElement) document.exitFullscreen(); } catch (e) { /* bỏ qua */ } };
  const onKey = e => { if (e.key === 'Escape') close(); };
  document.addEventListener('keydown', onKey);
  el.querySelector('.pclose').onclick = close;
  try { if (el.requestFullscreen) el.requestFullscreen().catch(() => {}); } catch (e) { /* bỏ qua */ }
}
