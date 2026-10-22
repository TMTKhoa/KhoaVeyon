// Câu đố nhanh, phát tài liệu, mở trang web đồng loạt (trang Tương tác).
S.quiz = S.quiz || {st: null, timer: null};

function viewClassroom() {
  const Q = S.quiz.st;
  let live = '';
  if (Q && Q.active) {
    const tot = Math.max(1, Q.answered);
    live = `<div style="margin-top:12px"><b>${esc(Q.q)}</b> <span class="muted">— ${Q.answered}/${Q.total} em đã trả lời${Q.closed ? ' (đã kết thúc)' : ''}</span>
      ${Q.opts.map((o, i) => `<div style="display:flex;gap:8px;align-items:center;margin:5px 0" title="${esc((Q.voters[i] || []).join(', '))}">
        <span style="width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${String.fromCharCode(65 + i)}. ${esc(o)}${Q.correct === i ? ' ✅' : ''}</span>
        <div style="flex:1;background:#e5e7eb;border-radius:6px;height:20px"><div style="width:${Math.round(100 * Q.counts[i] / tot)}%;height:100%;border-radius:6px;background:${Q.correct === i ? '#16a34a' : '#2563eb'}"></div></div><b style="width:28px;text-align:right">${Q.counts[i]}</b></div>`).join('')}
      ${Q.pending.length ? `<div class="muted" style="margin-top:6px">Chưa trả lời (${Q.pending.length}): ${esc(Q.pending.join(', '))}</div>` : '<div class="muted" style="margin-top:6px">Cả lớp đã trả lời.</div>'}
      <div class="row" style="margin-top:8px"><button class="btn" data-qz="end">⏹ Kết thúc</button><button class="btn primary" data-qz="reveal">✅ Kết thúc và công bố đáp án</button></div></div>`;
  }
  return `<section class="card"><h3>❓ Câu đố nhanh</h3>
    <input type="text" id="qzQ" maxlength="300" style="width:100%;box-sizing:border-box" placeholder="Câu hỏi, ví dụ: Thủ đô của Việt Nam là gì?">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:6px">${'ABCD'.split('').map((c, i) => `<label class="row" style="gap:6px"><input type="radio" name="qzC" value="${i}" title="Đáp án đúng"><input type="text" class="qzO" maxlength="100" style="flex:1" placeholder="Đáp án ${c}${i > 1 ? ' (tùy chọn)' : ''}"></label>`).join('')}</div>
    <div class="row" style="flex-wrap:wrap;margin-top:8px"><span class="muted">Chấm tròn = đáp án đúng (có thể bỏ trống)</span>
      <label class="muted">Thời gian <select id="qzSec" class="xsel"><option value="0">không giới hạn</option><option value="30">30 giây</option><option value="60">1 phút</option><option value="120">2 phút</option></select></label>
      <button class="btn primary" data-qz="start">❓ Gửi câu đố</button></div>${live}
    <h4 style="margin:16px 0 4px">📎 Phát tài liệu &amp; mở trang web</h4>
    <div class="row" style="flex-wrap:wrap;gap:8px"><button class="btn" data-qz="handout">📎 Phát tệp tới máy học sinh</button>
      <input type="text" id="qzUrl" style="flex:1;min-width:200px" placeholder="https://..."><button class="btn" data-qz="url">🌐 Mở trang này trên máy học sinh</button></div>
    <p class="sub">Máy nhận được là máy đang chọn (hoặc tất cả). Tài liệu được chép vào thư mục trên màn hình nền của học sinh.</p></section>`;
}

async function quizRefresh() {
  try { S.quiz.st = await api('/api/quiz_state', undefined, {quiet: true}); } catch (e) { return; }
  if (S.page === 'interact' && !document.activeElement.matches('input,textarea,select')) render();
}
function quizPoll() {
  if (S.quiz.timer) return;
  S.quiz.timer = setInterval(() => { if (S.page !== 'interact' || !(S.quiz.st && S.quiz.st.active && !S.quiz.st.closed)) return; quizRefresh(); }, 2500);
}
function readB64(f) {
  return new Promise((ok, no) => { const r = new FileReader(); r.onload = () => ok(String(r.result).split(',')[1] || ''); r.onerror = () => no(new Error('Không đọc được ' + f.name)); r.readAsDataURL(f); });
}

document.addEventListener('click', async e => {
  const el = e.target.closest('[data-qz]'); if (!el) return;
  e.preventDefault();
  const a = el.dataset.qz;
  try {
    if (a === 'start') {
      const q = $('#qzQ').value.trim();
      const opts = [...document.querySelectorAll('.qzO')].map(i => i.value.trim());
      const idx = opts.map((o, i) => o ? i : -1).filter(i => i >= 0);
      const chk = document.querySelector('input[name=qzC]:checked');
      const correct = chk && opts[+chk.value] ? idx.indexOf(+chk.value) : -1;
      if (!q || idx.length < 2) return toast('Cần câu hỏi và ít nhất 2 đáp án', 'err');
      const hs = await resolveTargets(); if (!hs) return;
      S.quiz.st = await api('/api/quiz_start', {hosts: hs, q, opts: idx.map(i => opts[i]), correct, secs: +$('#qzSec').value, cls: S.mon ? S.mon.cls : ''});
      quizPoll(); render(); toast('Đã gửi câu đố tới ' + hs.length + ' máy', 'ok');
    } else if (a === 'end' || a === 'reveal') {
      S.quiz.st = await api('/api/quiz_end', {reveal: a === 'reveal'}); render();
    } else if (a === 'url') {
      const url = $('#qzUrl').value.trim(); if (!url) return toast('Nhập địa chỉ trang web', 'err');
      const hs = await resolveTargets(); if (!hs) return;
      await api('/api/open_url', {hosts: hs, url}); toast('Đã mở trang web trên ' + hs.length + ' máy', 'ok');
    } else if (a === 'handout') {
      const inp = document.createElement('input'); inp.type = 'file'; inp.multiple = true;
      inp.onchange = async () => {
        try {
          const fs = [...inp.files]; if (!fs.length) return;
          const hs = await resolveTargets(); if (!hs) return;
          const files = []; for (const f of fs) files.push({name: f.name, data: await readB64(f)});
          const r = await api('/api/handout_send', {hosts: hs, files, open: 'folder'});
          toast('Đang phát ' + r.files.length + ' tệp tới ' + r.count + ' máy (xem nhật ký)', 'ok'); if (typeof openLog === 'function') openLog();
        } catch (err) { toast(err.message, 'err'); }
      };
      inp.click();
    }
  } catch (err) { toast(err.message, 'err'); }
});
quizRefresh();

// ---- chiếu bài một học sinh cho cả lớp: chụp -> xem trước -> xác nhận -> chiếu
async function funShare() {
  if (!S.sel || S.sel.size !== 1) return toast('Hãy chọn đúng 1 máy (của em cần chiếu bài)', 'warn');
  const src = [...S.sel][0];
  const snap = await api('/api/share_snap', {host: src, cls: S.mon ? S.mon.cls : ''});
  toast('Đang chụp màn hình ' + (snap.name || 'em này') + '...', 'ok');
  let r = null;
  for (let i = 0; i < 20 && !(r && r.ready); i++) {
    await new Promise(ok => setTimeout(ok, 1000));
    try { r = await api('/api/share_state?id=' + snap.id, undefined, {quiet: true}); } catch (err) { return toast(err.message, 'err'); }
  }
  if (!r || !r.ready) return toast('Máy học sinh chưa gửi ảnh (máy tắt, hoặc chưa bật giám sát để nhận bản helper mới?)', 'err');
  const targets = Object.values((S.mon && S.mon.machines) || {}).filter(m => m.online && m.host !== src).map(m => m.host);
  const hs = targets.length ? targets : S.hosts.filter(h => h !== src);
  const v = await modal({title: '📽 Xem trước trước khi chiếu cho cả lớp', ok: 'Chiếu cho ' + hs.length + ' máy',
    html: `<img src="${r.img}" style="max-width:100%;max-height:50vh;border:1px solid #cbd5e1;border-radius:8px"><div class="row" style="flex-wrap:wrap;gap:12px;margin-top:8px">
      <label class="muted">Tự tắt sau <select id="shSec" class="xsel"><option value="0">khi tôi bấm tắt</option><option value="30">30 giây</option><option value="60">1 phút</option><option value="180">3 phút</option></select></label>
      <label class="muted"><input type="checkbox" id="shHide"> không ghi tên em</label></div>
      <p class="sub">Kiểm tra ảnh không có tin nhắn riêng tư hay nội dung không phù hợp rồi mới chiếu.</p>`,
    collect: x => ({secs: +x.querySelector('#shSec').value, hide_name: x.querySelector('#shHide').checked})});
  if (!v) return;
  await api('/api/share_push', Object.assign({id: snap.id, hosts: hs}, v));
  toast('Đang chiếu bài cho ' + hs.length + ' máy. Bấm "Tắt chiếu bài" khi xong.', 'ok');
}
