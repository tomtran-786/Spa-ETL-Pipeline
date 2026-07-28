/**
 * Bắt lỗi NGAY LÚC SALES GÕ — đây là chỗ rẻ nhất để sửa dữ liệu.
 *
 * Ba việc:
 *   1. Tự điền NGÀY khi có dòng mới  -> diệt hẳn lỗi gõ nhầm năm (35 dòng ghi
 *      19/01/2025 trong file lẽ ra là 2026).
 *   2. Chặn chuyển sang "Đặt hẹn" khi chưa có SĐT -> chặn ĐÚNG CHỖ CÓ LÝ.
 *      Cố tình KHÔNG bắt buộc SĐT ở mọi dòng: 45,7% lead không có số là vì
 *      khách chỉ hỏi giá rồi im, ép nhập chỉ khiến sales gõ 0000000000 cho qua,
 *      và số rác đó sẽ join nhầm sang hóa đơn.
 *   3. Tự sửa chính tả NGUỒN ('instgram' -> 'Instagram') thay vì chặn — sales
 *      hay paste cả khối, chặn sẽ làm họ bỏ trống cột.
 *
 * Đây là trigger đơn giản: chạy được mà không cần cấp quyền, nhưng KHÔNG gửi
 * được email. Việc gửi mail nằm ở Watchdog.gs (trigger theo giờ).
 */
function onEdit(e) {
  if (!e || !e.range) return;
  const sheet = e.range.getSheet();
  if (sheet.getName() !== CONFIG.SHEET_LEAD) return;
  if (e.range.getRow() === 1) return; // hàng header

  try {
    const cols = _headerMap(sheet);
    _tuDienNgay(sheet, e.range, cols);
    _chanDatHenKhiThieuSdt(sheet, e, cols);
    _suaChinhTaNguon(sheet, e, cols);
  } catch (err) {
    // onEdit chết lặng lẽ sẽ khiến sales tưởng mọi thứ ổn -> hiện toast.
    sheet.getParent().toast('Lỗi kiểm tra: ' + err.message, '⚠️ PXV', 8);
  }
}

/** Map tên cột -> số cột (1-based). Tra theo tên nên chèn cột không làm vỡ. */
function _headerMap(sheet) {
  const header = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const map = {};
  header.forEach(function (name, i) {
    const key = String(name).trim();
    if (key && !(key in map)) map[key] = i + 1;
  });
  return map;
}

/**
 * Dòng vừa có nội dung mà NGÀY còn trống -> ghi ngày hôm nay (giá trị tĩnh,
 * không phải công thức TODAY() vì công thức sẽ đổi theo từng ngày mở file).
 */
function _tuDienNgay(sheet, range, cols) {
  const colNgay = cols[LEAD_COLS.NGAY];
  if (!colNgay) return;

  const row = range.getRow();
  const numRows = range.getNumRows();
  for (let r = row; r < row + numRows; r++) {
    const oNgay = sheet.getRange(r, colNgay);
    if (oNgay.getValue()) continue;                 // đã có ngày thì thôi
    if (_dongTrong(sheet, r)) continue;             // dòng rỗng thì chưa cần
    oNgay.setValue(new Date());
    oNgay.setNumberFormat('dd/MM/yyyy');
  }
}

function _dongTrong(sheet, row) {
  const values = sheet.getRange(row, 1, 1, sheet.getLastColumn()).getValues()[0];
  return values.every(function (v) { return v === '' || v === null; });
}

/**
 * Khách chuyển sang bước Đặt hẹn thì bắt buộc phải có SĐT — không có số thì
 * không thể gọi xác nhận lịch, và cũng không thể đối chiếu với hóa đơn sau này.
 */
function _chanDatHenKhiThieuSdt(sheet, e, cols) {
  const colTT = cols[LEAD_COLS.TT_DAT_HEN];
  const colSdt = cols[LEAD_COLS.SDT];
  if (!colTT || !colSdt) return;
  if (e.range.getColumn() !== colTT) return;

  const giaTri = String(e.range.getValue() || '').trim().toUpperCase();
  if (!TRANG_THAI_CAN_SDT.some(function (t) { return giaTri.indexOf(t) >= 0; })) return;

  const sdt = String(sheet.getRange(e.range.getRow(), colSdt).getValue() || '').trim();
  if (sdt) return;

  e.range.setValue(e.oldValue === undefined ? '' : e.oldValue);
  sheet.getParent().toast(
    'Phải nhập SỐ ĐT trước khi chuyển khách sang "Đặt hẹn". ' +
    'Chưa xin được số thì chọn lý do ở cột "' + LEAD_COLS.LY_DO_CHUA_CO_SDT + '".',
    '⛔ Thiếu số điện thoại', 12);
}

/**
 * Sửa chính tả NGUỒN theo bảng ÁNH_XẠ_ALIAS trong sheet.
 * Bảng nằm ở sheet chứ không nằm trong code để marketing tự sửa được.
 */
function _suaChinhTaNguon(sheet, e, cols) {
  const colNguon = cols[LEAD_COLS.NGUON];
  if (!colNguon || e.range.getColumn() !== colNguon) return;

  const goc = String(e.range.getValue() || '').trim();
  if (!goc) return;

  const alias = _bangAlias();
  const chuan = alias[goc.toUpperCase().replace(/\s+/g, ' ')];
  if (chuan && chuan !== goc) {
    e.range.setValue(chuan);
    sheet.getParent().toast('Đã sửa "' + goc + '" thành "' + chuan + '"', 'PXV', 4);
  }
}

/** Đọc bảng alias, cache 10 phút vì onEdit chạy liên tục. */
function _bangAlias() {
  const cache = CacheService.getScriptCache();
  const cached = cache.get('alias');
  if (cached) return JSON.parse(cached);

  const sheet = SpreadsheetApp.getActive().getSheetByName(CONFIG.SHEET_ALIAS);
  const map = {};
  if (sheet && sheet.getLastRow() > 1) {
    sheet.getRange(2, 1, sheet.getLastRow() - 1, 2).getValues()
      .forEach(function (r) {
        const sai = String(r[0] || '').trim().toUpperCase().replace(/\s+/g, ' ');
        const dung = String(r[1] || '').trim();
        if (sai && dung) map[sai] = dung;
      });
  }
  cache.put('alias', JSON.stringify(map), 600);
  return map;
}
