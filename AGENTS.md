# Context cho phiên làm việc sau

Pipeline phân tích sales/marketing cho spa Phun Xăm Vic. Đọc file này trước khi
sửa gì — phần lớn quyết định ở đây trông tùy tiện nếu không biết bối cảnh, và
có vài cái bẫy dữ liệu chỉ lộ ra khi chạy thật.

Tài liệu khác: [README.md](README.md) kiến trúc · [RUNBOOK.md](RUNBOOK.md) vận
hành · [apps_script/HUONG_DAN_CAI_DAT.md](apps_script/HUONG_DAN_CAI_DAT.md) cài đặt.

---

## Con số bất biến — đổi là có bug

Chạy `python -m pxv.run_daily` (backend local) phải luôn ra:

| Chỉ số | Giá trị |
|---|---|
| Doanh thu | **2.552.689.000đ** |
| Hóa đơn unique | **710** |
| Phễu | **2364 → 1274 → 303 → 186** |
| Tỷ lệ chốt | **7,87%** |
| CLV TB | 5.689.481đ (594 khách, 27,4% quay lại) |
| Dịch vụ mồi | 290 khách, 24,8% upsell 90 ngày |

`tests/test_golden.py` đối chiếu với `output/Master_Pipeline_2026.xlsx`. File đó
chứa dữ liệu khách nên **nằm ngoài git** — test tự skip khi không có, nên CI chạy
107 passed + 7 skipped còn máy local 122 passed.

**Sửa bất cứ gì trong `pxv/` xong phải chạy lại và so 3 số đầu.** Lệch mà không
giải thích được = đã phá thứ gì đó.

---

## Bẫy dữ liệu — đã trả giá để biết

**`clean_phone("0")` từng trả `"0"` và được dùng làm khóa join.** KiotViet ghi
`0` khi không có SĐT, nên 4 khách khác nhau bị gộp thành một người. Giờ trả
`None`. Đừng "sửa" lại thành trả chuỗi.

**Hóa đơn không có SĐT vẫn phải tính doanh thu** (81tr trong cửa sổ T1-T2/2026).
Chúng đi qua `_prepare_orphan_invoices()`, không qua merge. Lý do: `pandas` coi
mọi `NaN` là TRÙNG NHAU khi `duplicated()`, nên gộp chung sẽ khử trùng nhầm.

**`Khách cần trả` của KiotViet là TỔNG hóa đơn lặp trên từng dòng mặt hàng**,
không phải tiền từng món. `HD026957` có 2 dòng cùng ghi 3.000.000. Tiền chỉ giữ
ở dòng đầu mỗi hóa đơn (`io_*.load_invoices`). Cộng thẳng là nhân đôi.

**Số quốc tế phải giữ, không bỏ.** Có khách Việt kiều xuất hiện ở cả lead lẫn
hóa đơn. VN → `0XXXXXXXXX`, quốc tế → `+XXXX`, rác → `None`.

**File CSV lead cũ bị LỆCH CỘT khi export.** Ba cột cùng tên `TRẠNG THÁI`:

| Cột | Số dòng | Thực chất |
|---|---|---|
| `TRẠNG THÁI` | 0 | cột thừa, bỏ |
| `TRẠNG THÁI.1` | 2 | cột `TRẠNG THÁI` thật |
| `TRẠNG THÁI.2` | 1.280 | **TÊN NHÂN VIÊN** → `TƯ VẤN - SALE` |

Nhận diện bằng **nội dung**, không bằng vị trí. Xem `schema.rename_status_columns`.

**Sheet gốc có HAI cột trạng thái riêng biệt** dùng chung một dropdown 11 giá
trị (`TÌNH TRẠNG` = tình trạng tương tác, `TRẠNG THÁI` = trạng thái xử lý), cộng
`TƯ VẤN - SALE` và `THÔNG TIN KHÁCH`. **Không** phải 3 chặng Quan tâm → Đặt hẹn
→ Chốt đơn — giả định đó từng sai và đã bỏ.

**`NGÀY HẸN` cũ ghi thiếu năm** (`10/01`, `22/1`): 327/328 dòng không parse
được. `parse_date_vn(value, sau_ngay)` suy năm sao cho hẹn ≥ ngày lead. Không
truyền `sau_ngay` thì vẫn trả `NaT` — cố tình, không đoán bừa.

**T12/2025 mất toàn bộ hóa đơn**, không khôi phục được. `config.KNOWN_DATA_GAPS`
bỏ qua tháng này khi kiểm thủng tháng. Biểu đồ theo thời gian phải vẽ khoảng
trống có nhãn, **không phải doanh thu = 0**.

**~75% doanh thu đến từ khách vãng lai không có hồ sơ lead.** Đừng dùng ROAS
theo kênh làm mẫu số cho toàn bộ doanh thu.

---

## Bẫy kỹ thuật

**`khoa is None` không dùng được cho giá trị từ pandas.** Tùy phiên bản, `apply()`
biến `None` thành `NaN` và `is None` trả `False`. Dùng `isinstance(x, str)` hoặc
`pd.isna()`. Đây là lỗi từng xanh ở máy nhưng đỏ trên CI.

**Sheet rỗng cho cột dtype `object`, không phải `datetime64`.** `datetime - object`
ném `TypeError` ở chỗ cách xa nguyên nhân. `build_master` ép `to_datetime` trước
khi trừ, và `quality._check_nguon_co_du_lieu` báo rõ ngay từ đầu.

**Ghi Sheets phải dùng `value_input_option='RAW'`** + đặt cột định danh thành
text. Mặc định `USER_ENTERED` biến `'9.420.000'` thành `9.42` và `'0389...'` mất
số 0.

**CSV cho Excel phải có BOM (`utf-8-sig`).** Không có thì Excel Mac đọc bằng Mac
Roman: `NGÀY` → `NG√ÄY`. Script migrate ghi cả `.xlsx` (không có khái niệm bảng
mã) và đó là bản nên dùng.

**`onEdit` không được `setValue()` khi sửa nhiều ô.** Google không cấp
`e.oldValue` cho vùng nhiều ô, và `range.setValue('')` ghi rỗng lên TOÀN BỘ vùng.
Bản cũ làm vậy nên paste 50 dòng mất trắng 50. Giờ chỉ hoàn tác khi sửa đúng 1 ô.

**Hàm chuẩn hóa SĐT tồn tại HAI bản** — `pxv/clean.py` và
`apps_script/IngestPancake.gs::_chuanHoaSdt`. Lệch nhau là join hỏng âm thầm.
Sửa một bên phải sửa bên kia; đã đối chiếu 3.667 số thật, 0 lệch.

**`pandas<3.0`** ghim trong `requirements.txt` — bản 3.0 đổi nhiều hành vi mặc
định, mà pipeline này lấy tính đúng của con số làm sản phẩm.

---

## Nguyên tắc thiết kế

**Pipeline chủ động DỪNG khi dữ liệu sai.** GitHub chỉ gửi mail khi job crash.
Sự im lặng chính là thứ làm mất trọn T12/2025 mà 7 tháng sau mới phát hiện.
20 phép kiểm trong `quality.py`, 10 có thể DỪNG job.

**Phễu chỉ tính trên khách TỪNG INBOX.** Vãng lai chưa nhắn tin nên không thuộc
phễu marketing — để chung thì F4 > F3, phễu nở ra ở bước sau, vô lý.

**CLV và funnel mồi tính sẵn ở pipeline, không đẩy sang Looker.** `MASTER` có
mỗi dòng là cặp (SĐT × hóa đơn) nên khách mua 5 lần chiếm 5 dòng — `AVG(CLV)`
trên đó chia sai mẫu số.

**Không tự đoán năm khi ngày trông sai.** Code cũ ép `2025-Q1 → 2026` để vá 35
dòng; sang 2027 sẽ âm thầm bóp méo dữ liệu thật. Giờ đẩy vào bảng `CẦN_SỬA`.

**Quy tắc nghiệp vụ là DỮ LIỆU, không phải if-chain.** `mappings.py` + tab
`DANH_MỤC`. Danh sách dịch vụ mồi và cách gom kênh đổi theo chiến dịch.

**Ghép tên Pancake chặt tới mức bỏ sót còn hơn ghép sai.** Chỉ ghép khi tên
chuẩn hóa xuất hiện đúng 1 lần ở CẢ HAI phía; không so gần đúng; không ghi đè số
đã có. **Mặc định tắt** (`PXV_PANCAKE=1` để bật) vì không có dữ liệu thật để
kiểm chất lượng ghép. Đo trên tên thật: nếu Pancake phủ 60% thì vá được 53,9%,
trần cứng là 9,6% lead trùng tên nhau.

---

## Trạng thái

`main` = 44 file tracked, 122 test (local) / 107+7skip (CI). Remote đã có lại.

Lịch sử git **đã dọn PII** bằng `git filter-repo` — repo từng public và lộ tên +
SĐT của ~8.000 khách. Backup lịch sử cũ ở `../PXV-backup-*.bundle`.
**Không bao giờ commit `*.csv`/`*.xlsx`/`output/`.** Test dùng fixture bịa; đã
từng lỡ copy 2 SĐT và 4 tên khách thật vào test rồi phải rewrite history lần hai.

### Đang chặn

1. **Sheet `LEAD` rỗng** → chạy `scripts/migrate_lead_csv.py` rồi File → Import
   bản `.xlsx` vào ô A2 (bỏ tick "Convert text to numbers").
2. **3 biến `PXV_SHEET_*` chưa khai** trên GitHub → tab Variables.
   `GCP_SA_KEY` đã đúng (`pxvclient@phunxamvic.iam.gserviceaccount.com`).
3. **35 dòng ghi `NGÀY = 19/01/2025`** — cùng một ngày trong file lẽ ra là 2026,
   nghi gõ nhầm năm hàng loạt. Chưa quyết định sửa hay giữ.
4. `.DS_Store` lỡ được commit (`22f6ce4`) — nên xóa và thêm vào `.gitignore`.

### Chưa làm (theo plan)

- GĐ4: đối chiếu 2 backend trên Sheets (cần data trong sheet trước)
- GĐ6: test phá hoại có chủ đích — 8 kịch bản, làm trên **bản sao** sheet
- Dựng dashboard Looker Studio

Lưu ý GĐ4: hai backend **cố tình khác nhau** — `io_local` gộp 2 nguồn hẹn,
`io_sheets` chỉ dùng 1. Chênh đúng 4 SĐT. Đòi khớp tuyệt đối toàn bộ sẽ đỏ oan;
chỉ tiền/hóa đơn/DIM_KHACH/FUNNEL_MOI mới bất biến.

---

## Lệnh hay dùng

```bash
python -m pytest tests/ -q                 # 122 test
python -m pxv.run_daily                    # backend local
python -m pxv.check                        # kiểm kết nối Sheets (cần GCP_SA_KEY)
python scripts/migrate_lead_csv.py <csv>   # chuyển lead cũ sang định dạng mới
PXV_BACKEND=sheets python -m pxv.run_daily # chạy trên Google Sheets
```

Kiểm cú pháp Apps Script (node từ chối đuôi `.gs`, phải đổi sang `.js`):

```bash
for f in apps_script/*.gs; do cp "$f" "/tmp/$(basename $f .gs).js"; node --check "/tmp/$(basename $f .gs).js"; done
```

---

## Cách làm việc mà user này thích

Viết tiếng Việt. Ưu tiên **kiểm chứng bằng dữ liệu thật** hơn là suy đoán — nhiều
lần trong phiên trước, chạy thử đã lật ngược giả định (cột `TRẠNG THÁI`, mức độ
hiệu quả Pancake, nguyên nhân lỗi font). Nói thẳng khi phát hiện vấn đề trong
chính việc mình vừa làm. Commit message giải thích **vì sao**, không chỉ *cái gì*.
