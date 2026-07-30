# Cấu hình Looker Studio

Pipeline tính sẵn mọi con số rồi mới đẩy sang Looker. Vì thế phần lớn lỗi
dashboard **không nằm ở dữ liệu** mà ở cách Looker gộp và lọc lại số đã tính.

File này ghi lại những chỗ đã sai thật, kèm cách làm đúng. Đọc kèm
[AGENTS.md](../AGENTS.md) (bẫy dữ liệu) và [README.md](../README.md) (kiến trúc).

> Bản kiểm ngày 30/07/2026 (đối chiếu trực tiếp với `PXV_NHẬP_LIỆU` và
> `PXV_DASHBOARD_DATA` tải về từ Sheets): **7/9 thẻ KPI sai số**, do **hai**
> nguyên nhân độc lập nhau:
>
> 1. **Dữ liệu vào sai** — tab `LEAD` bị lật ngày/tháng (mục 1) và kho hóa đơn
>    thiếu 2 tháng lịch sử (mục 3). Pipeline tính đúng trên dữ liệu sai.
> 2. **Looker gộp/lọc lại sai** — cộng các tỷ số với nhau (mục 4).
>
> Sửa Looker mà không sửa nguồn thì số vẫn sai. Làm theo thứ tự mục 1 → 3 → 4.

---

## 1. Trường ngày — chỗ đã gây thiệt hại lớn nhất

Pipeline ghi ngày dạng **ISO `YYYY-MM-DD`**, và ghi bằng `value_input_option='RAW'`
nên trong Sheets nó là **chữ, không phải ô ngày**.

Trong Looker: tạo field kiểu **Date** với format **`YYYY-MM-DD`**. Đừng để
`Auto`, đừng chọn `MM/DD/YYYY`.

**Đây không phải rủi ro lý thuyết — tab `LEAD` đang bị lỗi này.** Đo trên bản
tải về ngày 30/07/2026: **1.012/2.426 dòng (42%)** rơi sai tháng.

Phân bố ngày trong tab `LEAD`:

| Tháng | Số lead | Ngày trong tháng xuất hiện |
|---|---|---|
| 2026-01 | 886 | 1, 2, **13→31** ← thiếu sạch ngày 3–12 |
| 2026-02 | 486 | 1, 2, **13→25** ← thiếu sạch ngày 3–12 |
| 2026-03 … 2026-12 | 1.012 | **chỉ có ngày 1 và 2** |

Ngày > 12 không lật được nên nằm im; ngày ≤ 12 thì lật thành `tháng = ngày gốc,
ngày = tháng gốc` — mà tháng luôn ≤ 12, nên tất cả đậu ở ngày 1–2. Kết quả vẫn
là ngày hợp lệ, mắt thường không thấy.

Looker lọc 01/01–28/02 nên chỉ còn `886 + 486` lead, và dashboard hiện **1.358**:

| | Lượng Lead | Có SĐT | Đặt lịch | Ra đơn |
|---|---|---|---|---|
| Đúng | **2.364** | 1.274 | 303 | 186 |
| Dashboard đang hiện | 1.358 | 708 | 184 | 110 |

Dấu hiệu trên biểu đồ theo thời gian: **khoảng trống đúng từ ngày 3 đến ngày 12
của mỗi tháng**, và đỉnh biểu đồ thấp bất thường.

**Cách sửa:** import lại tab `LEAD` từ bản `.xlsx` do
`scripts/migrate_lead_csv.py` sinh ra (File → Import → *Replace data at selected
cell*, ô A2, **bỏ tick** "Convert text to numbers, dates and formulas"). Bản
`.xlsx` ghi ô ngày thật nên không qua bước đọc chuỗi, đúng dù locale nào.

⚠️ Tab `LEAD` hiện có **5 lead nhập tay ngày 28/07/2026** không nằm trong file
gốc. Import đè sẽ mất 5 dòng đó — chép ra trước, nhập lại sau.

**Tự kiểm sau mỗi lần import:** mở tab `LEAD`, lọc cột `NGÀY`. **Thấy dữ liệu
rơi vào tháng ngoài kỳ báo cáo, hoặc thấy tháng nào chỉ có ngày 1–2, là đã lật
— import lại.** Pipeline giờ cũng tự dừng khi gặp (`Nghi lật ngày/tháng`).

---

## 2. Kho hóa đơn trên Sheets đang THIẾU 2 THÁNG lịch sử

Nguyên nhân độc lập với mục 1, và là thứ làm hỏng toàn bộ trang Customer Value.

| | Kho hóa đơn | Khoảng thời gian |
|---|---|---|
| Chạy local (từ file KiotViet) | 1.013 dòng | **01/11/2025** → 25/02/2026 |
| Tab `INVOICES_RAW` trên Sheets | **711 dòng** | **04/01/2026** → 25/02/2026 |

Thiếu nguyên **T11/2025: 302 hóa đơn, 915.858.500đ**. (T12/2025 thì đã biết là
mất hẳn, xem `config.KNOWN_DATA_GAPS`.)

Doanh thu trong kỳ **không đổi** (2.552.689.000đ vẫn đúng) vì T11 nằm ngoài cửa
sổ phân tích. Nhưng `DIM_KHACH` và `FUNNEL_MOI` **cố ý** đọc toàn bộ lịch sử để
tính CLV và upsell, nên chúng lãnh trọn:

| Thẻ | Dashboard đang hiện | Đúng (có T11) | Vì sao |
|---|---|---|---|
| CLV trung bình | 5.417.514đ | **5.689.481đ** | mất 175 khách cohort T11/2025 |
| Tỷ lệ khách quay lại | 24,3% | **27,4%** | nhóm gắn bó lâu nhất bị cắt |
| Upsell 90 ngày | **7,0%** | **24,8%** | cohort T11 có tỷ lệ upsell 46,8% |
| Số khách mua mồi | 215 | **290** | |

Con số trên dashboard khớp **chính xác** với bảng trong sheet, không qua bộ lọc
nào — nên đừng đi tìm cấu hình Looker để sửa. **Phải nạp lại hóa đơn T11/2025
vào Drive/KiotViet_Drop.**

**Vì sao không phép kiểm nào bắt được:** `Thủng tháng hóa đơn` chỉ dò lỗ hổng
*giữa* tháng đầu và tháng cuối. Lịch sử bị cụt ở đầu thì không tạo ra lỗ nào để
dò. Mốc `Doanh thu tháng đã đóng` cũng vô hiệu — nó so với lần chạy trước, mà
lần trước cũng đã cụt sẵn rồi.

---

## 3. Công thức KPI — không bao giờ SUM/AVG lên cột tỷ lệ

`HIEU_QUA_KENH` có sẵn `CPL`, `CAC`, `ROAS`, `tỷ_lệ_chốt_%` **tính theo từng
dòng (tháng × kênh)**. Looker mặc định `SUM`, mà cộng tỷ số thì vô nghĩa.

Đã đo trên dashboard thật:

| Thẻ | Đang hiện | Đúng | Sai vì |
|---|---|---|---|
| Trung bình tỷ lệ chốt | 10,0% | **7,87%** | `AVG(tỷ_lệ_chốt_%)` |
| ROAS | 8,61 | **4,18** | `SUM(ROAS)` — bằng đúng tổng 3 cột trong chart bên dưới |
| CAC | 12.616.529đ | **784.516đ** | `SUM(CAC)` — sai **16 lần** |

Luôn tính lại từ tổng, bằng calculated field trong Looker:

```
Tỷ lệ chốt  = SUM(có_đơn) / SUM(lead)          -- nguồn FACT_DAILY
CPL         = SUM(chi phí) / SUM(lead)         -- nguồn HIEU_QUA_KENH
CAC         = SUM(chi phí) / SUM(khách_mua)
ROAS        = SUM(doanh_thu) / SUM(chi phí)
```

**Cấm:**
- `SUM(ROAS)`, `SUM(CAC)`, `SUM(CPL)`, `AVG(CPL)`, `AVG(tỷ_lệ_chốt_%)`
- **Mọi pie/donut vẽ trên một tỷ số.** Donut "CAC theo Kênh" hiện đang chia
  phần trăm của CAC — không có ý nghĩa toán học, và nó nói Tiktok chiếm 58,7%
  CAC trong khi bubble chart ngay cạnh cho thấy Tiktok có CPL thấp nhất và tỷ
  lệ chốt cao nhất. Hai chart phủ định nhau.

Lưu ý: `_chia()` trong `marts.py` trả **NaN chứ không phải 0** khi mẫu số bằng 0
— cố ý, để Looker hiểu là "chưa có dữ liệu" thay vì "hiệu quả bằng 0". Đừng để
`AVG` kéo nhóm null xuống 0.

---

## 4. Bảng nào được lọc theo ngày, bảng nào không

| Bảng | Lọc theo ngày? | Ghi chú |
|---|---|---|
| `MASTER` | ✅ | dimension: `Ngày Lead` hoặc `Ngày HĐ` — chọn một, đừng trộn |
| `FACT_DAILY` | ✅ | xem cảnh báo mục 5 |
| `FUNNEL_DAILY` | ✅ | dùng cho native Funnel chart |
| `DIM_KHACH` | ❌ **KHÔNG** | |
| `FUNNEL_MOI` | ❌ **KHÔNG** | |
| `HIEU_QUA_KENH` | — | `tháng` là **chuỗi** `"YYYY-MM"`, Looker không lọc ngày được |

**Vì sao cấm lọc `DIM_KHACH` và `FUNNEL_MOI`:** CLV và tỷ lệ upsell được tính
trên **toàn bộ lịch sử mua**, cố ý lấy cả hóa đơn trước cửa sổ phân tích. Áp
date range của báo cáo lên chúng là phá đúng thiết kế đó — cắt mất cohort cũ,
tức nhóm gắn bó lâu nhất và có tỷ lệ mua lại cao nhất.

Đây là quy tắc **phòng ngừa**, chưa phải lỗi đang xảy ra: bản kiểm 30/07/2026
cho thấy Looker **không** lọc hai bảng này. Số CLV/upsell sai là do kho hóa đơn
thiếu lịch sử (mục 2), không phải do bộ lọc.

Muốn xem CLV theo kỳ thì lọc bằng `cohort_tháng` (dimension riêng), không phải
bằng date range của báo cáo.

---

## 5. `FACT_DAILY` trộn HAI trục thời gian trong cùng một cột `ngày`

| Cột | Trục thời gian |
|---|---|
| `lead`, `có_sđt`, `có_hẹn`, `có_đơn` | **ngày lead** |
| `doanh_thu`, `số_hóa_đơn` | **ngày hóa đơn** |

Trên dòng `ngày = 2026-01-15`: `có_đơn` nghĩa là "lead vào ngày 15/01 mà sau này
có đơn", còn `doanh_thu` nghĩa là "tiền thu được trong ngày 15/01". Hai thứ khác
nhau hoàn toàn.

**Đừng vẽ phễu và doanh thu trên cùng một trục thời gian.** Cần cả hai thì làm
hai chart riêng, ghi rõ trục của từng cái.

---

## 6. Bốn con số doanh thu — mỗi thẻ KPI phải ghi rõ nguồn

Workbook có bốn tổng doanh thu khác nhau, đều đúng, khác nhau ở **phạm vi**:

| Bảng | Phạm vi | Dùng khi | Giá trị (bản local đủ lịch sử) |
|---|---|---|---|
| `MASTER`, `FACT_DAILY` | trong cửa sổ phân tích | doanh thu kỳ báo cáo | 2.552.689.000đ |
| `DIM_KHACH` | trọn đời khách | CLV, phân khúc | 3.379.551.500đ |
| `DQ_STATUS` | các tháng đã đóng | mốc chống mất dữ liệu | 3.468.547.500đ |
| `HIEU_QUA_KENH` | chỉ phần **quy kết được về kênh** | ROAS, CAC | 610.372.500đ |

Không có nhãn nào trong workbook nói lên phạm vi, nên thẻ KPI **phải tự ghi**.
Một thẻ "Doanh thu" không kèm nguồn là một thẻ sai chờ ngày bị đọc nhầm.

⚠️ Ba con số cuối **hiện đang thấp hơn** trên Sheets vì kho hóa đơn thiếu
T11/2025 (mục 2). Chỉ số đầu — doanh thu trong kỳ — là không đổi. Dùng cột giá
trị này để đối chiếu sau khi nạp lại lịch sử.

---

## 7. 75,5% doanh thu KHÔNG quy kết được về kênh

| Kênh | Doanh thu | |
|---|---|---|
| **Vãng lai (không rõ nguồn)** | **1.927.694.500đ** | **75,5%** |
| Facebook | 415.830.500đ | 16,3% |
| Tiktok | 101.650.000đ | 4,0% |
| Còn lại | 107.514.000đ | 4,2% |

Khách vãng lai chưa từng inbox nên **không thuộc phễu marketing** (để chung thì
F4 > F3, phễu nở ra ở bước sau). Họ cũng không có `Ngày Lead`, nên **mọi bộ lọc
ngày dựa trên `Ngày Lead` đều loại họ đi** — đó là lý do chart "Doanh thu theo
kênh" hiện đang giấu mất 3/4 số tiền và làm Facebook trông như nguồn doanh thu
chính.

**Bắt buộc:** chart doanh thu theo kênh phải ghi tiêu đề *"chỉ phần quy kết được
— 75,5% doanh thu đến từ khách vãng lai không có hồ sơ lead"*. Và **không dùng
tổng doanh thu làm tử số ROAS** — ROAS theo kênh chỉ là **cận dưới**.

---

## 8. Chi phí quảng cáo hiện là SỐ MÔ PHỎNG

Dashboard đang hiện `Chi Phí Quảng Cáo = 145.920.000đ`. Con số này khớp **chính
xác** file `output/toy/chi_phi_qc_baseline.csv`, sinh bởi
`scripts/generate_toy_ad_costs.py` với CPL giả định (FB 70k / TikTok 55k / IG 90k).

`output/toy/scenario_manifest.csv` ghi rõ:

- `data_classification`: `TOY / SIMULATED — NOT ACTUAL MARKETING SPEND`
- `interpretation_limit`: doanh thu vẫn là lịch sử thật, nên **ROAS là chỉ số
  kịch bản, không phải kết quả đã đạt được**

Pipeline vận hành **không có** `chi_phi_qc.csv`, nên `HIEU_QUA_KENH` thật có
`chi phí = 0` toàn bộ và `CPL/CAC/ROAS = NaN` — DQ báo `Chi phí quảng cáo: chưa nhập`.

**Cho tới khi có chi phí thật:** trang Channel Performance phải có băng cảnh báo
"số liệu chi phí là mô phỏng cho case study". Đừng đưa trang này cho chủ spa xem
mà không có băng đó.

---

## 9. Upsell phải đọc theo cohort đã trưởng thành

`FUNNEL_MOI` dính **right-censoring**: khách mua dịch vụ mồi tháng gần nhất chưa
sống đủ 90 ngày để có cơ hội upsell. Gộp chung là kéo tỷ lệ xuống vô lý.

| Cohort mua mồi | Số khách | Upsell 90 ngày |
|---|---|---|
| T11/2025 | 77 | **46,8%** ← đã đủ chín |
| T1/2026 | 136 | 16,2% |
| T2/2026 | 77 | 18,2% ← chưa đủ 90 ngày |
| **Tổng pipeline** | 290 | **24,8%** |

Dashboard đang hiện **7,0%** vì **hai** lý do cộng dồn: kho hóa đơn thiếu hẳn
cohort T11/2025 (mục 2) — đúng cohort duy nhất đã đủ chín — và phần còn lại thì
dính right-censoring. Đọc con số đó sẽ kết luận dịch vụ mồi thất bại, trong khi
cohort đủ chín cho **46,8%**. Chênh lệch gấp **6,7 lần**.

**Cách làm đúng:** tách theo `ngày_mua_mồi` theo tháng, và **chỉ đọc tỷ lệ 90
ngày của các cohort cách ngày dữ liệu mới nhất ≥ 90 ngày.**

Hai lưu ý nữa:
- `upsell_30d/60d/90d` là **lồng nhau**, không phải bucket rời. Khách upsell
  ngày 20 sẽ `TRUE` ở cả ba. **Không cộng ba cột lại.**
- Cột tỷ lệ đang format 1 chữ số thập phân (`0,3` / `0,1` / `0,0`) — hai dòng có
  upsell thật đang hiển thị thành `0,0`. Đổi sang phần trăm, 1 chữ số.

---

## 10. Băng "dữ liệu tính đến ngày…"

`DQ_STATUS` có dòng `Chạy lúc` (mốc pipeline) và `Độ tươi hóa đơn` (hóa đơn mới
nhất). Đưa cả hai lên đầu mỗi trang.

Hiện tại: **dữ liệu dừng 25/02/2026, hôm nay 30/07/2026 — chênh 155 ngày.**
Dashboard không có băng nào nói điều đó, nên người xem đang đọc số 5 tháng cũ mà
tưởng là số hôm nay.

---

## 11. Vài lỗi lẻ đang có trên dashboard

- **Chart "CLV theo kênh tiếp cận" hỏng hẳn** — trục 0→1, không cột nào. Legend
  ghi `Trung bình Tổng doanh thu`, nhưng field đó **không tồn tại**; tên đúng là
  `tổng_doanh_thu` (snake_case, trong `DIM_KHACH`).
- **`DIM_KHACH` có 130/594 khách (21,9%) `Kênh Tiếp Cận` rỗng** — khách chỉ mua
  trước cửa sổ nên không có dòng trong `MASTER`. Looker sẽ âm thầm bỏ họ khỏi
  mọi chart chia theo kênh. Gộp thành nhóm "Không rõ" thay vì để null.
- **"Tỷ lệ hẹn 14,0%" ≠ "Có Đặt Lịch 13,55%"** của phễu ngay cạnh — hai thẻ trên
  cùng một trang mâu thuẫn nhau.
- **"Nhu cầu theo nhóm sản phẩm" dùng `[F] 1_Có Inbox`** trên `Phân loại sản phẩm`.
  Cột đó lấy `Tên hàng` (đã mua) rồi mới fallback sang `QUAN TÂM` (quan tâm lúc
  inbox) — trộn hai khái niệm. 326/2.364 rơi vào "Chưa rõ" nhưng chart không hiện.
- **Cờ `[F]` đã khử trùng theo SĐT** — `SUM([F] 4_Có Ra Đơn)` là **số KHÁCH ra
  đơn**, không phải số hóa đơn. Muốn đếm đơn thì dùng `số_hóa_đơn`.
- **Tên cột không nhất quán giữa các bảng.** `có_đơn` (FACT_DAILY) vs `khách_mua`
  (HIEU_QUA_KENH); `chi phí` có dấu cách; `SĐT` (DIM_KHACH) vs `SĐT Cuối` (MASTER);
  `Kênh Tiếp Cận` vs `kênh` (HIEU_QUA_KENH). Kiểm tên trước khi nối field.
