const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(
  path.join(__dirname, '..', 'apps_script', 'SalesCore.gs'),
  'utf8',
);
const context = {
  module: { exports: {} },
  exports: {},
  console,
};
vm.createContext(context);
vm.runInContext(source, context, { filename: 'SalesCore.gs' });
const core = context.module.exports;

test('SalesEntry nạp trước SalesCore không lỗi do thứ tự file Apps Script', () => {
  const loadContext = {
    module: { exports: {} },
    exports: {},
    console,
  };
  vm.createContext(loadContext);
  const entrySource = fs.readFileSync(
    path.join(__dirname, '..', 'apps_script', 'SalesEntry.gs'),
    'utf8',
  );
  assert.doesNotThrow(() => {
    vm.runInContext(entrySource, loadContext, { filename: 'SalesEntry.gs' });
    vm.runInContext(source, loadContext, { filename: 'SalesCore.gs' });
  });
  assert.equal(loadContext.module.exports.SALES_META.LEAD_ID, '_LEAD_ID');
});

const catalog = {
  'NGUỒN': ['Fanpage PXV'],
  'NHÓM SP': ['DỊCH VỤ'],
  'LOẠI TIN NHẮN': ['QUẢNG CÁO'],
  CHATPAGE: ['Sales 1'],
  'TÌNH TRẠNG': ['CHỜ TRẢ LỜI', 'ĐẶT HẸN'],
  'TRẠNG THÁI': ['CHỜ TRẢ LỜI', 'ĐẶT HẸN'],
  'LÝ DO CHƯA CÓ SĐT': ['Khách chưa cho'],
};

function baseLead() {
  return {
    NGÀY: '2026-07-30',
    'TÊN KHÁCH HÀNG': 'Khách thử',
    'SỐ ĐT': '',
    'LÝ DO CHƯA CÓ SĐT': 'Khách chưa cho',
    'LOẠI TIN NHẮN': 'QUẢNG CÁO',
    'NHÓM SP': 'DỊCH VỤ',
    CHATPAGE: 'Sales 1',
    NGUỒN: 'Fanpage PXV',
    'TÌNH TRẠNG': 'CHỜ TRẢ LỜI',
    'TRẠNG THÁI': 'CHỜ TRẢ LỜI',
    'GIỜ HẸN': '',
    'NGÀY HẸN': '',
  };
}

test('chuẩn hóa SĐT khớp Python cho VN, quốc tế và rác', () => {
  assert.equal(core.pxvSalesNormalizePhone('0390 000 001'), '0390000001');
  assert.equal(core.pxvSalesNormalizePhone('84390000001'), '0390000001');
  assert.equal(core.pxvSalesNormalizePhone('0016505550100'), '+16505550100');
  assert.equal(core.pxvSalesNormalizePhone('0'), '');
  assert.equal(core.pxvSalesNormalizePhone('ghi chú'), '');
});

test('ngày đầu chưa chốt hẹn vẫn nộp được khi có lý do thiếu SĐT', () => {
  const result = core.pxvValidateSalesLead(baseLead(), catalog);
  assert.equal(result.ok, true);
  assert.deepEqual(Array.from(result.errors), []);
});

test('ngày sau chốt hẹn bắt buộc SĐT, ngày và giờ', () => {
  const lead = baseLead();
  lead['TRẠNG THÁI'] = 'ĐẶT HẸN';
  const invalid = core.pxvValidateSalesLead(lead, catalog);
  const codes = Array.from(invalid.errors, (error) => error.code);
  assert.equal(invalid.ok, false);
  assert.ok(codes.includes('PHONE_REQUIRED_FOR_APPOINTMENT'));
  assert.ok(codes.includes('APPOINTMENT_DATE_REQUIRED'));
  assert.ok(codes.includes('APPOINTMENT_TIME_REQUIRED'));

  lead['SỐ ĐT'] = '390000001';
  lead['LÝ DO CHƯA CÓ SĐT'] = '';
  lead['NGÀY HẸN'] = '2026-07-31';
  lead['GIỜ HẸN'] = '14:30';
  const valid = core.pxvValidateSalesLead(lead, catalog);
  assert.equal(valid.ok, true);
  assert.equal(valid.normalized['SỐ ĐT'], '0390000001');
});

test('không cho lịch hẹn sớm hơn ngày inbox', () => {
  const lead = baseLead();
  lead['SỐ ĐT'] = '0390000001';
  lead['LÝ DO CHƯA CÓ SĐT'] = '';
  lead['TRẠNG THÁI'] = 'ĐẶT HẸN';
  lead['NGÀY HẸN'] = '2026-07-29';
  lead['GIỜ HẸN'] = '10:00';
  const result = core.pxvValidateSalesLead(lead, catalog);
  assert.ok(Array.from(result.errors, (error) => error.code)
    .includes('APPOINTMENT_BEFORE_LEAD'));
});

test('chỉ nhập giờ hoặc đặt trạng thái hẹn ở một trong hai cột vẫn phải đủ lịch', () => {
  const onlyTime = baseLead();
  onlyTime['GIỜ HẸN'] = '10:00';
  const timeCodes = Array.from(
    core.pxvValidateSalesLead(onlyTime, catalog).errors,
    (error) => error.code,
  );
  assert.ok(timeCodes.includes('PHONE_REQUIRED_FOR_APPOINTMENT'));
  assert.ok(timeCodes.includes('APPOINTMENT_DATE_REQUIRED'));

  const interactionStatus = baseLead();
  interactionStatus['TÌNH TRẠNG'] = 'ĐẶT HẸN';
  const statusCodes = Array.from(
    core.pxvValidateSalesLead(interactionStatus, catalog).errors,
    (error) => error.code,
  );
  assert.ok(statusCodes.includes('APPOINTMENT_TIME_REQUIRED'));
});

test('ngày mới chỉ nhận ISO và duplicate chỉ đi tiếp khi có lý do', () => {
  const nonIso = baseLead();
  nonIso.NGÀY = '30/07/2026';
  assert.ok(Array.from(
    core.pxvValidateSalesLead(nonIso, catalog).errors,
    (error) => error.code,
  ).includes('LEAD_DATE_INVALID'));

  assert.equal(
    core.pxvSalesDuplicateReasonError(true, '').code,
    'DUPLICATE_REASON_REQUIRED',
  );
  assert.equal(core.pxvSalesDuplicateReasonError(true, 'Khách inbox chiến dịch mới'), null);
  assert.equal(core.pxvSalesDuplicateReasonError(false, ''), null);
});

test('batch hỗn hợp validate từng dòng độc lập', () => {
  const invalid = baseLead();
  invalid['TÊN KHÁCH HÀNG'] = '';
  const results = [baseLead(), invalid, baseLead()].map(
    (lead) => core.pxvValidateSalesLead(lead, catalog).ok,
  );
  assert.deepEqual(results, [true, false, true]);
});

test('revision mới cập nhật cùng lead; retry không append lần hai', () => {
  assert.equal(core.pxvResolveSalesRevision(false, 0, 1, '', ''), 'APPEND');
  assert.equal(core.pxvResolveSalesRevision(true, 1, 2, 'abc', 'abc'), 'UPDATE');
  assert.equal(core.pxvResolveSalesRevision(true, 2, 2, 'abc', 'abc'), 'IGNORE');
  assert.equal(core.pxvResolveSalesRevision(true, 2, 1, 'abc', 'abc'), 'IGNORE');
});

test('follow-up hôm sau giữ một LEAD_ID và nguyên ngày inbox', () => {
  const central = new Map();
  const first = {
    _LEAD_ID: 'lead-01',
    _REVISION: 1,
    NGÀY: '2026-07-30',
    'NGÀY HẸN': '',
  };
  central.set(first._LEAD_ID, first);

  const followUp = {
    ...first,
    _REVISION: 2,
    'NGÀY HẸN': '2026-07-31',
    'GIỜ HẸN': '14:30',
  };
  const action = core.pxvResolveSalesRevision(true, 1, 2, 'same', 'same');
  assert.equal(action, 'UPDATE');
  central.set(followUp._LEAD_ID, followUp);

  assert.equal(central.size, 1);
  assert.equal(central.get('lead-01').NGÀY, '2026-07-30');
  assert.equal(central.get('lead-01')['NGÀY HẸN'], '2026-07-31');
});

test('manager sửa central sau lần sync tạo CONFLICT', () => {
  assert.equal(
    core.pxvResolveSalesRevision(true, 1, 2, 'checksum-cu', 'checksum-moi'),
    'CONFLICT',
  );
});

test('checksum ổn định và phát hiện đúng trường thay đổi', () => {
  const before = { A: '1', B: '2' };
  const sameOrderDifferent = { B: '2', A: '1' };
  const after = { A: '1', B: '3' };
  assert.equal(
    core.pxvSalesChecksum(before, ['A', 'B']),
    core.pxvSalesChecksum(sameOrderDifferent, ['A', 'B']),
  );
  assert.notEqual(
    core.pxvSalesChecksum(before, ['A', 'B']),
    core.pxvSalesChecksum(after, ['A', 'B']),
  );
  assert.deepEqual(
    Array.from(core.pxvSalesChangedFields(before, after, ['A', 'B'])),
    ['B'],
  );
});
