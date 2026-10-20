// KhoaVeyon - Tiện ích, gọi API, trạng thái chung, hộp thoại, chọn máy, chạy lệnh
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

// Tên hiển thị của máy (giáo viên tự đặt); chưa đặt thì dùng IP hoặc tên gốc
const hn = h => { const c = (S.st && S.st.cfg) || {}; return (c.host_names || {})[h] || (/^\d+$/.test((c.host_auto_names || {})[h] || '') ? '' : (c.host_auto_names || {})[h]) || h; };
async function refreshHostNames() {
  try {
    const r = await api('/api/hostnames');
    const a = JSON.stringify(r.auto), m = JSON.stringify(r.manual), c = S.st.cfg;
    if (a !== JSON.stringify(c.host_auto_names || {}) || m !== JSON.stringify(c.host_names || {})) {
      c.host_auto_names = r.auto; c.host_names = r.manual;
      if (['control', 'status', 'viol', 'report'].includes(S.page) && !document.querySelector('.modalbg')) render();
    }
  } catch (e) { /* bỏ qua */ }
}
const hnLabel = h => { const n = hn(h); return n === h ? esc(h) : `${esc(n)} <span class="hip">${esc(h)}</span>`; };
async function editHostName(h) {
  const cur = ((S.st.cfg.host_names) || {})[h] || '';
  const auto = ((S.st.cfg.host_auto_names) || {})[h];
  const v = await modal({title: 'Tên hiển thị của ' + h, ok: 'Lưu', collect: r => r.querySelector('input').value,
    html: '<p class="hint">Ví dụ “Máy 01”. Chỉ đổi cách hiện trong KhoaVeyon, không đổi tên thật của máy. Để trống để dùng lại ' + (auto ? 'tên PC tự dò được (' + esc(auto) + ')' : 'IP hoặc tên gốc') + '.</p><input type="text" class="xsel" maxlength="40" style="width:100%" value="' + esc(cur) + '">'});
  if (v === null) return;
  const r = await api('/api/hostname_set', {names: {[h]: v}});
  S.st.cfg.host_names = r.names || {};
  toast('Đã lưu tên máy', 'ok'); render();
}

const QUIET = ['/api/log', '/api/alerts', '/api/ping', '/api/status', '/api/hostnames'];   // các lệnh hỏi ngầm, không hiện "đang tải"
const L = {inflight: 0, pending: 0, jobs: [], serverBusy: false, since: 0, timer: null};
function updBusy() {
  const on = L.inflight > 0 || L.pending > 0 || L.serverBusy;
  const el = $('#busy'); if (!el) return;
  el.classList.toggle('hidden', !on);
  $('#topbar').classList.toggle('on', on);
  document.body.classList.toggle('waiting', on);
  let text = 'Đang thực hiện...', pct = 0;
  if (L.jobs.length) {
    const j = L.jobs[0], more = L.jobs.length > 1 ? ` (+${L.jobs.length - 1} việc)` : '';
    text = `${j.title}: ${j.done}/${j.total} máy${j.err ? `, ${j.err} lỗi` : ''}${more}`;
    pct = j.total ? Math.round(100 * j.done / j.total) : 0;
  } else if (L.inflight > 0) text = 'Đang xử lý, vui lòng chờ...';
  else if (L.pending > 0) text = 'Đang gửi lệnh...';
  $('#busyText').textContent = text;
  $('#busyBar').style.width = pct + '%';
}
/* ---------- màn hình chờ khi một thao tác chạy lâu ----------
   Lệnh trả lời nhanh thì không hiện gì. Quá 0,7 giây: hiện khung "đang chạy" giữa màn hình (chặn bấm lặp), kèm số giây đã chờ.
   Quá 8 giây: thêm lời giải thích và nút "Ẩn" để làm việc khác (lệnh vẫn chạy tiếp, kết quả báo sau). */
const SLOW_MSG = [
  ['/api/kq_', 'Đang kết nối KhoaQuiz qua Internet'], ['/api/kt_export', 'Đang kiểm tra máy học sinh và tạo file cho KhoaTool'],
  ['/api/school_attendance_set', 'Đang kiểm tra máy nào đang bật và dồn chỗ'], ['/api/school_attendance', 'Đang tải điểm danh'],
  ['/api/school_upload', 'Đang đọc file danh sách'], ['/api/upload', 'Đang tải file lên'], ['/api/setup_scan', 'Đang quét mạng tìm máy học sinh'],
  ['/api/setup_status', 'Đang kiểm tra thiết lập'], ['/api/veyon_list', 'Đang hỏi Veyon trên máy học sinh'], ['/api/report', 'Đang tổng hợp báo cáo'],
  ['/api/vcfg', 'Đang đọc cấu hình Veyon'], ['/api/list', 'Đang đọc hoặc ghi file Excel'], ['/api/exam', 'Đang chuẩn bị chế độ thi'],
  ['/api/school', 'Đang tải dữ liệu lớp học'], ['/api/startup', 'Đang tải cài đặt'], ['/api/update', 'Đang kiểm tra bản cập nhật'],
];
const SLOW = {list: [], seq: 0, timer: null, tick: null, hidden: new Set()};
function slowLabel(path) { const m = SLOW_MSG.find(([p]) => path.startsWith(p)); return m ? m[1] : 'Đang xử lý'; }
function slowStart(path) {
  const id = ++SLOW.seq;
  SLOW.list.push({id, label: slowLabel(path), t0: Date.now()});
  clearTimeout(SLOW.timer); SLOW.timer = setTimeout(slowShow, 700);
  return id;
}
function slowEnd(id) {
  SLOW.list = SLOW.list.filter(x => x.id !== id); SLOW.hidden.delete(id);
  if (!SLOW.list.length) { clearTimeout(SLOW.timer); clearInterval(SLOW.tick); SLOW.tick = null; const el = $('#slowbox'); if (el) el.remove(); }
  else slowShow();
}
function slowShow() {
  const vis = SLOW.list.filter(x => !SLOW.hidden.has(x.id) && Date.now() - x.t0 >= 650);
  let el = $('#slowbox');
  if (!vis.length) { if (el) el.remove(); if (SLOW.list.length) SLOW.timer = setTimeout(slowShow, 300); return; }
  const j = vis[0], sec = Math.floor((Date.now() - j.t0) / 1000), long = sec >= 8;
  if (!el) {
    el = document.createElement('div'); el.id = 'slowbox'; el.setAttribute('role', 'status'); el.setAttribute('aria-live', 'polite');
    el.addEventListener('click', e => { if (e.target.closest('[data-slowhide]')) { SLOW.list.forEach(x => SLOW.hidden.add(x.id)); slowShow(); } });
    document.body.appendChild(el);
  }
  el.innerHTML = `<div class="slowcard"><div class="slowring"></div><div class="slowtx"><b>${esc(j.label)}...</b>
      <div class="muted">Chương trình vẫn đang chạy, vui lòng chờ một chút${sec ? ` · ${sec} giây` : ''}${vis.length > 1 ? ` · ${vis.length} việc` : ''}</div>
      ${long ? `<div class="slowmore">Mạng chậm hoặc có máy học sinh không trả lời thì có thể mất tới 1 phút. Không cần bấm lại, kết quả sẽ hiện khi xong.</div><button class="btn sm ghost" data-slowhide="1">Ẩn, làm việc khác</button>` : ''}</div></div>`;
  if (!SLOW.tick) SLOW.tick = setInterval(slowShow, 1000);
}

/* nút vừa bấm: hiện vòng quay và khóa tạm cho tới khi lệnh của nó trả lời (tránh bấm hai lần) */
document.addEventListener('click', e => { const b = e.target.closest('button'); if (b) { L.lastBtn = b; L.lastBtnAt = Date.now(); } }, true);
function btnBusy() {
  const b = L.lastBtn; if (!b || Date.now() - L.lastBtnAt > 1500 || b.closest('#slowbox')) return null;
  L.lastBtn = null; b.classList.add('is-loading'); b.disabled = true; return b;
}
function btnDone(b) { if (b) { b.classList.remove('is-loading'); b.disabled = false; } }

function pollSoon() { clearTimeout(L.timer); L.timer = setTimeout(pollLog, 250); }
async function api(path, body, opts) {   // opts.quiet: lệnh chạy ngầm theo hẹn giờ, không hiện "đang tải"
  const quiet = (opts && opts.quiet) || QUIET.some(q => path.startsWith(q));
  const init = {method: body === undefined ? 'GET' : 'POST', headers: {'X-Token': TOKEN}};
  if (body !== undefined) { init.headers['Content-Type'] = 'application/json'; init.body = JSON.stringify(body); }
  let r, sid = 0, btn = null;
  if (!quiet) { L.inflight++; updBusy(); sid = slowStart(path); btn = btnBusy(); }
  try {
    try { r = await fetch(path, init); } catch (e) { throw new Error('Mất kết nối với chương trình. Hãy mở lại bằng Chay-KhoaVeyon.bat'); }
    const data = await r.json().catch(() => ({error: 'Phản hồi không hợp lệ'}));
    if (r.status === 423 || data.locked) { if (typeof showLock === 'function') showLock(data); throw new Error(data.error || 'Ứng dụng đang khóa'); }
    if (!r.ok || data.error) throw new Error(data.error || ('Lỗi ' + r.status));
    return data;
  } finally {
    if (!quiet) { L.inflight--; updBusy(); slowEnd(sid); btnDone(btn); }
  }
}

const PAGES = [
  {id:'setup', ic:'🚀', name:'Thiết lập ban đầu', title:'Thiết lập ban đầu', sub:'Một nút để chuẩn bị mọi thứ cần thiết trước khi dùng lần đầu.'},
  {id:'control', ic:'🎛️', name:'Điều khiển lớp', title:'Điều khiển lớp học', sub:'Chọn máy học sinh rồi bấm một nút để khóa máy, chặn web hoặc chặn ứng dụng.'},
  {id:'exam', ic:'📝', name:'Chế độ thi', title:'Chế độ thi', sub:'Một nút bật hết các bước cho giờ kiểm tra: khóa AI, chỉ trang cho phép, giám sát, nhãn chỗ ngồi. Hết giờ một nút để mở lại.'},
  {id:'status', ic:'📡', name:'Trạng thái máy', title:'Trạng thái máy học sinh', sub:'Máy nào đang bật, ai đăng nhập, đang bị hạn chế gì. Bật, tắt, khởi động lại hàng loạt.'},
  {id:'school', ic:'📅', name:'Lớp & lịch dạy', title:'Lớp và lịch dạy', sub:'Nhập danh sách lớp và thời khóa biểu để chương trình tự biết đang dạy lớp nào và ghi tên lớp vào từng vi phạm.'},
  {id:'auto', ic:'⏱️', name:'Tự động theo tiết', title:'Tự động theo thời khóa biểu', sub:'Vào tiết thì tự khóa theo chế độ lớp, hết tiết thì tự mở. Tự bật máy trước giờ học và tắt máy sau giờ học.'},
  {id:'seats', ic:'🪑', name:'Sơ đồ lớp học', title:'Sơ đồ lớp học', sub:'Xếp chỗ ngồi, điểm danh vắng và tự dồn chỗ theo máy gần nhất.'},
  {id:'viol', ic:'🚨', name:'Vi phạm', title:'Vi phạm của học sinh', sub:'Ảnh và thông tin vi phạm tự động gửi về từ các máy học sinh đang được giám sát.'},
  {id:'report', ic:'📊', name:'Báo cáo', title:'Báo cáo vi phạm', sub:'Thống kê cuối buổi: máy nào, trang nào vi phạm nhiều nhất.'},
  {id:'vcfg', ic:'🛠️', name:'Cấu hình Veyon', title:'Cấu hình Veyon', sub:'Sao lưu, so sánh, khôi phục và đẩy cấu hình xuống máy học sinh, thêm máy vào Veyon Master.'},
  {id:'dist', ic:'📦', name:'Phân phối & chạy', title:'Phân phối và chạy ứng dụng', sub:'Chép file sang máy học sinh rồi chạy ứng dụng chỉ với một nút bấm.'},
  {grp:'Danh sách'},
  {id:'keep', ic:'✅', name:'Ứng dụng được phép', list:'keep'},
  {id:'allow', ic:'🌐', name:'Trang web được phép', list:'allow'},
  {id:'block', ic:'⛔', name:'Ứng dụng bị chặn', list:'block'},
  {id:'ai', ic:'🤖', name:'Trang AI bị chặn', list:'ai'},
  {grp:'Hệ thống'},
  {id:'settings', ic:'⚙️', name:'Cài đặt', title:'Cài đặt', sub:'Đường dẫn, mẫu lệnh Veyon và tên các mục điều khiển.'},
];

const S = {setup:null, st:null, hosts:[], sel:new Set(), page:'control', lists:{}, payload:[], logSeq:0, logOpen:true, busy:false,
  school:null, att:null, layOpen:false, schoolBrief:null, seatCls:'', stu:{}, violCls:'', report:null, reportRange:'today', groupToasts:{}, alerts:[], alertSeq:0, alertInit:false, unseen:0, watching:0, violHost:'', applock:null, appLocked:false};

/* ---------- tiện ích giao diện ---------- */
function toast(msg, kind = '') {
  const el = document.createElement('div');
  el.className = 'toast ' + kind;
  el.textContent = msg;
  $('#toasts').appendChild(el);
  setTimeout(() => el.remove(), kind === 'err' ? 7000 : 3800);
}

function modal({title, html, ok = 'Đồng ý', cancel = 'Hủy', danger = false, collect = null, noCancel = false, third = null}) {
  return new Promise(resolve => {
    const root = $('#modalroot');
    root.innerHTML = `<div class="modalbg"><div class="modalbox" role="dialog"><h3>${esc(title)}</h3><div class="body">${html}</div>
      <div class="btns">${noCancel ? '' : `<button class="btn" data-m="cancel">${esc(cancel)}</button>`}${third ? `<button class="btn ghost" data-m="third">${esc(third.label)}</button>` : ''}<button class="btn ${danger ? 'danger' : 'primary'}" data-m="ok">${esc(ok)}</button></div></div></div>`;
    const done = v => { root.innerHTML = ''; document.removeEventListener('keydown', onKey); resolve(v); };
    const onKey = e => { if (e.key === 'Escape') done(null); };
    document.addEventListener('keydown', onKey);
    root.querySelector('[data-m=ok]').onclick = () => done(collect ? collect(root) : true);
    const c = root.querySelector('[data-m=cancel]'); if (c) c.onclick = () => done(null);
    const t3 = root.querySelector('[data-m=third]'); if (t3) t3.onclick = () => done(third.value);
    root.querySelector('.modalbg').addEventListener('mousedown', e => { if (e.target.classList.contains('modalbg')) done(null); });
    const f = root.querySelector('textarea,input'); if (f) f.focus(); else root.querySelector('[data-m=ok]').focus();
  });
}

/* ---------- máy học sinh ---------- */
async function saveHosts() { try { await api('/api/hosts', {hosts: S.hosts}); } catch (e) { toast(e.message, 'err'); } }

function addHosts(text) {
  let n = 0;
  for (const h of String(text).split(/[,\s;]+/)) {
    if (h && !S.hosts.includes(h)) { S.hosts.push(h); S.sel.add(h); n++; }
  }
  if (n) saveHosts();
  return n;
}

function targets() {
  const sel = S.hosts.filter(h => S.sel.has(h));
  return sel.length ? {hosts: sel, all: false} : {hosts: S.hosts.slice(), all: true};
}

async function resolveTargets() {
  if (!S.hosts.length) { toast('Hãy thêm máy học sinh trước ở trang "Điều khiển lớp".', 'warn'); return null; }
  const t = targets();
  if (t.all) {
    const ok = await modal({title: 'Áp dụng cho tất cả máy?', html: `Chưa chọn máy nào. Áp dụng cho <b>tất cả ${t.hosts.length} máy</b>?`, ok: 'Áp dụng cho tất cả'});
    if (!ok) return null;
  }
  return t.hosts;
}

function action(key) { return S.st.actions.find(a => a.key === key); }

async function confirmRisky(a, n) {
  if (!a.confirm) return true;
  return !!(await modal({title: 'Xác nhận', danger: true, ok: 'Tiếp tục',
    html: `<b>${esc(a.label)}</b> trên ${n} máy.<br>Ứng dụng đang mở của học sinh có thể bị đóng, bài chưa lưu sẽ mất.`}));
}

async function runAction(key) {
  const a = action(key);
  const hosts = await resolveTargets(); if (!hosts) return;
  if (!(await confirmRisky(a, hosts.length))) return;
  try {
    toast(`Đang gửi lệnh "${a.label}" tới ${hosts.length} máy...`);
    await api('/api/run', {key, hosts}); openLog();
    L.pending++; updBusy(); pollSoon();            // hiện "đang chạy" ngay, không chờ lần hỏi tiếp theo
    setTimeout(() => { L.pending = Math.max(0, L.pending - 1); updBusy(); }, 4000);
  }
  catch (e) { toast(e.message, 'err'); }
}
