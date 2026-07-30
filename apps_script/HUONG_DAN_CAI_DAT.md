# Hướng dẫn cài đặt Apps Script

Tổng thời gian **20–30 phút**. Làm một lần duy nhất.

> **Thứ tự dán 11 file KHÔNG quan trọng.** Apps Script gộp mọi file `.gs` trong cùng project vào một không gian chung, nên hàm ở file này gọi được hàm ở file kia bất kể dán trước hay sau. Điều quan trọng là **dán đủ cả 11 file rồi mới chạy hàm nào**.
>
> Thứ tự **chạy hàm** thì có quan trọng — xem Bước 5 và 7.

---

## Vai trò 11 file

| File | Làm gì | Khi nào chạy |
|---|---|---|
| `Config.gs` | Khai báo ID, ngưỡng, tên cột | Không chạy — chỉ sửa nội dung |
| `Bootstrap.gs` | **Dựng toàn bộ spreadsheet + thư mục** | Chạy 1 lần, đầu tiên |
| `Setup.gs` | Tạo trigger tự động | Chạy 1 lần, sau Bootstrap |
| `OnEdit.gs` | Kiểm lỗi ngay lúc sales gõ | Tự chạy, không cần cài |
| `Menu.gs` | Menu 🔄 PXV trên thanh công cụ | Tự chạy khi mở file |
| `IngestKiotViet.gs` | Nạp file hóa đơn từ Drive | Trigger mỗi giờ |
| `IngestPancake.gs` | Vá lead thiếu SĐT | Trigger hằng tuần |
| `Watchdog.gs` | Canh pipeline + nhắc export | Trigger hằng ngày |
| `SalesCore.gs` | Validation, checksum và revision dùng chung | Không chạy trực tiếp |
| `SalesEntry.gs` | Form, Lưu tạm/Nộp và follow-up trong file sale | Installable onEdit |
| `SalesIngest.gs` | Tạo file sale, registry, ingest và conflict log | Trigger mỗi 5 phút |

---

## Bước 1 — Tạo Google Sheet trống

Vào [sheets.new](https://sheets.new), đặt tên **chính xác** là:

```
PXV_NHẬP_LIỆU
```

Tên này chỉ để bạn dễ nhận ra; script tìm file theo ID nên đặt khác cũng được, nhưng đặt đúng thì hướng dẫn khớp với thực tế.

## Bước 2 — Mở trình soạn Apps Script

Trên thanh menu: **Tiện ích mở rộng** (Extensions) → **Apps Script**.

Một tab mới mở ra, có sẵn file `Code.gs` với hàm rỗng.

## Bước 3 — Dán 11 file

Với **mỗi** file trong thư mục `apps_script/`:

1. Bấm dấu **+** cạnh chữ "Files" (bên trái) → chọn **Script**
2. Gõ tên file **không có đuôi** — ví dụ gõ `Config`, không phải `Config.gs`
3. Xóa hết nội dung mẫu trong ô soạn thảo
4. Dán toàn bộ nội dung file tương ứng
5. `Ctrl+S` (hoặc `Cmd+S`) để lưu

Làm đủ 11 file: `Config`, `Bootstrap`, `Setup`, `OnEdit`, `Menu`,
`IngestKiotViet`, `IngestPancake`, `Watchdog`, `SalesCore`, `SalesEntry`,
`SalesIngest`.

Xong thì **xóa file `Code.gs`** mặc định (bấm ⋮ cạnh tên → Delete).

> Chưa cần sửa gì trong `Config.gs` ở bước này. Bước 6 mới điền.

## Bước 4 — Bật Drive API và Google Sheets API

Bên trái, cạnh chữ **Services**, bấm dấu **+**, thêm cả:

- **Drive API** — đọc file Excel của Pancake.
- **Google Sheets API** — ghi lead bằng `valueInputOption=RAW`, giữ số 0 đầu và
  ngày ISO.

Nếu quên Sheets API, code có fallback định dạng text nhưng sẽ ghi cảnh báo trong
Apps Script Executions.

## Bước 5 — Chạy `dungHeThong()`

Trên thanh công cụ, ô chọn hàm đang hiện `dungHeThong` (hoặc bấm mũi tên chọn). Bấm **Run**.

**Lần đầu Google sẽ hỏi quyền:**

1. Bấm **Review permissions**
2. Chọn tài khoản Google của bạn
3. Màn hình cảnh báo "Google hasn't verified this app" → bấm **Advanced**
4. Bấm **Go to *(tên project)* (unsafe)**
5. Bấm **Allow**

Cảnh báo này xuất hiện với mọi Apps Script tự viết chưa qua thẩm định của Google. Đây là script của chính bạn, chạy trong tài khoản của bạn.

**Script sẽ tạo:**

```
Drive/PXV/
  ├── PXV_NHẬP_LIỆU        LEAD, DANH_MỤC, ÁNH_XẠ_ALIAS,
  │                        CHI_PHÍ_QC, DANH_MỤC_SALES,
  │                        SALES_INGEST_LOG, SALES_LỖI...
  ├── PXV_KHO              INVOICES_RAW, PANCAKE_RAW, KIOTVIET_LOG
  ├── PXV_DASHBOARD_DATA   DQ_STATUS
  ├── KiotViet_Drop/       (thả file export KiotViet vào đây)
  ├── Pancake_Drop/        (thả file export Pancake vào đây)
  └── Sales_Entry/         (mỗi sale một file riêng)
```

kèm 8 dropdown, khóa hàng header, định dạng cột SĐT thành text.

Chạy xong xem **View → Logs** (hoặc `Ctrl+Enter`), sẽ thấy 5 ID được in ra.

> Chạy lại `dungHeThong()` lần nữa cũng không hỏng — chỗ nào đã có thì bỏ qua, không ghi đè dữ liệu.

## Bước 6 — Chép 5 ID vào `Config.gs`

Mở `Config.gs`, thay 5 dòng còn ghi `DÁN_ID...` bằng ID lấy từ Logs:

```javascript
KHO_ID: '1AbC...',
DASHBOARD_ID: '1XyZ...',
KIOTVIET_FOLDER_ID: '1Def...',
PANCAKE_FOLDER_ID: '1Ghi...',
SALES_FOLDER_ID: '1Jkl...',
```

Đồng thời sửa dòng email nhận cảnh báo:

```javascript
ALERT_EMAIL: 'email-cua-ban@gmail.com',
```

Lưu lại.

> **Bỏ qua bước này hệ thống vẫn chạy** — `dungHeThong()` đã lưu các ID vào
> Script Properties và code tự đọc từ đó.

## Bước 7 — Chạy `taoTrigger()`

Chọn hàm `taoTrigger` → **Run**.

Tạo 5 lịch chạy tự động, cộng một `onSaleEdit` cho mỗi file sale active:

| Hàm | Khi nào |
|---|---|
| `napKiotViet` | Mỗi giờ |
| `nhacExportKiotViet` | 08:00 hằng ngày |
| `canhChung` | 09:00 hằng ngày |
| `napPancakeAnToan` | 07:00 thứ Hai |
| `napLeadTuSales` | Mỗi 5 phút |

`onEdit` và `onOpen` **không nằm trong danh sách này** vì Google tự chạy chúng — không cần cài gì thêm.

## Bước 8 — Mở lại Google Sheet

Quay về tab Google Sheet, tải lại trang (`F5`). Menu **🔄 PXV** sẽ hiện cạnh menu Help.

Bấm **🔄 PXV → Kiểm tra cấu hình**. Phải thấy toàn dấu ✅:

```
✅ Đã điền đủ ID trong Config.gs
✅ Mở được Kho PXV_KHO
✅ Mở được Dashboard
✅ Mở được thư mục KiotViet_Drop
✅ Mở được thư mục Pancake_Drop
✅ Mở được thư mục Sales_Entry
⚠️ Chưa có GITHUB_TOKEN
✅ Đã đặt ít nhất 5 trigger
```

Dòng `GITHUB_TOKEN` báo vàng là bình thường — xem Bước 10.

---

## Bước 9 — Chia sẻ cho Service Account

Bước này cần làm **sau khi** đã tạo Service Account trên Google Cloud (xem README của repo).

Mở từng file → **Share** → dán email service account (dạng `pxv-pipeline@...iam.gserviceaccount.com`):

| File | Quyền | Vì sao |
|---|---|---|
| `PXV_NHẬP_LIỆU` | **Viewer** | Pipeline chỉ đọc, không được sửa dữ liệu sales nhập |
| `PXV_KHO` | **Editor** | Đọc hóa đơn |
| `PXV_DASHBOARD_DATA` | **Editor** | Ghi 6 bảng kết quả |

Bỏ tick "Notify people" — service account không đọc email.

> **Chỉ share đúng 3 file, không share cả thư mục PXV.** Nếu key rò rỉ, thiệt hại giới hạn ở 3 file thay vì toàn bộ Drive.

## Bước 10 — GitHub token (không bắt buộc)

Để nút **🔄 PXV → Chạy lại pipeline ngay** hoạt động:

1. [github.com/settings/personal-access-tokens](https://github.com/settings/personal-access-tokens) → **Generate new token**
2. **Repository access** → Only select repositories → chọn repo GitHub hiện tại của pipeline
3. **Permissions** → Repository permissions → **Contents: Read and write**
4. Generate → copy token
5. Về Apps Script → ⚙️ **Project Settings** → **Script Properties** → **Add script property**
   - Property: `GITHUB_TOKEN`
   - Value: token vừa copy
6. Thêm tiếp script property:
   - Property: `GITHUB_REPO`
   - Value: tên repo GitHub hiện tại của pipeline

> **Đừng dán token vào `Config.gs`.** Ai xem được script là đọc được, và file đó nằm trong repo.

---

## Việc cần làm trước khi cho sales dùng

**Sửa danh sách nhân viên.** Tab `DANH_MỤC`, cột `CHATPAGE` đang là `Sales 1/2/3` và cột `TƯ VẤN - SALE` đang là tên mẫu — đổi cả hai thành tên thật.

**Rà lại các danh mục khác** trong `DANH_MỤC`: `NGUỒN`, `TÌNH TRẠNG`, `TRẠNG THÁI`, `TƯ VẤN - SALE`. Sửa cho khớp cách gọi ở spa.

**Nếu thêm `NGUỒN` mới**, phải báo người kỹ thuật thêm vào bảng gom kênh trong `pxv/mappings.py`, không thì nguồn đó rơi vào nhóm "Khác" trên dashboard.

**Đọc tab `HƯỚNG_DẪN`** với đội sales — nhất là 5 quy tắc bắt buộc (không đổi tên cột, không gộp ô, không thêm dòng tổng).

### Tạo file riêng và pilot

1. Mở menu **🔄 PXV → Sales Entry → Dựng/nâng cấp hệ thống sales**.
   Nếu `DANH_MỤC` còn schema cũ, script tự tạo tab `DM_BACKUP_...` trước khi
   migrate; dữ liệu trong `LEAD` không bị sửa.
2. Chọn **Tạo file cho sale**, nhập tên `Trường Khang` và Gmail dùng pilot.
3. Sale mở file `PXV_SALES_Trường Khang`:
   - nhập form `NHẬP_MỚI` rồi tick **LƯU TẠM**;
   - cuối ngày tick **NỘP CUỐI NGÀY**;
   - hôm sau mở `ĐANG_THEO_DÕI`, bổ sung lịch hẹn rồi Nộp lại.
4. Trong tối đa 5 phút, quản lý kiểm tra:
   - `LEAD` có đúng một `_LEAD_ID`;
   - revision sau follow-up tăng từ 1 lên 2 nhưng `NGÀY` không đổi;
   - `SALES_INGEST_LOG` có một dòng cho mỗi revision;
   - lỗi/conflict, nếu có, nằm ở `SALES_LỖI`.
5. Pilot đủ hai ngày rồi mới tạo file cho các sale còn lại.

Sale chỉ được share file riêng. **Không share `PXV_NHẬP_LIỆU` cho sale.**

---

## Khi gặp lỗi

**"Chưa có KHO_ID"** — chưa chạy `dungHeThong()`, hoặc chạy lỗi giữa chừng. Chạy lại và xem Logs.

**"Không thấy sheet LEAD"** — `dungHeThong()` chưa chạy xong. Chạy lại bootstrap
và kiểm tra `PXV_NHẬP_LIỆU` có `LEAD`, `DANH_MỤC` cùng ba tab Sales Entry.

**Menu 🔄 PXV không hiện** — tải lại trang. Vẫn không có thì kiểm tra `Menu.gs` đã dán chưa và có hàm `onOpen`.

**"Drive is not defined"** khi chạy Pancake — chưa bật Drive API ở Bước 4.

**onEdit không phản ứng khi gõ** — mở Apps Script → **Executions** xem có lỗi không. Lưu ý `onEdit` không chạy khi bạn sửa ô bằng script hoặc bằng import, chỉ chạy khi người thật gõ tay.

**Trigger không chạy** — Apps Script → **Triggers** (biểu tượng đồng hồ) xem
ít nhất 5 trigger lịch và một `onSaleEdit` cho mỗi file sale active. Cột
"Last run" báo lỗi thì bấm vào xem chi tiết.

**Sale bấm Nộp nhưng dữ liệu không sang LEAD** — xem `SALES_LỖI`, rồi chạy menu
**Sales Entry → Nạp dữ liệu sales ngay**. Nếu báo `CONFLICT`, quản lý đã sửa
dòng trung tâm sau lần sync; đối chiếu `SALES_INGEST_LOG` trước khi quyết định
giữ giá trị nào.

Sự cố khi đã vận hành: xem [RUNBOOK.md](../RUNBOOK.md).

---

## Next-step checklist — triển khai live

- [ ] Kết nối repo với project Apps Script thật bằng `clasp`, hoặc chép đủ 11
      file `.gs` theo đúng thứ tự trong hướng dẫn này.
- [ ] Bật **Drive API** và **Google Sheets API** trong Apps Script.
- [ ] Chạy `dungHeThongSales()` bằng tài khoản quản lý; xác nhận script tạo
      `Sales_Entry`, ba tab quản trị và backup `DM_BACKUP_...` nếu phải migrate.
- [ ] Rà lại `DANH_MỤC`: tên sale, Gmail, `NGUỒN`, `NHÓM SP`, `CHATPAGE`,
      `LOẠI TIN NHẮN` và lý do thiếu SĐT đều là dữ liệu thật.
- [ ] Điền Gmail pilot của Trường Khang vào `DANH_MỤC_SALES`.
- [ ] Chạy **Sales Entry → Tạo file cho sale** và chỉ share
      `PXV_SALES_Trường Khang`; không share file quản lý.
- [ ] Kiểm tra trigger `onSaleEdit` của file pilot và trigger
      `napLeadTuSales` mỗi 5 phút.
- [ ] Pilot đủ hai ngày với ít nhất: một lead chưa hẹn, một lead bổ sung SĐT,
      một duplicate có lý do và một dòng validation lỗi.
- [ ] Quản lý và Trường Khang ký xác nhận số lead, revision và quyền truy cập
      trước khi tạo file cho sale tiếp theo.
- [ ] Rollout từng sale; theo dõi `SALES_LỖI` và `SALES_INGEST_LOG` hằng ngày
      trong tuần đầu.

## Verification checklist — điều kiện go-live

- [ ] Thư mục `Drive/PXV/` có ba spreadsheet hiện tại và thư mục `Sales_Entry`.
- [ ] `PXV_NHẬP_LIỆU` có `DANH_MỤC_SALES`, `SALES_INGEST_LOG`, `SALES_LỖI`.
- [ ] Cuối `LEAD` có đúng `_LEAD_ID`, `_REVISION`, `_BATCH_ID`,
      `_SUBMITTED_AT`, `_SOURCE_SALE_ID`; năm cột đang ẩn và được bảo vệ.
- [ ] File sale có đủ `NHẬP_MỚI`, `ĐANG_THEO_DÕI`, `HÔM_NAY`, `LỊCH_SỬ`;
      sale không mở được file quản lý.
- [ ] Cột SĐT giữ số 0 đầu; số VN, quốc tế và `"0"` cho kết quả chuẩn hóa đúng.
- [ ] Ngày đầu chưa hẹn tạo revision 1; ngày sau bổ sung lịch tạo revision 2
      trên cùng `_LEAD_ID`, giữ nguyên `NGÀY`, và `LEAD` vẫn chỉ có một dòng.
- [ ] Bổ sung SĐT sau khi từng chọn lý do thiếu SĐT hoạt động; lý do cũ phải
      được xóa trước khi Submit.
- [ ] Có lịch hoặc trạng thái hẹn nhưng thiếu SĐT/ngày/giờ bị chặn; ngày hẹn
      trước ngày inbox và ngày không phải ISO cũng bị chặn.
- [ ] Duplicate `SĐT + NGÀY` không có `LÝ DO TRÙNG` bị chặn; có lý do thì nhập
      được và lý do xuất hiện trong `SALES_INGEST_LOG`.
- [ ] Chạy ingest lại cùng revision không tạo dòng mới và ghi
      `IGNORED_IDEMPOTENT`.
- [ ] Một batch có dòng lỗi vẫn nhập các dòng hợp lệ; lỗi nằm trong
      `SALES_LỖI` và chuyển `RESOLVED` sau khi sửa thành công.
- [ ] Sửa thủ công LEAD trung tâm rồi Submit revision mới tạo `CONFLICT`, không
      ghi đè; cả hai lựa chọn giải quyết conflict đều được ghi lịch sử.
- [ ] Đóng theo dõi ẩn lead khỏi danh sách; quản lý mở lại được và revision sau
      đó vẫn cập nhật cùng dòng trung tâm.
- [ ] Menu **🔄 PXV → Kiểm tra cấu hình** toàn ✅, trừ `GITHUB_TOKEN` nếu không
      dùng nút chạy pipeline.
- [ ] Apps Script → Triggers có ít nhất năm trigger lịch và một `onSaleEdit`
      cho mỗi file sale active; không có execution lỗi chưa xử lý.
- [ ] Chạy lại `python -m pytest tests/ -q` và `node --test
      tests_js/*.test.cjs`: tất cả test đạt.
- [ ] Chạy pipeline sau pilot: doanh thu `2.552.689.000đ`, `710` hóa đơn và
      funnel nền `2380 → 1274 → 303 → 186`, cộng đúng số bước mới phát sinh từ
      lead pilot; không tăng inbox khi chỉ follow-up revision.
