/**
 * Logic THUẦN cho luồng nhập lead từ file riêng của sale.
 *
 * File này cố tình không gọi SpreadsheetApp/DriveApp để:
 *   - test được bằng Node trong CI;
 *   - phía file sale và phía quản lý dùng đúng MỘT bộ validation;
 *   - checksum/revision không phụ thuộc vị trí cột trong Google Sheets.
 */

const SALES_STATUS = {
  DRAFT: 'DRAFT',
  READY: 'READY',
  IMPORTED: 'IMPORTED',
  ERROR: 'ERROR',
  CONFLICT: 'CONFLICT',
  CLOSED: 'CLOSED',
};

const SALES_META = {
  LEAD_ID: '_LEAD_ID',
  REVISION: '_REVISION',
  SYNCED_REVISION: '_SYNCED_REVISION',
  BATCH_ID: '_BATCH_ID',
  STATUS: '_STATUS',
  CREATED_AT: '_CREATED_AT',
  UPDATED_AT: '_UPDATED_AT',
  SUBMITTED_AT: '_SUBMITTED_AT',
  IMPORTED_AT: '_IMPORTED_AT',
  CENTRAL_CHECKSUM: '_CENTRAL_CHECKSUM',
  ERROR: '_ERROR',
  SOURCE_SALE_ID: '_SOURCE_SALE_ID',
  DUPLICATE_REASON: 'LÝ DO TRÙNG',
  CLOSE_ACTION: '_ĐÓNG THEO DÕI',
};

const SALES_CENTRAL_META_HEADERS = [
  SALES_META.LEAD_ID,
  SALES_META.REVISION,
  SALES_META.BATCH_ID,
  SALES_META.SUBMITTED_AT,
  SALES_META.SOURCE_SALE_ID,
];

const SALES_REQUIRED_ON_SUBMIT = [
  'TÊN KHÁCH HÀNG',
  'NGUỒN',
  'NHÓM SP',
  'LOẠI TIN NHẮN',
  'CHATPAGE',
];

const SALES_APPOINTMENT_STATUSES = ['ĐẶT HẸN', 'ĐÃ LÀM DV', 'DỜI LỊCH'];

const SALES_ORIGIN_FIELDS = [
  'NGÀY',
  'LOẠI TIN NHẮN',
  'CHATPAGE',
  'NGUỒN',
  'BÀI QC',
  'TƯ VẤN - SALE',
];

const SALES_EDITABLE_FIELDS = [
  'TÊN KHÁCH HÀNG',
  'SỐ ĐT',
  'LÝ DO CHƯA CÓ SĐT',
  'NHÓM SP',
  'QUAN TÂM',
  'TÌNH TRẠNG',
  'TRẠNG THÁI',
  'THÔNG TIN KHÁCH',
  'GIỜ HẸN',
  'NGÀY HẸN',
  'GHI CHÚ',
  SALES_META.DUPLICATE_REASON,
];

const SALES_TRACKING_HEADERS = [
  SALES_META.STATUS,
  SALES_META.ERROR,
  SALES_META.CLOSE_ACTION,
  SALES_META.LEAD_ID,
  SALES_META.REVISION,
  SALES_META.SYNCED_REVISION,
  'TÊN KHÁCH HÀNG',
  'SỐ ĐT',
  'LÝ DO CHƯA CÓ SĐT',
  'NHÓM SP',
  'QUAN TÂM',
  'TÌNH TRẠNG',
  'TRẠNG THÁI',
  'THÔNG TIN KHÁCH',
  'GIỜ HẸN',
  'NGÀY HẸN',
  'GHI CHÚ',
  SALES_META.DUPLICATE_REASON,
  'NGÀY',
  'LOẠI TIN NHẮN',
  'CHATPAGE',
  'NGUỒN',
  'BÀI QC',
  'TƯ VẤN - SALE',
  SALES_META.BATCH_ID,
  SALES_META.CREATED_AT,
  SALES_META.UPDATED_AT,
  SALES_META.SUBMITTED_AT,
  SALES_META.IMPORTED_AT,
  SALES_META.CENTRAL_CHECKSUM,
  SALES_META.SOURCE_SALE_ID,
];

const SALES_FORM_FIELDS = [
  'TÊN KHÁCH HÀNG',
  'SỐ ĐT',
  'LÝ DO CHƯA CÓ SĐT',
  'LOẠI TIN NHẮN',
  'NHÓM SP',
  'CHATPAGE',
  'NGUỒN',
  'BÀI QC',
  'QUAN TÂM',
  'TÌNH TRẠNG',
  'TRẠNG THÁI',
  'THÔNG TIN KHÁCH',
  'GIỜ HẸN',
  'NGÀY HẸN',
  'GHI CHÚ',
  SALES_META.DUPLICATE_REASON,
];

/** Giá trị rỗng theo nghĩa nghiệp vụ, không coi 0/false là rỗng. */
function pxvSalesBlank(value) {
  return value === null || value === undefined || String(value).trim() === '';
}

function pxvSalesNormalizeText(value) {
  if (pxvSalesBlank(value)) return '';
  return String(value).trim().replace(/\s+/g, ' ').toUpperCase();
}

/**
 * Giữ đồng nhất với pxv.clean.clean_phone và _chuanHoaSdt.
 * VN -> 0XXXXXXXXX, quốc tế -> +XXXX, rác/"0" -> ''.
 */
function pxvSalesNormalizePhone(value) {
  if (value === null || value === undefined) return '';
  let digits = String(value).split('.')[0].replace(/\D/g, '');
  if (!digits) return '';
  if (digits.indexOf('00') === 0) digits = digits.slice(2);

  const candidates = [];
  if (digits.indexOf('84') === 0 && digits.length === 11) {
    candidates.push('0' + digits.slice(2));
  }
  if (digits.charAt(0) === '0') candidates.push(digits);
  if (digits.length === 9) candidates.push('0' + digits);

  for (let i = 0; i < candidates.length; i++) {
    const candidate = candidates[i];
    if (/^0[35789]\d{8}$/.test(candidate) || /^02\d{8,9}$/.test(candidate)) {
      return candidate;
    }
  }
  return digits.length >= 10 && digits.length <= 15 ? '+' + digits : '';
}

/** Chỉ nhận ISO đầy đủ cho dữ liệu mới; không suy năm. */
function pxvSalesIsIsoDate(value) {
  const text = String(value || '').trim();
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
  if (!match) return false;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day;
}

function pxvSalesIsTime(value) {
  return /^([01]\d|2[0-3]):[0-5]\d$/.test(String(value || '').trim());
}

function pxvSalesHasAppointment(record) {
  if (!pxvSalesBlank(record['NGÀY HẸN']) || !pxvSalesBlank(record['GIỜ HẸN'])) {
    return true;
  }
  const statuses = [
    pxvSalesNormalizeText(record['TÌNH TRẠNG']),
    pxvSalesNormalizeText(record['TRẠNG THÁI']),
  ];
  return SALES_APPOINTMENT_STATUSES.some(function (value) {
    const wanted = pxvSalesNormalizeText(value);
    return statuses.some(function (status) { return status.indexOf(wanted) >= 0; });
  });
}

function pxvSalesCatalogContains(catalog, field, value) {
  if (pxvSalesBlank(value)) return false;
  const values = catalog && catalog[field] ? catalog[field] : [];
  const wanted = pxvSalesNormalizeText(value);
  return values.some(function (item) {
    return pxvSalesNormalizeText(item) === wanted;
  });
}

function pxvSalesDuplicateReasonError(hasDuplicate, reason) {
  if (!hasDuplicate || !pxvSalesBlank(reason)) return null;
  return {
    code: 'DUPLICATE_REASON_REQUIRED',
    field: SALES_META.DUPLICATE_REASON,
    message: 'SĐT này đã có lead cùng ngày; nhập LÝ DO TRÙNG để tiếp tục',
  };
}

/**
 * Validation authoritative, chạy cả lúc sale Submit và lúc quản lý ingest.
 * Trả về record đã chuẩn hóa để code ghi Sheets không phải chuẩn hóa lần hai.
 */
function pxvValidateSalesLead(record, catalog) {
  const normalized = {};
  Object.keys(record || {}).forEach(function (key) {
    normalized[key] = record[key];
  });
  const errors = [];

  SALES_REQUIRED_ON_SUBMIT.forEach(function (field) {
    if (pxvSalesBlank(normalized[field])) {
      errors.push({ code: 'REQUIRED', field: field, message: 'Bắt buộc nhập ' + field });
    }
  });

  const phoneRaw = normalized['SỐ ĐT'];
  const phone = pxvSalesNormalizePhone(phoneRaw);
  const noPhoneReason = String(normalized['LÝ DO CHƯA CÓ SĐT'] || '').trim();
  const hasRawPhone = !pxvSalesBlank(phoneRaw);

  if (hasRawPhone && !phone) {
    errors.push({
      code: 'PHONE_INVALID',
      field: 'SỐ ĐT',
      message: 'SĐT không hợp lệ; không dùng số 0 hoặc ghi chú trong ô SĐT',
    });
  } else if (phone && noPhoneReason) {
    errors.push({
      code: 'PHONE_REASON_CONFLICT',
      field: 'LÝ DO CHƯA CÓ SĐT',
      message: 'Đã có SĐT thì phải xóa lý do chưa có SĐT',
    });
  } else if (!phone && !noPhoneReason) {
    errors.push({
      code: 'PHONE_OR_REASON_REQUIRED',
      field: 'SỐ ĐT',
      message: 'Phải có SĐT hợp lệ hoặc chọn LÝ DO CHƯA CÓ SĐT',
    });
  }
  if (phone) normalized['SỐ ĐT'] = phone;

  const catalogFields = [
    'NGUỒN', 'NHÓM SP', 'LOẠI TIN NHẮN', 'CHATPAGE',
    'TÌNH TRẠNG', 'TRẠNG THÁI', 'LÝ DO CHƯA CÓ SĐT',
  ];
  catalogFields.forEach(function (field) {
    if (pxvSalesBlank(normalized[field])) return;
    if (!pxvSalesCatalogContains(catalog, field, normalized[field])) {
      errors.push({
        code: 'CATALOG_MISMATCH',
        field: field,
        message: field + ' không nằm trong danh mục quản lý',
      });
    }
  });

  const leadDate = String(normalized['NGÀY'] || '').trim();
  if (!pxvSalesIsIsoDate(leadDate)) {
    errors.push({
      code: 'LEAD_DATE_INVALID',
      field: 'NGÀY',
      message: 'NGÀY phải có dạng YYYY-MM-DD',
    });
  }

  if (pxvSalesHasAppointment(normalized)) {
    if (!phone) {
      errors.push({
        code: 'PHONE_REQUIRED_FOR_APPOINTMENT',
        field: 'SỐ ĐT',
        message: 'Khách đã có lịch hẹn thì bắt buộc phải có SĐT',
      });
    }
    const appointmentDate = String(normalized['NGÀY HẸN'] || '').trim();
    if (!pxvSalesIsIsoDate(appointmentDate)) {
      errors.push({
        code: 'APPOINTMENT_DATE_REQUIRED',
        field: 'NGÀY HẸN',
        message: 'Ngày hẹn phải có dạng YYYY-MM-DD',
      });
    } else if (pxvSalesIsIsoDate(leadDate) && appointmentDate < leadDate) {
      errors.push({
        code: 'APPOINTMENT_BEFORE_LEAD',
        field: 'NGÀY HẸN',
        message: 'Ngày hẹn không được sớm hơn ngày khách inbox',
      });
    }
    if (!pxvSalesIsTime(normalized['GIỜ HẸN'])) {
      errors.push({
        code: 'APPOINTMENT_TIME_REQUIRED',
        field: 'GIỜ HẸN',
        message: 'Giờ hẹn phải có dạng HH:mm',
      });
    }
  }

  return { ok: errors.length === 0, errors: errors, normalized: normalized };
}

/** JSON ổn định để checksum không đổi theo thứ tự property. */
function pxvSalesStableJson(record, fields) {
  const out = {};
  (fields || []).forEach(function (field) {
    const value = record && record[field];
    out[field] = value === null || value === undefined ? '' : String(value);
  });
  return JSON.stringify(out);
}

/** FNV-1a 32 bit: đủ cho phát hiện sửa tay, chạy được cả Apps Script và Node. */
function pxvSalesChecksum(record, fields) {
  const text = pxvSalesStableJson(record, fields);
  let hash = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return ('00000000' + (hash >>> 0).toString(16)).slice(-8);
}

function pxvSalesChangedFields(before, after, fields) {
  return (fields || []).filter(function (field) {
    const oldValue = before && before[field] != null ? String(before[field]) : '';
    const newValue = after && after[field] != null ? String(after[field]) : '';
    return oldValue !== newValue;
  });
}

/**
 * Quyết định ingest không chạm Google Sheets, nên test được mọi nhánh retry.
 *
 * - Không có central -> APPEND.
 * - Central bị quản lý sửa kể từ sync trước -> CONFLICT.
 * - Revision cũ/bằng và checksum khớp -> IGNORE.
 * - Revision mới hơn -> UPDATE.
 */
function pxvResolveSalesRevision(
  centralExists,
  centralRevision,
  incomingRevision,
  lastCentralChecksum,
  currentCentralChecksum
) {
  if (!centralExists) return 'APPEND';
  if (lastCentralChecksum &&
      currentCentralChecksum &&
      lastCentralChecksum !== currentCentralChecksum) {
    return 'CONFLICT';
  }
  if (Number(incomingRevision || 0) <= Number(centralRevision || 0)) return 'IGNORE';
  return 'UPDATE';
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    SALES_STATUS: SALES_STATUS,
    SALES_META: SALES_META,
    SALES_CENTRAL_META_HEADERS: SALES_CENTRAL_META_HEADERS,
    SALES_REQUIRED_ON_SUBMIT: SALES_REQUIRED_ON_SUBMIT,
    SALES_APPOINTMENT_STATUSES: SALES_APPOINTMENT_STATUSES,
    SALES_ORIGIN_FIELDS: SALES_ORIGIN_FIELDS,
    SALES_EDITABLE_FIELDS: SALES_EDITABLE_FIELDS,
    SALES_TRACKING_HEADERS: SALES_TRACKING_HEADERS,
    SALES_FORM_FIELDS: SALES_FORM_FIELDS,
    pxvSalesBlank: pxvSalesBlank,
    pxvSalesNormalizeText: pxvSalesNormalizeText,
    pxvSalesNormalizePhone: pxvSalesNormalizePhone,
    pxvSalesIsIsoDate: pxvSalesIsIsoDate,
    pxvSalesIsTime: pxvSalesIsTime,
    pxvSalesHasAppointment: pxvSalesHasAppointment,
    pxvSalesDuplicateReasonError: pxvSalesDuplicateReasonError,
    pxvValidateSalesLead: pxvValidateSalesLead,
    pxvSalesStableJson: pxvSalesStableJson,
    pxvSalesChecksum: pxvSalesChecksum,
    pxvSalesChangedFields: pxvSalesChangedFields,
    pxvResolveSalesRevision: pxvResolveSalesRevision,
  };
}
