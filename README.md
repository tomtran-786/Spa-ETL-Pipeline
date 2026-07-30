# Phun Xăm Vic — Pipeline phân tích Sales & Marketing

Gộp dữ liệu tư vấn của sales, lịch hẹn và hóa đơn KiotViet thành các bảng phục vụ dashboard quản trị: doanh thu, phễu chuyển đổi, hiệu quả kênh quảng cáo, CLV và funnel dịch vụ mồi.

> **Cài đặt lần đầu**: [apps_script/HUONG_DAN_CAI_DAT.md](apps_script/HUONG_DAN_CAI_DAT.md)
> **Vận hành hằng ngày** (export file, xử lý cảnh báo, đọc số): [RUNBOOK.md](RUNBOOK.md)
> **Dựng dashboard**: [docs/LOOKER.md](docs/LOOKER.md) — công thức KPI đúng và các
> bẫy khi Looker gộp/lọc lại số pipeline đã tính.
> Tài liệu này dành cho người sửa code.

---

## Chạy thử

```bash
pip install -r requirements.txt
```

```bash
python -m pxv.run_daily
```

```bash
python -m pytest tests/ -v
```

Mặc định đọc file trên máy, kết quả ghi ra `output/PXV_DASHBOARD_DATA.xlsx`.

> ⚠️ **File dữ liệu không nằm trong git** vì chứa tên và số điện thoại khách hàng. Muốn chạy `run_daily` ở máy thì phải tự đặt các file nguồn vào thư mục gốc — xem [Nguồn dữ liệu](#nguồn-dữ-liệu-để-chạy-local). Test dùng dữ liệu bịa nên chạy được ngay sau khi clone.

---

## Nghiệp vụ

```
Khách nhắn tin  →  Sales xin SĐT  →  Đặt hẹn  →  Đến làm dịch vụ  →  Hóa đơn
    [F]1             [F]2            [F]3                             [F]4
```

Ba nguồn rời nhau, nối qua **số điện thoại đã chuẩn hóa**:

| Nguồn | Cho biết | Ai ghi |
|---|---|---|
| Sheet LEAD | Ai hỏi, hỏi gì, đến từ kênh nào | Sales |
| Cột `NGÀY HẸN` trong LEAD | Ai đã đặt lịch | Sales |
| KiotViet | Ai đã mua, mua gì, bao nhiêu tiền | Phần mềm bán hàng |

Bài toán lõi: KiotViet biết ai **mua** nhưng không biết họ đến từ đâu; sheet sales biết ai **hỏi** nhưng không biết có mua không. Chỉ số điện thoại nối được hai bên.

---

## Kiến trúc

```
Google Sheets          Drive/KiotViet_Drop      Drive/Pancake_Drop
  (sales nhập)          (export CSV tay)         (export Excel tay)
       │                        │                        │
       │              Apps Script kiểm file trước khi nạp
       │                        ↓                        ↓
       │              PXV_KHO: INVOICES_RAW      PXV_KHO: PANCAKE_RAW
       │              (chỉ thêm, không ghi đè)
       └────────────────────────┬────────────────────────┘
                                ↓
                  GitHub Actions — cron 06:15 hằng ngày
                  pytest → pxv.run_daily → kiểm chất lượng
                                ↓
                  PXV_DASHBOARD_DATA (9 bảng) → Looker Studio
                                ↓
                  Apps Script watchdog 09:00 canh pipeline
```

Chi phí hạ tầng **0đ/tháng**, không lớp nào cần thẻ tín dụng.

**Vì sao chia đôi Apps Script / GitHub Actions.** Apps Script làm phần buộc phải nằm trong Sheets — báo lỗi ngay lúc sales gõ, quét thư mục Drive, canh chừng — và không có key nào để rò rỉ. GitHub Actions chạy phần tính toán, giữ nguyên code pandas đã có test; viết lại logic sang JavaScript thì dễ lệch số.

---

## Cấu trúc code

```
pxv/
  config.py     Đường dẫn, cửa sổ thời gian, ngưỡng cảnh báo
  schema.py     Header kỳ vọng — lệch là dừng, không tính ra số sai
  clean.py      Chuẩn hóa SĐT, tiền, ngày
  mappings.py   Quy tắc nghiệp vụ dạng BẢNG DỮ LIỆU (kênh, sản phẩm, alias)
  ad_costs.py   Chuẩn hóa bảng chi phí quảng cáo
  io_local.py   Đọc file trên máy
  io_sheets.py  Đọc/ghi Google Sheets — cùng interface với io_local
  transform.py  build_master(): gộp 3 nguồn, phân nhóm MECE, cờ phễu
  marts.py      DIM_KHACH, FUNNEL_MOI, FACT_DAILY, HIEU_QUA_KENH, KPI
  quality.py    21 phép kiểm, cho pipeline DỪNG khi dữ liệu sai
  run_daily.py  Điểm chạy duy nhất

apps_script/    8 file .gs dán vào Google Sheets
                → HUONG_DAN_CAI_DAT.md: hướng dẫn cài từng bước
tests/          153 test, dùng dữ liệu bịa
scripts/        purge_pii_history.sh · migrate_lead_csv.py
spa.ipynb       Sổ tay khám phá ad-hoc, import từ pxv
```

Đổi nguồn dữ liệu bằng biến môi trường:

```bash
PXV_BACKEND=sheets python -m pxv.run_daily
```

---

## Bảng đầu ra

| Bảng | Mỗi dòng là | Trả lời |
|---|---|---|
| `MASTER` | 1 cặp (SĐT × hóa đơn) | Doanh thu, số lead, tỷ lệ chốt, sản phẩm, MECE |
| `DIM_KHACH` | 1 khách | CLV theo phân khúc, khách quay lại, cohort |
| `FUNNEL_MOI` | 1 khách mua dịch vụ mồi | Bán chéo cùng ngày vs upsell 30/60/90 ngày |
| `FACT_DAILY` | 1 cặp (ngày × kênh) | Biểu đồ theo thời gian |
| `FUNNEL_DAILY` | 1 cặp (ngày × kênh × bước) | Native Funnel chart có filter ngày/kênh |
| `HIEU_QUA_KENH` | 1 cặp (tháng × kênh) | CPL, CAC, ROAS, CLV:CAC theo tháng |
| `KPI` | 1 phạm vi (`TỔNG` + mỗi kênh) | **Mọi thẻ số trên dashboard** |
| `DQ_STATUS` | 1 phép kiểm | Băng "cập nhật lúc", đèn đỏ/xanh |

**Vì sao tính sẵn CLV và funnel mồi ở pipeline thay vì để Looker tính.** `MASTER` có mỗi dòng là một cặp (SĐT × hóa đơn), nên khách mua 5 lần chiếm 5 dòng. Trên cấu trúc đó `AVG(CLV)` sẽ chia cho mẫu số bị đếm 5 lần, còn tỷ lệ upsell thì cần so ngày mua đầu với các lần sau — Looker không làm được. Nguyên tắc: mỗi câu hỏi trả lời từ **một** bảng, không dùng Blend.

**Vì sao có thêm bảng `KPI`.** Cùng lý do, ở một dạng khác. `HIEU_QUA_KENH` giữ CPL/CAC/ROAS ở grain (tháng × kênh); Looker mặc định `SUM`, mà cộng tỷ số thì vô nghĩa — dashboard T7/2026 hiện ROAS 27,19 trong khi đúng là 4,18, và CAC sai 16 lần. `KPI` gộp sẵn với trọng số đúng nên `SUM` hay `AVG` trên một dòng đều ra cùng kết quả. Xem [docs/LOOKER.md](docs/LOOKER.md).

---

## Phân nhóm MECE

Vét cạn 8 tổ hợp của (Lead, Hẹn, Hóa đơn):

| Nhóm | Lead | Hẹn | HĐ | Ý nghĩa |
|---|---|---|---|---|
| 0 | ✅ | ❌ | ❌ | Nhắn tin nhưng không cho SĐT |
| 1 | ❌ | ❌ | ✅ | Vãng lai — mua mà chưa từng nhắn tin |
| 2 | ✅ | ❌ | ❌ | Có SĐT, chưa hẹn, chưa mua |
| 3 | ✅ | ❌ | ✅ | Chốt thẳng không cần hẹn |
| 4 | ✅ | ✅ | ❌ | Đặt hẹn nhưng rớt |
| 5 | ✅ | ✅ | ✅ | Đủ 3 bước |
| 6 | ❌ | ✅ | — | Có hẹn nhưng thiếu hồ sơ lead — **lỗi nhập liệu**, nên gần 0 |

---

## Quyết định thiết kế

**Phễu chỉ tính trên khách từng inbox.** Khách vãng lai chưa nhắn tin nên không thuộc phễu marketing — để chung sẽ làm bước sau lớn hơn bước trước, tức phễu nở ra, vô lý. Doanh thu vãng lai đếm ở cột riêng.

**Mỗi SĐT chỉ đếm một lần ở mỗi bước phễu.** Khách mua nhiều hóa đơn chiếm nhiều dòng; cờ phễu chỉ bật ở dòng đầu tiên.

**Số quốc tế được giữ, không bỏ.** Có khách Việt kiều xuất hiện ở cả lead lẫn hóa đơn. Số VN chuẩn hóa thành `0XXXXXXXXX`, số quốc tế thành `+XXXX`, rác thành `None`.

**Hóa đơn không có SĐT vẫn tính doanh thu.** KiotViet ghi `0` khi không có số — đó là tiền thật, chỉ là không join được với lead. Bỏ đi sẽ mất 81 triệu trong cửa sổ T1–T2/2026. Ngược lại, coi `"0"` là SĐT hợp lệ (như code cũ) thì hàng chục khách khác nhau bị gộp làm một người.

**Không tự đoán năm khi ngày trông sai.** Code cũ ép `2025-Q1` thành `2026` để vá 35 dòng gõ nhầm; sang 2027 quy tắc đó sẽ âm thầm bóp méo dữ liệu thật. Giờ ngày nghi sai được đẩy vào bảng `CẦN_SỬA` cho người xử lý tại nguồn.

**Quy tắc nghiệp vụ nằm trong `mappings.py` dạng bảng dữ liệu**, không phải if-chain. Danh sách dịch vụ mồi và cách gom kênh thay đổi theo chiến dịch nên người nghiệp vụ phải sửa được.

**Pipeline chủ động dừng khi dữ liệu sai.** GitHub chỉ gửi mail khi job crash, nên phải crash. Chính sự im lặng đã làm mất trọn tháng 12/2025 mà 7 tháng sau mới phát hiện.

---

## Giới hạn dữ liệu đã biết

Đọc kỹ trước khi kết luận bất cứ điều gì từ dashboard.

| Vấn đề | Ảnh hưởng |
|---|---|
| **T12/2025 mất toàn bộ hóa đơn** | Không khôi phục được. Biểu đồ theo thời gian phải vẽ khoảng trống có nhãn, **không phải doanh thu = 0** |
| **~46% lead không có SĐT** | Không biết họ có mua không. Phần lớn là khách hỏi giá rồi im, không hẳn lỗi sales |
| **~75% doanh thu không quy được về kênh** | Khách vãng lai không có hồ sơ lead. **Đừng dùng ROAS ở đây làm mẫu số cho toàn bộ doanh thu** |
| **35 lead ghi 19/01/2025** | Cùng một ngày, trong file lẽ ra là 2026 — nghi gõ nhầm năm hàng loạt, đang chờ xác nhận |
| **CLV mới có ~4 tháng dữ liệu** | Là giá trị *trong kỳ*, chưa phải giá trị trọn đời |

---

## Phát triển

**Golden file test.** `tests/test_golden.py` đối chiếu output với `output/Master_Pipeline_2026.xlsx` — bản đã nghiệm thu thủ công. Doanh thu và số hóa đơn phải khớp **tuyệt đối**; lead giảm đúng 35 dòng (do bỏ quy tắc ép năm) chứ không phải con số nào khác. File golden chứa dữ liệu khách nên nằm ngoài git, test tự bỏ qua khi không có.

**Chuẩn hóa SĐT tồn tại hai bản** — Python (`pxv/clean.py`) và JavaScript (`apps_script/IngestPancake.gs`). Lệch nhau là join hỏng âm thầm. Sửa một bên thì phải sửa bên kia và đối chiếu lại trên dữ liệu thật.

**Dữ liệu khách không bao giờ vào git.** `.gitignore` chặn `*.csv`, `*.xlsx`, `output/`. Test dùng dữ liệu bịa. Nếu lỡ commit, dùng `scripts/purge_pii_history.sh` — và nhớ rằng **xóa file thôi chưa đủ**: số điện thoại và tên khách có thể nằm trong comment, docstring và test, nên phải quét cả nội dung.

---

## Nguồn dữ liệu để chạy local

Đặt vào thư mục gốc, không commit:

| File | Nội dung |
|---|---|
| `Sales_Marketing dataset - SALE T1-2-3_2026.csv` | Lead từ sheet sales |
| `ĐĂT HẸN .csv` | Lịch hẹn |
| `Doanh thu T11.2025 đến 25.02.xlsx` | Hóa đơn KiotViet |
| `chi_phi_qc.csv` *(tùy chọn)* | Chi phí quảng cáo: `tháng, kênh, mã bài QC, chi phí` |
