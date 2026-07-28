"""Hợp đồng schema cho các nguồn đầu vào.

Mục đích: ai chèn/xóa/đổi tên cột trong Google Sheets thì job đỏ NGAY hôm sau,
thay vì dashboard sai ngầm nhiều tháng. Đây là bài học từ 3 cột trùng tên
``TRẠNG THÁI`` — pandas tự đổi thành TRẠNG THÁI.1/.2 và không ai biết cột nào
là cột nào.
"""
from __future__ import annotations

import pandas as pd

# Sheet gốc có HAI cột trạng thái riêng biệt, cùng dùng một danh sách giá trị:
#   TÌNH TRẠNG  — tình trạng tương tác  (Nhắn Qua Zalo, CẦN GỌI LẠI, KHÁCH CHỈ NT…)
#   TRẠNG THÁI  — trạng thái xử lý      (ĐẶT HẸN, ĐÃ LÀM DV, DỜI LỊCH…)
# và một cột người phụ trách: TÊN TƯ VẤN - SALE.
#
# File CSV cũ bị LỆCH CỘT khi export: 'TRẠNG THÁI' rỗng hoàn toàn, 'TRẠNG
# THÁI.1' chỉ còn 2 dòng, còn 'TRẠNG THÁI.2' lại chứa TÊN NHÂN VIÊN. Dữ liệu
# trạng thái thật nằm nguyên trong cột 'TÌNH TRẠNG' (1.373 dòng, khớp 7/9 giá
# trị của dropdown trong sheet).
#
# Vì vậy khi đọc file cũ: giữ 'TÌNH TRẠNG', đổi 'TRẠNG THÁI.2' thành cột người
# phụ trách, bỏ hai cột rỗng còn lại.
STATUS_RENAME = {
    "TRẠNG THÁI.2": "TƯ VẤN - SALE",
}

# Giá trị hợp lệ của hai cột trạng thái — lấy từ dropdown trong sheet gốc,
# cộng thêm các giá trị đang có thật trong dữ liệu.
TRANG_THAI_VALUES = [
    "ĐẶT HẸN", "ĐÃ LÀM DV", "DỜI LỊCH", "KHÁCH CHỈ NT", "Nhắn Qua Zalo",
    "CẦN GỌI LẠI", "CHỜ TRẢ LỜI", "GẤP", "Ứng tuyển",
    "KHÔNG TƯƠNG TÁC", "BẤM QC TỰ ĐỘNG",
]

# Giá trị nghĩa là khách đã sang bước có lịch hẹn -> bắt buộc phải có SĐT.
TRANG_THAI_CAN_SDT = ["ĐẶT HẸN", "ĐÃ LÀM DV", "DỜI LỊCH"]

LEAD_REQUIRED = [
    "NGÀY",
    "TÊN KHÁCH HÀNG",
    "SỐ ĐT",
    "LOẠI TIN NHẮN",
    "NHÓM SP",
    "CHATPAGE",
    "NGUỒN",
    "QUAN TÂM",
    "TÌNH TRẠNG",
    "NGÀY HẸN",
]

# TRẠNG THÁI và TƯ VẤN - SALE là tùy chọn: file CSV cũ bị lệch cột nên không
# có, nhưng sheet mới thì có. Thiếu cũng không chặn pipeline.
LEAD_OPTIONAL = ["TRẠNG THÁI", "TƯ VẤN - SALE", "GIỜ HẸN", "BÀI QC"]

HEN_REQUIRED = ["SỐ ĐT", "NGÀY HẸN"]

INVOICE_REQUIRED = [
    "Mã hóa đơn",
    "Thời gian",
    "Mã khách hàng",
    "Điện thoại",
    "Khách cần trả",
    "Mã hàng",
    "Tên hàng",
]


class SchemaError(ValueError):
    """Cột đầu vào không khớp kỳ vọng — dừng pipeline thay vì tính ra số sai."""


def validate_headers(df: pd.DataFrame, required: list[str], source_name: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SchemaError(
            f"Nguồn '{source_name}' thiếu cột: {missing}. "
            f"Cột đang có: {list(df.columns)}"
        )


def rename_status_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Đổi 3 cột TRẠNG THÁI trùng tên thành tên nói rõ từng chặng."""
    return df.rename(columns={k: v for k, v in STATUS_RENAME.items() if k in df.columns})


# Cột đầu ra của bảng MASTER — cố định để Looker Studio không gãy khi code đổi.
MASTER_COLUMNS = [
    "SĐT Cuối",
    "Ngày Lead",
    "Ngày HĐ",
    "NGÀY HẸN",
    "Phân nhóm MECE",
    "Kênh Tiếp Cận",
    "Doanh Thu (VNĐ)",
    "Số lượng Lead tính",
    "Thời gian ra đơn (Ngày)",
    "TÊN KHÁCH HÀNG",
    "LOẠI TIN NHẮN",
    "NHÓM SP",
    "CHATPAGE",
    "NGUỒN",
    "QUAN TÂM",
    "TÌNH TRẠNG",
    "TRẠNG THÁI",
    "TƯ VẤN - SALE",
    "BÀI QC",
    "Mã hóa đơn",
    "Mã khách hàng",
    "Tên hàng",
    "NHÓM SP_Clean",
    "Phân loại sản phẩm",
    "[Dịch vụ mồi]",
    "[F] 1_Có Inbox",
    "[F] 2_Có SĐT",
    "[F] 3_Có Đặt Lịch",
    "[F] 4_Có Ra Đơn",
    "[Vãng lai] Có Ra Đơn",
    "Khách mua trước cửa sổ",
    "Loại SĐT",
]
