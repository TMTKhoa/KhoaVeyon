// KhoaVeyon - Trang Cài đặt và cập nhật phần mềm
/* ---------- trang: Cài đặt ---------- */
function viewSettings() {
  const c = S.st.cfg;
  const f = (k, label, hint) => `<div><label class="field">${label}</label><input type="text" data-set="${k}" value="${esc(c[k])}">${hint ? `<div class="hint" style="margin-top:5px">${hint}</div>` : ''}</div>`;
  const feats = S.st.actions.map(a => `<tr><td style="width:46%">${a.icon} ${esc(a.label)}</td><td><input type="text" class="cell" style="border:1px solid #d3dae8!important" data-feat="${esc(a.key)}" value="${esc(c.features[a.key] || '')}"></td></tr>`).join('');
  return `<div class="steps">
    <section class="card"><h3>Đường dẫn</h3><div class="formgrid">
      ${f('list_dir', 'Thư mục chứa 4 file Excel', 'Có thể ghi đường dẫn tương đối (ví dụ lists) hoặc đầy đủ (ví dụ C:\\cmd).')}
      ${f('script_path', 'Đường dẫn script trên máy học sinh', 'Dùng khi sao chép lệnh để dán vào Veyon.')}
      ${f('veyon_cli', 'veyon-cli.exe', 'Tự tìm nếu để trống hoặc sai: thư mục veyon cạnh chương trình, PATH, Program Files.')}
      ${f('sync_dir', 'Thư mục đồng bộ (tùy chọn)', 'Thư mục chia sẻ mà máy học sinh đọc danh sách.')}
    </div>
    <div style="margin-top:16px"><label class="switch"><input type="checkbox" data-set="auto_sync" ${c.auto_sync ? 'checked' : ''}><span class="tr"></span><span>Tự đồng bộ sang thư mục đồng bộ mỗi khi bấm Lưu ở trang danh sách</span></label></div>
    <div class="row" style="margin-top:16px"><button class="btn" data-act="syncnow">Đồng bộ ngay</button><button class="btn ghost" data-act="openlists">Mở thư mục danh sách</button><button class="btn ghost" data-act="opendata">Mở thư mục dữ liệu</button></div></section>
    <section class="card"><h3>Mẫu lệnh Veyon</h3><div class="formgrid">
      <div class="full">${f('run_template', 'Lệnh chạy một mục', 'Dùng {cli} {host} {feature}. Cú pháp veyon-cli có thể khác theo phiên bản Veyon, nên hãy thử bằng nút bên dưới.')}</div>
      <div class="full">${f('list_template', 'Lệnh liệt kê các mục', '')}</div></div>
      <div class="row" style="margin-top:14px"><button class="btn" data-act="veyonlist">Kiểm tra kết nối Veyon (liệt kê mục của máy đầu tiên)</button></div></section>
    <section class="card"><h3>Tên các mục trong Veyon</h3><p class="sub">Tên mục "Programs &amp; websites" mà bạn đã tạo trong Veyon Master cho từng chức năng.</p>
      <table class="tbl"><tbody>${feats}</tbody></table></section>
    <section class="card"><h3>Tự chạy khi mở máy</h3>
      ${S.startup && S.startup.supported ? `<label class="switch"><input type="checkbox" data-startup="1" ${S.startup.on ? 'checked' : ''}><span class="tr"></span><span>Tự chạy KhoaVeyon (nền, không mở cửa sổ) khi tôi đăng nhập Windows</span></label>
        <p class="hint" style="margin-bottom:0">Để hẹn giờ theo thời khóa biểu, giám sát và tự áp lại hạn chế hoạt động ngay từ đầu buổi mà không cần nhớ mở chương trình. Mở cửa sổ bằng Chay-KhoaVeyon.bat như thường. Chương trình đã chạy nền sẽ không tự thoát, bấm Thoát trong chương trình để dừng. Tắt công tắc để gỡ.</p>` : '<p class="sub" style="margin:0">Tính năng này chỉ có trên Windows.</p>'}
    </section>
    ${appLockCard()}
    ${kqSettingsCard()}
    <section class="card"><h3>Cập nhật phần mềm</h3>
      <p class="sub">Đang dùng phiên bản <b>${esc(S.st.version)}</b>. Chương trình hỏi mục Releases của kho GitHub (kho công khai) xem có bản mới không, chỉ thay file chương trình, giữ nguyên cài đặt, danh sách và payload.</p>
      <div class="formgrid"><div><label class="field">Kho GitHub</label><input type="text" data-set="update_repo" value="${esc(c.update_repo)}" placeholder="chủ-sở-hữu/tên-kho"><div class="hint" style="margin-top:5px">Mặc định TMTKhoa/KhoaVeyon. Mỗi bản mới cần tạo một Release có tag lớn hơn (v1.1.0) và đính kèm file zip.</div></div></div>
      <div style="margin-top:14px;display:flex;flex-direction:column;gap:12px">
        <label class="switch"><input type="checkbox" data-set="update_check" ${c.update_check ? 'checked' : ''}><span class="tr"></span><span>Tự kiểm tra bản mới mỗi lần khởi động</span></label>
        <label class="switch"><input type="checkbox" data-set="update_auto" ${c.update_auto ? 'checked' : ''}><span class="tr"></span><span>Tự cài và khởi động lại khi có bản mới (không khuyến khích, nên xem trước rồi bấm cập nhật)</span></label></div>
      <div class="row" style="margin-top:14px"><button class="btn" data-act="checkupd">Kiểm tra bản mới</button></div>
      <p class="hint">Bản cập nhật chạy bằng quyền của bạn và có thể gửi lệnh xuống máy học sinh. Chỉ dùng kho của chính bạn và bảo vệ tài khoản GitHub bằng xác thực hai bước.</p></section>
    <div class="savebar"><div class="grow hint">Cài đặt lưu tại: ${esc(S.st.config_path)}</div><button class="btn primary" data-act="savesettings">💾 Lưu cài đặt</button></div>
  </div>`;
}

async function saveSettings() {
  const part = {features: {}};
  document.querySelectorAll('[data-set]').forEach(el => { part[el.dataset.set] = el.type === 'checkbox' ? el.checked : el.value; });
  document.querySelectorAll('[data-feat]').forEach(el => { part.features[el.dataset.feat] = el.value; });
  try {
    await api('/api/settings', part);
    S.st = await api('/api/state');
    S.lists = {};
    toast('Đã lưu cài đặt', 'ok'); render(true);
  } catch (e) { toast(e.message, 'err'); }
}


function showUpdate() {
  const bar = $('#updbar'), u = S.st.update; if (typeof updSideBtn === 'function') updSideBtn();
  if (!u || !u.newer) { bar.classList.add('hidden'); return; }
  bar.classList.remove('hidden');
  bar.innerHTML = `🔔 Có bản mới <b>${esc(u.latest)}</b> (đang dùng ${esc(u.current)}). <button class="btn primary sm" data-act="applyupd" style="margin-left:10px">Cập nhật ngay</button> <button class="link" data-act="notesupd" style="margin-left:8px">Xem thay đổi</button>`;
}

async function checkUpdate() {
  const btn = $('#sideUpd');
  if (btn) { btn.disabled = true; btn.querySelector('span').textContent = 'Đang kiểm tra...'; }
  try {
    if (document.querySelector('[data-set="update_repo"]')) await saveSettings();   // đang ở trang Cài đặt: lưu kho GitHub vừa sửa
    const u = await api('/api/update_check');
    S.st.update = u; showUpdate(); updSideBtn();
    if (!u.newer) { toast(`Đang dùng bản mới nhất (v${u.current})`, 'ok'); return; }
    const warn = S.watching ? `<div class="note warn" style="margin:10px 0 0">Đang giám sát ${S.watching} máy. Chương trình sẽ khởi động lại trong vài giây.</div>` : '';
    const ok = await modal({title: `Có bản mới ${u.latest}`, ok: 'Cập nhật ngay', cancel: 'Để sau',
      html: `<p style="margin-top:0">Đang dùng <b>v${esc(u.current)}</b>, bản mới nhất là <b>${esc(u.latest)}</b>. Bạn có muốn cập nhật không?</p>
        ${u.notes ? `<div class="muted" style="margin-bottom:4px">Thay đổi:</div><div style="white-space:pre-wrap;max-height:34vh;overflow:auto;background:#f3f6fb;border-radius:10px;padding:10px 12px;font-size:13px">${esc(u.notes)}</div>` : ''}
        <p class="hint" style="margin-bottom:0">Chương trình tải bản mới, thay file chương trình rồi tự khởi động lại. Cài đặt, danh sách, lớp và sơ đồ chỗ ngồi được giữ nguyên; bản cũ được sao lưu trong data\\backup-${esc(u.current)}.</p>${warn}`});
    if (ok) { await api('/api/update_apply', {}); openLog(); toast('Đang cập nhật, cửa sổ mới sẽ tự mở sau vài giây', 'ok'); }
  } catch (e) { toast(e.message, 'err'); }
  finally { updSideBtn(); }
}

function updSideBtn() {
  const btn = $('#sideUpd'); if (!btn) return;
  const u = S.st && S.st.update, has = !!(u && u.newer);
  btn.disabled = false; btn.classList.toggle('has', has);
  btn.querySelector('span').textContent = has ? 'Có bản mới ' + u.latest : 'Kiểm tra cập nhật';
}

/* hộp thoại hỏi khi GitHub có bản mới: hỏi một lần cho mỗi bản, "Để sau" thì hỏi lại sau 4 giờ, "Bỏ qua" thì không hỏi nữa */
let updAsking = false;
async function maybeAskUpdate(u) {
  if (!u || u.skipped || !u.can_apply || updAsking) return;
  if (S.updAsked && S.updAsked.v === u.latest && Date.now() - S.updAsked.t < 4 * 3600 * 1000) return;
  if ($('#modalroot').innerHTML || S.busy) return;           // đang mở hộp thoại khác hoặc đang chạy lệnh: để lần sau
  updAsking = true;
  try {
    S.st.update = Object.assign({}, S.st.update, {newer: true, latest: u.latest, current: u.current, notes: u.notes, page: u.page}); showUpdate();
    const warn = S.watching ? `<div class="note warn" style="margin:10px 0 0">Đang giám sát ${S.watching} máy. Chương trình sẽ khởi động lại trong vài giây, phần giám sát trên máy học sinh vẫn chạy, ảnh vi phạm sẽ được nhận lại sau khi mở lại.</div>` : '';
    const r = await modal({title: `Có bản mới ${u.latest}`, ok: 'Cập nhật ngay', cancel: 'Để sau', third: {label: 'Bỏ qua bản này', value: 'skip'},
      html: `<p style="margin-top:0">KhoaVeyon trên GitHub của bạn vừa có bản <b>${esc(u.latest)}</b> (đang dùng ${esc(u.current)}). Bạn có muốn cập nhật không?</p>
        ${u.notes ? `<div class="muted" style="margin-bottom:4px">Thay đổi:</div><div style="white-space:pre-wrap;max-height:34vh;overflow:auto;background:#f3f6fb;border-radius:10px;padding:10px 12px;font-size:13px">${esc(u.notes)}</div>` : ''}
        <p class="hint" style="margin-bottom:0">Danh sách, lớp, sơ đồ chỗ ngồi và cài đặt của bạn được giữ nguyên. Bản cũ được sao lưu trước khi thay.</p>${warn}`});
    S.updAsked = {v: u.latest, t: Date.now()};
    if (r === 'skip') { await saveCfg({update_skip: u.latest}); toast('Sẽ không hỏi lại bản ' + u.latest + ' (có bản mới hơn thì hỏi tiếp)', 'ok'); }
    else if (r) {
      try { await api('/api/update_apply', {}); openLog(); toast('Đang cập nhật, cửa sổ mới sẽ tự mở sau vài giây', 'ok'); } catch (e) { toast(e.message, 'err'); }
    }
  } finally { updAsking = false; }
}

async function applyUpdate() {
  const u = S.st.update;
  if (!(await modal({title: 'Cập nhật lên ' + u.latest + '?', ok: 'Cập nhật', html: 'Chương trình sẽ tải bản mới, thay file chương trình (bản cũ được sao lưu trong data\\backup-' + esc(u.current) + ') rồi tự khởi động lại. Không mất cài đặt và danh sách.'}))) return;
  try {
    await api('/api/update_apply', {});
    openLog(); toast('Đang cập nhật, cửa sổ mới sẽ tự mở sau vài giây', 'ok');
  } catch (e) { toast(e.message, 'err'); }
}

document.addEventListener('change', async e => {
  const t = e.target;
  if (!t.dataset || !t.dataset.startup || S.page !== 'settings') return;
  try { S.startup = await api('/api/startup', {action: 'set', on: t.checked}); toast(S.startup.on ? 'Đã bật tự chạy khi đăng nhập Windows' : 'Đã tắt tự chạy', 'ok'); }
  catch (err) { toast(err.message, 'err'); t.checked = !t.checked; }
});
