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
          <label class="muted">Lấy tên theo sơ đồ lớp <select id="wCls" class="xsel"><option value="">(lớp đang có tiết)</option>${((S.school || {}).classes || []).map(c => `<option ${c === S.wcls ? 'selected' : ''}>${esc(c)}</option>`).join('')}</select></label>
          <input type="text" id="wTitle" placeholder="Tiêu đề, ví dụ: Tin học 10" value="${esc(w.title)}" maxlength="60">
          <input type="text" id="wSub" placeholder="Dòng phụ (để trống = Lớp ...)" value="${esc(w.sub)}" maxlength="80">
          <div class="row">Màu <input type="color" id="wC1" value="${esc(w.c1)}"> → <input type="color" id="wC2" value="${esc(w.c2)}">
            <button class="btn sm ghost" data-ev="wallpic">Chọn ảnh nền...</button>${w.bg ? '<button class="btn sm ghost" data-ev="wallnopic">Bỏ ảnh</button>' : ''}</div>
          <label class="muted">Làm tối ảnh <input type="range" id="wDim" min="0" max="80" value="${w.dim}"></label>
          <label class="switch"><input type="checkbox" id="wSeat" ${w.seat ? 'checked' : ''}><span class="tr"></span><span>In số máy và tên em ngồi</span></label>
          <label class="switch"><input type="checkbox" id="wFollow" ${S.wfollow ? 'checked' : ''}><span class="tr"></span><span>Tự đổi theo tiết: sang lớp khác thì đổi tên lớp và tên em, hết tiết thì trả hình nền cũ</span></label>
          <div class="muted" style="font-size:12.5px">Trong tiêu đề / dòng phụ có thể gõ <code>{lop}</code> (lớp đang có tiết), <code>{ten}</code> (tên em), <code>{may}</code> (số máy). Để trống dòng phụ = “Lớp ...” tự đổi theo tiết.</div>
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
function tickSnd() {
  try { interactBeep = interactBeep || new (window.AudioContext || window.webkitAudioContext)(); const o = interactBeep.createOscillator(), g = interactBeep.createGain(); o.type = 'square'; o.frequency.value = 520 + Math.random() * 300; g.gain.value = 0.03; o.connect(g); g.connect(interactBeep.destination); o.start(); o.stop(interactBeep.currentTime + 0.04); } catch (e) { /* bỏ qua */ }
}
function fanfare() {
  try {
    interactBeep = interactBeep || new (window.AudioContext || window.webkitAudioContext)();
    [523, 659, 784, 1047].forEach((f, k) => { const o = interactBeep.createOscillator(), g = interactBeep.createGain(); o.frequency.value = f; g.gain.value = 0.07; o.connect(g); g.connect(interactBeep.destination); const t = interactBeep.currentTime + k * 0.13; o.start(t); o.stop(t + 0.18); });
  } catch (e) { /* bỏ qua */ }
}
async function doDraw(opts) {
  const root = $('#modalroot');
  const repeat = !!(opts && opts.repeat);
  let r;
  S.drawOpt = S.drawOpt || {announce: true, hide: false, sound: true};
  try { r = await api('/api/draw', {cls: S.seatCls || '', repeat, send: true, announce: S.drawOpt.announce, hide_name: S.drawOpt.hide}); } catch (err) { toast(err.message, 'err'); return; }
  const names = r.names.length > 1 ? r.names : [r.name, r.name];
  let stop = false;
  root.innerHTML = `<div class="drawbg"><div class="drawbox"><div class="muted">Lớp ${esc(r.cls)}</div><div class="big roll" id="drawName">...</div><div class="muted" id="drawInfo">&nbsp;</div>
    <div class="row" style="justify-content:center;margin-top:16px;flex-wrap:wrap;gap:12px"><label class="muted"><input type="checkbox" id="drawRep" ${repeat ? 'checked' : ''}> gọi lại em đã gọi</label><label class="muted"><input type="checkbox" id="drawAnn" ${S.drawOpt.announce ? 'checked' : ''}> báo cả lớp</label><label class="muted"><input type="checkbox" id="drawHide" ${S.drawOpt.hide ? 'checked' : ''}> chỉ nêu số máy</label><label class="muted"><input type="checkbox" id="drawSnd" ${S.drawOpt.sound ? 'checked' : ''}> âm thanh</label></div>
    <div class="row" style="justify-content:center;margin-top:12px"><button class="btn primary" id="drawAgain" disabled>🎲 Bốc tiếp</button><button class="btn" id="drawStar" disabled>⭐ Trả lời đúng: tặng sao</button><button class="btn" id="drawFull">⛶ Toàn màn hình</button><button class="btn" id="drawClose">Đóng</button></div></div></div>`;
  const close = () => { stop = true; root.innerHTML = ''; S.drawNo = 0; if (S.page === 'seats') render(); };
  $('#drawClose').onclick = () => { try { if (document.fullscreenElement) document.exitFullscreen(); } catch (e) { /* bỏ qua */ } close(); };
  const sync = () => { S.drawOpt = {announce: $('#drawAnn').checked, hide: $('#drawHide').checked, sound: $('#drawSnd').checked}; };
  ['drawAnn', 'drawHide', 'drawSnd'].forEach(id => { $('#' + id).onchange = sync; });
  $('#drawFull').onclick = () => { try { const e = root.firstElementChild; if (document.fullscreenElement) document.exitFullscreen(); else e.requestFullscreen(); } catch (e) { /* bỏ qua */ } };
  $('#drawStar').onclick = async () => { try { await api('/api/star', {hosts: [r.host], text: 'Em trả lời đúng rồi!', cls: r.cls}); S.fun && (S.fun.board = null, S.fun.boardCls = ''); $('#drawStar').disabled = true; toast('⭐ Đã tặng sao cho ' + r.name, 'ok'); } catch (err) { toast(err.message, 'err'); } };
  $('#drawAgain').onclick = () => { const rep = $('#drawRep').checked; stop = true; doDraw({repeat: rep}); };
  const t0 = Date.now(); let i = 0;
  const tick = () => {
    if (stop) return;
    const el = $('#drawName'); if (!el) return;
    if (Date.now() - t0 < 2200) { el.textContent = ($('#drawHide') && $('#drawHide').checked) ? 'Máy ?' : names[i++ % names.length]; if (S.drawOpt.sound) tickSnd(); setTimeout(tick, 70 + (Date.now() - t0) / 14); return; }
    el.textContent = S.drawOpt.hide ? 'Máy số ' + r.no : r.name; el.classList.remove('roll'); $('#drawStar').disabled = !r.host;
    $('#drawInfo').innerHTML = `Máy số ${r.no} · còn ${r.left} em chưa được gọi${r.new_round ? ' · <b>bắt đầu vòng mới</b>' : ''}${r.host ? '' : ' · máy này chưa có trong danh sách'}`;
    $('#drawAgain').disabled = false;
    S.drawNo = r.no; if (S.page === 'seats') render();
    if (S.drawOpt.sound) fanfare(); else ding();
  };
  tick();
}

document.addEventListener('click', async e => {
  const el = e.target.closest('[data-ev]'); if (!el || el.type === 'checkbox') return;
  e.preventDefault();
  const a = el.dataset.ev;
  try {
    if (a === 'draw') await doDraw();
    else if (a === 'lockstyle') await lockStyleDialog();
    else if (a === 'lockpic') {
      const data = await pickImageDownscaled(); if (!data) return;
      const r = await api('/api/wall_bg', {data: data.split(',')[1]}); S.lockSpec.bg = r.id; const lb = $('#lkBg'); if (lb) lb.textContent = 'Đã chọn ảnh';
    }
    else if (a === 'lockpicclr') { S.lockSpec.bg = ''; const lb = $('#lkBg'); if (lb) lb.textContent = 'Không dùng ảnh'; }
    else if (a === 'wallpic') {
      const data = await pickImageDownscaled(); if (!data) return;
      const r = await api('/api/wall_bg', {data: data.split(',')[1]});
      wallRead(); S.wspec.bg = r.id; S.wbgData = data; render();
    }
    else if (a === 'wallnopic') { wallRead(); S.wspec.bg = ''; S.wbgData = ''; render(); }
    else if (a === 'wallapply') {
      const spec = wallRead(), hs = await resolveTargets(); if (!hs) return;
      S.wfollow = !!($('#wFollow') || {}).checked;
      await api('/api/wall_apply', {hosts: hs, spec, follow: S.wfollow, cls: ($('#wCls') || {}).value || ''}); openLog(); toast('Đang đổi hình nền ' + hs.length + ' máy', 'ok');
    }
    else if (a === 'wallrestore') {
      const hs = await resolveTargets(); if (!hs) return;
      S.wfollow = false; await api('/api/wall_restore', {hosts: hs}); openLog(); toast('Đang trả hình nền cũ', 'ok');
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
document.addEventListener('change', async e => {
  const t = e.target;
  if (t.dataset && t.dataset.ev === 'handopt') {
    const on = t.checked, hs = S.hosts.slice();
    try { await api('/api/hand_option', {enabled: on, hosts: hs}); if (hs.length) openLog(); S.interact.hand_enabled = on; toast(on ? 'Đã bật nút giơ tay' : 'Đã tắt nút giơ tay trên máy học sinh', 'ok'); } catch (err) { toast(err.message, 'err'); }
    return;
  }
  if (t.dataset && t.dataset.ev === 'baropt') {
    const on = t.checked, hs = S.hosts.slice();
    try { await api('/api/bar_option', {enabled: on, hosts: hs}); if (hs.length) openLog(); S.interact.bar_enabled = on; toast(on ? 'Đã hiện lại thanh hỗ trợ học sinh' : 'Đã tắt thanh hỗ trợ học sinh trên máy học sinh', 'ok'); } catch (err) { toast(err.message, 'err'); }
    return;
  }
  if (t.id === 'wPreset' && t.value) {
    const p = S.wall.presets[t.value]; if (!p) return;
    Object.assign(S.wspec, p); S.wbgData = '';
    if (p.bg) api('/api/wall_img?id=' + p.bg).then(r => { S.wbgData = r.data; wallDraw(); }).catch(() => {});
    render();
  } else if (t.id === 'wCls') { S.wcls = t.value; } else if (['wTitle', 'wSub', 'wC1', 'wC2', 'wDim', 'wSeat', 'wLock'].includes(t.id)) { wallRead(); wallDraw(); }
});
document.addEventListener('input', e => { if (['wTitle', 'wSub', 'wC1', 'wC2', 'wDim'].includes(e.target.id)) { wallRead(); wallDraw(); } });


/* ---------- Giao diện màn hình khóa ---------- */
async function lockStyleDialog() {
  S.lockSpec = (await api('/api/lock_style')).style;
  const k = S.lockSpec;
  const v = await modal({title: '🎨 Giao diện màn hình khóa', ok: 'Lưu', html: `<div style="display:grid;gap:8px;min-width:min(420px,80vw)">
      <div class="row"><input type="text" id="lkIcon" value="${esc(k.icon)}" maxlength="4" style="width:64px;text-align:center"><input type="text" id="lkTitle" value="${esc(k.title)}" maxlength="60" style="flex:1" placeholder="Tiêu đề, có thể dùng {lop}"></div>
      <div class="row">Màu <input type="color" id="lkC1" value="${esc(k.c1)}"> → <input type="color" id="lkC2" value="${esc(k.c2)}">
        <button class="btn sm ghost" data-ev="lockpic">Chọn ảnh nền...</button><button class="btn sm ghost" data-ev="lockpicclr">Bỏ ảnh</button><span class="muted" id="lkBg">${k.bg ? 'Đã chọn ảnh' : 'Không dùng ảnh'}</span></div>
      <label class="muted">Làm tối ảnh <input type="range" id="lkDim" min="0" max="80" value="${k.dim}"></label>
      <label class="switch"><input type="checkbox" id="lkClock" ${k.clock ? 'checked' : ''}><span class="tr"></span><span>Hiện đồng hồ</span></label>
      <label class="switch"><input type="checkbox" id="lkSeat" ${k.seat ? 'checked' : ''}><span class="tr"></span><span>Hiện tên em và số máy</span></label>
      <div class="muted" style="font-size:12.5px">Lời nhắn bạn nhập ở ô “Nhắn tin” hiện ở giữa màn hình. Lưu xong, bấm “Khóa màn hình kèm lời nhắn” để dùng giao diện này.</div></div>`,
    collect: r => ({icon: r.querySelector('#lkIcon').value, title: r.querySelector('#lkTitle').value, c1: r.querySelector('#lkC1').value, c2: r.querySelector('#lkC2').value,
      dim: +r.querySelector('#lkDim').value, clock: r.querySelector('#lkClock').checked, seat: r.querySelector('#lkSeat').checked, bg: S.lockSpec.bg})});
  if (!v) return;
  await api('/api/lock_style_save', {spec: v}); toast('Đã lưu giao diện màn hình khóa', 'ok');
}
