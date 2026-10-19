// KhoaVeyon - Trang Chế độ thi (một nút bật, một nút tắt)
async function loadExam() { S.exam = await api('/api/exam'); S.exam.offset = S.exam.now - Date.now() / 1000; if (!S.examDraft) S.examDraft = {steps: Object.assign({}, S.exam.steps), cls: '', minutes: 0, stop_watch: S.exam.stop_watch !== false, collect_paths: (S.exam.collect_paths || []).join('\n'), kq_url: S.exam.kq_url || ''}; }

function examClock() {
  const x = S.exam; if (!x || !x.active) return '';
  const now = Date.now() / 1000 + (x.offset || 0), el = Math.max(0, Math.round(now - x.since));
  const fmt = s => { const m = Math.floor(s / 60); return m >= 60 ? Math.floor(m / 60) + ' giờ ' + (m % 60) + ' phút' : m + ' phút ' + (s % 60) + ' giây'; };
  const left = x.end_at ? Math.max(0, Math.round(x.end_at - now)) : -1;
  return `Đã thi ${fmt(el)}` + (left >= 0 ? ` · còn lại <b>${fmt(left)}</b>` : ' · không đặt giờ tự tắt');
}

function examExtraRow() {
  const x = S.exam, d = S.examDraft;
  return `<div class="row" style="flex-wrap:wrap;margin-top:12px">
      <button class="btn ghost" data-xa="examcollect" title="Chép file mới sửa trong các thư mục thu bài về máy giáo viên, không cần kết thúc thi">📥 Thu file bài làm ngay</button>
      <button class="btn ghost" data-xa="examrelease" title="Dùng khi máy tắt lúc kết thúc thi nên còn bị khóa USB, in ấn hoặc chặn sao chép-dán">🔓 Gỡ khóa USB / in / sao chép-dán</button>
      <button class="btn ghost" data-xa="examfiles">Mở thư mục bài đã thu</button>
      ${x.collected ? `<span class="muted">Lần thu gần nhất: ${esc(x.collected)}</span>` : ''}</div>`;
}

function viewExam() {
  const x = S.exam; if (!x) return '<div class="empty">Đang tải...</div>';
  const d = S.examDraft;
  const lab = k => (x.all_steps.find(s => s.key === k) || {label: k}).label;
  if (x.active) {
    const steps = x.all_steps.filter(s => x.steps[s.key]).map(s => `<li>${esc(s.label)}</li>`).join('');
    return `<div class="stack"><section class="card" style="border:2px solid #f59e0b">
      <h3>🔒 Đang trong giờ thi${x.cls ? ' · lớp ' + esc(x.cls) : ''} <span class="badge">${x.hosts.length} máy</span></h3>
      <div style="font-size:18px;margin:8px 0" id="examClock">${examClock()}</div>
      <p class="sub" style="margin-bottom:6px">Đã áp dụng:</p><ul style="margin:0 0 14px 20px">${steps || '<li class="muted">(không có bước nào)</li>'}</ul>
      <div class="row"><button class="btn danger" data-xa="examend" ${x.busy ? 'disabled' : ''}>⏹ KẾT THÚC THI, mở lại cho cả lớp</button>
        <button class="btn" data-act="gopage" data-page-to="viol">🚨 Xem vi phạm</button>${x.cls && x.steps.kq ? `<button class="btn" data-kq="compare" data-cls="${esc(x.cls)}">🔎 Đối chiếu tên – máy (KhoaQuiz)</button>` : ''}<button class="btn ghost" data-act="gopage" data-page-to="report">📊 Báo cáo</button></div>
      ${examExtraRow()}
      ${x.busy ? `<p class="hint">Đang ${x.busy === 'start' ? 'bật' : 'tắt'} chế độ thi, xem tiến trình ở Nhật ký bên dưới.</p>` : ''}
      <p class="hint" style="margin-bottom:0">Máy nào tắt lúc bấm Kết thúc sẽ còn bị hạn chế đến khi mở khóa thủ công (trang Điều khiển lớp). Kết thúc xong, vào trang Báo cáo để xuất danh sách vi phạm kèm ảnh.</p>
    </section></div>`;
  }
  const chk = s => `<label class="switch"><input type="checkbox" data-xe="step" data-k="${esc(s.key)}" ${d.steps[s.key] ? 'checked' : ''}><span class="tr"></span><span>${esc(s.label)}</span></label>`;
  return `<div class="stack"><section class="card">
    <h3>Chế độ thi <span class="badge">${targets().hosts.length} máy</span></h3>
    <p class="sub">Một nút bật hết các bước cần cho giờ kiểm tra, hết giờ một nút để mở lại. Máy áp dụng: ${targets().all ? 'tất cả máy trong danh sách' : 'các máy đã tick ở Điều khiển lớp'}.</p>
    <div class="formgrid"><div><label class="field">Lớp đang thi (để hiện nhãn chỗ ngồi)</label>
      <select data-xe="cls"><option value="">(không chọn lớp)</option>${x.classes.map(c => `<option value="${esc(c)}" ${d.cls === c ? 'selected' : ''}>Lớp ${esc(c)}</option>`).join('')}</select></div>
      <div><label class="field">Tự tắt sau (phút, 0 = không đặt giờ)</label><input type="number" min="0" max="600" data-xe="minutes" value="${esc(d.minutes)}"></div></div>
    <div style="display:flex;flex-direction:column;gap:12px;margin:14px 0">${x.all_steps.map(chk).join('')}
      <label class="switch"><input type="checkbox" data-xe="stop_watch" ${d.stop_watch ? 'checked' : ''}><span class="tr"></span><span>Khi kết thúc thi cũng tắt giám sát</span></label></div>
    <div style="margin:0 0 14px"><label class="field">Thư mục thu file bài làm (mỗi dòng một thư mục; <code>{user}</code> = tài khoản học sinh đang đăng nhập)</label>
      <textarea data-xe="collect_paths" rows="3" style="width:100%;font-family:Consolas,monospace" spellcheck="false" placeholder="C:\\BaiLam&#10;C:\\Users\\{user}\\Documents">${esc(d.collect_paths)}</textarea>
      <p class="hint" style="margin:4px 0 0">Chỉ dùng khi bật bước “thu file bài làm”. Chỉ thu file mới sửa trong giờ thi, mỗi file tối đa 50 MB, mỗi máy tối đa 500 MB; lưu ở <code>data\\exam_files</code>.</p></div>
    <div style="margin:0 0 14px"><label class="field">Link bài kiểm tra KhoaQuiz (dùng khi bật bước “Mở bài kiểm tra KhoaQuiz”)</label>
      <div class="row" style="flex-wrap:nowrap"><input data-xe="kq_url" style="flex:1" placeholder="https://khoaquiz.netlify.app/kiemtra.html?e=..." value="${esc(d.kq_url || '')}">
        <button class="btn" data-kq="pickexam" title="Lấy danh sách bài kiểm tra từ tài khoản KhoaQuiz đã liên kết">📋 Chọn từ KhoaQuiz</button></div>
      <p class="hint" style="margin:4px 0 0">Mỗi máy mở link kèm số máy (<code>&amp;m=MAY12</code>). Sau giờ thi, bấm “Đối chiếu tên – máy” để biết bài nào nộp từ máy của bạn khác.</p></div>
    <div class="row"><button class="btn primary" data-xa="examstart" ${x.busy ? 'disabled' : ''}>▶ BẮT ĐẦU THI</button></div>
    ${examExtraRow()}
    <p class="hint" style="margin-bottom:0">Trang được phép lấy từ “Trang web được phép”, nên kiểm tra danh sách đó trước. Bước khóa AI đóng các trình duyệt đang mở. Máy tắt lúc bấm sẽ bị bỏ qua và ghi ở Nhật ký.</p>
  </section></div>`;
}

document.addEventListener('change', e => {
  const t = e.target.closest('[data-xe]'); if (!t || !S.examDraft) return;
  const k = t.dataset.xe;
  if (k === 'step') S.examDraft.steps[t.dataset.k] = t.checked;
  else if (k === 'stop_watch') S.examDraft.stop_watch = t.checked;
  else if (k === 'cls') S.examDraft.cls = t.value;
  else if (k === 'minutes') S.examDraft.minutes = Math.max(0, parseInt(t.value) || 0);
  else if (k === 'collect_paths') S.examDraft.collect_paths = t.value;
  else if (k === 'kq_url') S.examDraft.kq_url = t.value.trim();
});

document.addEventListener('click', async e => {
  const el = e.target.closest('[data-xa]'); if (!el) return;
  const a = el.dataset.xa; if (!['examstart', 'examend', 'examcollect', 'examrelease', 'examfiles'].includes(a)) return;
  e.preventDefault();
  try {
    if (a === 'examstart') {
      const hs = targets().hosts; if (!hs.length) { toast('Hãy thêm máy học sinh trước ở trang "Điều khiển lớp".', 'warn'); return; }
      const d = S.examDraft, on = S.exam.all_steps.filter(s => d.steps[s.key]);
      if (!on.length) { toast('Chưa chọn bước nào', 'warn'); return; }
      if (d.steps.kq && !d.kq_url) { toast('Đã bật bước mở bài KhoaQuiz nhưng chưa có link bài kiểm tra', 'warn'); return; }
      const ok = await modal({title: `Bắt đầu thi cho ${hs.length} máy?`, ok: 'Bắt đầu thi', danger: true,
        html: `<p style="margin-top:0">Chương trình sẽ làm lần lượt:</p><ol style="margin:0 0 10px 20px">${on.map(s => `<li>${esc(s.label)}</li>`).join('')}</ol>${d.steps.blockai ? '<div class="note warn" style="margin:0">Trình duyệt đang mở trên máy học sinh sẽ bị đóng, bài chưa lưu có thể mất.</div>' : ''}`});
      if (!ok) return;
      await api('/api/exam_start', {hosts: hs, steps: d.steps, cls: d.cls, minutes: d.minutes, stop_watch: d.stop_watch, collect_paths: d.collect_paths, kq_url: d.kq_url || ''});
      openLog(); toast('Đang bật chế độ thi...', 'ok');
    } else if (a === 'examfiles') {
      await api('/api/open', {what: 'examfiles'});
    } else if (a === 'examcollect') {
      const hs = await resolveTargets(); if (!hs) return;
      const paths = (S.examDraft.collect_paths || '').split('\n').map(x => x.trim()).filter(Boolean);
      if (!paths.length) { toast('Nhập ít nhất một thư mục thu bài', 'warn'); return; }
      await api('/api/exam_collect', {hosts: hs, paths, minutes: 180});
      openLog(); toast(`Đang thu file từ ${hs.length} máy...`, 'ok');
    } else if (a === 'examrelease') {
      const hs = await resolveTargets(); if (!hs) return;
      const ok = await modal({title: `Gỡ khóa USB, in ấn, sao chép-dán trên ${hs.length} máy?`, ok: 'Gỡ khóa', html: 'Mở lại ổ USB, bật lại dịch vụ in và gỡ chặn sao chép-dán. Không đụng tới các hạn chế khác.'});
      if (!ok) return;
      await api('/api/exam_release', {hosts: hs});
      openLog(); toast('Đang gỡ khóa...', 'ok');
    } else {
      const ok = await modal({title: 'Kết thúc thi?', ok: 'Kết thúc, mở lại cho cả lớp', html: 'Chương trình sẽ thu file bài làm (nếu đã chọn), gỡ nhãn chỗ ngồi, tắt giám sát (nếu đã chọn), cho vào lại mọi trang, mở khóa, mở khóa công cụ AI và mở lại USB, in ấn, sao chép-dán (nếu đã khóa).'});
      if (!ok) return;
      await api('/api/exam_end', {});
      openLog(); toast('Đang tắt chế độ thi...', 'ok');
    }
    await examReload();
  } catch (err) { toast(err.message, 'err'); }
});

async function examReload(quiet) {
  S.exam = await api('/api/exam', undefined, {quiet: !!quiet}); S.exam.offset = S.exam.now - Date.now() / 1000;
  if (S.page === 'exam') { const v = $('#view'); if (v) v.innerHTML = viewExam(); }
}
setInterval(() => { const c = $('#examClock'); if (c) c.innerHTML = examClock(); }, 1000);
setInterval(() => { if (S.page === 'exam') examReload(true).catch(() => {}); }, 4000);
