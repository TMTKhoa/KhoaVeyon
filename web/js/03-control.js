// KhoaVeyon - Trang Điều khiển lớp
/* ---------- trang: Điều khiển lớp ---------- */
function viewControl() {
  const st = S.st;
  const tile = k => { const a = action(k); return `<button class="tile ${a.kind}" data-act="run" data-key="${esc(k)}"><span class="ico">${a.icon}</span><span>${esc(a.label)}</span></button>`; };
  const aiExtra = g => g.keys.includes('blockai') ? `<p class="hint" style="margin:12px 0 0">Khóa cả trang web AI, AI tích hợp trong Chrome, Edge, Firefox, Brave và ứng dụng AI. Danh sách trang nằm ở mục “Trang AI bị chặn”. Lần đầu bấm khóa, trình duyệt đang mở sẽ bị đóng.</p><div class="row" style="margin-top:10px"><button class="btn ghost" data-act="aistatus">🔍 Kiểm tra máy nào đã khóa AI</button></div><label class="switch" style="margin-top:12px"><input type="checkbox" data-cfg="lock_with_ai" ${st.cfg.lock_with_ai ? 'checked' : ''}><span class="tr"></span><span>Bấm “Khóa toàn bộ” thì khóa luôn AI, bấm “Mở khóa toàn bộ” thì mở AI</span></label>` : '';
  const groups = st.groups.map(g => `<section class="card"><h3>${esc(g.title)}</h3><div class="tiles">${g.keys.map(tile).join('')}</div>${aiExtra(g)}</section>`).join('');
  const hostItems = S.hosts.map((h, i) => `<li class="${S.sel.has(h) ? 'sel' : ''}"><label><input type="checkbox" data-host="${i}" ${S.sel.has(h) ? 'checked' : ''}><span>${hnLabel(h)}</span></label><button class="ed" title="Đặt tên hiển thị" data-xa="editname" data-h="${esc(h)}">✎</button><button class="x" title="Xóa máy này" data-act="rmhost" data-i="${i}">×</button></li>`).join('');
  const opts = st.actions.map(a => `<option value="${esc(a.key)}">${esc(a.label)}</option>`).join('');
  return `<div class="grid-control">
    <section class="card">
      <h3>Máy học sinh <span class="badge">${S.hosts.length}</span></h3>
      <form class="addhost" data-form="addhost"><input type="text" id="hostInput" placeholder="Tên máy hoặc IP, ví dụ PC01" autocomplete="off"><button class="btn primary">Thêm</button></form>
      <div class="hosttools"><button class="link" data-act="selall">Chọn tất cả</button><button class="link" data-act="selnone">Bỏ chọn</button><span class="muted">Đã chọn ${S.hosts.filter(h => S.sel.has(h)).length}/${S.hosts.length}</span></div>
      ${S.hosts.length ? `<ul class="hostlist">${hostItems}</ul>` : `<div class="empty">Chưa có máy nào.<br>Nhập tên máy hoặc IP ở trên, có thể dán nhiều máy cách nhau bằng dấu phẩy hoặc dấu cách.</div>`}
      <p class="hint" style="margin-bottom:0">Không chọn máy nào nghĩa là áp dụng cho tất cả máy trong danh sách.</p>
    </section>
    <div class="stack">
      <div class="legend"><span><i style="background:#fb923c"></i>Cam: bật hạn chế</span><span><i style="background:#4ade80"></i>Xanh lá: gỡ hạn chế</span><span><i style="background:#cbd5e1"></i>Xám: việc khác</span></div>
      <section class="card">
        <h3>Chụp màn hình</h3>
        <p class="sub">Chụp màn hình người đang đăng nhập trên các máy đang chọn, ảnh lưu ở thư mục <code>data\\screenshots</code> trên máy này (mỗi lần một thư mục theo giờ).</p>
        <div class="row"><button class="btn primary" data-act="shot">📸 Chụp màn hình các máy</button><button class="btn ghost" data-act="openshots">Mở thư mục ảnh</button></div>
        <label class="switch" style="margin-top:12px"><input type="checkbox" data-cfg="shot_before_lock" ${st.cfg.shot_before_lock ? 'checked' : ''}><span class="tr"></span><span>Tự chụp màn hình trước khi bấm nút khóa, chặn hoặc đóng ứng dụng</span></label>
      </section>
      <section class="card">
        <h3>Giám sát vi phạm (tự chụp ảnh)</h3>
        <p class="sub">Khi cửa sổ đang mở là <b>trang web không có trong AllowPage</b> hoặc <b>ứng dụng không có trong KeepAppList</b>, hoặc học sinh <b>cố mở một trang hay ứng dụng AI</b> (trong BlockAIList), máy học sinh tự chụp màn hình. Danh sách Excel được đọc lại mỗi 30 giây. Không ghi phím gõ.</p>
        <div class="row"><button class="btn primary" data-act="watch_start">👁 Bật giám sát</button><button class="btn" data-act="watch_stop">Tắt giám sát</button><button class="btn" data-act="gopage" data-page-to="viol">🚨 Xem vi phạm</button><button class="btn ghost" data-act="watch_fetch">⬇ Lấy ảnh ngay</button><button class="btn ghost" data-act="openevidence">Mở thư mục ảnh</button><span class="badge" id="watchInfo"></span></div>
        <label class="switch" style="margin-top:12px"><input type="checkbox" data-cfg="watch_autostart" ${st.cfg.watch_autostart !== false ? 'checked' : ''}><span class="tr"></span><span>Tự chạy lại giám sát mỗi khi học sinh đăng nhập (kể cả sau khi khởi động lại máy). Áp dụng ở lần bấm “Bật giám sát” tiếp theo; “Tắt giám sát” sẽ gỡ luôn.</span></label>
        <label class="switch" style="margin-top:12px"><input type="checkbox" data-cfg="watch_notify_student" ${st.cfg.watch_notify_student !== false ? 'checked' : ''}><span class="tr"></span><span>Báo cho học sinh khi vi phạm: sau khi máy này <b>đã nhận</b> ảnh vi phạm, máy học sinh hiện bảng đỏ “ĐÃ GHI NHẬN VI PHẠM” (trang/ứng dụng, giờ chụp, đã gửi cho giáo viên) trong 10 giây. Mỗi lần vi phạm chỉ báo một lần. Áp dụng ở lần bấm “Bật giám sát” tiếp theo.</span></label>
        <label class="switch" style="margin-top:12px"><input type="checkbox" data-cfg="watch_disclose" ${st.cfg.watch_disclose !== false ? 'checked' : ''}><span class="tr"></span><span>Hiện nhãn nhỏ “ĐANG GIÁM SÁT” ở góc màn hình học sinh khi bật giám sát (công khai với học sinh). Nhãn dùng chung khung với nhãn “Máy này của ai”, nên cái sau sẽ thay cái trước.</span></label>
        <div class="formgrid" style="margin-top:12px"><div><label class="field">Chụp lại sau (giây) nếu vẫn ở trang đó</label><input type="text" data-cfg="watch_repeat" value="${esc(st.cfg.watch_repeat)}"></div><div><label class="field">Số ảnh tối đa mỗi lần vi phạm</label><input type="text" data-cfg="watch_max" value="${esc(st.cfg.watch_max)}"></div></div>
        <p class="hint">Sau khi bật, chương trình <b>tự nhận ảnh vi phạm</b> từ máy học sinh về máy này (vài giây một lần), kêu bíp và hiện thông báo kèm ảnh, tên máy, nội dung vi phạm, ngày giờ. Toàn bộ lưu ở <code>data\\evidence\\TÊNMÁY</code> và bảng <code>violations.csv</code>, ảnh cũ hơn số ngày đặt ở trang Vi phạm sẽ tự xóa. Khi đang giám sát, đóng cửa sổ chương trình không làm chương trình thoát (để không bỏ lỡ báo động); muốn thoát hãy bấm “Tắt giám sát” rồi “Thoát chương trình”.</p>
      </section>
      <section class="card">
        <h3>Thông báo cho học sinh</h3>
        <p class="sub">Hiện bảng thông báo lớn giữa màn hình các máy đang chọn rồi tự tắt (học sinh bấm vào bảng để tắt sớm). Bảng này dùng chung khung với nhãn “Máy này của ai”, nên sẽ thay nhãn chỗ ngồi đang hiện.</p>
        <div class="row"><input type="text" id="noticeText" maxlength="160" placeholder="Ví dụ: Còn 5 phút nữa, lưu bài và nộp lên lớp học" style="flex:1;min-width:260px"><label class="muted">Hiện <input type="number" id="noticeSecs" min="3" max="300" value="20" style="width:64px" class="xsel"> giây</label><button class="btn primary" data-act="notice">📢 Gửi thông báo</button></div>
      </section>
      ${groups}
      <section class="card">
        <h3>Nâng cao: lấy lệnh để dán vào Veyon</h3>
        <p class="sub">Dùng khi bạn muốn tạo nút "Run program" trong Veyon Master thay vì bấm ở đây.</p>
        <div class="row"><select id="copySel" style="flex:1;min-width:240px">${opts}</select><button class="btn" data-act="copycmd">Sao chép lệnh</button></div>
      </section>
    </div>
  </div>`;
}
