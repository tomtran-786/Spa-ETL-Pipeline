/**
 * Menu "🔄 PXV" trên thanh công cụ Google Sheets.
 *
 * Mục đích: quản lý tự xử được phần lớn sự cố mà không phải gọi lập trình viên.
 * Đây là cách giảm rủi ro "chỉ một người biết sửa".
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('🔄 PXV')
    .addItem('Chạy lại pipeline ngay', 'chayLaiPipeline')
    .addItem('Xem trạng thái dữ liệu', 'xemTrangThai')
    .addSeparator()
    .addItem('Nạp file KiotViet vừa thả', 'napKiotViet')
    .addItem('Nạp file Pancake vừa thả', 'napPancake')
    .addSeparator()
    .addItem('Kiểm tra cấu hình', 'kiemTraCauHinh')
    .addItem('⚙️ Dựng lại hệ thống (chạy 1 lần)', 'dungHeThong')
    .addToUi();
}

/**
 * Gọi GitHub Actions chạy lại pipeline mà không cần đợi tới 06:15 hôm sau.
 *
 * Token lưu ở Script Properties, KHÔNG để trong code (Apps Script nhiều người
 * xem được). Xem hướng dẫn tạo token trong Setup.gs.
 */
function chayLaiPipeline() {
  const ui = SpreadsheetApp.getUi();
  const token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
  if (!token) {
    ui.alert('Chưa cấu hình', 'Chưa có GITHUB_TOKEN trong Script Properties.\n\n' +
      'Xem hướng dẫn ở đầu file Setup.gs.', ui.ButtonSet.OK);
    return;
  }

  const url = 'https://api.github.com/repos/' + CONFIG.GITHUB_OWNER + '/' +
    CONFIG.GITHUB_REPO + '/dispatches';
  const res = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    headers: { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json' },
    payload: JSON.stringify({ event_type: 'chay-pipeline' }),
    muteHttpExceptions: true,
  });

  if (res.getResponseCode() === 204) {
    ui.alert('Đã gửi yêu cầu',
      'Pipeline đang chạy. Khoảng 2-3 phút nữa dashboard sẽ có số mới.\n\n' +
      'Xem tiến trình: github.com/' + CONFIG.GITHUB_OWNER + '/' +
      CONFIG.GITHUB_REPO + '/actions', ui.ButtonSet.OK);
  } else {
    ui.alert('Không gửi được',
      'GitHub trả về mã ' + res.getResponseCode() + '.\n\n' +
      res.getContentText().slice(0, 300) + '\n\n' +
      'Token có thể đã hết hạn — tạo token mới theo hướng dẫn ở Setup.gs.',
      ui.ButtonSet.OK);
  }
}

/** Hiện tóm tắt trạng thái để biết số trên dashboard có đáng tin không. */
function xemTrangThai() {
  const ui = SpreadsheetApp.getUi();
  try {
    const sheet = SpreadsheetApp.openById(_id('DASHBOARD_ID'))
      .getSheetByName(CONFIG.SHEET_DQ);
    if (!sheet || sheet.getLastRow() < 2) {
      ui.alert('Chưa có dữ liệu', 'Pipeline chưa chạy lần nào.', ui.ButtonSet.OK);
      return;
    }
    const rows = sheet.getRange(2, 1, sheet.getLastRow() - 1, 4).getValues();
    const dong = rows.map(function (r) {
      return r[1] + '  ' + r[0] + ': ' + r[2];
    });
    ui.alert('Trạng thái dữ liệu', dong.join('\n'), ui.ButtonSet.OK);
  } catch (err) {
    ui.alert('Lỗi', err.message, ui.ButtonSet.OK);
  }
}

/** Kiểm nhanh xem đã điền đủ ID và cấp đủ quyền chưa. */
function kiemTraCauHinh() {
  const ui = SpreadsheetApp.getUi();
  const ketQua = [];

  try {
    _guardConfig();
    ketQua.push('✅ Đã điền đủ ID trong Config.gs');
  } catch (err) {
    ui.alert('Cấu hình chưa xong', err.message, ui.ButtonSet.OK);
    return;
  }

  [['Kho PXV_KHO', _id('KHO_ID')], ['Dashboard', _id('DASHBOARD_ID')]]
    .forEach(function (p) {
      try {
        SpreadsheetApp.openById(p[1]).getName();
        ketQua.push('✅ Mở được ' + p[0]);
      } catch (e) {
        ketQua.push('❌ Không mở được ' + p[0] + ' — kiểm tra ID và quyền chia sẻ');
      }
    });

  [['KiotViet_Drop', _id('KIOTVIET_FOLDER_ID')], ['Pancake_Drop', _id('PANCAKE_FOLDER_ID')]]
    .forEach(function (p) {
      try {
        DriveApp.getFolderById(p[1]).getName();
        ketQua.push('✅ Mở được thư mục ' + p[0]);
      } catch (e) {
        ketQua.push('❌ Không mở được thư mục ' + p[0]);
      }
    });

  ketQua.push(PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN')
    ? '✅ Đã có GITHUB_TOKEN'
    : '⚠️ Chưa có GITHUB_TOKEN (nút "Chạy lại pipeline" sẽ không dùng được)');

  const triggers = ScriptApp.getProjectTriggers().length;
  ketQua.push(triggers >= 3
    ? '✅ Đã đặt ' + triggers + ' trigger'
    : '⚠️ Mới có ' + triggers + ' trigger — chạy hàm taoTrigger() trong Setup.gs');

  ui.alert('Kiểm tra cấu hình', ketQua.join('\n'), ui.ButtonSet.OK);
}
