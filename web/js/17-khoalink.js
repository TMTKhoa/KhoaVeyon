// KhoaVeyon - Kết nối KhoaQuiz (liên kết, danh sách lớp, đối chiếu điểm danh, bài kiểm tra) và xuất file cho KhoaTool
let KQ_LOADING = false;
async function kqEnsure(force) {
  if ((S.kq && !force) || KQ_LOADING) return;
  KQ_LOADING = true;
  try { S.kq = await api('/api/kq_status'); } catch (e) { S.kq = {linked: false, url: 'https://khoaquiz.netlify.app', error: e.message}; }
  KQ_LOADING = false;
  if (S.page === 'settings') render();
}

function kqSettingsCard() {
  const k = S.kq;
  if (!k) { kqEnsure(); return '<section class="card"><h3>Liên kết KhoaQuiz</h3><p class="muted">Đang kiểm tra...</p></section>'; }
  const state = k.linked
    ? `<div class="note">Đã liên kết tài khoản <b>${esc(k.name || '?')}</b> tại ${esc(k.url)} (mã đuôi …${esc(k.hint)}, lúc ${esc(k.at)}).</div>`
    : '<div class="muted">Chưa liên kết.</div>';
  return `<section class="card"><h3>Liên kết KhoaQuiz</h3>
    <p class="sub">Trong KhoaQuiz: Cài đặt → <b>Liên kết KhoaTool / KhoaVeyon</b> → chọn <b>KhoaVeyon</b> → Tạo mã, rồi dán mã vào đây. Mã của KhoaVeyon tách riêng với mã của KhoaTool, nên liên kết ở đây không làm KhoaTool mất liên kết.</p>
    ${state}
    <div class="formgrid" style="margin-top:12px">
      <div><label class="field">Địa chỉ KhoaQuiz</label><input type="text" id="kqUrl" value="${esc(k.url || 'https://khoaquiz.netlify.app')}"></div>
      <div><label class="field">Mã liên kết</label><input type="text" id="kqCode" placeholder="KQ-XXXXXX-XXXXXX-XXXXXX-XXXXXX" autocomplete="off" spellcheck="false"></div></div>
    <div class="row" style="margin-top:12px"><button class="btn primary" data-kq="link">${k.linked ? 'Đổi mã liên kết' : 'Liên kết'}</button>${k.linked ? '<button class="btn ghost" data-kq="unlink">Hủy liên kết trên máy này</button>' : ''}</div>
    <p class="hint" style="margin-bottom:0">Dùng cho: lấy danh sách lớp (trang Lớp &amp; lịch dạy), đối chiếu điểm danh với bài làm (trang Sơ đồ lớp học), mở bài kiểm tra trên máy học sinh (trang Chế độ thi). Cần Internet khi bấm các nút này; mất mạng thì chỉ các nút KhoaQuiz báo lỗi. Mã lưu trong <code>data\\khoaquiz.json</code>, chỉ tài khoản Windows đang dùng đọc được.</p>
  </section>`;
}

function kqFlagHtml(r) {
  const color = {suggest_absent: 'warn', did_but_absent: 'warn', other_machine: 'err', moved: '', offline: ''};
  return r.flags.map(f => `<div class="note ${color[f.code] || ''}" style="margin:2px 0;padding:4px 8px;font-size:12.5px">${esc(f.text)}</div>`).join('');
}

async function kqCompare(cls) {
  toast('Đang lấy bài làm từ KhoaQuiz...', '');
  let d;
  try { d = await api('/api/kq_compare?cls=' + encodeURIComponent(cls)); } catch (e) { toast(e.message, 'err'); return; }
  const flagged = d.rows.filter(r => r.flags.length), sug = d.rows.filter(r => r.flags.some(f => f.code === 'suggest_absent'));
  const rows = (flagged.length ? flagged : d.rows).map(r => `<tr><td><b>${esc(r.name)}</b></td><td>${r.seat || '—'}</td><td>${r.did ? '✔ ' + (r.score != null ? esc(r.score) : '') : '<span class="muted">chưa làm</span>'}</td><td>${r.kv_absent ? 'vắng' : 'có mặt'}</td><td>${kqFlagHtml(r) || '<span class="muted">khớp</span>'}</td></tr>`).join('');
  const extra = d.extras.length ? `<div class="note warn" style="margin-top:8px">Có bài làm KhoaQuiz nhưng không có trong danh sách lớp KhoaVeyon: <b>${d.extras.map(x => esc(x.name) + (x.m ? ' (máy ' + esc(x.m) + ')' : '')).join(', ')}</b>. Có thể học sinh gõ sai tên hoặc danh sách lớp cũ.</div>` : '';
  const c = d.counts;
  const html = `${d.note ? `<div class="note warn">${esc(d.note)}</div>` : `<p style="margin-top:0">Bài: <b>${d.titles.map(esc).join('; ')}</b> · ${d.did}/${d.total} em có bài làm · gợi ý vắng ${c.suggest_absent} · làm bài mà bị đánh vắng ${c.did_but_absent} · nộp từ máy của bạn khác <b>${c.other_machine}</b></p>`}
    <div style="max-height:52vh;overflow:auto"><table class="tbl"><thead><tr><th>Học sinh</th><th>Máy</th><th>KhoaQuiz</th><th>KhoaVeyon</th><th>Ghi chú</th></tr></thead><tbody>${rows}</tbody></table></div>${extra}
    <p class="hint" style="margin-bottom:0">${flagged.length ? 'Chỉ hiện các em cần chú ý.' : 'Mọi em đều khớp.'} Số máy lấy từ link bài kiểm tra mở bằng Chế độ thi (<code>m=</code>), học sinh có thể sửa nên chỉ dùng để phát hiện chọn nhầm tên.</p>`;
  const ok = await modal({title: `Đối chiếu KhoaQuiz · lớp ${d.cls}`, html, ok: sug.length ? `Đánh vắng ${sug.length} em gợi ý` : 'Đóng', cancel: 'Đóng', noCancel: !sug.length});
  if (ok && sug.length) {
    const sure = await modal({title: 'Đánh vắng theo gợi ý?', ok: 'Đánh vắng', html: `Các em sau không có bài làm KhoaQuiz: <b>${sug.map(r => esc(r.name)).join(', ')}</b>. Nếu em có mặt nhưng chưa làm bài thì đừng đánh vắng.`});
    if (!sure) return;
    if (S.seatCls !== d.cls) S.seatCls = d.cls;
    await attAct({action: 'absent_many', names: sug.map(r => r.name)});
  }
}

async function kqPickExam() {
  let r;
  try { r = await api('/api/kq_exams'); } catch (e) { toast(e.message, 'err'); return; }
  if (!r.items.length) { toast('KhoaQuiz chưa có bài kiểm tra nào (KhoaQuiz → Kiểm tra → Lưu cài đặt)', 'warn'); return; }
  const v = await modal({title: 'Chọn bài kiểm tra KhoaQuiz', ok: 'Chọn',
    html: `<div style="display:flex;flex-direction:column;gap:8px">${r.items.map((x, i) => `<label class="switch"><input type="radio" name="kqex" value="${i}" ${i === 0 ? 'checked' : ''}><span>${esc(x.title || x.id)} <span class="muted">· ${x.open ? (x.phase === 'run' ? 'đang làm bài' : 'đang mở phòng chờ') : 'chưa mở'} · ${esc(x.minutes)} phút${x.cls.length ? ' · ' + x.cls.map(esc).join(', ') : ''}</span></span></label>`).join('')}</div>
      <p class="hint" style="margin-bottom:0">Bài chưa mở thì học sinh chưa vào được: mở bài trong KhoaQuiz trước giờ thi.</p>`,
    collect: root => { const c = root.querySelector('input[name=kqex]:checked'); return c ? r.items[+c.value] : null; }});
  if (!v) return;
  S.examDraft.kq_url = v.url; S.examDraft.steps.kq = true;
  if (S.page === 'exam') { const el = $('#view'); if (el) el.innerHTML = viewExam(); }
  toast('Đã chọn: ' + (v.title || v.id), 'ok');
}

async function kqRosters() {
  let pv;
  try { pv = await api('/api/kq_rosters_preview'); } catch (e) { toast(e.message, 'err'); return; }
  let sid = '';
  if (pv.schools.length > 1) {
    sid = await modal({title: 'Lấy danh sách lớp của trường nào?', ok: 'Lấy danh sách',
      html: `<select id="kqSid" style="width:100%">${pv.schools.map(s => `<option value="${esc(s.id)}">${esc(s.name)} (${s.classes} lớp)</option>`).join('')}</select>`,
      collect: root => root.querySelector('#kqSid').value});
    if (!sid) return;
  } else {
    const ok = await modal({title: 'Lấy danh sách lớp từ KhoaQuiz?', ok: 'Lấy danh sách', html: `KhoaQuiz có ${pv.total} lớp có danh sách học sinh. Các lớp này được cập nhật trong KhoaVeyon, lớp khác giữ nguyên; chỗ ngồi của em đã rời lớp được bỏ.`});
    if (!ok) return;
  }
  try {
    const r = await api('/api/kq_rosters_import', {sid});
    S.school = r; toast(`Đã lấy ${r.imported.new + r.imported.updated} lớp (${r.imported.students} học sinh) từ KhoaQuiz`, 'ok');
    render();
  } catch (e) { toast(e.message, 'err'); }
}

async function ktExport() {
  try {
    const r = await api('/api/kt_export', {});
    const blob = new Blob([JSON.stringify(r.data, null, 1)], {type: 'application/json'});
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = r.name; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    toast(`Đã xuất ${r.name} (${r.data.classes.length} lớp, ${r.data.machines.length} máy hỏng). Trong KhoaTool: Báo cáo buổi dạy hoặc Điểm danh → Nhập từ KhoaVeyon.`, 'ok');
  } catch (e) { toast(e.message, 'err'); }
}

document.addEventListener('click', async e => {
  const el = e.target.closest('[data-kq]'); if (!el) return;
  e.preventDefault();
  const a = el.dataset.kq;
  try {
    if (a === 'link') {
      const url = ($('#kqUrl') || {}).value || '', code = ($('#kqCode') || {}).value || '';
      if (!code.trim()) { toast('Dán mã liên kết lấy từ KhoaQuiz', 'warn'); return; }
      S.kq = await api('/api/kq_link', {url, code}); toast('Đã liên kết KhoaQuiz: ' + (S.kq.name || ''), 'ok'); render();
    } else if (a === 'unlink') {
      if (!await modal({title: 'Hủy liên kết KhoaQuiz trên máy này?', ok: 'Hủy liên kết', html: 'Mã bị xóa khỏi máy này. Muốn thu hồi hẳn (mã đã lộ), vào KhoaQuiz → Cài đặt → Liên kết → KhoaVeyon → Hủy liên kết.'})) return;
      S.kq = await api('/api/kq_unlink', {}); render();
    } else if (a === 'compare') await kqCompare(el.dataset.cls);
    else if (a === 'pickexam') await kqPickExam();
    else if (a === 'rosters') await kqRosters();
    else if (a === 'ktexport') await ktExport();
  } catch (err) { toast(err.message, 'err'); }
});
