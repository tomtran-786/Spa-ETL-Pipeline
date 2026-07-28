"""Quy tắc nghiệp vụ dạng DỮ LIỆU, không phải if-chain trong code.

Marketing đổi chiến dịch thì sửa ở đây (và sau này là ở sheet DANH_MỤC) chứ
không cần lập trình viên. Mỗi bảng là danh sách có thứ tự — luật đứng trước
thắng — nên đọc là biết luật nào ưu tiên, khác với if-chain phải dò từng dòng.
"""
from __future__ import annotations

from .clean import normalize_text

# --- Kênh tiếp cận -------------------------------------------------------
# Áp lên chuỗi ghép "CHATPAGE | NGUỒN". Thứ tự quan trọng: TIKTOK đứng trước
# FANPAGE nên "Tiktok PXV" thắng "Fanpage".
#
# HẠN CHẾ ĐÃ BIẾT: vì ghép 2 cột rồi mới dò, một lead có
# CHATPAGE="Tiktok PXV" nhưng NGUỒN="Giới thiệu" sẽ ra "Tiktok". Đúng hơn là
# NGUỒN nên thắng CHATPAGE. Chưa đổi vì sẽ làm lệch số so với báo cáo đang dùng
# — xem ghi chú trong tests/test_golden.py.
CHANNEL_RULES: list[tuple[str, str]] = [
    ("TIKTOK", "Tiktok"),
    ("FANPAGE", "Facebook"),
    ("FACEBOOK", "Facebook"),
    ("FB CÔ HƯỜNG", "Facebook"),
    ("INSTGRAM", "Instagram"),
    ("INSTAGRAM", "Instagram"),
    ("HOTLINE", "Hotline/Zalo"),
    ("ZALO", "Hotline/Zalo"),
    ("KHÁCH CŨ", "Khách cũ"),
    ("DATA CŨ", "Khách cũ"),
    ("FILE CŨ", "Khách cũ"),
    ("GIỚI THIỆU", "Giới thiệu"),
]
CHANNEL_WALKIN = "Vãng lai (không rõ nguồn)"
CHANNEL_OTHER = "Khác"


def classify_channel(chatpage, nguon, is_walkin: bool = False) -> str:
    combined = f"{chatpage} | {nguon}".upper()
    for keyword, channel in CHANNEL_RULES:
        if keyword in combined:
            return channel
    return CHANNEL_WALKIN if is_walkin else CHANNEL_OTHER


# --- Phân loại sản phẩm --------------------------------------------------
# Dò trên Tên hàng (hóa đơn); nếu chưa mua thì dò trên QUAN TÂM (lead hỏi gì).
PRODUCT_RULES: list[tuple[tuple[str, ...], str]] = [
    (("XOÁ", "XÓA"), "Xóa Laser"),
    (("MÀY", "TẠO SỢI", "ĐIÊU KHẮC"), "Làm Mày"),
    (("MÔI",), "Làm Môi"),
    (("CO2", "BÓC TÁCH"), "CO2 / Cắt đáy sẹo"),
    (("MÍ", "EYELINER"), "Làm Mí"),
]
PRODUCT_COURSE = "Khóa học"
PRODUCT_UNKNOWN = "Chưa rõ"
PRODUCT_OTHER = "Dịch vụ/SP khác"


def classify_product(ten_hang, quan_tam) -> str:
    import pandas as pd

    source = ten_hang if pd.notna(ten_hang) else quan_tam
    text = str(source).upper() if pd.notna(source) else ""
    if not text or text == "NAN":
        return PRODUCT_UNKNOWN
    for keywords, label in PRODUCT_RULES:
        if any(k in text for k in keywords):
            return label
    if "PLASMA" in text and "KHÓA" in text:
        return PRODUCT_COURSE
    return PRODUCT_OTHER


# --- Nhóm sản phẩm -------------------------------------------------------
TRAINING_KEYWORDS = ("KHÓA HỌC", "ĐÀO TẠO", "PLASMA ONLINE")


def classify_product_group(nhom_sp, ten_hang) -> str:
    import pandas as pd

    if pd.notna(nhom_sp):
        return normalize_text(nhom_sp)
    text = str(ten_hang).upper() if pd.notna(ten_hang) else ""
    return "ĐÀO TẠO" if any(k in text for k in TRAINING_KEYWORDS) else "DỊCH VỤ"


# --- Sửa chính tả giá trị NGUỒN -----------------------------------------
# Khóa đã chuẩn hóa (normalize_text), giá trị là dạng viết đúng.
SOURCE_ALIASES: dict[str, str] = {
    "INSTGRAM": "Instagram",
    "INSTAGRAM": "Instagram",
    "FANPAGE PXV": "Fanpage PXV",
    "FANPAGE HỌC VIỆN": "Fanpage học viện",
    "TIKTOK PXV": "Tiktok PXV",
    "TIKTOK HỌC VIỆN": "Tiktok học viện",
    "FB CÔ HƯỜNG": "FB Cô Hường",
    "KHÁCH CŨ": "Khách cũ",
    "DATA CŨ 2023": "DATA CŨ 2023",
    "KHÁCH GIỚI THIỆU": "Khách giới thiệu",
    "HOTLINE": "Hotline",
    "ZALO": "Zalo",
}

# Danh mục NGUỒN hợp lệ — dùng để đếm tỷ lệ giá trị lạ.
SOURCE_CATALOG = set(SOURCE_ALIASES.values())
