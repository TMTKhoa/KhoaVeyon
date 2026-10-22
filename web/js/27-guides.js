// Hướng dẫn thao tác cho học sinh: thư viện ảnh động + hướng dẫn tự tạo.
S.gd = S.gd || {items: null, kid: null};
function gdKid() {
  if (S.gd.kid === null) {
    let v = null; try { v = localStorage.getItem('kv_gd_kid'); } catch (e) { /* bỏ qua */ }
    S.gd.kid = v === null ? /^[123](?!\d)/.test((S.mon && S.mon.cls) || '') : v === '1';   // chưa chọn: tự đoán theo lớp đang xem (lớp 1-3)
  }
  return S.gd.kid;
}
function gdSetKid(v) { S.gd.kid = v; try { localStorage.setItem('kv_gd_kid', v ? '1' : '0'); } catch (e) { /* bỏ qua */ } render(); }
function gdView_(g) { return gdKid() && g.kid ? Object.assign({}, g, g.kid, {img: g.builtin ? g.img.replace('.gif', 'kid.gif') : g.img}) : g; }

async function gdLoad() {
  try { S.gd.items = (await api('/api/guides', undefined, {quiet: true})).items; } catch (e) { S.gd.items = []; }
  if (S.page === 'interact') render();
}
function gdKeys(k) {
  if (!k) return '';
  return k.split(/\s*(\+|,)\s*/).filter(Boolean).map(t => t === '+' ? '<span class="gdplus">+</span>' : t === ',' ? '<span class="gdor">hoặc</span>' : `<kbd>${esc(t)}</kbd>`).join('');
}
function gdSteps(steps) { return `<div class="gdsteps">${steps.map((s, i) => `<div class="gdstep"><span class="gdn">${i + 1}</span><span>${esc(s)}</span></div>`).join('')}</div>`; }
function gdImg(g) { return g.img ? `<img src="${esc(g.img)}" alt="" loading="lazy" ${g.builtin ? '' : `data-gdimg="${esc(g.id)}"`} style="width:100%;border-radius:8px;display:block;background:#f1f5f9;aspect-ratio:16/9;object-fit:contain">` : '<div class="gdnoimg">Không có ảnh</div>'; }

function viewGuides() {
  if (!S.gd.items) { gdLoad(); return `<section class="card"><h3>📘 Hướng dẫn thao tác cho học sinh</h3><p class="sub">Đang tải...</p></section>`; }
  const kidOn = gdKid();
  const cards = S.gd.items.map(g0 => { const g = gdView_(g0); return `<div class="gdcard"><div class="gdimg" data-gd="view" data-id="${esc(g.id)}" title="Bấm để xem lớn">${gdImg(g)}${g.builtin ? '' : '<span class="gdtag">Của tôi</span>'}</div>
      <div class="gdtitle">${esc(g.title)}</div><div class="gdkeys">${gdKeys(g.keys)}</div>
      <div class="gdact"><button class="btn sm primary" data-gd="send" data-id="${esc(g.id)}">📤 Gửi cho lớp</button>${g.builtin ? '' : `<button class="btn sm ghost" data-gd="edit" data-id="${esc(g.id)}" title="Sửa">✏</button><button class="btn sm ghost" data-gd="del" data-id="${esc(g.id)}" title="Xóa">🗑</button>`}</div></div>`; }).join('');
  return `<section class="card"><h3>📘 Hướng dẫn thao tác cho học sinh</h3>
    <p class="sub">Gửi ảnh động và các bước làm (ví dụ phóng to / thu nhỏ bằng Ctrl + lăn chuột) tới máy học sinh. Học sinh xem lại được từ menu nút nổi → “Hướng dẫn thao tác...”. “Gửi” áp dụng cho các máy đang chọn (không chọn = tất cả, có hỏi lại).</p>
    <div class="row" style="gap:10px;flex-wrap:wrap;align-items:center;margin:4px 0 12px"><b>Dành cho:</b>
      <div class="seg"><button class="btn sm ${kidOn ? '' : 'primary'}" data-gd="lv0">Học sinh lớn (lớp 4 trở lên)</button><button class="btn sm ${kidOn ? 'primary' : ''}" data-gd="lv1">🧒 Lớp nhỏ (lớp 1–3): câu ngắn, chữ to, đọc thành tiếng</button></div></div>
    <div class="gdgrid">${cards}</div>
    <div class="row" style="margin-top:10px"><button class="btn" data-gd="new">➕ Tạo hướng dẫn riêng (ảnh / GIF của bạn)</button></div></section>`;
}
async function gdSend(id, secs) {
  const hs = await resolveTargets(); if (!hs) return;
  await api('/api/guide_send', {id, hosts: hs, secs: secs || 0, kid: gdKid()}); openLog(); toast('Đã gửi hướng dẫn tới ' + hs.length + ' máy', 'ok');
}
function gdFind(id) { return (S.gd.items || []).find(g => g.id === id); }
async function gdView(id) {
  const g0 = gdFind(id); if (!g0) return;
  const g = gdView_(g0);
  let img = g.img;
  if (!g.builtin && g.img) { try { img = (await api('/api/guide_img?id=' + encodeURIComponent(id), undefined, {quiet: true})).data; } catch (e) { img = ''; } }
  await modal({title: g.title, ok: '📤 Gửi cho lớp', cancel: 'Đóng', html: `<div class="gdview">${img ? `<img src="${esc(img)}" class="gdbig">` : ''}${g.keys ? `<div class="gdkeys" style="margin:10px 0">${gdKeys(g.keys)}</div>` : ''}${gdSteps(g.steps)}${g.tip ? `<div class="gdtip">✨ Mẹo: ${esc(g.tip)}</div>` : ''}</div>`}).then(ok => ok && gdSend(id));
}
async function gdEdit(id) {
  const g = id ? gdFind(id) : null;
  let imgData = '';
  const v = await modal({title: g ? 'Sửa hướng dẫn' : 'Tạo hướng dẫn riêng', ok: 'Lưu', html: `<div style="display:grid;gap:8px">
      <input type="text" id="gdT" maxlength="80" placeholder="Tiêu đề, ví dụ: Đổi cỡ chữ trong Word" value="${esc(g ? g.title : '')}">
      <input type="text" id="gdK" maxlength="60" placeholder="Phím tắt (tùy chọn), ví dụ: Ctrl + B" value="${esc(g ? g.keys : '')}">
      <textarea id="gdS" rows="5" placeholder="Mỗi dòng là một bước">${esc(g ? g.steps.join('\n') : '')}</textarea>
      <input type="text" id="gdP" maxlength="200" placeholder="Mẹo (tùy chọn)" value="${esc(g ? g.tip : '')}">
      <details><summary class="muted">🧒 Bản cho lớp nhỏ (tùy chọn): câu ngắn, từ dễ hiểu</summary><div style="display:grid;gap:8px;margin-top:6px"><input type="text" id="gdKT" maxlength="80" placeholder="Tiêu đề ngắn gọn" value="${esc(g && g.kid && g.kid.title !== g.title ? g.kid.title : '')}">
        <textarea id="gdKS" rows="4" placeholder="Mỗi dòng một bước, viết thật ngắn">${esc(g && g.kid && g.kid.steps.join('|') !== g.steps.join('|') ? g.kid.steps.join('\n') : '')}</textarea></div></details>
      <label class="muted">Ảnh hoặc GIF minh họa (dưới 3 MB) <input type="file" id="gdF" accept="image/gif,image/png,image/jpeg"></label></div>`,
    collect: r => ({title: r.querySelector('#gdT').value, keys: r.querySelector('#gdK').value, steps: r.querySelector('#gdS').value.split('\n').map(x => x.trim()).filter(Boolean), tip: r.querySelector('#gdP').value, kid_title: r.querySelector('#gdKT').value, kid_steps: r.querySelector('#gdKS').value.split('\n').map(x => x.trim()).filter(Boolean), file: r.querySelector('#gdF').files[0] || null})});
  if (!v) return;
  const body = {id: g ? g.id : '', title: v.title, keys: v.keys, steps: v.steps, tip: v.tip, kid_title: v.kid_title, kid_steps: v.kid_steps};
  if (v.file) body.image = await readB64(v.file);
  S.gd.items = (await api('/api/guide_save', body)).items; render(); toast('Đã lưu hướng dẫn', 'ok');
}
document.addEventListener('click', async e => {
  const el = e.target.closest('[data-gd]'); if (!el) return;
  e.preventDefault();
  try {
    const a = el.dataset.gd, id = el.dataset.id;
    if (a === 'lv0') return gdSetKid(false);
    if (a === 'lv1') return gdSetKid(true);
    if (a === 'send') await gdSend(id);
    else if (a === 'view') await gdView(id);
    else if (a === 'new') await gdEdit('');
    else if (a === 'edit') await gdEdit(id);
    else if (a === 'del') { if (!await modal({title: 'Xóa hướng dẫn này?', ok: 'Xóa', danger: true, html: esc((gdFind(id) || {}).title || '')})) return; S.gd.items = (await api('/api/guide_delete', {id})).items; render(); }
  } catch (err) { toast(err.message, 'err'); }
});
// ảnh của hướng dẫn riêng: nạp qua API (có mã bảo vệ), không dùng đường dẫn trực tiếp
document.addEventListener('error', e => { /* bỏ qua ảnh lỗi */ }, true);
async function gdFillImgs() {
  for (const im of document.querySelectorAll('img[data-gdimg]:not([data-done])')) {
    im.dataset.done = '1';
    try { im.src = (await api('/api/guide_img?id=' + encodeURIComponent(im.dataset.gdimg), undefined, {quiet: true})).data; } catch (err) { /* bỏ qua */ }
  }
}
new MutationObserver(() => { if (document.querySelector('img[data-gdimg]:not([data-done])')) gdFillImgs(); }).observe(document.documentElement, {childList: true, subtree: true});

async function monGuide() {
  if (!S.gd.items) { try { S.gd.items = (await api('/api/guides', undefined, {quiet: true})).items; } catch (e) { S.gd.items = []; } }
  const id = await modal({title: '📘 Gửi hướng dẫn thao tác', ok: 'Gửi', html: `<select id="mgG" style="width:100%">${S.gd.items.map(g => `<option value="${esc(g.id)}">${esc(g.title)}</option>`).join('')}</select>
      <label class="switch" style="margin-top:10px"><input type="checkbox" id="mgK" ${gdKid() ? 'checked' : ''}><span class="tr"></span><span>🧒 Bản cho lớp nhỏ (lớp 1–3): câu ngắn, chữ to</span></label>`,
    collect: r => ({id: r.querySelector('#mgG').value, kid: r.querySelector('#mgK').checked})});
  if (id) { S.gd.kid = id.kid; try { localStorage.setItem('kv_gd_kid', id.kid ? '1' : '0'); } catch (e) { /* bỏ qua */ } await gdSend(id.id); }
}
