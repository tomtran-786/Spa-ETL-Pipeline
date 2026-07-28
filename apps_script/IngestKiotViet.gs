/**
 * Nạp file export KiotViet từ thư mục Drive vào kho INVOICES_RAW.
 *
 * VÌ SAO CÓ FILE NÀY: tháng 12/2025 mất TOÀN BỘ hóa đơn (0 dòng, kẹp giữa
 * T11=302 và T1=484) và không ai biết cho tới 7 tháng sau, lúc đó KiotViet
 * không export lại được nữa. Nguyên nhân gốc không phải "quên export" mà là
 * mô hình mỗi lần export ghi đè file cũ — một lần quên là mất vĩnh viễn.
 *
 * Kho này CHỈ THÊM, không ghi đè. Quên một tháng thì export lại khoảng rộng
 * hơn lúc nào cũng được, kho tự vá; export trùng khoảng cũng không nhân đôi
 * doanh thu vì khử trùng theo (Mã hóa đơn + Mã hàng).
 *
 * Chạy theo trigger mỗi giờ — xem Setup.gs.
 */
function napKiotViet() {
  _guardConfig();
  const folder = DriveApp.getFolderById(CONFIG.KIOTVIET_FOLDER_ID);
  const files = folder.getFiles();
  let daXuLy = 0;

  while (files.hasNext()) {
    const file = files.next();
    if (file.getName().indexOf('~') === 0) continue;
    daXuLy++;
    try {
      _xuLyMotFile(file, folder);
    } catch (err) {
      _chuyenFile(file, folder, '_loi');
      _guiMail('❌ Không nạp được file KiotViet',
        'File: ' + file.getName() + '\n\nLý do: ' + err.message +
        '\n\nFile đã chuyển sang thư mục _loi. Sửa rồi thả lại vào KiotViet_Drop.');
    }
  }
  if (daXuLy === 0) Logger.log('Không có file mới.');
}

function _xuLyMotFile(file, folder) {
  const noiDung = _docNoiDung(file);
  const hash = Utilities.base64Encode(
    Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, noiDung));

  const kho = SpreadsheetApp.openById(CONFIG.KHO_ID);
  const log = _sheetOrCreate(kho, CONFIG.SHEET_KV_LOG,
    ['tháng', 'số hóa đơn', 'doanh thu', 'ngày nạp gần nhất', 'hash file']);

  // [Kiểm 1] Nội dung trùng lần nạp trước -> nhiều khả năng export nhầm khoảng cũ.
  if (_hashDaTonTai(log, hash)) {
    _chuyenFile(file, folder, '_trung');
    _guiMail('⚠️ File KiotViet trùng nội dung',
      'File "' + file.getName() + '" giống hệt một file đã nạp trước đó.\n\n' +
      'Nhiều khả năng bạn export nhầm khoảng ngày cũ. Kiểm tra lại khoảng ngày ' +
      'khi export rồi thả file mới vào.');
    return;
  }

  const rows = Utilities.parseCsv(noiDung);
  if (rows.length < 2) throw new Error('File rỗng hoặc chỉ có dòng tiêu đề.');

  // [Kiểm 2] Header đúng định dạng KiotViet.
  const header = rows[0].map(function (h) { return String(h).trim(); });
  const thieu = KIOTVIET_COLUMNS.filter(function (c) { return header.indexOf(c) < 0; });
  if (thieu.length) {
    throw new Error('File này không giống export KiotViet. Thiếu cột: ' +
      thieu.join(', ') + '. Bạn có chọn đúng báo cáo "Chi tiết hóa đơn" không?');
  }

  const idx = {};
  KIOTVIET_COLUMNS.forEach(function (c) { idx[c] = header.indexOf(c); });
  const data = rows.slice(1).filter(function (r) {
    return String(r[idx['Mã hóa đơn']] || '').trim() !== '';
  });
  if (!data.length) throw new Error('Không có dòng hóa đơn nào trong file.');

  const ngay = data.map(function (r) { return _parseNgay(r[idx['Thời gian']]); })
                   .filter(Boolean);
  if (!ngay.length) throw new Error('Không đọc được cột "Thời gian".');
  ngay.sort(function (a, b) { return a - b; });
  const dauKy = ngay[0], cuoiKy = ngay[ngay.length - 1];

  const canhBao = [];

  // [Kiểm 3] File cũ.
  const soNgayCu = Math.floor((new Date() - cuoiKy) / 86400000);
  if (soNgayCu > CONFIG.HOA_DON_CU_QUA_NGAY) {
    canhBao.push('Hóa đơn mới nhất trong file là ' + _dinhDangNgay(cuoiKy) +
      ', đã ' + soNgayCu + ' ngày. Kiểm tra lại khoảng ngày khi export.');
  }

  // [Kiểm 4] Thủng tháng — ĐÚNG CA ĐÃ XẢY RA VỚI T12/2025.
  const thang = {};
  ngay.forEach(function (d) { thang[_thangCua(d)] = true; });
  const thieuThang = _cacThangGiua(dauKy, cuoiKy).filter(function (t) { return !thang[t]; });
  if (thieuThang.length) {
    canhBao.push('THIẾU TOÀN BỘ HÓA ĐƠN THÁNG: ' + thieuThang.join(', ') +
      '. Export lại khoảng này ngay — dữ liệu thiếu quá lâu sẽ không lấy lại được.');
  }

  // [Kiểm 5] Nhiều ngày liên tiếp không có hóa đơn.
  const chuoiTrong = _chuoiNgayTrong(ngay, dauKy, cuoiKy);
  if (chuoiTrong.length) {
    canhBao.push('Không có hóa đơn nào trong ' + chuoiTrong.length +
      ' ngày liên tiếp quanh ' + chuoiTrong[0] + ' (nếu là ngày nghỉ thì bỏ qua).');
  }

  // [Kiểm 6] Sụt giảm bất thường so với trung bình đã ghi nhận.
  const sutGiam = _kiemSutGiam(log, thang, data, idx);
  if (sutGiam) canhBao.push(sutGiam);

  const themMoi = _upsert(kho, header, data);
  _capNhatLog(log, data, idx, hash);
  _chuyenFile(file, folder, '_daNap');

  const tomTat = 'File: ' + file.getName() +
    '\nKhoảng: ' + _dinhDangNgay(dauKy) + ' → ' + _dinhDangNgay(cuoiKy) +
    '\nDòng trong file: ' + data.length +
    '\nDòng thêm mới vào kho: ' + themMoi +
    '\nDòng đã có sẵn (bỏ qua): ' + (data.length - themMoi);

  if (canhBao.length) {
    _guiMail('⚠️ Nạp KiotViet xong nhưng có vấn đề',
      tomTat + '\n\n--- CẦN XỬ LÝ ---\n• ' + canhBao.join('\n• '));
  } else {
    Logger.log('Nạp OK: ' + tomTat);
  }
}

/** Đọc nội dung file. Chỉ nhận CSV — KiotViet export CSV sẵn. */
function _docNoiDung(file) {
  const ten = file.getName().toLowerCase();
  if (ten.slice(-4) === '.csv' || file.getMimeType() === MimeType.CSV) {
    return file.getBlob().getDataAsString('UTF-8');
  }
  throw new Error('Chỉ nhận file .csv. File "' + file.getName() + '" là định dạng khác. ' +
    'Trong KiotViet chọn Xuất file > CSV.');
}

/**
 * Thêm dòng mới vào kho, bỏ qua dòng đã có. Khóa khử trùng là
 * "Mã hóa đơn|Mã hàng" — một hóa đơn nhiều mặt hàng vẫn giữ đủ từng dòng.
 */
function _upsert(kho, header, data) {
  const sheet = _sheetOrCreate(kho, CONFIG.SHEET_INVOICES,
    header.concat(['_khóa', '_ngày nạp']));
  // Cột tiền phải là text: '9.420.000' mà để Sheets tự hiểu sẽ thành 9.42.
  sheet.getRange(1, 1, sheet.getMaxRows(), sheet.getLastColumn())
       .setNumberFormat('@');

  const daCo = {};
  if (sheet.getLastRow() > 1) {
    const colKhoa = header.length + 1;
    sheet.getRange(2, colKhoa, sheet.getLastRow() - 1, 1).getValues()
      .forEach(function (r) { daCo[r[0]] = true; });
  }

  const iHD = header.indexOf('Mã hóa đơn');
  const iMH = header.indexOf('Mã hàng');
  const homNay = _dinhDangNgay(new Date());
  const them = [];
  data.forEach(function (r) {
    const khoa = String(r[iHD]).trim() + '|' + String(r[iMH]).trim();
    if (daCo[khoa]) return;
    daCo[khoa] = true;
    them.push(r.concat([khoa, homNay]));
  });

  if (them.length) {
    sheet.getRange(sheet.getLastRow() + 1, 1, them.length, them[0].length)
         .setValues(them);
  }
  return them.length;
}

/** Log mỗi tháng một dòng — nhìn 3 giây là thấy tháng nào thủng. */
function _capNhatLog(log, data, idx, hash) {
  const theoThang = {};
  data.forEach(function (r) {
    const d = _parseNgay(r[idx['Thời gian']]);
    if (!d) return;
    const t = _thangCua(d);
    if (!theoThang[t]) theoThang[t] = { hd: {}, tien: 0 };
    const maHD = String(r[idx['Mã hóa đơn']]).trim();
    if (!theoThang[t].hd[maHD]) {
      theoThang[t].hd[maHD] = true;
      theoThang[t].tien += _parseTien(r[idx['Khách cần trả']]);
    }
  });

  const cu = {};
  if (log.getLastRow() > 1) {
    log.getRange(2, 1, log.getLastRow() - 1, 5).getValues()
      .forEach(function (r, i) { cu[String(r[0])] = i + 2; });
  }
  const homNay = _dinhDangNgay(new Date());
  Object.keys(theoThang).sort().forEach(function (t) {
    const soHD = Object.keys(theoThang[t].hd).length;
    const dong = [t, soHD, theoThang[t].tien, homNay, hash];
    if (cu[t]) log.getRange(cu[t], 1, 1, 5).setValues([dong]);
    else log.appendRow(dong);
  });
}

function _hashDaTonTai(log, hash) {
  if (log.getLastRow() < 2) return false;
  return log.getRange(2, 5, log.getLastRow() - 1, 1).getValues()
    .some(function (r) { return r[0] === hash; });
}

function _kiemSutGiam(log, thangTrongFile, data, idx) {
  if (log.getLastRow() < 4) return null;
  const rows = log.getRange(2, 1, log.getLastRow() - 1, 2).getValues();
  const ganDay = rows.slice(-3).map(function (r) { return Number(r[1]) || 0; });
  const tb = ganDay.reduce(function (a, b) { return a + b; }, 0) / ganDay.length;
  if (!tb) return null;

  const thangMoiNhat = Object.keys(thangTrongFile).sort().pop();
  const hd = {};
  data.forEach(function (r) {
    const d = _parseNgay(r[idx['Thời gian']]);
    if (d && _thangCua(d) === thangMoiNhat) hd[String(r[idx['Mã hóa đơn']])] = true;
  });
  const soHD = Object.keys(hd).length;
  if (soHD < tb * CONFIG.SUT_GIAM_BAT_THUONG) {
    return 'Tháng ' + thangMoiNhat + ' chỉ có ' + soHD + ' hóa đơn, thấp hơn nhiều so ' +
      'với trung bình ' + Math.round(tb) + '. Kiểm tra xem export đã đủ khoảng chưa.';
  }
  return null;
}

// --- Tiện ích ------------------------------------------------------------

function _sheetOrCreate(ss, ten, header) {
  let sheet = ss.getSheetByName(ten);
  if (!sheet) {
    sheet = ss.insertSheet(ten);
    sheet.appendRow(header);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function _chuyenFile(file, folder, tenThuMuc) {
  const it = folder.getFoldersByName(tenThuMuc);
  const dich = it.hasNext() ? it.next() : folder.createFolder(tenThuMuc);
  dich.addFile(file);
  folder.removeFile(file);
}

/** KiotViet ghi ngày kiểu dd/MM/yyyy, có thể kèm giờ. */
function _parseNgay(v) {
  if (!v) return null;
  if (v instanceof Date) return v;
  const m = String(v).trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (!m) {
    const d = new Date(v);
    return isNaN(d.getTime()) ? null : d;
  }
  return new Date(Number(m[3]), Number(m[2]) - 1, Number(m[1]));
}

/** '9.420.000' -> 9420000. Dấu chấm là ngăn nghìn, không phải thập phân. */
function _parseTien(v) {
  const n = parseInt(String(v == null ? '' : v).replace(/[^\d]/g, ''), 10);
  return isNaN(n) ? 0 : n;
}

function _dinhDangNgay(d) {
  return Utilities.formatDate(d, Session.getScriptTimeZone(), 'dd/MM/yyyy');
}

function _thangCua(d) {
  return Utilities.formatDate(d, Session.getScriptTimeZone(), 'yyyy-MM');
}

function _cacThangGiua(dau, cuoi) {
  const out = [];
  const d = new Date(dau.getFullYear(), dau.getMonth(), 1);
  while (d <= cuoi) {
    out.push(_thangCua(d));
    d.setMonth(d.getMonth() + 1);
  }
  return out;
}

/** Chuỗi >=3 ngày liên tiếp không có hóa đơn, bỏ qua ngày nghỉ đã khai báo. */
function _chuoiNgayTrong(ngay, dau, cuoi) {
  const co = {};
  ngay.forEach(function (d) {
    co[Utilities.formatDate(d, Session.getScriptTimeZone(), 'yyyy-MM-dd')] = true;
  });
  const nghi = {};
  CONFIG.NGAY_NGHI.forEach(function (n) { nghi[n] = true; });

  const trong = [];
  let chuoi = [];
  const d = new Date(dau);
  while (d <= cuoi) {
    const key = Utilities.formatDate(d, Session.getScriptTimeZone(), 'yyyy-MM-dd');
    if (!co[key] && !nghi[key]) {
      chuoi.push(key);
    } else {
      if (chuoi.length >= 3) trong.push.apply(trong, chuoi);
      chuoi = [];
    }
    d.setDate(d.getDate() + 1);
  }
  if (chuoi.length >= 3) trong.push.apply(trong, chuoi);
  return trong;
}

function _guiMail(tieuDe, noiDung) {
  MailApp.sendEmail({
    to: _alertEmails().join(','),
    subject: '[PXV] ' + tieuDe,
    body: noiDung + '\n\n--\nTin nhắn tự động từ pipeline Phun Xăm Vic.',
  });
}
