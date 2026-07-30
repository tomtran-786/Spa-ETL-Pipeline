/**
 * Giao diện file riêng của sale.
 *
 * Code vẫn nằm trong project PXV_NHẬP_LIỆU. Khi tạo file sale, quản lý cài
 * installable onEdit trigger trỏ tới file đó. Trigger chạy bằng quyền quản lý,
 * nên sale không cần thấy Apps Script và không cần quyền vào file LEAD trung tâm.
 */

const SALES_TABS = {
  FORM: 'NHẬP_MỚI',
  TRACKING: 'ĐANG_THEO_DÕI',
  TODAY: 'HÔM_NAY',
  HISTORY: 'LỊCH_SỬ',
  CATALOG: 'DANH_MỤC_CACHE',
  CONFIG: 'CẤU_HÌNH',
};

const SALES_FORM_START_ROW = 4;
const SALES_FORM_SAVE_CELL = 'B22';
const SALES_FORM_SUBMIT_CELL = 'B23';
const SALES_FORM_RESULT_CELL = 'B25';

const SALES_TODAY_HEADERS = [
  SALES_META.STATUS,
  SALES_META.ERROR,
  SALES_META.LEAD_ID,
  'TÊN KHÁCH HÀNG',
  'SỐ ĐT',
  'TRẠNG THÁI',
  'NGÀY HẸN',
  'GIỜ HẸN',
  SALES_META.UPDATED_AT,
];

const SALES_HISTORY_HEADERS = [
  'thời điểm',
  SALES_META.LEAD_ID,
  SALES_META.REVISION,
  SALES_META.BATCH_ID,
  'hành động',
  'trường thay đổi',
  'kết quả',
];

/** Installable trigger cho tất cả file sale gọi vào đây. */
function onSaleEdit(e) {
  if (!e || !e.range) return;
  const ss = e.source || e.range.getSheet().getParent();
  if (!ss.getSheetByName(SALES_TABS.CONFIG)) return;

  const lock = LockService.getScriptLock();
  try {
    lock.waitLock(30000);
    const sheet = e.range.getSheet();
    if (sheet.getName() === SALES_TABS.FORM) {
      _salesHandleFormAction(ss, e);
    } else if (sheet.getName() === SALES_TABS.TRACKING) {
      _salesHandleTrackingEdit(ss, e);
    }
  } catch (err) {
    _salesWriteFormResult(ss, '❌ ' + err.message, '#f4cccc');
    ss.toast('Lỗi: ' + err.message, 'PXV Sales', 10);
  } finally {
    if (lock.hasLock()) lock.releaseLock();
  }
}

function _salesHandleFormAction(ss, e) {
  const a1 = e.range.getA1Notation();
  if (a1 !== SALES_FORM_SAVE_CELL && a1 !== SALES_FORM_SUBMIT_CELL) return;
  if (e.range.getValue() !== true) return;

  try {
    if (a1 === SALES_FORM_SAVE_CELL) {
      _salesSaveDraft(ss);
    } else {
      _salesSubmitDrafts(ss);
    }
  } finally {
    e.range.setValue(false);
  }
}

function _salesHandleTrackingEdit(ss, e) {
  if (e.range.getRow() < 2) return;
  const sheet = e.range.getSheet();
  const headers = _salesHeaders(sheet);
  const firstCol = e.range.getColumn();
  const lastCol = firstCol + e.range.getNumColumns() - 1;
  const touched = headers.slice(firstCol - 1, lastCol);

  if (touched.indexOf(SALES_META.CLOSE_ACTION) >= 0) {
    for (let row = e.range.getRow(); row <= e.range.getLastRow(); row++) {
      if (sheet.getRange(row, headers.indexOf(SALES_META.CLOSE_ACTION) + 1).getValue() === true) {
        _salesCloseTrackingRow(ss, sheet, row, headers);
      }
    }
    _salesRefreshToday(ss);
    return;
  }

  const changesBusinessField = touched.some(function (field) {
    return SALES_EDITABLE_FIELDS.indexOf(field) >= 0;
  });
  if (!changesBusinessField) return;

  for (let row = e.range.getRow(); row <= e.range.getLastRow(); row++) {
    const record = _salesReadRow(sheet, row, headers);
    if (record[SALES_META.STATUS] === SALES_STATUS.CLOSED) {
      if (e.range.getNumRows() === 1 && e.range.getNumColumns() === 1 &&
          e.oldValue !== undefined) {
        e.range.setValue(e.oldValue);
      }
      record[SALES_META.ERROR] = 'Lead đã đóng; quản lý phải mở lại trước khi sửa';
      _salesWriteFields(sheet, row, headers, record, [SALES_META.ERROR]);
      continue;
    }
    record[SALES_META.STATUS] = SALES_STATUS.DRAFT;
    record[SALES_META.ERROR] = '';
    record[SALES_META.UPDATED_AT] = _salesNowIso();
    _salesWriteFields(sheet, row, headers, record, [
      SALES_META.STATUS, SALES_META.ERROR, SALES_META.UPDATED_AT,
    ]);
  }
  _salesRefreshToday(ss);
}

function _salesSaveDraft(ss) {
  const config = _salesFileConfig(ss);
  const record = _salesReadForm(ss);
  if (pxvSalesBlank(record[LEAD_COLS.TEN])) {
    throw new Error('Nhập TÊN KHÁCH HÀNG trước khi Lưu tạm.');
  }

  const now = _salesNowIso();
  record[LEAD_COLS.NGAY] = _salesTodayIso();
  record[LEAD_COLS.TU_VAN] = config.sale_name;
  record[SALES_META.LEAD_ID] = Utilities.getUuid();
  record[SALES_META.REVISION] = 0;
  record[SALES_META.SYNCED_REVISION] = 0;
  record[SALES_META.BATCH_ID] = '';
  record[SALES_META.STATUS] = SALES_STATUS.DRAFT;
  record[SALES_META.CREATED_AT] = now;
  record[SALES_META.UPDATED_AT] = now;
  record[SALES_META.SUBMITTED_AT] = '';
  record[SALES_META.IMPORTED_AT] = '';
  record[SALES_META.CENTRAL_CHECKSUM] = '';
  record[SALES_META.ERROR] = '';
  record[SALES_META.SOURCE_SALE_ID] = config.sale_id;
  record[SALES_META.CLOSE_ACTION] = false;

  const sheet = ss.getSheetByName(SALES_TABS.TRACKING);
  _salesAppendRecords(sheet, SALES_TRACKING_HEADERS, [record]);
  _salesClearForm(ss);
  _salesRefreshToday(ss);
  _salesWriteFormResult(
    ss,
    '✅ Đã lưu nháp ' + record[SALES_META.LEAD_ID].slice(0, 8),
    '#d9ead3'
  );
  ss.toast('Đã lưu nháp. Cuối ngày nhớ bấm Nộp.', 'PXV Sales', 6);
}

function _salesSubmitDrafts(ss) {
  const fileConfig = _salesFileConfig(ss);
  const manager = SpreadsheetApp.openById(fileConfig.manager_id);
  const tracking = ss.getSheetByName(SALES_TABS.TRACKING);
  const headers = _salesHeaders(tracking);
  const rows = _salesReadAllRecords(tracking, headers);
  const catalog = _salesReadCatalog(ss);
  const batchId = Utilities.getUuid();
  let ready = 0;
  let failed = 0;

  rows.forEach(function (item) {
    const record = item.record;
    if ([SALES_STATUS.DRAFT, SALES_STATUS.ERROR].indexOf(record[SALES_META.STATUS]) < 0) {
      return;
    }

    _salesApplySourceAlias(manager, record);
    const validation = pxvValidateSalesLead(record, catalog);
    let errors = validation.errors.slice();
    const duplicate = validation.ok
      ? _salesFindCentralDuplicate(ss, validation.normalized)
      : null;
    const duplicateError = pxvSalesDuplicateReasonError(
      Boolean(duplicate), record[SALES_META.DUPLICATE_REASON]
    );
    if (duplicateError) errors.push(duplicateError);

    if (errors.length) {
      record[SALES_META.STATUS] = SALES_STATUS.ERROR;
      record[SALES_META.ERROR] = errors.map(function (error) {
        return error.field + ': ' + error.message;
      }).join(' | ');
      failed++;
    } else {
      Object.keys(validation.normalized).forEach(function (field) {
        record[field] = validation.normalized[field];
      });
      record[SALES_META.REVISION] = Math.max(
        Number(record[SALES_META.REVISION] || 0),
        Number(record[SALES_META.SYNCED_REVISION] || 0)
      ) + 1;
      record[SALES_META.BATCH_ID] = batchId;
      record[SALES_META.SUBMITTED_AT] = _salesNowIso();
      record[SALES_META.STATUS] = SALES_STATUS.READY;
      record[SALES_META.ERROR] = duplicate ? '⚠️ Trùng đã có lý do — chờ nộp' : '';
      ready++;
    }
    record[SALES_META.UPDATED_AT] = _salesNowIso();
    _salesWriteFields(tracking, item.row, headers, record, SALES_TRACKING_HEADERS);
  });

  _salesRefreshToday(ss);
  const message = '✅ ' + ready + ' dòng sẵn sàng nộp; ' + failed + ' dòng cần sửa.';
  _salesWriteFormResult(ss, message, failed ? '#fff2cc' : '#d9ead3');
  ss.toast(message + ' Hệ thống quản lý sẽ nhận trong tối đa 5 phút.', 'PXV Sales', 10);
}

function _salesCloseTrackingRow(ss, sheet, row, headers) {
  const record = _salesReadRow(sheet, row, headers);
  record[SALES_META.CLOSE_ACTION] = false;
  if (record[SALES_META.STATUS] !== SALES_STATUS.IMPORTED) {
    record[SALES_META.ERROR] = 'Chỉ đóng được lead đã đồng bộ và không còn thay đổi nháp';
    _salesWriteFields(sheet, row, headers, record, [
      SALES_META.CLOSE_ACTION, SALES_META.ERROR,
    ]);
    return;
  }
  record[SALES_META.STATUS] = SALES_STATUS.CLOSED;
  record[SALES_META.ERROR] = '';
  record[SALES_META.UPDATED_AT] = _salesNowIso();
  _salesWriteFields(sheet, row, headers, record, [
    SALES_META.CLOSE_ACTION, SALES_META.STATUS,
    SALES_META.ERROR, SALES_META.UPDATED_AT,
  ]);
  sheet.hideRows(row);
  ss.toast('Đã đóng theo dõi. Dữ liệu vẫn còn trong LEAD và LỊCH_SỬ.', 'PXV Sales', 6);
}

function _salesReadForm(ss) {
  const sheet = ss.getSheetByName(SALES_TABS.FORM);
  const record = {};
  SALES_FORM_FIELDS.forEach(function (field, index) {
    const cell = sheet.getRange(SALES_FORM_START_ROW + index, 2);
    if (field === LEAD_COLS.NGAY_HEN || field === LEAD_COLS.GIO_HEN) {
      record[field] = cell.getDisplayValue().trim();
    } else {
      record[field] = cell.getValue();
    }
  });
  return record;
}

function _salesClearForm(ss) {
  const sheet = ss.getSheetByName(SALES_TABS.FORM);
  sheet.getRange(SALES_FORM_START_ROW, 2, SALES_FORM_FIELDS.length, 1).clearContent();
}

function _salesFindCentralDuplicate(ss, record) {
  const phone = pxvSalesNormalizePhone(record[LEAD_COLS.SDT]);
  if (!phone || !record[LEAD_COLS.NGAY]) return null;
  const config = _salesFileConfig(ss);
  const manager = SpreadsheetApp.openById(config.manager_id);
  const lead = manager.getSheetByName(CONFIG.SHEET_LEAD);
  if (!lead || lead.getLastRow() < 2) return null;
  const headers = _salesHeaders(lead);
  const phoneCol = headers.indexOf(LEAD_COLS.SDT);
  const dateCol = headers.indexOf(LEAD_COLS.NGAY);
  const idCol = headers.indexOf(SALES_META.LEAD_ID);
  if (phoneCol < 0 || dateCol < 0) return null;

  const values = lead.getRange(2, 1, lead.getLastRow() - 1, lead.getLastColumn())
    .getDisplayValues();
  for (let i = 0; i < values.length; i++) {
    const sameId = idCol >= 0 &&
      String(values[i][idCol] || '') === String(record[SALES_META.LEAD_ID] || '');
    if (sameId) continue;
    if (pxvSalesNormalizePhone(values[i][phoneCol]) === phone &&
        _salesDisplayDateToIso(values[i][dateCol]) === String(record[LEAD_COLS.NGAY])) {
      return { row: i + 2, lead_id: idCol >= 0 ? values[i][idCol] : '' };
    }
  }
  return null;
}

function _salesRefreshToday(ss) {
  const tracking = ss.getSheetByName(SALES_TABS.TRACKING);
  const todaySheet = ss.getSheetByName(SALES_TABS.TODAY);
  if (!tracking || !todaySheet) return;
  const headers = _salesHeaders(tracking);
  const records = _salesReadAllRecords(tracking, headers);
  const today = _salesTodayIso();
  const activeStatuses = [
    SALES_STATUS.DRAFT, SALES_STATUS.READY, SALES_STATUS.ERROR, SALES_STATUS.CONFLICT,
  ];
  const selected = records.filter(function (item) {
    const created = String(item.record[SALES_META.CREATED_AT] || '');
    const updated = String(item.record[SALES_META.UPDATED_AT] || '');
    return created.indexOf(today) === 0 ||
      updated.indexOf(today) === 0 ||
      activeStatuses.indexOf(item.record[SALES_META.STATUS]) >= 0;
  }).map(function (item) {
    return SALES_TODAY_HEADERS.map(function (field) {
      return item.record[field] == null ? '' : item.record[field];
    });
  });

  const clearRows = Math.max(todaySheet.getLastRow() - 1, 0);
  if (clearRows) todaySheet.getRange(2, 1, clearRows, todaySheet.getLastColumn()).clearContent();
  if (selected.length) {
    _salesEnsureSize(todaySheet, selected.length + 1, SALES_TODAY_HEADERS.length);
    todaySheet.getRange(2, 1, selected.length, SALES_TODAY_HEADERS.length).setValues(selected);
  }
}

function _salesReadCatalog(ss) {
  const sheet = ss.getSheetByName(SALES_TABS.CATALOG);
  const values = sheet.getDataRange().getDisplayValues();
  const headers = values.length ? values[0] : [];
  const catalog = {};
  headers.forEach(function (header, col) {
    catalog[header] = values.slice(1).map(function (row) {
      return String(row[col] || '').trim();
    }).filter(String);
  });
  return catalog;
}

function _salesFileConfig(ss) {
  const sheet = ss.getSheetByName(SALES_TABS.CONFIG);
  if (!sheet || sheet.getLastRow() < 2) throw new Error('File sale thiếu CẤU_HÌNH');
  const rows = sheet.getRange(2, 1, sheet.getLastRow() - 1, 2).getDisplayValues();
  const config = {};
  rows.forEach(function (row) {
    config[String(row[0]).trim()] = String(row[1]).trim();
  });
  ['sale_id', 'sale_name', 'manager_id'].forEach(function (key) {
    if (!config[key]) throw new Error('CẤU_HÌNH thiếu ' + key);
  });
  return config;
}

function _salesHeaders(sheet) {
  return sheet.getRange(1, 1, 1, sheet.getLastColumn()).getDisplayValues()[0]
    .map(function (value) { return String(value).trim(); });
}

function _salesReadRow(sheet, row, headers) {
  const values = sheet.getRange(row, 1, 1, headers.length).getDisplayValues()[0];
  const record = {};
  headers.forEach(function (header, index) {
    record[header] = values[index];
  });
  const closeCol = headers.indexOf(SALES_META.CLOSE_ACTION);
  if (closeCol >= 0) record[SALES_META.CLOSE_ACTION] =
    sheet.getRange(row, closeCol + 1).getValue() === true;
  return record;
}

function _salesReadAllRecords(sheet, headers) {
  if (sheet.getLastRow() < 2) return [];
  const values = sheet.getRange(2, 1, sheet.getLastRow() - 1, headers.length)
    .getDisplayValues();
  const closeCol = headers.indexOf(SALES_META.CLOSE_ACTION);
  const closeValues = closeCol >= 0
    ? sheet.getRange(2, closeCol + 1, sheet.getLastRow() - 1, 1).getValues()
    : [];
  return values.map(function (row, index) {
    const record = {};
    headers.forEach(function (header, col) { record[header] = row[col]; });
    if (closeCol >= 0) record[SALES_META.CLOSE_ACTION] = closeValues[index][0] === true;
    return { row: index + 2, record: record };
  }).filter(function (item) {
    return !pxvSalesBlank(item.record[SALES_META.LEAD_ID]);
  });
}

function _salesRecordToRow(headers, record) {
  return headers.map(function (header) {
    const value = record[header];
    return value === null || value === undefined ? '' : value;
  });
}

function _salesAppendRecords(sheet, headers, records) {
  if (!records.length) return;
  _salesEnsureSize(sheet, sheet.getLastRow() + records.length, headers.length);
  const start = sheet.getLastRow() + 1;
  sheet.getRange(start, 1, records.length, headers.length)
    .setValues(records.map(function (record) {
      return _salesRecordToRow(headers, record);
    }));
  const closeCol = headers.indexOf(SALES_META.CLOSE_ACTION) + 1;
  if (closeCol) {
    const rule = SpreadsheetApp.newDataValidation().requireCheckbox().build();
    sheet.getRange(start, closeCol, records.length, 1).setDataValidation(rule);
  }
}

function _salesWriteFields(sheet, row, headers, record, fields) {
  fields.forEach(function (field) {
    const col = headers.indexOf(field) + 1;
    if (!col) return;
    sheet.getRange(row, col).setValue(
      record[field] === null || record[field] === undefined ? '' : record[field]
    );
  });
}

function _salesEnsureSize(sheet, rows, cols) {
  if (sheet.getMaxRows() < rows) {
    sheet.insertRowsAfter(sheet.getMaxRows(), rows - sheet.getMaxRows());
  }
  if (sheet.getMaxColumns() < cols) {
    sheet.insertColumnsAfter(sheet.getMaxColumns(), cols - sheet.getMaxColumns());
  }
}

function _salesTodayIso() {
  return Utilities.formatDate(new Date(), 'Asia/Ho_Chi_Minh', 'yyyy-MM-dd');
}

function _salesNowIso() {
  return Utilities.formatDate(new Date(), 'Asia/Ho_Chi_Minh', "yyyy-MM-dd'T'HH:mm:ssXXX");
}

function _salesDisplayDateToIso(value) {
  const text = String(value || '').trim();
  if (pxvSalesIsIsoDate(text)) return text;
  const match = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(text);
  if (!match) return '';
  return match[3] + '-' + ('0' + match[2]).slice(-2) + '-' + ('0' + match[1]).slice(-2);
}

function _salesWriteFormResult(ss, message, color) {
  const sheet = ss.getSheetByName(SALES_TABS.FORM);
  if (!sheet) return;
  sheet.getRange(SALES_FORM_RESULT_CELL).setValue(message).setBackground(color || '#ffffff');
}
