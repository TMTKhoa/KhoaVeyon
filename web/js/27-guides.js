// Hướng dẫn thao tác cho học sinh: thư viện ảnh động + hướng dẫn tự tạo.
S.gd = S.gd || {items: null};

async function gdLoad() {
  try { S.gd.items = (await api('/api/guides', undefined, {quiet: true})).items; } catch (e) { S.gd.items = []; }
  if (S.page === 'interact') render();
}
function gdImg(g) { return g.img ? `<img src="${esc(g.img)}" alt="" loading="lazy" ${g.builtin ? '' : `data-gdimg="${esc(g.id)}"`} style="width:100%;border-radius:8px;display:block;background:#f1f5f9;aspect-ratio:16/9;object-fit:contain">` : '<div class="gdnoimg">Không có ảnh</div>'; }

function viewGuides() {
  if (!S.gd.items) { gdLoad(); return `<section class="card"><h3>📘 Hướng dẫn thao tác cho học sinh</h3><p class="sub">Đang tải...</p></section>`; }
  const cards = S.gd.items.map(g => `<div class="gdcard">${gdImg(g)}<b>${esc(g.title)}</b><div class="muted">${esc(g.keys || '')}</div>
      <div class="row" style="gap:6px;flex-wrap:wrap"><button class="btn sm primary" data-gd="send" data-id="${esc(g.id)}">📤 Gửi</button><button class="btn sm" data-gd="view" data-id="${esc(g.id)}">🔍 Xem lớn</button>${g.builtin ? '' : `<button class="btn sm ghost" data-gd="edit" data-id="${esc(g.id)}">✏</button><button class="btn sm ghost" data-gd="del" data-id="${esc(g.id)}">🗑</button>`}</div></div>`).join('');
  return `<section class="card"><h3>📘 Hướng dẫn thao tác cho học sinh</h3>
    <p class="sub">Gửi ảnh động và các bước làm (ví dụ phóng to / thu nhỏ bằng Ctrl + lăn chuột) tới máy học sinh. Học sinh xem lại được từ menu nút nổi → “Hướng dẫn thao tác...”. “Gửi” áp dụng cho các máy đang chọn (không chọn = tất cả, có hỏi lại).</p>
    <div class="gdgrid">${cards}</div>
    <div class="row" style="margin-top:10px"><button class="btn" data-gd="new">➕ Tạo hướng dẫn riêng (ảnh / GIF của bạn)</button></div></section>`;
}
async function gdSend(id, secs) {
  const hs = await resolveTargets(); if (!hs) return;
  await api('/api/guide_send', {id, hosts: hs, secs: secs || 0}); openLog(); toast('Đã gửi hướng dẫn tới ' + hs.length + ' máy', 'ok');
}
function gdFind(id) { return (S.gd.items || []).find(g => g.id === id); }
async function gdView(id) {
  const g = gdFind(id); if (!g) return;
  let img = g.img;
  if (!g.builtin && g.img) { try { img = (await api('/api/guide_img?id=' + encodeURIComponent(id), undefined, {quiet: true})).data; } catch (e) { img = ''; } }
  await modal({title: g.title, ok: 'Đóng', noCancel: true, html: `${img ? `<img src="${esc(img)}" style="max-width:100%;border-radius:10px">` : ''}${g.keys ? `<p><b>Phím:</b> ${esc(g.keys)}</p>` : ''}<ol>${g.steps.map(s => `<li>${esc(s)}</li>`).join('')}</ol>${g.tip ? `<p class="muted">Mẹo: ${esc(g.tip)}</p>` : ''}`});
}
async function gdEdit(id) {
  const g = id ? gdFind(id) : null;
  let imgData = '';
  const v = await modal({title: g ? 'Sửa hướng dẫn' : 'Tạo hướng dẫn riêng', ok: 'Lưu', html: `<div style="display:grid;gap:8px">
      <input type="text" id="gdT" maxlength="80" placeholder="Tiêu đề, ví dụ: Đổi cỡ chữ trong Word" value="${esc(g ? g.title : '')}">
      <input type="text" id="gdK" maxlength="60" placeholder="Phím tắt (tùy chọn), ví dụ: Ctrl + B" value="${esc(g ? g.keys : '')}">
      <textarea id="gdS" rows="5" placeholder="Mỗi dòng là một bước">${esc(g ? g.steps.join('\n') : '')}</textarea>
      <input type="text" id="gdP" maxlength="200" placeholder="Mẹo (tùy chọn)" value="${esc(g ? g.tip : '')}">
      <label class="muted">Ảnh hoặc GIF minh họa (dưới 3 MB) <input type="file" id="gdF" accept="image/gif,image/png,image/jpeg"></label></div>`,
    collect: r => ({title: r.querySelector('#gdT').value, keys: r.querySelector('#gdK').value, steps: r.querySelector('#gdS').value.split('\n').map(x => x.trim()).filter(Boolean), tip: r.querySelector('#gdP').value, file: r.querySelector('#gdF').files[0] || null})});
  if (!v) return;
  const body = {id: g ? g.id : '', title: v.title, keys: v.keys, steps: v.steps, tip: v.tip};
  if (v.file) body.image = await readB64(v.file);
  S.gd.items = (await api('/api/guide_save', body)).items; render(); toast('Đã lưu hướng dẫn', 'ok');
}
document.addEventListener('click', async e => {
  const el = e.target.closest('[data-gd]'); if (!el) return;
  e.preventDefault();
  try {
    const a = el.dataset.gd, id = el.dataset.id;
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
  const id = await modal({title: '📘 Gửi hướng dẫn thao tác', ok: 'Gửi', html: `<select id="mgG" style="width:100%">${S.gd.items.map(g => `<option value="${esc(g.id)}">${esc(g.title)}</option>`).join('')}</select>`, collect: r => r.querySelector('#mgG').value});
  if (id) await gdSend(id);
}
