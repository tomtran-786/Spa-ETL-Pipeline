"""Chi phí quảng cáo và các chỉ số CPL/CAC/ROAS. Dữ liệu trong file này là BỊA."""
import numpy as np
import pandas as pd
import pytest

from pxv import ad_costs, marts, transform

WINDOW = pd.Timestamp("2026-01-01")


@pytest.mark.parametrize("raw,expected", [
    ("2026-01", "2026-01"),
    ("2026/1", "2026-01"),
    ("01/2026", "2026-01"),      # marketing hay gõ kiểu này
    ("1/2026", "2026-01"),
    ("15/01/2026", "2026-01"),   # lỡ gõ cả ngày
    ("không phải tháng", None),
    ("", None),
    (None, None),
])
def test_parse_thang_chap_nhan_nhieu_kieu_go(raw, expected):
    """Marketing gõ tay nên phải nhận nhiều định dạng, thay vì im lặng bỏ dòng."""
    assert ad_costs.parse_thang(raw) == expected


def test_normalize_gop_dung_cac_kieu_ghi_thang():
    df = pd.DataFrame({
        "tháng": ["2026-01", "01/2026"],
        "kênh": ["Facebook", "Facebook"],
        "mã bài QC": ["A", "B"],
        "chi phí": ["10.000.000", "5.000.000"],
    })
    out = ad_costs.normalize(df)
    assert list(out["tháng"]) == ["2026-01", "2026-01"]
    assert out["chi phí"].sum() == 15_000_000


def test_normalize_bo_dong_khong_dung_duoc():
    df = pd.DataFrame({
        "tháng": ["2026-01", None, "2026-01", "2026-01"],
        "kênh": ["Facebook", "Tiktok", None, "Tiktok"],
        "mã bài QC": ["", "", "", ""],
        "chi phí": ["1.000.000", "500.000", "500.000", "0"],
    })
    out = ad_costs.normalize(df)
    assert len(out) == 1, "chỉ dòng đủ tháng + kênh + chi phí > 0 mới được giữ"


def test_normalize_bang_rong_van_hop_le():
    assert ad_costs.normalize(pd.DataFrame()).empty
    assert ad_costs.normalize(None).empty


def test_normalize_thieu_cot_thi_bao_loi_ro_rang():
    with pytest.raises(ValueError, match="thiếu cột"):
        ad_costs.normalize(pd.DataFrame({"tháng": ["2026-01"]}))


def test_phat_hien_ten_kenh_go_sai():
    """Gõ sai tên kênh thì tiền biến mất khỏi mọi phép tính mà không ai biết."""
    costs = ad_costs.normalize(pd.DataFrame({
        "tháng": ["2026-01", "2026-01"],
        "kênh": ["Facebook", "Fanpage sai tên"],
        "mã bài QC": ["", ""],
        "chi phí": ["1.000.000", "2.000.000"],
    }))
    assert ad_costs.unknown_channels(costs, {"Facebook", "Tiktok"}) == ["Fanpage sai tên"]


# --- Chỉ số hiệu quả ------------------------------------------------------

@pytest.fixture
def master(df_lead, df_hen, df_inv):
    return transform.build_master(df_lead, df_hen, df_inv, WINDOW)


def test_chi_so_tinh_dung(master):
    """4 lead Facebook trong T1/2026, 2 người mua. Chi 1 triệu."""
    costs = ad_costs.normalize(pd.DataFrame({
        "tháng": ["2026-01"], "kênh": ["Facebook"],
        "mã bài QC": [""], "chi phí": ["1.000.000"],
    }))
    r = marts.build_hieu_qua_kenh(master, costs)
    fb = r[(r["kênh"] == "Facebook") & (r["tháng"] == "2026-01")].iloc[0]

    assert fb["CPL"] == round(1_000_000 / fb["lead"])
    assert fb["CAC"] == round(1_000_000 / fb["khách_mua"])
    assert fb["ROAS"] == round(fb["doanh_thu"] / 1_000_000, 2)


def test_khong_co_chi_phi_thi_tra_NaN_chu_khong_phai_0(master):
    """0 sẽ bị biểu đồ hiểu là 'hiệu quả bằng không', khác hẳn 'chưa có dữ liệu'."""
    r = marts.build_hieu_qua_kenh(master, ad_costs.EMPTY.copy())
    assert not r.empty, "vẫn phải ra bảng dù chưa nhập chi phí"
    assert r["CPL"].isna().all()
    assert r["ROAS"].isna().all()
    assert (r["chi phí"] == 0).all()


def test_kenh_khong_ai_mua_khong_lam_vo_phep_chia(master):
    """Kênh có lead nhưng 0 khách mua -> CAC không xác định, không được chia 0."""
    costs = ad_costs.normalize(pd.DataFrame({
        "tháng": ["2026-01"], "kênh": ["Hotline/Zalo"],
        "mã bài QC": [""], "chi phí": ["1.000.000"],
    }))
    r = marts.build_hieu_qua_kenh(master, costs)
    assert np.isfinite(r["CAC"].dropna()).all()


def test_quy_ket_theo_thang_cua_LEAD_khong_phai_thang_hoa_don(master):
    """Khách 0912345678 inbox 06/01 nhưng mua HD003 ngày 01/02.

    Doanh thu phải tính về tháng 1 (tháng bỏ tiền chạy quảng cáo), không phải
    tháng 2 — nếu không marketing sẽ đánh giá sai tháng nào hiệu quả.
    """
    r = marts.build_hieu_qua_kenh(master, ad_costs.EMPTY.copy())
    t1 = r[r["tháng"] == "2026-01"]["doanh_thu"].sum()
    assert t1 == master["Doanh Thu (VNĐ)"][master["Ngày Lead"].notna()].sum()
    assert "2026-02" not in set(r["tháng"]), "không lead nào phát sinh tháng 2"
