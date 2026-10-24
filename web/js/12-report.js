// KhoaVeyon - Trang Báo cáo và xem ảnh phóng to
/* ---------- báo cáo cuối buổi ---------- */
async function loadReport() { S.report = await api('/api/report?range=' + encodeURIComponent(S.reportRange)); }

function viewReport() {
  const r = S.report;
  const ranges = {'2h': 'Hai giờ qua', today: 'Hôm nay', week: 'Tuần này', '7d': '7 ngày qua', month: 'Tháng này', '30d': '30 ngày qua', all: 'Tất cả'};
  const head = `<section class="card"><div class="toolbar" style="margin-bottom:0">
      <select id="reportRange">${Object.entries(ranges).map(([k, v]) => `<option value="${k}" ${S.reportRange === k ? 'selected' : ''}>${v}</option>`).join('')}</select>
      <button class="btn" data-act="reportreload">↻ Làm mới</button><span class="grow"></span>
      <button class="btn primary" data-act="reportexport">📊 Xuất Excel</button>
      <button class="btn primary" data-act="reportprint" title="Mở báo cáo kèm ảnh và tên học sinh, bấm In rồi chọn Lưu thành PDF">🖨 Báo cáo in / PDF</button>
      <button class="btn" data-kq="ktexport" title="File JSON tình hình buổi học hôm nay (vắng, máy hỏng, vi phạm, Veyon) để nhập vào KhoaTool">📤 Xuất cho KhoaTool</button>
      <button class="btn ghost" data-act="openreports">Mở thư mục báo cáo</button></div>
      <p class="hint" style="margin:12px 0 0">Một “lần vi phạm” là các ảnh liên tiếp của cùng một máy và cùng một trang/ứng dụng (cách nhau dưới ${r ? r.gap : 60} giây), nên học sinh ở yên một trang chỉ tính một lần.</p></section>`;
  if (!r || !r.episodes) return `<div class="stack">${head}<div class="empty">Chưa có vi phạm trong khoảng “${esc(ranges[S.reportRange])}”.</div></div>`;
  const maxH = Math.max(...r.by_host.map(h => h.count)), maxI = Math.max(...r.by_item.map(i => i.count)), maxHr = Math.max(...r.by_hour.map(h => h.count));
  const top = r.by_item[0], worst = r.by_host[0], peak = r.by_hour.reduce((a, b) => b.count > a.count ? b : a);
  const tagOf = t => `<span class="tag ${esc(t)}">${t === 'site' ? 'Trang web' : (t === 'ai' ? 'Công cụ AI' : 'Ứng dụng')}</span>`;
  const hostRows = r.by_host.map(h => `<tr><td><b>${esc(hn(h.host))}</b></td><td class="barcell"><div class="bar" style="width:${Math.round(h.count / maxH * 100)}%"></div></td><td><b>${h.count}</b> lần <span class="muted">(${h.shots} ảnh)</span></td><td class="muted">${h.top.map(t => esc(t.name) + ' ×' + t.count).join(', ')}</td></tr>`).join('');
  const itemRows = r.by_item.map(i => `<tr><td><b>${esc(i.name)}</b> ${tagOf(i.type)}</td><td class="barcell"><div class="bar" style="width:${Math.round(i.count / maxI * 100)}%"></div></td><td><b>${i.count}</b> lần · ${i.hosts} máy</td><td class="act">${i.type === 'ai' ? '' : `<button class="btn" data-act="allowadd" data-type="${esc(i.type)}" data-name="${esc(i.name)}" title="Thêm vào ${i.type === 'site' ? 'danh sách trang web' : 'danh sách ứng dụng'} được phép">＋ Cho phép</button>`}</td></tr>`).join('');
  const maxDay = Math.max(1, ...r.by_day.map(d => d.count)), maxWd = Math.max(1, ...r.by_weekday.map(w => w.count));
  const dayChart = r.by_day.length > 1 ? `<div class="hours">${r.by_day.slice(-31).map(d => `<div><i style="height:${Math.round(d.count / maxDay * 70)}px" title="${esc(d.date)}: ${d.count} lần"></i>${esc(d.date.slice(8))}</div>`).join('')}</div><p class="hint" style="margin-bottom:0">Số lần vi phạm mỗi ngày (số dưới cột là ngày trong tháng), và theo thứ trong tuần ở hàng dưới.</p>` : '<p class="muted" style="margin:0">Chọn khoảng thời gian dài hơn (tuần này, tháng này) để thấy xu hướng theo ngày.</p>';
  const repeatCard = r.repeat_students.length ? `<section class="card"><h3>Học sinh tái phạm <span class="badge">${r.repeat_students.length}</span></h3><table class="tbl"><thead><tr><th>Học sinh</th><th>Lớp</th><th>Số ngày vi phạm</th><th>Số lần</th></tr></thead><tbody>${r.repeat_students.map(x => `<tr><td><b>${esc(x.student)}</b></td><td>${esc(x.cls)}</td><td>${x.days}</td><td>${x.count}</td></tr>`).join('')}</tbody></table><p class="hint" style="margin-bottom:0">Học sinh vi phạm ở từ 2 ngày khác nhau trở lên trong khoảng đã chọn. Tên lấy theo sơ đồ chỗ ngồi lúc vi phạm.</p></section>` : '';
  const chronicCard = r.chronic_items.length ? `<section class="card"><h3>Trang / ứng dụng bị vào lặp lại nhiều ngày</h3><table class="tbl"><thead><tr><th>Nội dung</th><th>Số ngày</th><th>Số lần</th><th>Số máy</th></tr></thead><tbody>${r.chronic_items.map(x => `<tr><td><b>${esc(x.name)}</b> ${tagOf(x.type)}</td><td>${x.days}</td><td>${x.count}</td><td>${x.hosts}</td></tr>`).join('')}</tbody></table><p class="hint" style="margin-bottom:0">Vào lặp lại từ 3 ngày khác nhau: nếu cần cho bài học thì thêm vào danh sách được phép, nếu không thì cân nhắc chặn hẳn hoặc nhắc nhở.</p></section>` : '';
  const sug = r.suggest.length ? `<div class="note warn" style="margin:0">Các trang này có từ 3 máy trở lên cùng vào: <b>${r.suggest.map(esc).join(', ')}</b>. Có thể là trang cần cho bài học, hãy cân nhắc bấm “＋ Cho phép”. Nếu không thì nhắc nhở cả lớp.</div>` : '';
  return `<div class="stack">${head}
    <div class="stats">
      <div class="stat"><div class="n">${r.episodes}</div><div class="l">lần vi phạm (${r.shots} ảnh)</div></div>
      <div class="stat"><div class="n">${r.machines}</div><div class="l">máy có vi phạm</div></div>
      <div class="stat"><div class="n" style="font-size:20px">${esc(hn(worst.host))}</div><div class="l">vi phạm nhiều nhất: ${worst.count} lần</div></div>
      <div class="stat"><div class="n" style="font-size:20px;word-break:break-all">${esc(top.name)}</div><div class="l">bị vào nhiều nhất: ${top.count} lần, ${top.hosts} máy</div></div>
      <div class="stat"><div class="n">${esc(peak.hour)}h</div><div class="l">giờ cao điểm (${peak.count} lần)</div></div>
    </div>
    ${sug}
    <section class="card"><h3>Theo máy</h3><table class="tbl"><thead><tr><th>Máy</th><th></th><th>Số lần</th><th>Hay vào</th></tr></thead><tbody>${hostRows}</tbody></table></section>
    <section class="card"><h3>Theo trang web / ứng dụng</h3><table class="tbl"><thead><tr><th>Nội dung</th><th></th><th>Số lần</th><th></th></tr></thead><tbody>${itemRows}</tbody></table>
      <p class="hint" style="margin-bottom:0">“＋ Cho phép” chỉ thêm dòng vào danh sách. Hãy mở trang “Trang web được phép” hoặc “Ứng dụng được phép” rồi bấm Lưu để áp dụng.</p></section>
    <section class="card"><h3>Xu hướng theo ngày</h3>${dayChart}
      <div class="hours" style="margin-top:12px">${r.by_weekday.map(w => `<div><i style="height:${Math.round(w.count / maxWd * 70)}px" title="${w.label}: ${w.count} lần"></i>${esc(w.label.replace('Thứ ', 'T').replace('Chủ nhật', 'CN'))}</div>`).join('')}</div></section>
    ${repeatCard}${chronicCard}
    <section class="card"><h3>Theo giờ</h3><div class="hours">${r.by_hour.map(h => `<div><i style="height:${Math.round(h.count / maxHr * 70)}px" title="${h.count} lần"></i>${esc(h.hour)}h</div>`).join('')}</div></section>
  </div>`;
}

function lightbox(e) {
  const el = document.createElement('div');
  el.className = 'lightbox';
  el.innerHTML = `<img src="${imgUrl(e)}" alt=""><div class="cap">${e.student ? `🎓 <b>${esc(e.student)}</b>${e.cls ? ' · Lớp ' + esc(e.cls) : ''} · ` : (e.cls ? 'Lớp ' + esc(e.cls) + ' · ' : '')}<b>${esc(hn(e.host))}</b> · ${esc(e.text)}<br>${esc(e.date)} ${esc(e.time)}${e.user ? ' · ' + esc(e.user) : ''}${e.window ? '<br>' + esc(e.window) : ''}${(e.recent || []).length ? `<div class="lbrec">${recentLog(e)}</div>` : ''}</div>`;
  el.querySelector('.lbrec') && (el.querySelector('.lbrec').onclick = ev => ev.stopPropagation());   // bấm vào nhật ký thì không đóng ảnh
  const close = () => { el.remove(); document.removeEventListener('keydown', onKey); };
  const onKey = ev => { if (ev.key === 'Escape') close(); };
  document.addEventListener('keydown', onKey);
  el.onclick = close;
  document.body.appendChild(el);
}
