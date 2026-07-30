/**
 * Quản trị file sale và đồng bộ revision vào LEAD trung tâm.
 *
 * Mọi hàm trong file này chạy bằng quyền chủ file PXV_NHẬP_LIỆU. Sale chỉ có
 * quyền sửa file riêng; installable onEdit trigger cũng do quản lý sở hữu.
 */

const SALES_REGISTRY_HEADERS = [
  'sale_id', 'tên sale', 'gmail', 'file_id', 'active',
  'lần đồng bộ cuối', 'lỗi gần nhất',
];

const SALES_LOG_HEADERS = [
  'thời điểm', 'lead_id', 'revision', 'batch_id', 'sale_id', 'file_id',
  'source_row', 'target_row', 'hành động', 'trường thay đổi',
  'before_json', 'after_json', 'checksum_before', 'checksum_after',
  'kết quả', 'lỗi', 'lý do trùng',
];

const SALES_ERROR_HEADERS = [
  'thời điểm', 'lead_id', 'revision', 'batch_id', 'sale_id', 'file_id',
  'source_row', 'mã lỗi', 'trường lỗi', 'thông báo',
  'trạng thái', 'resolved_at',
];

const SALES_CATALOG_HEADERS = [
  'NGUỒN', 'NHÓM SP', 'TÌNH TRẠNG', 'TRẠNG THÁI',
  'TƯ VẤN - SALE', 'LÝ DO CHƯA CÓ SĐT', 'KÊNH (đã gom)',
  'LOẠI TIN NHẮN', 'CHATPAGE',
];

const SALES_DEFAULT_STATUSES = [
  'Nhắn Qua Zalo', 'CẦN GỌI LẠI', 'KHÁCH CHỈ NT', 'CHỜ TRẢ LỜI',
  'KHÔNG TƯƠNG TÁC', 'BẤM QC TỰ ĐỘNG', 'GẤP', 'Ứng tuyển',
  'ĐẶT HẸN', 'ĐÃ LÀM DV', 'DỜI LỊCH',
];

const SALES_DEFAULT_NAMES = [
  'Trường Khang', 'Hoàng Diễm', 'Bảo Bình', 'Thanh Hằng',
  'Thùy Dương', 'Mai Thy', 'Lễ Tân', 'CSKH',
];

/** Nâng cấp file quản lý hiện có mà không tạo lại kho/dashboard. */
function dungHeThongSales() {
  const manager = SpreadsheetApp.getActive();
  PropertiesService.getScriptProperties().setProperty('MANAGER_ID', manager.getId());
  const root = _taoThuMuc('PXV');
  const folder = _taoThuMucCon(root, 'Sales_Entry');
  PropertiesService.getScriptProperties().setProperty('SALES_FOLDER_ID', folder.getId());
  _migrateSalesCatalogIfNeeded(manager);
  _dungSalesAdmin(manager);
  SpreadsheetApp.getUi().alert(
    'PXV Sales Entry đã sẵn sàng',
    'Đã tạo registry, log, bảng lỗi và metadata LEAD.\n\n' +
      'Bước tiếp theo: menu 🔄 PXV > Sales Entry > Tạo file cho sale.',
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}

function _dungSalesAdmin(manager) {
  _salesEnsureAdminTab(manager, CONFIG.SHEET_SALES_REGISTRY, SALES_REGISTRY_HEADERS);
  _salesEnsureAdminTab(manager, CONFIG.SHEET_SALES_LOG, SALES_LOG_HEADERS);
  _salesEnsureAdminTab(manager, CONFIG.SHEET_SALES_ERRORS, SALES_ERROR_HEADERS);

  [
    CONFIG.SHEET_SALES_REGISTRY,
    CONFIG.SHEET_SALES_LOG,
    CONFIG.SHEET_SALES_ERRORS,
  ].forEach(function (name) {
    const sheet = manager.getSheetByName(name);
    sheet.setFrozenRows(1);
    sheet.getRange(1, 1, 1, sheet.getLastColumn())
      .setFontWeight('bold').setBackground('#d9ead3').setWrap(true);
  });

  const registry = manager.getSheetByName(CONFIG.SHEET_SALES_REGISTRY);
  registry.setColumnWidths(1, SALES_REGISTRY_HEADERS.length, 150);
  const activeCol = SALES_REGISTRY_HEADERS.indexOf('active') + 1;
  registry.getRange(2, activeCol, Math.max(registry.getMaxRows() - 1, 1), 1)
    .setDataValidation(SpreadsheetApp.newDataValidation().requireCheckbox().build());

  _salesEnsureCentralLeadHeaders(manager);
  _salesSeedRegistry(manager);
}

function _salesEnsureAdminTab(manager, name, expectedHeaders) {
  const sheet = _taoTab(manager, name, expectedHeaders);
  const current = _salesHeaders(sheet);
  expectedHeaders.forEach(function (header) {
    if (current.indexOf(header) >= 0) return;
    current.push(header);
    _salesEnsureSize(sheet, sheet.getMaxRows(), current.length);
    sheet.getRange(1, current.length).setValue(header);
  });
  return sheet;
}

/**
 * Live DANH_MỤC từng còn schema ba chặng cũ. Backup trước, rồi dựng canonical
 * mà không đụng một ô nào trong LEAD.
 */
function migrateDanhMucSales() {
  const manager = SpreadsheetApp.getActive();
  const changed = _migrateSalesCatalogIfNeeded(manager);
  SpreadsheetApp.getUi().alert(
    changed ? 'Đã migrate DANH_MỤC và giữ một tab backup.' : 'DANH_MỤC đã đúng schema.',
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}

function _migrateSalesCatalogIfNeeded(manager) {
  let sheet = manager.getSheetByName('DANH_MỤC');
  if (!sheet) {
    sheet = _taoTab(manager, 'DANH_MỤC', SALES_CATALOG_HEADERS);
    _dienDanhMuc(sheet);
    return true;
  }
  const currentHeaders = sheet.getRange(1, 1, 1, sheet.getLastColumn())
    .getDisplayValues()[0].map(function (value) { return String(value).trim(); });
  if (SALES_CATALOG_HEADERS.every(function (header, index) {
    return currentHeaders[index] === header;
  })) {
    return false;
  }

  const timestamp = Utilities.formatDate(
    new Date(), 'Asia/Ho_Chi_Minh', 'yyyyMMdd_HHmmss'
  );
  const backup = sheet.copyTo(manager);
  backup.setName(('DM_BACKUP_' + timestamp).slice(0, 99));

  const oldValues = sheet.getDataRange().getDisplayValues();
  const oldMap = {};
  currentHeaders.forEach(function (header, index) { oldMap[header] = index; });
  const preserved = {};
  ['NGUỒN', 'NHÓM SP', 'LÝ DO CHƯA CÓ SĐT', 'KÊNH (đã gom)',
   'LOẠI TIN NHẮN', 'CHATPAGE'].forEach(function (header) {
    if (!(header in oldMap)) return;
    preserved[header] = oldValues.slice(1).map(function (row) {
      return String(row[oldMap[header]] || '').trim();
    }).filter(String);
  });

  const names = _salesObservedNames(manager);
  const canonical = {
    'NGUỒN': preserved['NGUỒN'] || [],
    'NHÓM SP': preserved['NHÓM SP'] || [],
    'TÌNH TRẠNG': SALES_DEFAULT_STATUSES,
    'TRẠNG THÁI': SALES_DEFAULT_STATUSES,
    'TƯ VẤN - SALE': names,
    'LÝ DO CHƯA CÓ SĐT': preserved['LÝ DO CHƯA CÓ SĐT'] || [],
    'KÊNH (đã gom)': preserved['KÊNH (đã gom)'] || [],
    'LOẠI TIN NHẮN': preserved['LOẠI TIN NHẮN'] || [],
    'CHATPAGE': preserved['CHATPAGE'] || [],
  };

  sheet.clearContents();
  _salesEnsureSize(sheet, Math.max.apply(null, SALES_CATALOG_HEADERS.map(function (header) {
    return (canonical[header] || []).length + 1;
  })), SALES_CATALOG_HEADERS.length);
  sheet.getRange(1, 1, 1, SALES_CATALOG_HEADERS.length).setValues([SALES_CATALOG_HEADERS]);
  SALES_CATALOG_HEADERS.forEach(function (header, col) {
    const values = canonical[header] || [];
    if (values.length) {
      sheet.getRange(2, col + 1, values.length, 1)
        .setValues(values.map(function (value) { return [value]; }));
    }
  });
  sheet.getRange(1, 1, 1, SALES_CATALOG_HEADERS.length)
    .setFontWeight('bold').setBackground('#e8eaed').setWrap(true);
  sheet.setFrozenRows(1);
  return true;
}

function _salesObservedNames(manager) {
  const names = {};
  SALES_DEFAULT_NAMES.forEach(function (name) { names[name] = true; });
  const lead = manager.getSheetByName(CONFIG.SHEET_LEAD);
  if (!lead || lead.getLastRow() < 2) return Object.keys(names);
  const headers = _salesHeaders(lead);
  const col = headers.indexOf(LEAD_COLS.TU_VAN) + 1;
  if (!col) return Object.keys(names);
  lead.getRange(2, col, lead.getLastRow() - 1, 1).getDisplayValues()
    .forEach(function (row) {
      String(row[0] || '').split(',').forEach(function (part) {
        const name = part.trim();
        if (name) names[name] = true;
      });
    });
  return Object.keys(names).sort();
}

function _salesEnsureCentralLeadHeaders(manager) {
  const lead = manager.getSheetByName(CONFIG.SHEET_LEAD);
  if (!lead) throw new Error('Không thấy sheet ' + CONFIG.SHEET_LEAD);
  const headers = _salesHeaders(lead);
  SALES_CENTRAL_META_HEADERS.forEach(function (header) {
    if (headers.indexOf(header) >= 0) return;
    headers.push(header);
    _salesEnsureSize(lead, lead.getMaxRows(), headers.length);
    lead.getRange(1, headers.length).setValue(header);
  });

  const refreshed = _salesHeaders(lead);
  SALES_CENTRAL_META_HEADERS.forEach(function (header) {
    const col = refreshed.indexOf(header) + 1;
    lead.getRange(1, col, lead.getMaxRows(), 1).setNumberFormat('@');
    lead.getRange(1, col).setFontWeight('bold').setBackground('#d9ead3');
    if (!lead.isColumnHiddenByUser(col)) lead.hideColumns(col);
    const protections = lead.getProtections(SpreadsheetApp.ProtectionType.RANGE)
      .filter(function (protection) {
        return protection.getDescription() === 'PXV Sales metadata: ' + header;
      });
    if (!protections.length) {
      const protection = lead.getRange(1, col, lead.getMaxRows(), 1).protect()
        .setDescription('PXV Sales metadata: ' + header);
      protection.removeEditors(protection.getEditors());
      if (protection.canDomainEdit()) protection.setDomainEdit(false);
    }
  });
}

function _salesSeedRegistry(manager) {
  const registry = manager.getSheetByName(CONFIG.SHEET_SALES_REGISTRY);
  const existing = {};
  if (registry.getLastRow() > 1) {
    registry.getRange(2, 1, registry.getLastRow() - 1, SALES_REGISTRY_HEADERS.length)
      .getDisplayValues().forEach(function (row) {
        existing[String(row[1] || '').trim()] = true;
      });
  }
  const rows = _salesObservedNames(manager).filter(function (name) {
    return !existing[name];
  }).map(function (name) {
    return [_salesSlug(name), name, '', '', false, '', ''];
  });
  if (rows.length) {
    registry.getRange(registry.getLastRow() + 1, 1, rows.length, rows[0].length)
      .setValues(rows);
  }
}

/** Menu quản lý: hỏi tên + Gmail, rồi tạo file và trigger. */
function taoFileChoSale() {
  const ui = SpreadsheetApp.getUi();
  const namePrompt = ui.prompt(
    'Tạo file sale', 'Nhập tên sale đúng như DANH_MỤC:', ui.ButtonSet.OK_CANCEL
  );
  if (namePrompt.getSelectedButton() !== ui.Button.OK) return;
  const saleName = namePrompt.getResponseText().trim();
  const emailPrompt = ui.prompt(
    'Tạo file sale', 'Nhập Gmail của ' + saleName + ':', ui.ButtonSet.OK_CANCEL
  );
  if (emailPrompt.getSelectedButton() !== ui.Button.OK) return;

  try {
    const result = _salesCreateFile(
      SpreadsheetApp.getActive(), saleName, emailPrompt.getResponseText().trim()
    );
    ui.alert(
      'Đã tạo file',
      'File: ' + result.name + '\n' + result.url +
        '\n\nĐã share Editor cho ' + result.email + ' và cài trigger kiểm tra.',
      ui.ButtonSet.OK
    );
  } catch (err) {
    ui.alert('Không tạo được file', err.message, ui.ButtonSet.OK);
  }
}

function _salesCreateFile(manager, saleName, email) {
  if (!saleName) throw new Error('Tên sale không được trống');
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
    throw new Error('Gmail không hợp lệ: ' + email);
  }
  _dungSalesAdmin(manager);
  const registry = manager.getSheetByName(CONFIG.SHEET_SALES_REGISTRY);
  const registryRows = _salesRegistryRecords(registry);
  const found = registryRows.filter(function (item) {
    return pxvSalesNormalizeText(item.record['tên sale']) ===
      pxvSalesNormalizeText(saleName);
  })[0];
  if (found && found.record.file_id) {
    throw new Error('Sale này đã có file: ' + found.record.file_id);
  }

  const saleId = found ? found.record.sale_id : _salesSlug(saleName);
  const file = SpreadsheetApp.create('PXV_SALES_' + saleName);
  file.setSpreadsheetLocale('vi_VN');
  file.setSpreadsheetTimeZone('Asia/Ho_Chi_Minh');
  _salesMoveToFolder(file.getId(), _salesFolder());
  _salesBuildFile(manager, file, {
    sale_id: saleId,
    sale_name: saleName,
    email: email,
    manager_id: manager.getId(),
  });
  DriveApp.getFileById(file.getId()).addEditor(email);
  _ensureSalesOnEditTrigger(file.getId());

  const registryRecord = {
    sale_id: saleId,
    'tên sale': saleName,
    gmail: email,
    file_id: file.getId(),
    active: true,
    'lần đồng bộ cuối': '',
    'lỗi gần nhất': '',
  };
  if (found) {
    _salesWriteRegistryRecord(registry, found.row, registryRecord);
  } else {
    registry.appendRow(SALES_REGISTRY_HEADERS.map(function (header) {
      return registryRecord[header] == null ? '' : registryRecord[header];
    }));
  }
  return { name: file.getName(), url: file.getUrl(), email: email };
}

function _salesBuildFile(manager, salesFile, sale) {
  const first = salesFile.getSheets()[0];
  first.setName(SALES_TABS.FORM);
  first.clear();
  [
    SALES_TABS.TRACKING,
    SALES_TABS.TODAY,
    SALES_TABS.HISTORY,
    SALES_TABS.CATALOG,
    SALES_TABS.CONFIG,
  ].forEach(function (name) {
    if (!salesFile.getSheetByName(name)) salesFile.insertSheet(name);
  });

  _salesBuildForm(salesFile.getSheetByName(SALES_TABS.FORM), sale);
  _salesBuildTracking(salesFile.getSheetByName(SALES_TABS.TRACKING));
  _salesBuildReadOnlyTable(
    salesFile.getSheetByName(SALES_TABS.TODAY), SALES_TODAY_HEADERS, '#d9ead3'
  );
  _salesBuildReadOnlyTable(
    salesFile.getSheetByName(SALES_TABS.HISTORY), SALES_HISTORY_HEADERS, '#d9ead3'
  );
  _salesWriteConfig(salesFile, sale);
  _salesSyncCatalogToFile(manager, salesFile);
  _salesApplyTrackingValidations(salesFile);
  _salesProtectFile(salesFile);
  _salesRefreshToday(salesFile);

  salesFile.setActiveSheet(salesFile.getSheetByName(SALES_TABS.FORM));
  salesFile.getSheetByName(SALES_TABS.CATALOG).hideSheet();
  salesFile.getSheetByName(SALES_TABS.CONFIG).hideSheet();
}

function _salesBuildForm(sheet, sale) {
  _salesEnsureSize(sheet, 30, 4);
  sheet.getRange('A1:D1').merge().setValue('PXV — NHẬP LEAD | ' + sale.sale_name)
    .setFontWeight('bold').setFontSize(16).setFontColor('#ffffff')
    .setBackground('#274e13').setHorizontalAlignment('center');
  sheet.getRange('A2:D2').merge().setValue(
    'Nhập một khách → Lưu tạm. Cuối ngày bấm Nộp để gửi các dòng hợp lệ.'
  ).setBackground('#d9ead3').setWrap(true);
  sheet.getRange(SALES_FORM_START_ROW, 1, SALES_FORM_FIELDS.length, 1)
    .setValues(SALES_FORM_FIELDS.map(function (field) { return [field]; }))
    .setFontWeight('bold').setBackground('#f3f6f4');
  sheet.getRange(SALES_FORM_START_ROW, 2, SALES_FORM_FIELDS.length, 1)
    .setBackground('#fff2cc');
  sheet.getRange('A22').setValue('LƯU TẠM').setFontWeight('bold');
  sheet.getRange('A23').setValue('NỘP CUỐI NGÀY').setFontWeight('bold');
  sheet.getRange(SALES_FORM_SAVE_CELL).insertCheckboxes();
  sheet.getRange(SALES_FORM_SUBMIT_CELL).insertCheckboxes();
  sheet.getRange('A25').setValue('KẾT QUẢ').setFontWeight('bold');
  sheet.getRange('B25:D26').merge().setWrap(true);
  sheet.setColumnWidth(1, 190);
  sheet.setColumnWidth(2, 330);
  sheet.setColumnWidths(3, 2, 90);
  sheet.setFrozenRows(2);
  sheet.setHiddenGridlines(true);

  const dateRow = SALES_FORM_START_ROW + SALES_FORM_FIELDS.indexOf(LEAD_COLS.NGAY_HEN);
  const timeRow = SALES_FORM_START_ROW + SALES_FORM_FIELDS.indexOf(LEAD_COLS.GIO_HEN);
  const phoneRow = SALES_FORM_START_ROW + SALES_FORM_FIELDS.indexOf(LEAD_COLS.SDT);
  sheet.getRange(phoneRow, 2).setNumberFormat('@');
  sheet.getRange(dateRow, 2).setNumberFormat('yyyy-mm-dd');
  sheet.getRange(timeRow, 2).setNumberFormat('HH:mm');
}

function _salesBuildTracking(sheet) {
  sheet.clear();
  _salesEnsureSize(sheet, 1000, SALES_TRACKING_HEADERS.length);
  sheet.getRange(1, 1, 1, SALES_TRACKING_HEADERS.length).setValues([SALES_TRACKING_HEADERS])
    .setFontWeight('bold').setBackground('#274e13').setFontColor('#ffffff')
    .setWrap(true);
  sheet.setFrozenRows(1);
  sheet.setFrozenColumns(3);
  sheet.setColumnWidth(1, 110);
  sheet.setColumnWidth(2, 280);
  sheet.setColumnWidth(3, 105);
  sheet.setColumnWidths(7, 12, 145);
  sheet.getRange(2, 1, sheet.getMaxRows() - 1, SALES_TRACKING_HEADERS.length)
    .setVerticalAlignment('middle');
  const closeCol = SALES_TRACKING_HEADERS.indexOf(SALES_META.CLOSE_ACTION) + 1;
  sheet.getRange(2, closeCol, sheet.getMaxRows() - 1, 1).insertCheckboxes();
  [
    LEAD_COLS.SDT,
    SALES_META.LEAD_ID,
    SALES_META.BATCH_ID,
    SALES_META.CENTRAL_CHECKSUM,
    SALES_META.SOURCE_SALE_ID,
  ].forEach(function (field) {
    const col = SALES_TRACKING_HEADERS.indexOf(field) + 1;
    if (col) sheet.getRange(1, col, sheet.getMaxRows(), 1).setNumberFormat('@');
  });
  [LEAD_COLS.NGAY, LEAD_COLS.NGAY_HEN].forEach(function (field) {
    const col = SALES_TRACKING_HEADERS.indexOf(field) + 1;
    if (col) sheet.getRange(2, col, sheet.getMaxRows() - 1, 1).setNumberFormat('yyyy-mm-dd');
  });
  const timeCol = SALES_TRACKING_HEADERS.indexOf(LEAD_COLS.GIO_HEN) + 1;
  if (timeCol) {
    sheet.getRange(2, timeCol, sheet.getMaxRows() - 1, 1).setNumberFormat('HH:mm');
  }
  if (!sheet.getFilter()) {
    sheet.getRange(1, 1, sheet.getMaxRows(), SALES_TRACKING_HEADERS.length).createFilter();
  }
}

function _salesBuildReadOnlyTable(sheet, headers, color) {
  sheet.clear();
  _salesEnsureSize(sheet, 1000, headers.length);
  sheet.getRange(1, 1, 1, headers.length).setValues([headers])
    .setFontWeight('bold').setBackground(color).setWrap(true);
  sheet.setFrozenRows(1);
  sheet.setColumnWidths(1, headers.length, 150);
}

function _salesWriteConfig(salesFile, sale) {
  const sheet = salesFile.getSheetByName(SALES_TABS.CONFIG);
  sheet.clear();
  const rows = [
    ['KEY', 'VALUE'],
    ['sale_id', sale.sale_id],
    ['sale_name', sale.sale_name],
    ['email', sale.email],
    ['manager_id', sale.manager_id],
  ];
  sheet.getRange(1, 1, rows.length, 2).setValues(rows);
}

function _salesApplyTrackingValidations(salesFile) {
  const tracking = salesFile.getSheetByName(SALES_TABS.TRACKING);
  const catalog = salesFile.getSheetByName(SALES_TABS.CATALOG);
  const catalogHeaders = _salesHeaders(catalog);
  const trackingHeaders = _salesHeaders(tracking);
  const categorical = [
    'NGUỒN', 'NHÓM SP', 'TÌNH TRẠNG', 'TRẠNG THÁI',
    'LÝ DO CHƯA CÓ SĐT', 'LOẠI TIN NHẮN', 'CHATPAGE',
  ];
  categorical.forEach(function (field) {
    const trackingCol = trackingHeaders.indexOf(field) + 1;
    const catalogCol = catalogHeaders.indexOf(field) + 1;
    if (!trackingCol || !catalogCol) return;
    const rule = SpreadsheetApp.newDataValidation()
      .requireValueInRange(
        catalog.getRange(2, catalogCol, Math.max(catalog.getMaxRows() - 1, 1), 1),
        true
      ).setAllowInvalid(false).build();
    tracking.getRange(2, trackingCol, tracking.getMaxRows() - 1, 1)
      .setDataValidation(rule).setBackground('#fff2cc');
  });

  SALES_FORM_FIELDS.forEach(function (field, index) {
    const catalogCol = catalogHeaders.indexOf(field) + 1;
    if (!catalogCol) return;
    const rule = SpreadsheetApp.newDataValidation()
      .requireValueInRange(
        catalog.getRange(2, catalogCol, Math.max(catalog.getMaxRows() - 1, 1), 1),
        true
      ).setAllowInvalid(false).build();
    salesFile.getSheetByName(SALES_TABS.FORM)
      .getRange(SALES_FORM_START_ROW + index, 2).setDataValidation(rule);
  });
}

function _salesProtectFile(salesFile) {
  const tracking = salesFile.getSheetByName(SALES_TABS.TRACKING);
  const headers = _salesHeaders(tracking);
  const unprotected = [];
  SALES_EDITABLE_FIELDS.forEach(function (field) {
    const col = headers.indexOf(field) + 1;
    if (col) {
      const range = tracking.getRange(2, col, tracking.getMaxRows() - 1, 1);
      range.setBackground('#fff2cc');
      unprotected.push(range);
    }
  });
  const closeCol = headers.indexOf(SALES_META.CLOSE_ACTION) + 1;
  if (closeCol) {
    unprotected.push(tracking.getRange(2, closeCol, tracking.getMaxRows() - 1, 1));
  }
  SALES_ORIGIN_FIELDS.forEach(function (field) {
    const col = headers.indexOf(field) + 1;
    if (col) tracking.getRange(2, col, tracking.getMaxRows() - 1, 1).setBackground('#eeeeee');
  });
  const trackingProtection = tracking.protect()
    .setDescription('PXV cấu trúc; chỉ ô vàng và Đóng theo dõi được sửa');
  trackingProtection.setUnprotectedRanges(unprotected);
  trackingProtection.removeEditors(trackingProtection.getEditors());
  if (trackingProtection.canDomainEdit()) trackingProtection.setDomainEdit(false);

  [
    SALES_META.LEAD_ID, SALES_META.REVISION, SALES_META.SYNCED_REVISION,
    SALES_META.BATCH_ID, SALES_META.CREATED_AT, SALES_META.UPDATED_AT,
    SALES_META.SUBMITTED_AT, SALES_META.IMPORTED_AT,
    SALES_META.CENTRAL_CHECKSUM, SALES_META.SOURCE_SALE_ID,
  ].forEach(function (field) {
    const col = headers.indexOf(field) + 1;
    if (!col) return;
    tracking.getRange(1, col, tracking.getMaxRows(), 1).setBackground('#eeeeee');
    tracking.hideColumns(col);
  });

  const form = salesFile.getSheetByName(SALES_TABS.FORM);
  const formProtection = form.protect().setDescription('PXV form; chỉ ô nhập và nút được sửa');
  formProtection.setUnprotectedRanges([
    form.getRange(SALES_FORM_START_ROW, 2, SALES_FORM_FIELDS.length, 1),
    form.getRange(SALES_FORM_SAVE_CELL),
    form.getRange(SALES_FORM_SUBMIT_CELL),
  ]);
  formProtection.removeEditors(formProtection.getEditors());
  if (formProtection.canDomainEdit()) formProtection.setDomainEdit(false);

  [SALES_TABS.TODAY, SALES_TABS.HISTORY, SALES_TABS.CATALOG, SALES_TABS.CONFIG]
    .forEach(function (name) {
      const sheet = salesFile.getSheetByName(name);
      const protection = sheet.protect().setDescription('PXV chỉ đọc: ' + name);
      protection.removeEditors(protection.getEditors());
      if (protection.canDomainEdit()) protection.setDomainEdit(false);
    });
}

function _salesSyncCatalogToFile(manager, salesFile) {
  _migrateSalesCatalogIfNeeded(manager);
  const source = manager.getSheetByName('DANH_MỤC');
  const target = salesFile.getSheetByName(SALES_TABS.CATALOG);
  const values = source.getDataRange().getDisplayValues();
  target.clearContents();
  _salesEnsureSize(target, values.length, values[0].length);
  target.getRange(1, 1, values.length, values[0].length).setValues(values);
  target.getRange(1, 1, 1, values[0].length)
    .setFontWeight('bold').setBackground('#e8eaed');
}

function dongBoDanhMucSales() {
  const manager = SpreadsheetApp.getActive();
  const registry = manager.getSheetByName(CONFIG.SHEET_SALES_REGISTRY);
  if (!registry) throw new Error('Chạy dungHeThongSales() trước');
  let ok = 0;
  let failed = 0;
  _salesRegistryRecords(registry).forEach(function (item) {
    if (!_salesIsActive(item.record.active) || !item.record.file_id) return;
    try {
      const salesFile = SpreadsheetApp.openById(item.record.file_id);
      _salesSyncCatalogToFile(manager, salesFile);
      _salesApplyTrackingValidations(salesFile);
      ok++;
    } catch (err) {
      failed++;
      item.record['lỗi gần nhất'] = err.message;
      _salesWriteRegistryRecord(registry, item.row, item.record);
    }
  });
  SpreadsheetApp.getUi().alert('Đồng bộ danh mục: ' + ok + ' file đạt, ' + failed + ' lỗi.');
}

/** Trigger 5 phút: đọc mọi file active, ingest độc lập từng dòng. */
function napLeadTuSales() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) {
    Logger.log('Bỏ qua napLeadTuSales: lần trước vẫn đang chạy.');
    return;
  }
  try {
    const manager = _salesManagerSpreadsheet();
    _dungSalesAdmin(manager);
    const registry = manager.getSheetByName(CONFIG.SHEET_SALES_REGISTRY);
    const context = _salesCentralContext(manager);

    _salesRegistryRecords(registry).forEach(function (item) {
      if (!_salesIsActive(item.record.active) || !item.record.file_id) return;
      try {
        const count = _salesIngestFile(manager, item.record, context);
        item.record['lần đồng bộ cuối'] = _salesNowIso();
        item.record['lỗi gần nhất'] = count + ' revision xử lý';
      } catch (err) {
        item.record['lỗi gần nhất'] = err.message;
        _salesAppendError(manager, {
          sale_id: item.record.sale_id,
          file_id: item.record.file_id,
        }, {
          code: 'FILE_INGEST_FAILED',
          field: '',
          message: err.message,
        });
      }
      _salesWriteRegistryRecord(registry, item.row, item.record);
    });
  } finally {
    lock.releaseLock();
  }
}

/** Menu quản lý dùng cùng logic nhưng có thông báo kết quả. */
function napLeadTuSalesNgay() {
  napLeadTuSales();
  SpreadsheetApp.getUi().alert('Đã quét xong các file sale. Xem SALES_INGEST_LOG và SALES_LỖI.');
}

function _salesCentralContext(manager) {
  const lead = manager.getSheetByName(CONFIG.SHEET_LEAD);
  _salesEnsureCentralLeadHeaders(manager);
  const headers = _salesHeaders(lead);
  const rows = lead.getLastRow() < 2 ? [] :
    lead.getRange(2, 1, lead.getLastRow() - 1, headers.length).getDisplayValues();
  const index = {};
  rows.forEach(function (row, offset) {
    const record = {};
    headers.forEach(function (header, col) { record[header] = row[col]; });
    const leadId = String(record[SALES_META.LEAD_ID] || '').trim();
    if (leadId) index[leadId] = { row: offset + 2, record: record };
  });
  return {
    lead: lead,
    headers: headers,
    rows: rows,
    index: index,
    catalog: _salesReadManagerCatalog(manager),
    nextRow: lead.getLastRow() + 1,
  };
}

function _salesIngestFile(manager, sale, context) {
  const salesFile = SpreadsheetApp.openById(sale.file_id);
  const tracking = salesFile.getSheetByName(SALES_TABS.TRACKING);
  if (!tracking) throw new Error('File sale thiếu tab ' + SALES_TABS.TRACKING);
  const headers = _salesHeaders(tracking);
  const records = _salesReadAllRecords(tracking, headers);
  let processed = 0;

  records.forEach(function (item) {
    const incoming = item.record;
    if (incoming[SALES_META.STATUS] !== SALES_STATUS.READY) return;
    incoming[LEAD_COLS.TU_VAN] = sale['tên sale'];
    incoming[SALES_META.SOURCE_SALE_ID] = sale.sale_id;
    _salesApplySourceAlias(manager, incoming);

    const validation = pxvValidateSalesLead(incoming, context.catalog);
    if (!validation.ok) {
      _salesRejectRow(manager, salesFile, tracking, item, headers, sale, validation.errors);
      processed++;
      return;
    }
    Object.keys(validation.normalized).forEach(function (field) {
      incoming[field] = validation.normalized[field];
    });

    const duplicate = _salesCentralDuplicate(context, incoming);
    const duplicateError = pxvSalesDuplicateReasonError(
      Boolean(duplicate), incoming[SALES_META.DUPLICATE_REASON]
    );
    if (duplicateError) {
      duplicateError.message += ' (LEAD dòng ' + duplicate.row + ')';
      _salesRejectRow(
        manager, salesFile, tracking, item, headers, sale, [duplicateError]
      );
      processed++;
      return;
    }

    const leadId = String(incoming[SALES_META.LEAD_ID]);
    const existing = context.index[leadId] || null;
    const before = existing ? existing.record : {};
    const currentChecksum = existing
      ? pxvSalesChecksum(before, LEAD_HEADERS)
      : '';
    const action = pxvResolveSalesRevision(
      Boolean(existing),
      existing ? before[SALES_META.REVISION] : 0,
      incoming[SALES_META.REVISION],
      incoming[SALES_META.CENTRAL_CHECKSUM],
      currentChecksum
    );

    if (action === 'CONFLICT') {
      _salesConflictRow(
        manager, salesFile, tracking, item, headers, sale,
        'LEAD trung tâm đã được quản lý sửa sau revision trước'
      );
      processed++;
      return;
    }
    if (action === 'IGNORE') {
      _salesAckIgnored(salesFile, tracking, item, headers, incoming, before, currentChecksum);
      _salesAppendLog(manager, sale, item.row, existing.row, 'IGNORE', [], before, before, {
        result: 'IGNORED_IDEMPOTENT',
        error: '',
        duplicateReason: incoming[SALES_META.DUPLICATE_REASON] || '',
      });
      _salesResolveOpenErrors(manager, incoming[SALES_META.LEAD_ID]);
      processed++;
      return;
    }

    const after = {};
    context.headers.forEach(function (header) {
      after[header] = before[header] == null ? '' : before[header];
    });
    LEAD_HEADERS.forEach(function (header) {
      after[header] = incoming[header] == null ? '' : incoming[header];
    });
    after[SALES_META.LEAD_ID] = leadId;
    after[SALES_META.REVISION] = Number(incoming[SALES_META.REVISION] || 0);
    after[SALES_META.BATCH_ID] = incoming[SALES_META.BATCH_ID] || '';
    after[SALES_META.SUBMITTED_AT] =
      incoming[SALES_META.SUBMITTED_AT] || incoming[SALES_META.UPDATED_AT] || _salesNowIso();
    after[SALES_META.SOURCE_SALE_ID] = sale.sale_id;
    after[SALES_META.DUPLICATE_REASON] =
      incoming[SALES_META.DUPLICATE_REASON] || '';

    const targetRow = existing ? existing.row : context.nextRow++;
    _salesRawWriteCentral(manager.getId(), context.lead, targetRow, context.headers, after);
    const checksum = pxvSalesChecksum(after, LEAD_HEADERS);
    const changed = pxvSalesChangedFields(before, after, LEAD_HEADERS);
    const importedAt = _salesNowIso();

    incoming[SALES_META.STATUS] = SALES_STATUS.IMPORTED;
    incoming[SALES_META.SYNCED_REVISION] = incoming[SALES_META.REVISION];
    incoming[SALES_META.IMPORTED_AT] = importedAt;
    incoming[SALES_META.CENTRAL_CHECKSUM] = checksum;
    incoming[SALES_META.ERROR] = '';
    _salesWriteFields(tracking, item.row, headers, incoming, SALES_TRACKING_HEADERS);
    _salesAppendSalesHistory(salesFile, incoming, action, changed, 'IMPORTED');
    _salesAppendLog(manager, sale, item.row, targetRow, action, changed, before, after, {
      result: 'IMPORTED',
      error: '',
      duplicateReason: incoming[SALES_META.DUPLICATE_REASON] || '',
    });
    _salesResolveOpenErrors(manager, incoming[SALES_META.LEAD_ID]);

    context.index[leadId] = { row: targetRow, record: after };
    if (existing) {
      context.rows[existing.row - 2] = _salesRecordToRow(context.headers, after);
    } else {
      context.rows.push(_salesRecordToRow(context.headers, after));
    }
    _salesRefreshToday(salesFile);
    processed++;
  });
  return processed;
}

function _salesRawWriteCentral(spreadsheetId, lead, row, headers, record) {
  const values = _salesRecordToRow(headers, record);
  const range = "'" + lead.getName().replace(/'/g, "''") + "'!A" + row +
    ':' + _chuCot(headers.length) + row;
  if (typeof Sheets !== 'undefined' && Sheets.Spreadsheets && Sheets.Spreadsheets.Values) {
    Sheets.Spreadsheets.Values.update(
      { values: [values] },
      spreadsheetId,
      range,
      { valueInputOption: 'RAW' }
    );
    return;
  }

  // Fallback có chủ đích để file không chết nếu người cài quên bật Sheets API.
  // Định dạng TEXT trước rồi mới setValues để giữ số 0 và ngày ISO.
  const target = lead.getRange(row, 1, 1, headers.length);
  target.setNumberFormat('@');
  target.setValues([values]);
  Logger.log('⚠️ Chưa bật Advanced Sheets service; đã dùng fallback TEXT + setValues.');
}

function _salesRejectRow(manager, salesFile, tracking, item, headers, sale, errors) {
  item.record[SALES_META.STATUS] = SALES_STATUS.ERROR;
  item.record[SALES_META.ERROR] = errors.map(function (error) {
    return error.field + ': ' + error.message;
  }).join(' | ');
  _salesWriteFields(tracking, item.row, headers, item.record, [
    SALES_META.STATUS, SALES_META.ERROR,
  ]);
  errors.forEach(function (error) {
    _salesAppendError(manager, {
      lead_id: item.record[SALES_META.LEAD_ID],
      revision: item.record[SALES_META.REVISION],
      batch_id: item.record[SALES_META.BATCH_ID],
      sale_id: sale.sale_id,
      file_id: sale.file_id,
      source_row: item.row,
    }, error);
  });
  _salesAppendSalesHistory(salesFile, item.record, 'REJECT', [], 'ERROR');
  _salesRefreshToday(salesFile);
}

function _salesConflictRow(manager, salesFile, tracking, item, headers, sale, message) {
  item.record[SALES_META.STATUS] = SALES_STATUS.CONFLICT;
  item.record[SALES_META.ERROR] = message;
  _salesWriteFields(tracking, item.row, headers, item.record, [
    SALES_META.STATUS, SALES_META.ERROR,
  ]);
  _salesAppendError(manager, {
    lead_id: item.record[SALES_META.LEAD_ID],
    revision: item.record[SALES_META.REVISION],
    batch_id: item.record[SALES_META.BATCH_ID],
    sale_id: sale.sale_id,
    file_id: sale.file_id,
    source_row: item.row,
  }, { code: 'CONFLICT', field: '', message: message });
  _salesAppendSalesHistory(salesFile, item.record, 'CONFLICT', [], 'CONFLICT');
  _salesRefreshToday(salesFile);
}

function _salesAckIgnored(salesFile, tracking, item, headers, incoming, central, checksum) {
  incoming[SALES_META.STATUS] = SALES_STATUS.IMPORTED;
  incoming[SALES_META.REVISION] = Number(central[SALES_META.REVISION] || 0);
  incoming[SALES_META.SYNCED_REVISION] = incoming[SALES_META.REVISION];
  incoming[SALES_META.CENTRAL_CHECKSUM] = checksum;
  incoming[SALES_META.ERROR] = '';
  _salesWriteFields(tracking, item.row, headers, incoming, [
    SALES_META.STATUS, SALES_META.REVISION, SALES_META.SYNCED_REVISION,
    SALES_META.CENTRAL_CHECKSUM, SALES_META.ERROR,
  ]);
  _salesAppendSalesHistory(salesFile, incoming, 'IGNORE', [], 'IMPORTED');
  _salesRefreshToday(salesFile);
}

function _salesCentralDuplicate(context, incoming) {
  const phone = pxvSalesNormalizePhone(incoming[LEAD_COLS.SDT]);
  if (!phone) return null;
  const date = String(incoming[LEAD_COLS.NGAY] || '');
  for (let i = 0; i < context.rows.length; i++) {
    const row = context.rows[i];
    const record = {};
    context.headers.forEach(function (header, col) { record[header] = row[col]; });
    if (String(record[SALES_META.LEAD_ID] || '') ===
        String(incoming[SALES_META.LEAD_ID] || '')) continue;
    if (pxvSalesNormalizePhone(record[LEAD_COLS.SDT]) === phone &&
        _salesDisplayDateToIso(record[LEAD_COLS.NGAY]) === date) {
      return { row: i + 2, lead_id: record[SALES_META.LEAD_ID] || '' };
    }
  }
  return null;
}

function _salesReadManagerCatalog(manager) {
  const sheet = manager.getSheetByName('DANH_MỤC');
  const values = sheet.getDataRange().getDisplayValues();
  const headers = values[0] || [];
  const catalog = {};
  headers.forEach(function (header, col) {
    catalog[header] = values.slice(1).map(function (row) {
      return String(row[col] || '').trim();
    }).filter(String);
  });
  return catalog;
}

function _salesApplySourceAlias(manager, record) {
  const source = String(record[LEAD_COLS.NGUON] || '').trim();
  if (!source) return record;
  const cache = CacheService.getScriptCache();
  const key = 'sales_alias_' + manager.getId();
  let aliases;
  const cached = cache.get(key);
  if (cached) {
    aliases = JSON.parse(cached);
  } else {
    aliases = {};
    const sheet = manager.getSheetByName(CONFIG.SHEET_ALIAS);
    if (sheet && sheet.getLastRow() > 1) {
      sheet.getRange(2, 1, sheet.getLastRow() - 1, 2).getDisplayValues()
        .forEach(function (row) {
          const wrong = pxvSalesNormalizeText(row[0]);
          const right = String(row[1] || '').trim();
          if (wrong && right) aliases[wrong] = right;
        });
    }
    cache.put(key, JSON.stringify(aliases), 600);
  }
  const corrected = aliases[pxvSalesNormalizeText(source)];
  if (corrected) record[LEAD_COLS.NGUON] = corrected;
  return record;
}

function _salesAppendLog(manager, sale, sourceRow, targetRow, action, changed, before, after, result) {
  const sheet = manager.getSheetByName(CONFIG.SHEET_SALES_LOG);
  const afterChecksum = pxvSalesChecksum(after, LEAD_HEADERS);
  const row = [
    _salesNowIso(),
    after[SALES_META.LEAD_ID] || before[SALES_META.LEAD_ID] || '',
    after[SALES_META.REVISION] || before[SALES_META.REVISION] || '',
    after[SALES_META.BATCH_ID] || '',
    sale.sale_id || '',
    sale.file_id || '',
    sourceRow || '',
    targetRow || '',
    action,
    changed.join(', '),
    pxvSalesStableJson(before, LEAD_HEADERS),
    pxvSalesStableJson(after, LEAD_HEADERS),
    before && Object.keys(before).length ? pxvSalesChecksum(before, LEAD_HEADERS) : '',
    afterChecksum,
    result.result,
    result.error || '',
    result.duplicateReason || after[SALES_META.DUPLICATE_REASON] || '',
  ];
  sheet.appendRow(row);
}

function _salesAppendError(manager, meta, error) {
  const sheet = manager.getSheetByName(CONFIG.SHEET_SALES_ERRORS);
  if (!sheet) return;
  sheet.appendRow([
    _salesNowIso(),
    meta.lead_id || '',
    meta.revision || '',
    meta.batch_id || '',
    meta.sale_id || '',
    meta.file_id || '',
    meta.source_row || '',
    error.code || 'UNKNOWN',
    error.field || '',
    error.message || '',
    'OPEN',
    '',
  ]);
}

function _salesResolveOpenErrors(manager, leadId) {
  if (!leadId) return;
  const sheet = manager.getSheetByName(CONFIG.SHEET_SALES_ERRORS);
  if (!sheet || sheet.getLastRow() < 2) return;
  const headers = _salesHeaders(sheet);
  const idCol = headers.indexOf('lead_id');
  const statusCol = headers.indexOf('trạng thái');
  const resolvedCol = headers.indexOf('resolved_at');
  if (idCol < 0 || statusCol < 0 || resolvedCol < 0) return;
  const values = sheet.getRange(2, 1, sheet.getLastRow() - 1, headers.length)
    .getDisplayValues();
  values.forEach(function (row, index) {
    if (String(row[idCol]) !== String(leadId) || row[statusCol] !== 'OPEN') return;
    sheet.getRange(index + 2, statusCol + 1).setValue('RESOLVED');
    sheet.getRange(index + 2, resolvedCol + 1).setValue(_salesNowIso());
  });
}

function _salesAppendSalesHistory(salesFile, record, action, changed, result) {
  const sheet = salesFile.getSheetByName(SALES_TABS.HISTORY);
  sheet.appendRow([
    _salesNowIso(),
    record[SALES_META.LEAD_ID] || '',
    record[SALES_META.REVISION] || '',
    record[SALES_META.BATCH_ID] || '',
    action,
    changed.join(', '),
    result,
  ]);
}

function _salesRegistryRecords(registry) {
  if (!registry || registry.getLastRow() < 2) return [];
  const raw = registry.getRange(
    2, 1, registry.getLastRow() - 1, SALES_REGISTRY_HEADERS.length
  ).getValues();
  return raw.map(function (row, index) {
    const record = {};
    SALES_REGISTRY_HEADERS.forEach(function (header, col) {
      record[header] = row[col];
    });
    return { row: index + 2, record: record };
  }).filter(function (item) {
    return !pxvSalesBlank(item.record.sale_id) || !pxvSalesBlank(item.record['tên sale']);
  });
}

function _salesWriteRegistryRecord(registry, row, record) {
  registry.getRange(row, 1, 1, SALES_REGISTRY_HEADERS.length).setValues([
    SALES_REGISTRY_HEADERS.map(function (header) {
      return record[header] === null || record[header] === undefined ? '' : record[header];
    }),
  ]);
}

function _salesIsActive(value) {
  return value === true || ['TRUE', '1', 'CÓ', 'YES'].indexOf(
    pxvSalesNormalizeText(value)
  ) >= 0;
}

function _salesSlug(value) {
  return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[đĐ]/g, 'd').toLowerCase()
    .replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
}

function _salesManagerSpreadsheet() {
  const id = PropertiesService.getScriptProperties().getProperty('MANAGER_ID');
  return id ? SpreadsheetApp.openById(id) : SpreadsheetApp.getActive();
}

function _salesFolder() {
  let id;
  try {
    id = _id('SALES_FOLDER_ID');
  } catch (err) {
    const folder = _taoThuMucCon(_taoThuMuc('PXV'), 'Sales_Entry');
    id = folder.getId();
    PropertiesService.getScriptProperties().setProperty('SALES_FOLDER_ID', id);
  }
  return DriveApp.getFolderById(id);
}

function _salesMoveToFolder(fileId, folder) {
  const file = DriveApp.getFileById(fileId);
  folder.addFile(file);
  try {
    DriveApp.getRootFolder().removeFile(file);
  } catch (err) {
    Logger.log('Không xóa được file sale khỏi My Drive root: ' + err.message);
  }
}

function _ensureSalesOnEditTrigger(fileId) {
  const exists = ScriptApp.getProjectTriggers().some(function (trigger) {
    return trigger.getHandlerFunction() === 'onSaleEdit' &&
      trigger.getTriggerSourceId &&
      trigger.getTriggerSourceId() === fileId;
  });
  if (!exists) {
    ScriptApp.newTrigger('onSaleEdit').forSpreadsheet(fileId).onEdit().create();
  }
}

function taoLaiTriggerSales() {
  const manager = SpreadsheetApp.getActive();
  const registry = manager.getSheetByName(CONFIG.SHEET_SALES_REGISTRY);
  if (!registry) throw new Error('Chạy dungHeThongSales() trước');
  let count = 0;
  _salesRegistryRecords(registry).forEach(function (item) {
    if (!_salesIsActive(item.record.active) || !item.record.file_id) return;
    _ensureSalesOnEditTrigger(item.record.file_id);
    count++;
  });
  SpreadsheetApp.getUi().alert('Đã bảo đảm trigger onEdit cho ' + count + ' file sale.');
}

function moLaiLeadSale() {
  const ui = SpreadsheetApp.getUi();
  const filePrompt = ui.prompt('Mở lại lead', 'Nhập file ID của sale:', ui.ButtonSet.OK_CANCEL);
  if (filePrompt.getSelectedButton() !== ui.Button.OK) return;
  const idPrompt = ui.prompt('Mở lại lead', 'Nhập LEAD_ID:', ui.ButtonSet.OK_CANCEL);
  if (idPrompt.getSelectedButton() !== ui.Button.OK) return;
  const salesFile = SpreadsheetApp.openById(filePrompt.getResponseText().trim());
  const tracking = salesFile.getSheetByName(SALES_TABS.TRACKING);
  const headers = _salesHeaders(tracking);
  const found = _salesReadAllRecords(tracking, headers).filter(function (item) {
    return item.record[SALES_META.LEAD_ID] === idPrompt.getResponseText().trim();
  })[0];
  if (!found) throw new Error('Không tìm thấy LEAD_ID trong file sale');
  found.record[SALES_META.STATUS] = SALES_STATUS.IMPORTED;
  found.record[SALES_META.ERROR] = '';
  found.record[SALES_META.UPDATED_AT] = _salesNowIso();
  _salesWriteFields(tracking, found.row, headers, found.record, [
    SALES_META.STATUS, SALES_META.ERROR, SALES_META.UPDATED_AT,
  ]);
  tracking.showRows(found.row);
  _salesRefreshToday(salesFile);
  ui.alert('Đã mở lại lead cho sale tiếp tục follow-up.');
}

function giaiQuyetConflictGiuLead() {
  _salesResolveConflict(false);
}

function giaiQuyetConflictDungBanSale() {
  _salesResolveConflict(true);
}

function _salesResolveConflict(useSalesVersion) {
  const ui = SpreadsheetApp.getUi();
  const filePrompt = ui.prompt(
    'Giải quyết conflict', 'Nhập file ID của sale:', ui.ButtonSet.OK_CANCEL
  );
  if (filePrompt.getSelectedButton() !== ui.Button.OK) return;
  const idPrompt = ui.prompt(
    'Giải quyết conflict', 'Nhập LEAD_ID:', ui.ButtonSet.OK_CANCEL
  );
  if (idPrompt.getSelectedButton() !== ui.Button.OK) return;

  const manager = SpreadsheetApp.getActive();
  const salesFile = SpreadsheetApp.openById(filePrompt.getResponseText().trim());
  const tracking = salesFile.getSheetByName(SALES_TABS.TRACKING);
  const trackingHeaders = _salesHeaders(tracking);
  const found = _salesReadAllRecords(tracking, trackingHeaders).filter(function (item) {
    return item.record[SALES_META.LEAD_ID] === idPrompt.getResponseText().trim();
  })[0];
  if (!found) throw new Error('Không tìm thấy LEAD_ID trong file sale');
  if (found.record[SALES_META.STATUS] !== SALES_STATUS.CONFLICT) {
    throw new Error('Lead này không ở trạng thái CONFLICT');
  }

  const context = _salesCentralContext(manager);
  const central = context.index[found.record[SALES_META.LEAD_ID]];
  if (!central) throw new Error('Không tìm thấy LEAD_ID trong LEAD trung tâm');
  const changed = pxvSalesChangedFields(central.record, found.record, LEAD_HEADERS);
  const choice = ui.alert(
    useSalesVersion ? 'Dùng bản của sale?' : 'Giữ bản trong LEAD?',
    'Các trường khác nhau: ' + (changed.join(', ') || '(không còn khác)') +
      '\n\nThao tác này được ghi vào LỊCH_SỬ.',
    ui.ButtonSet.YES_NO
  );
  if (choice !== ui.Button.YES) return;

  const currentChecksum = pxvSalesChecksum(central.record, LEAD_HEADERS);
  if (useSalesVersion) {
    found.record[SALES_META.CENTRAL_CHECKSUM] = currentChecksum;
    found.record[SALES_META.REVISION] = Math.max(
      Number(found.record[SALES_META.REVISION] || 0),
      Number(central.record[SALES_META.REVISION] || 0) + 1
    );
    found.record[SALES_META.STATUS] = SALES_STATUS.READY;
    found.record[SALES_META.ERROR] = '';
    found.record[SALES_META.SUBMITTED_AT] = _salesNowIso();
    _salesWriteFields(tracking, found.row, trackingHeaders, found.record, [
      SALES_META.CENTRAL_CHECKSUM, SALES_META.REVISION,
      SALES_META.STATUS, SALES_META.ERROR, SALES_META.SUBMITTED_AT,
    ]);
    _salesAppendSalesHistory(
      salesFile, found.record, 'RESOLVE_USE_SALES', changed, 'READY'
    );
    napLeadTuSales();
  } else {
    LEAD_HEADERS.forEach(function (field) {
      found.record[field] = central.record[field] == null ? '' : central.record[field];
    });
    found.record[SALES_META.REVISION] = Number(central.record[SALES_META.REVISION] || 0);
    found.record[SALES_META.SYNCED_REVISION] = found.record[SALES_META.REVISION];
    found.record[SALES_META.CENTRAL_CHECKSUM] = currentChecksum;
    found.record[SALES_META.STATUS] = SALES_STATUS.IMPORTED;
    found.record[SALES_META.ERROR] = '';
    _salesWriteFields(tracking, found.row, trackingHeaders, found.record, SALES_TRACKING_HEADERS);
    _salesAppendSalesHistory(
      salesFile, found.record, 'RESOLVE_KEEP_CENTRAL', changed, 'IMPORTED'
    );
    _salesRefreshToday(salesFile);
    _salesResolveOpenErrors(manager, found.record[SALES_META.LEAD_ID]);
  }
  ui.alert('Đã giải quyết conflict.');
}

function xemTrangThaiSalesEntry() {
  const manager = SpreadsheetApp.getActive();
  const registry = manager.getSheetByName(CONFIG.SHEET_SALES_REGISTRY);
  if (!registry) {
    SpreadsheetApp.getUi().alert('Chưa chạy dungHeThongSales().');
    return;
  }
  const rows = _salesRegistryRecords(registry);
  const active = rows.filter(function (item) { return _salesIsActive(item.record.active); });
  const errors = active.filter(function (item) {
    return item.record['lỗi gần nhất'] &&
      String(item.record['lỗi gần nhất']).indexOf('revision xử lý') < 0;
  });
  SpreadsheetApp.getUi().alert(
    'Sales Entry',
    'Registry: ' + rows.length + '\nActive: ' + active.length +
      '\nFile có lỗi gần nhất: ' + errors.length,
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}
