// KhoaVeyon - Giao diện rút gọn: Khóa / Mở cả lớp, Sửa máy tính (quét → chẩn đoán → sửa), thiết kế Desktop học sinh
/* ---------- chế độ giao diện: đầy đủ / rút gọn ---------- */
const SIMPLE_NAV = ['home', 'keep', 'allow', 'block', 'vcfg', 'desk', 'settings'];   // trang hiện trong menu ở chế độ rút gọn
S.simple = {locked: false, busy: '', hosts_n: 0, since: 0, last: ''};
S.repair = {running: false, steps: [], report: [], summary: ''};
S.desk = null; S.deskBg = ''; S.homeWatch = false;

const isSimple = () => typeof UI !== 'undefined' && UI.mode === 'simple';

function applyMode() {
  const sm = isSimple();
  document.body.classList.toggle('simplemode', sm);
  const b = $('#modeBtn');
  if (b) {
    b.innerHTML = sm ? '<span class="mi">🧰</span><span>Chuyển sang <b>Đầy đủ</b></span>' : '<span class="mi">⚡</span><span>Chuyển sang <b>Rút gọn</b></span>';
    b.title = sm ? 'Hiện đủ mọi trang và tính năng' : 'Chỉ hiện nút Khóa / Mở lớp, Sửa máy tính, danh sách và cấu hình Veyon';
  }
}

function setMode(m) {
  uiCommit({mode: m});
  applyMode();
  go(m === 'simple' ? 'home' : 'control');
}

/* ---------- trang chính (rút gọn) ---------- */
async function loadHome() {
  S.simple = await api('/api/simple', undefined, {quiet: true});
  S.repair = await api('/api/repair_state', undefined, {quiet: true});
}

const STEP_ICON = {wait: '○', run: '⏳', ok: '✅', warn: '⚠️', bad: '❌'};

function viewHome() {
  const s = S.simple, r = S.repair, n = S.hosts.length, locked = !!s.locked, busy = s.busy, opts = Object.assign({apps: true, web: true, desk: true}, s.opts || {});
  const since = s.since ? new Date(s.since * 1000).toLocaleTimeString('vi-VN', {hour: '2-digit', minute: '2-digit'}) : '';
  const steps = (r.steps || []).map(x => `<li class="rp-${x.state}"><span class="rpi">${x.state === 'run' ? '<i class="spin"></i>' : STEP_ICON[x.state] || '○'}</span><div><b>${esc(x.label)}</b>${x.detail ? `<div class="muted">${esc(x.detail)}</div>` : ''}</div></li>`).join('');
  const rep = (r.report || []).filter(x => !x.ok).map(x => `<li><b>${esc(x.host === 'Máy giáo viên' || typeof hn !== 'function' ? x.host : hn(x.host))}</b><ul>${x.issues.map(i => `<li>${esc(i)}</li>`).join('')}</ul></li>`).join('');
  const chips = S.hosts.slice(0, 60).map(h => `<span class="chip2">${hnLabelSafe(h)}</span>`).join('');
  return `<div class="stack simplehome">
    <section class="card lockhero ${locked ? 'is-locked' : 'is-open'}">
      <div class="lh-state">
        <div class="lh-ic">${busy ? '<i class="slowring"></i>' : locked ? '🔒' : '🔓'}</div>
        <div><div class="lh-t">${busy === 'lock' ? 'Đang khóa lớp...' : busy === 'unlock' ? 'Đang mở khóa...' : locked ? 'LỚP ĐANG KHÓA' : 'LỚP ĐANG MỞ'}</div>
          <div class="muted">${n ? `Áp dụng cho <b>tất cả ${n} máy</b> học sinh` : 'Chưa có máy nào, bấm “Quét mạng tìm máy” bên dưới'}${locked && since ? ` · khóa lúc ${since}` : ''}${s.last && !busy ? ` · ${esc(s.last)}` : ''}</div></div>
      </div>
      <div class="lh-btns">
        <button class="bigbtn lockb" data-sx="lock" ${busy ? 'disabled' : ''}><span>🔒</span>KHÓA LỚP</button>
        <button class="bigbtn openb" data-sx="unlock" ${busy ? 'disabled' : ''}><span>🔓</span>MỞ KHÓA</button>
      </div>
      <div class="lh-what lh-opts">
        <div class="muted" style="margin-bottom:6px">Bấm <b>KHÓA LỚP</b> sẽ khóa đúng những mục được tick dưới đây (MỞ KHÓA luôn gỡ tất cả):</div>
        <label class="lh-opt"><input type="checkbox" data-sxo="apps" ${opts.apps ? 'checked' : ''} ${busy ? 'disabled' : ''}><span>⛔ <b>Ứng dụng:</b> chặn tất cả, chỉ chạy được ứng dụng trong <a href="#" data-page="keep">danh sách được phép</a> (đồng thời tắt Task Manager, Cài đặt, Registry, CMD, PowerShell)</span></label>
        <label class="lh-opt"><input type="checkbox" data-sxo="web" ${opts.web ? 'checked' : ''} ${busy ? 'disabled' : ''}><span>🌐 <b>Web:</b> chỉ vào được trang trong <a href="#" data-page="allow">danh sách trang được phép</a> (gồm cả tên miền con như <code>abc.example.com</code>)</span></label>
        <label class="lh-opt"><input type="checkbox" data-sxo="desk" ${opts.desk ? 'checked' : ''} ${busy ? 'disabled' : ''}><span>🖼️ <b>Desktop:</b> giữ nguyên bộ icon, vị trí icon và hình nền do bạn <a href="#" data-page="desk">thiết kế</a>. Học sinh không thêm, xóa, kéo icon hay đổi hình nền được</span></label>
      </div>
    </section>
    <section class="card">
      <h3>🔧 Sửa máy tính</h3>
      <p class="sub">Một nút làm lần lượt: <b>quét mạng</b> (nhận lại máy bị đổi IP) → <b>chẩn đoán</b> từng máy → <b>tự sửa</b> lỗi tìm được.</p>
      <div class="row"><button class="btn primary big" data-sx="repair" ${r.running ? 'disabled' : ''}>${r.running ? '<i class="spin"></i> Đang sửa...' : '🔧 Sửa máy tính'}</button>
        <button class="btn ghost" data-sx="scan" ${r.running ? 'disabled' : ''}>📡 Chỉ quét mạng tìm máy</button></div>
      ${steps ? `<ol class="rpsteps">${steps}</ol>` : ''}
      ${r.summary ? `<div class="note ${/^✔/.test(r.summary) ? '' : 'warn'}" style="margin-top:12px">${esc(r.summary)}</div>` : ''}
      ${rep ? `<details class="rpdet" open><summary>Máy còn lỗi cần xử lý tại chỗ</summary><ul>${rep}</ul></details>` : ''}
    </section>
    <section class="card">
      <h3>Máy học sinh <span class="badge">${n}</span></h3>
      <div class="chips2">${chips || '<span class="muted">Chưa có máy nào</span>'}</div>
      <form class="addhost" data-form="addhost" style="margin-top:12px"><input type="text" id="hostInput" placeholder="Thêm máy: tên máy hoặc IP" autocomplete="off"><button class="btn primary">Thêm</button></form>
    </section>
    <div class="tiles2">
      <button class="tile2" data-page="keep"><span>✅</span><b>Ứng dụng được phép</b><small>Sửa danh sách</small></button>
      <button class="tile2" data-page="allow"><span>🌐</span><b>Trang web được phép</b><small>Sửa danh sách</small></button>
      <button class="tile2" data-page="vcfg"><span>🛠️</span><b>Cấu hình Veyon</b><small>Sao lưu, đẩy cấu hình</small></button>
      <button class="tile2" data-page="desk"><span>🖼️</span><b>Desktop học sinh</b><small>Thiết kế icon, hình nền</small></button>
    </div>
  </div>`;
}

function hnLabelSafe(h) { return typeof hnLabel === 'function' ? hnLabel(h) : esc(h); }

async function refreshHostsFromServer() {
  try { S.st = await api('/api/state', undefined, {quiet: true}); S.hosts = S.st.cfg.hosts.slice(); S.sel = new Set([...S.sel].filter(h => S.hosts.includes(h))); } catch (e) { /* bỏ qua */ }
}

async function homeLock(on) {
  if (!S.hosts.length) { toast('Chưa có máy nào. Thêm máy hoặc bấm “Quét mạng tìm máy”.', 'warn'); return; }
  const o = Object.assign({apps: true, web: true, desk: true}, S.simple.opts || {});
  if (on && !(o.apps || o.web || o.desk)) { toast('Hãy tick ít nhất một mục cần khóa.', 'warn'); return; }
  if (on) {
    const ok = await modal({title: 'Khóa cả lớp?', ok: '🔒 Khóa lớp', danger: true,
      html: `Khóa <b>${S.hosts.length} máy</b>: ${[o.apps && 'chặn mọi ứng dụng ngoài danh sách được phép', o.web && 'chỉ cho vào các trang web được phép', o.desk && 'khóa Desktop (icon, vị trí, hình nền)'].filter(Boolean).join('; ')}.${o.apps ? '<br>Ứng dụng khác đang mở của học sinh sẽ bị đóng, bài chưa lưu có thể mất.' : ''}`});
    if (!ok) return;
  }
  try { S.simple = await api('/api/simple_lock', {lock: on, hosts: S.hosts, opts: o}); S.homeWatch = true; openLog(); render(); }
  catch (e) { toast(e.message, 'err'); }
}

async function homeRepair() {
  try { S.repair = await api('/api/repair_start', {hosts: S.hosts, scan: true}); S.homeWatch = true; openLog(); render(); }
  catch (e) { toast(e.message, 'err'); }
}

async function homeScan() {
  try {
    toast('Đang quét mạng tìm máy chạy Veyon...');
    const r = await api('/api/setup_scan', {});
    S.hosts = r.hosts.slice(); S.st.cfg.hosts = r.hosts.slice();
    toast(`Thấy ${r.found.length} máy, thêm mới ${r.added}${r.moved.length ? `, đổi IP ${r.moved.length}` : ''}`, 'ok');
    render();
  } catch (e) { toast(e.message, 'err'); }
}

let homeWasBusy = false;
async function homePoll() {
  if (S.page !== 'home' || !isSimple() || document.hidden) return;
  if (!S.homeWatch && !S.simple.busy && !S.repair.running) return;
  if ($('#modalroot') && $('#modalroot').innerHTML.trim()) return;
  const ae = document.activeElement;
  if (ae && /^(INPUT|TEXTAREA|SELECT)$/.test(ae.tagName)) return;
  try { await loadHome(); } catch (e) { return; }
  const busy = !!(S.simple.busy || S.repair.running);
  if (homeWasBusy && !busy) { S.homeWatch = false; await refreshHostsFromServer(); }
  homeWasBusy = busy;
  if (S.page === 'home') render();
}
setInterval(homePoll, 1500);

/* ---------- thiết kế Desktop học sinh ---------- */
const DESK_APPS = [
  ['Google Chrome', '%ProgramFiles%\\Google\\Chrome\\Application\\chrome.exe', '🌐'],
  ['Microsoft Edge', '%ProgramFiles(x86)%\\Microsoft\\Edge\\Application\\msedge.exe', '🧭'],
  ['Word', '%ProgramFiles%\\Microsoft Office\\root\\Office16\\WINWORD.EXE', '📘'],
  ['Excel', '%ProgramFiles%\\Microsoft Office\\root\\Office16\\EXCEL.EXE', '📗'],
  ['PowerPoint', '%ProgramFiles%\\Microsoft Office\\root\\Office16\\POWERPNT.EXE', '📙'],
  ['Notepad', 'notepad.exe', '📝'], ['Máy tính', 'calc.exe', '🧮'], ['Paint', 'mspaint.exe', '🎨'], ['File Explorer', 'explorer.exe', '📁'],
];

async function loadDesk() {
  const d = await api('/api/desk');
  d.sel = null; d.dirty = false; S.desk = d; S.deskBg = '';
  if (d.wall) { try { S.deskBg = (await api('/api/wall_img?id=' + d.wall, undefined, {quiet: true})).data; } catch (e) { /* bỏ qua */ } }
  if (!S.lists.allow) { try { await loadList('allow'); } catch (e) { /* bỏ qua */ } }
}

function deskFreeCell() {
  const D = S.desk, used = new Set(D.items.map(i => i.col + ',' + i.row));
  for (let c = 0; c < D.cols; c++) for (let r = 0; r < D.rows; r++) if (!used.has(c + ',' + r)) return [c, r];
  return [0, 0];
}

function deskAdd(it) {
  const D = S.desk;
  if (D.items.some(x => x.name.toLowerCase() === it.name.toLowerCase())) { toast('Đã có icon tên “' + it.name + '”', 'warn'); return; }
  const [col, row] = deskFreeCell();
  const n = Object.assign({id: 'i' + Date.now().toString(36) + Math.floor(Math.random() * 99), args: '', col, row}, it);
  D.items.push(n); D.sel = n.id; D.dirty = true; render();
}

function deskIconHtml(it, sel) {
  const D = S.desk;
  return `<div class="dk-ic ${sel ? 'sel' : ''}" data-id="${esc(it.id)}" style="left:${it.col / D.cols * 100}%;top:${it.row / D.rows * 100}%;width:${100 / D.cols}%;height:${100 / D.rows}%"><span class="e">${esc(it.emoji || '📁')}</span><span class="n">${esc(it.name)}</span></div>`;
}

function deskSideHtml() {
  const D = S.desk, it = D.items.find(x => x.id === D.sel);
  if (!it) return '<p class="muted">Bấm một icon trên màn hình để sửa tên, đích mở hoặc xóa. Kéo icon để đổi chỗ.</p>';
  return `<div class="formgrid">
      <div><label class="field">Tên icon</label><input type="text" data-dk="name" value="${esc(it.name)}" maxlength="40"></div>
      <div><label class="field">Biểu tượng (emoji)</label><input type="text" data-dk="emoji" value="${esc(it.emoji)}" maxlength="4"></div>
    </div>
    <label class="field" style="margin-top:8px">${it.kind === 'url' ? 'Địa chỉ trang web' : 'Đường dẫn chương trình'}</label>
    <input type="text" data-dk="target" value="${esc(it.target)}" spellcheck="false">
    ${it.kind === 'app' ? `<label class="field" style="margin-top:8px">Tham số (không bắt buộc)</label><input type="text" data-dk="args" value="${esc(it.args)}" spellcheck="false">` : ''}
    <div class="row" style="margin-top:10px"><button class="btn danger sm" data-dkx="del">🗑 Xóa icon này</button></div>`;
}

function viewDesk() {
  const D = S.desk;
  if (!D) return '<div class="note">Đang tải...</div>';
  const allowRows = ((S.lists.allow && S.lists.allow.rows) || []).map(r => String(r.a || '').trim()).filter(Boolean);
  const siteBtns = allowRows.slice(0, 40).map(d => `<button class="chip" data-dkx="addsite" data-d="${esc(d)}">+ ${esc(d)}</button>`).join('');
  const appBtns = DESK_APPS.map((a, i) => `<button class="chip" data-dkx="addapp" data-i="${i}">+ ${a[2]} ${esc(a[0])}</button>`).join('');
  const bg = S.deskBg ? `background-image:url('${S.deskBg}')` : '';
  return `<div class="stack deskpage">
    <div class="note">Đây là <b>màn hình Desktop giả lập</b> của học sinh. Kéo icon đến vị trí muốn, bấm <b>Gửi xuống máy học sinh</b>. Khi khóa Desktop, <b>chỉ đúng các icon bạn đặt ở đây</b> hiện trên máy học sinh (icon khác, kể cả This PC / Thùng rác, bị ẩn hoặc dọn đi). Học sinh <b>không thêm, xóa, đổi tên, kéo đổi chỗ icon</b> và <b>không đổi được hình nền</b> (chuột phải Desktop bị tắt, “Set as desktop background” bị chặn; nếu có cách lách thì bị đặt lại trong vài giây). Mở khóa Desktop là mọi thứ trở lại bình thường.</div>
    <div class="deskgrid">
      <section class="card">
        <h3>Màn hình học sinh <span class="badge">${D.items.length} icon</span>${D.dirty ? '<span class="badge warn">chưa lưu</span>' : ''}</h3>
        <div class="deskscr" style="${bg}"><div class="dk-grid" id="dkGrid" style="--dkc:${D.cols};--dkr:${D.rows}">${D.items.map(i => deskIconHtml(i, i.id === D.sel)).join('')}</div>
          <div class="dk-task"><span class="dk-start">⊞</span><span class="dk-search">Tìm kiếm</span><span class="sp"></span><span>🔊 📶 12:00</span></div></div>
        <div class="row" style="margin-top:14px">
          <button class="btn" data-dkx="save">💾 Lưu thiết kế</button>
          <button class="btn primary" data-dkx="apply">📤 Gửi xuống máy học sinh và khóa Desktop</button>
          <button class="btn ghost" data-dkx="send">Chỉ gửi, chưa khóa</button>
          <button class="btn ghost" data-dkx="unlock">🔓 Mở khóa Desktop</button>
        </div>
      </section>
      <div class="stack">
        <section class="card"><h3>Icon đang chọn</h3><div id="dkSide">${deskSideHtml()}</div></section>
        <section class="card"><h3>Hình nền</h3>
          <div class="row"><button class="btn sm" data-dkx="wall">🖼 Chọn ảnh nền...</button>${D.wall ? '<button class="btn sm ghost" data-dkx="nowall">Bỏ ảnh nền</button>' : '<span class="muted">Chưa chọn: giữ hình nền hiện tại của máy học sinh (vẫn không cho học sinh đổi)</span>'}</div>
          <p class="hint" style="margin:10px 0 0">Muốn hình nền có <b>tiêu đề lớp, số máy và tên em ngồi</b>? Dùng <a href="#" data-page="interact">Hình nền máy học sinh ở trang Tương tác</a>: hình đó được ưu tiên trong lúc đang dùng, bấm “Trả hình nền cũ” thì máy tự quay về hình nền thiết kế ở đây. Hai nơi không còn đè lên nhau.</p></section>
        <section class="card"><h3>Thêm icon</h3>
          <label class="field">Ứng dụng</label><div class="chips">${appBtns}</div>
          <label class="field" style="margin-top:12px">Trang web trong danh sách được phép</label><div class="chips">${siteBtns || '<span class="muted">Danh sách trang được phép đang trống</span>'}</div>
          <label class="field" style="margin-top:12px">Tự nhập</label>
          <div class="row"><input type="text" id="dkNewName" placeholder="Tên icon" style="flex:1;min-width:110px"><input type="text" id="dkNewTarget" placeholder="Địa chỉ web hoặc đường dẫn .exe" style="flex:2;min-width:160px"><button class="btn sm primary" data-dkx="addcustom">Thêm</button></div></section>
      </div>
    </div>
  </div>`;
}

function deskPaint() {
  const g = $('#dkGrid'); if (!g || !S.desk) return;
  g.innerHTML = S.desk.items.map(i => deskIconHtml(i, i.id === S.desk.sel)).join('');
}

function deskCurrent() { const D = S.desk; return D && D.items.find(x => x.id === D.sel); }

function deskPayload() { const D = S.desk; return {wall: D.wall, items: D.items.map(i => ({id: i.id, name: i.name, kind: i.kind, target: i.target, args: i.args, emoji: i.emoji, col: i.col, row: i.row}))}; }

async function deskSave() {
  const r = await api('/api/desk_save', {design: deskPayload()});
  Object.assign(S.desk, r, {sel: S.desk.sel, dirty: false});
  S.desk.items = r.items;
  if (S.desk.sel && !r.items.some(i => i.id === S.desk.sel)) S.desk.sel = null;
  return r;
}

async function deskPushNow(lock) {
  if (!S.hosts.length) { toast('Chưa có máy học sinh nào.', 'warn'); return; }
  await deskSave();
  await api('/api/desk_apply', {hosts: S.hosts, lock}); openLog();
  toast(lock ? 'Đang gửi thiết kế và khóa Desktop ' + S.hosts.length + ' máy' : 'Đang gửi thiết kế ' + S.hosts.length + ' máy', 'ok');
  render();
}

/* ---------- sự kiện ---------- */
document.addEventListener('change', e => {
  const t = e.target; if (!t.dataset || !t.dataset.sxo) return;
  S.simple.opts = Object.assign({apps: true, web: true, desk: true}, S.simple.opts || {}, {[t.dataset.sxo]: t.checked});
});

document.addEventListener('click', async e => {
  const m = e.target.closest('#modeBtn');
  if (m) { setMode(isSimple() ? 'full' : 'simple'); return; }
  const a = e.target.closest('a[data-page]'); if (a) e.preventDefault();
  const sx = e.target.closest('[data-sx]');
  if (sx && !sx.disabled) {
    const v = sx.dataset.sx;
    if (v === 'lock') homeLock(true); else if (v === 'unlock') homeLock(false);
    else if (v === 'repair') homeRepair(); else if (v === 'scan') homeScan();
    return;
  }
  const dk = e.target.closest('[data-dkx]'); if (!dk || !S.desk) return;
  const v = dk.dataset.dkx, D = S.desk;
  try {
    if (v === 'addsite') {
      const d = dk.dataset.d.replace(/^\*\./, '').replace(/^https?:\/\//, '').replace(/\/.*$/, '');
      deskAdd({name: d.replace(/^www\./, '').split('.')[0].replace(/^./, c => c.toUpperCase()), kind: 'url', target: 'https://' + d, emoji: '🌐'});
    } else if (v === 'addapp') { const p = DESK_APPS[+dk.dataset.i]; deskAdd({name: p[0], kind: 'app', target: p[1], emoji: p[2]}); }
    else if (v === 'addcustom') {
      const name = ($('#dkNewName').value || '').trim(), t = ($('#dkNewTarget').value || '').trim();
      if (!name || !t) { toast('Nhập tên và địa chỉ / đường dẫn', 'warn'); return; }
      const web = /^https?:\/\//i.test(t) || /^[\w-]+(\.[\w-]+)+(\/.*)?$/.test(t) && !/\.(exe|lnk|bat|cmd)$/i.test(t);
      deskAdd({name, kind: web ? 'url' : 'app', target: web && !/^https?:\/\//i.test(t) ? 'https://' + t : t, emoji: web ? '🌐' : '📁'});
    } else if (v === 'del') { D.items = D.items.filter(i => i.id !== D.sel); D.sel = null; D.dirty = true; render(); }
    else if (v === 'wall') {
      const data = await pickImageDownscaled(); if (!data) return;
      const r = await api('/api/wall_bg', {data: data.split(',')[1]}); D.wall = r.id; S.deskBg = data; D.dirty = true; render();
    } else if (v === 'nowall') { D.wall = ''; S.deskBg = ''; D.dirty = true; render(); }
    else if (v === 'save') { await deskSave(); toast('Đã lưu thiết kế Desktop', 'ok'); render(); }
    else if (v === 'apply') await deskPushNow(true);
    else if (v === 'send') await deskPushNow(false);
    else if (v === 'unlock') {
      if (!S.hosts.length) { toast('Chưa có máy học sinh nào.', 'warn'); return; }
      await api('/api/run', {key: 'desklock-stop', hosts: S.hosts}); openLog(); toast('Đang mở khóa Desktop', 'ok');
    }
  } catch (err) { toast(err.message, 'err'); }
});

document.addEventListener('input', e => {
  const t = e.target; if (!t.dataset || !t.dataset.dk) return;
  const it = deskCurrent(); if (!it) return;
  it[t.dataset.dk] = t.value; S.desk.dirty = true;
  deskPaint();
});

// kéo icon: gắn vào lưới theo ô
let dkDrag = null;
document.addEventListener('pointerdown', e => {
  const ic = e.target.closest('.dk-ic'); if (!ic || !S.desk || S.page !== 'desk') return;
  const it = S.desk.items.find(x => x.id === ic.dataset.id), grid = $('#dkGrid'); if (!it || !grid) return;
  dkDrag = {id: it.id, rect: grid.getBoundingClientRect(), x: e.clientX, y: e.clientY, moved: false, oc: it.col, or: it.row};
  if (S.desk.sel !== it.id) { S.desk.sel = it.id; deskPaint(); const sd = $('#dkSide'); if (sd) sd.innerHTML = deskSideHtml(); }
  e.preventDefault();
});
document.addEventListener('pointermove', e => {
  if (!dkDrag) return;
  if (!dkDrag.moved && Math.hypot(e.clientX - dkDrag.x, e.clientY - dkDrag.y) < 5) return;
  dkDrag.moved = true;
  const D = S.desk, it = D.items.find(x => x.id === dkDrag.id); if (!it) return;
  const r = dkDrag.rect;
  it.col = Math.max(0, Math.min(D.cols - 1, Math.floor((e.clientX - r.left) / r.width * D.cols)));
  it.row = Math.max(0, Math.min(D.rows - 1, Math.floor((e.clientY - r.top) / r.height * D.rows)));
  const el = $('#dkGrid .dk-ic[data-id="' + it.id + '"]');
  if (el) { el.style.left = it.col / D.cols * 100 + '%'; el.style.top = it.row / D.rows * 100 + '%'; el.classList.add('drag'); }
});
document.addEventListener('pointerup', () => {
  if (!dkDrag) return;
  const d = dkDrag; dkDrag = null;
  if (!d.moved) return;
  const D = S.desk, it = D.items.find(x => x.id === d.id); if (!it) return;
  const other = D.items.find(x => x.id !== it.id && x.col === it.col && x.row === it.row);
  if (other) { other.col = d.oc; other.row = d.or; }   // thả lên icon khác thì hai icon đổi chỗ
  D.dirty = true; render();
});
