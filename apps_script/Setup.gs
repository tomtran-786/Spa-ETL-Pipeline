/**
 * CHẠY MỘT LẦN KHI CÀI ĐẶT.
 *
 * ============================================================
 * CÁC BƯỚC CÀI (làm đúng thứ tự)
 * ============================================================
 *
 * 1. Tạo Google Sheet TRỐNG, đặt tên "PXV_NHẬP_LIỆU"
 *    > Tiện ích mở rộng (Extensions) > Apps Script
 *
 * 2. Dán từng file .gs trong thư mục apps_script/ vào project
 *    (bấm + > Script, đặt tên đúng như tên file, rồi dán nội dung)
 *
 * 3. Bật hai Advanced Services:
 *    - Drive API: đọc file Excel của Pancake
 *    - Google Sheets API: ghi lead bằng valueInputOption=RAW
 *    Menu trái > Services (+) > chọn từng API > Add
 *
 * 4. Chạy hàm dungHeThong() ở Bootstrap.gs
 *    Lần đầu Google sẽ hỏi cấp quyền — bấm Review permissions > Advanced >
 *    Go to ... (unsafe) > Allow. Đây là script của chính bạn nên an toàn.
 *    Script tự tạo 2 spreadsheet còn lại, 2 thư mục Drive, toàn bộ tab,
 *    dropdown và định dạng. Xem View > Logs để lấy các ID.
 *
 * 5. Chép các ID từ Logs vào Config.gs, rồi chạy taoTrigger() ở file này.
 *    (Bỏ qua bước chép cũng chạy được — dungHeThong() đã lưu ID vào Script
 *    Properties — nhưng nên điền để người sau đọc code là biết.)
 *
 * 6. (Không bắt buộc) Để nút "Chạy lại pipeline" hoạt động:
 *    a. Vào github.com > Settings > Developer settings >
 *       Personal access tokens > Fine-grained tokens > Generate new token
 *    b. Repository access: chọn đúng repo GitHub hiện tại của pipeline
 *    c. Permissions > Repository permissions > Contents: Read and write
 *    d. Copy token
 *    e. Về Apps Script > Project Settings (bánh răng) > Script Properties >
 *       Add script property: tên GITHUB_TOKEN, giá trị là token vừa copy
 *    f. Thêm script property GITHUB_REPO, giá trị là tên repo GitHub hiện tại
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
  const manager = SpreadsheetApp.getActive();
  PropertiesService.getScriptProperties().setProperty('MANAGER_ID', manager.getId());
  _dungSalesAdmin(manager);

  // Quét thư mục KiotViet_Drop mỗi giờ — người export thả file lúc nào cũng được.
  ScriptApp.newTrigger('napKiotViet').timeBased().everyHours(1).create();

  // Canh chừng pipeline, 09:00 hằng ngày (sau giờ pipeline chạy 06:15).
  ScriptApp.newTrigger('canhChung').timeBased().atHour(9).everyDays(1).create();

  // Nhắc export KiotViet, 08:00 hằng ngày.
  ScriptApp.newTrigger('nhacExportKiotViet').timeBased().atHour(8).everyDays(1).create();

  // Nạp Pancake hằng tuần (sáng thứ Hai) — chỉ chạy khi đã điền PANCAKE_COLS.
  ScriptApp.newTrigger('napPancakeAnToan').timeBased()
    .onWeekDay(ScriptApp.WeekDay.MONDAY).atHour(7).create();

  // Quét các batch sale đã bấm Nộp. Trigger chạy bằng quyền chủ file quản lý.
  ScriptApp.newTrigger('napLeadTuSales').timeBased().everyMinutes(5).create();
  _salesRegistryRecords(manager.getSheetByName(CONFIG.SHEET_SALES_REGISTRY))
    .forEach(function (item) {
      if (_salesIsActive(item.record.active) && item.record.file_id) {
        _ensureSalesOnEditTrigger(item.record.file_id);
      }
    });

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
  const scheduled = [
    'napKiotViet', 'canhChung', 'nhacExportKiotViet',
    'napPancakeAnToan', 'napLeadTuSales',
  ];
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (scheduled.indexOf(t.getHandlerFunction()) >= 0) {
      ScriptApp.deleteTrigger(t);
    }
  });
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
 * Hai hàm taoSheetPhuTro() và taoTabChiPhiQC() đã được gộp vào
 * dungHeThong() trong Bootstrap.gs — dựng một lần là ra đủ mọi tab.
 */
