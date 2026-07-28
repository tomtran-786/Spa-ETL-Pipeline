"""Dữ liệu giả lập cho test. TOÀN BỘ LÀ BỊA — không lấy từ khách hàng thật."""
import pandas as pd
import pytest

from pxv.clean import clean_phone, phone_kind


def _lead(ngay, sdt, ten, nguon="Fanpage PXV", chatpage="NV A",
          ngay_hen=None, quan_tam="Môi", nhom_sp="DỊCH VỤ"):
    return {
        "NGÀY": ngay, "SỐ ĐT": sdt, "TÊN KHÁCH HÀNG": ten,
        "LOẠI TIN NHẮN": "TỰ NHIÊN", "NHÓM SP": nhom_sp, "CHATPAGE": chatpage,
        "NGUỒN": nguon, "QUAN TÂM": quan_tam, "TÌNH TRẠNG": "Nhắn Qua Zalo",
        "NGÀY HẸN": ngay_hen, "BÀI QC": "QC001",
    }


@pytest.fixture
def df_lead():
    """5 lead bịa, phủ các tình huống: có/không SĐT, có/không hẹn."""
    rows = [
        _lead("05/01/2026", "0390000001", "Khách Có Đủ Bước", ngay_hen="10/01/2026"),
        _lead("06/01/2026", "0912345678", "Khách Chốt Thẳng"),
        _lead("07/01/2026", "0987654321", "Khách Hẹn Rồi Rớt", ngay_hen="12/01/2026"),
        _lead("08/01/2026", "0911222333", "Khách Chỉ Hỏi Giá"),
        _lead("09/01/2026", None, "Khách Không Cho Số"),
    ]
    df = pd.DataFrame(rows)
    df["Phone_Clean"] = df["SỐ ĐT"].apply(clean_phone)
    df["Loại SĐT"] = df["SỐ ĐT"].apply(phone_kind)
    df["Ngày Lead"] = pd.to_datetime(df["NGÀY"], dayfirst=True)
    return df


@pytest.fixture
def df_hen():
    return pd.DataFrame({
        "Phone_Clean": ["0390000001", "0987654321"],
        "NGÀY HẸN": pd.to_datetime(["2026-01-10", "2026-01-12"]),
    })


@pytest.fixture
def df_inv():
    """4 hóa đơn bịa. HD003 có 2 mặt hàng để test lỗi cộng tiền trùng.

    HD004 không có SĐT (KiotViet ghi '0') — phải vẫn tính doanh thu.
    """
    rows = [
        # (mã HĐ, SĐT, tên hàng, mã hàng, tổng HĐ, ngày)
        ("HD001", "0390000001", "(DV) Phun Môi - GOLD", "SP1", 5000000, "2026-01-15"),
        ("HD002", "0912345678", "(DV) GÓI TIẾT KIỆM - XÓA CHÂN MÀY TRỌN GÓI", "SP2", 900000, "2026-01-20"),
        ("HD003", "0912345678", "(DV) Tạo sợi tả thực", "SP3", 8000000, "2026-02-01"),
        ("HD003", "0912345678", "(DV) Xử lý đồi mồi", "SP4", 8000000, "2026-02-01"),
        ("HD004", "0", "(DV) Phun Mày - DIAMOND", "SP5", 7000000, "2026-02-05"),
    ]
    df = pd.DataFrame(rows, columns=["Mã hóa đơn", "Điện thoại", "Tên hàng",
                                     "Mã hàng", "Khách cần trả", "Thời gian"])
    df["Mã khách hàng"] = "KH" + df["Mã hóa đơn"].str[-3:]
    df["Phone_Clean"] = df["Điện thoại"].apply(clean_phone)
    df["Ngày HĐ"] = pd.to_datetime(df["Thời gian"])

    # Giống io_local.load_invoices: tiền chỉ nằm ở dòng đầu mỗi hóa đơn.
    df = df.sort_values(["Mã hóa đơn", "Mã hàng"]).reset_index(drop=True)
    first = ~df.duplicated("Mã hóa đơn", keep="first")
    df["Doanh Thu (VNĐ)"] = df["Khách cần trả"].where(first, 0)
    return df
