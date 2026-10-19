// KhoaVeyon - Trang cấu hình Veyon
/* ---------- trang: Cấu hình Veyon ---------- */
async function loadVcfg() { S.vcfg = await api('/api/vcfg_info'); }

function viewVcfg() {
  const v = S.vcfg, hosts = targets().hosts;
  const opt = (val, text, cur) => `<option value="${esc(val)}" ${cur === val ? 'selected' : ''}>${esc(text)}</option>`;
  const refs = (cur) => `<option value="">— chọn —</option>${opt('master', 'Máy master (hiện tại)', cur)}${hosts.map(h => opt('host:' + h, h + ' (đọc trực tiếp)', cur)).join('')}${v.backups.map(f => opt(f.name, f.name + ' · ' + f.time, cur)).join('')}`;
  const files = `<option value="">— chọn file sao lưu —</option>${v.backups.map(f => opt(f.name, f.name + ' · ' + f.time, S.vcF)).join('')}`;
  const rows = v.push.map((r, i) => `<div class="row" style="margin-bottom:8px"><input type="text" style="flex:2" data-vk="${i}" placeholder="Nhóm/Tên khóa" value="${esc(r.key)}"><input type="text" style="flex:1" data-vv="${i}" placeholder="Giá trị" value="${esc(r.value)}"><button class="btn sm ghost" data-act="vc_delrow" data-i="${i}">✕</button></div>`).join('');
  const presets = `<option value="">+ Thêm khóa gợi ý…</option>${v.presets.map((p, i) => `<option value="${i}">${esc(p.key)} = ${esc(p.value)} · ${esc(p.desc)}</option>`).join('')}`;
  return `<div class="steps">
    <section class="card"><h3>Sao lưu, so sánh, khôi phục</h3>
      <p class="sub">Mỗi bản sao lưu là file JSON do <code>veyon-cli config export</code> tạo, lưu trong <code>${esc(v.dir)}</code>. Máy học sinh đọc từ xa qua <code>schtasks</code> và <code>\\\\máy\\C$</code> nên cần đủ điều kiện như ở trang Thiết lập ban đầu.</p>
      <div class="row"><button class="btn primary" data-act="vc_backup_master">💾 Sao lưu master</button>
        <button class="btn" data-act="vc_backup_clients">💾 Sao lưu ${targets().all ? 'tất cả ' : ''}${hosts.length} máy học sinh</button></div>
      <div class="row" style="margin-top:16px"><select data-vc="a">${refs(S.vcA)}</select><span>↔</span><select data-vc="b">${refs(S.vcB)}</select>
        <button class="btn" data-act="vc_compare">🔍 So sánh</button></div>
      <div class="row" style="margin-top:16px"><select data-vc="f" style="flex:1">${files}</select>
        <button class="btn" data-act="vc_restore_master">↩ Khôi phục master</button>
        <button class="btn" data-act="vc_restore_clients">↩ Khôi phục ${hosts.length} máy</button></div>
      <p class="hint">So sánh hiện kết quả ở Nhật ký (~ khác giá trị, + chỉ có ở B, - chỉ có ở A). Khôi phục dùng <code>config import</code> nên <b>thay toàn bộ</b> cấu hình; trước đó chương trình tự lưu cấu hình cũ của máy đó vào cùng thư mục.</p>
    </section>
    <section class="card"><h3>Đẩy cấu hình Veyon Service xuống máy học sinh</h3>
      <p class="sub">Ghi từng khóa bằng <code>veyon-cli config set</code> trên máy học sinh (giữ nguyên các khóa khác), sau đó tùy chọn khởi động lại Veyon Service. Cấu hình cũ của mỗi máy được lưu trước khi đẩy.</p>
      ${rows || '<p class="hint">Chưa có khóa nào. Thêm khóa gợi ý hoặc bấm “Thêm dòng”.</p>'}
      <div class="row"><select data-vc="preset">${presets}</select><button class="btn sm" data-act="vc_addrow">+ Thêm dòng</button></div>
      <label class="switch" style="margin-top:12px"><input type="checkbox" data-vc="restart" ${v.restart ? 'checked' : ''}><span class="tr"></span><span>Khởi động lại Veyon Service sau khi đẩy (kết nối Veyon tới máy đó ngắt vài giây)</span></label>
      <div class="formgrid" style="margin-top:12px"><div><label class="field">veyon-cli.exe trên máy học sinh</label><input type="text" data-vc="cli" value="${esc(v.client_cli)}"></div></div>
      <div class="row" style="margin-top:14px"><button class="btn" data-act="vc_savepush">Lưu danh sách khóa</button>
        <button class="btn primary" data-act="vc_push">▶ Đẩy xuống ${targets().all ? 'tất cả ' : ''}${hosts.length} máy</button></div>
      <p class="hint">Tên khóa gợi ý chưa được kiểm chứng trên Veyon thật. Sau khi đẩy, dùng “So sánh” giữa máy học sinh và bản sao lưu trước đó để xem khóa nào thật sự đổi.</p>
    </section>
    <section class="card"><h3>Danh sách máy của Veyon Master</h3>
      <p class="sub">Thêm các máy học sinh đang chọn vào danh sách máy của Veyon Master (<code>veyon-cli networkobjects add</code>). Máy đã có thì bỏ qua. Dùng sau khi “Tìm máy học sinh trong mạng”.</p>
      <div class="formgrid"><div><label class="field">Tên nhóm có sẵn trong Master</label><input type="text" data-vc="loc" list="vc-locs" value="${esc(v.location)}"><datalist id="vc-locs">${(v.locations || []).map(n => `<option value="${esc(n)}">`).join('')}</datalist><div class="hint" style="margin-top:5px">Gõ đúng tên nhóm đang có trong Veyon Master (không phân biệt hoa thường). Để trống để tool tự làm: dùng nhóm có sẵn trong Veyon, chưa có nhóm nào thì tự tạo nhóm “KhoaVeyon”.</div></div></div>
      <div class="row" style="margin-top:14px"><button class="btn" data-act="vc_netobj_scan">🔍 Tự dò nhóm trong máy</button><button class="btn primary" data-act="vc_netobj">➕ Thêm ${targets().all ? 'tất cả ' : ''}${hosts.length} máy vào Veyon Master</button></div>
      <p class="hint">Cần quyền quản trị nên Windows có thể hiện hộp thoại UAC. Chưa kiểm chứng định dạng kết quả của <code>networkobjects list</code>, nên việc nhận biết máy “đã có” dựa vào việc tên máy xuất hiện trong kết quả đó.</p>
    </section>
  </div>`;
}

function vcCollect() {
  const q = k => document.querySelector(`[data-vc="${k}"]`);
  const v = S.vcfg;
  if (q('restart')) v.restart = q('restart').checked;
  if (q('cli')) v.client_cli = q('cli').value;
  if (q('loc')) v.location = q('loc').value;
  return {push: v.push, restart: v.restart, location: v.location, client_cli: v.client_cli};
}

async function vcRun(body, okMsg) {
  try { await api('/api/vcfg_run', body); openLog(); toast(okMsg, 'ok'); setTimeout(() => go('vcfg'), 4000); }
  catch (e) { toast(e.message, 'err'); }
}

async function vcAction(act, el) {
  const v = S.vcfg;
  if (act === 'vc_addrow') { vcCollect(); v.push.push({key: '', value: ''}); render(); return; }
  if (act === 'vc_delrow') { vcCollect(); v.push.splice(+el.dataset.i, 1); render(); return; }
  if (act === 'vc_savepush') { try { await api('/api/vcfg_save', vcCollect()); toast('Đã lưu', 'ok'); } catch (e) { toast(e.message, 'err'); } return; }
  if (act === 'vc_netobj_scan') return vcRun({step: 'netobj_scan'}, 'Đang dò nhóm, kết quả ở Nhật ký');
  if (act === 'vc_backup_master') return vcRun({step: 'backup_master'}, 'Đang sao lưu cấu hình master');
  if (act === 'vc_compare') { if (!S.vcA || !S.vcB) { toast('Chọn hai bên để so sánh', 'warn'); return; } return vcRun({step: 'compare', a: S.vcA, b: S.vcB}, 'Đang so sánh, kết quả ở Nhật ký'); }
  const hosts = await resolveTargets(); if (!hosts) return;
  if (act === 'vc_backup_clients') return vcRun({step: 'backup_clients', hosts}, `Đang sao lưu ${hosts.length} máy`);
  if (act === 'vc_restore_master' || act === 'vc_restore_clients') {
    if (!S.vcF) { toast('Chọn file sao lưu để khôi phục', 'warn'); return; }
    const m = act === 'vc_restore_master';
    if (!(await modal({title: 'Khôi phục cấu hình Veyon?', danger: true, ok: 'Khôi phục', html: `File <b>${esc(S.vcF)}</b> sẽ <b>thay toàn bộ</b> cấu hình Veyon của ${m ? 'máy master (cần quyền quản trị)' : hosts.length + ' máy học sinh, Veyon Service sẽ khởi động lại'}. Cấu hình hiện tại được lưu trước.`}))) return;
    return vcRun({step: m ? 'restore_master' : 'restore_clients', file: S.vcF, hosts: m ? [] : hosts}, 'Đang khôi phục');
  }
  if (act === 'vc_push') {
    const c = vcCollect();
    if (!(await modal({title: 'Đẩy cấu hình xuống máy học sinh?', ok: 'Đẩy', html: `Ghi ${c.push.filter(r => r.key.trim()).length} khóa vào ${hosts.length} máy${c.restart ? ', rồi khởi động lại Veyon Service' : ''}.`}))) return;
    try { await api('/api/vcfg_save', c); } catch (e) { toast(e.message, 'err'); return; }
    return vcRun({step: 'push', hosts, push: c.push, restart: c.restart}, 'Đang đẩy cấu hình');
  }
  if (act === 'vc_netobj') { const c = vcCollect(); try { await api('/api/vcfg_save', c); } catch (e) { toast(e.message, 'err'); return; } return vcRun({step: 'netobj', hosts, location: c.location}, 'Đang thêm máy vào Veyon Master. Nếu Windows hỏi quyền quản trị, bấm Yes.'); }
}

document.addEventListener('input', e => {
  const t = e.target; if (!S.vcfg) return;
  if (t.dataset && t.dataset.vk !== undefined) S.vcfg.push[+t.dataset.vk].key = t.value;
  else if (t.dataset && t.dataset.vv !== undefined) S.vcfg.push[+t.dataset.vv].value = t.value;
});
document.addEventListener('change', e => {
  const t = e.target; if (!t.dataset || t.dataset.vc === undefined) return;
  if (t.dataset.vc === 'a') S.vcA = t.value;
  else if (t.dataset.vc === 'b') S.vcB = t.value;
  else if (t.dataset.vc === 'f') S.vcF = t.value;
  else if (t.dataset.vc === 'preset' && t.value !== '') {
    const p = S.vcfg.presets[+t.value]; vcCollect();
    if (!S.vcfg.push.some(r => r.key === p.key)) S.vcfg.push.push({key: p.key, value: p.value});
    render();
  }
});
