# Sổ tay vận hành — Pipeline Phun Xăm Vic

Tài liệu này dành cho **người không làm kỹ thuật**. Mỗi tình huống có tối đa 5 bước.

Nếu làm hết các bước mà vẫn không xong → xem mục [Khi nào cần gọi người kỹ thuật](#khi-nào-cần-gọi-người-kỹ-thuật) ở cuối.

> 📷 Chỗ nào ghi `[Ảnh: ...]` là nên chụp màn hình dán vào khi cài xong, để người sau dễ theo.

---

## Mục lục

**Việc hằng ngày**
- [Kế toán: export hóa đơn KiotViet](#kế-toán-export-hóa-đơn-kiotviet)
- [Sales: nhập lead](#sales-nhập-lead)

**Khi có sự cố**
- [Dashboard không cập nhật / số bị cũ](#dashboard-không-cập-nhật--số-bị-cũ)
- [Nhận email cảnh báo — tra theo tiêu đề](#nhận-email-cảnh-báo--tra-theo-tiêu-đề)
- [Số doanh thu trông sai](#số-doanh-thu-trông-sai)
- [Sales bị chặn không nhập được](#sales-bị-chặn-không-nhập-được)

**Việc định kỳ**
- [Thêm nguồn quảng cáo mới](#thêm-nguồn-quảng-cáo-mới)
- [Đổi danh sách dịch vụ mồi](#đổi-danh-sách-dịch-vụ-mồi)
- [Nhập chi phí quảng cáo hằng tháng](#nhập-chi-phí-quảng-cáo-hằng-tháng)
- [Nhân viên mới / nghỉ việc](#nhân-viên-mới--nghỉ-việc)

**Đọc hiểu**
- [Ý nghĩa các con số trên dashboard](#ý-nghĩa-các-con-số-trên-dashboard)
- [Khi số trên dashboard khác số trong sheet](#khi-số-trên-dashboard-khác-số-trong-sheet)
- [Những chỗ dữ liệu đã biết là thiếu](#những-chỗ-dữ-liệu-đã-biết-là-thiếu)
- [Khi nào cần gọi người kỹ thuật](#khi-nào-cần-gọi-người-kỹ-thuật)

---

# Việc hằng ngày

## Kế toán: export hóa đơn KiotViet

Làm mỗi ngày, mất khoảng 2 phút. Sáng 8h sẽ có email nhắc.

1. Mở KiotViet → **Báo cáo** → **Chi tiết hóa đơn**
2. Chọn khoảng ngày. **Lấy rộng hơn vài ngày cũng không sao** — hệ thống tự bỏ phần trùng, không cộng đôi doanh thu
3. Bấm **Xuất file** → chọn **CSV**
4. Kéo thả file vừa tải vào thư mục Google Drive **`KiotViet_Drop`**
5. Xong. Không cần đổi tên file.

**Trong vòng 1 tiếng** hệ thống tự nạp. Nếu file có vấn đề, bạn sẽ nhận email báo.

> ⚠️ **Quên một hôm không sao** — hôm sau chỉ cần chọn khoảng ngày rộng ra là bù được. Nhưng **đừng quên cả tháng**: tháng 12/2025 đã mất trọn vẹn vì không ai để ý, và giờ KiotViet không cho export lại nữa.

---

## Sales: nhập lead

Mỗi khách nhắn tin = 1 dòng mới trong sheet **LEAD**.

1. Gõ nội dung vào dòng trống tiếp theo — **cột NGÀY tự điền**, không cần gõ
2. Nhập **SỐ ĐT** nếu xin được. Chưa xin được thì chọn lý do ở cột **LÝ DO CHƯA CÓ SĐT**
3. Chọn **NGUỒN** từ danh sách xổ xuống (gõ sai chính tả hệ thống tự sửa)
4. Khi khách đồng ý đến, đổi **TRẠNG THÁI** thành `ĐẶT HẸN` và điền **NGÀY HẸN**
5. Khách làm xong dịch vụ thì đổi **TRẠNG THÁI** thành `ĐÃ LÀM DV`

**Không sửa** các cột nền vàng — đó là cột hệ thống tự tính.

---

# Khi có sự cố

## Dashboard không cập nhật / số bị cũ

Dấu hiệu: băng trên đầu dashboard ghi ngày cũ, hoặc nhận email `🔴 PIPELINE CHƯA CHẠY...`

1. Mở Google Sheet nhập liệu → menu **🔄 PXV** → **Chạy lại pipeline ngay**
2. Đợi 2–3 phút, mở lại dashboard xem đã cập nhật chưa
3. Nếu hiện thông báo lỗi về token → xem mục [Khi nào cần gọi người kỹ thuật](#khi-nào-cần-gọi-người-kỹ-thuật)
4. Nếu không có gì xảy ra, mở link này xem có dòng nào màu đỏ không:
   `github.com/tomtran-786/Phun-Xam-Vic---Data-Analysis/actions`
5. Nếu thấy chữ **"This workflow was disabled"** → bấm nút **Enable workflow**

> **Vì sao lịch chạy tự tắt?** GitHub tự động tắt sau 60 ngày nếu không ai thay đổi gì trong repo. Hệ thống đã có 3 lớp chống việc này, nhưng nếu vẫn xảy ra thì bước 5 là cách xử.

---

## Nhận email cảnh báo — tra theo tiêu đề

Mọi email đều bắt đầu bằng `[PXV]`.

### `🔴 PIPELINE CHƯA CHẠY ... NGÀY`
Số trên dashboard đang là số cũ. → Làm theo mục [Dashboard không cập nhật](#dashboard-không-cập-nhật--số-bị-cũ).

### `⚠️ File KiotViet trùng nội dung`
Bạn thả nhầm lại file cũ. Không sao cả, hệ thống đã chặn.
1. Vào KiotViet export lại với **khoảng ngày mới**
2. Thả file mới vào `KiotViet_Drop`

### `⚠️ Nạp KiotViet xong nhưng có vấn đề` → *THIẾU TOÀN BỘ HÓA ĐƠN THÁNG*
**Đây là cảnh báo nghiêm trọng nhất. Xử ngay trong ngày.**
1. Đọc email xem thiếu tháng nào
2. Vào KiotViet export đúng khoảng tháng đó
3. Thả file vào `KiotViet_Drop`
4. Kiểm tra lại: mở sheet `KIOTVIET_LOG` trong file **PXV_KHO**, tháng đó phải có số hóa đơn > 0

> Để càng lâu càng khó cứu. KiotViet giới hạn thời gian truy xuất dữ liệu cũ.

### `⚠️ Nạp KiotViet xong nhưng có vấn đề` → *Hóa đơn mới nhất ... đã X ngày*
Bạn export nhầm khoảng ngày cũ. → Export lại với khoảng ngày gần đây.

### `❌ Không nạp được file KiotViet`
File sai định dạng. Đọc dòng "Lý do" trong email:
- *"Chỉ nhận file .csv"* → trong KiotViet chọn **Xuất file → CSV**, không phải Excel
- *"không giống export KiotViet"* → chọn đúng báo cáo **Chi tiết hóa đơn**
- File lỗi nằm ở thư mục `KiotViet_Drop/_loi`, sửa xong thả lại vào `KiotViet_Drop`

### `⚠️ Pipeline chạy nhưng dữ liệu có vấn đề`
Mở Google Sheet nhập liệu → menu **🔄 PXV** → **Xem trạng thái dữ liệu** để biết chi tiết.

---

## Số doanh thu trông sai

1. Mở dashboard, xem **băng trạng thái trên đầu trang**: dữ liệu cập nhật đến ngày nào? Nếu cũ → làm theo mục [Dashboard không cập nhật](#dashboard-không-cập-nhật--số-bị-cũ)
2. Kiểm tra bạn có đang xem đúng **khoảng thời gian** không — nhớ rằng **tháng 12/2025 không có dữ liệu**, xem mục [Những chỗ dữ liệu đã biết là thiếu](#những-chỗ-dữ-liệu-đã-biết-là-thiếu)
3. Mở file **PXV_KHO** → sheet `KIOTVIET_LOG`, so doanh thu từng tháng với sổ sách
4. Lệch ở một tháng cụ thể → export lại tháng đó từ KiotViet và thả vào `KiotViet_Drop`
5. Vẫn lệch → gọi người kỹ thuật, **kèm theo ảnh chụp sheet `KIOTVIET_LOG`**

> **Lưu ý về cách đọc doanh thu theo kênh:** khoảng **3/4 doanh thu đến từ khách vãng lai** — người mua hàng nhưng chưa từng nhắn tin. Số doanh thu chia theo kênh quảng cáo **chỉ tính phần khách có hồ sơ lead**, đừng dùng nó làm mẫu số cho toàn bộ doanh thu.

---

## Sales bị chặn không nhập được

### Hiện thông báo *"Phải nhập SỐ ĐT trước khi chuyển khách sang Đặt hẹn"*

Đây là chặn có chủ đích, không phải lỗi. Khách đã hẹn đến cửa hàng thì phải có số để gọi xác nhận.

1. Xin số điện thoại khách, điền vào cột **SỐ ĐT**
2. Rồi mới đổi cột **TRẠNG THÁI**

Nếu khách nhất định không cho số nhưng vẫn hẹn đến (hiếm):
1. Điền cột **LÝ DO CHƯA CÓ SĐT** = `Khách chưa cho`
2. Ghi giờ hẹn vào cột **GHI CHÚ**
3. Báo quản lý để theo dõi riêng

### Ngày tự điền bị sai

Cột NGÀY tự lấy ngày hôm nay. Nếu nhập bù cho hôm trước:
1. Xóa ô NGÀY
2. Gõ tay ngày đúng theo dạng `dd/mm/yyyy`

---

# Việc định kỳ

## Thêm nguồn quảng cáo mới

Ví dụ mở thêm kênh Threads.

1. Mở Google Sheet nhập liệu → sheet **DANH_MỤC**
2. Thêm giá trị mới vào cột **NGUỒN**
3. Báo người kỹ thuật thêm nguồn đó vào bảng phân loại kênh, nếu không nó sẽ rơi vào nhóm "Khác" trên dashboard

## Đổi danh sách dịch vụ mồi

Hiện đang tính 3 nhóm: `GÓI TIẾT KIỆM`, `Xóa lần 01`, `CO2 Fractional`.

Đổi danh sách này **làm thay đổi toàn bộ báo cáo funnel dịch vụ mồi**, kể cả số của các tháng trước. Cần báo người kỹ thuật, không tự sửa.

## Nhập chi phí quảng cáo hằng tháng

Đầu mỗi tháng, marketing nhập khoảng 10 dòng.

1. Mở Google Sheet nhập liệu → sheet **CHI_PHÍ_QC**
2. Mỗi dòng: `tháng` · `kênh` · `mã bài QC` · `chi phí`
3. Xong. Dashboard tự tính CPL, CAC, ROAS

> **Không nhập phần này thì không trả lời được câu "kênh nào hiệu quả"** — chỉ biết kênh nào ra *nhiều* lead, không biết kênh nào ra lead *rẻ*. Một kênh 200 lead tốn 50 triệu kém hơn kênh 80 lead tốn 5 triệu, mà nhìn số lượng thì tưởng ngược lại.

## Nhân viên mới / nghỉ việc

**Nhân viên mới:** thêm tên vào cột `CHATPAGE` trong sheet **DANH_MỤC**, rồi chia sẻ quyền sửa Google Sheet nhập liệu cho họ.

**Nhân viên nghỉ:** bỏ quyền truy cập Google Sheet. **Không xóa các dòng cũ của họ** — sẽ mất lịch sử và làm sai số báo cáo các tháng trước.

> ⚠️ Nếu người nghỉ việc là **người đã cài đặt Apps Script**, các tự động hóa sẽ ngừng chạy. Phải báo người kỹ thuật cài lại bằng tài khoản chủ doanh nghiệp.

---

# Đọc hiểu

## Ý nghĩa các con số trên dashboard

### Phễu bán hàng

| Bước | Nghĩa là gì |
|---|---|
| **Có Inbox** | Số lượt khách nhắn tin |
| **Có SĐT** | Trong số đó, bao nhiêu người cho số điện thoại |
| **Có Đặt Lịch** | Bao nhiêu người đặt hẹn đến cửa hàng |
| **Có Ra Đơn** | Bao nhiêu người thực sự mua |

Số liệu kỳ T1–T2/2026: **2.380 → 1.274 → 303 → 186**, tỷ lệ chốt 7,82%.

**Chỗ rớt nhiều nhất là bước SĐT → Đặt lịch** (chỉ 23,8% đi tiếp). Có số điện thoại rồi mà không hẹn được lịch — đây là chỗ đáng cải thiện nhất, không phải khâu chốt đơn (61,4% đã khá tốt).

### Sáu nhóm khách hàng

| Nhóm | Nghĩa là gì |
|---|---|
| 0 | Nhắn tin nhưng không cho số |
| 1 | **Khách vãng lai** — mua hàng, chưa từng nhắn tin |
| 2 | Có số nhưng chưa hẹn, chưa mua |
| 3 | Mua thẳng, không cần hẹn |
| 4 | Đặt hẹn rồi nhưng không đến / không mua |
| 5 | Đủ 3 bước: nhắn tin → hẹn → mua |
| 6 | Có hẹn nhưng thiếu hồ sơ lead — **lỗi nhập liệu**, số này nên gần 0 |

### CLV (giá trị khách hàng)

Tổng tiền một khách đã chi. **Lưu ý:** hiện chỉ có dữ liệu khoảng 4 tháng, nên đây là *giá trị trong kỳ*, chưa phải giá trị trọn đời thật. Con số sẽ đáng tin dần khi tích lũy đủ 12 tháng.

### Khi số trên dashboard khác số trong sheet

Pipeline tính đúng nhưng Looker vẫn hiện sai được — nó gộp và lọc lại số đã tính. Bản kiểm 30/07/2026 tìm ra **7/9 thẻ KPI sai**, nặng nhất là mất 43% lead do ngày bị đọc nhầm ngày/tháng.

Cách sửa từng lỗi nằm ở **[docs/LOOKER.md](docs/LOOKER.md)**. Ba dấu hiệu cần biết:

- **Biểu đồ theo thời gian trống từ ngày 3 đến 12 mỗi tháng** → ngày bị lật lúc import tab LEAD. Import lại, xem [Sales: nhập lead](#sales-nhập-lead).
- **CLV và tỷ lệ upsell thấp hơn bạn nhớ** → đúng như vậy, hai thay đổi từ 30/07/2026. Một: pipeline chỉ tính hóa đơn từ 01/01/2026 trở đi (bỏ T11/2025). Hai: **bán chéo cùng ngày giờ tách khỏi upsell** — 19,2% khách mua thêm ngay tại quầy, còn 7,0% mới thật sự quay lại hôm khác. Số 17,3% cũ là hai thứ trộn lẫn.
- **Thẻ ROAS / CAC cao bất thường** → Looker đang cộng các tỷ số lại với nhau. Mọi thẻ số phải lấy từ bảng `KPI`, lọc `phạm vi = "TỔNG"`.
- **Chi phí quảng cáo hiện 145.920.000đ** → đó là số **mô phỏng** cho case study, không phải chi tiêu thật.

---

## Những chỗ dữ liệu đã biết là thiếu

Đọc kỹ mục này trước khi kết luận bất cứ điều gì từ dashboard.

### 🔴 Tháng 12/2025 không có hóa đơn nào

Mất toàn bộ, không khôi phục được. Trên biểu đồ theo thời gian, tháng này hiện **khoảng trống có nhãn** — **không phải doanh thu bằng 0**. Đừng tính trung bình tháng mà gộp cả T12/2025 vào.

### 🟠 Khoảng 46% lead không có số điện thoại

Phần lớn là khách chỉ hỏi giá rồi im — không hẳn là lỗi sales. Hệ quả: không biết những người đó sau này có mua không. Đang khắc phục bằng cách nạp thêm dữ liệu từ Pancake.

### 🟠 3/4 doanh thu không quy được về kênh quảng cáo

Khách vãng lai không có hồ sơ lead nên không biết họ đến từ đâu. **Đừng dùng doanh thu theo kênh để tính ROI tuyệt đối.**

### 🟠 35 lead ghi ngày 19/01/2025

Cả 35 dòng cùng một ngày, trong file lẽ ra là năm 2026 — nhiều khả năng gõ nhầm năm hàng loạt. Hệ thống **không tự sửa** (đoán sai sẽ phá dữ liệu thật), các dòng này nằm ở sheet **`CẦN_SỬA`**. Nếu xác nhận là gõ nhầm, sửa trực tiếp trong sheet LEAD rồi chạy lại pipeline.

---

## Khi nào cần gọi người kỹ thuật

Tự xử được phần lớn tình huống ở trên. Cần gọi khi:

- Email cảnh báo lặp lại **3 ngày liên tiếp** dù đã làm theo hướng dẫn
- Menu **🔄 PXV** biến mất khỏi Google Sheet
- Bấm "Chạy lại pipeline" báo lỗi **token hết hạn**
- Số doanh thu lệch sổ sách mà đã kiểm tra `KIOTVIET_LOG` vẫn không ra
- Cần thêm cột mới vào sheet nhập liệu, hoặc đổi danh sách dịch vụ mồi
- Người cài đặt Apps Script nghỉ việc

**Khi báo, gửi kèm:**
1. Ảnh chụp email cảnh báo (nếu có)
2. Ảnh chụp menu 🔄 PXV → *Xem trạng thái dữ liệu*
3. Mô tả bạn đã thử làm gì rồi

---

## Thông tin liên hệ

| Việc | Ai phụ trách |
|---|---|
| Export KiotViet hằng ngày | _(điền tên)_ |
| Nhập chi phí quảng cáo | _(điền tên)_ |
| Nhận email cảnh báo | `tomt74762@gmail.com` |
| Người kỹ thuật | _(điền tên + cách liên hệ + thời gian phản hồi cam kết)_ |

> Bảng này **phải điền** trước khi bàn giao. Sự cố không có người chịu trách nhiệm rõ ràng chính là cách tháng 12/2025 bị mất.
