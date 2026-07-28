/**
 * Cấu hình chung. ĐIỀN CÁC ID Ở ĐÂY trước khi chạy bất cứ thứ gì.
 *
 * Lấy ID spreadsheet từ URL:
 *   docs.google.com/spreadsheets/d/<ID_Ở_ĐÂY>/edit
 * Lấy ID thư mục Drive từ URL:
 *   drive.google.com/drive/folders/<ID_Ở_ĐÂY>
 *
 * KHÔNG dán token GitHub vào file này — file này nằm trong Apps Script mà
 * nhiều người xem được. Token lưu ở Project Settings > Script Properties
 * (xem hướng dẫn trong Setup.gs).
 */
const CONFIG = {
  // --- Spreadsheet ---
  KHO_ID: 'DÁN_ID_PXV_KHO_VÀO_ĐÂY',
  DASHBOARD_ID: 'DÁN_ID_PXV_DASHBOARD_DATA_VÀO_ĐÂY',

  // --- Thư mục Drive để thả file export ---
  KIOTVIET_FOLDER_ID: 'DÁN_ID_THƯ_MỤC_KiotViet_Drop_VÀO_ĐÂY',
  PANCAKE_FOLDER_ID: 'DÁN_ID_THƯ_MỤC_Pancake_Drop_VÀO_ĐÂY',

  // --- Người nhận cảnh báo (cách nhau bằng dấu phẩy) ---
  ALERT_EMAIL: 'tomt74762@gmail.com',

  // --- GitHub (để nút "Chạy lại pipeline" hoạt động) ---
  GITHUB_OWNER: 'tomtran-786',
  GITHUB_REPO: 'Phun-Xam-Vic---Data-Analysis',

  // --- Tên sheet ---
  SHEET_LEAD: 'LEAD',
  SHEET_ALIAS: 'ÁNH_XẠ_ALIAS',
  SHEET_INVOICES: 'INVOICES_RAW',
  SHEET_KV_LOG: 'KIOTVIET_LOG',
  SHEET_PANCAKE: 'PANCAKE_RAW',
  SHEET_DQ: 'DQ_STATUS',

  // --- Ngưỡng ---
  HOA_DON_CU_QUA_NGAY: 8,      // file thả vào mà hóa đơn mới nhất cũ hơn ngần này -> cảnh báo
  PIPELINE_TRE_QUA_GIO: 26,    // pipeline không chạy quá ngần này -> báo đỏ
  SUT_GIAM_BAT_THUONG: 0.5,    // số HĐ tháng < 50% trung bình 3 tháng -> cảnh báo

  // Ngày nghỉ dài, không coi "3 ngày liên tiếp không có hóa đơn" là bất thường.
  // Định dạng YYYY-MM-DD, thêm dịp Tết hằng năm vào đây.
  NGAY_NGHI: ['2026-02-17', '2026-02-18', '2026-02-19', '2026-02-20'],
};

/** Cột bắt buộc của file export KiotViet. Lệch là chặn, không nạp. */
const KIOTVIET_COLUMNS = [
  'Mã hóa đơn', 'Thời gian', 'Mã khách hàng', 'Tên khách hàng',
  'Điện thoại', 'Người bán', 'Khách cần trả', 'Mã hàng', 'Tên hàng', 'Số lượng',
];

/** Tên cột trong sheet LEAD. Tra theo TÊN chứ không theo vị trí, để chèn cột không vỡ. */
const LEAD_COLS = {
  NGAY: 'NGÀY',
  TEN: 'TÊN KHÁCH HÀNG',
  SDT: 'SỐ ĐT',
  NGUON: 'NGUỒN',
  TT_QUAN_TAM: 'TT_QUAN_TÂM',
  TT_DAT_HEN: 'TT_ĐẶT_HẸN',
  TT_CHOT_DON: 'TT_CHỐT_ĐƠN',
  NGAY_HEN: 'NGÀY HẸN',
  LY_DO_CHUA_CO_SDT: 'LÝ DO CHƯA CÓ SĐT',
};

/** Giá trị của TT_ĐẶT_HẸN nghĩa là khách đã sang bước đặt hẹn -> bắt buộc phải có SĐT. */
const TRANG_THAI_CAN_SDT = ['ĐẶT HẸN', 'ĐÃ LÀM DV', 'CHỐT ĐƠN', 'CHỐT'];

function _alertEmails() {
  return CONFIG.ALERT_EMAIL.split(',').map(function (s) { return s.trim(); })
    .filter(String);
}

function _guardConfig() {
  const chuaDien = Object.keys(CONFIG).filter(function (k) {
    return typeof CONFIG[k] === 'string' && CONFIG[k].indexOf('DÁN_ID') === 0;
  });
  if (chuaDien.length) {
    throw new Error('Chưa điền ID trong Config.gs: ' + chuaDien.join(', '));
  }
}
