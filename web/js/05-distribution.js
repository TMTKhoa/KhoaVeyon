// KhoaVeyon - Trang Phân phối và chạy
/* ---------- trang: Phân phối & chạy ---------- */
function fmtSize(n) { return n > 1048576 ? (n / 1048576).toFixed(1) + ' MB' : n > 1024 ? Math.round(n / 1024) + ' KB' : n + ' B'; }

function viewDist() {
  const c = S.st.cfg, skip = new Set(c.dist_payload_skip || []);
  const files = S.payload.map((f, i) => `<div class="file"><input type="checkbox" data-pl="${i}" ${skip.has(f.name) ? '' : 'checked'}><span>${f.dir ? '📁' : '📄'}</span><span class="nm">${esc(f.name)}</span><span class="sz">${f.dir ? 'thư mục' : fmtSize(f.size)}</span><button class="iconbtn del" title="Xóa khỏi thư mục payload" data-act="delpl" data-i="${i}">✕</button></div>`).join('');
  const extra = (c.dist_files || []).map((p, i) => `<div class="file"><span>📎</span><span class="nm">${esc(p)}</span><button class="iconbtn del" data-act="delextra" data-i="${i}">✕</button></div>`).join('');
  const opts = S.st.actions.map(a => `<option value="${esc(a.key)}" ${a.key === c.dist_action ? 'selected' : ''}>${esc(a.label)}</option>`).join('');
  const t = targets();
  const mode = c.dist_mode;
  const rc = (v, t1, d) => `<div class="rc ${mode === v ? 'on' : ''}" data-act="mode" data-v="${v}"><b>${t1}</b><span>${d}</span></div>`;
  return `<div class="steps">
    <section class="card">
      <h3><span class="stepno">1</span>Chọn nội dung cần chép</h3>
      <label class="switch" style="margin-bottom:12px"><input type="checkbox" data-cfg="dist_include_lists" ${c.dist_include_lists ? 'checked' : ''}><span class="tr"></span><span>Kèm 4 file Excel danh sách (ứng dụng được phép, trang web được phép, ứng dụng bị chặn, trang AI bị chặn)</span></label>
      <div class="hint">File trong thư mục <b>payload</b> của chương trình (bỏ tick để không chép):</div>
      <div class="files">${files || '<div class="empty">Thư mục payload đang trống. Bấm "Thêm file" để tải file lên, ví dụ KhoaVeyonServices.bat.</div>'}${extra}</div>
      <div class="row"><button class="btn primary sm" data-act="upload">＋ Thêm file</button><input type="file" id="fileInput" multiple class="hidden"><button class="btn sm" data-act="addextra">Thêm theo đường dẫn</button><button class="btn ghost sm" data-act="openpayload">Mở thư mục payload</button></div>
      <div style="margin-top:16px"><label class="field">Thư mục đích trên máy học sinh</label>
        <input type="text" data-cfg="dist_target" value="${esc(c.dist_target)}" style="max-width:360px">
        <div class="hint" style="margin-top:6px">Máy học sinh đã cài Agent thì chép thẳng qua Agent (không cần tài khoản quản trị). Máy chưa cài Agent thì chép qua chia sẻ quản trị (\\\\máy\\C$), khi đó tài khoản đang đăng nhập trên máy này phải là quản trị viên trên máy học sinh.</div></div>
    </section>
    <section class="card">
      <h3><span class="stepno">2</span>Chọn cách chạy sau khi chép</h3>
      <div class="radiocards">
        ${rc('none', 'Chỉ chép file', 'Không chạy gì thêm.')}
        ${rc('schtasks', 'Chạy lệnh Windows', 'Tạo tác vụ trên máy học sinh rồi chạy ngay (schtasks).')}
        ${rc('veyon', 'Kích hoạt mục Veyon', 'Dùng veyon-cli như các nút ở trang Điều khiển lớp.')}
      </div>
      <div style="margin-top:16px">
      ${mode === 'schtasks' ? `<label class="field">Lệnh chạy trên máy học sinh</label><input type="text" data-cfg="dist_cmd" value="${esc(c.dist_cmd)}">
        <label class="switch" style="margin-top:12px"><input type="checkbox" data-cfg="dist_interactive" ${c.dist_interactive ? 'checked' : ''}><span class="tr"></span><span>Hiện cửa sổ cho học sinh (chạy bằng tài khoản đang đăng nhập, chưa kiểm chứng)</span></label>
        <p class="hint">Mặc định chạy bằng quyền SYSTEM nên học sinh không thấy cửa sổ, phù hợp script nền như KhoaVeyonServices.bat. Muốn mở ứng dụng có giao diện thì bật tùy chọn trên.</p>` : ''}
      ${mode === 'veyon' ? `<label class="field">Mục Veyon cần kích hoạt</label><select data-cfg="dist_action">${opts}</select>` : ''}
      </div>
    </section>
    <section class="card">
      <h3><span class="stepno">3</span>Thực hiện</h3>
      <p class="sub">Áp dụng cho <b>${t.all ? 'tất cả ' + t.hosts.length : t.hosts.length}</b> máy ${t.all ? '(chưa chọn máy cụ thể ở trang Điều khiển lớp)' : 'đã chọn'}.</p>
      <div class="row"><button class="btn primary" data-act="dist" data-copy="1" data-run="1">▶ Phân phối rồi chạy</button><button class="btn" data-act="dist" data-copy="1" data-run="0">Chỉ phân phối</button><button class="btn" data-act="dist" data-copy="0" data-run="1">Chỉ chạy</button></div>
      <div style="margin-top:18px"><label class="switch"><input type="checkbox" data-cfg="auto_push" ${c.auto_push ? 'checked' : ''}><span class="tr"></span><span>Tự động gửi file danh sách xuống máy học sinh mỗi khi bấm Lưu ở các trang danh sách</span></label></div>
    </section>
  </div>`;
}

async function loadPayload() { S.payload = (await api('/api/payload')).items; }

async function saveCfg(part) {
  try { await api('/api/settings', part); Object.assign(S.st.cfg, part); }
  catch (e) { toast(e.message, 'err'); }
}

async function runDist(copy, run) {
  const c = S.st.cfg;
  const hosts = await resolveTargets(); if (!hosts) return;
  const skip = new Set(c.dist_payload_skip || []);
  const payload = S.payload.filter(f => !skip.has(f.name)).map(f => f.name);
  const mode = c.dist_mode;
  if (run && mode === 'none') { toast('Hãy chọn cách chạy ở bước 2.', 'warn'); return; }
  const steps = [];
  if (copy) steps.push(`chép file sang <b>${esc(c.dist_target)}</b>`);
  if (run && mode === 'schtasks') steps.push(`chạy lệnh <code>${esc(c.dist_cmd)}</code>`);
  if (run && mode === 'veyon') steps.push(`kích hoạt mục Veyon "<b>${esc(action(c.dist_action).label)}</b>"`);
  const ok = await modal({title: 'Xác nhận', ok: 'Thực hiện', html: `Trên <b>${hosts.length}</b> máy sẽ:<ul style="margin:8px 0 0;padding-left:20px"><li>${steps.join('</li><li>')}</li></ul>`});
  if (!ok) return;
  try {
    await api('/api/dist', {copy, run, mode, hosts, include_lists: c.dist_include_lists, payload, extra: c.dist_files || [],
      target: c.dist_target, cmd: c.dist_cmd, action: c.dist_action, interactive: c.dist_interactive});
    toast('Đã bắt đầu, xem kết quả từng máy ở Nhật ký', 'ok'); openLog();
  } catch (e) { toast(e.message, 'err'); }
}

async function uploadFiles(files) {
  for (const f of files) {
    try {
      const sid = slowStart('/api/upload');
      const r = await fetch('/api/upload?name=' + encodeURIComponent(f.name), {method: 'PUT', headers: {'X-Token': TOKEN}, body: f}).finally(() => slowEnd(sid));
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || 'Lỗi tải lên');
      toast('Đã thêm ' + f.name, 'ok');
    } catch (e) { toast(f.name + ': ' + e.message, 'err'); }
  }
  await loadPayload(); render();
}
