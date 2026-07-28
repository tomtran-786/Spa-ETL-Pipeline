"""Gỡ tình trạng lệch cột của file CSV cũ. Dữ liệu trong file này là BỊA."""
import pandas as pd

from pxv import schema


def _file_cu_lech_cot():
    """Giống hệt CSV export cũ: ba cột cùng tên 'TRẠNG THÁI'.

    pandas đánh số hậu tố .1/.2 khi đọc. Nội dung thật:
      TRẠNG THÁI    rỗng hoàn toàn      -> cột thừa
      TRẠNG THÁI.1  trạng thái xử lý    -> cột TRẠNG THÁI thật
      TRẠNG THÁI.2  TÊN NHÂN VIÊN       -> cột TƯ VẤN - SALE
    """
    return pd.DataFrame({
        "TÌNH TRẠNG": ["Nhắn Qua Zalo", "CẦN GỌI LẠI"],
        "TRẠNG THÁI": [None, None],
        "TRẠNG THÁI.1": ["ĐẶT HẸN", None],
        "TRẠNG THÁI.2": ["Nhân Viên A", "Nhân Viên B"],
    })


def test_bo_cot_rong_va_doi_ten_hai_cot_con_lai():
    out = schema.rename_status_columns(_file_cu_lech_cot())
    assert list(out.columns) == ["TÌNH TRẠNG", "TRẠNG THÁI", "TƯ VẤN - SALE"]
    assert out["TRẠNG THÁI"].tolist() == ["ĐẶT HẸN", None]
    assert out["TƯ VẤN - SALE"].tolist() == ["Nhân Viên A", "Nhân Viên B"]


def test_ten_nhan_vien_KHONG_duoc_roi_vao_cot_trang_thai():
    """Ánh xạ sai từng đổ 1.280 tên người vào cột dropdown chỉ nhận trạng thái."""
    out = schema.rename_status_columns(_file_cu_lech_cot())
    assert "Nhân Viên A" not in out["TRẠNG THÁI"].tolist()


def test_khong_dung_toi_file_moi_da_dung_ten():
    """Sheet mới không có cột trùng tên — hàm phải để nguyên."""
    goc = pd.DataFrame({"TÌNH TRẠNG": ["Nhắn Qua Zalo"],
                        "TRẠNG THÁI": ["ĐẶT HẸN"],
                        "TƯ VẤN - SALE": ["Nhân Viên A"]})
    out = schema.rename_status_columns(goc)
    assert out.equals(goc)


def test_validate_headers_chan_khi_thieu_cot():
    import pytest
    with pytest.raises(schema.SchemaError, match="thiếu cột"):
        schema.validate_headers(pd.DataFrame({"NGÀY": []}),
                                schema.LEAD_REQUIRED, "lead")
