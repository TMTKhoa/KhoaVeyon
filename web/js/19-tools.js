// KhoaVeyon - Công cụ mới: Chẩn đoán, Sao lưu/Khôi phục, Excel mẫu và giờ tiết
async function downloadFile(query, fallbackName) {
  const r = await fetch('/api/download?' + query, {headers: {'X-Token': TOKEN}});
  if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(d.error || ('Lỗi ' + r.status)); }
  const cd = r.headers.get('Content-Disposition') || '', m = /filename\*=UTF-8''([^;]+)/.exec(cd);
  const name = m ? decodeURIComponent(m[1]) : fallbackName;
  const url = URL.createObjectURL(await r.blob());
  const a = document.createElement('a'); a.href = url; a.download = name; document.body.appendChild(a); a.click();
  setTimeout(() => { a.remove(); URL.revokeObjectURL(url); }, 1000);
  return name;
}
function fileToB64(file) {
  return new Promise((res, rej) => { const fr = new FileReader(); fr.onload = () => res(String(fr.result).split(',')[1] || ''); fr.onerror = () => rej(new Error('Không đọc được file')); fr.readAsDataURL(file); });
}

/* ---------- Sao lưu / Khôi phục (đặt trong Cài đặt) ---------- */
function backupCard() {
  return `<section class="card"><h3>Sao lưu và khôi phục</h3>
    <p class="sub">Một file .zip chứa danh sách máy, tên hiển thị, cấu hình, lớp, thời khóa biểu, sơ đồ chỗ ngồi và các danh sách Excel. Dùng để chuyển sang máy giáo viên khác hoặc cài lại Windows. Ảnh vi phạm không nằm trong file sao lưu.</p>
    <div class="row" style="flex-wrap:wrap">
      <button class="btn primary" data-tl="backup" data-secrets="1">💾 Sao lưu đầy đủ</button>
      <button class="btn" data-tl="backup" data-secrets="0" title="Không kèm khóa Agent: máy học sinh đã cài vẫn cần khóa của máy cũ, nên dùng bản đầy đủ nếu muốn máy học sinh tự nhận máy mới">Sao lưu không kèm khóa Agent</button>
      <button class="btn" data-tl="restore">📂 Khôi phục từ file...</button>
    </div>
    <p class="hint" style="margin-bottom:0">⚠ Bản đầy đủ chứa <b>khóa bí mật Agent</b>: ai có file này điều khiển được các máy học sinh. Cất ở nơi an toàn. Khi khôi phục, chương trình tự lưu bản hiện tại vào file <code>truoc-khi-khoi-phuc.zip</code> trong thư mục dữ liệu. Đường dẫn riêng của từng máy (veyon-cli, thư mục danh sách...) không bị chép đè.</p></section>`;
}
async function restoreFlow() {
  const files = await new Promise(res => pickFile('.zip', false, f => res(f)));
  const f = files[0]; if (!f) return;
  const data = await fileToB64(f);
  const pv = await api('/api/backup_preview', {data});
  const ck = (k, t, on = true) => `<label style="display:block;margin:6px 0"><input type="checkbox" data-part="${k}" ${on ? 'checked' : ''}> ${t}</label>`;
  const parts = await modal({title: 'Khôi phục từ ' + f.name, ok: 'Khôi phục', danger: true,
    collect: r => [...r.querySelectorAll('[data-part]:checked')].map(x => x.dataset.part),
    html: `<p>Sao lưu lúc <b>${esc(pv.created || '?')}</b> (KhoaVeyon ${esc(pv.version || '?')})${pv.secrets ? ', có kèm khóa Agent' : ', không kèm khóa Agent'}.</p>
      ${ck('config', `Danh sách máy và cấu hình (${pv.hosts} máy)`)}${ck('school', `Lớp, thời khóa biểu, sơ đồ (${pv.classes} lớp, ${pv.slots} tiết/tuần)`)}${ck('lists', `Danh sách Excel (${pv.lists.length} file${pv.lists.length ? ': ' + esc(pv.lists.join(', ')) : ''})`, pv.lists.length > 0)}
      <p class="hint">Phần được chọn sẽ <b>thay</b> dữ liệu hiện tại.</p>`});
  if (!parts || !parts.length) return;
  const r = await api('/api/backup_restore', {data, parts});
  toast('Đã khôi phục: ' + r.done.join(', '), 'ok');
  S.st = await api('/api/state'); S.hosts = S.st.cfg.hosts.slice(); S.lists = {}; S.school = null;
  try { await loadSchool(); } catch (e) { /* bỏ qua */ }
  render(true);
}

/* ---------- Excel mẫu và giờ tiết (đặt trong trang Lớp & lịch dạy) ---------- */
function schoolTemplateCard(sc) {
  const bells = sc.bells || {};
  const rows = Array.from({length: 10}, (_, i) => { const n = String(i + 1), b = bells[n] || ['', '']; return `<tr><td>Tiết ${n}</td><td><input type="time" class="xsel" data-bell="${n}" data-i="0" value="${esc(b[0])}"></td><td><input type="time" class="xsel" data-bell="${n}" data-i="1" value="${esc(b[1])}"></td></tr>`; }).join('');
  return `<section class="card"><div class="toolbar" style="margin-bottom:10px"><b>File mẫu và giờ tiết</b></div>
    <div class="row" style="flex-wrap:wrap;gap:10px">
      <button class="btn" data-tl="tpl" data-what="timetable">⬇ Tải Excel thời khóa biểu mẫu</button>
      <button class="btn" data-tl="tpl" data-what="classes">⬇ Tải Excel danh sách lớp mẫu</button>
    </div>
    <p class="hint">File thời khóa biểu mẫu dùng đúng giờ tiết bên dưới. Điền tên lớp vào ô, lưu rồi bấm “Nhập thời khóa biểu”. Ô vàng là ví dụ, xóa hoặc thay đi.</p>
    <details><summary><b>Giờ các tiết</b> <span class="muted">(dùng khi file thời khóa biểu chỉ ghi số tiết, và cho file mẫu)</span></summary>
      <div class="row" style="margin:10px 0;flex-wrap:wrap"><select class="xsel" id="bellPreset"><option value="">— chọn bộ giờ có sẵn —</option>${(sc.bell_sets || []).map(s => `<option value="${esc(s.key)}">${esc(s.label)}</option>`).join('')}</select>
        <button class="btn sm" data-tl="bellpreset">Áp dụng bộ giờ</button></div>
      <table class="tbl" style="max-width:380px"><thead><tr><th></th><th>Bắt đầu</th><th>Kết thúc</th></tr></thead><tbody>${rows}</tbody></table>
      <div class="row" style="margin-top:10px"><button class="btn primary sm" data-tl="bellsave">Lưu giờ tiết</button><span class="muted">Đổi giờ xong cần nhập lại thời khóa biểu (nếu file ghi số tiết) để áp dụng.</span></div></details></section>`;
}

/* ---------- Chẩn đoán ---------- */
const DG_ST = {ok: ['#16a34a', '●', 'Tốt'], warn: ['#f59e0b', '●', 'Chú ý'], bad: ['#dc2626', '●', 'Lỗi'], na: ['#94a3b8', '○', 'Chưa rõ']};
function viewDiag() {
  const d = S.diag;
  const dot = st => { const [c, ic] = DG_ST[st] || DG_ST.na; return `<span style="color:${c};font-size:16px">${ic}</span>`; };
  const t = d ? d.teacher.map(r => `<tr><td>${dot(r.state)}</td><td><b>${esc(r.label)}</b></td><td class="muted">${esc(r.detail)}</td><td>${r.fix ? `<button class="btn sm" data-tl="dgfix" data-fix="${esc(r.fix)}">🔧 Mở cổng tường lửa</button>` : ''}</td></tr>`).join('') : '';
  let body = '';
  if (d) {
    const cols = ['veyon', 'agent', 'clock', 'service'], names = {veyon: 'Veyon', agent: 'Agent', clock: 'Giờ máy', service: 'Dịch vụ'};
    const fixes = {};
    d.machines.forEach(m => m.rows.forEach(r => { if (r.fix && r.fix !== 'firewall') (fixes[r.fix] = fixes[r.fix] || []).push(m.host); }));
    const fname = {time: 'Đồng bộ giờ', service: 'Cài lại dịch vụ'};
    const bulk = Object.entries(fixes).map(([k, hs]) => `<button class="btn sm" data-tl="dgfix" data-fix="${esc(k)}" data-hs="${esc(JSON.stringify(hs))}">🔧 ${fname[k]} (${hs.length} máy)</button>`).join(' ');
    const rows = d.machines.map(m => {
      const by = Object.fromEntries(m.rows.map(r => [r.id, r]));
      const cells = cols.map(c => { const r = by[c] || {state: 'na', detail: ''}; return `<td title="${esc(r.detail)}">${dot(r.state)}${r.state !== 'ok' && r.state !== 'na' ? ` <span style="font-size:12px">${esc(r.detail)}</span>` : ''}${r.fix ? ` <button class="link" data-tl="dgfix" data-fix="${esc(r.fix)}" data-hs="${esc(JSON.stringify([m.host]))}">Sửa</button>` : ''}</td>`; }).join('');
      return `<tr><td><b>${hnLabel(m.host)}</b></td>${cells}</tr>`;
    }).join('');
    const ok = d.machines.filter(m => m.rows.every(r => r.state === 'ok')).length;
    body = `<div style="margin:8px 0"><b>${ok}</b>/${d.machines.length} máy đạt đủ.${bulk ? '<div class="row" style="margin-top:8px;flex-wrap:wrap">' + bulk + '</div>' : ''}</div>
      <table class="tbl"><thead><tr><th>Máy</th>${cols.map(c => `<th>${names[c]}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table>
      <h4 style="margin:18px 0 6px">Máy giáo viên</h4><table class="tbl"><tbody>${t}</tbody></table>`;
  }
  return `<section class="card"><h3>Chẩn đoán</h3>
    <p class="sub">Bảng xanh/đỏ cho từng máy: Veyon, Agent, giờ máy, bản dịch vụ; tường lửa kiểm ở máy giáo viên. Rê chuột vào ô để xem chi tiết. Máy chưa chọn thì kiểm tất cả.</p>
    <div class="row"><button class="btn primary" data-tl="dgrun">🩺 Chẩn đoán ngay</button><span class="muted">${S.diagAt ? 'Lần cuối: ' + esc(S.diagAt) : ''}</span></div>${body}</section>`;
}
async function runDiag() {
  const hs = S.hosts.filter(h => S.sel.has(h)); const hosts = hs.length ? hs : S.hosts;
  if (!hosts.length) { toast('Chưa có danh sách máy học sinh', 'err'); return; }
  S.diag = await api('/api/diagnose', {hosts}); S.diagAt = new Date().toLocaleTimeString('vi-VN'); render();
}

document.addEventListener('click', async e => {
  const el = e.target.closest('[data-tl]'); if (!el) return;
  e.preventDefault();
  try {
    const a = el.dataset.tl;
    if (a === 'backup') { const n = await downloadFile('what=backup&secrets=' + el.dataset.secrets, 'KhoaVeyon-backup.zip'); toast('Đã tải ' + n, 'ok'); }
    else if (a === 'restore') await restoreFlow();
    else if (a === 'tpl') { const q = el.dataset.what === 'timetable' ? 'what=timetable' : 'what=classes'; const n = await downloadFile(q, 'mau.xlsx'); toast('Đã tải ' + n, 'ok'); }
    else if (a === 'bellpreset') { const k = $('#bellPreset').value; if (!k) { toast('Chọn một bộ giờ trước', 'err'); return; } S.school = await api('/api/school_set', {action: 'bells', preset: k}); toast('Đã đặt giờ tiết', 'ok'); render(); }
    else if (a === 'bellsave') {
      const b = {}; document.querySelectorAll('[data-bell]').forEach(i => { const n = i.dataset.bell; (b[n] = b[n] || ['', ''])[+i.dataset.i] = i.value; });
      Object.keys(b).forEach(n => { if (!b[n][0] || !b[n][1]) delete b[n]; });
      S.school = await api('/api/school_set', {action: 'bells', bells: b}); toast('Đã lưu giờ tiết', 'ok'); render();
    }
    else if (a === 'dgrun') await runDiag();
    else if (a === 'dgfix') {
      const fix = el.dataset.fix, hs = el.dataset.hs ? JSON.parse(el.dataset.hs) : [];
      const t = {firewall: 'Mở cổng Agent trên tường lửa máy giáo viên?', time: `Đồng bộ giờ ${hs.length} máy?`, service: `Cài lại dịch vụ KhoaVeyon trên ${hs.length} máy?`}[fix];
      if (!await modal({title: t, ok: 'Sửa ngay', html: fix === 'firewall' ? 'Cần chạy KhoaVeyon bằng quyền quản trị.' : fix === 'time' ? 'Đặt múi giờ Việt Nam và đồng bộ giờ qua Internet.' : 'Chép bản mới và chạy -install.'})) return;
      const r = await api('/api/diagnose_fix', {fix, hosts: hs}); toast(r.msg || 'Xong', r.ok === false ? 'err' : 'ok');
      if (fix !== 'firewall') openLog();
      setTimeout(() => runDiag().catch(() => {}), fix === 'firewall' ? 300 : 15000);
    }
  } catch (err) { toast(err.message, 'err'); }
});
