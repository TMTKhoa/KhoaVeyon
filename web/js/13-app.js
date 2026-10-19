// KhoaVeyon - Khung ứng dụng: menu, chuyển trang, xử lý bấm/nhập, nhật ký
/* ---------- điều hướng và vẽ lại ---------- */
function buildNav() {
  $('#nav').innerHTML = PAGES.map(p => p.grp ? `<div class="grp">${p.grp}</div>`
    : `<button data-page="${p.id}" class="${S.page === p.id ? 'on' : ''}${p.id === 'viol' && S.unseen ? ' alerting' : ''}"><span class="ic">${p.ic}</span><span class="tx">${esc(p.name)}</span>${p.id === 'viol' && S.unseen ? `<span class="nbadge">${S.unseen > 99 ? '99+' : S.unseen}</span>` : ''}</button>`).join('');
}

async function go(id) {
  S.page = id;
  if (id === 'viol') { S.unseen = 0; S.freshFrom = S.seenSeq || 0; S.seenSeq = S.alertSeq; }
  const p = PAGES.find(x => x.id === id);
  buildNav();   // đánh dấu mục menu ngay khi bấm
  const ph = setTimeout(() => { if (S.page === id) { const v = $('#view'); if (v) v.innerHTML = `<div class="loadview"><div class="slowring"></div><div><b>Đang mở trang ${esc(p.title || p.name || '')}...</b><div class="muted">Đang lấy dữ liệu, vui lòng chờ một chút.</div></div></div>`; } }, 250);
  try {
    if (p.list && !S.lists[p.list]) await loadList(p.list);
    if (id === 'dist') await loadPayload();
    if (id === 'setup') await loadSetup();
    if (id === 'vcfg') await loadVcfg();
    if (id === 'report') await loadReport();
    if (id === 'school' || id === 'seats') await loadSchool();
    if (id === 'auto') await loadAuto();
    if (id === 'settings') S.startup = await api('/api/startup', {});
    if (id === 'exam') { await loadExam(); await examReload(); }
  } catch (e) { toast(e.message, 'err'); }
  clearTimeout(ph);
  if (S.page !== id) return;   // đã bấm sang trang khác trong lúc chờ
  if (id === 'seats' && S.logOpen && typeof toggleLog === 'function') toggleLog();   // thu gọn nhật ký để sơ đồ có đủ chỗ
  buildNav(); render(true);
  if (id === 'status') pollStatus(true);
}

function render(top) {
  const main = $('#main'), keep = main.scrollTop;
  const p = PAGES.find(x => x.id === S.page);
  const m = p.list ? S.st.lists[p.list] : null;
  $('#title').textContent = m ? m.title : p.title;
  $('#sub').textContent = m ? 'Sửa nội dung file Excel bằng giao diện, không cần mở Excel.' : p.sub;
  const v = $('#view');
  if (S.page === 'setup') v.innerHTML = viewSetup();
  else if (S.page === 'control') v.innerHTML = viewControl();
  else if (S.page === 'status') v.innerHTML = viewStatus();
  else if (S.page === 'auto') v.innerHTML = viewAuto();
  else if (S.page === 'exam') v.innerHTML = viewExam();
  else if (S.page === 'dist') v.innerHTML = viewDist();
  else if (S.page === 'vcfg') v.innerHTML = viewVcfg();
  else if (S.page === 'viol') v.innerHTML = viewViol();
  else if (S.page === 'school') v.innerHTML = viewSchool();
  else if (S.page === 'seats') v.innerHTML = viewSeatsPage();
  else if (S.page === 'report') v.innerHTML = viewReport();
  else if (S.page === 'settings') v.innerHTML = viewSettings();
  else v.innerHTML = viewList(p.list);
  if (p.list) applyFilter(p.list);
  main.scrollTop = top ? 0 : keep;
  document.body.classList.toggle('seatmode', S.page === 'seats');
  fitSeats(); if (S.page === 'seats') setTimeout(fitSeats, 350);
  const st = S.st;
  updWatchInfo(); updClassBadge(); showUpdate(); $('#verTxt').textContent = 'Quản lý lớp học · v' + st.version; $('#verNum').textContent = 'v' + st.version; updSideBtn();
  $('#statusDot').className = 'dot ' + (st.veyon_cli_found ? 'ok' : 'bad');
  $('#statusTxt').textContent = st.veyon_cli_found ? 'Đã tìm thấy veyon-cli' : 'Chưa thấy veyon-cli';
  $('#status').title = st.veyon_cli_path + (st.veyon_cli_found ? '' : ' (không tồn tại, bấm để mở Cài đặt)');
}

/* ---------- sự kiện ---------- */
document.addEventListener('click', async e => {
  const nav = e.target.closest('[data-page]');
  if (nav) { go(nav.dataset.page); return; }
  const el = e.target.closest('[data-act]');
  if (!el) return;
  const act = el.dataset.act, i = +el.dataset.i;
  const p = PAGES.find(x => x.id === S.page), kind = p.list;
  switch (act) {
    case 'setupall': setupStep('all', false); break;
    case 'setupveyon': setupStep('veyon', false); break;
    case 'setupkeys': setupStep('authkeys', true); break;
    case 'setuplists': setupStep('lists', false); break;
    case 'setuppayload': setupStep('payload', false); break;
    case 'diagnose': setupStep('diagnose', true); break;
    case 'pushsetup': setupStep('push', true); break;
    case 'veyonkit': if (await modal({title: 'Gửi Setup-MayHocSinh.bat qua Veyon?', ok: 'Gửi', html: 'Veyon sẽ mở bộ cài trên máy học sinh. Mỗi máy hiện hộp thoại UAC: cần có người bấm <b>Yes</b> (tài khoản thường thì nhập mật khẩu quản trị). Máy phải đang có người đăng nhập Windows.'})) setupStep('veyonkit', true); break;
    case 'lockcmd': if (await modal({title: 'Khóa thư mục C:\\cmd?', ok: 'Khóa', html: 'Học sinh sẽ chỉ đọc và chạy được file trong C:\\cmd, không sửa hay xóa được. Giáo viên vẫn cập nhật qua KhoaVeyon. Máy học sinh phải dùng tài khoản người dùng thường.'})) setupStep('lock', true); break;
    case 'unlockcmd': setupStep('unlock', true); break;
    case 'scan': scanHosts(); break;
    case 'aistatus': { const hs = await resolveTargets(); if (!hs) break; try { await api('/api/ai_status', {hosts: hs}); openLog(); L.pending++; updBusy(); pollSoon(); setTimeout(() => { L.pending = Math.max(0, L.pending - 1); updBusy(); }, 4000); toast(`Đang kiểm tra ${hs.length} máy`, 'ok'); } catch (err) { toast(err.message, 'err'); } break; }
    case 'shot': { const hs = await resolveTargets(); if (!hs) break; try { await api('/api/shot', {hosts: hs}); openLog(); L.pending++; updBusy(); pollSoon(); setTimeout(() => { L.pending = Math.max(0, L.pending - 1); updBusy(); }, 4000); toast(`Đang chụp màn hình ${hs.length} máy`, 'ok'); } catch (err) { toast(err.message, 'err'); } break; }
    case 'watch_start': case 'watch_stop': case 'watch_fetch': { const hs = await resolveTargets(); if (!hs) break; const step = act.slice(6); try { await api('/api/watch', {step, hosts: hs}); openLog(); L.pending++; updBusy(); pollSoon(); setTimeout(() => { L.pending = Math.max(0, L.pending - 1); updBusy(); }, 4000); toast(`Đã gửi lệnh tới ${hs.length} máy`, 'ok'); } catch (err) { toast(err.message, 'err'); } break; }
    case 'notice': {
      const txt = (($('#noticeText') || {}).value || '').trim(), secs = parseInt((($('#noticeSecs') || {}).value), 10) || 20;
      if (!txt) { toast('Nhập nội dung thông báo', 'warn'); break; }
      const hs = await resolveTargets(); if (!hs) break;
      try { await api('/api/notice', {text: txt, seconds: secs, hosts: hs}); openLog(); L.pending++; updBusy(); pollSoon(); setTimeout(() => { L.pending = Math.max(0, L.pending - 1); updBusy(); }, 4000); toast(`Đang gửi thông báo tới ${hs.length} máy`, 'ok'); } catch (err) { toast(err.message, 'err'); }
      break; }
    case 'variantload': {
      const n = (($('#variantSel') || {}).value || '');
      if (!n) { toast('Chọn một bản riêng trong danh sách', 'warn'); break; }
      try {
        const r = await api('/api/list_variant?kind=' + kind + '&name=' + encodeURIComponent(n));
        const L2 = S.lists[kind]; L2.rows = r.rows.map(x => ({a: x[0], b: x[1]})); L2.warn = Object.fromEntries(r.warnings.map(w => [w.row, w.msg]));
        markDirty(kind); render(); toast(`Đã tải bản "${n}" vào bảng. Bấm Lưu nếu muốn dùng làm danh sách chính.`, 'ok');
      } catch (err) { toast(err.message, 'err'); }
      break; }
    case 'variantsave': {
      const v = await modal({title: 'Lưu bảng thành bản riêng', ok: 'Lưu', collect: r => r.querySelector('input').value.trim(), html: '<input type="text" class="xsel" style="width:100%" placeholder="Ví dụ: Kiểm tra Văn">'});
      if (!v) break;
      try {
        const L2 = S.lists[kind];
        const r = await api('/api/list_variant_save', {kind, name: v, rows: L2.rows.filter(x => x.a.trim()).map(x => [x.a.trim(), x.b.trim()])});
        L2.variants = r.variants; toast(`Đã lưu bản riêng "${r.name}" (${r.count} dòng). Chọn nó trong “Chế độ lớp” ở trang Tự động theo tiết.`, 'ok'); render();
      } catch (err) { toast(err.message, 'err'); }
      break; }
    case 'variantdel': {
      const n = (($('#variantSel') || {}).value || '');
      if (!n) { toast('Chọn bản riêng cần xóa', 'warn'); break; }
      if (!(await modal({title: 'Xóa bản riêng "' + n + '"?', ok: 'Xóa', danger: true, html: 'Chế độ lớp nào đang dùng bản này sẽ quay về danh sách chính.'}))) break;
      try { const r = await api('/api/list_variant_delete', {kind, name: n}); S.lists[kind].variants = r.variants; render(); toast('Đã xóa bản riêng', 'ok'); } catch (err) { toast(err.message, 'err'); }
      break; }
    case 'pinunlock': case 'pinlock': case 'pinset': case 'pinclear': {
      let body = {action: act === 'pinunlock' ? 'unlock' : act === 'pinlock' ? 'lock' : act === 'pinset' ? 'set' : 'clear'};
      if (act === 'pinunlock' || act === 'pinclear') {
        const v = await modal({title: act === 'pinunlock' ? 'Nhập mã xem ảnh' : 'Bỏ mã xem ảnh', ok: act === 'pinunlock' ? 'Mở khóa' : 'Bỏ mã', danger: act === 'pinclear', collect: r => r.querySelector('input').value, html: '<input type="password" class="xsel" style="width:100%" autocomplete="off" placeholder="Mã hiện tại">'});
        if (v === null) break; body.pin = v;
      } else if (act === 'pinset') {
        const has = S.privacy && S.privacy.pin_set;
        const v = await modal({title: has ? 'Đổi mã xem ảnh' : 'Đặt mã xem ảnh', ok: 'Lưu mã', collect: r => [...r.querySelectorAll('input')].map(i => i.value), html: `<p class="hint" style="margin-top:0">Có mã thì ảnh vi phạm bị khóa, phải nhập mã mới xem được (tự khóa lại sau 15 phút). Mã không được lưu dạng chữ và không khôi phục được nếu quên (bỏ mã cũng cần nhập mã).</p>${has ? '<input type="password" class="xsel" style="width:100%;margin-bottom:8px" autocomplete="off" placeholder="Mã hiện tại">' : ''}<input type="password" class="xsel" style="width:100%" autocomplete="off" placeholder="Mã mới (ít nhất 4 ký tự)">`});
        if (v === null) break; body.pin = has ? v[0] : ''; body.new_pin = has ? v[1] : v[0];
      }
      try { S.privacy = await api('/api/privacy_pin', body); render(); toast(act === 'pinunlock' ? 'Đã mở khóa ảnh' : act === 'pinlock' ? 'Đã khóa ảnh' : act === 'pinset' ? 'Đã lưu mã xem ảnh' : 'Đã bỏ mã xem ảnh', 'ok'); } catch (err) { toast(err.message, 'err'); }
      break; }
    case 'privacyacl': try { S.privacy = await api('/api/privacy_acl', {on: el.dataset.on === '1'}); render(); toast(S.privacy.acl ? 'Đã giới hạn quyền đọc thư mục ảnh' : 'Đã trả lại quyền thư mục ảnh', 'ok'); } catch (err) { toast(err.message, 'err'); } break;
    case 'gopage': go(el.dataset.pageTo); break;
    case 'reportreload': try { await loadReport(); render(); } catch (err) { toast(err.message, 'err'); } break;
    case 'reportexport': try { const r = await api('/api/report_export', {range: S.reportRange}); toast('Đã xuất báo cáo: ' + r.path, 'ok'); api('/api/open', {what: 'reports'}).catch(() => {}); } catch (err) { toast(err.message, 'err'); } break;
    case 'reportprint': try { const r = await api('/api/report_export', {range: S.reportRange, format: 'html'}); toast('Đã tạo báo cáo để in hoặc lưu PDF: ' + r.path, 'ok'); } catch (err) { toast(err.message, 'err'); } break;
    case 'openreports': api('/api/open', {what: 'reports'}).catch(err => toast(err.message, 'warn')); break;
    case 'allowadd': {
      const k = el.dataset.type === 'site' ? 'allow' : 'keep', name = el.dataset.name;
      try {
        if (!S.lists[k]) await loadList(k);
        const n = addRows(k, [[name, 'Thêm từ báo cáo ' + new Date().toLocaleDateString('vi-VN')]]);
        toast(n ? `Đã thêm "${name}". Mở trang “${k === 'allow' ? 'Trang web được phép' : 'Ứng dụng được phép'}” và bấm Lưu để áp dụng.` : `"${name}" đã có trong danh sách`, n ? 'ok' : 'warn');
        el.disabled = true; el.textContent = n ? '✓ Đã thêm' : '✓ Đã có';
      } catch (err) { toast(err.message, 'err'); }
      break; }
    case 'cleanup': {
      const d = +S.st.cfg.keep_days || 0;
      if (!d) { toast('Đang để 0 ngày (không tự xóa). Nhập số ngày muốn giữ ảnh.', 'warn'); break; }
      if (await modal({title: 'Dọn ảnh cũ?', ok: 'Dọn ngay', danger: true, html: `Xóa ảnh và bản ghi vi phạm cũ hơn <b>${d} ngày</b> trên máy này. Không hoàn tác được.`})) {
        try { const r = await api('/api/cleanup', {}); S.alerts = S.alerts.filter(x => x.ts >= r.cutoff); toast(`Đã xóa ${r.images} ảnh, ${r.records} bản ghi, ${r.shots} thư mục ảnh chụp`, 'ok'); render(); }
        catch (err) { toast(err.message, 'err'); }
      }
      break; }
    case 'viewimg': { const ev = S.alerts[+el.dataset.i]; if (ev) lightbox(ev); break; }
    case 'galview': { const ev = galState().items[+el.dataset.gi]; if (ev) lightbox(ev); break; }
    case 'violtab': S.violTab = el.dataset.tab; if (S.violTab === 'gallery') galState().loaded = false; render(); break;
    case 'galrange': galRange(el.dataset.r); await loadGallery(); break;
    case 'galreset': { const g = galState(); g.f = {from: '', to: '', cls: '', host: '', student: '', type: '', q: ''}; await loadGallery(); break; }
    case 'galreload': await loadGallery(); break;
    case 'galmore': await loadGallery(true); break;
    case 'evopen': api('/api/evidence_open', {img: el.dataset.img}).catch(err => toast(err.message, 'warn')); break;
    case 'evopen_dir': api('/api/evidence_open', {date: el.dataset.date, cls: el.dataset.cls}).catch(err => toast(err.message, 'warn')); break;
    case 'evopen_today': api('/api/evidence_open', {date: todayIso()}).catch(err => toast(err.message, 'warn')); break;
    case 'evopen_filter': { const f = galState().f; api('/api/evidence_open', f.from && f.from === f.to ? {date: f.from, cls: f.cls} : {}).catch(err => toast(err.message, 'warn')); break; }
    case 'alertclear': if (await modal({title: 'Xóa danh sách vi phạm?', ok: 'Xóa danh sách', danger: true, html: 'Danh sách trên màn hình sẽ được làm trống. Ảnh vẫn còn trong thư mục <code>data\\evidence</code>.'})) { try { await api('/api/alerts_clear', {}); S.alerts = []; S.unseen = 0; render(); } catch (err) { toast(err.message, 'err'); } } break;
    case 'openevidence': api('/api/open', {what: 'evidence'}).catch(err => toast(err.message, 'warn')); break;
    case 'locknow': await lockNow(); break;
    case 'selftest': await runSelftest(); break;
    case 'seatproject': projectSeats(); break;
    case 'aioptsave': {
      const o = {}; document.querySelectorAll('[data-aiopt]').forEach(x => { o[x.dataset.aiopt] = x.checked; });
      try { await api('/api/ai_opts', o); Object.assign(S.st.cfg, o); const m = $('#aiOptMsg'); if (m) m.textContent = 'Đã lưu'; toast('Đã lưu tùy chọn khóa AI', 'ok'); }
      catch (err) { toast(err.message, 'err'); }
      break; }
    case 'alsetpw': {
      const cur = $('#alCur').value, nw = $('#alNew').value, nw2 = $('#alNew2').value;
      try { S.applock = await api('/api/applock', {action: 'setpin', pin: cur, new_pin: nw, confirm: nw2}); toast('Đã đổi mật khẩu khóa màn hình', 'ok'); render(); }
      catch (err) { toast(err.message, 'err'); }
      break; }
    case 'alidle': {
      try { S.applock = await api('/api/applock', {action: 'idle', idle_min: $('#alIdle').value}); lockActivity(); toast('Đã lưu thời gian tự khóa', 'ok'); }
      catch (err) { toast(err.message, 'err'); }
      break; }
    case 'openshots': api('/api/open', {what: 'shots'}).catch(err => toast(err.message, 'warn')); break;
    case 'vc_backup_master': case 'vc_backup_clients': case 'vc_compare': case 'vc_restore_master': case 'vc_restore_clients':
    case 'vc_addrow': case 'vc_delrow': case 'vc_savepush': case 'vc_push': case 'vc_netobj': case 'vc_netobj_scan': vcAction(act, el); break;
    case 'refreshsetup': refreshSetup(); break;
    case 'gosettings': go('settings'); break;
    case 'checkupd': checkUpdate(); break;
    case 'applyupd': applyUpdate(); break;
    case 'notesupd': modal({title: 'Thay đổi ' + S.st.update.latest, noCancel: true, ok: 'Đóng', html: '<div style="white-space:pre-wrap">' + esc(S.st.update.notes || 'Không có ghi chú.') + '</div>'}); break;
    case 'run': runAction(el.dataset.key); break;
    case 'selall': S.hosts.forEach(h => S.sel.add(h)); render(); break;
    case 'selnone': S.sel.clear(); render(); break;
    case 'rmhost': S.sel.delete(S.hosts[i]); S.hosts.splice(i, 1); saveHosts(); render(); break;
    case 'copycmd': {
      const a = action($('#copySel').value);
      const text = 'cmd.exe /c ' + S.st.cfg.script_path + ' ' + a.switch;
      try { await navigator.clipboard.writeText(text); toast('Đã sao chép: ' + text, 'ok'); }
      catch (err) { await modal({title: 'Sao chép lệnh', noCancel: true, ok: 'Đóng', html: `<input type="text" value="${esc(text)}" readonly onfocus="this.select()">`}); }
      break;
    }
    case 'addrow': { const L = S.lists[kind]; L.rows.push({a: '', b: ''}); markDirty(kind); render();
      const ins = document.querySelectorAll('#rows input[data-f=a]'); if (ins.length) ins[ins.length - 1].focus(); break; }
    case 'delrow': S.lists[kind].rows.splice(i, 1); markDirty(kind); scheduleCheck(kind); render(); break;
    case 'up': case 'down': {
      const rows = S.lists[kind].rows, j = act === 'up' ? i - 1 : i + 1;
      if (j >= 0 && j < rows.length) { [rows[i], rows[j]] = [rows[j], rows[i]]; markDirty(kind); scheduleCheck(kind); render(); }
      break;
    }
    case 'preset': { const n = addRows(kind, S.st.lists[kind].presets[el.dataset.name]); toast(n ? `Đã thêm ${n} dòng` : 'Các dòng này đã có trong danh sách', n ? 'ok' : 'warn'); render(); break; }
    case 'paste': {
      const text = await modal({title: 'Dán nhiều dòng', ok: 'Thêm vào danh sách',
        html: `<p class="hint" style="margin-top:0">Mỗi dòng một mục. Có thể dán từ Excel (cột A và cột B) hoặc từ Notepad.</p><textarea id="pasteTxt" placeholder="chrome&#10;mspaint&#10;notepad"></textarea>`,
        collect: r => r.querySelector('#pasteTxt').value});
      if (text) {
        const items = text.split(/\r?\n/).map(l => l.split('\t')).map(c => [(c[0] || '').trim(), (c[1] || '').trim()]).filter(c => c[0]);
        const n = addRows(kind, items); toast(n ? `Đã thêm ${n} dòng` : 'Không có dòng mới để thêm', n ? 'ok' : 'warn'); render();
      }
      break;
    }
    case 'reload': {
      if (S.lists[kind].dirty && !(await modal({title: 'Bỏ thay đổi?', html: 'Các thay đổi chưa lưu sẽ bị mất.', ok: 'Tải lại', danger: true}))) break;
      try { await loadList(kind); render(); toast('Đã tải lại từ file', 'ok'); } catch (err) { toast(err.message, 'err'); }
      break;
    }
    case 'save': saveList(kind, false); break;
    case 'saveapply': saveList(kind, true); break;
    case 'mode': await saveCfg({dist_mode: el.dataset.v}); render(); break;
    case 'upload': $('#fileInput').click(); break;
    case 'schoolimport': $('#schoolFile_' + el.dataset.kind).click(); break;
    case 'schoolset': await schoolSet({action: 'set', cls: el.dataset.cls}); break;
    case 'seatpick': await seatPick(+el.dataset.n); break;
    case 'layopen': S.layOpen = !S.layOpen; render(); break;
    case 'attoggle': await attAct({action: 'toggle', name: el.dataset.name}); break;
    case 'attpresent': await attAct({action: 'present'}); break;
    case 'attrecheck': toast('Đang kiểm tra máy bật/tắt...'); await attAct({action: 'recheck'}); break;
    case 'announce': await seatAnnounce(false); break;
    case 'announceclear': await seatAnnounce(true); break;
    case 'seatauto': await seatAuto(); break;
    case 'seatclear': await seatSave({seats: {}}); break;
    case 'seatall': await seatSave({}, true); toast('Đã áp dụng kiểu phòng này cho tất cả các lớp', 'ok'); break;
    case 'schoolclear': await schoolSet({action: 'clear'}); break;
    case 'schoolstudents': {
      try {
        const r = await api('/api/school_students?cls=' + encodeURIComponent(el.dataset.cls));
        await modal({title: `Lớp ${el.dataset.cls} (${r.names.length} học sinh)`, ok: 'Đóng', noCancel: true,
          html: `<ol style="margin:0;padding-left:34px;max-height:52vh;overflow:auto;columns:2;column-gap:28px">${r.names.map(n => `<li>${esc(n)}</li>`).join('')}</ol>`});
      } catch (err) { toast(err.message, 'err'); }
      break;
    }
    case 'addextra': {
      const v = await modal({title: 'Thêm theo đường dẫn', ok: 'Thêm', html: '<p class="hint" style="margin-top:0">Đường dẫn đầy đủ của file hoặc thư mục trên máy này, ví dụ D:\\Phanmem\\setup.exe</p><input type="text" id="pathTxt" placeholder="D:\\Phanmem\\setup.exe">', collect: r => r.querySelector('#pathTxt').value.trim()});
      if (v) { const l = (S.st.cfg.dist_files || []).concat([v.replace(/^"|"$/g, '')]); await saveCfg({dist_files: l}); render(); }
      break;
    }
    case 'delextra': { const l = S.st.cfg.dist_files.slice(); l.splice(i, 1); await saveCfg({dist_files: l}); render(); break; }
    case 'delpl': {
      const f = S.payload[i];
      if (await modal({title: 'Xóa file?', danger: true, ok: 'Xóa', html: `Xóa <b>${esc(f.name)}</b> khỏi thư mục payload trên máy này?`})) {
        try { await api('/api/payload_delete', {name: f.name}); await loadPayload(); render(); } catch (err) { toast(err.message, 'err'); }
      }
      break;
    }
    case 'openpayload': api('/api/open', {what: 'payload'}).catch(err => toast(err.message, 'warn')); break;
    case 'openlists': api('/api/open', {what: 'lists'}).catch(err => toast(err.message, 'warn')); break;
    case 'opendata': api('/api/open', {what: 'data'}).catch(err => toast(err.message, 'warn')); break;
    case 'dist': runDist(el.dataset.copy === '1', el.dataset.run === '1'); break;
    case 'savesettings': saveSettings(); break;
    case 'syncnow': {
      try { await saveSettings(); const r = await api('/api/sync', {}); toast(`Đã đồng bộ ${r.count} file`, 'ok'); openLog(); } catch (err) { toast(err.message, 'err'); }
      break;
    }
    case 'veyonlist': {
      try { await api('/api/veyon_list', {host: S.hosts[0] || ''}); toast('Đang chạy, xem kết quả ở Nhật ký', 'ok'); openLog(); } catch (err) { toast(err.message, 'err'); }
      break;
    }
  }
});

document.addEventListener('submit', e => {
  e.preventDefault();
  if (e.target.dataset.form === 'addhost') {
    const inp = $('#hostInput'), n = addHosts(inp.value);
    if (!n && inp.value.trim()) toast('Máy này đã có trong danh sách', 'warn');
    render(); const x = $('#hostInput'); if (x) x.focus();
  }
});

document.addEventListener('input', e => {
  const t = e.target;
  const p = PAGES.find(x => x.id === S.page);
  if (t.dataset.f && p.list) { S.lists[p.list].rows[+t.dataset.i][t.dataset.f] = t.value; markDirty(p.list); if (t.dataset.f === 'a') scheduleCheck(p.list); }
  else if (t.id === 'filter') { S.lists[p.list].filter = t.value; applyFilter(p.list); }
  else if (t.dataset.gal === 'q') {   // gõ tìm: giữ chữ đang gõ (trang tự vẽ lại khi có vi phạm mới), lọc sau khi ngừng gõ 0,4 giây
    galState().f.q = t.value; clearTimeout(S.galTimer);
    S.galTimer = setTimeout(async () => { await loadGallery(); const x = document.querySelector('[data-gal="q"]'); if (x) { x.focus(); x.setSelectionRange(x.value.length, x.value.length); } }, 400);
  }
});

document.addEventListener('change', async e => {
  const t = e.target;
  if (t.dataset.host !== undefined) { const h = S.hosts[+t.dataset.host]; t.checked ? S.sel.add(h) : S.sel.delete(h); render(); }
  else if (t.dataset.pl !== undefined) {
    const skip = new Set(S.st.cfg.dist_payload_skip || []), name = S.payload[+t.dataset.pl].name;
    t.checked ? skip.delete(name) : skip.add(name);
    await saveCfg({dist_payload_skip: [...skip]});
  }
  else if (t.id === 'violFilter') { S.violHost = t.value; render(); }
  else if (t.id === 'seatClsSel') { S.seatCls = t.value; try { await seatNames(); } catch (err) { /* bỏ qua */ } await loadAtt(); render(); }
  else if (t.dataset.attset) { await attAct({action: 'setting', [t.dataset.attset]: t.checked}); }
  else if (t.dataset.lay) { await seatSave({[t.dataset.lay]: t.value}); }
  else if (t.id === 'violCls') { S.violCls = t.value; render(); }
  else if (t.dataset.gal) { galState().f[t.dataset.gal] = t.value; await loadGallery(); }
  else if (t.dataset.schoolfile) { await schoolUpload(t.dataset.schoolfile, t.files[0]); t.value = ''; }
  else if (t.dataset.schoolauto !== undefined) { await schoolSet({action: 'auto', value: t.checked}); }
  else if (t.id === 'reportRange') { S.reportRange = t.value; try { await loadReport(); render(); } catch (err) { toast(err.message, 'err'); } }
  else if (t.dataset.cfg) { await saveCfg({[t.dataset.cfg]: t.type === 'checkbox' ? t.checked : t.value}); if (t.dataset.cfg === 'auto_push') render(); }
  else if (t.id === 'fileInput') { await uploadFiles(t.files); t.value = ''; }
});

$('#status').onclick = () => go('settings');
$('#classBadge').onclick = () => go('school');
$('#lockBtn').onclick = () => lockNow();
$('#quitBtn').onclick = async () => {
  if (!(await modal({title: 'Thoát KhoaVeyon?', html: 'Cửa sổ sẽ đóng. Các lệnh đang chạy nền có thể bị dừng.', ok: 'Thoát', danger: true}))) return;
  try { await api('/api/quit', {}); } catch (e) { /* đang đóng */ }
  document.body.insertAdjacentHTML('beforeend', '<div class="bye"><div><div style="font-size:54px">👋</div><h2>Đã thoát KhoaVeyon</h2><p class="muted">Bạn có thể đóng cửa sổ này.</p></div></div>');
  setTimeout(() => window.close(), 600);
};

/* ---------- nhật ký ---------- */
function openLog() { if (!S.logOpen) toggleLog(true); }
function toggleLog(v) {
  S.logOpen = v === undefined ? !S.logOpen : v;
  $('#logdock').classList.toggle('closed', !S.logOpen);
  $('#main').classList.toggle('logclosed', !S.logOpen);
  $('#logToggle').textContent = S.logOpen ? 'Thu gọn ▾' : 'Mở rộng ▴';
}
$('#loghead').onclick = e => { if (!e.target.closest('#logClear')) toggleLog(); };
$('#logClear').onclick = () => { $('#logbody').innerHTML = ''; $('#logcount').textContent = ''; };

let logLines = 0;
async function pollLog() {
  try {
    const r = await api('/api/log?since=' + S.logSeq);
    S.logSeq = r.last;
    if (r.items.length) {
      const body = $('#logbody'), atEnd = body.scrollTop + body.clientHeight >= body.scrollHeight - 30;
      body.insertAdjacentHTML('beforeend', r.items.map(x => `<div class="ln ${x.kind}"><span class="t">${x.t}</span>${esc(x.msg)}</div>`).join(''));
      logLines += r.items.length; $('#logcount').textContent = logLines + ' dòng';
      if (atEnd) body.scrollTop = body.scrollHeight;
    }
    S.busy = !!r.busy; L.serverBusy = !!r.busy; L.jobs = r.jobs || []; if (r.busy) L.pending = 0; updBusy();
  } catch (e) { /* mất kết nối tạm thời */ }
  clearTimeout(L.timer);
  L.timer = setTimeout(pollLog, (L.serverBusy || L.pending) ? 350 : 1500);   // đang chạy thì hỏi dày hơn
}


/* ---------- Trạng thái máy, bật/tắt máy hàng loạt (3.4.0) ---------- */
S.stat = null; S.auto = null; S.autoDirty = false;
