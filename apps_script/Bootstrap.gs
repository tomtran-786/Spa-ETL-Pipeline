/**
 * DỰNG TOÀN BỘ HỆ THỐNG SHEETS — CHẠY MỘT LẦN DUY NHẤT.
 *
 * ============================================================
 * CÁCH DÙNG
 * ============================================================
 * 1. Tạo một Google Sheet TRỐNG, đặt tên "PXV_NHẬP_LIỆU"
 * 2. Extensions > Apps Script, dán TẤT CẢ file .gs trong thư mục apps_script/
 * 3. Chọn hàm `dungHeThong` ở thanh trên, bấm Run
 * 4. Google hỏi cấp quyền lần đầu -> Review permissions > Advanced >
 *    Go to ... (unsafe) > Allow  (script của chính bạn nên an toàn)
 * 5. Xem kết quả ở View > Logs — script in ra 3 ID để dán vào Config.gs
 *
 * Script tự tạo: 2 spreadsheet phụ, 2 thư mục Drive, toàn bộ tab, dropdown,
 * khóa vùng và định dạng. Chạy lại lần nữa cũng không hỏng — chỗ nào đã có
 * thì bỏ qua.
 * ============================================================
 */

const LEAD_HEADERS = [
  'NGÀY',                 // onEdit tự điền, không cho gõ tay
  'TÊN KHÁCH HÀNG',
  'SỐ ĐT',                // định dạng TEXT để không mất số 0 đầu
  'LÝ DO CHƯA CÓ SĐT',    // tách "sales chưa xin" khỏi "khách không cho"
  'LOẠI TIN NHẮN',
  'NHÓM SP',
  'CHATPAGE',
  'NGUỒN',
  'BÀI QC',               // để quy kết chi phí tới từng bài quảng cáo
  'QUAN TÂM',
  'TÌNH TRẠNG',
  'TT_QUAN_TÂM',          // 3 chặng: Quan tâm -> Đặt hẹn -> Chốt đơn
  'TT_ĐẶT_HẸN',
  'TT_CHỐT_ĐƠN',
  'GIỜ HẸN',
  'NGÀY HẸN',
  'GHI CHÚ',
];

const INVOICE_HEADERS = [
  'Mã hóa đơn', 'Thời gian', 'Mã khách hàng', 'Tên khách hàng', 'Điện thoại',
  'Người bán', 'Khách cần trả', 'Mã hàng', 'Tên hàng', 'Số lượng',
  '_khóa', '_ngày nạp',
];

function dungHeThong() {
  const ss = SpreadsheetApp.getActive();
  const ketQua = [];

  Logger.log('Bắt đầu dựng hệ thống...\n');

  _dungSheetNhapLieu(ss);
  ketQua.push(['PXV_NHẬP_LIỆU (file này)', ss.getId()]);

  const kho = _taoSpreadsheet('PXV_KHO', function (s) {
    _taoTab(s, 'INVOICES_RAW', INVOICE_HEADERS);
    _taoTab(s, 'PANCAKE_RAW', ['SĐT', 'Tên khách', 'Page', 'Ngày', '_ngày nạp']);
    _taoTab(s, 'KIOTVIET_LOG',
      ['tháng', 'số hóa đơn', 'doanh thu', 'ngày nạp gần nhất', 'hash file']);
    // Cột SĐT và tiền phải là text, nếu không Sheets đọc '9.420.000' thành 9.42
    s.getSheetByName('INVOICES_RAW').getRange('A:L').setNumberFormat('@');
    s.getSheetByName('PANCAKE_RAW').getRange('A:A').setNumberFormat('@');
  });
  ketQua.push(['PXV_KHO', kho.getId()]);

  const dash = _taoSpreadsheet('PXV_DASHBOARD_DATA', function (s) {
    // Tạo sẵn DQ_STATUS để watchdog không báo lỗi trước lần chạy pipeline đầu.
    _taoTab(s, 'DQ_STATUS', ['tên', 'trạng_thái', 'giá_trị', 'ghi_chú']);
    s.getSheetByName('DQ_STATUS').appendRow(
      ['Chạy lúc', '🟠 CẢNH BÁO', '', 'pipeline chưa chạy lần nào']);
  });
  ketQua.push(['PXV_DASHBOARD_DATA', dash.getId()]);

  const goc = _taoThuMuc('PXV');
  const kvDrop = _taoThuMucCon(goc, 'KiotViet_Drop');
  const pcDrop = _taoThuMucCon(goc, 'Pancake_Drop');
  ketQua.push(['Thư mục KiotViet_Drop', kvDrop.getId()]);
  ketQua.push(['Thư mục Pancake_Drop', pcDrop.getId()]);

  // Lưu vào Script Properties để các script khác dùng được ngay, đỡ phải
  // chép tay. Config.gs vẫn nên điền để người sau đọc code là biết.
  PropertiesService.getScriptProperties().setProperties({
    KHO_ID: kho.getId(),
    DASHBOARD_ID: dash.getId(),
    KIOTVIET_FOLDER_ID: kvDrop.getId(),
    PANCAKE_FOLDER_ID: pcDrop.getId(),
  });

  Logger.log('\n' + '='.repeat(64));
  Logger.log(' XONG. CHÉP CÁC ID SAU VÀO Config.gs');
  Logger.log('='.repeat(64));
  ketQua.forEach(function (r) { Logger.log('  ' + r[0] + ':\n      ' + r[1]); });
  Logger.log('\n' + '='.repeat(64));
  Logger.log(' VIỆC TIẾP THEO');
  Logger.log('='.repeat(64));
  Logger.log('  1. Dán 4 ID trên vào Config.gs (KHO_ID, DASHBOARD_ID,');
  Logger.log('     KIOTVIET_FOLDER_ID, PANCAKE_FOLDER_ID)');
  Logger.log('  2. Chạy hàm taoTrigger() để bật tự động hóa');
  Logger.log('  3. Chia sẻ 3 spreadsheet + thư mục PXV cho Service Account:');
  Logger.log('       PXV_NHẬP_LIỆU      -> Viewer');
  Logger.log('       PXV_KHO            -> Editor');
  Logger.log('       PXV_DASHBOARD_DATA -> Editor');
  Logger.log('  4. Đóng/mở lại file này để hiện menu 🔄 PXV');
  Logger.log('  5. Bấm 🔄 PXV > Kiểm tra cấu hình');
}

// --- Sheet nhập liệu -----------------------------------------------------

function _dungSheetNhapLieu(ss) {
  _taoTab(ss, 'DANH_MỤC', ['NGUỒN', 'NHÓM SP', 'TT_QUAN_TÂM', 'TT_ĐẶT_HẸN',
                           'TT_CHỐT_ĐƠN', 'LÝ DO CHƯA CÓ SĐT', 'KÊNH (đã gom)',
                           'LOẠI TIN NHẮN', 'CHATPAGE']);
  _dienDanhMuc(ss.getSheetByName('DANH_MỤC'));

  _taoTab(ss, 'ÁNH_XẠ_ALIAS', ['Gõ sai (viết hoa)', 'Sửa thành']);
  _dienAlias(ss.getSheetByName('ÁNH_XẠ_ALIAS'));

  _taoTab(ss, 'TỪ_LẠ_CHỜ_DUYỆT', ['giá trị lạ', 'cột', 'người nhập', 'thời điểm']);
  _taoTab(ss, 'CHI_PHÍ_QC', ['tháng', 'kênh', 'mã bài QC', 'chi phí']);

  const lead = _taoTab(ss, 'LEAD', LEAD_HEADERS);
  _dinhDangLead(lead);
  _datValidationLead(ss, lead);
  _khoaVungLead(lead);
  _dungTabHuongDan(ss);
  _dinhDangChiPhi(ss);

  // Xóa tab "Sheet1" mặc định nếu còn trống
  const mac_dinh = ss.getSheetByName('Sheet1') || ss.getSheetByName('Trang tính1');
  if (mac_dinh && ss.getSheets().length > 1 && mac_dinh.getLastRow() === 0) {
    ss.deleteSheet(mac_dinh);
  }
  Logger.log('  ✅ PXV_NHẬP_LIỆU: 6 tab, dropdown, khóa vùng, định dạng');
}

function _dienDanhMuc(s) {
  if (s.getLastRow() > 1) return;
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
    // KÊNH ĐÃ GOM — nhiều NGUỒN gom về một kênh ('Fanpage PXV' và 'FB Cô Hường'
    // đều là Facebook). Bảng CHI_PHÍ_QC nhập theo cột NÀY, không phải cột NGUỒN.
    ['Facebook', 'Tiktok', 'Instagram', 'Hotline/Zalo', 'Khách cũ', 'Giới thiệu'],
    ['TỰ NHIÊN', 'QUẢNG CÁO', 'ĐÃ TƯƠNG TÁC'],
    ['Sales 1', 'Sales 2', 'Sales 3'],   // đổi thành tên nhân viên thật
  ];
  cols.forEach(function (vals, i) {
    s.getRange(2, i + 1, vals.length, 1)
     .setValues(vals.map(function (v) { return [v]; }));
  });
  s.getRange(1, 1, 1, cols.length).setFontWeight('bold')
   .setBackground('#e8eaed');
  s.setFrozenRows(1);
}

function _dienAlias(s) {
  if (s.getLastRow() > 1) return;
  s.getRange(2, 1, 6, 2).setValues([
    ['INSTGRAM', 'Instagram'],
    ['INSTAGRAM', 'Instagram'],
    ['FACEBOOOK', 'Facebook'],
    ['KHACH CU', 'Khách cũ'],
    ['FANPAGE PXV', 'Fanpage PXV'],
    ['TIKTOK PXV', 'Tiktok PXV'],
  ]);
  s.getRange('C2').setValue(
    'Thêm dòng khi thấy sales gõ sai kiểu mới. Cột A viết HOA không dấu ' +
    'cách thừa; onEdit tự sửa thành cột B.');
}

function _dinhDangLead(lead) {
  const iSdt = LEAD_HEADERS.indexOf('SỐ ĐT') + 1;
  // Đặt TEXT trước khi có dữ liệu — đây là nguyên nhân gốc của việc SĐT bị
  // mất số 0 đầu. Đặt sau khi đã nhập thì không cứu được số cũ.
  lead.getRange(1, iSdt, lead.getMaxRows(), 1).setNumberFormat('@');

  const iNgay = LEAD_HEADERS.indexOf('NGÀY') + 1;
  const iHen = LEAD_HEADERS.indexOf('NGÀY HẸN') + 1;
  lead.getRange(1, iNgay, lead.getMaxRows(), 1).setNumberFormat('dd/MM/yyyy');
  lead.getRange(1, iHen, lead.getMaxRows(), 1).setNumberFormat('dd/MM/yyyy');

  lead.getRange(1, 1, 1, LEAD_HEADERS.length)
      .setFontWeight('bold').setBackground('#d9ead3').setWrap(true);
  lead.setFrozenRows(1);
  lead.setColumnWidths(1, LEAD_HEADERS.length, 130);

  // Tô đỏ dòng đã chuyển Đặt hẹn mà vẫn thiếu SĐT (onEdit chặn, đây là lớp 2)
  const colSdt = _chuCot(iSdt), colTT = _chuCot(LEAD_HEADERS.indexOf('TT_ĐẶT_HẸN') + 1);
  const rule = SpreadsheetApp.newConditionalFormatRule()
    .whenFormulaSatisfied('=AND($' + colTT + '2<>"",$' + colSdt + '2="")')
    .setBackground('#f4cccc')
    .setRanges([lead.getRange(2, 1, lead.getMaxRows() - 1, LEAD_HEADERS.length)])
    .build();
  lead.setConditionalFormatRules([rule]);
}

function _datValidationLead(ss, lead) {
  const dm = ss.getSheetByName('DANH_MỤC');
  // cột trong LEAD -> cột trong DANH_MỤC
  const map = {
    'NGUỒN': 'A', 'NHÓM SP': 'B', 'TT_QUAN_TÂM': 'C', 'TT_ĐẶT_HẸN': 'D',
    'TT_CHỐT_ĐƠN': 'E', 'LÝ DO CHƯA CÓ SĐT': 'F', 'LOẠI TIN NHẮN': 'H',
    'CHATPAGE': 'I',
  };
  Object.keys(map).forEach(function (ten) {
    const i = LEAD_HEADERS.indexOf(ten) + 1;
    if (!i) return;
    // TT_ĐẶT_HẸN dùng Reject vì nó quyết định bước phễu; các cột khác dùng
    // cảnh báo mềm, vì sales hay paste cả khối và Reject sẽ làm họ bỏ trống cột.
    const chatChe = (ten === 'TT_ĐẶT_HẸN');
    const rule = SpreadsheetApp.newDataValidation()
      .requireValueInRange(dm.getRange(map[ten] + '2:' + map[ten]), true)
      .setAllowInvalid(!chatChe)
      .build();
    lead.getRange(2, i, lead.getMaxRows() - 1, 1).setDataValidation(rule);
  });
}

function _khoaVungLead(lead) {
  // Khóa hàng header: sales chèn/đổi tên cột sẽ làm pipeline dừng vì lệch schema.
  const p = lead.getRange(1, 1, 1, LEAD_HEADERS.length).protect()
    .setDescription('Header — đổi tên cột sẽ làm pipeline dừng');
  p.removeEditors(p.getEditors());
  if (p.canDomainEdit()) p.setDomainEdit(false);
}

function _dinhDangChiPhi(ss) {
  const s = ss.getSheetByName('CHI_PHÍ_QC');
  if (s.getLastRow() > 1) return;
  s.getRange('A:A').setNumberFormat('@');
  s.getRange('D:D').setNumberFormat('#,##0');
  s.getRange(1, 1, 1, 4).setFontWeight('bold').setBackground('#fff2cc');
  s.setFrozenRows(1);
  s.setColumnWidths(1, 4, 140);
  const dm = ss.getSheetByName('DANH_MỤC');
  const rule = SpreadsheetApp.newDataValidation()
    .requireValueInRange(dm.getRange('G2:G'), true).setAllowInvalid(false)
    .setHelpText('Chọn KÊNH ĐÃ GOM (Facebook, Tiktok...), không phải NGUỒN.')
    .build();
  s.getRange('B2:B').setDataValidation(rule);
  s.getRange('F2').setValue(
    'Marketing nhập ~10 dòng/tháng. Không có bảng này thì dashboard chỉ biết ' +
    'kênh nào ra NHIỀU lead, không biết kênh nào ĐÁNG tiền.');
}

function _dungTabHuongDan(ss) {
  if (ss.getSheetByName('HƯỚNG_DẪN')) return;
  const s = ss.insertSheet('HƯỚNG_DẪN', 0);
  const dong = [
    ['QUY TẮC BẮT BUỘC — vi phạm sẽ làm pipeline dừng hoặc ra số sai'],
    [''],
    ['1. Hàng 1 là header, KHÔNG đổi tên / chèn / xóa cột'],
    ['2. KHÔNG gộp ô (merge), KHÔNG thêm dòng tổng ở cuối bảng'],
    ['3. Một dòng = một lần khách nhắn tin'],
    ['4. KHÔNG dùng màu để ghi nhớ ý nghĩa — màu không export được, hãy dùng cột'],
    ['5. Cột NGÀY tự điền, không gõ tay'],
    [''],
    ['NHẬP LIỆU'],
    ['- Xin được SĐT thì nhập ngay. Chưa xin được thì chọn LÝ DO CHƯA CÓ SĐT'],
    ['- Chuyển TT_ĐẶT_HẸN sang "Đặt hẹn" bắt buộc phải có SĐT (hệ thống chặn)'],
    ['- NGUỒN gõ sai chính tả hệ thống tự sửa'],
    [''],
    ['KHI CÓ SỰ CỐ — xem RUNBOOK.md, hoặc bấm menu 🔄 PXV > Xem trạng thái'],
  ];
  s.getRange(1, 1, dong.length, 1).setValues(dong);
  s.getRange('A1').setFontWeight('bold').setFontSize(13);
  s.getRange('A9').setFontWeight('bold');
  s.setColumnWidth(1, 640);
}

// --- Tiện ích ------------------------------------------------------------

function _taoSpreadsheet(ten, dungNoiDung) {
  const cu = DriveApp.getFilesByName(ten);
  if (cu.hasNext()) {
    const s = SpreadsheetApp.open(cu.next());
    Logger.log('  ↷ ' + ten + ' đã có, bỏ qua');
    return s;
  }
  const s = SpreadsheetApp.create(ten);
  dungNoiDung(s);
  const mac_dinh = s.getSheetByName('Sheet1') || s.getSheetByName('Trang tính1');
  if (mac_dinh && s.getSheets().length > 1) s.deleteSheet(mac_dinh);
  Logger.log('  ✅ ' + ten);
  return s;
}

function _taoTab(ss, ten, header) {
  let s = ss.getSheetByName(ten);
  if (!s) {
    s = ss.insertSheet(ten);
    s.appendRow(header);
    s.setFrozenRows(1);
    s.getRange(1, 1, 1, header.length).setFontWeight('bold');
  }
  return s;
}

function _taoThuMuc(ten) {
  const it = DriveApp.getFoldersByName(ten);
  return it.hasNext() ? it.next() : DriveApp.createFolder(ten);
}

function _taoThuMucCon(cha, ten) {
  const it = cha.getFoldersByName(ten);
  const f = it.hasNext() ? it.next() : cha.createFolder(ten);
  Logger.log('  ✅ Thư mục ' + ten);
  return f;
}

/** 1 -> 'A', 27 -> 'AA' */
function _chuCot(n) {
  let s = '';
  while (n > 0) {
    const m = (n - 1) % 26;
    s = String.fromCharCode(65 + m) + s;
    n = (n - m - 1) / 26;
  }
  return s;
}
