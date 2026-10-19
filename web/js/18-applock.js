// KhoaVeyon - Khóa màn hình ứng dụng giáo viên (mật khẩu, mặc định 0000)
function showLock(status) {
  if (status && typeof status.idle_min !== 'undefined') S.applock = status;
  S.appLocked = true;
  if ($('#lockscreen')) return;   // đã hiện rồi thì không dựng lại (giữ ô đang gõ)
  const dft = S.applock && S.applock.is_default;
  const el = document.createElement('div');
  el.id = 'lockscreen'; el.className = 'lockscreen';
  el.innerHTML = `<div class="lockbox">
      <div class="lk-logo"><img src="/assets/icon.svg" alt=""></div>
      <h2>Màn hình đang khóa</h2>
      <p class="muted">Nhập mật khẩu để tiếp tục dùng KhoaVeyon.</p>
      <form id="lockForm" autocomplete="off">
        <input type="password" id="lockPw" placeholder="Mật khẩu" autocomplete="off">
        <button class="btn primary" type="submit">Mở khóa</button>
        <div class="lk-err" id="lockErr"></div>
      </form>
      ${dft ? '<p class="lk-hint">Mật khẩu mặc định là <b>0000</b>. Nên đổi mật khẩu ở Cài đặt sau khi mở khóa.</p>' : ''}</div>`;
  document.body.appendChild(el);
  el.querySelector('#lockForm').onsubmit = async ev => {
    ev.preventDefault();
    try {
      S.applock = await api('/api/applock', {action: 'unlock', pin: $('#lockPw').value});
      hideLock();
    } catch (e) { $('#lockErr').textContent = e.message; const i = $('#lockPw'); i.value = ''; i.focus(); }
  };
  setTimeout(() => { const i = $('#lockPw'); if (i) i.focus(); }, 60);
}

function hideLock() {
  S.appLocked = false;
  const el = $('#lockscreen'); if (el) el.remove();
  lockActivity();
  render(); pollAlerts();
}

async function lockNow() {
  try { S.applock = await api('/api/applock', {action: 'lock'}); showLock(S.applock); }
  catch (e) { toast(e.message, 'err'); }
}

// Tự khóa khi không thao tác sau S.applock.idle_min phút (0 = tắt)
let lockIdleTimer = null;
function lockActivity() {
  clearTimeout(lockIdleTimer);
  const m = S.applock && +S.applock.idle_min;
  if (!m || S.appLocked) return;
  lockIdleTimer = setTimeout(lockNow, m * 60000);
}
['mousemove', 'keydown', 'mousedown', 'touchstart', 'wheel'].forEach(ev =>
  document.addEventListener(ev, () => { if (!S.appLocked) lockActivity(); }, {passive: true}));

// Thẻ trong trang Cài đặt
function appLockCard() {
  const a = S.applock || {};
  return `<section class="card"><h3>Khóa màn hình ứng dụng</h3>
    <p class="sub">Khi rời máy, bấm <b>🔒 Khóa</b> ở góc trên để che giao diện sau một mật khẩu, tránh học sinh lên chỉnh cài đặt hay gửi lệnh. Khi đang khóa, chương trình từ chối mọi thao tác cho tới khi nhập đúng mật khẩu.${a.is_default ? ' <b style="color:#b45309">Đang dùng mật khẩu mặc định 0000 — nên đổi.</b>' : ''}</p>
    <div class="formgrid">
      <div><label class="field">Mật khẩu hiện tại</label><input type="password" id="alCur" autocomplete="off" placeholder="Mặc định 0000"></div>
      <div><label class="field">Mật khẩu mới</label><input type="password" id="alNew" autocomplete="off" placeholder="Ít nhất 4 ký tự"></div>
      <div><label class="field">Nhập lại mật khẩu mới</label><input type="password" id="alNew2" autocomplete="off"></div>
    </div>
    <div class="row" style="margin-top:12px;gap:10px;align-items:center">
      <button class="btn primary" data-act="alsetpw">Đổi mật khẩu</button>
      <button class="btn" data-act="locknow">🔒 Khóa ngay</button>
      <span class="grow"></span>
      <span class="row" style="gap:8px"><span class="muted">Tự khóa khi không thao tác sau</span><input type="number" id="alIdle" min="0" max="240" value="${esc(a.idle_min || 0)}" style="width:68px" class="xsel"><span class="muted">phút (0 = tắt)</span><button class="btn ghost" data-act="alidle">Lưu</button></span>
    </div>
    <p class="hint" style="margin-bottom:0">Mật khẩu chỉ lưu dạng băm ở <code>data\\applock.json</code>, không hiện lại và không khôi phục được nếu quên. Quên thì xóa file này để trở về mặc định 0000.</p></section>`;
}
