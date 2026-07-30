"""Bảng KPI — chốt chặn lỗi Looker cộng các cột tỷ số lại với nhau.

Dữ liệu trong file này là BỊA.
"""
import pandas as pd
import pytest

from pxv import marts, transform

WINDOW = pd.Timestamp("2026-01-01")


@pytest.fixture
def master(df_lead, df_hen, df_inv):
    """PHẢI có từ 2 kênh trở lên: cộng tỷ số của một kênh duy nhất thì ra đúng
    chính nó, và mọi phép kiểm 'gộp có trọng số' sẽ xanh giả."""
    lead = df_lead.copy()
    lead.loc[lead.index[:2], "NGUỒN"] = "Tiktok PXV"   # 2 khách mua đều về Tiktok
    return transform.build_master(lead, df_hen, df_inv, WINDOW)


@pytest.fixture
def costs():
    """Chi phí bằng nhau, doanh thu lệch hẳn — để tỷ số gộp khác tổng tỷ số."""
    return pd.DataFrame({
        "tháng": ["2026-01", "2026-01"],
        "kênh": ["Facebook", "Tiktok"],
        "mã bài QC": ["QC1", "QC2"],
        "chi phí": [2_000_000, 2_000_000],
    })


def _tong(kpi):
    return kpi[kpi["phạm vi"] == marts.KPI_TONG].iloc[0]


def test_dung_thu_tu_cot_va_co_dong_TONG(master, costs):
    kpi = marts.build_kpi(master, costs)
    assert list(kpi.columns) == marts.KPI_COLUMNS
    assert kpi["phạm vi"].iloc[0] == marts.KPI_TONG      # TỔNG luôn đứng đầu
    assert (kpi["phạm vi"] == marts.KPI_TONG).sum() == 1


def test_dong_TONG_khop_tong_cua_MASTER(master, costs):
    t = _tong(marts.build_kpi(master, costs))
    for cột, cờ in zip(["lead", "có_sđt", "có_hẹn", "khách_mua"],
                       transform.FUNNEL_FLAGS):
        assert t[cột] == int(master[cờ].sum())
    assert t["doanh_thu_toàn_bộ"] == int(master["Doanh Thu (VNĐ)"].sum())


def test_doanh_thu_toan_bo_lon_hon_phan_quy_ket(master, costs):
    """Chênh lệch chính là doanh thu khách vãng lai — thứ hay bị lấy nhầm làm mẫu số."""
    t = _tong(marts.build_kpi(master, costs))
    assert t["doanh_thu_toàn_bộ"] > t["doanh_thu_quy_kết"]
    assert pd.isna(marts.build_kpi(master, costs)["doanh_thu_toàn_bộ"].iloc[1])


def test_ty_le_chot_cua_TONG_KHAC_trung_binh_cac_kenh(master, costs):
    """Đây đúng là bug đang chặn: dashboard hiện AVG các kênh (9,6%) thay vì 7,87%."""
    kpi = marts.build_kpi(master, costs)
    kênh = kpi[kpi["phạm vi"] != marts.KPI_TONG]
    assert _tong(kpi)["tỷ_lệ_chốt_%"] != pytest.approx(kênh["tỷ_lệ_chốt_%"].mean())


def test_ROAS_va_CAC_co_trong_so_chu_khong_phai_tong_cac_ty_so(master, costs):
    kpi = marts.build_kpi(master, costs)
    t = _tong(kpi)
    kênh = kpi[kpi["phạm vi"] != marts.KPI_TONG]
    assert t["ROAS"] == pytest.approx(
        round(t["doanh_thu_quy_kết"] / t["chi phí"], 2))
    assert t["CAC"] == pytest.approx(round(t["chi phí"] / t["khách_mua"]))
    # Cộng các tỷ số lại phải RA KHÁC — nếu bằng nhau thì bảng này vô dụng.
    assert t["ROAS"] != pytest.approx(kênh["ROAS"].sum())


def test_khong_co_chi_phi_thi_tra_NaN_chu_khong_phai_0(master):
    """0 nghĩa là 'hiệu quả bằng 0'; ở đây phải là 'chưa có dữ liệu để tính'."""
    kpi = marts.build_kpi(master, pd.DataFrame(columns=["tháng", "kênh", "chi phí"]))
    assert kpi[["CPL", "CAC", "ROAS"]].isna().all().all()
    assert kpi["tỷ_lệ_chốt_%"].notna().any()   # tỷ lệ chốt không cần chi phí


def test_master_rong_van_du_cot(costs):
    kpi = marts.build_kpi(pd.DataFrame(), costs)
    assert kpi.empty and list(kpi.columns) == marts.KPI_COLUMNS


def test_clv_va_upsell_chi_dien_o_dong_TONG(master, costs, df_inv):
    dim = marts.build_dim_khach(master, df_inv)
    moi = marts.build_funnel_moi(df_inv)
    kpi = marts.build_kpi(master, costs, dim, moi)
    t = _tong(kpi)
    assert t["khách_mua_mồi"] == len(moi)
    assert t["CLV_TB"] == pytest.approx(round(dim["tổng_doanh_thu"].mean()))
    # Funnel mồi dựng từ hóa đơn nên không có cột kênh -> dòng kênh phải để trống.
    kênh = kpi[kpi["phạm vi"] != marts.KPI_TONG]
    assert kênh["upsell_90d_%"].isna().all()
