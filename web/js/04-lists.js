// KhoaVeyon - Trang các danh sách Excel
/* ---------- trang: danh sách Excel ---------- */
async function loadList(kind) {
  const r = await api('/api/list?kind=' + kind);
  S.lists[kind] = {rows: r.rows.map(x => ({a: x[0], b: x[1]})), warn: Object.fromEntries(r.warnings.map(w => [w.row, w.msg])), dirty: false, path: r.path, exists: r.exists, filter: '', variants: r.variants || []};
}

function viewList(kind) {
  const L = S.lists[kind], m = S.st.lists[kind];
  const presets = Object.keys(m.presets).map(n => `<button class="chip" data-act="preset" data-name="${esc(n)}">+ ${esc(n)}</button>`).join('');
  const rows = L.rows.map((r, i) => `<tr data-i="${i}"><td class="num">${i + 1}</td>
      <td><input type="text" class="cell" data-f="a" data-i="${i}" value="${esc(r.a)}" placeholder="${esc(m.col_a)}" spellcheck="false"></td>
      <td><input type="text" class="cell" data-f="b" data-i="${i}" value="${esc(r.b)}" placeholder="Ghi chú (không bắt buộc)"></td>
      <td class="act"><span class="warnslot" data-i="${i}">${warnHtml(L.warn[i])}</span><button class="iconbtn" title="Lên" data-act="up" data-i="${i}">↑</button><button class="iconbtn" title="Xuống" data-act="down" data-i="${i}">↓</button><button class="iconbtn del" title="Xóa dòng" data-act="delrow" data-i="${i}">✕</button></td></tr>`).join('');
  const t = targets();
  const pushInfo = S.st.cfg.auto_push
    ? `Khi lưu, file sẽ tự gửi xuống <b>${t.all ? 'tất cả ' + t.hosts.length : t.hosts.length}</b> máy học sinh${S.hosts.length ? '' : ' (chưa có máy nào)'}.`
    : 'Tự gửi file xuống máy học sinh đang tắt (bật ở trang Phân phối & chạy).';
  return `<div class="stack">
    <div class="note">${esc(m.hint)}</div>
    ${kind === 'ai' ? aiOptsCard() : ''}
    <section class="card">
      <div class="toolbar">
        <input type="search" class="grow" id="filter" placeholder="Tìm trong danh sách..." value="${esc(L.filter)}">
        <button class="btn primary" data-act="addrow">＋ Thêm dòng</button>
        <button class="btn" data-act="paste">📋 Dán nhiều dòng</button>
        <button class="btn ghost" data-act="reload">↻ Tải lại</button>
      </div>
      <div class="toolbar"><span class="muted">Bản riêng:</span><select class="xsel" id="variantSel" style="width:auto;min-width:220px"><option value="">(chọn một bản)</option>${(L.variants || []).map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join('')}</select><button class="btn sm ghost" data-act="variantload">Tải vào bảng</button><button class="btn sm ghost" data-act="variantsave">Lưu bảng thành bản riêng…</button><button class="btn sm ghost" data-act="variantdel">Xóa bản đã chọn</button></div>
      ${presets ? `<div class="toolbar"><span class="muted">Thêm nhanh:</span><div class="chips">${presets}</div></div>` : ''}
      ${L.rows.length ? `<table class="tbl"><thead><tr><th>#</th><th>${esc(m.col_a)}</th><th>Ghi chú</th><th></th></tr></thead><tbody id="rows">${rows}</tbody></table>`
        : `<div class="empty">Danh sách đang trống.<br>Bấm "Thêm dòng", "Dán nhiều dòng" hoặc chọn một nhóm có sẵn ở trên.</div>`}
    </section>
    <div class="savebar">
      <div class="grow"><span id="dirtyTxt">${L.dirty ? '<span class="dirty">● Có thay đổi chưa lưu</span>' : '<span class="muted">Đã lưu</span>'}</span><br><span class="hint">${pushInfo}<br>File: ${esc(L.path)}</span></div>
      <button class="btn" data-act="save">💾 Lưu</button>
      <button class="btn primary" data-act="saveapply">▶ Lưu và áp dụng (${esc(m.apply_label)})</button>
    </div>
  </div>`;
}

function warnHtml(w) { return w ? `<span class="warnmark" title="${esc(w)}">⚠</span>` : ''; }

function markDirty(kind) {
  S.lists[kind].dirty = true;
  const el = $('#dirtyTxt'); if (el) el.innerHTML = '<span class="dirty">● Có thay đổi chưa lưu</span>';
}

let checkTimer = null;
function scheduleCheck(kind) {
  clearTimeout(checkTimer);
  checkTimer = setTimeout(async () => {
    try {
      const L = S.lists[kind];
      const r = await api('/api/check', {kind, rows: L.rows.map(x => [x.a, x.b])});
      L.warn = Object.fromEntries(r.warnings.map(w => [w.row, w.msg]));
      document.querySelectorAll('.warnslot').forEach(el => { el.innerHTML = warnHtml(L.warn[el.dataset.i]); });
    } catch (e) { /* bỏ qua */ }
  }, 350);
}

function applyFilter(kind) {
  const L = S.lists[kind], q = L.filter.trim().toLowerCase();
  document.querySelectorAll('#rows tr').forEach(tr => {
    const r = L.rows[tr.dataset.i];
    tr.classList.toggle('hidden', !!q && !((r.a + ' ' + r.b).toLowerCase().includes(q)));
  });
}

function addRows(kind, items) {
  const L = S.lists[kind], have = new Set(L.rows.map(r => r.a.toLowerCase()));
  let n = 0;
  for (const [a, b] of items) {
    if (a && !have.has(a.toLowerCase())) { L.rows.push({a, b: b || ''}); have.add(a.toLowerCase()); n++; }
  }
  if (n) { markDirty(kind); scheduleCheck(kind); }
  return n;
}

async function saveList(kind, apply) {
  const L = S.lists[kind], m = S.st.lists[kind];
  let hosts;
  if (apply) {
    hosts = await resolveTargets(); if (!hosts) return;
    if (!(await confirmRisky(action(m.apply), hosts.length))) return;
  } else {
    hosts = targets().hosts;
  }
  try {
    const r = await api('/api/list', {kind, rows: L.rows.map(x => [x.a.trim(), x.b.trim()]), hosts, apply: !!apply});
    L.rows = L.rows.filter(x => x.a.trim()).map(x => ({a: x.a.trim(), b: x.b.trim()}));
    L.warn = Object.fromEntries(r.warnings.map(w => [w.row, w.msg]));
    L.dirty = false; L.exists = true;
    let msg = `Đã lưu ${r.count} dòng`;
    if (r.pushed) msg += `, đang gửi xuống ${r.pushed} máy`;
    if (r.applied) msg += `, đang áp dụng lệnh`;
    toast(msg, 'ok');
    if (r.warnings.length) toast(`${r.warnings.length} dòng có thể bị script bỏ qua (xem dấu ⚠)`, 'warn');
    if (r.pushed || r.applied) openLog();
    render();
  } catch (e) { toast(e.message, 'err'); }
}

/* Tùy chọn khóa AI (chặn AI Overviews, tắt DoH, chặn extension) — áp dụng ở lần "Khóa toàn bộ công cụ AI" tiếp theo */
function aiOptsCard() {
  const c = S.st.cfg;
  const sw = (k, label, on) => `<label class="switch" style="margin:4px 0"><input type="checkbox" data-aiopt="${k}" ${on ? 'checked' : ''}><span class="tr"></span><span>${label}</span></label>`;
  return `<section class="card"><h3>Khi bấm “Khóa toàn bộ công cụ AI”, làm thêm</h3>
    ${sw('ai_block_overviews', 'Chặn <b>AI Overviews</b> trong Google Search: ép công cụ tìm kiếm mặc định về bộ lọc “Web” (udm=14, không có khung AI) trên Chrome/Edge. <i>Lưu ý: nếu học sinh tự vào google.com rồi tìm thì khung AI vẫn có thể hiện — chỉ “Chỉ trang cho phép” mới bỏ hẳn.</i>', c.ai_block_overviews !== false)}
    ${sw('ai_disable_doh', 'Tắt <b>DNS-over-HTTPS</b> của trình duyệt, để chặn bằng file hosts không bị lách bằng DNS mã hóa', c.ai_disable_doh !== false)}
    ${sw('ai_block_ext', 'Chặn <b>mọi extension</b> trình duyệt (Chrome/Edge/Brave) — tắt hết, không chỉ extension AI. Cân nhắc vì sẽ tắt cả extension học tập', !!c.ai_block_ext)}
    <div class="row" style="margin-top:8px"><button class="btn primary" data-act="aioptsave">💾 Lưu tùy chọn và gửi xuống máy</button><span class="muted" id="aiOptMsg"></span></div>
    <p class="hint" style="margin-bottom:0">Ba tùy chọn này ghi vào <code>ai_opts.txt</code> cạnh các file Excel và gửi xuống máy học sinh. AI Overviews và tắt DoH <b>mặc định bật</b>; chặn extension mặc định tắt. Có hiệu lực ở lần bấm <b>Khóa toàn bộ công cụ AI</b> tiếp theo.</p></section>`;
}
