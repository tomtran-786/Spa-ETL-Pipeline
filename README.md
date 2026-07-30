# Phun Xăm Vic — Sales & Marketing Data Pipeline

Pipeline hợp nhất dữ liệu lead, lịch hẹn, hóa đơn KiotViet và chi phí quảng cáo
thành các bảng đã tính sẵn cho Looker Studio. Hệ thống trả lời bốn nhóm câu hỏi:

- Phễu `Inbox → Có SĐT → Đặt lịch → Ra đơn`
- Doanh thu và hiệu quả theo kênh
- CLV, tỷ lệ quay lại và cohort khách hàng
- Hiệu quả dịch vụ mồi: bán chéo cùng ngày và upsell khi khách quay lại

Pipeline chạy bằng Python/pandas trên GitHub Actions; Apps Script phụ trách nhập
dữ liệu, kiểm tra ngay trên Google Sheets và theo dõi job hằng ngày.

## Trạng thái hiện tại

Lần đối chiếu trực tiếp gần nhất: **30/07/2026 14:59 (Asia/Ho_Chi_Minh)**.

| Chỉ số trên backend Sheets | Giá trị |
|---|---:|
| Dòng trong tab `LEAD` | **2.426** |
| Phễu | **2.367 → 1.267 → 295 → 183** |
| Tỷ lệ chốt trên inbox | **7,73%** |
| Hóa đơn unique trong cửa sổ phân tích | **710** |
| Doanh thu | **2.552.689.000đ** |
| Trạng thái pipeline | **Đang chạy bình thường** |

Ngày 30/07/2026, tab `LEAD` đã được đối chiếu lại với
`output/LEAD_da_chuyen.csv`: bổ sung 4 lead còn thiếu, giữ nguyên 5 dòng đã được
chuẩn hóa ngày trống thành `01/01/2026`, và không phục hồi 13 dòng hoàn toàn
rỗng của file cũ. Sau chuẩn hóa, hai nguồn khớp theo multiset.

> **Không dùng `2.380 → 1.274 → 303 → 186` để xác nhận backend Sheets.**
> Đây là golden baseline của bộ file local cũ. Backend local còn đọc file lịch
> hẹn riêng, còn Sheets chỉ đọc cột `NGÀY HẸN` trong tab `LEAD`; dữ liệu local
> cũng từng chứa các dòng rỗng đã bị loại khi migrate. Hai backend không được
> kỳ vọng khớp toàn bộ phễu. Doanh thu, số hóa đơn, `DIM_KHACH` và
> `FUNNEL_MOI` mới là các mốc đối chiếu chặt giữa hai backend.

### Việc còn mở

- 35 lead mang ngày `19/01/2025`, nghi gõ nhầm năm nhưng chưa được phép tự sửa.
- Tab `CHI_PHÍ_QC` đang chứa **145.920.000đ chi phí mô phỏng**; CPL, CAC và ROAS
  chưa được dùng như số vận hành thật.
- Các scorecard Looker phải lấy từ bảng `KPI`, không cộng tỷ số từ
  `HIEU_QUA_KENH`. Xem [docs/LOOKER.md](docs/LOOKER.md).
- Hóa đơn mới nhất trong kho đang cũ; DQ sẽ tiếp tục cảnh báo cho tới khi có
  export KiotViet mới.

## Tài liệu

| Nhu cầu | Tài liệu |
|---|---|
| Cài đặt Google Sheets, Drive và Apps Script lần đầu | [apps_script/HUONG_DAN_CAI_DAT.md](apps_script/HUONG_DAN_CAI_DAT.md) |
| Vận hành, nhập dữ liệu và xử lý cảnh báo | [RUNBOOK.md](RUNBOOK.md) |
| Cấu hình nguồn dữ liệu và biểu đồ Looker Studio | [docs/LOOKER.md](docs/LOOKER.md) |
| Bối cảnh kỹ thuật và các bẫy dữ liệu đã gặp | [AGENTS.md](AGENTS.md) |

## Chạy local

Yêu cầu Python 3.12.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Chạy test:

```bash
python -m pytest tests/ -q
```

Chạy pipeline bằng file local:

```bash
python -m pxv.run_daily
```

Kết quả được ghi vào `output/PXV_DASHBOARD_DATA.xlsx`.

Chạy với Google Sheets:

```bash
PXV_BACKEND=sheets python -m pxv.run_daily
```

Backend Sheets cần `GCP_SA_KEY` và ba biến `PXV_SHEET_*`; xem mục
[Cấu hình triển khai](#cấu-hình-triển-khai).

> Dữ liệu thật chứa tên và số điện thoại khách hàng, không nằm trong git. Test
> dùng fixture bịa nên chạy được ngay sau khi clone.

## Mô hình nghiệp vụ

```text
Khách inbox  →  Có SĐT  →  Đặt lịch  →  Ra đơn
    [F]1         [F]2        [F]3         [F]4
```

Các nguồn được nối qua số điện thoại đã chuẩn hóa:

| Nguồn | Grain | Vai trò |
|---|---|---|
| Tab `LEAD` | Một lần khách inbox | Ngày lead, nguồn, nội dung quan tâm, sales phụ trách |
| Cột `NGÀY HẸN` | Một lịch hẹn | Xác định bước đặt lịch trên backend Sheets |
| `INVOICES_RAW` | Một dòng mặt hàng | Hóa đơn, dịch vụ và doanh thu KiotViet |
| `CHI_PHÍ_QC` | Tháng × kênh × bài quảng cáo | CPL, CAC và ROAS |
| `PANCAKE_RAW` | Một hội thoại có SĐT | Nguồn bổ sung SĐT, mặc định tắt |

KiotViet biết khách đã mua nhưng không biết họ đến từ kênh nào. Sheet sales biết
khách đã hỏi nhưng không biết họ có mua hay không. SĐT là khóa nối hai phía;
lead không có SĐT vẫn được giữ trong F1 nhưng không thể quy kết doanh thu.

## Kiến trúc

```text
PXV_NHẬP_LIỆU                  Google Drive
  LEAD                           KiotViet_Drop
  DANH_MỤC                       Pancake_Drop
  CHI_PHÍ_QC                          │
       │                     Apps Script kiểm tra/nạp
       │                              │
       └──────────────┬───────────────┘
                      ↓
                    PXV_KHO
              INVOICES_RAW / PANCAKE_RAW
                      │
                      ↓
      GitHub Actions — 06:15 hằng ngày hoặc chạy tay
        pytest → run_daily → quality checks → ghi Sheets
                      │
                      ↓
              PXV_DASHBOARD_DATA
                      │
                      ↓
                 Looker Studio

Apps Script watchdog chạy 09:00 để phát hiện pipeline im lặng.
```

Apps Script xử lý phần gắn với giao diện Sheets: menu vận hành, `onEdit`, nạp
file Drive và watchdog. Python giữ toàn bộ logic tính toán có test. Cách chia
này tránh viết lại hai bản logic nghiệp vụ bằng hai ngôn ngữ.

## Luồng xử lý

1. Đọc lead, lịch hẹn, hóa đơn và chi phí từ backend đã chọn.
2. Chuẩn hóa SĐT, tiền, ngày và schema.
3. Dựng `MASTER`, phân nhóm MECE và cờ phễu.
4. Dựng các mart cho CLV, dịch vụ mồi, chuỗi thời gian, hiệu quả kênh và KPI.
5. Chạy DQ; lỗi nghiêm trọng làm job dừng thay vì xuất số sai.
6. Ghi 9 bảng ra Excel local hoặc `PXV_DASHBOARD_DATA`.

## Bảng đầu ra

| Bảng | Mỗi dòng là | Dùng để trả lời |
|---|---|---|
| `MASTER` | Một cặp SĐT × hóa đơn | Doanh thu, phễu, sản phẩm, phân nhóm MECE |
| `DIM_KHACH` | Một khách có SĐT | CLV, cohort, số lần mua, khách quay lại |
| `FUNNEL_MOI` | Một khách mua dịch vụ mồi | Bán chéo cùng ngày và upsell 30/60/90 ngày |
| `FACT_DAILY` | Ngày × kênh | Biểu đồ lead, doanh thu và hóa đơn theo thời gian |
| `FUNNEL_DAILY` | Ngày × kênh × bước | Native Funnel chart có filter ngày/kênh |
| `HIEU_QUA_KENH` | Tháng × kênh | Phân tích cohort marketing theo tháng |
| `KPI` | `TỔNG` hoặc một kênh | Scorecard CPL, CAC, ROAS, CLV và tỷ lệ chuyển đổi |
| `DQ_STATUS` | Một phép kiểm | Mốc chạy, cảnh báo và trạng thái xanh/đỏ |
| `CẦN_SỬA` | Một dòng dữ liệu nghi sai | Danh sách cần sửa tại nguồn |

### Vì sao phải có các mart riêng

`MASTER` có grain SĐT × hóa đơn. Khách mua năm lần xuất hiện năm dòng, nên
`AVG(CLV)` hoặc tỷ lệ upsell tính trực tiếp trên đó sẽ sai mẫu số.
`DIM_KHACH` và `FUNNEL_MOI` giải quyết vấn đề này trước khi đưa sang Looker.

Tương tự, `HIEU_QUA_KENH` có grain tháng × kênh. Looker cộng `ROAS`, `CAC` hoặc
`CPL` qua nhiều tháng sẽ cho kết quả vô nghĩa. `KPI` tính lại tử số và mẫu số
đúng trọng số rồi mới xuất một dòng cho từng phạm vi.

## Các quy tắc bảo toàn tính đúng

### Số điện thoại

- Việt Nam → `0XXXXXXXXX`
- Quốc tế → `+XXXX`
- Rỗng, `"0"` hoặc rác → `None`
- Python (`pxv/clean.py`) và Apps Script (`IngestPancake.gs`) phải cho cùng kết quả

Không được dùng `"0"` làm khóa join: KiotViet dùng giá trị này khi không có SĐT,
nên nhiều khách khác nhau sẽ bị gộp thành một.

### Hóa đơn

- `Khách cần trả` là tổng hóa đơn lặp trên từng dòng mặt hàng.
- Doanh thu chỉ được giữ ở dòng đầu của mỗi `Mã hóa đơn`.
- Hóa đơn không có SĐT vẫn phải tính doanh thu và được xử lý tách khỏi merge.
- Mọi backend chuẩn hóa `Ngày HĐ` về ngày, bỏ phần giờ.
- Lịch sử hóa đơn hiện bắt đầu từ `01/01/2026`.

### Lead và ngày

- Chỉ ô `NGÀY` thật sự trống mới được gán `01/01/2026`.
- Ngày có chữ rác phải giữ trạng thái không đọc được để DQ cảnh báo.
- Ngày ghi thiếu năm trong `NGÀY HẸN` chỉ được suy khi có ngày lead làm mốc.
- Mọi dữ liệu ngày ghi ra ngoài dùng ISO `YYYY-MM-DD`.
- Ghi Google Sheets bằng `RAW`; cột định danh phải là text để không mất số 0 đầu.

### Phễu

- Chỉ khách từng inbox mới thuộc phễu marketing.
- Mỗi SĐT chỉ được đếm một lần ở mỗi bước.
- Lead không có SĐT vẫn tính F1, nhưng không thể đi tiếp sang F2–F4.
- Khách vãng lai được tính doanh thu nhưng không được làm F4 lớn hơn F3.

## Phân nhóm MECE

| Nhóm | Lead | Hẹn | Hóa đơn | Ý nghĩa |
|---|---:|---:|---:|---|
| 0 | Có, thiếu SĐT | Không | Không | Lead chưa cho SĐT |
| 1 | Không | Không | Có | Khách vãng lai |
| 2 | Có | Không | Không | Có SĐT, chưa hẹn và chưa mua |
| 3 | Có | Không | Có | Chốt thẳng không cần hẹn |
| 4 | Có | Có | Không | Đặt hẹn nhưng chưa ra đơn |
| 5 | Có | Có | Có | Đi đủ ba bước |
| 6 | Không | Có | Bất kỳ | Hẹn thiếu hồ sơ lead — lỗi dữ liệu |

## Data Quality

Lần chạy gần nhất xuất **24 dòng trạng thái**, gồm mốc chạy, kiểm nguồn, ngày,
SĐT, hóa đơn, phễu, MECE, danh mục, chi phí và drift so với lần trước.

Các lỗi có thể làm job dừng:

- Nguồn đầu vào rỗng hoặc sai schema
- Dấu hiệu ngày/tháng bị lật khi import
- Thiếu nguyên tháng hóa đơn ngoài khoảng trống đã biết
- Rớt hóa đơn hoặc doanh thu khi merge
- Một SĐT bị đếm nhiều lần trong phễu
- Phễu nở ở bước sau
- Có dòng không rơi vào nhóm MECE
- Số lead giảm hoặc doanh thu tháng đã đóng thay đổi vượt ngưỡng

Các cảnh báo hiện còn tồn tại nhưng không làm job dừng:

- 35 lead trước cửa sổ phân tích, cùng dồn vào `19/01/2025`
- 15 ô SĐT không đọc được
- Hóa đơn mới nhất đã cũ

Nguyên tắc của dự án: **thà giữ dashboard cũ kèm cảnh báo còn hơn ghi đè bằng
số mới nhưng sai**.

## Golden baseline và test

Khi có đủ bộ dữ liệu local cũ, `python -m pxv.run_daily` phải giữ các mốc:

| Chỉ số local golden | Giá trị |
|---|---:|
| Doanh thu | **2.552.689.000đ** |
| Hóa đơn unique | **710** |
| Phễu local | **2.380 → 1.274 → 303 → 186** |
| Tỷ lệ chốt | **7,82%** |

CLV và funnel dịch vụ mồi phụ thuộc `INVOICE_HISTORY_START`; đổi mốc lịch sử
thì các chỉ số này được phép thay đổi nhưng phải được giải thích.

```bash
python -m pytest tests/ -q
```

Trạng thái hiện tại: **153 passed** khi có
`output/Master_Pipeline_2026.xlsx`. File golden chứa PII nên không nằm trong git;
khi thiếu file, 7 kiểm tra golden tự skip và CI chạy phần còn lại.

Sau khi sửa bất kỳ file nào trong `pxv/`:

1. Chạy toàn bộ test.
2. Chạy pipeline local nếu có dữ liệu.
3. So lại doanh thu và hóa đơn với golden.
4. Nếu sửa chuẩn hóa SĐT, kiểm cả bản Python và Apps Script.

## Cấu trúc repository

```text
pxv/
  config.py      Cấu hình, đường dẫn và ngưỡng DQ
  schema.py      Hợp đồng cột đầu vào/đầu ra
  clean.py       Chuẩn hóa SĐT, tiền và ngày
  mappings.py    Quy tắc gom kênh, sản phẩm và alias
  ad_costs.py    Chuẩn hóa chi phí quảng cáo
  io_local.py    Backend file CSV/XLSX
  io_sheets.py   Backend Google Sheets
  pancake.py     Vá SĐT từ dữ liệu Pancake, mặc định tắt
  transform.py   MASTER, MECE và cờ phễu
  marts.py       Các mart phân tích và KPI
  quality.py     Kiểm chất lượng và drift
  run_daily.py   Entry point của pipeline

apps_script/     Menu, onEdit, ingest Drive, setup và watchdog
docs/            Hướng dẫn cấu hình Looker Studio
scripts/         Migrate lead, tạo chi phí mô phỏng, dọn lịch sử PII
tests/           Unit/integration tests dùng fixture bịa
state/           Dấu hoạt động do workflow hằng ngày cập nhật
```

## Nguồn dữ liệu local

Đặt các file sau ở thư mục gốc và không commit:

| File | Bắt buộc | Nội dung |
|---|---:|---|
| `Sales_Marketing dataset - SALE T1-2-3_2026.csv` | Có | Lead từ sheet sales cũ |
| `ĐĂT HẸN .csv` | Có | Lịch hẹn local bổ sung |
| `Doanh thu T11.2025 đến 25.02.xlsx` | Có | Hóa đơn KiotViet |
| `chi_phi_qc.csv` | Không | `tháng, kênh, mã bài QC, chi phí` |
| File Pancake | Không | Chỉ đọc khi bật `PXV_PANCAKE=1` |

Chuyển file lead cũ sang schema 17 cột:

```bash
python scripts/migrate_lead_csv.py <file-nguon.csv>
```

Script tạo cả CSV có BOM và XLSX. Khi import vào Google Sheets, ưu tiên XLSX để
tránh locale tự lật ngày/tháng.

## Cấu hình triển khai

GitHub Actions cần:

| Loại | Tên | Nội dung |
|---|---|---|
| Secret | `GCP_SA_KEY` | JSON Service Account |
| Variable | `PXV_SHEET_NHAP_LIEU` | ID file nhập liệu |
| Variable | `PXV_SHEET_KHO` | ID file kho |
| Variable | `PXV_SHEET_DASHBOARD` | ID file đầu ra |

Workflow `.github/workflows/daily.yml` chạy theo ba cách:

- Cron `06:15` hằng ngày theo giờ Việt Nam
- `workflow_dispatch` từ GitHub
- `repository_dispatch` từ menu **🔄 PXV → Chạy lại pipeline ngay**

Sau job thành công, workflow cập nhật `state/last_run.txt` để scheduled workflow
không bị GitHub tự tắt do repository không có hoạt động.

Các biến tùy chọn:

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `PXV_BACKEND` | `local` | Chọn `local` hoặc `sheets` |
| `PXV_WINDOW_START` | `2026-01-01` | Ngày bắt đầu cửa sổ phân tích |
| `PXV_INVOICE_HISTORY_START` | `2026-01-01` | Mốc lịch sử hóa đơn |
| `PXV_PANCAKE` | tắt | Đặt `1` để bật vá SĐT từ Pancake |

## Looker Studio

Mỗi câu hỏi nên đọc từ đúng một bảng; tránh Blend nếu pipeline đã xuất mart phù
hợp.

- Scorecard tổng và theo kênh: dùng `KPI`
- Biểu đồ theo ngày: dùng `FACT_DAILY`
- Funnel có filter ngày/kênh: dùng `FUNNEL_DAILY`
- CLV và retention: dùng `DIM_KHACH`
- Dịch vụ mồi: dùng `FUNNEL_MOI`
- Trạng thái dữ liệu: dùng `DQ_STATUS`

Không đặt filter ngày lên `KPI`, `DIM_KHACH` hoặc `FUNNEL_MOI` vì các bảng này
đã được tính ở grain riêng. Chi tiết xem [docs/LOOKER.md](docs/LOOKER.md).

> **Cảnh báo:** chi phí hiện tại là dữ liệu mô phỏng được sinh bởi
> `scripts/generate_toy_ad_costs.py`. Không dùng CPL, CAC hoặc ROAS để ra quyết
> định kinh doanh cho tới khi `CHI_PHÍ_QC` được thay bằng chi phí thật.

## Giới hạn dữ liệu đã biết

| Vấn đề | Ảnh hưởng |
|---|---|
| Mất toàn bộ hóa đơn T12/2025 | Không thể khôi phục; biểu đồ phải để khoảng trống, không coi là doanh thu 0 |
| Khoảng 46% lead không có SĐT | Không nối được với hóa đơn và không biết họ có mua hay không |
| Khoảng 75% doanh thu không quy được về kênh | Không dùng doanh thu toàn bộ làm tử số ROAS theo kênh |
| 35 lead mang ngày `19/01/2025` | Đang bị loại khỏi cửa sổ; chờ xác nhận trước khi sửa |
| Lịch sử hóa đơn bắt đầu `01/01/2026` | CLV hiện là giá trị trong kỳ, chưa phải lifetime value trọn đời |
| Chi phí quảng cáo là mô phỏng | CPL, CAC và ROAS chỉ dùng để kiểm thử dashboard |

## Bảo mật dữ liệu

- Không commit `*.csv`, `*.xlsx`, `output/` hoặc bất kỳ export chứa PII.
- Test chỉ dùng tên và SĐT bịa.
- Service Account chỉ được chia sẻ đúng các spreadsheet cần thiết.
- Khi ghi Sheets, dùng `RAW` và giữ cột định danh ở dạng text.
- Repository từng được rewrite lịch sử để xóa PII; xóa file ở commit mới không
  đủ nếu dữ liệu đã xuất hiện trong lịch sử git.

Nếu lỡ commit dữ liệu khách, dừng push và dùng
`scripts/purge_pii_history.sh`; sau đó quét lại cả code, test, comment và
docstring trước khi xuất bản lịch sử mới.
