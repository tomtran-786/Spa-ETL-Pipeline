# Spa — Sales & Marketing Data Pipeline

ETL pipeline hợp nhất dữ liệu sales, lịch hẹn, KiotViet và quảng cáo để đo phễu
chuyển đổi, doanh thu, hiệu quả kênh, CLV và hành vi quay lại.

Dashboard vận hành: [PXV — Looker Studio](https://datastudio.google.com/u/0/reporting/19939443-e921-49d9-948d-03b4d663c5da/page/jQvqF).

## 1. Bối cảnh vấn đề

Dữ liệu khách hàng đang nằm rời rạc:

| Nguồn | Biết được | Không biết được |
|---|---|---|
| Google Sheets của sales | Khách hỏi gì, đến từ đâu, có đặt lịch không | Khách có mua và chi bao nhiêu |
| KiotViet | Khách mua gì, doanh thu bao nhiêu | Khách đến từ kênh nào |
| Dữ liệu quảng cáo | Chi phí theo kênh/bài QC | Lead và doanh thu tạo ra |
| Pancake | Hội thoại và một phần SĐT | Kết quả mua hàng |

SĐT là khóa chung khả dụng nhất, nhưng dữ liệu thực tế không sạch:

- Khoảng 46% lead không có SĐT.
- SĐT có nhiều định dạng, gồm số Việt Nam, quốc tế và giá trị rác.
- Tổng hóa đơn KiotViet lặp trên từng dòng mặt hàng.
- Một khách có thể inbox hoặc mua nhiều lần, dễ bị đếm trùng.
- Ngày có thể bị lật ngày/tháng khi import qua Google Sheets.
- Khoảng 75% doanh thu đến từ khách chưa có hồ sơ lead.

Nếu join và tính trực tiếp trong Looker Studio, dashboard vẫn có thể trông hợp
lý nhưng sai doanh thu, mẫu số hoặc tỷ lệ chuyển đổi.

## 2. Solution này là gì

Solution gồm hai phần:

- **Python/pandas pipeline** làm sạch, join, tính metric, kiểm chất lượng và xuất
  các data mart cho Looker Studio.
- **Apps Script** nạp file từ Drive, kiểm tra dữ liệu ngay trên Google Sheets,
  cung cấp file nhập riêng cho từng sale, đồng bộ revision có audit, menu vận
  hành và watchdog theo dõi pipeline.

```text
Google Sheets + Google Drive
             │
             ▼
 File riêng sale → Apps Script ingest
      LEAD_ID + revision
             │
             ▼
 PXV_KHO: invoice / Pancake
             │
             ▼
        GitHub Actions
 pytest → ETL → DQ → load output
             │
             ▼
 PXV_DASHBOARD_DATA → Looker Studio
```

Metric được tính ở đúng grain trong pipeline, không để BI tool tự cộng lại
ROAS, CAC, CLV hoặc tỷ lệ upsell.

### PXV Sales Entry — nhập lead và follow-up nhiều ngày

Mỗi sale làm việc trong một spreadsheet riêng do quản lý sở hữu. File có bốn
giao diện chính:

| Tab | Mục đích |
|---|---|
| `NHẬP_MỚI` | Form tạo lead mới và lưu nháp |
| `ĐANG_THEO_DÕI` | Tìm và cập nhật lead đã nộp |
| `HÔM_NAY` | Draft, revision và lỗi cần xử lý trong ngày |
| `LỊCH_SỬ` | Batch, revision và kết quả đồng bộ |

Một lead giữ nguyên `_LEAD_ID` trong toàn bộ vòng đời tư vấn. Ví dụ:

```text
30/07: khách chưa chốt hẹn → Submit revision 1 → append vào LEAD
31/07: khách chốt hẹn      → Submit revision 2 → update đúng dòng cũ
```

`NGÀY` inbox không đổi, vì vậy follow-up không tạo thêm inbox và không làm phồng
funnel. Trigger quản lý quét mỗi 5 phút, chỉ append khi `_LEAD_ID` chưa tồn tại
và chỉ update khi revision mới hơn.

Các lớp bảo vệ dữ liệu:

- Chuẩn hóa SĐT giống pipeline Python; giữ số quốc tế và loại giá trị `"0"`.
- Ngày mới dùng ISO `YYYY-MM-DD`, giờ dùng `HH:mm`.
- Có lịch hẹn thì bắt buộc SĐT, ngày và giờ; ngày hẹn không trước ngày inbox.
- Duplicate `SĐT + NGÀY` cần `LÝ DO TRÙNG` mới được tiếp tục.
- Checksum phát hiện quản lý đã sửa dòng trung tâm; revision chuyển `CONFLICT`
  thay vì tự ghi đè.
- Mỗi dòng được xử lý độc lập: một dòng lỗi không chặn phần còn lại của batch.
- Ghi `LEAD` bằng Sheets API `RAW` để không mất số 0 hoặc lật ngày/tháng.

Phía quản lý có `DANH_MỤC_SALES`, `SALES_INGEST_LOG` và `SALES_LỖI`. Sale chỉ
được share file riêng, không có quyền vào `PXV_NHẬP_LIỆU`. Cách cài đặt, pilot
và verification checklist nằm trong
[`apps_script/HUONG_DAN_CAI_DAT.md`](apps_script/HUONG_DAN_CAI_DAT.md).

## 3. Kết quả và insights

Lần đối chiếu backend Sheets gần nhất: **30/07/2026 14:59**.

| Chỉ số | Kết quả |
|---|---:|
| Dòng lead | **2.426** |
| Phễu | **2.367 → 1.267 → 295 → 183** |
| Tỷ lệ chốt trên inbox | **7,73%** |
| Hóa đơn unique | **710** |
| Doanh thu | **2.552.689.000đ** |

Các insight chính:

- **53,5% lead có SĐT dùng được**; gần một nửa inbox chưa thể nối với hóa đơn.
- **Có SĐT → Đặt lịch chỉ đạt khoảng 23,3%**. Đây là điểm rơi lớn nhất của phễu.
- **Đặt lịch → Ra đơn đạt khoảng 62%**; khi khách đã đặt lịch, khả năng mua cao.
- Khoảng **75% doanh thu chưa quy kết được về kênh** vì khách mua không có hồ sơ
  lead. ROAS theo kênh chỉ phản ánh phần doanh thu match được.
- Dịch vụ mồi tạo khoảng **19,5% bán chéo cùng ngày**, nhưng chỉ khoảng **7,0%**
  khách quay lại upsell vào ngày khác trong 90 ngày.

Các giới hạn cần nhớ:

- T12/2025 mất toàn bộ hóa đơn và không thể khôi phục.
- 35 lead mang ngày `19/01/2025`, nghi sai năm nhưng chưa được tự sửa.
- Lịch sử hóa đơn dùng cho CLV hiện bắt đầu từ `01/01/2026`.
- `CHI_PHÍ_QC` đang chứa **145.920.000đ dữ liệu mô phỏng**; CPL, CAC và ROAS
  chưa phải số vận hành thật.

> Golden funnel local là `2.380 → 1.274 → 303 → 186`, nhưng không dùng để xác
> nhận toàn bộ backend Sheets: local có thêm nguồn lịch hẹn và từng chứa các
> dòng rỗng đã bị loại khi migrate. Mốc đối chiếu chặt giữa hai backend là
> doanh thu, hóa đơn và các mart chỉ phụ thuộc hóa đơn.

## 4. Luồng ETL

### Extract

Hai backend dùng chung interface:

- [`pxv/io_local.py`](pxv/io_local.py): đọc CSV/XLSX local.
- [`pxv/io_sheets.py`](pxv/io_sheets.py): đọc/ghi Google Sheets.

Apps Script kiểm và nạp dữ liệu Drive:

- [KiotViet ingest](apps_script/IngestKiotViet.gs)
- [Pancake ingest](apps_script/IngestPancake.gs)
- [Validation khi nhập liệu](apps_script/OnEdit.gs)
- [Sales Entry core](apps_script/SalesCore.gs)
- [Form/follow-up file sale](apps_script/SalesEntry.gs)
- [Registry và ingest revision](apps_script/SalesIngest.gs)
- [Watchdog](apps_script/Watchdog.gs)

### Transform

| Bước | Logic | File |
|---|---|---|
| Validate schema | Dừng khi thiếu header bắt buộc | [`pxv/schema.py`](pxv/schema.py) |
| Làm sạch | Chuẩn hóa SĐT, ngày và tiền | [`pxv/clean.py`](pxv/clean.py) |
| Mapping | Gom nguồn, kênh và sản phẩm | [`pxv/mappings.py`](pxv/mappings.py) |
| Core model | Join lead–hẹn–hóa đơn, MECE và cờ phễu | [`pxv/transform.py`](pxv/transform.py) |
| Data marts | CLV, funnel mồi, daily, channel KPI | [`pxv/marts.py`](pxv/marts.py) |

Các nguyên tắc quan trọng:

- Lead không SĐT vẫn tính F1 nhưng không đi tiếp sang F2–F4.
- Một SĐT chỉ được đếm một lần ở mỗi bước phễu.
- Hóa đơn không SĐT vẫn phải bảo toàn doanh thu.
- `Khách cần trả` chỉ được giữ ở dòng đầu mỗi hóa đơn.
- Ngày ghi ra ngoài dùng ISO `YYYY-MM-DD`.

### Data Quality và Load

[`pxv/quality.py`](pxv/quality.py) kiểm nguồn, ngày, SĐT, hóa đơn, phễu, MECE,
chi phí và drift so với lần chạy trước. Job dừng khi:

- Dữ liệu nguồn rỗng hoặc sai schema.
- Có dấu hiệu lật ngày/tháng.
- Rớt hóa đơn/doanh thu khi merge.
- Phễu bị đếm trùng hoặc nở ở bước sau.
- Số lead giảm hoặc doanh thu tháng đã đóng thay đổi bất thường.

[`pxv/run_daily.py`](pxv/run_daily.py) điều phối job và ghi 9 bảng ra Excel hoặc
`PXV_DASHBOARD_DATA`.

Workflow: [`.github/workflows/daily.yml`](.github/workflows/daily.yml).

Hướng dẫn xử lý cảnh báo: [`RUNBOOK.md`](RUNBOOK.md).

## 5. Schema dữ liệu

Schema bắt buộc và danh sách cột cố định nằm tại
[`pxv/schema.py`](pxv/schema.py).

### Input

| Bảng | Grain | Cột chính |
|---|---|---|
| `LEAD` | Một lần khách inbox | Cột nghiệp vụ hiện có + `_LEAD_ID`, `_REVISION`, `_BATCH_ID`, `_SUBMITTED_AT`, `_SOURCE_SALE_ID` |
| `DANH_MỤC_SALES` | Một sale/file | Gmail, file ID, active và lần đồng bộ |
| `SALES_INGEST_LOG` | Một revision | Before/after, checksum và dòng đích |
| `SALES_LỖI` | Một lỗi ingest | Validation hoặc conflict cần quản lý xử lý |
| `INVOICES_RAW` | Một dòng mặt hàng | `Mã hóa đơn`, `Thời gian`, `Điện thoại`, `Khách cần trả`, `Mã hàng`, `Tên hàng` |
| `CHI_PHÍ_QC` | Tháng × kênh × bài QC | `tháng`, `kênh`, `mã bài QC`, `chi phí` |
| `PANCAKE_RAW` | Một hội thoại có SĐT | `SĐT`, `Tên khách`, `Page`, `Ngày` |

### Output

| Bảng | Grain | Mục đích |
|---|---|---|
| `MASTER` | SĐT × hóa đơn | Doanh thu, phễu, sản phẩm và MECE |
| `DIM_KHACH` | Một khách có SĐT | CLV, cohort và khách quay lại |
| `FUNNEL_MOI` | Một khách mua dịch vụ mồi | Cross-sell và upsell 30/60/90 ngày |
| `FACT_DAILY` | Ngày × kênh | Chuỗi thời gian |
| `FUNNEL_DAILY` | Ngày × kênh × bước | Funnel có filter |
| `HIEU_QUA_KENH` | Tháng × kênh | CPL, CAC, ROAS và CLV:CAC |
| `KPI` | `TỔNG` hoặc một kênh | Scorecard đã tính đúng trọng số |
| `DQ_STATUS` | Một phép kiểm | Trạng thái dữ liệu và mốc chạy |
| `CẦN_SỬA` | Một dòng nghi sai | Dữ liệu cần sửa tại nguồn |

Cách nối từng bảng vào Looker:
[`docs/LOOKER.md`](docs/LOOKER.md).

## 6. Cách setup

### Local

Yêu cầu Python 3.12:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/ -q
node --test tests_js/*.test.cjs
python -m pxv.run_daily
```

Kết quả: `output/PXV_DASHBOARD_DATA.xlsx`.

Tên file nguồn local mặc định nằm trong
[`pxv/config.py`](pxv/config.py). Không commit CSV/XLSX thật vì chứa PII.

Chuyển file lead cũ sang schema 17 cột:

```bash
python scripts/migrate_lead_csv.py <file-nguon.csv>
```

### Google Sheets

GitHub Actions cần:

| Loại | Biến |
|---|---|
| Secret | `GCP_SA_KEY` |
| Variable | `PXV_SHEET_NHAP_LIEU` |
| Variable | `PXV_SHEET_KHO` |
| Variable | `PXV_SHEET_DASHBOARD` |

Chạy tay:

```bash
PXV_BACKEND=sheets python -m pxv.run_daily
```

Workflow tự chạy lúc 06:15 hoặc từ menu
**🔄 PXV → Chạy lại pipeline ngay**.

Tài liệu setup:

- [Cài Google Sheets, Drive và Apps Script](apps_script/HUONG_DAN_CAI_DAT.md)
- [Vận hành hằng ngày](RUNBOOK.md)
- [Cấu hình Looker Studio](docs/LOOKER.md)

Test hiện tại: **154 Python tests** và **12 Sales Entry tests**. Khi thiếu
`output/Master_Pipeline_2026.xlsx`, golden tests tự skip vì file chứa PII và
không nằm trong git.

## 7. Guardrails phát triển

Các quy tắc này bảo vệ những lỗi dữ liệu từng xảy ra trong vận hành:

- Sau mọi thay đổi trong `pxv/`, chạy pipeline và giữ ba mốc nền:
  `2.552.689.000đ`, `710` hóa đơn và funnel `2380 → 1274 → 303 → 186`.
- `clean_phone("0")` phải trả `None`; số quốc tế phải được giữ dạng `+...`.
- Hóa đơn thiếu SĐT vẫn tính doanh thu và không được deduplicate chung qua
  khóa `NaN`.
- `Khách cần trả` là tổng hóa đơn lặp trên từng dòng hàng; chỉ cộng một lần cho
  mỗi mã hóa đơn.
- Mọi ngày ghi sang Sheets phải là ISO và mọi giá trị được ghi bằng `RAW`.
- Không sửa một phía của chuẩn hóa SĐT: Python và Apps Script phải luôn khớp.
- Không commit CSV/XLSX/output hoặc dữ liệu khách thật. Fixtures và test chỉ dùng
  dữ liệu tổng hợp.
- T12/2025 là khoảng trống dữ liệu đã biết, không được biểu diễn thành doanh thu
  bằng 0.
- CLV và funnel dịch vụ mồi phải tính ở pipeline theo grain khách, không tính
  lại bằng `AVG` trên bảng `MASTER`.

## 8. Định hướng phát triển và scale-up

### Giai đoạn 1 — Hoàn thiện dữ liệu vận hành

- Thay chi phí mô phỏng bằng chi phí thật.
- Xử lý 35 lead nghi sai năm sau xác nhận nghiệp vụ.
- Duy trì ingest KiotViet hằng ngày.
- Đo chất lượng ghép Pancake trước khi bật `PXV_PANCAKE=1`.

### Giai đoạn 2 — Cải thiện attribution

- Tăng tỷ lệ thu thập SĐT trong quy trình sales.
- Thu thập campaign/ad ID thay vì chỉ dùng tên nguồn.
- Bổ sung booking/referral code cho khách vãng lai.
- Tách first-touch, last-touch và cohort attribution.

### Giai đoạn 3 — Đưa nghiệp vụ ra khỏi code

- Quản lý source alias, nhóm sản phẩm và dịch vụ mồi trong `DANH_MỤC`.
- Thêm version và ngày hiệu lực cho mapping.
- Cho phép nghiệp vụ cập nhật quy tắc mà không deploy code.

### Giai đoạn 4 — Scale hạ tầng và analytics

Khi Google Sheets không còn phù hợp:

- Chuyển raw và marts sang BigQuery/data warehouse.
- Ingest incremental, partition theo ngày và cluster theo SĐT chuẩn hóa.
- Tách staging, core model và marts bằng data contract.
- Bổ sung lineage, metric definitions và alerting tập trung.
- Mở rộng retention cohort, lead scoring, forecast và phân tích năng suất sales.

Mọi mở rộng phải giữ nguyên nguyên tắc: metric ở đúng grain, có test, có DQ và
không để BI tool tự suy diễn lại logic nghiệp vụ.
