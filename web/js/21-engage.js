// KhoaVeyon - Bốc thăm gọi tên và hình nền máy học sinh
S.wall = {presets: {}, bgs: [], loaded: false};
S.wspec = {title: 'Tiết học', sub: '', c1: '#1d4ed8', c2: '#0ea5e9', bg: '', seat: true, lock: false, dim: 35};
S.wbgData = '';   // ảnh nền đang xem trước (data URL), chỉ để vẽ xem trước

async function loadWall() { try { Object.assign(S.wall, await api('/api/wall', undefined, {quiet: true}), {loaded: true}); } catch (e) { /* bỏ qua */ } }

function viewEngage() {
  if (!S.wall.loaded) { loadWall().then(() => { if (S.page === 'interact') render(); }); }
  const w = S.wspec, names = Object.keys(S.wall.presets || {});
  return `<section class="card"><h3>🎲 Bốc thăm gọi tên</h3>
      <p class="sub">Chọn ngẫu nhiên một em đang có mặt trong sơ đồ chỗ ngồi của lớp (bỏ qua em vắng và máy tắt); tên em hiện lên máy của em đó. Mỗi vòng không gọi trùng cho đến khi hết lớp.</p>
      <div class="row"><button class="btn primary" data-ev="draw">🎲 Bốc thăm</button></div></section>
    <section class="card"><h3>🖼 Hình nền máy học sinh</h3>
      <p class="sub">Vẽ hình nền có tiêu đề, số máy và tên em đang ngồi, gửi tới các máy đang chọn (không chọn = tất cả). Có thể gắn mẫu vào từng chế độ ở trang Tự động để đầu tiết tự đổi, hết tiết tự trả lại hình nền cũ của em.</p>
      <div class="row" style="flex-wrap:wrap;align-items:flex-start">
        <div style="flex:1;min-width:260px"><canvas id="wallPrev" class="wallprev" width="640" height="360"></canvas></div>
        <div style="flex:1;min-width:260px;display:grid;gap:8px">
          <label class="muted">Mẫu đã lưu <select id="wPreset" class="xsel"><option value="">(chọn để nạp)</option>${names.map(n => `<option>${esc(n)}</option>`).join('')}</select></label>
          <input type="text" id="wTitle" placeholder="Tiêu đề, ví dụ: Tin học 10" value="${esc(w.title)}" maxlength="60">
          <input type="text" id="wSub" placeholder="Dòng phụ (để trống = Lớp ...)" value="${esc(w.sub)}" maxlength="80">
          <div class="row">Màu <input type="color" id="wC1" value="${esc(w.c1)}"> → <input type="color" id="wC2" value="${esc(w.c2)}">
            <button class="btn sm ghost" data-ev="wallpic">Chọn ảnh nền...</button>${w.bg ? '<button class="btn sm ghost" data-ev="wallnopic">Bỏ ảnh</button>' : ''}</div>
          <label class="muted">Làm tối ảnh <input type="range" id="wDim" min="0" max="80" value="${w.dim}"></label>
          <label class="switch"><input type="checkbox" id="wSeat" ${w.seat ? 'checked' : ''}><span class="tr"></span><span>In số máy và tên em ngồi</span></label>
          <label class="switch"><input type="checkbox" id="wLock" ${w.lock ? 'checked' : ''}><span class="tr"></span><span>Khóa, không cho em đổi hình nền</span></label>
        </div></div>
      <div class="row" style="flex-wrap:wrap;margin-top:8px">
        <button class="btn primary" data-ev="wallapply">🖼 Đổi hình nền</button>
        <button class="btn" data-ev="wallrestore">↩ Trả hình nền cũ</button>
        <button class="btn ghost" data-ev="wallsave">💾 Lưu thành mẫu</button>
        ${names.length ? '<button class="btn ghost" data-ev="walldel">🗑 Xóa mẫu đang chọn</button>' : ''}
      </div></section>`;
}

const wImgCache = {};
function wallDraw() {
  const cv = $('#wallPrev'); if (!cv) return;
  const w = S.wspec, g = cv.getContext('2d'), W = cv.width, H = cv.height;
  const paint = img => {
    if (img) {
      const sc = Math.max(W / img.width, H / img.height); g.drawImage(img, (W - img.width * sc) / 2, (H - img.height * sc) / 2, img.width * sc, img.height * sc);
      g.fillStyle = `rgba(0,0,0,${w.dim / 100})`; g.fillRect(0, 0, W, H);
    } else { const gr = g.createLinearGradient(0, 0, W, H); gr.addColorStop(0, w.c1); gr.addColorStop(1, w.c2); g.fillStyle = gr; g.fillRect(0, 0, W, H); }
    g.fillStyle = '#fff'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.font = 'bold 36px Segoe UI, sans-serif'; g.fillText(w.title, W / 2, H * 0.30);
    g.font = '20px Segoe UI, sans-serif'; g.fillText(w.sub || 'Lớp 10A1', W / 2, H * 0.30 + 42);
    if (w.seat) { g.fillStyle = 'rgba(0,0,0,.55)'; g.fillRect(W - 290, H - 130, 270, 80); g.fillStyle = '#fff'; g.font = 'bold 26px Segoe UI, sans-serif'; g.fillText('Nguyễn Văn A', W - 155, H - 105); g.font = '16px Segoe UI, sans-serif'; g.fillText('Máy số 12', W - 155, H - 70); }
  };
  if (S.wbgData) { const k = S.wbgData; if (wImgCache[k]) paint(wImgCache[k]); else { const im = new Image(); im.onload = () => { wImgCache[k] = im; paint(im); }; im.src = k; } } else paint(null);
}
setInterval(() => { if (S.page === 'interact' && $('#wallPrev')) wallDraw(); }, 700);

function wallRead() {
  const v = id => ($('#' + id) || {}).value;
  Object.assign(S.wspec, {title: v('wTitle') || '', sub: v('wSub') || '', c1: v('wC1') || S.wspec.c1, c2: v('wC2') || S.wspec.c2, dim: +(v('wDim') || 35),
    seat: !!($('#wSeat') || {}).checked, lock: !!($('#wLock') || {}).checked});
  return Object.assign({}, S.wspec);
}

function pickImageDownscaled() {
  return new Promise((resolve, reject) => {
    const inp = document.createElement('input'); inp.type = 'file'; inp.accept = 'image/*';
    inp.onchange = () => {
      const f = inp.files[0]; if (!f) return resolve(null);
      const im = new Image(), url = URL.createObjectURL(f);
      im.onload = () => {
        const sc = Math.min(1, 1920 / im.width, 1080 / im.height), c = document.createElement('canvas');
        c.width = Math.round(im.width * sc); c.height = Math.round(im.height * sc); c.getContext('2d').drawImage(im, 0, 0, c.width, c.height);
        URL.revokeObjectURL(url); resolve(c.toDataURL('image/jpeg', 0.82));
      };
      im.onerror = () => reject(new Error('Không đọc được ảnh'));
      im.src = url;
    };
    inp.click();
  });
}

/* ---------- Bốc thăm ---------- */
async function doDraw(opts) {
  const root = $('#modalroot');
  const repeat = !!(opts && opts.repeat);
  let r;
  try { r = await api('/api/draw', {cls: S.seatCls || '', repeat, send: true}); } catch (err) { toast(err.message, 'err'); return; }
  const names = r.names.length > 1 ? r.names : [r.name, r.name];
  let stop = false;
  root.innerHTML = `<div class="drawbg"><div class="drawbox"><div class="muted">Lớp ${esc(r.cls)}</div><div class="big roll" id="drawName">...</div><div class="muted" id="drawInfo">&nbsp;</div>
    <div class="row" style="justify-content:center;margin-top:16px"><label class="muted"><input type="checkbox" id="drawRep" ${repeat ? 'checked' : ''}> cho phép gọi lại em đã gọi</label></div>
    <div class="row" style="justify-content:center;margin-top:12px"><button class="btn primary" id="drawAgain" disabled>🎲 Bốc tiếp</button><button class="btn" id="drawClose">Đóng</button></div></div></div>`;
  const close = () => { stop = true; root.innerHTML = ''; S.drawNo = 0; if (S.page === 'seats') render(); };
  $('#drawClose').onclick = close;
  $('#drawAgain').onclick = () => { const rep = $('#drawRep').checked; stop = true; doDraw({repeat: rep}); };
  const t0 = Date.now(); let i = 0;
  const tick = () => {
    if (stop) return;
    const el = $('#drawName'); if (!el) return;
    if (Date.now() - t0 < 2200) { el.textContent = names[i++ % names.length]; setTimeout(tick, 70 + (Date.now() - t0) / 14); return; }
    el.textContent = r.name; el.classList.remove('roll');
    $('#drawInfo').innerHTML = `Máy số ${r.no} · còn ${r.left} em chưa được gọi${r.new_round ? ' · <b>bắt đầu vòng mới</b>' : ''}${r.host ? '' : ' · máy này chưa có trong danh sách'}`;
    $('#drawAgain').disabled = false;
    S.drawNo = r.no; if (S.page === 'seats') render();
    ding();
  };
  tick();
}

document.addEventListener('click', async e => {
  const el = e.target.closest('[data-ev]'); if (!el) return;
  e.preventDefault();
  const a = el.dataset.ev;
  try {
    if (a === 'draw') await doDraw();
    else if (a === 'wallpic') {
      const data = await pickImageDownscaled(); if (!data) return;
      const r = await api('/api/wall_bg', {data: data.split(',')[1]});
      wallRead(); S.wspec.bg = r.id; S.wbgData = data; render();
    }
    else if (a === 'wallnopic') { wallRead(); S.wspec.bg = ''; S.wbgData = ''; render(); }
    else if (a === 'wallapply') {
      const spec = wallRead(), hs = await resolveTargets(); if (!hs) return;
      await api('/api/wall_apply', {hosts: hs, spec}); openLog(); toast('Đang đổi hình nền ' + hs.length + ' máy', 'ok');
    }
    else if (a === 'wallrestore') {
      const hs = await resolveTargets(); if (!hs) return;
      await api('/api/wall_restore', {hosts: hs}); openLog(); toast('Đang trả hình nền cũ', 'ok');
    }
    else if (a === 'wallsave') {
      const spec = wallRead();
      const name = await modal({title: 'Lưu mẫu hình nền', ok: 'Lưu', html: '<input type="text" id="wName" style="width:100%" maxlength="40" placeholder="Tên mẫu, ví dụ: Giờ thực hành">', collect: r => r.querySelector('#wName').value.trim()});
      if (!name) return;
      Object.assign(S.wall, await api('/api/wall_preset_save', {name, spec})); render(); toast('Đã lưu mẫu', 'ok');
    }
    else if (a === 'walldel') {
      const n = ($('#wPreset') || {}).value; if (!n) { toast('Chọn mẫu cần xóa ở ô “Mẫu đã lưu”', 'warn'); return; }
      if (!await modal({title: 'Xóa mẫu “' + n + '”?', ok: 'Xóa', danger: true, html: 'Chế độ tự động đang dùng mẫu này sẽ không đổi hình nền nữa.'})) return;
      Object.assign(S.wall, await api('/api/wall_preset_delete', {name: n})); render();
    }
  } catch (err) { toast(err.message, 'err'); }
});
document.addEventListener('change', e => {
  const t = e.target;
  if (t.id === 'wPreset' && t.value) {
    const p = S.wall.presets[t.value]; if (!p) return;
    Object.assign(S.wspec, p); S.wbgData = '';
    if (p.bg) api('/api/wall_img?id=' + p.bg).then(r => { S.wbgData = r.data; wallDraw(); }).catch(() => {});
    render();
  } else if (['wTitle', 'wSub', 'wC1', 'wC2', 'wDim', 'wSeat', 'wLock'].includes(t.id)) { wallRead(); wallDraw(); }
});
document.addEventListener('input', e => { if (['wTitle', 'wSub', 'wC1', 'wC2', 'wDim'].includes(e.target.id)) { wallRead(); wallDraw(); } });
