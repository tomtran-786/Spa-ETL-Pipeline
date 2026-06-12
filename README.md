# Phun Xăm Vic — Sales Pipeline trên Google Sheets

Pipeline tổng hợp dữ liệu tư vấn (từ 5 nhân viên sales) và dữ liệu bán hàng (từ KiotViet) thành một dashboard Master duy nhất, phục vụ phân tích funnel conversion.

---

## Mục lục

- [Phần I — Hướng dẫn sử dụng](#phần-i--hướng-dẫn-sử-dụng)
  - [1. Cấu trúc file](#1-cấu-trúc-file)
  - [2. Quy trình hàng ngày](#2-quy-trình-hàng-ngày)
  - [3. Đọc kết quả ở Master](#3-đọc-kết-quả-ở-master)
  - [4. Đếm funnel đúng cách](#4-đếm-funnel-đúng-cách)
  - [5. Troubleshoot](#5-troubleshoot)
- [Phần II — Tài liệu kỹ thuật](#phần-ii--tài-liệu-kỹ-thuật)
  - [6. Kiến trúc tổng thể](#6-kiến-trúc-tổng-thể)
  - [7. Chuẩn hóa SĐT](#7-chuẩn-hóa-sđt-khóa-join)
  - [8. _KV_Block](#8-_kv_block--dòng-kv-driven)
  - [9. _Orphan_Block](#9-_orphan_block--dòng-orphan-lead)
  - [10. Master](#10-master--gộp-2-block)
  - [11. Phân nhóm MECE](#11-phân-nhóm-mece)
  - [12. Tradeoff và hạn chế](#12-tradeoff-và-hạn-chế)
  - [13. Maintenance](#13-maintenance)
  - [14. Lý do thiết kế (FAQ kỹ thuật)](#14-lý-do-thiết-kế-faq-kỹ-thuật)

---

# Phần I — Hướng dẫn sử dụng

## 1. Cấu trúc file

File có 10 sheet, trong đó 2 sheet ẩn (`_KV_Block`, `_Orphan_Block`) làm việc tính toán nền.

| Sheet | Vai trò | Ai dùng |
|---|---|---|
| `Hướng Dẫn` | README rút gọn trong file | Tất cả |
| `Master` | Dashboard đầu ra cuối cùng | Admin / Phân tích |
| `KiotViet` | Paste export raw từ KiotViet | Admin |
| `Đặng Đông` | Sheet nhập liệu của NV Đặng Đông | NV |
| `Huyền Trang` | Sheet nhập liệu của NV Huyền Trang | NV |
| `Trường Khang` | Sheet nhập liệu của NV Trường Khang | NV |
| `Hoàng Diễm` | Sheet nhập liệu của NV Hoàng Diễm | NV |
| `Mai Thy` | Sheet nhập liệu của NV Mai Thy | NV |
| `Danh Mục` | Tham khảo danh sách dropdown | Admin |
| `_KV_Block` (ẩn) | Helper — sinh 1 dòng/HĐ | Backend |
| `_Orphan_Block` (ẩn) | Helper — sinh 1 dòng/lead không match HĐ | Backend |

## 2. Quy trình hàng ngày

### Cho nhân viên sales

1. Mở file Google Sheet, vào sheet **mang tên mình**.
2. Mỗi inbox = 1 dòng mới. Điền theo thứ tự:
   - **Ngày Lead** (cột A): nhập ngày khách nhắn
   - **Mã vùng** (cột B): bấm ▼ chọn `+84` (mặc định)
   - **Số ĐT** (cột C): nhập số (vd `0390000001` hoặc `390000001` đều được)
   - **Tên khách hàng** (cột D): nhập tên
   - **LOẠI TIN NHẮN** (cột F): bấm ▼ chọn
   - **NHÓM SP** (cột G): bấm ▼ chọn `DỊCH VỤ` hoặc `ĐÀO TẠO`
   - **NGUỒN** (cột H): bấm ▼ chọn kênh khách đến từ đâu
   - **QUAN TÂM** (cột I): bấm ▼ chọn dịch vụ khách hỏi
   - **TÌNH TRẠNG** (cột J): bấm ▼ chọn trạng thái lead
   - **NGÀY HẸN** (cột K): nhập nếu có hẹn cụ thể

3. **KHÔNG sửa** các cột màu vàng:
   - Cột E (SĐT Cuối) — tự chuẩn hóa
   - Cột L (CHATPAGE) — tự điền tên NV

### Cho admin

1. Cuối ngày / cuối tuần, export hóa đơn từ KiotViet ra CSV.
2. Vào sheet `KiotViet`, click ô A2, Ctrl+V để paste toàn bộ CSV (cả header lẫn data đều được).
3. Master tự cập nhật. Có thể mất 10-30 giây để recalc xong.

## 3. Đọc kết quả ở Master

Mỗi dòng trong Master = 1 đơn vị phân tích, có thể là:

- **1 hóa đơn** (khách đã mua) — cột J `Mã hóa đơn` có giá trị
- **1 lead chưa ra đơn** (khách inbox nhưng chưa mua) — cột J trống, cột P `Phễu` = "Không có hóa đơn"

24 cột của Master:

| Cột | Tên | Ý nghĩa |
|---|---|---|
| A | SĐT Cuối | SĐT đã chuẩn hóa, dùng làm khóa join |
| B | Ngày Lead | Ngày NV ghi nhận lead |
| C | Thời gian (HĐ) | Ngày phát sinh hóa đơn (nếu có) |
| D | CHATPAGE | NV nào tư vấn |
| E-I | Thông tin lead | Loại tin nhắn, nhóm SP, nguồn, quan tâm, tình trạng |
| J-M | Thông tin HĐ | Mã HĐ, Mã KH, Tên hàng, Doanh thu |
| N | NGÀY HẸN | Ngày hẹn đến cửa hàng |
| O | Thời gian ra đơn (Ngày) | Số ngày từ lead → mua |
| P | Phễu | TRUE/FALSE/"Không có hóa đơn" |
| Q-S | NHÓM SP_Clean, Kênh Tiếp Cận, Phân loại sản phẩm | Phân loại auto |
| T-W | [F]1 → [F]4 | 4 cờ funnel (0/1) |
| X | Phân nhóm MECE | Nhãn nhóm 0-5 (xem mục 11) |

## 4. Đếm funnel đúng cách

**Vấn đề:** Một SĐT có thể có nhiều dòng (vì mua nhiều HĐ). Nếu SUM cờ funnel thẳng → đếm trùng.

**Giải pháp:** Thêm 2 cột helper vào Master để chọn đúng "góc nhìn":

### Setup 1 lần

Vào Master, gõ vào ô:
- **Y1:** `Lead_Unique_Flag`
- **Z1:** `HĐ_Unique_Flag`
- **Y2:** `=ARRAYFORMULA(IF(A2:A="",,IF(COUNTIF(A$2:A2,A2:A)=1,1,0)))`
- **Z2:** `=ARRAYFORMULA(IF(A2:A="",,IF(J2:J<>"",1,0)))`

### Cách hoạt động

```
Cờ Y = "Đây có phải dòng ĐẦU TIÊN của SĐT này không?"
       → SUM(Y) = số KHÁCH unique

Cờ Z = "Dòng này có Mã HĐ không?"
       → SUM(Z) = số HÓA ĐƠN
```

Ví dụ: khách A inbox 1 lần, mua combo 3 HĐ. Master sẽ có 3 dòng cùng SĐT A.
- Y = `1, 0, 0` → tổng 1 (đếm 1 khách) ✓
- Z = `1, 1, 1` → tổng 3 (đếm 3 HĐ) ✓

### Công thức dùng 2 cờ này

| Câu hỏi | Công thức |
|---|---|
| Bao nhiêu **khách** unique có inbox? | `=SUMIFS(T:T, Y:Y, 1)` |
| Bao nhiêu **khách** unique có hẹn? | `=SUMIFS(V:V, Y:Y, 1)` |
| Bao nhiêu **khách** unique mua hàng? | `=SUMIFS(W:W, Y:Y, 1)` |
| Bao nhiêu **hóa đơn** đã bán? | `=SUM(Z:Z)` |
| Tổng doanh thu | `=SUM(M:M)` |
| Tỷ lệ chốt = khách mua / khách inbox | `=SUMIFS(W:W,Y:Y,1) / SUMIFS(T:T,Y:Y,1)` |

> **Luôn dùng cờ Y khi tính funnel conversion** để khử trùng theo SĐT, không thì tỷ lệ sẽ bị méo.

## 5. Troubleshoot

| Triệu chứng | Nguyên nhân | Fix |
|---|---|---|
| Cột N (KiotViet) ra `#NAME?` | File đang ở Office Compatibility mode | File → Save as Google Sheets (icon X chuyển thành G) |
| Cột Ngày Lead / NGÀY HẸN ở Master hiện số `46023` thay vì `04/01/2026` | QUERY strip date format khi gộp mảng | Click header cột → Format → Number → Date |
| Lead đã nhập nhưng không lên Master | SĐT NV gõ không match với KiotViet | Kiểm tra SĐT Cuối ở cột E sheet NV vs cột N sheet KiotViet — phải giống hệt |
| Master load chậm | Đang recalc 100k formula | Đợi 10-30 giây lần đầu, sau đó nhanh dần |
| Vượt 1500 dòng KiotViet | Hết capacity của _KV_Block | Xem mục 13 "Mở rộng capacity" |

---

# Phần II — Tài liệu kỹ thuật

## 6. Kiến trúc tổng thể

```
┌─────────────────┐         ┌──────────────────────────┐
│  KiotViet       │         │  5 sheet NV              │
│  (paste raw)    │         │  (NV gõ + dropdown)      │
│  Mỗi HĐ 1 dòng  │         │  Mỗi lead 1 dòng         │
│                 │         │                           │
│  Cột N tự       │         │  Cột E tự chuẩn hóa SĐT  │
│  chuẩn hóa SĐT  │         │  Cột L tự điền CHATPAGE  │
└────────┬────────┘         └──────────┬───────────────┘
         │                              │
         ▼                              ▼
    ┌─────────────────────────────────────────┐
    │  2 sheet ẨN làm việc nền                │
    │                                          │
    │  ┌──────────────┐    ┌────────────────┐ │
    │  │ _KV_Block    │    │ _Orphan_Block  │ │
    │  │              │    │                 │ │
    │  │ 1500 dòng    │    │ 5 × 500 = 2500 │ │
    │  │ (1 dòng/HĐ)  │    │ (1 dòng/lead   │ │
    │  │              │    │  không có HĐ)  │ │
    │  └──────┬───────┘    └────────┬───────┘ │
    │         │                     │          │
    └─────────┼─────────────────────┼──────────┘
              │                     │
              └──────────┬──────────┘
                         │
                         ▼
                ┌────────────────┐
                │  Master        │
                │  QUERY gộp 2   │
                │  block, lọc rỗng│
                └────────────────┘
```

**Vấn đề cốt lõi:** Hai nguồn data lệch nhau và phải JOIN qua SĐT.

- KiotViet = bằng chứng KHÁCH MUA, không có thông tin lead
- Sheet NV = bằng chứng KHÁCH HỎI, không biết có mua không

Một khách xuất hiện ở:
- Chỉ KiotViet → **Nhóm 1** (vãng lai)
- Chỉ NV → **Nhóm 0/2/4** (lead chưa chốt)
- Cả 2 → **Nhóm 3/5** (lead chốt được)

## 7. Chuẩn hóa SĐT (khóa join)

**Quy tắc:** `"0" + (strip mọi ký tự không phải số → strip mọi số 0 đầu)`

**Formula:**
```
=IF(C2="","","0" & REGEXREPLACE(REGEXREPLACE(C2&"","[^0-9]",""),"^0+",""))
```

**Test:**
```
KiotViet: "0390000001"   →  "0390000001"
NV gõ:    "390000001"    →  "0390000001"
NV gõ:    "(+84) 389..." →  "084389..."  (case này train NV không gõ +84)
```

**Vị trí:**
- KiotViet cột **N** — cố tình đặt ngoài vùng paste của CSV (CSV có 13 cột do trailing comma, paste sẽ chiếm A:M)
- NV cột **E** — đặt sau cột Tên khách hàng

## 8. _KV_Block — dòng KV-driven

**Mục đích:** Với mỗi HĐ trong KiotViet, sinh 1 dòng output có 24 cột (đầy đủ thông tin HĐ + lookup thông tin lead).

**Pre-allocate:** 1500 dòng × 24 cột = 36.000 ô formula.

**Layout 1 dòng:**

| Cột | Logic |
|---|---|
| 1 (SĐT) | `=KiotViet!N{r}` — pull thẳng |
| 2 (Ngày Lead) | Chain lookup qua 5 NV |
| 3 (Thời gian HĐ) | `=KiotViet!B{r}` |
| 4 (CHATPAGE) | Chain lookup qua 5 NV cột L |
| 5-9 | Chain lookup các cột thông tin lead |
| 10-12 | `=KiotViet!A{r}/C{r}/I{r}` (Mã HĐ, Mã KH, Tên hàng) |
| 13 (Doanh thu) | `=IFERROR(VALUE(SUBSTITUTE(KiotViet!G{r}&"",".","")),KiotViet!G{r})` — xử lý format VN `9.420.000` |
| 14 (NGÀY HẸN) | Chain lookup |
| 15 (TG ra đơn) | `=IF(...,Thời gian HĐ - Ngày Lead,"")` |
| 16 (Phễu) | `=REGEXMATCH(Tên hàng, "GÓI TIẾT KIỆM|Xóa lần 01|CO2 Fractional")` |
| 17 (NHÓM SP_Clean) | Ưu tiên NV input; fallback derive từ Tên hàng |
| 18 (Kênh Tiếp Cận) | Derive từ NGUỒN (Fanpage→Facebook, Tiktok→Tiktok, v.v.) |
| 19 (Phân loại SP) | REGEXMATCH chain trên Tên hàng |
| 20-23 (Funnel flags) | Đơn giản: cờ 1 nếu cột tương ứng không rỗng |
| 24 (MECE) | IF chain trên CHATPAGE + NGÀY HẸN |

### Chain lookup — pattern lõi

Không thể union 5 sheet NV bằng formula thuần (ARRAYFORMULA bị lỗi khi parse từ xlsx). Thay vào đó, mỗi cột cần lookup thử lần lượt qua 5 sheet:

```
=IF(SĐT="","",
  IFNA(INDEX('Đặng Đông'!A:A, MATCH(SĐT, 'Đặng Đông'!E:E, 0)),
   IFNA(INDEX('Huyền Trang'!A:A, MATCH(SĐT, 'Huyền Trang'!E:E, 0)),
    IFNA(INDEX('Trường Khang'!A:A, MATCH(SĐT, 'Trường Khang'!E:E, 0)),
     IFNA(INDEX('Hoàng Diễm'!A:A, MATCH(SĐT, 'Hoàng Diễm'!E:E, 0)),
      IFNA(INDEX('Mai Thy'!A:A, MATCH(SĐT, 'Mai Thy'!E:E, 0)),
       ""))))))
```

NV nào ghi SĐT trước → thông tin lead lấy từ sheet đó.

## 9. _Orphan_Block — dòng orphan lead

**Mục đích:** Tìm các lead NV đã ghi nhưng SĐT không match HĐ nào trong KiotViet.

**Pre-allocate:** 5 NV × 500 slot/NV = 2500 dòng × 24 cột = 60.000 ô formula.

**Layout:**

```
Dòng 2-501:    check orphan cho 'Đặng Đông' dòng 2-501
Dòng 502-1001: check orphan cho 'Huyền Trang' dòng 2-501
Dòng 1002-1501: 'Trường Khang'
Dòng 1502-2001: 'Hoàng Diễm'
Dòng 2002-2501: 'Mai Thy'
```

**Điều kiện orphan trong từng ô:**
```
AND('NV'!E{src}<>"", COUNTIF(KiotViet!N$2:N$1501, 'NV'!E{src})=0)
```
Dịch: SĐT của NV không rỗng AND SĐT đó không xuất hiện trong cột N của KiotViet.

**Mỗi ô có pattern:** `=IF(orphan_condition, value, "")` — nếu orphan thì pull data, không thì để rỗng (Master sẽ filter).

## 10. Master — gộp 2 block

Chỉ có **1 formula duy nhất** ở ô A2:

```
=QUERY(
  {_KV_Block!A2:X1501; _Orphan_Block!A2:X2501},
  "select * where Col1 is not null and Col1 <> ''",
  0
)
```

- `{ ... ; ... }` = stack vertical 2 bảng
- `QUERY(..., "where Col1 is not null and Col1 <> ''", 0)` = lọc bỏ dòng có SĐT rỗng

## 11. Phân nhóm MECE

| Nhóm | Có CHATPAGE | Có SĐT | Có Hẹn | Có HĐ | Ý nghĩa |
|---|---|---|---|---|---|
| 0 | ❌ | ❌ | ❌ | ❌ | Lead chưa có SĐT (hiếm, vì không SĐT thì không vào pipeline) |
| 1 | ❌ | ✅ | ❌ | ❌ | Vãng lai, chỉ có HĐ |
| 2 | ✅ | ✅ | ❌ | ❌ | Có SĐT nhưng chưa hẹn & chưa chốt |
| 3 | ✅ | ✅ | ❌ | ✅ | Chốt thẳng không cần hẹn |
| 4 | ✅ | ✅ | ✅ | ❌ | Đặt hẹn nhưng rớt |
| 5 | ✅ | ✅ | ✅ | ✅ | Lead hoàn hảo (đủ 3 bước) |

Logic implement: IF chain trên 2 biến `has_lead` (CHATPAGE) và `has_hen` (NGÀY HẸN) trong _KV_Block; biến `has_hen` và `has_sdt` trong _Orphan_Block.

## 12. Tradeoff và hạn chế

### Case 1: 1 SĐT có nhiều lead (NV ghi nhiều dòng), 1 HĐ
- Pipeline ra 1 dòng (theo HĐ), chain lookup chỉ pull lead info đầu tiên
- ✅ Không double count
- ❌ Mất các lần inbox khác

### Case 2: 1 SĐT 1 lead, mua nhiều HĐ ← Đếm trùng funnel
- Pipeline ra N dòng (theo N HĐ), mỗi dòng cùng thông tin lead
- ❌ SUM cờ funnel [F]1/[F]3 sẽ bị inflate
- ✅ Doanh thu đúng (sum theo HĐ là đúng)

**Giải pháp:** Dùng cờ Y/Z như mục 4 để chọn đúng góc nhìn count.

### Hạn chế khác

- ARRAYFORMULA bị lỗi `#NAME?` khi parse từ xlsx ghi bởi openpyxl → phải dùng per-cell formulas, file ~1MB và load 10-30s lần đầu.
- Thêm/bớt NV cần sửa chain lookup (extend số tầng IFNA) — không tự động.
- Không xử lý case khách quay lại sau lâu (vd 6 tháng) — vẫn coi là cùng 1 SĐT lead.

## 13. Maintenance

### Mở rộng capacity KiotViet (>1500 HĐ)

1. Vào sheet `_KV_Block`, chọn dòng 1501 (dòng cuối có formula)
2. Copy toàn bộ dòng đó
3. Paste xuống các dòng 1502, 1503, ...
4. Vào sheet `KiotViet` cột N, copy ô N1501, paste xuống tiếp
5. Update formula Master A2: đổi `X1501` thành số mới

### Mở rộng capacity NV (>500 lead/NV)

Phức tạp hơn — cần extend cả `_Orphan_Block` (mỗi NV chiếm 500 slot liên tiếp). Khuyến nghị rebuild file qua script Python.

### Thêm NV mới

1. Tạo sheet mới copy từ 1 sheet NV có sẵn, đổi tên thành tên NV mới
2. Update cột L (CHATPAGE auto): sửa formula thành `=IF(A{r}="","","Tên NV mới")` cho từng dòng
3. Vào `_KV_Block`, sửa chain lookup ở mọi cột dùng chain (cột 2, 4, 5, 6, 7, 8, 9, 14): thêm 1 tầng IFNA cho NV mới
4. Vào `_Orphan_Block`, allocate thêm 500 dòng cho NV mới (ở cuối), copy logic từ block 1 NV cũ

→ Đây là lúc cần rebuild file bằng script Python.

### Đổi keyword Phễu

1. Edit → Find and replace (Ctrl+H)
2. Tìm: `GÓI TIẾT KIỆM|Xóa lần 01|CO2 Fractional`
3. Thay: regex mới
4. "Also search within formulas" = ON, "Search" = "All sheets"

### Thêm cột data NV cần ghi

1. Click chuột phải header cột → Insert column left/right
2. Gõ header
3. Lặp lại cho cả 5 sheet NV — **GG Sheets tự shift reference**, Master không cần đụng

## 14. Lý do thiết kế (FAQ kỹ thuật)

**Tại sao per-cell formulas thay vì ARRAYFORMULA?**

ARRAYFORMULA viết từ openpyxl (Python lib tạo xlsx) bị Google Sheets parse ra `#NAME?`. Quirk này không document rõ trong openpyxl. Per-cell formulas là cách workaround bulletproof: mỗi ô độc lập, không phụ thuộc array spreading.

Trade off: 96k cell formulas thay vì ~5 ARRAYFORMULA, file ~1MB, load chậm hơn ban đầu. Đổi lại: chạy ổn định mọi lúc.

**Tại sao chain IFNA(INDEX/MATCH) thay vì VLOOKUP với array literal `{}`?**

Lý do tương tự — array literal `{D:D, A:A}` cũng bị lỗi tương tự khi ghi từ openpyxl. INDEX/MATCH với open range hoạt động ổn định.

**Tại sao cột N (SĐT Cuối) ở KiotViet đặt xa thế?**

CSV của KiotViet có 13 cột (10 cột data + 3 trailing comma). Paste sẽ chiếm A:M. Đặt N để không bị paste đè.

**Tại sao 2 sheet block phải ẩn?**

Tránh user vô tình edit. Cũng để tab bar gọn hơn. Cần xem: View → Show hidden sheets.

**Tại sao QUERY ở Master không dùng ARRAYFORMULA wrapper?**

QUERY tự return 2D array, không cần ARRAYFORMULA. Đây là exception duy nhất hoạt động ổn định khi ghi từ openpyxl.

**Tại sao không dùng Apps Script?**

Yêu cầu của user là "formula thuần, không code". Apps Script linh hoạt hơn nhưng cần permission, harder để debug khi NV không phải dev.

---

## Build từ đầu (cho dev)

Pipeline được generate bằng Python script `build_v3.py` dùng openpyxl. Để rebuild khi thay đổi cấu trúc lớn (thêm/bớt NV, đổi capacity):

```bash
python3 build_v3.py
# Output: Phun_Xam_Vic_Pipeline_v3.xlsx
```

Upload lên Google Drive, mở bằng Google Sheets, mọi formula tự chạy.

---

*Pipeline thiết kế để chạy formula-only trên Google Sheets, không cần Apps Script hay backend riêng.*
