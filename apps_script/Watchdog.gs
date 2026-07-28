/**
 * Canh chừng pipeline — mảnh quan trọng nhất của cả hệ giám sát.
 *
 * Lý do phải có: GitHub Actions chỉ gửi mail khi job CHẠY và HỎNG. Nếu job
 * không chạy nữa thì im lặng tuyệt đối. Mà GitHub TỰ TẮT scheduled workflow
 * sau 60 ngày repo không có commit mới — khi pipeline ổn định thì sẽ không ai
 * commit nữa, nên tình huống này gần như chắc chắn xảy ra.
 *
 * Watchdog chạy ở HỆ THỐNG KHÁC (Google) với thứ nó theo dõi (GitHub), nên nó
 * bắt được cả trường hợp GitHub chết hoàn toàn.
 *
 * Chạy theo trigger 09:00 hằng ngày — xem Setup.gs.
 */
function canhChung() {
  _guardConfig();

  let chayLuc = null;
  let loiDoc = null;
  try {
    chayLuc = _docMocChayLuc();
  } catch (err) {
    loiDoc = err.message;
  }

  if (loiDoc || !chayLuc) {
    _guiMail('🔴 KHÔNG ĐỌC ĐƯỢC TRẠNG THÁI PIPELINE',
      'Không đọc được mốc "Chạy lúc" trong sheet ' + CONFIG.SHEET_DQ + '.\n\n' +
      'Lý do: ' + (loiDoc || 'không tìm thấy dòng "Chạy lúc"') + '\n\n' +
      'Nghĩa là pipeline có thể chưa từng chạy, hoặc sheet đã bị đổi cấu trúc.\n' +
      'Xem RUNBOOK.md mục "Dashboard không cập nhật".');
    return;
  }

  const soGio = (new Date() - chayLuc) / 3600000;
  if (soGio > CONFIG.PIPELINE_TRE_QUA_GIO) {
    _guiMail('🔴 PIPELINE CHƯA CHẠY ' + Math.floor(soGio / 24) + ' NGÀY',
      'Lần chạy gần nhất: ' + Utilities.formatDate(
        chayLuc, Session.getScriptTimeZone(), 'dd/MM/yyyy HH:mm') +
      ' (' + Math.floor(soGio) + ' giờ trước).\n\n' +
      'Số trên dashboard đang là số CŨ. Việc cần làm:\n' +
      '1. Mở https://github.com/' + CONFIG.GITHUB_OWNER + '/' + CONFIG.GITHUB_REPO +
      '/actions xem job có bị tắt không.\n' +
      '   (GitHub tự tắt lịch chạy sau 60 ngày repo không có thay đổi — nếu vậy ' +
      'bấm "Enable workflow".)\n' +
      '2. Hoặc mở Google Sheet nhập liệu, menu "🔄 PXV" > "Chạy lại pipeline ngay".\n' +
      '3. Vẫn không được thì xem RUNBOOK.md.');
    return;
  }

  // Pipeline còn sống — kiểm tiếp xem có phép kiểm nào báo đỏ không.
  const loi = _cacPhepKiemDo();
  if (loi.length) {
    _guiMail('⚠️ Pipeline chạy nhưng dữ liệu có vấn đề',
      'Lần chạy: ' + Utilities.formatDate(
        chayLuc, Session.getScriptTimeZone(), 'dd/MM/yyyy HH:mm') + '\n\n' +
      'Các phép kiểm không đạt:\n• ' + loi.join('\n• ') + '\n\n' +
      'Xem chi tiết ở sheet ' + CONFIG.SHEET_DQ + '.');
  }
}

function _docMocChayLuc() {
  const sheet = SpreadsheetApp.openById(CONFIG.DASHBOARD_ID)
    .getSheetByName(CONFIG.SHEET_DQ);
  if (!sheet) throw new Error('Không có sheet ' + CONFIG.SHEET_DQ);
  if (sheet.getLastRow() < 2) throw new Error('Sheet ' + CONFIG.SHEET_DQ + ' rỗng');

  const rows = sheet.getRange(2, 1, sheet.getLastRow() - 1, 3).getValues();
  for (let i = 0; i < rows.length; i++) {
    if (String(rows[i][0]).trim() === 'Chạy lúc') {
      const v = rows[i][2];
      const d = (v instanceof Date) ? v : new Date(String(v).replace(' ', 'T'));
      return isNaN(d.getTime()) ? null : d;
    }
  }
  return null;
}

function _cacPhepKiemDo() {
  const sheet = SpreadsheetApp.openById(CONFIG.DASHBOARD_ID)
    .getSheetByName(CONFIG.SHEET_DQ);
  if (!sheet || sheet.getLastRow() < 2) return [];
  return sheet.getRange(2, 1, sheet.getLastRow() - 1, 4).getValues()
    .filter(function (r) { return String(r[1]).indexOf('DỪNG') >= 0; })
    .map(function (r) { return r[0] + ': ' + r[2] + (r[3] ? ' — ' + r[3] : ''); });
}

/**
 * Nhắc kế toán export KiotViet. Chạy 08:00 các ngày làm việc.
 * Rẻ hơn nhiều so với việc mất thêm một tháng dữ liệu.
 */
function nhacExportKiotViet() {
  _guardConfig();
  const log = SpreadsheetApp.openById(CONFIG.KHO_ID).getSheetByName(CONFIG.SHEET_KV_LOG);
  let lanCuoi = 'chưa từng nạp';
  if (log && log.getLastRow() > 1) {
    const ngay = log.getRange(2, 4, log.getLastRow() - 1, 1).getValues()
      .map(function (r) { return String(r[0]); }).filter(String).sort();
    if (ngay.length) lanCuoi = ngay[ngay.length - 1];
  }
  _guiMail('Nhắc: export hóa đơn KiotViet hôm nay',
    'Lần nạp gần nhất: ' + lanCuoi + '\n\n' +
    'Các bước:\n' +
    '1. Mở KiotViet > Báo cáo > Chi tiết hóa đơn\n' +
    '2. Chọn khoảng ngày (lấy rộng hơn vài ngày cũng không sao — kho tự khử trùng)\n' +
    '3. Xuất file CSV\n' +
    '4. Kéo thả file vào thư mục Drive "KiotViet_Drop"\n\n' +
    'Không cần đặt tên file theo quy tắc nào cả.');
}
