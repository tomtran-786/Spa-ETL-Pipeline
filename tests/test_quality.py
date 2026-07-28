"""Phép kiểm chất lượng — nhất là phép chống mất dữ liệu im lặng.

Dữ liệu trong file này là BỊA.
"""
import pandas as pd
import pytest

from pxv import quality, transform
from pxv.quality import FAIL, MOC_DT_THANG_DONG, MOC_SO_DONG_LEAD

WINDOW = pd.Timestamp("2026-01-01")


@pytest.fixture
def bo_ba(df_lead, df_hen, df_inv):
    master = transform.build_master(df_lead, df_hen, df_inv, WINDOW)
    return df_lead, df_inv, master


def _ten_cac_loi(rep):
    return {c.tên for c in rep.failed}


def test_lan_chay_dau_khong_co_moc_thi_khong_fail(bo_ba):
    lead, inv, master = bo_ba
    rep = quality.run_checks(lead, inv, master, None, truoc=None)
    assert "Số dòng lead không giảm" not in _ten_cac_loi(rep)


def test_ghi_lai_2_moc_cho_lan_sau(bo_ba):
    lead, inv, master = bo_ba
    df = quality.run_checks(lead, inv, master, None, truoc=None).to_frame()
    assert MOC_SO_DONG_LEAD in set(df["tên"])
    assert MOC_DT_THANG_DONG in set(df["tên"])


def test_khong_phá_gi_thi_khong_bao_do(bo_ba):
    lead, inv, master = bo_ba
    truoc = {MOC_SO_DONG_LEAD: len(lead),
             MOC_DT_THANG_DONG: quality.doanh_thu_thang_da_dong(inv)}
    rep = quality.run_checks(lead, inv, master, None, truoc)
    assert "Số dòng lead không giảm" not in _ten_cac_loi(rep)
    assert "Doanh thu tháng đã đóng không đổi" not in _ten_cac_loi(rep)


def test_xoa_dong_lead_thi_phai_DUNG(bo_ba):
    """Đây là phép kiểm DUY NHẤT bắt được việc xóa dòng ở sheet nguồn.

    Các phép kiểm khác đều so nguồn với kết quả — cả hai cùng đến từ nguồn đã
    bị xóa nên hai vế vẫn bằng nhau và báo xanh.
    """
    lead, inv, master = bo_ba
    truoc = {MOC_SO_DONG_LEAD: len(lead) + 500}   # lần trước nhiều hơn 500 dòng
    rep = quality.run_checks(lead, inv, master, None, truoc)
    assert "Số dòng lead không giảm" in _ten_cac_loi(rep)


def test_them_dong_lead_thi_khong_sao(bo_ba):
    """Dữ liệu được phép TĂNG — sales nhập thêm mỗi ngày là chuyện bình thường."""
    lead, inv, master = bo_ba
    truoc = {MOC_SO_DONG_LEAD: max(len(lead) - 3, 0)}
    rep = quality.run_checks(lead, inv, master, None, truoc)
    assert "Số dòng lead không giảm" not in _ten_cac_loi(rep)


def test_doanh_thu_thang_da_dong_doi_thi_phai_DUNG(bo_ba):
    """Tháng đã kết thúc thì doanh thu không được đổi nữa."""
    lead, inv, master = bo_ba
    thuc = quality.doanh_thu_thang_da_dong(inv)
    if thuc == 0:
        pytest.skip("fixture không có hóa đơn thuộc tháng đã đóng")
    truoc = {MOC_DT_THANG_DONG: int(thuc * 2)}   # lần trước gấp đôi
    rep = quality.run_checks(lead, inv, master, None, truoc)
    assert "Doanh thu tháng đã đóng không đổi" in _ten_cac_loi(rep)


def test_doanh_thu_thang_dang_chay_khong_tinh_vao_moc(df_inv):
    """Tháng hiện tại còn phát sinh nên không được đưa vào phép so."""
    hom_nay = pd.Timestamp.now().normalize()
    them = df_inv.iloc[[0]].copy()
    them["Mã hóa đơn"] = "HD_THANG_NAY"
    them["Ngày HĐ"] = hom_nay
    them["Doanh Thu (VNĐ)"] = 999_000_000

    truoc = quality.doanh_thu_thang_da_dong(df_inv)
    sau = quality.doanh_thu_thang_da_dong(pd.concat([df_inv, them], ignore_index=True))
    assert truoc == sau, "hóa đơn tháng này không được cộng vào mốc"


def test_doc_moc_cu_bo_qua_bang_hong():
    assert quality.doc_moc_cu(None) == {}
    assert quality.doc_moc_cu(pd.DataFrame()) == {}
    assert quality.doc_moc_cu(pd.DataFrame({"khác": [1]})) == {}


def test_doc_moc_cu_doc_duoc_so_co_dau_phay():
    """Giá trị ghi ra sheet có dấu phân cách nghìn, đọc lại phải ra số."""
    df = pd.DataFrame({"tên": [MOC_SO_DONG_LEAD, MOC_DT_THANG_DONG],
                       "giá_trị": ["2,439", "3,468,547,500"]})
    assert quality.doc_moc_cu(df) == {MOC_SO_DONG_LEAD: 2439,
                                      MOC_DT_THANG_DONG: 3468547500}
