// KhoaVeyon - Báo động và trang Vi phạm
/* ---------- báo động vi phạm ---------- */
const imgOk = e => !!e.img && !(S.privacy && S.privacy.blocked);   // ảnh có và chưa bị khóa bằng mã xem ảnh
const imgUrl = e => imgOk(e) ? '/evidence/' + e.img.split('/').map(encodeURIComponent).join('/') + '?t=' + encodeURIComponent(TOKEN) : '';
const kindLabel = e => e.type === 'site' ? 'Trang web' : (e.type === 'ai' ? 'Công cụ AI' : 'Ứng dụng');

function updWatchInfo() {
  const el = $('#watchInfo'); if (!el) return;
  el.textContent = S.watching ? `Đang nhận cảnh báo từ ${S.watching} máy` : 'Chưa bật giám sát';
}

function alertGap() { return Math.max(10, +S.st.cfg.alert_group_sec || 60); }
function fillAlertToast(g) {
  const e = g.last, n = g.count, secs = Math.round(g.last.ts - g.first.ts);
  const title = n > 1 ? `${esc(hn(e.host))} vi phạm liên tục` : `${esc(hn(e.host))} vừa vi phạm`;
  const more = n > 1 ? `<span class="cnt">${n} ảnh</span>` : '';
  const dur = n > 1 ? `<div class="sm">${n} ảnh trong ${secs < 60 ? secs + ' giây' : Math.round(secs / 60) + ' phút'}, mới nhất lúc ${esc(e.time)}</div>` : `<div class="sm">${esc(e.date)} ${esc(e.time)}${e.user ? ' · ' + esc(e.user) : ''}${e.window ? '<br>' + esc(e.window) : ''}</div>`;
  g.el.innerHTML = `${imgOk(e) ? `<img src="${imgUrl(e)}" alt="">` : ''}<div class="tt"><b>🚨 ${title}${more}</b>${esc(e.text)}${dur}</div><button class="xx" title="Đóng">×</button>`;
  g.el.querySelector('.xx').onclick = ev => { ev.stopPropagation(); g.el.remove(); };
}
function showAlert(e) {
  const key = e.host + '|' + e.type + '|' + e.name, gap = alertGap();
  let g = S.groupToasts[key];
  if (g && document.body.contains(g.el) && e.ts - g.last.ts <= gap) {   // cùng máy, cùng trang: cập nhật thông báo cũ, không tạo cái mới
    g.count++; g.last = e; fillAlertToast(g);
    clearTimeout(g.timer); g.timer = setTimeout(() => g.el.remove(), 20000);
    return;
  }
  const box = $('#toasts');
  const olds = [...box.querySelectorAll('.toast.alert')];
  while (olds.length >= 4) olds.shift().remove();
  const el = document.createElement('div');
  el.className = 'toast alert';
  g = S.groupToasts[key] = {el, count: 1, first: e, last: e, timer: null};
  fillAlertToast(g);
  el.onclick = ev => { if (!ev.target.closest('.xx')) go('viol'); el.remove(); };
  box.appendChild(el);
  g.timer = setTimeout(() => el.remove(), 20000);
}

let titleTimer = null;
function flashTitle(text) {
  clearInterval(titleTimer);
  let n = 0;
  titleTimer = setInterval(() => {
    document.title = (n++ % 2) ? 'KhoaVeyon' : '🚨 ' + text;
    if (n > 12 || document.hasFocus()) { clearInterval(titleTimer); document.title = 'KhoaVeyon'; }
  }, 800);
}

async function pollAlerts() {
  try {
    const r = await api('/api/alerts?since=' + S.alertSeq);
    S.watching = r.watching; updWatchInfo(); S.schoolBrief = r.school; updClassBadge(); maybeAskUpdate(r.update);
    if (r.privacy) { const was = S.privacy && S.privacy.blocked; S.privacy = r.privacy; if (S.page === 'viol' && !!was !== !!r.privacy.blocked) render(); }
    if (!S.alertInit) {                       // lần đầu: nạp lịch sử, không báo động lại việc cũ
      S.alerts = r.items; S.alertSeq = r.last; S.seenSeq = r.last; S.freshFrom = r.last; S.alertInit = true; return;
    }
    if (!r.items.length) return;
    S.alertSeq = r.last;
    S.alerts = S.alerts.concat(r.items).slice(-500);
    if (S.st.cfg.alert_popup !== false) r.items.slice(-30).forEach(showAlert);
    flashTitle(`${r.items[r.items.length - 1].host} vi phạm`);
    if (S.page === 'viol') { S.seenSeq = S.alertSeq; render(); } else { S.unseen += r.items.length; buildNav(); }
  } catch (e) { /* mất kết nối tạm thời */ }
}

function groupAlerts(list, gap) {
  const out = [], last = {};
  for (const e of list) {
    const k = e.host + '|' + e.type + '|' + e.name, g = last[k];
    if (g && e.ts - g.lastTs <= gap) { g.items.push(e); g.lastTs = e.ts; }
    else { const ng = {host: e.host, type: e.type, name: e.name, text: e.text, items: [e], firstTs: e.ts, lastTs: e.ts}; out.push(ng); last[k] = ng; }
  }
  return out.sort((a, b) => b.lastTs - a.lastTs);
}

const todayIso = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
const dmy = s => /^\d{4}-\d{2}-\d{2}$/.test(s || '') ? s.slice(8) + '/' + s.slice(5, 7) + '/' + s.slice(0, 4) : (s || '');
function violTabs() {
  const t = S.violTab || 'recent';
  return `<div class="row" style="gap:8px"><button class="btn ${t === 'recent' ? 'primary' : ''}" data-act="violtab" data-tab="recent">🚨 Vi phạm gần đây</button><button class="btn ${t === 'gallery' ? 'primary' : ''}" data-act="violtab" data-tab="gallery">🖼 Bộ sưu tập ảnh</button></div>`;
}

function viewViol() {
  if (S.violTab === 'gallery') return violTabs() + viewGallery();
  const st = S.st, c = st.cfg;
  const hostsIn = [...new Set(S.alerts.map(e => e.host))].sort();
  const clsIn = [...new Set(S.alerts.map(e => e.cls).filter(Boolean))].sort();
  const src = S.alerts.filter(e => (!S.violHost || e.host === S.violHost) && (!S.violCls || e.cls === S.violCls));
  const groups = groupAlerts(src, alertGap());
  const opts = `<option value="">Tất cả máy (${S.alerts.length} ảnh)</option>` + hostsIn.map(h => `<option value="${esc(h)}" ${S.violHost === h ? 'selected' : ''}>${esc(hn(h))} (${S.alerts.filter(e => e.host === h).length})</option>`).join('');
  const cards = groups.map(g => {
    const e = g.items[g.items.length - 1], n = g.items.length, fresh = g.items.some(x => x.id > (S.freshFrom || 0));
    const secs = Math.round(g.lastTs - g.firstTs);
    const thumbs = n > 1 ? `<div class="thumbs">${g.items.slice(-8).map(x => imgOk(x) ? `<img src="${imgUrl(x)}" alt="" loading="lazy" data-act="viewimg" data-i="${S.alerts.indexOf(x)}">` : '').join('')}</div>` : '';
    return `<div class="vcard ${fresh ? 'fresh' : ''}">
      ${imgOk(e) ? `<img class="shot" src="${imgUrl(e)}" alt="Ảnh vi phạm" loading="lazy" data-act="viewimg" data-i="${S.alerts.indexOf(e)}">` : (e.img && S.privacy && S.privacy.blocked ? `<div class="noimg">🔒 Ảnh đang khóa<br>(nhập mã xem ảnh ở đầu trang)</div>` : `<div class="noimg">Không có ảnh<br>(ảnh bị xóa hoặc chưa chép được)</div>`)}
      ${thumbs}
      <div class="vb">${e.img ? `<button class="btn ghost sm vopen" data-act="evopen" data-img="${esc(e.img)}" title="Mở thư mục chứa ảnh này (chọn sẵn ảnh)">📂</button>` : ''}<div class="pc">🖥 ${esc(hn(e.host))}<span class="tag ${esc(e.type)}">${kindLabel(e)}</span>${e.cls ? `<span class="tag" style="background:#e7f8ef;color:#15803d">Lớp ${esc(e.cls)}</span>` : ''}${n > 1 ? `<span class="cnt">${n} ảnh</span>` : ''}</div>
        <div class="what">${esc(e.text)}</div>
        <div class="meta">🕒 ${esc(e.time)} · ${esc(e.date)}${n > 1 ? ` (kéo dài ${secs < 60 ? secs + ' giây' : Math.round(secs / 60) + ' phút'})` : ''}${e.student ? `<br>🎓 <b>${esc(e.student)}</b> (máy ${e.seat})` : ''}${e.user ? '<br>👤 ' + esc(e.user) : ''}${e.window ? '<br>🪟 ' + esc(e.window) : ''}${recentLog(e)}</div></div></div>`;
  }).join('');
  return `${violTabs()}<div class="stack" style="margin-top:12px">
    <section class="card">
      <div class="toolbar" style="margin-bottom:0">
        <select id="violFilter" style="min-width:220px">${opts}</select>
        ${clsIn.length ? `<select id="violCls"><option value="">Tất cả lớp</option>${clsIn.map(c => `<option value="${esc(c)}" ${S.violCls === c ? 'selected' : ''}>Lớp ${esc(c)} (${S.alerts.filter(e => e.cls === c).length})</option>`).join('')}</select>` : ''}
        <span class="badge" id="watchInfo"></span><span class="grow"></span>
        <button class="btn" data-act="gopage" data-page-to="report">📊 Báo cáo</button>
        <button class="btn" data-act="gopage" data-page-to="control">👁 Bật / tắt giám sát</button>
        <button class="btn" data-act="evopen_today" title="Mở data\\evidence\\<hôm nay>">📂 Thư mục ảnh hôm nay</button>
        <button class="btn ghost" data-act="openevidence">Mở thư mục ảnh</button>
        <button class="btn danger" data-act="alertclear">Xóa danh sách</button>
      </div>
      <div class="row" style="margin-top:14px;gap:22px">
        <label class="switch"><input type="checkbox" data-cfg="alert_sound" ${c.alert_sound !== false ? 'checked' : ''}><span class="tr"></span><span>Kêu bíp khi có vi phạm</span></label>
        <button class="btn sm" data-act="alerttest" title="Phát thử một hồi bíp để kiểm tra loa máy giáo viên">🔔 Thử tiếng báo</button>
        <label class="switch"><input type="checkbox" data-cfg="alert_popup" ${c.alert_popup !== false ? 'checked' : ''}><span class="tr"></span><span>Hiện thông báo kèm ảnh</span></label>
        <span class="row" style="gap:8px"><span class="muted">Nhận ảnh mỗi</span><input type="text" data-cfg="alert_poll" value="${esc(c.alert_poll || '3')}" style="width:60px"><span class="muted">giây</span></span>
      </div>
      <div class="row" style="margin-top:12px;gap:8px"><span class="muted">Tên trường (ghi vào đầu tên file ảnh)</span><input type="text" data-cfg="school_name" maxlength="80" value="${esc(c.school_name || '')}" placeholder="Ví dụ: THPT Nguyễn Du" style="width:auto;flex:0 1 340px"></div>
      <div class="row" style="margin-top:12px;gap:8px;flex-wrap:wrap">
        <span class="muted">Lớp ghi cho vi phạm:</span>
        <select data-cfg="alert_cls_mode" style="width:auto">
          <option value="current" ${c.alert_cls_mode !== 'manual' ? 'selected' : ''}>Theo lớp hiện tại</option>
          <option value="manual" ${c.alert_cls_mode === 'manual' ? 'selected' : ''}>Thủ công</option>
        </select>
        ${c.alert_cls_mode === 'manual' ? `<input type="text" data-cfg="alert_cls_manual" list="alertClsList" value="${esc(c.alert_cls_manual || '')}" placeholder="Ví dụ: 5A4" style="width:110px"><datalist id="alertClsList">${((S.school && S.school.classes) || []).map(x => `<option value="${esc(x.name)}">`).join('')}</datalist>${c.alert_cls_manual ? '' : '<span class="muted">(chưa chọn lớp: tạm dùng lớp hiện tại)</span>'}` : ''}
      </div>
      <div class="row" style="margin-top:12px;gap:14px;flex-wrap:wrap">${privacyRow()}</div>
      <div class="row" style="margin-top:12px;gap:22px">
        <span class="row" style="gap:8px"><span class="muted">Gộp vi phạm giống nhau cách nhau dưới</span><input type="text" data-cfg="alert_group_sec" value="${esc(c.alert_group_sec || '60')}" style="width:60px"><span class="muted">giây (chỉ bíp một lần)</span></span>
        <span class="row" style="gap:8px"><span class="muted">Tự xóa ảnh sau</span><input type="text" data-cfg="keep_days" value="${esc(c.keep_days ?? '14')}" style="width:60px"><span class="muted">ngày, bản ghi chữ sau</span><input type="text" data-cfg="keep_records_days" value="${esc(c.keep_records_days ?? '180')}" style="width:60px"><span class="muted">ngày (0 = không xóa)</span><button class="btn" data-act="cleanup">🧹 Dọn ngay</button></span>
      </div>
      <p class="hint" style="margin-bottom:0">Mỗi vi phạm gồm ảnh màn hình, tên máy, tài khoản học sinh, nội dung (trang web hoặc ứng dụng), tiêu đề cửa sổ, ngày và giờ. Học sinh ở yên một trang thì nhiều ảnh được gộp thành một thẻ. Ảnh được xếp theo <code>data\\evidence\\&lt;ngày&gt;\\&lt;lớp&gt;</code>, tên file gồm trường, lớp, học sinh, máy, ngày giờ và trang/ứng dụng. Lịch sử nằm ở <code>data\\evidence\\violations.csv</code>. Ô viền đỏ là vi phạm mới kể từ lần xem trước. Thời hạn lưu ảnh nên theo quy định của nhà trường.</p>
    </section>
    ${groups.length ? `<div class="vgrid">${cards}</div>` : `<div class="empty">Chưa có vi phạm nào.<br>Bật giám sát ở trang “Điều khiển lớp”, khi học sinh mở trang web hoặc ứng dụng ngoài danh sách, ảnh sẽ tự hiện ở đây.</div>`}
  </div>`;
}

/* ---------- Bộ sưu tập ảnh vi phạm (mọi ảnh đã lưu, có bộ lọc) ---------- */
function galState() {
  if (!S.gal) S.gal = {f: {from: todayIso(), to: todayIso(), cls: '', host: '', student: '', type: '', q: ''}, items: [], total: 0, all: 0, facets: null, loaded: false};
  return S.gal;
}
async function loadGallery(more) {
  const g = galState();
  const qs = new URLSearchParams(Object.assign({}, g.f, {offset: more ? g.items.length : 0, limit: 120}));
  try {
    const r = await api('/api/gallery?' + qs.toString());
    g.items = more ? g.items.concat(r.items) : r.items; g.total = r.total; g.all = r.all; g.facets = r.facets; g.loaded = true;
  } catch (err) { toast(err.message, 'err'); }
  if (S.page === 'viol' && S.violTab === 'gallery') render();
}
function galRange(r) {
  const g = galState(), t = todayIso(), back = n => { const d = new Date(); d.setDate(d.getDate() - n); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
  if (r === 'today') { g.f.from = t; g.f.to = t; }
  else if (r === '7') { g.f.from = back(6); g.f.to = t; }
  else if (r === '30') { g.f.from = back(29); g.f.to = t; }
  else { g.f.from = ''; g.f.to = ''; }
}
function viewGallery() {
  const g = galState(), f = g.f, fc = g.facets || {dates: [], classes: [], hosts: [], students: []};
  if (!g.loaded) { loadGallery(); return `<div class="empty" style="margin-top:12px">Đang tải ảnh…</div>`; }
  const t = todayIso(), rangeOn = r => (r === 'today' && f.from === t && f.to === t) || (r === 'all' && !f.from && !f.to);
  const sel = (key, label, vals, fmt) => `<select data-gal="${key}"><option value="">${label}</option>${vals.map(v => `<option value="${esc(v)}" ${f[key] === v ? 'selected' : ''}>${esc(fmt ? fmt(v) : v)}</option>`).join('')}</select>`;
  const clsVals = fc.classes.concat(fc.no_class ? ['-'] : []);
  const oneDay = f.from && f.from === f.to;
  const openLabel = oneDay ? `📂 Mở thư mục ${dmy(f.from)}${f.cls ? ' / ' + (f.cls === '-' ? 'chưa rõ lớp' : 'lớp ' + f.cls) : ''}` : '📂 Mở thư mục ảnh';
  // nhóm theo ngày + lớp, giống cách xếp thư mục trên ổ đĩa
  const groups = [], byKey = {};
  g.items.forEach((e, i) => { const k = e.date + '|' + (e.cls || ''); let gr = byKey[k]; if (!gr) { gr = byKey[k] = {date: e.date, cls: e.cls || '', items: []}; groups.push(gr); } gr.items.push([e, i]); });
  groups.sort((a, b) => (b.date || '').localeCompare(a.date || '') || (!a.cls) - (!b.cls) || a.cls.localeCompare(b.cls, 'vi'));
  const tile = ([e, i]) => {
    const pic = !e.exists ? `<div class="noimg">Ảnh đã bị xóa<br>(quá hạn lưu)</div>` : (imgOk(e) ? `<img src="${imgUrl(e)}" alt="" loading="lazy" data-act="galview" data-gi="${i}">` : `<div class="noimg">🔒 Ảnh đang khóa</div>`);
    return `<div class="gtile">${pic}<div class="gcap"><div class="gl1">${e.student ? `🎓 <b>${esc(e.student)}</b>` : `🖥 <b>${esc(hn(e.host))}</b>`}<span class="tag ${esc(e.type)}">${kindLabel(e)}</span></div>
      <div class="gl2" title="${esc(e.window || '')}">${esc(e.name)}</div>
      <div class="gl3">🕒 ${esc(e.time)}${e.student ? ' · 🖥 ' + esc(hn(e.host)) : ''}${e.exists ? `<button class="btn ghost sm" data-act="evopen" data-img="${esc(e.img)}" title="Mở thư mục và chọn sẵn ảnh này">📂</button>` : ''}</div></div></div>`;
  };
  const body = groups.map(gr => `<div class="ghead"><b>📅 ${esc(dmy(gr.date))}</b> · ${gr.cls ? 'Lớp ' + esc(gr.cls) : '<span class="muted">Chưa rõ lớp</span>'} <span class="muted">(${gr.items.length} ảnh${g.items.length < g.total ? ' đã tải' : ''})</span>
      <button class="btn ghost sm" data-act="evopen_dir" data-date="${esc(gr.date)}" data-cls="${esc(gr.cls || '-')}">📂 Mở thư mục</button></div>
    <div class="ggrid">${gr.items.map(tile).join('')}</div>`).join('');
  return `<div class="stack" style="margin-top:12px">
    <section class="card">
      <div class="row gfilters" style="gap:8px;flex-wrap:wrap">
        <span class="chips">${[['today', 'Hôm nay'], ['7', '7 ngày'], ['30', '30 ngày'], ['all', 'Tất cả']].map(([r, l]) => `<button class="chip" data-act="galrange" data-r="${r}" ${rangeOn(r) ? 'style="background:var(--primary-l);border-style:solid"' : ''}>${l}</button>`).join('')}</span>
        <span class="muted">Từ</span><input type="date" data-gal="from" value="${esc(f.from)}"><span class="muted">đến</span><input type="date" data-gal="to" value="${esc(f.to)}">
      </div>
      <div class="row gfilters" style="gap:8px;flex-wrap:wrap;margin-top:10px">
        ${sel('cls', 'Tất cả lớp', clsVals, v => v === '-' ? 'Chưa rõ lớp' : 'Lớp ' + v)}
        ${sel('student', 'Tất cả học sinh', fc.students)}
        ${sel('host', 'Tất cả máy', fc.hosts, hn)}
        <select data-gal="type"><option value="">Mọi loại</option>${[['site', 'Trang web'], ['ai', 'Công cụ AI'], ['app', 'Ứng dụng']].map(([v, l]) => `<option value="${v}" ${f.type === v ? 'selected' : ''}>${l}</option>`).join('')}</select>
        <input type="search" data-gal="q" value="${esc(f.q)}" placeholder="Tìm trang, ứng dụng, tên…" style="min-width:200px">
        <button class="btn ghost" data-act="galreset">Bỏ lọc</button>
        <span class="grow"></span>
        <button class="btn" data-act="galreload">↻ Làm mới</button>
        <button class="btn primary" data-act="evopen_filter">${esc(openLabel)}</button>
      </div>
      <p class="hint" style="margin-bottom:0">${g.total} ảnh khớp bộ lọc (tổng ${g.all} ảnh đã lưu). Bấm ảnh để phóng to, 📂 để mở đúng thư mục trên máy. Ảnh nằm ở <code>data\\evidence\\&lt;ngày&gt;\\&lt;lớp&gt;</code>.</p>
    </section>
    ${g.items.length ? body : `<div class="empty">Không có ảnh nào khớp bộ lọc.${f.from ? '<br>Thử bấm “Tất cả” để xem mọi ngày.' : ''}</div>`}
    ${g.items.length < g.total ? `<div class="row" style="justify-content:center"><button class="btn" data-act="galmore">Tải thêm (${g.total - g.items.length} ảnh)</button></div>` : ''}
  </div>`;
}

function privacyRow() {
  const pr = S.privacy || {};
  const state = !pr.pin_set ? 'chưa đặt' : (pr.blocked ? '<b>đang khóa</b>' : `đang mở, tự khóa sau ${Math.max(1, Math.ceil((pr.left || 0) / 60))} phút`);
  return `<span class="muted">🔒 Mã xem ảnh: ${state}</span>
    ${pr.pin_set ? (pr.blocked ? '<button class="btn primary" data-act="pinunlock">Nhập mã để xem ảnh</button>' : '<button class="btn" data-act="pinlock">Khóa ảnh ngay</button>') : ''}
    <button class="btn ghost" data-act="pinset">${pr.pin_set ? 'Đổi mã' : 'Đặt mã xem ảnh'}</button>${pr.pin_set ? '<button class="btn ghost" data-act="pinclear">Bỏ mã</button>' : ''}
    ${pr.windows ? `<button class="btn ghost" data-act="privacyacl" data-on="${pr.acl ? '0' : '1'}" title="Chỉ tài khoản Windows đang chạy chương trình, quản trị viên và SYSTEM đọc được thư mục data\\evidence">${pr.acl ? '✔ Đang giới hạn quyền đọc thư mục ảnh (bấm để bỏ)' : 'Giới hạn quyền đọc thư mục ảnh'}</button>` : ''}`;
}


/* Nhật ký dùng máy trong ~5 phút trước và lúc vi phạm (do script giám sát trên máy học sinh ghi kèm ảnh) */
function recentLog(e) {
  const r = e.recent || []; if (!r.length) return '';
  const fd = d => d < 60 ? d + 's' : Math.round(d / 60) + ' phút';
  return `<details class="rlog"><summary>🕘 Em đã làm gì trong 5 phút trước (${r.length} mục)</summary><table class="tbl"><tbody>${r.slice().reverse().map(x => `<tr><td>${esc(x.t)}</td><td><b>${esc(x.p)}</b></td><td>${esc(x.w)}</td><td class="muted">${esc(fd(x.d))}</td></tr>`).join('')}</tbody></table></details>`;
}
