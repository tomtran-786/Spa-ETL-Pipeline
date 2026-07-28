"""Hợp đồng schema cho các nguồn đầu vào.

Mục đích: ai chèn/xóa/đổi tên cột trong Google Sheets thì job đỏ NGAY hôm sau,
thay vì dashboard sai ngầm nhiều tháng. Đây là bài học từ 3 cột trùng tên
``TRẠNG THÁI`` — pandas tự đổi thành TRẠNG THÁI.1/.2 và không ai biết cột nào
là cột nào.
"""
from __future__ import annotations

import pandas as pd

# File lead xuất từ Google Sheets có 3 cột cùng tên "TRẠNG THÁI"; pandas tự
# đánh số hậu tố. Đây là 3 chặng của cùng một khách:
#   TRẠNG THÁI    -> Quan tâm
#   TRẠNG THÁI.1  -> Đặt hẹn
#   TRẠNG THÁI.2  -> Chốt đơn
# Khi dựng sheet mới sẽ đổi hẳn thành TT_QUAN_TÂM / TT_ĐẶT_HẸN / TT_CHỐT_ĐƠN.
STATUS_RENAME = {
    "TRẠNG THÁI": "TT_QUAN_TÂM",
    "TRẠNG THÁI.1": "TT_ĐẶT_HẸN",
    "TRẠNG THÁI.2": "TT_CHỐT_ĐƠN",
}

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
