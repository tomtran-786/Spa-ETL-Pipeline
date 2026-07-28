"""Vá SĐT từ Pancake. Toàn bộ dữ liệu ở đây là BỊA.

Các test này chứng minh ĐƯỜNG ỐNG chạy đúng, KHÔNG chứng minh việc ghép tên
cho kết quả đúng ngoài thực tế — chuyện đó chỉ đo được bằng dữ liệu thật.
"""
from pathlib import Path

import pandas as pd
import pytest

from pxv import pancake
from pxv.clean import clean_phone, phone_kind
from pxv.pancake import COT_CO, fill_missing_phones, khoa_ten

TOY = Path(__file__).parent / "fixtures" / "pancake_toy.csv"


@pytest.fixture
def df_pancake():
    df = pd.read_csv(TOY, dtype=str)
    df["Phone_Clean"] = df["SĐT"].apply(clean_phone)
    return df.dropna(subset=["Phone_Clean"])


def _lead(ten, sdt=None):
    return {"TÊN KHÁCH HÀNG": ten, "SỐ ĐT": sdt,
            "Phone_Clean": clean_phone(sdt), "Loại SĐT": phone_kind(sdt)}


@pytest.fixture
def df_lead_thieu():
    """Lead phủ đủ các tình huống ghép."""
    return pd.DataFrame([
        _lead("Khách Vá Được Một"),                 # khớp 1:1 -> vá
        _lead("  khách vá được bốn  "),             # khác hoa thường + khoảng trắng -> vá
        _lead("Khách   Vá   Được   Năm"),           # nhiều khoảng trắng -> vá
        _lead("Khách Trùng Tên Ở Lead"),            # trùng tên ở lead -> bỏ qua
        _lead("Khách Trùng Tên Ở Lead"),            # ^ dòng thứ hai cùng tên
        _lead("Khách Trùng Tên Ở Pancake"),         # Pancake có 2 số -> bỏ qua
        _lead("Khách Chưa Từng Xuất Hiện"),         # không có ở Pancake
        _lead("Khách Đã Có Số Rồi", "0912345678"),  # đã có số -> không đụng
        _lead("Xuân Yến (BV Phương Châu)"),         # Pancake chỉ có 'Xuân Yến' -> KHÔNG ghép
        _lead(None),                                # không có tên
    ])


def test_khoa_ten_gop_khoang_trang_va_hoa_thuong():
    assert khoa_ten("  Khách   Vá  Được  ") == khoa_ten("khách vá được")
    assert khoa_ten("") is None
    assert khoa_ten(None) is None


def test_khoa_ten_KHONG_bo_phan_trong_ngoac():
    """Bỏ ngoặc sẽ gộp hai người khác nhau — đúng kiểu sai lầm cần tránh."""
    assert khoa_ten("Xuân Yến (BV Phương Châu)") != khoa_ten("Xuân Yến")


def test_va_duoc_khi_ten_khop_1_1(df_lead_thieu, df_pancake):
    out, tk = fill_missing_phones(df_lead_thieu, df_pancake)
    assert out.loc[0, "Phone_Clean"] == "0390000010"
    assert bool(out.loc[0, COT_CO]) is True
    assert tk["vá_được"] == 3   # ba dòng khớp 1:1 sau chuẩn hóa


def test_chuan_hoa_hoa_thuong_va_khoang_trang(df_lead_thieu, df_pancake):
    out, _ = fill_missing_phones(df_lead_thieu, df_pancake)
    assert out.loc[1, "Phone_Clean"] == "0390000013"   # '  khách vá được bốn  '
    assert out.loc[2, "Phone_Clean"] == "0390000014"   # nhiều khoảng trắng


def test_trung_ten_o_lead_thi_BO_QUA(df_lead_thieu, df_pancake):
    """Hai lead cùng tên: gán cho ai cũng có thể sai, nên không gán."""
    out, tk = fill_missing_phones(df_lead_thieu, df_pancake)
    assert out.loc[3, "Phone_Clean"] is None or pd.isna(out.loc[3, "Phone_Clean"])
    assert out.loc[4, "Phone_Clean"] is None or pd.isna(out.loc[4, "Phone_Clean"])
    assert tk["bỏ_qua_trùng_tên_lead"] == 2


def test_trung_ten_o_pancake_thi_BO_QUA(df_lead_thieu, df_pancake):
    """Pancake có 2 số cho cùng một tên: không biết chọn số nào."""
    out, tk = fill_missing_phones(df_lead_thieu, df_pancake)
    assert pd.isna(out.loc[5, "Phone_Clean"])
    assert tk["bỏ_qua_trùng_tên_pancake"] == 1


def test_KHONG_ghi_de_so_da_co(df_lead_thieu, df_pancake):
    """Pancake có 'Khách Đã Có Số Rồi' = 0390000050, nhưng lead đã có số khác."""
    out, _ = fill_missing_phones(df_lead_thieu, df_pancake)
    assert out.loc[7, "Phone_Clean"] == "0912345678"
    assert bool(out.loc[7, COT_CO]) is False


def test_ten_gan_giong_KHONG_duoc_ghep(df_lead_thieu, df_pancake):
    """'Xuân Yến (BV Phương Châu)' vs 'Xuân Yến' — chặt còn hơn ghép sai."""
    out, _ = fill_missing_phones(df_lead_thieu, df_pancake)
    assert pd.isna(out.loc[8, "Phone_Clean"])


def test_lead_khong_co_ten_thi_bo_qua(df_lead_thieu, df_pancake):
    out, tk = fill_missing_phones(df_lead_thieu, df_pancake)
    assert pd.isna(out.loc[9, "Phone_Clean"])
    assert tk["không_tìm_thấy_tên"] >= 1


def test_pancake_rong_thi_khong_doi_gi(df_lead_thieu):
    truoc = df_lead_thieu["Phone_Clean"].notna().sum()
    out, tk = fill_missing_phones(df_lead_thieu, pd.DataFrame())
    assert out["Phone_Clean"].notna().sum() == truoc
    assert tk["vá_được"] == 0


def test_khong_lam_mat_dong_nao(df_lead_thieu, df_pancake):
    out, _ = fill_missing_phones(df_lead_thieu, df_pancake)
    assert len(out) == len(df_lead_thieu)


def test_thong_ke_du_de_quyet_dinh_giu_hay_bo(df_lead_thieu, df_pancake):
    """Thống kê phải đếm cả ca bỏ qua, không chỉ đếm ca thành công."""
    _, tk = fill_missing_phones(df_lead_thieu, df_pancake)
    for khoa in ("vá_được", "lead_thiếu_sđt", "bỏ_qua_trùng_tên_lead",
                 "bỏ_qua_trùng_tên_pancake", "không_tìm_thấy_tên", "tỷ_lệ_vá_%"):
        assert khoa in tk
    assert "Pancake: vá" in pancake.tom_tat(tk)


@pytest.mark.parametrize("gia_tri_rong", [None, float("nan"), pd.NA, ""])
def test_ten_rong_moi_kieu_deu_vao_dung_nhanh(df_pancake, gia_tri_rong):
    """Lead không có tên phải đếm vào 'không tìm thấy tên', KHÔNG phải 'trùng tên'.

    Tùy phiên bản, pandas biến None thành NaN khi apply() trên cột object.
    Code cũ dùng `khoa is None` nên NaN lọt qua và bị đếm nhầm — test ở máy
    xanh còn CI đỏ, đúng kiểu lỗi khó truy nhất.
    """
    df = pd.DataFrame([
        _lead("Khách Vá Được Một"),
        _lead(gia_tri_rong),
    ])
    _, tk = fill_missing_phones(df, df_pancake)
    assert tk["không_tìm_thấy_tên"] == 1
    assert tk["bỏ_qua_trùng_tên_lead"] == 0
    assert tk["vá_được"] == 1
