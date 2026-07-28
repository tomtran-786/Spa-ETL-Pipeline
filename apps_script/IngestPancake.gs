/**
 * Nạp file export Pancake để vá lead thiếu SĐT (hiện 45,7% lead không có số).
 *
 * Lấy file từ Pancake:
 *   Thống kê > Sao lưu > "Hộp thư có số điện thoại"
 *   > chọn khoảng ngày > Tạo yêu cầu > tải file Excel
 *
 * CHƯA BIẾT FILE CÓ CỘT GÌ — tài liệu Pancake không công bố. Vì vậy file này
 * có 2 phần:
 *   1. khamPhaPancake()  — chạy TRƯỚC, in ra danh sách cột của file thật
 *   2. napPancake()      — chạy SAU, khi đã điền PANCAKE_COLS bên dưới
 *
 * Đừng đoán tên cột rồi viết code theo phỏng đoán: sai tên cột thì script vẫn
 * chạy nhưng không vá được SĐT nào, và không ai biết vì sao.
 */

/** ĐIỀN SAU KHI CHẠY khamPhaPancake(). Để trống thì napPancake() sẽ từ chối chạy. */
const PANCAKE_COLS = {
  SDT: '',        // vd: 'Số điện thoại'
  TEN: '',        // vd: 'Tên khách hàng'
  PAGE: '',       // vd: 'Trang'      (không bắt buộc)
  NGAY: '',       // vd: 'Thời gian'  (không bắt buộc)
};

/**
 * Bước 1 — đọc file đầu tiên trong Pancake_Drop và in ra cấu trúc.
 * Chạy hàm này từ menu Apps Script, rồi xem kết quả ở View > Logs.
 */
function khamPhaPancake() {
  _guardConfig();
  const folder = DriveApp.getFolderById(_id('PANCAKE_FOLDER_ID'));
  const files = folder.getFiles();
  if (!files.hasNext()) {
    Logger.log('Chưa có file nào trong Pancake_Drop. Export từ Pancake rồi thả vào đó.');
    return;
  }
  const file = files.next();
  const rows = _docBang(file);
  if (!rows.length) { Logger.log('File rỗng.'); return; }

  Logger.log('File: ' + file.getName());
  Logger.log('Số dòng: ' + rows.length + ' (kể cả header)');
  Logger.log('--- CÁC CỘT ---');
  rows[0].forEach(function (ten, i) {
    const mau = rows.length > 1 ? String(rows[1][i] || '').slice(0, 40) : '';
    Logger.log('  [' + i + '] "' + ten + '"   ví dụ: ' + mau);
  });
  Logger.log('\nChép tên cột chứa SĐT và tên khách vào PANCAKE_COLS ở đầu file này.');
}

/**
 * Bước 2 — nạp vào PANCAKE_RAW. Pipeline Python sẽ join theo SĐT/tên để điền
 * SĐT cho lead còn trống.
 *
 * Chạy theo trigger hằng tuần, hoặc bấm tay từ menu PXV.
 */
function napPancake() {
  _guardConfig();
  if (!PANCAKE_COLS.SDT) {
    throw new Error('Chưa điền PANCAKE_COLS. Chạy khamPhaPancake() trước để xem ' +
      'file có cột gì, rồi điền tên cột vào đầu file IngestPancake.gs.');
  }

  const folder = DriveApp.getFolderById(_id('PANCAKE_FOLDER_ID'));
  const files = folder.getFiles();
  const kho = SpreadsheetApp.openById(_id('KHO_ID'));
  let tongThem = 0, soFile = 0;

  while (files.hasNext()) {
    const file = files.next();
    if (file.getName().indexOf('~') === 0) continue;
    soFile++;
    try {
      tongThem += _napMotFilePancake(file, kho);
      _chuyenFile(file, folder, '_daNap');
    } catch (err) {
      _chuyenFile(file, folder, '_loi');
      _guiMail('❌ Không nạp được file Pancake',
        'File: ' + file.getName() + '\nLý do: ' + err.message);
    }
  }
  Logger.log('Đã xử lý ' + soFile + ' file, thêm ' + tongThem + ' SĐT mới.');
}

function _napMotFilePancake(file, kho) {
  const rows = _docBang(file);
  if (rows.length < 2) throw new Error('File rỗng.');

  const header = rows[0].map(function (h) { return String(h).trim(); });
  const iSdt = header.indexOf(PANCAKE_COLS.SDT);
  if (iSdt < 0) {
    throw new Error('Không thấy cột "' + PANCAKE_COLS.SDT + '". Cột đang có: ' +
      header.join(' | ') + '. Chạy lại khamPhaPancake() nếu Pancake đổi định dạng.');
  }
  const iTen = PANCAKE_COLS.TEN ? header.indexOf(PANCAKE_COLS.TEN) : -1;
  const iPage = PANCAKE_COLS.PAGE ? header.indexOf(PANCAKE_COLS.PAGE) : -1;
  const iNgay = PANCAKE_COLS.NGAY ? header.indexOf(PANCAKE_COLS.NGAY) : -1;

  const sheet = _sheetOrCreate(kho, CONFIG.SHEET_PANCAKE,
    ['SĐT', 'Tên khách', 'Page', 'Ngày', '_ngày nạp']);
  sheet.getRange(1, 1, sheet.getMaxRows(), 1).setNumberFormat('@'); // giữ số 0 đầu

  const daCo = {};
  if (sheet.getLastRow() > 1) {
    sheet.getRange(2, 1, sheet.getLastRow() - 1, 1).getValues()
      .forEach(function (r) { daCo[String(r[0]).trim()] = true; });
  }

  const homNay = _dinhDangNgay(new Date());
  const them = [];
  rows.slice(1).forEach(function (r) {
    const sdt = _chuanHoaSdt(r[iSdt]);
    if (!sdt || daCo[sdt]) return;
    daCo[sdt] = true;
    them.push([sdt,
      iTen >= 0 ? r[iTen] : '',
      iPage >= 0 ? r[iPage] : '',
      iNgay >= 0 ? r[iNgay] : '',
      homNay]);
  });

  if (them.length) {
    sheet.getRange(sheet.getLastRow() + 1, 1, them.length, 5).setValues(them);
  }
  return them.length;
}

/**
 * Chuẩn hóa SĐT giống hệt pxv/clean.py để hai bên join khớp nhau.
 * Số VN -> 0XXXXXXXXX, số quốc tế -> +XXXX, rác -> ''.
 */
function _chuanHoaSdt(v) {
  if (v == null) return '';
  let d = String(v).split('.')[0].replace(/\D/g, '');
  if (!d) return '';
  if (d.indexOf('00') === 0) d = d.slice(2);

  const ungVien = [];
  if (d.indexOf('84') === 0 && d.length === 11) ungVien.push('0' + d.slice(2));
  if (d.charAt(0) === '0') ungVien.push(d);
  if (d.length === 9) ungVien.push('0' + d);

  for (let i = 0; i < ungVien.length; i++) {
    const c = ungVien[i];
    if (/^0[35789]\d{8}$/.test(c) || /^02\d{8,9}$/.test(c)) return c;
  }
  return (d.length >= 10 && d.length <= 15) ? '+' + d : '';
}

/** Đọc file thành mảng 2 chiều. Nhận cả CSV lẫn Excel (Pancake xuất Excel). */
function _docBang(file) {
  const ten = file.getName().toLowerCase();
  if (ten.slice(-4) === '.csv' || file.getMimeType() === MimeType.CSV) {
    return Utilities.parseCsv(file.getBlob().getDataAsString('UTF-8'));
  }
  // Excel: nhờ Drive chuyển sang Google Sheets rồi đọc, xong xóa bản tạm.
  const tam = Drive.Files.copy(
    { title: '[tạm] ' + file.getName(), mimeType: MimeType.GOOGLE_SHEETS },
    file.getId());
  try {
    const sheet = SpreadsheetApp.openById(tam.id).getSheets()[0];
    return sheet.getDataRange().getValues();
  } finally {
    DriveApp.getFileById(tam.id).setTrashed(true);
  }
}
