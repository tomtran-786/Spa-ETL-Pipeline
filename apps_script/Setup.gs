/**
 * CHẠY MỘT LẦN KHI CÀI ĐẶT.
 *
 * ============================================================
 * CÁC BƯỚC CÀI (làm đúng thứ tự)
 * ============================================================
 *
 * 1. Mở Google Sheet nhập liệu (PXV_NHẬP_LIỆU)
 *    > Tiện ích mở rộng (Extensions) > Apps Script
 *
 * 2. Dán từng file .gs trong thư mục apps_script/ vào project
 *    (bấm + > Script, đặt tên đúng như tên file, rồi dán nội dung)
 *
 * 3. Mở Config.gs, điền các ID còn ghi "DÁN_ID..."
 *
 * 4. Bật Advanced Drive Service (để đọc được file Excel của Pancake):
 *    Menu trái > Services (+) > chọn "Drive API" > Add
 *
 * 5. Chạy hàm taoTrigger() ở file này
 *    (chọn hàm ở thanh trên rồi bấm Run)
 *    Lần đầu Google sẽ hỏi cấp quyền — bấm Review permissions > Advanced >
 *    Go to ... (unsafe) > Allow. Đây là script của chính bạn nên an toàn.
 *
 * 6. (Không bắt buộc) Để nút "Chạy lại pipeline" hoạt động:
 *    a. Vào github.com > Settings > Developer settings >
 *       Personal access tokens > Fine-grained tokens > Generate new token
 *    b. Repository access: chọn đúng repo Phun-Xam-Vic---Data-Analysis
 *    c. Permissions > Repository permissions > Contents: Read and write
 *    d. Copy token
 *    e. Về Apps Script > Project Settings (bánh răng) > Script Properties >
 *       Add script property: tên GITHUB_TOKEN, giá trị là token vừa copy
 *    KHÔNG dán token vào Config.gs — file đó ai xem script cũng đọc được.
 *
 * 7. Đóng và mở lại Google Sheet — menu "🔄 PXV" sẽ hiện trên thanh công cụ.
 *
 * 8. Bấm menu 🔄 PXV > Kiểm tra cấu hình để xác nhận mọi thứ đã đúng.
 *
 * ============================================================
 */

/** Tạo toàn bộ trigger cần thiết. Chạy lại nhiều lần cũng không bị trùng. */
function taoTrigger() {
  _guardConfig();
  _xoaTriggerCu();

  // Quét thư mục KiotViet_Drop mỗi giờ — người export thả file lúc nào cũng được.
  ScriptApp.newTrigger('napKiotViet').timeBased().everyHours(1).create();

  // Canh chừng pipeline, 09:00 hằng ngày (sau giờ pipeline chạy 06:15).
  ScriptApp.newTrigger('canhChung').timeBased().atHour(9).everyDays(1).create();

  // Nhắc export KiotViet, 08:00 hằng ngày.
  ScriptApp.newTrigger('nhacExportKiotViet').timeBased().atHour(8).everyDays(1).create();

  // Nạp Pancake hằng tuần (sáng thứ Hai) — chỉ chạy khi đã điền PANCAKE_COLS.
  ScriptApp.newTrigger('napPancakeAnToan').timeBased()
    .onWeekDay(ScriptApp.WeekDay.MONDAY).atHour(7).create();

  const n = ScriptApp.getProjectTriggers().length;
  Logger.log('Đã tạo ' + n + ' trigger:');
  ScriptApp.getProjectTriggers().forEach(function (t) {
    Logger.log('  - ' + t.getHandlerFunction());
  });
}

/** Bọc napPancake để trigger hằng tuần không báo lỗi khi chưa cấu hình xong. */
function napPancakeAnToan() {
  if (!PANCAKE_COLS.SDT) {
    Logger.log('Bỏ qua: chưa điền PANCAKE_COLS (chạy khamPhaPancake() trước).');
    return;
  }
  napPancake();
}

function _xoaTriggerCu() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() !== 'onEdit' && t.getHandlerFunction() !== 'onOpen') {
      ScriptApp.deleteTrigger(t);
    }
  });
}

/**
 * Tạo sẵn các sheet phụ trợ trong file nhập liệu, kèm dữ liệu mẫu.
 * Chạy một lần sau khi tạo spreadsheet mới.
 */
function taoSheetPhuTro() {
  const ss = SpreadsheetApp.getActive();

  // Bảng sửa chính tả — marketing tự thêm dòng khi thấy sales gõ sai kiểu mới.
  if (!ss.getSheetByName(CONFIG.SHEET_ALIAS)) {
    const s = ss.insertSheet(CONFIG.SHEET_ALIAS);
    s.appendRow(['Gõ sai (viết hoa)', 'Sửa thành']);
    s.getRange(2, 1, 6, 2).setValues([
      ['INSTGRAM', 'Instagram'],
      ['FACEBOOOK', 'Facebook'],
      ['TIKTOK PXV ', 'Tiktok PXV'],
      ['FANPAGE PXV ', 'Fanpage PXV'],
      ['KHACH CU', 'Khách cũ'],
      ['ZALO ', 'Zalo'],
    ]);
    s.setFrozenRows(1);
  }

  // Danh mục giá trị hợp lệ cho dropdown.
  if (!ss.getSheetByName('DANH_MỤC')) {
    const s = ss.insertSheet('DANH_MỤC');
    s.appendRow(['NGUỒN', 'NHÓM SP', 'TT_QUAN_TÂM', 'TT_ĐẶT_HẸN', 'TT_CHỐT_ĐƠN',
                 'LÝ DO CHƯA CÓ SĐT', 'KÊNH (đã gom)']);
    const cols = [
      ['Fanpage PXV', 'Fanpage học viện', 'FB Cô Hường', 'Tiktok PXV',
       'Tiktok học viện', 'Instagram', 'Hotline', 'Zalo', 'Khách cũ',
       'Khách giới thiệu'],
      ['DỊCH VỤ', 'ĐÀO TẠO'],
      ['Quan tâm', 'Chỉ hỏi giá', 'Không phản hồi'],
      ['Đặt hẹn', 'Đã làm DV', 'Hủy lịch', 'Bom lịch'],
      ['Chốt đơn', 'Không chốt'],
      ['Khách chưa cho', 'Chỉ hỏi giá', 'Spam-ads', 'Khách cũ đã có số',
       'Chưa kịp hỏi'],
      // Cột G — KÊNH ĐÃ GOM. Nhiều NGUỒN gom về một kênh: 'Fanpage PXV' và
      // 'FB Cô Hường' đều là Facebook. Bảng CHI_PHÍ_QC phải nhập theo cột này,
      // KHÔNG phải cột NGUỒN, vì báo cáo hiệu quả tính theo kênh đã gom.
      ['Facebook', 'Tiktok', 'Instagram', 'Hotline/Zalo', 'Khách cũ',
       'Giới thiệu'],
    ];
    cols.forEach(function (vals, i) {
      s.getRange(2, i + 1, vals.length, 1)
       .setValues(vals.map(function (v) { return [v]; }));
    });
    s.setFrozenRows(1);
  }

  Logger.log('Đã tạo sheet phụ trợ. Bước tiếp theo: đặt Data Validation cho ' +
    'sheet LEAD trỏ vào DANH_MỤC, và đặt cột SỐ ĐT thành Plain text.');
}

/**
 * Đặt cột SỐ ĐT thành text. PHẢI CHẠY TRƯỚC KHI CÓ DỮ LIỆU.
 * Đây là nguyên nhân gốc của việc '0390000002' bị mất số 0 thành 390000002.
 */
function datDinhDangCotSdt() {
  const sheet = SpreadsheetApp.getActive().getSheetByName(CONFIG.SHEET_LEAD);
  if (!sheet) throw new Error('Không thấy sheet ' + CONFIG.SHEET_LEAD);
  const header = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const col = header.indexOf(LEAD_COLS.SDT) + 1;
  if (!col) throw new Error('Không thấy cột ' + LEAD_COLS.SDT);
  sheet.getRange(1, col, sheet.getMaxRows(), 1).setNumberFormat('@');
  Logger.log('Đã đặt cột ' + LEAD_COLS.SDT + ' (cột ' + col + ') thành text.');
}

/**
 * Tạo tab CHI_PHÍ_QC để marketing nhập chi phí quảng cáo hằng tháng.
 *
 * Không có bảng này thì dashboard chỉ trả lời được "kênh nào ra NHIỀU lead",
 * không trả lời được "kênh nào ĐÁNG tiền". Một kênh 200 lead tốn 50 triệu kém
 * hơn kênh 80 lead tốn 5 triệu, mà nhìn số lượng thì tưởng ngược lại.
 */
function taoTabChiPhiQC() {
  const ss = SpreadsheetApp.getActive();
  if (ss.getSheetByName('CHI_PHÍ_QC')) {
    Logger.log('Tab CHI_PHÍ_QC đã có sẵn.');
    return;
  }
  const s = ss.insertSheet('CHI_PHÍ_QC');
  s.appendRow(['tháng', 'kênh', 'mã bài QC', 'chi phí']);
  s.getRange(2, 1, 2, 4).setValues([
    ['2026-01', 'Facebook', 'QC-FB-001', 180000000],
    ['2026-01', 'Tiktok', 'QC-TT-001', 25000000],
  ]);
  s.setFrozenRows(1);
  s.getRange('A:A').setNumberFormat('@');       // tháng giữ dạng text
  s.getRange('D:D').setNumberFormat('#,##0');   // chi phí có dấu phân cách nghìn
  s.setColumnWidths(1, 4, 140);

  // Kênh phải chọn từ cột "KÊNH (đã gom)" của DANH_MỤC — KHÔNG phải cột NGUỒN.
  // Báo cáo hiệu quả tính theo kênh đã gom ('Facebook'), còn NGUỒN là giá trị
  // thô sales nhập ('Fanpage PXV', 'FB Cô Hường'). Chọn nhầm cột thì chi phí
  // không khớp dòng nào và biến mất khỏi mọi phép tính mà không ai biết.
  const dm = ss.getSheetByName('DANH_MỤC');
  if (dm) {
    const rule = SpreadsheetApp.newDataValidation()
      .requireValueInRange(dm.getRange('G2:G'), true)
      .setAllowInvalid(false)
      .setHelpText('Chọn kênh đã gom (Facebook, Tiktok...). Gõ tự do sẽ làm ' +
                   'chi phí không được tính vào báo cáo.')
      .build();
    s.getRange('B2:B').setDataValidation(rule);
  }

  s.getRange('F2').setValue(
    'Mỗi tháng nhập ~10 dòng. Cột "mã bài QC" để trống nếu tính chi phí ' +
    'cho cả kênh. Tháng ghi 2026-01 hoặc 01/2026 đều được.');
  Logger.log('Đã tạo tab CHI_PHÍ_QC (kèm 2 dòng ví dụ — xóa đi trước khi dùng thật).');
}
