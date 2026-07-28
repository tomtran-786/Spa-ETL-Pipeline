"""Đọc dữ liệu từ file local.

Cùng interface với ``io_sheets.py`` (sẽ viết ở tuần 3) để chuyển sang Google
Sheets chỉ phải đổi chỗ import, không đụng logic tính toán.
"""
from __future__ import annotations

import pandas as pd

from . import ad_costs, config, schema
from .clean import clean_money, clean_phone, parse_date_vn, phone_kind


def load_leads(path=None) -> pd.DataFrame:
    """Lead từ sheet SALE. Trả về 1 dòng / 1 lần inbox."""
    df = pd.read_csv(path or config.F_LEAD)
    df = df.dropna(how="all")
    schema.validate_headers(df, schema.LEAD_REQUIRED, "lead")
    df = schema.rename_status_columns(df)
    df["Phone_Clean"] = df["SỐ ĐT"].apply(clean_phone)
    df["Loại SĐT"] = df["SỐ ĐT"].apply(phone_kind)
    df["Ngày Lead"] = df["NGÀY"].apply(parse_date_vn)
    return df


def load_appointments(df_lead: pd.DataFrame, path=None) -> pd.DataFrame:
    """Hẹn = hợp nhất 2 nguồn: cột NGÀY HẸN trong file lead + file ĐĂT HẸN riêng.

    Chỉ dùng file ĐĂT HẸN sẽ mất 106 SĐT (file lead có 309, file hẹn có 207).

    Sắp xếp theo ngày hẹn TRƯỚC khi khử trùng, nên "hẹn đầu tiên của khách" là
    xác định. Code cũ khử trùng trên concat chưa sort -> kết quả phụ thuộc thứ
    tự file, chạy 2 lần có thể ra 2 giá trị khác nhau.
    """
    from_lead = df_lead.loc[
        df_lead["NGÀY HẸN"].notna(), ["SỐ ĐT", "NGÀY HẸN", "Ngày Lead"]].copy()

    other = pd.read_csv(path or config.F_HEN)
    schema.validate_headers(other, schema.HEN_REQUIRED, "đặt hẹn")
    other = other[["SỐ ĐT", "NGÀY HẸN"]].copy()
    other["Ngày Lead"] = pd.NaT     # file riêng đã có năm đầy đủ, không cần suy

    hen = pd.concat([from_lead, other], ignore_index=True)
    hen["Phone_Clean"] = hen["SỐ ĐT"].apply(clean_phone)
    # Truyền ngày lead để suy năm cho các ô ghi thiếu năm ('10/01', '22/1').
    hen["NGÀY HẸN"] = [parse_date_vn(v, moc)
                       for v, moc in zip(hen["NGÀY HẸN"], hen["Ngày Lead"])]
    hen = hen.dropna(subset=["Phone_Clean"])
    hen = (hen.sort_values(["Phone_Clean", "NGÀY HẸN"], na_position="last")
              .drop_duplicates("Phone_Clean", keep="first"))
    return hen[["Phone_Clean", "NGÀY HẸN"]]


def load_invoices(path=None) -> pd.DataFrame:
    """Hóa đơn KiotViet. Một dòng = một mặt hàng trong hóa đơn.

    QUAN TRỌNG — cột ``Khách cần trả`` là TỔNG TIỀN CỦA CẢ HÓA ĐƠN, được lặp
    lại y nguyên trên mỗi dòng mặt hàng. Ví dụ HD026957 có 2 mặt hàng, cả 2
    dòng đều ghi 3.000.000 (không phải 1.5tr mỗi dòng). Cộng thẳng sẽ ra 6tr.

    Cách xử: ``Doanh Thu (VNĐ)`` chỉ mang giá trị ở DÒNG ĐẦU của mỗi hóa đơn,
    các dòng sau = 0. Nhờ vậy SUM() luôn đúng mà vẫn giữ được chi tiết mặt hàng
    cho phân tích sản phẩm.
    """
    df = pd.read_excel(path or config.F_INV, sheet_name=0)
    schema.validate_headers(df, schema.INVOICE_REQUIRED, "hóa đơn")

    df["Phone_Clean"] = df["Điện thoại"].apply(clean_phone)
    df["Ngày HĐ"] = pd.to_datetime(df["Thời gian"], errors="coerce", dayfirst=True)
    df["_tổng_hóa_đơn"] = df["Khách cần trả"].apply(clean_money)

    df = df.sort_values(["Mã hóa đơn", "Mã hàng"], na_position="last").reset_index(drop=True)
    is_first_line = ~df.duplicated("Mã hóa đơn", keep="first")
    df["Doanh Thu (VNĐ)"] = df["_tổng_hóa_đơn"].where(is_first_line, 0)
    return df.drop(columns=["_tổng_hóa_đơn"])


def load_ad_costs(path=None) -> pd.DataFrame:
    """Chi phí quảng cáo. Chưa có file thì trả bảng rỗng, không làm gãy pipeline."""
    p = path or config.F_CHIPHI
    if not p.exists():
        return ad_costs.EMPTY.copy()
    return ad_costs.normalize(pd.read_csv(p))


def load_previous_dq() -> pd.DataFrame | None:
    """DQ_STATUS của lần chạy trước, để đối chiếu chống mất dữ liệu."""
    out = config.OUT_DIR / "PXV_DASHBOARD_DATA.xlsx"
    if not out.exists():
        return None
    try:
        return pd.read_excel(out, sheet_name="DQ_STATUS")
    except Exception:
        return None
