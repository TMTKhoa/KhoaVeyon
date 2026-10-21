// KhoaVeyon - Trang Lớp và lịch dạy
function viewSchool() {
  const sc = S.school || {}, cls = sc.classes || [], slots = sc.slots || [];
  const cur = sc.current, nxt = sc.next, dayN = ['Thứ hai', 'Thứ ba', 'Thứ tư', 'Thứ năm', 'Thứ sáu', 'Thứ bảy', 'Chủ nhật'];
  const total = cls.reduce((a, c) => a + c.count, 0);
  const todayIdx = (new Date().getDay() + 6) % 7;
  const nowTxt = cur
    ? `<div style="font-size:30px;font-weight:800">Lớp ${esc(cur.cls)}</div><div class="muted">${sc.source === 'manual' ? 'Do bạn đặt tay' + (cur.until ? ' (hết hiệu lực lúc ' + new Date(cur.until * 1000).toTimeString().slice(0, 5) + ')' : '') : `Tiết ${esc(cur.start)} – ${esc(cur.end)}`}</div>`
    : `<div style="font-size:24px;font-weight:800" class="muted">Ngoài giờ dạy</div><div class="muted">Chưa có tiết nào đang diễn ra.</div>`;
  const nextTxt = nxt
    ? `<div style="font-size:30px;font-weight:800">Lớp ${esc(nxt.cls)}</div><div class="muted">${nxt.date === new Date().toISOString().slice(0, 10) || (nxt.day === todayIdx) ? 'Hôm nay' : dayN[nxt.day]} ${esc(nxt.start)} – ${esc(nxt.end)}</div>`
    : `<div class="muted" style="font-size:16px">${sc.auto === false ? 'Đang tắt chế độ tự động theo lịch.' : slots.length ? 'Không còn tiết nào trong tuần.' : 'Chưa nhập thời khóa biểu.'}</div>`;
  const times = [...new Set(slots.map(s => s.start + '|' + s.end))].sort();
  const days = [...new Set(slots.map(s => s.day))].sort((a, b) => a - b);
  const short = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];
  const grid = slots.length ? `<table class="sgrid"><tr><th></th>${days.map(d => `<th>${short[d]}${d === todayIdx ? ' •' : ''}</th>`).join('')}</tr>
      ${times.map(t => { const [a, b] = t.split('|'); return `<tr><td class="tm">${a}–${b}</td>${days.map(d => {
        const s = slots.find(x => x.day === d && x.start === a && x.end === b);
        const on = s && cur && sc.source === 'schedule' && cur.cls === s.cls && cur.start === a && d === todayIdx;
        return s ? `<td class="${on ? 'on' : ''}">${esc(s.cls)}</td>` : '<td class="nil"></td>'; }).join('')}</tr>`; }).join('')}</table>`
    : '<div class="empty">Chưa có thời khóa biểu. Bấm “Nhập thời khóa biểu” và chọn file Excel.</div>';
  const chips = cls.length ? `<div class="cchips">${cls.map(c => `<span class="cchip ${cur && cur.cls === c.name ? 'on' : ''}" data-act="schoolset" data-cls="${esc(c.name)}" title="Bấm để đặt làm lớp hiện tại">${esc(c.name)}<small>${c.count} HS</small></span>`).join('')}</div>`
    : '<div class="empty">Chưa có danh sách lớp. Bấm “Nhập danh sách lớp” và chọn file Excel điểm danh.</div>';
  const info = (f, at) => f ? `<span class="muted">${esc(f)} · nhập lúc ${esc(at)}</span>` : '<span class="muted">Chưa nhập</span>';
  return `<div class="stack">
    <section class="card"><div style="display:grid;grid-template-columns:1fr 1fr;gap:22px">
      <div><div class="muted" style="margin-bottom:6px">ĐANG DẠY</div>${nowTxt}</div>
      <div><div class="muted" style="margin-bottom:6px">LỚP KẾ TIẾP</div>${nextTxt}</div></div>
      <div class="row" style="margin-top:16px;gap:22px">
        <label class="switch"><input type="checkbox" data-schoolauto ${sc.auto !== false ? 'checked' : ''}><span class="tr"></span><span>Tự chuyển lớp theo thời khóa biểu</span></label>
        ${(sc.source === 'manual') ? '<button class="btn" data-act="schoolclear">↩ Quay lại theo lịch</button>' : ''}
      </div>
      <p class="hint" style="margin-bottom:0">Tên lớp hiện tại hiện ở góc trên bên phải và được ghi vào từng vi phạm (lọc được ở trang Vi phạm). Lịch đổi đột xuất thì bấm tên một lớp ở dưới để đặt làm lớp hiện tại${sc.auto === false ? '' : ' (có hiệu lực 45 phút rồi tự quay lại theo lịch)'}.</p>
    </section>
    <section class="card"><div class="toolbar" style="margin-bottom:10px"><b>Nhập dữ liệu</b><span class="grow"></span></div>
      ${S.schoolErr ? `<div class="note warn" style="margin-bottom:10px">⚠ ${esc(S.schoolErr)}</div>` : ''}
      <div class="row" style="gap:12px;flex-wrap:wrap">
        <button class="btn primary" data-act="schoolimport" data-kind="classes">📥 Nhập danh sách lớp</button>${info(sc.classes_file, sc.classes_at)}
        <input type="file" id="schoolFile_classes" data-schoolfile="classes" accept=".xlsx,.xlsm,.json" class="hidden">
        <button class="btn" data-kq="rosters" title="Lấy danh sách học sinh từ tài khoản KhoaQuiz đã liên kết (gộp, lớp khác giữ nguyên)">☁ Lấy từ KhoaQuiz</button>
      </div>
      <div class="row" style="gap:12px;flex-wrap:wrap;margin-top:10px">
        <button class="btn primary" data-act="schoolimport" data-kind="timetable">📥 Nhập thời khóa biểu</button>${info(sc.timetable_file, sc.timetable_at)}
        <input type="file" id="schoolFile_timetable" data-schoolfile="timetable" accept=".xlsx,.xlsm,.xls" class="hidden">
      </div>
      <p class="hint" style="margin-bottom:0">Danh sách lớp: file điểm danh của trường (mỗi lớp một sheet, tên lớp ở ô E2, họ tên ở cột C), thay toàn bộ danh sách; hoặc file <b>.json</b> xuất từ KhoaTool (Thống kê → Xuất cho KhoaVeyon) hay nút <b>Lấy từ KhoaQuiz</b>, chỉ cập nhật các lớp có trong đó. Thời khóa biểu: bảng tiết × thứ, ô ghi tên lớp. File chỉ được đọc để lấy dữ liệu, không gửi xuống máy học sinh. Nhập lại bất cứ lúc nào để cập nhật.</p>
      ${(sc.unknown || []).length ? `<div class="note warn" style="margin-top:10px">Lớp có trong thời khóa biểu nhưng không có trong danh sách lớp: <b>${sc.unknown.map(esc).join(', ')}</b></div>` : ''}
    </section>
    ${schoolTemplateCard(sc)}
    <section class="card"><div class="toolbar" style="margin-bottom:10px"><b>Thời khóa biểu</b>${sc.subject || sc.teacher ? `<span class="muted">${esc([sc.subject, sc.teacher].filter(Boolean).join(' · '))}${sc.from ? ' · từ ' + esc(sc.from.split('-').reverse().join('/')) : ''}</span>` : ''}</div>${grid}</section>
    <section class="card"><div class="toolbar" style="margin-bottom:10px"><b>Các lớp</b><span class="muted">${cls.length} lớp · ${total} học sinh</span><span class="grow"></span></div>${chips}
      ${cls.length ? `<div class="row" style="margin-top:12px;gap:8px;flex-wrap:wrap"><span class="muted">Xem danh sách học sinh:</span>${cls.map(c => `<button class="btn ghost sm" data-act="schoolstudents" data-cls="${esc(c.name)}">${esc(c.name)}</button>`).join('')}</div>` : ''}
    </section></div>`;
}
