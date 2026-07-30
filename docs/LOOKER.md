# Cấu hình Looker Studio

Pipeline tính sẵn mọi con số rồi mới đẩy sang Looker. Vì thế phần lớn lỗi
dashboard **không nằm ở dữ liệu** mà ở cách Looker gộp và lọc lại số đã tính.

File này ghi lại những chỗ đã sai thật, kèm cách làm đúng. Đọc kèm
[AGENTS.md](../AGENTS.md) (bẫy dữ liệu) và [README.md](../README.md) (kiến trúc).

> **Trạng thái 30/07/2026** — đối chiếu trực tiếp với `PXV_NHẬP_LIỆU` và
> `PXV_DASHBOARD_DATA` tải về từ Sheets:
>
> | | Tình trạng |
> |---|---|
> | Mục 1 — lật ngày/tháng ở tab `LEAD` | ✅ đã sửa (import lại, phễu về 2.380) |
> | Mục 2 — phạm vi lịch sử hóa đơn | ✅ đã chốt (bỏ T11/2025 có chủ đích) |
> | Mục 3 — Looker cộng các tỷ số | ❌ **còn sai** — cần trỏ thẻ sang bảng `KPI` |
>
> Việc còn lại nằm hoàn toàn trong Looker: **mục 3**. Pipeline đã xuất sẵn bảng
> `KPI` để không cần viết công thức tay.

---

## 1. Trường ngày — chỗ đã gây thiệt hại lớn nhất

Pipeline ghi ngày dạng **ISO `YYYY-MM-DD`**, và ghi bằng `value_input_option='RAW'`
nên trong Sheets nó là **chữ, không phải ô ngày**.

Trong Looker: tạo field kiểu **Date** với format **`YYYY-MM-DD`**. Đừng để
`Auto`, đừng chọn `MM/DD/YYYY`.

**Đây không phải rủi ro lý thuyết — tab `LEAD` ĐÃ dính lỗi này một lần.** Đo
trên bản tải về ngày 30/07/2026, trước khi import lại: **1.012/2.426 dòng (42%)**
rơi sai tháng. Ghi lại đây để nhận ra ngay nếu tái diễn.

Phân bố ngày trong tab `LEAD` lúc đó:

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
| Đúng | **2.380** | 1.274 | 303 | 186 |
| Khi bị lật | 1.358 | 708 | 184 | 110 |

Dấu hiệu trên biểu đồ theo thời gian: **khoảng trống đúng từ ngày 3 đến ngày 12
của mỗi tháng**, và đỉnh biểu đồ thấp bất thường (77 thay vì 223).

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

## 2. Phạm vi lịch sử hóa đơn — T11/2025 bị bỏ CÓ CHỦ ĐÍCH

Tab `INVOICES_RAW` trên Sheets chỉ có 711 dòng từ 04/01/2026, trong khi file
KiotViet ở máy local có 1.013 dòng từ 01/11/2025 — thiếu nguyên **T11/2025: 302
hóa đơn, 915.858.500đ**.

Nghiệp vụ chốt (30/07/2026): **không nạp lại T11**, cho hai backend cùng một
phạm vi. Mốc nằm ở `config.INVOICE_HISTORY_START = 2026-01-01`; `io_local` cắt
hóa đơn cũ hơn mốc này ngay lúc đọc. Nạp lại được T11 thì đổi mốc về
`"2025-11-01"` (hoặc đặt biến `PXV_INVOICE_HISTORY_START`) là số tự khớp lại.

Hệ quả cần biết khi đọc trang Customer Value:

| Chỉ số | Phạm vi hiện tại | Nếu có T11/2025 |
|---|---|---|
| CLV trung bình | **5.396.710đ** (458 khách) | 5.689.481đ (594 khách) |
| Tỷ lệ khách quay lại | **24,2%** | 27,4% |
| Số khách mua mồi | **214** | 290 |

Doanh thu trong kỳ **không đổi** (2.552.689.000đ) vì T11 vốn nằm ngoài cửa sổ
phân tích — chỉ CLV và funnel mồi bị thu hẹp, vì hai bảng đó cố ý đọc toàn bộ
lịch sử.

Một tác dụng phụ tốt: trước đây `DIM_KHACH` có **130/594 khách (21,9%) `Kênh
Tiếp Cận` rỗng** — khách chỉ mua trước cửa sổ nên không có dòng nào trong
`MASTER`. Looker âm thầm bỏ họ khỏi mọi chart chia theo kênh. Giờ **còn 0**.

⚠️ Lần đầu chạy sau khi đổi mốc, phép kiểm `Doanh thu tháng đã đóng không đổi`
sẽ **DỪNG job** (lệch 26,4%). Đúng như thiết kế — nó không phân biệt được
"đổi phạm vi có chủ đích" với "mất dữ liệu". Chạy lại lần thứ hai là mốc mới
được ghi nhận và job xanh.

---

## 3. Mọi thẻ KPI phải trỏ vào bảng `KPI` — đừng dùng `HIEU_QUA_KENH`

`HIEU_QUA_KENH` giữ `CPL`, `CAC`, `ROAS`, `tỷ_lệ_chốt_%` ở grain **(tháng × kênh)**.
Looker mặc định `SUM`, mà cộng tỷ số thì vô nghĩa. Đo trên dashboard thật ngày
30/07/2026 — **toàn bộ trang Channel Performance sai**:

| Thẻ | Đang hiện | = SUM cột tỷ số | Đúng |
|---|---|---|---|
| Trung bình tỷ lệ chốt | 9,6% | 9,49% (AVG) | **7,82%** |
| ROAS | 27,19 | 27,45 | **4,18** |
| CAC | 5.139.536đ | 5.089.416đ | **784.516đ** |
| CPL Tiktok | ~110.000 | **110.000** | **55.000** |
| CPL Facebook | ~140.000 | **140.000** | **70.000** |
| ROAS Instagram | 14,1 | **14,14** | 8,91 |

CPL khớp từng đồng vì file chi phí mô phỏng sinh ra bằng `lead × CPL` — CPL đúng
phải trả về chính 55k/70k/90k, còn dashboard ra **gấp đúng 2 lần** = tổng 2 tháng.

### Cách sửa: bảng `KPI`

Pipeline giờ xuất thêm tab **`KPI`** — mỗi dòng là một **phạm vi**, mọi tỷ số đã
gộp sẵn với trọng số đúng. `SUM` hay `AVG` trên **một dòng** đều ra cùng kết quả,
nên không còn đường nào sai.

| Chart | Cấu hình |
|---|---|
| Mọi **thẻ số** (scorecard) | nguồn `KPI`, lọc `phạm vi = "TỔNG"` |
| Chart **theo kênh** (ROAS, CPL, CAC) | nguồn `KPI`, lọc `phạm vi != "TỔNG"`, dimension = `phạm vi` |

Cột có sẵn: `lead` · `có_sđt` · `có_hẹn` · `khách_mua` · `tỷ_lệ_có_sđt_%` ·
`tỷ_lệ_hẹn_%` · `tỷ_lệ_chốt_%` · `doanh_thu_quy_kết` · `doanh_thu_toàn_bộ` ·
`chi phí` · `CPL` · `CAC` · `ROAS` · `CLV_TB` · `tỷ_lệ_quay_lại_%` ·
`khách_mua_mồi` · `bán_chéo_cùng_ngày_%` · `upsell_90d_%`.

Bốn cột chỉ có ở dòng `TỔNG` (để trống ở dòng kênh): `doanh_thu_toàn_bộ`,
`khách_mua_mồi`, `bán_chéo_cùng_ngày_%`, `upsell_90d_%` — funnel mồi dựng từ hóa
đơn nên không có kênh.

`CLV_TB` ở đây thay cho chart **"CLV theo kênh tiếp cận"** đang hỏng (trục 0→1,
không cột nào) vì legend trỏ vào field `Trung bình Tổng doanh thu` **không tồn tại**.

⚠️ Bảng `KPI` đã gộp theo **TOÀN KỲ**. Đừng đặt bộ lọc ngày lên nó — không có
cột ngày để lọc, và số sẽ không đổi dù bạn kéo date range.

### Vẫn cấm

- `SUM(ROAS)`, `SUM(CAC)`, `SUM(CPL)`, `AVG(CPL)`, `AVG(tỷ_lệ_chốt_%)` — trên
  bất kỳ bảng nào.
- **Mọi pie/donut vẽ trên một tỷ số.** Donut "CAC theo Kênh" vô nghĩa về mặt
  toán học **kể cả khi số đã đúng** — phần trăm của một tỷ số không cộng thành
  100% được. Đổi sang **bar chart** CAC theo kênh, hoặc nếu muốn giữ donut thì
  vẽ `chi phí` (số cộng được) chứ không phải `CAC`.

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
cho thấy Looker **không** lọc hai bảng này. Số CLV/upsell thấp là do phạm vi
lịch sử hóa đơn (mục 2), không phải do bộ lọc.

Bảng `KPI` cũng **không lọc theo ngày được** — nó đã gộp theo toàn kỳ.

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

| Bảng | Phạm vi | Dùng khi | Giá trị hiện tại |
|---|---|---|---|
| `KPI` → `doanh_thu_toàn_bộ` | trong cửa sổ, GỒM vãng lai | **thẻ "Doanh thu"** | 2.552.689.000đ |
| `KPI` → `doanh_thu_quy_kết` | chỉ phần quy kết được về kênh | ROAS, CAC | 610.372.500đ |
| `MASTER`, `FACT_DAILY` | trong cửa sổ phân tích | biểu đồ theo thời gian | 2.552.689.000đ |
| `DIM_KHACH` | trọn đời khách (từ 01/01/2026) | CLV, phân khúc | 2.471.693.000đ |
| `DQ_STATUS` | các tháng đã đóng | mốc chống mất dữ liệu | 2.552.689.000đ |

Không có nhãn nào trong workbook nói lên phạm vi, nên thẻ KPI **phải tự ghi**.
Một thẻ "Doanh thu" không kèm nguồn là một thẻ sai chờ ngày bị đọc nhầm.

Dùng bảng `KPI` là cách gọn nhất: hai cột `doanh_thu_toàn_bộ` và
`doanh_thu_quy_kết` nằm cạnh nhau trên cùng một dòng, chênh lệch giữa chúng
chính là phần vãng lai (mục 7).

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

## 9. Dịch vụ mồi — bán chéo tại quầy KHÁC upsell quay lại

### Hai chỉ số TÁCH RIÊNG, đừng gộp

`FUNNEL_MOI` đo hai hành vi khác hẳn nhau:

| Chỉ số | Nghĩa là gì | Hiện tại |
|---|---|---|
| `bán_chéo_cùng_ngày` | Mua thêm dịch vụ chính **ngay trong lượt đó** — bán thêm tại quầy | **19,2%** (41/214) |
| `upsell_90d` | **Quay lại một ngày khác** trong vòng 90 ngày | **7,0%** (15/214) |

Gộp chung ra 23,8%, nhưng con số đó không trả lời được câu đáng giá nhất: *dịch
vụ mồi có kéo được khách quay lại không*. Câu trả lời là **7,0%** — thấp hơn
nhiều so với cảm giác, và đó mới là thứ cần cải thiện.

Ngược lại, **19,2% bán chéo tại quầy là điểm mạnh** đang bị con số gộp che mất:
gần 1/5 khách vào bằng dịch vụ mồi chi thêm tiền ngay trong buổi đó
(299.977.000đ, so với 127.162.500đ từ khách quay lại).

⚠️ Con số này **từng phụ thuộc vào việc dữ liệu có phần GIỜ hay không** — local
giữ giờ ra 17,3%, Sheets mất giờ ra 7,0%, cùng một bộ hóa đơn. Đã sửa: `io_local`
cắt giờ và phép so làm trên NGÀY, hai backend giờ ra cùng một số.

### Vẫn phải đọc theo cohort đã trưởng thành

`upsell_90d` dính **right-censoring**: khách mua mồi tháng gần nhất chưa sống đủ
90 ngày để có cơ hội quay lại.

| Cohort mua mồi | Số khách |
|---|---|
| T1/2026 | 137 ← mới quan sát được ~55 ngày |
| T2/2026 | 77 ← chưa đủ 90 ngày |

Dữ liệu dừng 25/02/2026 nên **không cohort nào đủ chín**. 7,0% vì thế là **cận
dưới**, không phải tỷ lệ thật. Thẻ `upsell_90d_%` phải ghi kèm "chưa đủ 90 ngày
quan sát".

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
- ~~`DIM_KHACH` có 130/594 khách `Kênh Tiếp Cận` rỗng~~ — **đã hết** sau khi
  chốt phạm vi lịch sử hóa đơn (mục 2). Nếu sau này nạp lại T11/2025 thì nhóm
  này quay lại: khách chỉ mua trước cửa sổ không có dòng nào trong `MASTER`, và
  Looker sẽ âm thầm bỏ họ khỏi mọi chart chia theo kênh.
- **"Tỷ lệ hẹn 14,0%" ≠ "Có Đặt Lịch 13,55%"** của phễu ngay cạnh — hai thẻ trên
  cùng một trang mâu thuẫn nhau.
- **"Nhu cầu theo nhóm sản phẩm" dùng `[F] 1_Có Inbox`** trên `Phân loại sản phẩm`.
  Cột đó lấy `Tên hàng` (đã mua) rồi mới fallback sang `QUAN TÂM` (quan tâm lúc
  inbox) — trộn hai khái niệm. 342/2.380 rơi vào "Chưa rõ" nhưng chart không hiện.
- **Cờ `[F]` đã khử trùng theo SĐT** — `SUM([F] 4_Có Ra Đơn)` là **số KHÁCH ra
  đơn**, không phải số hóa đơn. Muốn đếm đơn thì dùng `số_hóa_đơn`.
- **Tên cột không nhất quán giữa các bảng.** `có_đơn` (FACT_DAILY) vs `khách_mua`
  (HIEU_QUA_KENH); `chi phí` có dấu cách; `SĐT` (DIM_KHACH) vs `SĐT Cuối` (MASTER);
  `Kênh Tiếp Cận` vs `kênh` (HIEU_QUA_KENH). Kiểm tên trước khi nối field.
