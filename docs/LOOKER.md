# Cấu hình Looker Studio

Pipeline tính sẵn mọi con số rồi mới đẩy sang Looker. Vì thế phần lớn lỗi
dashboard **không nằm ở dữ liệu** mà ở cách Looker gộp và lọc lại số đã tính.

File này ghi lại những chỗ đã sai thật, kèm cách làm đúng. Đọc kèm
[README.md](../README.md) (kiến trúc, guardrails và các bẫy dữ liệu).

> **Trạng thái 30/07/2026 — bản kiểm LẦN 2** (ảnh chụp 3 trang dashboard, đối
> chiếu với `output/PXV_DASHBOARD_DATA.xlsx`, không suy đoán từ ảnh):
>
> | Mục | Tình trạng |
> |---|---|
> | 1 — lật ngày/tháng ở tab `LEAD` | ✅ đã sửa (đỉnh biểu đồ về 223, phễu về 2.380) |
> | 2 — phạm vi lịch sử hóa đơn | ✅ đã chốt (bỏ T11/2025 có chủ đích) |
> | 3 — Looker cộng các tỷ số | 🟡 **nửa xong** — chart theo kênh đã ĐÚNG, thẻ số vẫn không trỏ vào `KPI` |
> | 4 — lọc ngày sai bảng | ❌ **thành lỗi thật** — `FUNNEL_MOI` đang bị lọc, còn 78/214 khách |
> | 8 — chi phí QC là số mô phỏng | ❌ vẫn chưa có băng cảnh báo |
> | 10 — băng độ tươi dữ liệu | ❌ chưa có; footer "Last Updated 30/07" đang nói ngược sự thật |
> | 11 — chart "CLV theo kênh" | ❌ **đổi dạng lỗi**: hết trống, nhưng đang vẽ `lead` chứ không phải `CLV_TB` |
> | 12 — nhãn / định dạng | ❌ nhãn cắt chữ, `[F] 1_Có Inbox` lộ ra, tỷ lệ hiện `0.0`, `null` |
> | 13 — sắp xếp & ngữ cảnh | ❌ 3 trang 3 kỳ ngày khác nhau; 10/10 thẻ số không có delta |
>
> **Việc phải làm, theo thứ tự: [mục 14](#14-checklist-sửa--làm-theo-thứ-tự-này).**
> 6 việc P0 đều nằm hoàn toàn trong Looker, không cần chạy lại pipeline.

---

## 0. Dashboard đang có gì — kiểm kê 30/07/2026

Ba trang, tổng 10 thẻ số + 9 chart + 1 bảng. Ghi lại đầy đủ để lần sau so được.

### Trang 1 — MARKETING PERFORMANCE · date range `Jan 1 – Feb 28, 2026`

| Visual | Đang hiện | Số đúng (`KPI`, dòng `TỔNG`) |
|---|---|---|
| Thẻ Lượng Lead | **2.367** | **2.380** |
| Thẻ Tỷ lệ hẹn | **12,46%** | **12,73%** |
| Thẻ "Trung bình tỷ lệ chốt" | **7,73%** | **7,82%** |
| Thẻ Doanh thu quy về Lead | **579M** | **610.372.500đ** |
| Phễu 4 chặng | 100% / 53,53% / 12,46% / 7,73% | 100% / 53,53% / 12,73% / 7,82% |
| Line "Lead và đặt hẹn qua thời gian" | 2 chuỗi, đỉnh ~223 ngày 08–09/01 | đỉnh 223 ✅ đúng |
| Bar "Doanh thu theo kênh" | FB ~390M · TikTok ~101M · Khác ~34M · Khách cũ ~32M · Others | thiếu caption vãng lai (mục 7) |

**Cả 4 thẻ + phễu đang chạy trên mẫu số 2.367**, và nội bộ nhất quán với nhau:

```
1267 / 2367 = 53,53%      295 / 2367 = 12,46%      183 / 2367 = 7,73%
```

Nghĩa là **không phải lỗi công thức mà là lỗi nguồn**: chúng tính lại từ
`MASTER` + bộ lọc ngày, thay vì đọc bảng `KPI` đã gộp sẵn. Phễu đúng là
`2380 → 1274 → 303 → 186`; dashboard đang là `2367 → 1267 → 295 → 183`, tức
**mất 13 lead và 3 khách đã mua**.

> Đáng chú ý: trong `MASTER` ở local, **không có dòng nào** có `Ngày Lead` ngoài
> khoảng 01/01–28/02/2026 (min 2026-01-01, max 2026-02-25). Vậy 13 lead biến mất
> **không đến từ dữ liệu local** — chúng đến từ bản trên Sheets (tab `LEAD` có 5
> lead nhập tay ngày 28/07/2026, xem mục 1) hoặc từ cách Looker đọc field ngày.
> Trỏ thẻ sang `KPI` là xong, không cần truy tiếp.

### Trang 2 — CHANNEL PERFORMANCE & BUDGET DISTRIBUTION · **không có bộ lọc ngày**

| Visual | Đang hiện | Nhận xét |
|---|---|---|
| Thẻ Chi Phí Quảng Cáo | **145.920.000đ** | ❌ **SỐ MÔ PHỎNG** (mục 8), không nhãn |
| Thẻ ROAS | **3,97** | = 579M / 145,92M · đúng phải **4,18** |
| Thẻ CAC | **797.377đ** | = 145.920.000 / **183** · đúng phải **784.516đ** (/186) |
| Bubble CPL × tỷ lệ chốt | 3 điểm (FB, TikTok, IG) | số đúng, nhưng 3 điểm thì bar rõ hơn |
| Bar ROAS theo kênh | IG 8,9 · TikTok 4,6 · FB 3,2 | ✅ **khớp `KPI` + chi phí toy** (8,91 / 4,57 / 3,27) |
| Bar CAC theo kênh | FB ~1,0M · TikTok ~540k · IG ~450k | ✅ **khớp** (994.344 / 542.000 / 450.000) |
| Footer | `Data Last Updated: 7/30/2026 6:41:55 PM` | ❌ đó là mốc chạy pipeline, không phải độ tươi dữ liệu (mục 10) |

**Tiến bộ thật:** lỗi `SUM` trên cột tỷ số ở mục 3 **đã hết** — ROAS từ 27,19 về
3,97, CAC từ 5.139.536 về 797.377, donut "CAC theo Kênh" đã thành bar. Toàn bộ
chart **theo kênh** giờ đúng từng con số. Chỉ còn 3 thẻ tổng là lấy sai nguồn.

Còn 4–5 dòng danh mục **rỗng hoàn toàn** trên hai bar chart (Hotline/Zalo, Giới
thiệu, Khách cũ, Khác, Others). Đó là `NaN` = "chưa nhập chi phí" (đúng thiết kế
của `_chia()`), nhưng người xem đọc thành "hiệu quả bằng 0".

### Trang 3 — CUSTOMER VALUE & SERVICE STRATEGY · date range `Feb 1 – Feb 28, 2026`

| Visual | Đang hiện | Số đúng |
|---|---|---|
| Thẻ CLV Trung Bình | ~5,1xx,xxx *(bị tooltip che trong ảnh)* | **5.396.710đ** (458 khách) |
| Thẻ Tỷ lệ khách quay lại | **24,30%** | **24,24%** (111/458) |
| Thẻ Tỷ lệ cần Upsell 90 ngày | **6,98%** | **7,01%** (15/214) |
| Bar "CLV theo kênh tiếp cận" | legend `lead`, trục 0–2,5K, có cột **TỔNG** ≈2380 | phải là `CLV_TB`, lọc bỏ `TỔNG` |
| Bar "Nhu cầu theo nhóm sản phẩm" | legend `[F] 1_Có Inbox`, tổng cột ~516 | đang lọc T2 → lệch mẫu số với thẻ phía trên |
| Bar "Doanh thu theo dịch vụ thực mua" | nhãn trục đè nhau | |
| Bảng "Hiệu quả dịch vụ mồi" | 5 dòng, `Khách mua mồi` = 10+31+1+12+24 = **78** | **214** |

Hai phát hiện nặng nhất của cả bản kiểm nằm ở trang này:

**(a) Chart "CLV theo kênh tiếp cận" đang vẽ SAI CỘT.** Đọc từng cột: TỔNG≈2380 ·
Facebook≈1733 · Khách cũ≈47 · Instagram≈25 — khớp **chính xác** cột `KPI.lead`,
không phải `KPI.CLV_TB`. Chart mang tiêu đề CLV nhưng đang hiện **số lượng lead**.
Kèm lỗi thứ hai: thiếu bộ lọc `phạm vi != "TỔNG"` nên cột TỔNG nuốt hết thang đo.
CLV đúng theo kênh: Khách cũ 6.428.000 · IG 4.010.000 · FB 3.363.970 · TikTok
2.541.250 — thứ tự **ngược hẳn** so với thứ tự đang hiện.

**(b) Bảng "Hiệu quả dịch vụ mồi" đang bị lọc theo ngày.** Cộng cột `Khách mua mồi`
được **78**, trong khi `FUNNEL_MOI` có **214 khách / 5 dịch vụ**. 78 ≈ cohort
T2/2026 (77 khách) → date range `Feb 1–28` đang áp lên `FUNNEL_MOI`, đúng thứ mục
4 cấm. Hệ quả kép: chỉ còn cohort **chưa sống đủ 90 ngày**, nên cột UpSell ra
`0.0` và cột số ngày ra `null` gần hết. Trong khi đó **thẻ "6,98%" phía trên lại
tính trên đủ 214** → cùng một trang, hai mẫu số khác nhau.

Số đúng của bảng (toàn kỳ):

| Dịch vụ mồi | Khách | Bán chéo cùng ngày | Upsell 90d |
|---|---|---|---|
| (DV) GÓI TIẾT KIỆM - XÓA CHÂN MÀY TRỌN GÓI | **88** | 12 | 9 (10,2%) |
| (DV) Xóa lần 01 - Chân Mày | **73** | 4 | 2 (2,7%) |
| (DV) Công nghệ CO2 Fractional - Tách thâm | **38** | 13 | 3 (7,9%) |
| (DV) Công nghệ CO2 Fractional - Gói Double bóc tách | **11** | 11 | 0 (0,0%) |
| (DV) Xóa lần 01 - Mí (Trên HOẶC Dưới) | **4** | 1 | 1 (25,0%) |

Bảng đang xếp theo `Tỷ lệ UpSell` giảm dần, nên dòng đầu tiên là dòng có **n=10**.
Dịch vụ mồi lớn nhất thật (88 khách, 10,2%) bị đẩy xuống. Sắp theo `Khách mua mồi`
giảm dần, và **đừng xếp hạng theo tỷ lệ khi n < 20**.

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

✅ **Bản kiểm 30/07/2026 (lần 2): đã sửa xong.** Đường xu hướng trang 1 có đỉnh
223 ở ngày 08–09/01 và không còn khoảng trống ngày 3–12. Đó là dấu hiệu tin được
nhất cho thấy bản import lại vẫn giữ.

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
30/07/2026 (**bản kiểm lần 1**) — toàn bộ trang Channel Performance sai:

| Thẻ | Kiểm lần 1 | = SUM cột tỷ số | Đúng |
|---|---|---|---|
| Trung bình tỷ lệ chốt | 9,6% | 9,49% (AVG) | **7,82%** |
| ROAS | 27,19 | 27,45 | **4,18** |
| CAC | 5.139.536đ | 5.089.416đ | **784.516đ** |
| CPL Tiktok | ~110.000 | **110.000** | **55.000** |
| CPL Facebook | ~140.000 | **140.000** | **70.000** |
| ROAS Instagram | 14,1 | **14,14** | 8,91 |

CPL khớp từng đồng vì file chi phí mô phỏng sinh ra bằng `lead × CPL` — CPL đúng
phải trả về chính 55k/70k/90k, còn dashboard ra **gấp đúng 2 lần** = tổng 2 tháng.

### 🟡 Bản kiểm lần 2: chart theo kênh đã đúng, thẻ số thì chưa

| | Kiểm lần 1 | Kiểm lần 2 | Đúng |
|---|---|---|---|
| ROAS (thẻ) | 27,19 | **3,97** | 4,18 |
| CAC (thẻ) | 5.139.536 | **797.377** | 784.516 |
| Tỷ lệ chốt (thẻ) | 9,6% | **7,73%** | 7,82% |
| ROAS Instagram (chart) | 14,14 | **8,9** ✅ | 8,91 |
| CAC Facebook (chart) | — | **~1,0M** ✅ | 994.344 |

Ba thẻ đã thoát lỗi cộng-tỷ-số (giờ là tỷ-số-của-tổng, **phương pháp đúng**)
nhưng vẫn tính lại từ `MASTER` đã lọc ngày, nên mẫu số là 2.367/183 thay vì
2.380/186. Lệch 1–5% — nhỏ, và chính vì nhỏ nên **không ai phát hiện được bằng
mắt**; chỉ lộ ra khi đối chiếu với bảng `KPI`.

`797.377 × 183 = 145.920.000` — khớp từng đồng, xác nhận mẫu số là 183.

### Cách sửa: bảng `KPI`

Pipeline xuất tab **`KPI`** — mỗi dòng là một **phạm vi**, mọi tỷ số đã gộp sẵn
với trọng số đúng. `SUM` hay `AVG` trên **một dòng** đều ra cùng kết quả, nên
không còn đường nào sai.

| Chart | Cấu hình |
|---|---|
| Mọi **thẻ số** (scorecard) | nguồn `KPI`, lọc `phạm vi = "TỔNG"`, **không có date filter** |
| Chart **theo kênh** (ROAS, CPL, CAC, CLV) | nguồn `KPI`, lọc `phạm vi != "TỔNG"`, dimension = `phạm vi` |

Cột có sẵn: `lead` · `có_sđt` · `có_hẹn` · `khách_mua` · `tỷ_lệ_có_sđt_%` ·
`tỷ_lệ_hẹn_%` · `tỷ_lệ_chốt_%` · `doanh_thu_quy_kết` · `doanh_thu_toàn_bộ` ·
`chi phí` · `CPL` · `CAC` · `ROAS` · `CLV_TB` · `tỷ_lệ_quay_lại_%` ·
`khách_mua_mồi` · `bán_chéo_cùng_ngày_%` · `upsell_90d_%`.

Giá trị dòng `TỔNG` hiện tại — dùng làm mốc đối chiếu sau mỗi lần sửa chart:

```
lead 2380 · có_sđt 1274 · có_hẹn 303 · khách_mua 186
tỷ_lệ_có_sđt 53,53% · tỷ_lệ_hẹn 12,73% · tỷ_lệ_chốt 7,82%
doanh_thu_quy_kết 610.372.500 · doanh_thu_toàn_bộ 2.552.689.000
CLV_TB 5.396.710 · tỷ_lệ_quay_lại 24,24%
khách_mua_mồi 214 · bán_chéo_cùng_ngày 19,16% · upsell_90d 7,01%
```

Bốn cột chỉ có ở dòng `TỔNG` (để trống ở dòng kênh): `doanh_thu_toàn_bộ`,
`khách_mua_mồi`, `bán_chéo_cùng_ngày_%`, `upsell_90d_%` — funnel mồi dựng từ hóa
đơn nên không có kênh.

⚠️ Bảng `KPI` đã gộp theo **TOÀN KỲ**. Đừng đặt bộ lọc ngày lên nó — không có
cột ngày để lọc, và số sẽ không đổi dù bạn kéo date range. Nếu một thẻ trỏ vào
`KPI` mà số vẫn thay đổi khi kéo date range, nghĩa là nó **chưa** thật sự trỏ vào
`KPI`.

### Vẫn cấm

- `SUM(ROAS)`, `SUM(CAC)`, `SUM(CPL)`, `AVG(CPL)`, `AVG(tỷ_lệ_chốt_%)` — trên
  bất kỳ bảng nào.
- **Mọi pie/donut vẽ trên một tỷ số.** Donut "CAC theo Kênh" vô nghĩa về mặt
  toán học **kể cả khi số đã đúng** — phần trăm của một tỷ số không cộng thành
  100% được. Đổi sang **bar chart** CAC theo kênh, hoặc nếu muốn giữ donut thì
  vẽ `chi phí` (số cộng được) chứ không phải `CAC`. ✅ đã sửa ở kiểm lần 2.
- **`SUM(Doanh Thu (VNĐ))` kèm bộ lọc `[F] 1_Có Inbox = 1`.** Cờ `[F]` đã khử
  trùng theo SĐT nên chỉ đúng 1 dòng/khách có cờ; lọc như vậy làm mất doanh thu
  của các hóa đơn còn lại. Đo thử: ra **415.796.000đ** thay vì 610.372.500đ.
  Doanh thu quy kết **chỉ lấy từ `KPI.doanh_thu_quy_kết`**.

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
| `KPI` | ❌ **KHÔNG** | đã gộp toàn kỳ, không có cột ngày |
| `HIEU_QUA_KENH` | — | `tháng` là **chuỗi** `"YYYY-MM"`, Looker không lọc ngày được |

**Vì sao cấm lọc `DIM_KHACH` và `FUNNEL_MOI`:** CLV và tỷ lệ upsell được tính
trên **toàn bộ lịch sử mua**, cố ý lấy cả hóa đơn trước cửa sổ phân tích. Áp
date range của báo cáo lên chúng là phá đúng thiết kế đó — cắt mất cohort cũ,
tức nhóm gắn bó lâu nhất và có tỷ lệ mua lại cao nhất.

### ❌ Kiểm lần 2: đây không còn là quy tắc phòng ngừa — đã thành lỗi thật

Bản kiểm lần 1 nói "Looker **không** lọc hai bảng này". **Sai rồi.** Bảng
"Hiệu quả dịch vụ mồi" trên trang 3 đang cộng ra **78 khách mua mồi** thay vì
**214**, và 78 ≈ cohort T2/2026 (77 khách) — đúng bằng phần date range
`Feb 1 – Feb 28` chừa lại.

Đây là kiểu lỗi tệ nhất trong cả file này: nó **không làm gì đổ vỡ**, chỉ làm mọi
tỷ lệ upsell tụt về 0 và mọi "số ngày đến upsell" thành `null`, rồi để người đọc
tự kết luận "dịch vụ mồi không hiệu quả". Đúng ra 9/88 khách của gói mồi lớn nhất
đã quay lại (10,2%).

Và vì thẻ `6,98%` phía trên **không** bị lọc, trang 3 đang tự mâu thuẫn: thẻ đọc
214 khách, bảng ngay dưới đọc 78.

**Cách phát hiện lại về sau:** mở bảng, cộng cột `Khách mua mồi`. **Không ra 214
là đang bị lọc.** Tương tự, thẻ CLV không ra 5.396.710 là đang bị lọc hoặc trỏ
sai field.

Muốn xem CLV/upsell theo kỳ thì lọc bằng `cohort_tháng` (dimension riêng trong
`DIM_KHACH`), **không** phải bằng date range của báo cáo.

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

### Hai điểm đầu/cuối của đường xu hướng đều cần chú thích

Đây là hai cái bẫy đọc biểu đồ, không phải lỗi dữ liệu — nhưng không ghi ra thì
người xem kết luận sai:

- **Điểm 01/01/2026 bị phồng.** `clean.parse_lead_dates` gán lead **trống ô NGÀY**
  về `config.LEAD_DATE_DEFAULT = 01/01/2026`, nên ngày đó có **53 lead thay vì
  33** — 20 lead là "không biết ngày", không phải "vào ngày 1/1". Nghiệp vụ đã
  chọn không đánh dấu nên **không có cách phân biệt về sau**.
- **Điểm cuối là kỳ chưa trọn.** Hóa đơn/lead dừng 25/02/2026, nên cột/điểm cuối
  luôn thấp và tạo cảm giác lao dốc. Cắt bỏ điểm cuối, hoặc vẽ nét đứt.

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

⚠️ **Con số bất biến quan trọng nhất của pipeline — `doanh_thu_toàn_bộ`
2.552.689.000đ — hiện KHÔNG xuất hiện ở bất kỳ đâu trên dashboard.** Ba trang chỉ
có `579M` (quy kết, và còn lệch). Chủ spa xem dashboard này sẽ tưởng cả kỳ thu
được 579 triệu, tức **thiếu 1,97 tỷ**. Đây là việc P0 số 6 ở mục 14.

Cách tính `doanh_thu_quy_kết = 610.372.500`, ghi ra để khỏi phải suy lại: đó là
tổng doanh thu của **Nhóm 5 (Lead hoàn hảo, 505.282.500đ) + Nhóm 3 (Chốt thẳng
không cần hẹn, 105.090.000đ)** trong `Phân nhóm MECE`. **Không** gồm Nhóm 6 (Hẹn
thiếu hồ sơ lead — lỗi data, 14.622.000đ) và **không** gồm Nhóm 1 (Vãng lai,
1.927.694.500đ).

---

## 7. 75,5% doanh thu KHÔNG quy kết được về kênh

| Kênh | Doanh thu | |
|---|---|---|
| **Vãng lai (không rõ nguồn)** | **1.927.694.500đ** | **75,5%** |
| Facebook | 396.948.500đ | 15,6% |
| Tiktok | 101.650.000đ | 4,0% |
| Còn lại (Khách cũ, Khác, Instagram) | 126.396.000đ | 4,9% |

Khách vãng lai chưa từng inbox nên **không thuộc phễu marketing** (để chung thì
F4 > F3, phễu nở ra ở bước sau). Họ cũng không có `Ngày Lead`, nên **mọi bộ lọc
ngày dựa trên `Ngày Lead` đều loại họ đi** — đó là lý do chart "Doanh thu theo
kênh" hiện đang giấu mất 3/4 số tiền và làm Facebook trông như nguồn doanh thu
chính.

**Bắt buộc:** chart doanh thu theo kênh phải ghi tiêu đề *"chỉ phần quy kết được
— 75,5% doanh thu đến từ khách vãng lai không có hồ sơ lead"*. Và **không dùng
tổng doanh thu làm tử số ROAS** — ROAS theo kênh chỉ là **cận dưới**.

❌ Kiểm lần 2: chart trang 1 vẫn mang tiêu đề trần "Doanh thu theo kênh", chưa có
caption.

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
`chi phí = 0` toàn bộ và `CPL/CAC/ROAS = NaN` — DQ báo `Chi phí quảng cáo: chưa nhập`
(🟠 CẢNH BÁO trong `DQ_STATUS`, xác nhận lại ngày 30/07/2026).

**Cho tới khi có chi phí thật:** trang Channel Performance phải có băng cảnh báo
"số liệu chi phí là mô phỏng cho case study". Đừng đưa trang này cho chủ spa xem
mà không có băng đó.

❌ Kiểm lần 2: **vẫn chưa có băng.** Đây là lỗi ACES nặng nhất của cả dashboard —
một trang trông chính xác tuyệt đối (3 thẻ, 3 chart, số khớp nhau từng đồng) mà
**toàn bộ mẫu số là số bịa**. Trang càng đẹp thì càng đáng lo, vì không có gì
trong thiết kế gợi cho người xem là nên nghi ngờ.

Nội dung băng đề xuất, đặt ngay dưới tiêu đề trang, nền đỏ/vàng:

> ⚠️ **CHI PHÍ QUẢNG CÁO LÀ SỐ MÔ PHỎNG** (CPL giả định FB 70k / TikTok 55k /
> IG 90k). Doanh thu là số thật. Vì vậy ROAS · CAC · CPL trên trang này là
> **kịch bản để kiểm thử pipeline**, không phải hiệu quả đã đạt được.
> Chi phí thật chưa được nhập.

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

❌ Kiểm lần 2: **chỉ số `bán_chéo_cùng_ngày` (19,2%) không có mặt ở đâu trên
dashboard.** Trang 3 chỉ hiện `upsell_90d`. Tức điểm mạnh lớn nhất của mảng dịch
vụ mồi đang bị bỏ trắng, còn điểm yếu thì hiện — và hiện dưới dạng đã bị lọc sai
(mục 4) nên còn tệ hơn thực tế.

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
  upsell thật đang hiển thị thành `0,0`. Đổi sang phần trăm, 1 chữ số. ❌ kiểm
  lần 2: vẫn còn (`0.1` / `0.0`).

---

## 10. Băng "dữ liệu tính đến ngày…"

`DQ_STATUS` có dòng `Chạy lúc` (mốc pipeline) và `Độ tươi hóa đơn` (hóa đơn mới
nhất). Đưa cả hai lên đầu mỗi trang.

Hiện tại: **dữ liệu dừng 25/02/2026, hôm nay 30/07/2026 — chênh 155 ngày**
(`DQ_STATUS` → `Độ tươi hóa đơn` = 🟠 155 ngày).

❌ Kiểm lần 2: không chỉ thiếu băng — **footer đang nói ngược sự thật.** Trang 2
ghi `Data Last Updated: 7/30/2026 6:41:55 PM`. Đó là mốc **chạy pipeline**, không
phải độ tươi dữ liệu. Người xem đọc nó thành "số của hôm nay", trong khi hóa đơn
mới nhất đã 5 tháng tuổi. Một footer sai còn tệ hơn không có footer.

Băng đề xuất, đặt trên cùng **cả ba trang**:

> 📅 Dữ liệu tính đến **25/02/2026** · pipeline chạy **30/07/2026** ·
> ⚠️ hóa đơn mới nhất đã **155 ngày** trước

---

## 11. Vài lỗi lẻ đang có trên dashboard

- **Chart "CLV theo kênh tiếp cận"** — kiểm lần 1: trục 0→1, không cột nào, vì
  legend trỏ vào field `Trung bình Tổng doanh thu` **không tồn tại**.
  🔄 Kiểm lần 2: **đổi dạng lỗi, chưa hết lỗi.** Giờ có cột, nhưng legend là
  `lead` và chart đang vẽ **số lượng lead** dưới tiêu đề CLV, kèm cột `TỔNG` chưa
  bị lọc. Cách sửa ở mục 14, việc P0-4.
- ~~`DIM_KHACH` có 130/594 khách `Kênh Tiếp Cận` rỗng~~ — **đã hết** sau khi
  chốt phạm vi lịch sử hóa đơn (mục 2). Nếu sau này nạp lại T11/2025 thì nhóm
  này quay lại: khách chỉ mua trước cửa sổ không có dòng nào trong `MASTER`, và
  Looker sẽ âm thầm bỏ họ khỏi mọi chart chia theo kênh.
- ~~**"Tỷ lệ hẹn 14,0%" ≠ "Có Đặt Lịch 13,55%"**~~ — ✅ **đã hết** ở kiểm lần 2,
  hai chỗ giờ cùng hiện 12,46%. (Vẫn còn lệch với `KPI` là 12,73% — việc P0-5.)
- **Thẻ vẫn tên là "Trung bình tỷ lệ chốt".** Cách tính giờ đã đúng (tỷ số của
  tổng), nhưng chữ "Trung bình" là di sản của thời `AVG(tỷ_lệ_chốt_%)` và vẫn mời
  người đọc hiểu thành trung bình các tỷ lệ. Đổi thành **"Tỷ lệ chốt"**.
- **"Nhu cầu theo nhóm sản phẩm" dùng `[F] 1_Có Inbox`** trên `Phân loại sản phẩm`.
  Cột đó lấy `Tên hàng` (đã mua) rồi mới fallback sang `QUAN TÂM` (quan tâm lúc
  inbox) — trộn hai khái niệm. 342/2.380 rơi vào "Chưa rõ" nhưng chart không hiện.
  Kiểm lần 2: legend vẫn để nguyên tên field nội bộ `[F] 1_Có Inbox` cho người
  xem đọc.
- **Cờ `[F]` đã khử trùng theo SĐT** — `SUM([F] 4_Có Ra Đơn)` là **số KHÁCH ra
  đơn**, không phải số hóa đơn. Muốn đếm đơn thì dùng `số_hóa_đơn`.
- **Tên cột không nhất quán giữa các bảng.** `có_đơn` (FACT_DAILY) vs `khách_mua`
  (HIEU_QUA_KENH); `chi phí` có dấu cách; `SĐT` (DIM_KHACH) vs `SĐT Cuối` (MASTER);
  `Kênh Tiếp Cận` vs `kênh` (HIEU_QUA_KENH). Kiểm tên trước khi nối field.

---

## 12. Nhãn và định dạng — lỗi trình bày, không phải lỗi số

Số đúng mà đọc không ra thì cũng không dùng được. Danh sách đo trên ảnh chụp
30/07/2026:

| Chỗ | Đang bị | Sửa |
|---|---|---|
| Trục danh mục mọi bar chart | `Faceb…` · `Instag…` · `Xóa Laser` đè lên nhau | nới cột nhãn, hoặc bar ngang + rút gọn tên kênh |
| Bảng dịch vụ mồi | **hai dòng cắt thành cùng một chuỗi** `(DV) Công nghệ CO2 Fractional -…` → không phân biệt được dịch vụ nào | thêm field rút gọn: `Tách thâm` / `Double bóc tách` |
| Legend "Nhu cầu theo nhóm sản phẩm" | `[F] 1_Có Inbox` | đổi nhãn thành `Số lead` |
| Cột `Tỷ lệ UpSell 90D` | `0.1` · `0.0` (số thập phân) | format **Percent, 1 chữ số** |
| Cột `Số ngày trung bình` | in thẳng `null` | đổi "Missing data" → `—` hoặc `chưa có` |
| Phễu trang 1 | chỉ có `%`, không có số tuyệt đối | `Có Inbox 2.380 (100%)` → `1.274 (53,5%)` → `303 (12,7%)` → `186 (7,8%)` |
| Line "Lead và đặt hẹn" | 2 chuỗi lệch 5–20 lần trên **cùng một trục** → đường "đặt hẹn" bị bóp dẹt sát 0, vô nghĩa | **Bar-Line chart**: bar = lead, line = đặt hẹn trên **trục phụ** |
| Bubble "CPL × tỷ lệ chốt" | 3 điểm, chữ nhạt gần như không đọc được, legend `phạm vi` không nói gì, nhãn `Instagram` cắt ở mép phải | 3 điểm thì dùng **bar CPL theo kênh**; giữ bubble thì tăng contrast + đổi legend |
| Bar ROAS/CAC theo kênh | 4–5 dòng danh mục **rỗng hoàn toàn** (NaN = chưa có chi phí) → đọc thành "hiệu quả 0" | lọc `chi phí > 0`, hoặc ghi chú "kênh không chạy QC" |
| Thẻ ROAS & CAC trang 2 | chữ số nhạt hơn thẻ Chi Phí ngay cạnh | thống nhất style cả hàng |
| Thẻ CLV | tooltip đè lên chính con số | bỏ tooltip hoặc dời |

---

## 13. Sắp xếp & ngữ cảnh — chiếu theo tiêu chí ACES

Tham chiếu: tài liệu *How to Design a Dashboard* (Chartio) — **A**ccurate ·
**C**lear · **E**mpowering · **S**uccinct.

### Đang làm đúng, giữ nguyên

- **Hàng thẻ số trên cùng → chart chi tiết bên dưới**, cả 3 trang. Đúng khung mẫu.
- Đúng hai template tài liệu gợi ý: *High-level number → line graph* (Lượng Lead →
  xu hướng theo ngày) và *Indicator → table with relevant details* (Tỷ lệ upsell →
  bảng hiệu quả dịch vụ mồi).
- **Chọn đúng loại chart theo bản chất dữ liệu:** funnel cho drop-off, line cho
  liên tục, bar cho danh mục rời rạc, **không pie/donut cho tỷ số**.
- **Succinct: đạt.** 3 trang, mỗi trang 4–7 visual, đúng khuyến nghị "3–6 loại
  chart / trang". Không trang nào bị nhồi.

### Chưa đúng

1. **Ba trang, ba kỳ ngày khác nhau.** Trang 1 `Jan 1 – Feb 28` · trang 3
   `Feb 1 – Feb 28` · trang 2 không có bộ lọc nào. Đọc trang 1 rồi sang trang 3 sẽ
   thấy hai bộ số không cộng vào nhau được. **Thống nhất `01/01 – 28/02/2026`.**
2. **Vị trí bắt mắt nhất dành cho chỉ số ít giá trị nhất.** Tài liệu hỏi *"Which
   visualization grabs your eye first? Should it?"* — góc trên-trái trang 1 là
   `Lượng Lead 2.367`, một chỉ số vanity. Với chủ spa, thứ tự nên là:
   **Doanh thu toàn bộ → Doanh thu quy kết → Tỷ lệ chốt → Lượng Lead.**
3. **Hai thẻ trang 1 trùng lặp hoàn toàn với phễu ngay bên dưới.**
   `Tỷ lệ hẹn 12,46%` = chặng 3 của phễu; `Trung bình tỷ lệ chốt 7,73%` = chặng 4.
   Tài liệu: *"Should any of these be grouped together?"* — đây là chỗ đó. Thay
   hai thẻ này bằng **Doanh thu toàn bộ** + **delta so kỳ trước**.
4. **10/10 thẻ số là Single Value trần** — không delta, không kỳ trước, không mục
   tiêu. Tài liệu phân biệt rõ ba dạng: *Single Value* / *Single Value Indicator*
   (kèm mũi tên biến động) / *Bullet* (kèm mục tiêu). Đây là khoảng trống lớn nhất
   về **E — Empowering**: xem xong không biết nên làm gì. Ưu tiên chuyển 4 thẻ
   quyết định ngân sách (Doanh thu, Tỷ lệ chốt, ROAS, CAC) sang dạng có delta.
5. **Không có link-out, không có định nghĩa chỉ số, không ghi ai sở hữu.**
   Workbook có 4 con số doanh thu khác nhau (mục 6) mà không thẻ nào ghi phạm vi.
6. **Trang 2 mất cân bằng bố cục** — cột phải chỉ có 1 chart, dưới nó là mảng
   trắng lớn; tooltip của bubble chart đè lên vùng tiêu đề.
7. **Trang 3 xếp 3 bar chart cạnh nhau đo 3 thứ không so được với nhau** (CLV
   theo kênh / nhu cầu sản phẩm / doanh thu dịch vụ). Mắt sẽ so chúng theo phản
   xạ. Nên gom 2 chart "sản phẩm" lại một nhóm, đưa "CLV theo kênh" về sát thẻ CLV.

---

## 14. Checklist sửa — làm theo thứ tự này

Toàn bộ P0 nằm trong Looker Studio, **không cần chạy lại pipeline**. Sau mỗi việc
có "cách kiểm" — làm ngay, đừng để dồn.

### P0 — sai số. Sửa xong 6 việc này mới được đưa dashboard cho ai xem.

**P0-1 · Băng cảnh báo chi phí mô phỏng (trang 2)** — mục 8
- Thêm text box nền đỏ/vàng ngay dưới tiêu đề trang, nội dung ở mục 8.
- *Kiểm:* băng hiện rõ trước khi mắt kịp chạm vào thẻ ROAS.

**P0-2 · Băng độ tươi dữ liệu (cả 3 trang)** — mục 10
- Thêm text box: `Dữ liệu tính đến 25/02/2026 · pipeline chạy 30/07/2026 · hóa đơn mới nhất đã 155 ngày`.
- **Xóa hoặc đổi nhãn footer `Data Last Updated`** — hiện nó nói ngược sự thật.
- *Kiểm:* không còn chỗ nào trên dashboard gợi ý rằng đây là số của tháng 7.

**P0-3 · Bỏ date filter khỏi bảng "Hiệu quả dịch vụ mồi" (trang 3)** — mục 4
- Chọn bảng → Setup → mục **Date Range Dimension**: để trống (`None`).
- Nếu date range là control cấp trang: chọn bảng → Resource → *Manage filters* →
  bỏ liên kết; hoặc chuột phải control → *Apply to selected charts* và bỏ tick
  bảng này + mọi visual đọc `FUNNEL_MOI` / `DIM_KHACH` / `KPI`.
- *Kiểm:* **cộng cột `Khách mua mồi` phải ra đúng 214.** Dòng đầu (sau khi làm
  P1-4) phải là *GÓI TIẾT KIỆM - XÓA CHÂN MÀY TRỌN GÓI* với 88 khách.

**P0-4 · Sửa chart "CLV theo kênh tiếp cận" (trang 3)** — mục 11
- Data source → `KPI`.
- Dimension = `phạm vi`; Metric = **`CLV_TB`** (đang là `lead` — đây là lỗi).
- Aggregation của metric: **`AVG` hoặc `MAX`, KHÔNG `SUM`** (mỗi kênh 1 dòng nên
  ba cái ra cùng kết quả, nhưng đặt `SUM` là để lại bẫy cho lần sau).
- Add filter: **`phạm vi` `!=` `TỔNG`** — thiếu bước này thì cột TỔNG nuốt thang đo.
- Không có date range dimension.
- *Kiểm:* 4 cột, cao nhất là **Khách cũ 6.428.000**, thấp nhất **TikTok 2.541.250**.
  Không còn cột `TỔNG`. Thứ tự **ngược** với hiện tại — đó là dấu hiệu đã sửa đúng.

**P0-5 · Trỏ 6 thẻ số sang bảng `KPI`** — mục 3
- Áp cho: `Lượng Lead` · `Tỷ lệ hẹn` · `Tỷ lệ chốt` · `Doanh thu quy về Lead`
  (trang 1) · `ROAS` · `CAC` (trang 2).
- Mỗi thẻ: Data source → `KPI`; filter **`phạm vi` `=` `TỔNG`**; Date Range
  Dimension = `None`.
- Metric tương ứng: `lead` · `tỷ_lệ_hẹn_%` · `tỷ_lệ_chốt_%` · `doanh_thu_quy_kết`
  · `ROAS` · `CAC`.
- Làm luôn với 3 thẻ trang 3 (`CLV_TB` · `tỷ_lệ_quay_lại_%` · `upsell_90d_%`) —
  hiện đang gần đúng nhưng lệch ở số thập phân, cùng nguyên nhân.
- *Kiểm:* số phải là **2.380 · 12,73% · 7,82% · 610.372.500 · 4,18 · 784.516**.
  Rồi **kéo date range** — nếu số vẫn nhảy thì thẻ chưa thật trỏ vào `KPI`.

**P0-6 · Thêm thẻ "Doanh thu" (toàn bộ) vào trang 1** — mục 6
- Nguồn `KPI`, `phạm vi = TỔNG`, metric `doanh_thu_toàn_bộ` → **2.552.689.000đ**.
- Đặt ở **góc trên-trái**, và dời `Lượng Lead` sang phải (mục 13, việc 2).
- Ghi phụ đề dưới thẻ: *"gồm cả khách vãng lai"*; thẻ `Doanh thu quy về Lead` ghi
  *"chỉ phần quy kết về kênh — 23,9% tổng doanh thu"*.
- *Kiểm:* hai thẻ tiền cạnh nhau, tổng hiểu được ngay là 2,55 tỷ chứ không phải 579M.

### P1 — clear. Số đã đúng, giờ làm cho đọc được.

- **P1-1** · Caption chart "Doanh thu theo kênh" (trang 1): *"chỉ phần quy kết
  được — 75,5% doanh thu đến từ khách vãng lai không có hồ sơ lead"* — mục 7.
- **P1-2** · Line "Lead và đặt hẹn" → **Bar-Line 2 trục**; cắt điểm cuối
  (26/02, kỳ chưa trọn); chú thích điểm 01/01 *"gồm 20 lead khuyết ngày"* — mục 5.
- **P1-3** · Phễu: hiện cả số tuyệt đối `2.380 → 1.274 → 303 → 186` — mục 12.
- **P1-4** · Bảng dịch vụ mồi: format `%` cho cột UpSell, `—` cho null, thêm field
  tên rút gọn, **sắp theo `Khách mua mồi` giảm dần**, và thêm cột
  `bán_chéo_cùng_ngày` — mục 9 + 12.
- **P1-5** · Đổi legend `[F] 1_Có Inbox` → `Số lead`; đổi tên thẻ
  `Trung bình tỷ lệ chốt` → `Tỷ lệ chốt` — mục 11 + 12.
- **P1-6** · Lọc `chi phí > 0` trên hai bar ROAS/CAC theo kênh để bỏ 4–5 dòng
  rỗng — mục 12.
- **P1-7** · Xoay/nới nhãn trục cho hết cắt chữ ở cả 5 bar chart — mục 12.
- **P1-8** · Chú thích thẻ upsell: *"cohort chưa đủ 90 ngày quan sát — đây là cận
  dưới"* — mục 9.
- **P1-9** · Thống nhất date range `01/01 – 28/02/2026` trên cả 3 trang, và cho
  trang 2 một control hiện rõ (dù `KPI` không lọc được — để người xem biết kỳ nào)
  — mục 13.

### P2 — empowering. Làm sau, nhưng đây là phần biến dashboard thành công cụ ra quyết định.

- **P2-1** · Chuyển 4 thẻ quyết định ngân sách (Doanh thu · Tỷ lệ chốt · ROAS ·
  CAC) sang dạng có **delta so kỳ trước**; nếu có mục tiêu thì dùng **Bullet
  chart** — mục 13, việc 4.
- **P2-2** · Thêm chỉ số `bán_chéo_cùng_ngày_%` (19,2%) lên trang 3 — điểm mạnh
  lớn nhất của mảng dịch vụ mồi đang bị bỏ trắng — mục 9.
- **P2-3** · Bubble 3 điểm → bar chart CPL theo kênh — mục 12.
- **P2-4** · Bỏ 2 thẻ trùng phễu ở trang 1; sắp lại thứ tự thẻ theo mức độ quyết
  định — mục 13, việc 2–3.
- **P2-5** · Gom lại bố cục trang 2 (mảng trắng) và trang 3 (3 bar không so được
  với nhau) — mục 13, việc 6–7.
- **P2-6** · Thêm ghi chú định nghĩa cho mỗi thẻ tiền (4 phạm vi doanh thu ở mục 6)
  và ghi người sở hữu + nhịp cập nhật ở footer.

---

## Bộ mốc tự kiểm nhanh

Sau bất kỳ lần sửa chart nào, mở dashboard và kiểm 6 con số này. Lệch cái nào là
chart đó đang lấy sai nguồn hoặc bị lọc sai:

| Chỗ trên dashboard | Phải ra đúng |
|---|---|
| Thẻ Doanh thu (toàn bộ) | **2.552.689.000đ** |
| Phễu chặng 1 → 4 | **2.380 → 1.274 → 303 → 186** |
| Thẻ Tỷ lệ chốt | **7,82%** |
| Thẻ CLV trung bình | **5.396.710đ** |
| Cộng cột `Khách mua mồi` trong bảng dịch vụ mồi | **214** |
| Chart CLV theo kênh, cột cao nhất | **Khách cũ, 6.428.000đ** |

Ba con số đầu là **bất biến của pipeline** (xem [README.md](../README.md)) — sai
là hoặc dashboard lấy sai nguồn, hoặc pipeline đã vỡ. Ba con số sau phụ thuộc
`config.INVOICE_HISTORY_START`; đổi mốc đó thì cập nhật lại bảng này.
