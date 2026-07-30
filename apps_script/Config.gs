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
  SALES_FOLDER_ID: 'DÁN_ID_THƯ_MỤC_Sales_Entry_VÀO_ĐÂY',

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
  SHEET_SALES_REGISTRY: 'DANH_MỤC_SALES',
  SHEET_SALES_LOG: 'SALES_INGEST_LOG',
  SHEET_SALES_ERRORS: 'SALES_LỖI',

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
  LY_DO_CHUA_CO_SDT: 'LÝ DO CHƯA CÓ SĐT',
  LOAI_TIN_NHAN: 'LOẠI TIN NHẮN',
  NHOM_SP: 'NHÓM SP',
  CHATPAGE: 'CHATPAGE',
  NGUON: 'NGUỒN',
  BAI_QC: 'BÀI QC',
  QUAN_TAM: 'QUAN TÂM',
  TINH_TRANG: 'TÌNH TRẠNG',
  TRANG_THAI: 'TRẠNG THÁI',
  TU_VAN: 'TƯ VẤN - SALE',
  THONG_TIN_KHACH: 'THÔNG TIN KHÁCH',
  GIO_HEN: 'GIỜ HẸN',
  NGAY_HEN: 'NGÀY HẸN',
  GHI_CHU: 'GHI CHÚ',
};

/** Giá trị TRẠNG THÁI nghĩa là khách đã có lịch hẹn -> bắt buộc phải có SĐT. */
const TRANG_THAI_CAN_SDT = ['ĐẶT HẸN', 'ĐÃ LÀM DV', 'DỜI LỊCH'];

function _alertEmails() {
  return CONFIG.ALERT_EMAIL.split(',').map(function (s) { return s.trim(); })
    .filter(String);
}

/**
 * Lấy ID: ưu tiên Config.gs, chưa điền thì lấy từ Script Properties do
 * dungHeThong() ghi vào. Nhờ vậy chạy được ngay sau khi dựng, không phải
 * chép tay các ID trước. Vẫn nên điền Config.gs để người sau đọc code là biết.
 */
function _id(ten) {
  const v = CONFIG[ten];
  if (v && v.indexOf('DÁN_ID') !== 0) return v;
  const p = PropertiesService.getScriptProperties().getProperty(ten);
  if (p) return p;
  throw new Error('Chưa có ' + ten + '. Chạy dungHeThong() trong Bootstrap.gs, ' +
    'hoặc điền tay vào Config.gs.');
}

function _guardConfig() {
  ['KHO_ID', 'DASHBOARD_ID', 'KIOTVIET_FOLDER_ID', 'PANCAKE_FOLDER_ID']
    .forEach(function (k) { _id(k); });
}
