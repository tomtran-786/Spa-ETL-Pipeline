"""Cờ phễu và bảo toàn doanh thu — hai thứ dễ sai nhất khi merge nhiều nguồn."""
import pandas as pd
import pytest

from pxv import marts, transform

WINDOW = pd.Timestamp("2026-01-01")


@pytest.fixture
def master(df_lead, df_hen, df_inv):
    return transform.build_master(df_lead, df_hen, df_inv, WINDOW)


def test_moi_sdt_chi_dem_mot_lan(master):
    """Khách HD003 mua hóa đơn 2 mặt hàng + 1 hóa đơn khác -> nhiều dòng,
    nhưng chỉ được tính là 1 lead ở mỗi bước phễu."""
    có_sđt = master[master["SĐT Cuối"].notna()]
    for flag in transform.FUNNEL_FLAGS:
        assert có_sđt.groupby("SĐT Cuối")[flag].sum().max() <= 1


def test_pheu_thu_hep_dan(master):
    vals = [int(master[f].sum()) for f in transform.FUNNEL_FLAGS]
    assert vals == sorted(vals, reverse=True), f"phễu nở ra ở bước sau: {vals}"


def test_vang_lai_khong_lam_phinh_pheu(master):
    """Khách vãng lai chưa từng inbox nên không thuộc phễu marketing.

    Bug cũ tính [F]4 trên mọi dòng có hóa đơn, khiến F4 (505) > F3 (313).
    """
    vãng_lai = master[master["Phân nhóm MECE"] == transform.MECE_WALKIN]
    assert vãng_lai["[F] 1_Có Inbox"].sum() == 0
    assert vãng_lai["[F] 4_Có Ra Đơn"].sum() == 0
    assert vãng_lai["[Vãng lai] Có Ra Đơn"].sum() > 0


def test_doanh_thu_khong_bi_cong_trung_theo_mat_hang(master, df_inv):
    """'Khách cần trả' là TỔNG hóa đơn lặp trên từng dòng mặt hàng.

    HD003 có 2 mặt hàng, mỗi dòng ghi 8.000.000. Cộng thẳng ra 16tr — sai.
    """
    assert master["Doanh Thu (VNĐ)"].sum() == 5_000_000 + 900_000 + 8_000_000 + 7_000_000


def test_hoa_don_khong_co_sdt_van_duoc_tinh_doanh_thu(master):
    """HD004 có SĐT ghi '0'. Không join được với lead, nhưng tiền là tiền thật."""
    hd004 = master[master["Mã hóa đơn"] == "HD004"]
    assert len(hd004) == 1
    assert hd004["Doanh Thu (VNĐ)"].iloc[0] == 7_000_000
    assert hd004["Phân nhóm MECE"].iloc[0] == transform.MECE_WALKIN


def test_khong_rot_hoa_don_nao_khi_merge(master, df_inv):
    nguồn = df_inv[df_inv["Ngày HĐ"] >= WINDOW]["Mã hóa đơn"].nunique()
    assert master["Mã hóa đơn"].nunique() == nguồn


def test_lead_khong_co_sdt_van_duoc_dem_la_lead(master):
    nhóm0 = master[master["Phân nhóm MECE"] == transform.MECE_NO_PHONE]
    assert len(nhóm0) == 1
    assert nhóm0["[F] 1_Có Inbox"].iloc[0] == 1
    assert nhóm0["[F] 2_Có SĐT"].iloc[0] == 0


def test_dim_khach_moi_sdt_mot_dong(master, df_inv):
    dim = marts.build_dim_khach(master, df_inv, WINDOW)
    assert dim["SĐT"].is_unique
    # 0912345678 mua HD002 + HD003 -> 2 hóa đơn, tổng 8.9tr
    khách = dim[dim["SĐT"] == "0912345678"].iloc[0]
    assert khách["số_hóa_đơn"] == 2
    assert khách["tổng_doanh_thu"] == 8_900_000
    assert bool(khách["là_khách_quay_lại"]) is True


def test_funnel_moi_bat_duoc_upsell(df_inv):
    """0912345678 mua GÓI TIẾT KIỆM (mồi) 20/01, rồi Tạo sợi tả thực 01/02."""
    fm = marts.build_funnel_moi(df_inv, WINDOW)
    row = fm[fm["SĐT"] == "0912345678"].iloc[0]
    assert bool(row["upsell_30d"])
    assert row["doanh_thu_upsell"] == 8_000_000
    assert row["số_ngày_đến_upsell"] == 12


def test_funnel_daily_dung_dang_long_va_bao_toan_cac_buoc(master):
    """Mart cho Looker Funnel phải có nhãn bước + metric, không được lệch số."""
    funnel = marts.build_funnel_daily(marts.build_daily(master))

    assert list(funnel.columns) == marts.FUNNEL_DAILY_COLUMNS
    assert set(funnel["Bước phễu"]) == {s[0] for s in marts.FUNNEL_STAGES}

    actual = funnel.groupby("Bước phễu")["Số khách"].sum().to_dict()
    expected = {
        label: int(master[flag].sum())
        for label, _, _, flag in marts.FUNNEL_STAGES
    }
    assert actual == expected

    orders = (funnel[["Bước phễu", "Thứ tự bước"]]
              .drop_duplicates().sort_values("Thứ tự bước"))
    assert orders["Bước phễu"].tolist() == [s[0] for s in marts.FUNNEL_STAGES]
