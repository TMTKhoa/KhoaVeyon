// KhoaVeyon - Trang Trạng thái máy
function ago(ts) {
  if (!ts) return '';
  const s = Math.max(0, Math.round(Date.now() / 1000 - ts));
  return s < 90 ? 'vài giây' : s < 3600 ? Math.round(s / 60) + ' phút' : Math.round(s / 3600 * 10) / 10 + ' giờ';
}
const HEALTH = {green: ['#16a34a', 'Tốt'], yellow: ['#f59e0b', 'Cần chú ý'], red: ['#dc2626', 'Có lỗi'], off: ['#94a3b8', 'Tắt'], wait: ['#cbd5e1', '...']};
function healthCell(r) {
  const [c, t] = HEALTH[r.health || 'wait'];
  const probs = (r.problems || []).map(p => `<div class="hprob" style="font-size:12px;margin-top:3px">${esc(p.text)}${p.fix ? ` <button class="link" data-xa="healthfix" data-fix="${esc(p.fix)}" data-h="${esc(r.host)}">Sửa</button>` : ''}</div>`).join('');
  return `<span class="hdot" style="display:inline-block;width:11px;height:11px;border-radius:50%;background:${c};vertical-align:-1px"></span> <b style="color:${c}">${t}</b>${probs}`;
}
function healthSummary() {
  const s = S.stat; if (!s || !S.hosts.length) return '';
  const fixes = {};
  s.hosts.forEach(r => (r.problems || []).forEach(p => { if (p.fix) (fixes[p.fix] = fixes[p.fix] || []).push(r.host); }));
  const names = {svc: 'Cài lại dịch vụ', watch: 'Bật lại giám sát', blockai: 'Khóa AI'};
  const btns = Object.entries(fixes).map(([k, hs]) => `<button class="btn sm" data-xa="healthfix" data-fix="${esc(k)}" data-hs="${esc(JSON.stringify(hs))}">🔧 ${names[k]} (${hs.length} máy)</button>`).join(' ');
  return `<span style="color:#16a34a">● <b>${s.green}</b> tốt</span> · <span style="color:#f59e0b">● <b>${s.yellow}</b> cần chú ý</span> · <span style="color:#dc2626">● <b>${s.red}</b> có lỗi</span> · <span style="color:#64748b">● <b>${s.off}</b> tắt</span>${btns ? '<div class="row" style="margin-top:8px;flex-wrap:wrap">' + btns + '</div>' : ''}`;
}
function statusRows() {
  const rows = (S.stat && S.stat.hosts) || [];
  const byHost = new Map(rows.map(r => [r.host, r]));
  return S.hosts.map((h, i) => {
    const r = byHost.get(h) || {checked: false};
    const wait = !r.checked;
    const dot = wait ? '<span class="sdot wait"></span>Đang kiểm tra' : r.online ? `<span class="sdot on"></span>Đang bật <span class="muted">· ${esc(ago(r.since))}</span>` : `<span class="sdot off"></span>Tắt <span class="muted">· ${esc(ago(r.since))}</span>`;
    const ai = !r.online ? '' : r.ai === 'locked' ? '<span class="rchip ok">Đã khóa</span>' : r.ai === 'half' ? '<span class="rchip">Khóa dở</span>' : r.ai === 'open' ? '<span class="rchip mute">Chưa khóa</span>' : r.ai === 'unknown' ? '<span class="rchip mute" title="Không đọc được C$ hoặc không đủ quyền">Không rõ</span>' : '<span class="muted">…</span>';
    const rs = (r.restrict || []).map(x => `<span class="rchip">${esc(x)}</span>`).join('') || (r.online ? '<span class="muted">Không</span>' : '');
    const mac = r.mac ? esc(r.mac) : '<span class="muted">chưa có</span>';
    return `<tr class="${r.online ? '' : 'offrow'}"><td><input type="checkbox" data-host="${i}" ${S.sel.has(h) ? 'checked' : ''}></td>
      <td>${healthCell(r)}</td>
      <td><b>${hnLabel(h)}</b> <a href="#" class="ed" data-xa="editname" data-h="${esc(h)}" title="Đặt tên hiển thị">✎</a></td><td>${dot}</td>
      <td>${r.online ? (r.veyon ? '<span class="rchip ok">Veyon</span>' : '<span class="rchip">Chưa có Veyon</span>') : ''}</td>
      <td>${r.online ? (r.user ? esc(r.user) : '<span class="muted">chưa ai đăng nhập</span>') : ''}</td>
      <td>${rs}</td><td>${ai}</td><td>${r.watching ? '👁' : ''}</td>
      <td><a href="#" data-xa="editmac" data-i="${i}" title="Bấm để nhập MAC tay">${mac}</a></td></tr>`;
  }).join('');
}
function statusSummary() {
  const s = S.stat;
  if (!S.hosts.length) return '';
  if (!s) return 'Đang kiểm tra...';
  return `<b>${s.online}</b>/${s.total} máy đang bật`;
}
function viewStatus() {
  const noMac = S.stat ? S.stat.hosts.filter(r => !r.mac).length : 0;
  return `<section class="card">
    <h3>Trạng thái các máy học sinh <span class="badge" id="statusSum">${statusSummary()}</span></h3>
    <p class="sub">Tự cập nhật vài giây một lần khi trang này đang mở. Cột “Đang hạn chế” cho biết lệnh KhoaVeyon đã gửi gần nhất (chưa chắc đã có hiệu lực: bấm “Kiểm tra hiệu lực” để đọc trạng thái thật). Cột AI được đọc thật từ máy.</p>
    <label class="switch" style="margin:4px 0 8px"><input type="checkbox" data-cfg="reapply_on_boot" ${S.st.cfg.reapply_on_boot !== false ? 'checked' : ''}><span class="tr"></span><span>Máy khởi động lại hoặc bật lại thì tự áp lại các hạn chế đang bật (đợi có người đăng nhập; chỉ hoạt động khi KhoaVeyon đang mở)</span></label>
    <div class="row" style="flex-wrap:wrap;margin:6px 0 10px"><button class="btn" data-xa="verify" data-fix="0">✔ Kiểm tra hiệu lực</button><button class="btn" data-xa="verify" data-fix="1">✔ Kiểm tra và gửi lại lệnh nếu lệch</button><button class="btn" data-act="selftest">🧪 Tự kiểm tra 1 máy</button></div>
    <div id="healthSum" style="margin:6px 0 10px">${healthSummary()}</div>
    <div class="hosttools"><button class="link" data-act="selall">Chọn tất cả</button><button class="link" data-act="selnone">Bỏ chọn</button><span class="muted">Đã chọn ${S.hosts.filter(h => S.sel.has(h)).length}/${S.hosts.length}. Không chọn = tất cả.</span></div>
    <div class="row" style="flex-wrap:wrap;margin:10px 0 14px">
      <button class="btn ok" data-xa="power" data-p="wake">🟢 Bật máy</button>
      <button class="btn danger" data-xa="power" data-p="shutdown">⏻ Tắt máy</button>
      <button class="btn" data-xa="power" data-p="restart">🔄 Khởi động lại</button>
      <button class="btn" data-xa="power" data-p="logoff">🚪 Đăng xuất học sinh</button>
      <button class="btn ghost" data-xa="power" data-p="cancel">Hủy lệnh tắt máy</button>
      <button class="btn ghost" data-xa="power" data-p="getmac">Lấy MAC</button>
      <label class="muted" style="display:inline-flex;gap:6px;align-items:center">Chờ <input type="number" id="pwDelay" min="0" max="3600" value="${esc(S.pwDelay ?? 30)}" style="width:70px" class="xsel"> giây trước khi tắt</label>
    </div>
    ${S.hosts.length ? `<table class="tbl stbl"><thead><tr><th></th><th>Sức khỏe</th><th>Máy</th><th>Trạng thái</th><th>Veyon</th><th>Người đăng nhập</th><th>Đang hạn chế</th><th>Khóa AI</th><th>Giám sát</th><th>MAC</th></tr></thead><tbody id="statusBody">${statusRows()}</tbody></table>`
      : '<div class="empty">Chưa có máy nào. Thêm máy ở trang “Điều khiển lớp”.</div>'}
    <p class="hint" style="margin-bottom:0">Bật máy cần <b>Wake-on-LAN</b> được bật trong BIOS và card mạng, và máy giáo viên cùng mạng LAN. MAC tự được nhớ khi máy đang bật (${noMac ? noMac + ' máy chưa có MAC' : 'đã đủ MAC'}). Tắt máy, khởi động lại, đăng xuất cần quyền quản trị trên máy học sinh, giống các lệnh khác của chương trình.</p>
  </section>`;
}
async function pollStatus(now) {
  if (S.page !== 'status') return;
  try {
    S.stat = await api('/api/status' + (now ? '?now=1' : ''));
    if (S.page !== 'status') return;
    const b = $('#statusBody'); if (b) b.innerHTML = statusRows();
    const m = $('#statusSum'); if (m) m.innerHTML = statusSummary();
    const hs = $('#healthSum'); if (hs) hs.innerHTML = healthSummary();
  } catch (e) { /* mất kết nối thì lần sau thử lại */ }
}
setInterval(() => pollStatus(false), 4000);

document.addEventListener('click', async e => {
  const el = e.target.closest('[data-xa]');
  if (!el) return;
  e.preventDefault();
  const a = el.dataset.xa;
  try {
    if (a === 'power') {
      const p = el.dataset.p;
      const d = $('#pwDelay'); if (d) S.pwDelay = d.value;
      const hs = await resolveTargets(); if (!hs) return;
      const names = {shutdown: 'Tắt máy', restart: 'Khởi động lại', logoff: 'Đăng xuất học sinh'};
      if (names[p]) {
        const ok = await modal({title: names[p] + ` ${hs.length} máy?`, danger: true, ok: names[p],
          html: p === 'logoff' ? 'Học sinh sẽ bị đăng xuất ngay, <b>bài chưa lưu sẽ mất</b>.' : `Máy sẽ ${p === 'shutdown' ? 'tắt' : 'khởi động lại'} sau <b>${esc(S.pwDelay ?? 30)} giây</b>. Bài chưa lưu có thể mất. Bấm “Hủy lệnh tắt máy” để dừng trong thời gian chờ.`});
        if (!ok) return;
      }
      await api('/api/power', {action: p, hosts: hs, delay: +(S.pwDelay ?? 30)});
      openLog(); L.pending++; updBusy(); pollSoon(); setTimeout(() => { L.pending = Math.max(0, L.pending - 1); updBusy(); }, 4000);
      setTimeout(() => pollStatus(true), 3000); setTimeout(() => pollStatus(true), 12000);
      toast(`Đã gửi lệnh cho ${hs.length} máy`, 'ok');
    } else if (a === 'verify') {
      const fix = el.dataset.fix === '1';
      const hs = await resolveTargets(); if (!hs) return;
      if (fix) {
        const ok = await modal({title: `Kiểm tra và gửi lại lệnh cho ${hs.length} máy?`, ok: 'Kiểm tra', html: 'Máy nào có hạn chế không khớp với lệnh đã gửi sẽ được gửi lại đúng lệnh đó. Lệnh có dấu ⚠ như khóa AI có thể đóng trình duyệt đang mở.'});
        if (!ok) return;
      }
      await api('/api/verify', {hosts: hs, fix});
      openLog(); L.pending++; updBusy(); pollSoon(); setTimeout(() => { L.pending = Math.max(0, L.pending - 1); updBusy(); }, 4000);
      toast(`Đang kiểm tra ${hs.length} máy, xem kết quả ở Nhật ký`, 'ok');
    } else if (a === 'healthfix') {
      const fix = el.dataset.fix, hs = el.dataset.hs ? JSON.parse(el.dataset.hs) : [el.dataset.h];
      const names = {svc: 'Cài lại dịch vụ KhoaVeyon', watch: 'Bật lại giám sát', blockai: 'Khóa công cụ AI'};
      const ok = await modal({title: `${names[fix]} trên ${hs.length} máy?`, ok: 'Sửa ngay', danger: fix === 'blockai',
        html: fix === 'blockai' ? 'Trình duyệt đang mở trên các máy này sẽ bị đóng.' : fix === 'svc' ? 'Chép <code>KhoaVeyonServices.bat</code> mới nhất từ thư mục payload xuống máy học sinh rồi chạy <code>-install</code>.' : 'Chép lại script giám sát và chạy lại trên các máy này.'});
      if (!ok) return;
      await api('/api/health_fix', {fix, hosts: hs});
      openLog(); toast('Đang sửa, xem kết quả ở Nhật ký', 'ok');
      setTimeout(() => pollStatus(true), 8000); setTimeout(() => pollStatus(true), 25000);
    } else if (a === 'editname') {
      await editHostName(el.dataset.h);
    } else if (a === 'editmac') {
      const h = S.hosts[+el.dataset.i], cur = ((S.stat && S.stat.hosts.find(r => r.host === h)) || {}).mac || '';
      const v = await modal({title: 'Địa chỉ MAC của ' + h, ok: 'Lưu', collect: r => r.querySelector('input').value,
        html: `<p class="hint">Dạng AA-BB-CC-DD-EE-FF. Để trống để xóa.</p><input type="text" class="xsel" style="width:100%" value="${esc(cur)}">`});
      if (v === null) return;
      await api('/api/macs_set', {macs: {[h]: v}}); toast('Đã lưu MAC', 'ok'); pollStatus(true);
    }
  } catch (err) { toast(err.message, 'err'); }
});

/* ---------- A4: tự kiểm tra một máy ---------- */
async function runSelftest() {
  const sel = S.hosts.filter(h => S.sel.has(h));
  let host;
  if (sel.length === 1) host = sel[0];
  else if (sel.length === 0 && S.hosts.length === 1) host = S.hosts[0];
  else { toast('Hãy chọn đúng MỘT máy để tự kiểm tra (tick một máy ở bảng dưới)', 'warn'); return; }
  try { await api('/api/selftest', {hosts: [host]}); } catch (e) { toast(e.message, 'err'); return; }
  openLog();
  modal({title: '🧪 Tự kiểm tra ' + hn(host), ok: 'Đóng', noCancel: true,
    html: '<div id="stResult"><p class="muted">Đang chạy lần lượt các bước trên máy (mỗi bước bật hạn chế đều tự gỡ lại ngay). Có thể mất gần một phút; chi tiết chạy ở Nhật ký.</p></div>'});
  const t0 = Date.now();
  const timer = setInterval(async () => {
    const box = document.querySelector('#stResult');
    if (!box) { clearInterval(timer); return; }
    try {
      const r = await api('/api/selftest_result', undefined, {quiet: true});
      if (r.result && (r.result.done || r.result.error)) { clearInterval(timer); box.innerHTML = renderSelftest(r.result); }
    } catch (e) { /* tạm thời */ }
    if (Date.now() - t0 > 180000) clearInterval(timer);
  }, 2000);
}
function renderSelftest(d) {
  if (d.error) return `<div class="note warn">Lỗi: ${esc(d.error)}</div>`;
  const ic = {ok: '✔', bad: '✘', unknown: '▪', skip: '–'};
  const cl = {ok: '#15803d', bad: '#b91c1c', unknown: '#b45309', skip: '#64748b'};
  const rows = (d.steps || []).map(s => `<tr><td style="color:${cl[s.status] || ''};font-weight:800;font-size:16px">${ic[s.status] || '?'}</td><td><b>${esc(s.name)}</b></td><td class="muted">${esc(s.detail || '')}</td></tr>`).join('');
  const head = d.ok != null ? `<p>Kết quả: đạt <b>${d.ok}/${d.total}</b> bước. ✔ đạt · ✘ chưa đạt · ▪ chưa kiểm được.</p>` : '';
  return head + `<table class="tbl"><tbody>${rows}</tbody></table><p class="hint">Bước ✘ hoặc ▪ nào bất ngờ, hãy chép dòng tương ứng trong Nhật ký gửi lại để chỉnh.</p>`;
}
