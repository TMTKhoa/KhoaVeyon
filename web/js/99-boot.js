// KhoaVeyon - Khởi động
/* ---------- khởi động ---------- */
(async function init() {
  try {
    S.st = await api('/api/state');
  } catch (e) {
    $('#view').innerHTML = `<div class="note warn">${esc(e.message)}</div>`; return;
  }
  S.hosts = S.st.cfg.hosts.slice();
  S.page = S.st.cfg.setup_done ? 'control' : 'setup';
  if (S.page === 'setup') { try { await loadSetup(); } catch (e) { toast(e.message, 'err'); } }
  buildNav(); render(true);
  pollLog();
  pollAlerts(); setInterval(pollAlerts, 1500);
  refreshHostNames(); setInterval(refreshHostNames, 15000);
  try { S.applock = await api('/api/applock', undefined, {quiet: true}); lockActivity(); } catch (e) { /* bỏ qua */ }
  // Quay lại cửa sổ sau khi làm việc khác (hoặc có thay đổi từ máy chủ như tự động theo tiết): nạp lại dữ liệu lớp và sơ đồ
  let syncing = false;
  const resync = async () => {
    if (syncing || document.hidden || !['seats', 'school'].includes(S.page)) return;
    if ($('#modalroot') && $('#modalroot').innerHTML.trim()) return;   // đang mở hộp thoại thì không làm mới
    const ae = document.activeElement;
    if (ae && /^(INPUT|TEXTAREA|SELECT)$/.test(ae.tagName)) return;
    syncing = true;
    try { S.stu = {}; await loadSchool(); render(); } catch (e) { /* bỏ qua */ } finally { syncing = false; }
  };
  document.addEventListener('visibilitychange', resync);
  window.addEventListener('focus', resync);
  setTimeout(async () => { try { S.st.update = (await api('/api/state', undefined, {quiet: true})).update; showUpdate(); } catch (e) { /* bỏ qua */ } }, 6000);
})();
