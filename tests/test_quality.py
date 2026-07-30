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


# --- Nguồn rỗng: phải báo rõ, không được ném TypeError ---------------------

def _lead_rong():
    """Giống hệt io_sheets.load_leads() khi tab LEAD chỉ có hàng tiêu đề.

    Quan trọng: cột ngày lúc này mang dtype OBJECT chứ không phải datetime64,
    nên `Ngày HĐ - Ngày Lead` từng ném TypeError giữa chừng.
    """
    from pxv import schema
    from pxv.clean import clean_phone, parse_date_vn, phone_kind
    df = pd.DataFrame(columns=schema.LEAD_REQUIRED + schema.LEAD_OPTIONAL)
    df["Phone_Clean"] = df["SỐ ĐT"].apply(clean_phone)
    df["Loại SĐT"] = df["SỐ ĐT"].apply(phone_kind)
    df["Ngày Lead"] = df["NGÀY"].apply(parse_date_vn)
    return df


def _hen_rong():
    return pd.DataFrame({"Phone_Clean": pd.Series(dtype=object),
                         "NGÀY HẸN": pd.Series(dtype=object)})


def test_sheet_lead_rong_KHONG_lam_crash(df_inv):
    """Trước đây ném 'unsupported operand type(s) for -: Timestamp and float'."""
    master = transform.build_master(_lead_rong(), _hen_rong(), df_inv, WINDOW)
    assert len(master) > 0, "vẫn phải dựng được bảng từ hóa đơn vãng lai"


def test_sheet_lead_rong_thi_bao_DUNG_voi_ly_do_ro(df_inv):
    lead = _lead_rong()
    master = transform.build_master(lead, _hen_rong(), df_inv, WINDOW)
    rep = quality.run_checks(lead, df_inv, master, None, None)
    loi = {c.tên for c in rep.failed}
    assert "Sheet LEAD có dữ liệu" in loi
    ghi_chu = next(c.ghi_chú for c in rep.checks if c.tên == "Sheet LEAD có dữ liệu")
    assert "hàng tiêu đề" in ghi_chu   # nói được phải làm gì, không chỉ báo lỗi


def test_kho_hoa_don_rong_thi_bao_DUNG(df_lead, df_hen):
    inv_rong = pd.DataFrame(columns=["Mã hóa đơn", "Phone_Clean", "Ngày HĐ",
                                     "Doanh Thu (VNĐ)", "Tên hàng", "Mã khách hàng"])
    master = transform.build_master(df_lead, df_hen, inv_rong, WINDOW)
    rep = quality.run_checks(df_lead, inv_rong, master, None, None)
    assert "Kho hóa đơn có dữ liệu" in {c.tên for c in rep.failed}


def test_ca_hai_nguon_deu_co_thi_khong_bao_gi(bo_ba):
    lead, inv, master = bo_ba
    rep = quality.run_checks(lead, inv, master, None, None)
    loi = {c.tên for c in rep.failed}
    assert "Sheet LEAD có dữ liệu" not in loi
    assert "Kho hóa đơn có dữ liệu" not in loi


# --- Nghi lật ngày/tháng ------------------------------------------------------
# Lỗi: Sheets locale Mỹ đọc '10/01/2026' thành 1 tháng 10. Ngày > 12 không lật
# được nên nằm im, ngày <= 12 thì lật — kết quả vẫn là ngày hợp lệ. Dấu vân tay
# là những tháng KHÔNG CÓ lead nào sau ngày 12.

TEN_KIEM_LAT = "Nghi lật ngày/tháng"
_THANG_NAY = pd.Timestamp.now().normalize().to_period("M")


def _ngay(lech_thang: int, cac_ngay):
    """Ngày trong tháng cách tháng hiện tại ``lech_thang`` tháng về trước."""
    ky = _THANG_NAY - lech_thang
    return [pd.Timestamp(year=ky.year, month=ky.month, day=d) for d in cac_ngay]


def _kiem_lat(*nhom_ngay):
    rep = quality.QualityReport()
    ngay = [d for nhom in nhom_ngay for d in nhom]
    quality._check_lat_ngay_thang(pd.DataFrame({"Ngày Lead": ngay}), rep)
    return next(c for c in rep.checks if c.tên == TEN_KIEM_LAT)


def test_ngay_trai_deu_ca_thang_thi_khong_bao():
    kiem = _kiem_lat(_ngay(2, range(1, 26)), _ngay(3, range(1, 26)))
    assert kiem.trạng_thái == quality.OK


def test_hai_thang_khong_co_ngay_nao_sau_12_thi_phai_DUNG():
    kiem = _kiem_lat(_ngay(2, [1, 2, 3, 4, 5]), _ngay(3, [1, 2, 3, 4, 5]))
    assert kiem.trạng_thái == FAIL
    # Thông báo phải chỉ được việc cần làm, không chỉ báo có lỗi.
    assert "Convert text to numbers" in kiem.ghi_chú


def test_mot_thang_le_loi_chua_du_de_DUNG():
    """Một tháng vắng nửa cuối có thể là spa nghỉ; lật thật tạo ra cả chục tháng."""
    kiem = _kiem_lat(_ngay(2, [1, 2, 3, 4, 5]), _ngay(3, range(1, 26)))
    assert kiem.trạng_thái == quality.OK


def test_thang_it_lead_khong_du_mau_thi_bo_qua():
    kiem = _kiem_lat(_ngay(2, [1, 2]), _ngay(3, [1, 2]), _ngay(4, range(1, 26)))
    assert kiem.trạng_thái == quality.OK


def test_thang_dang_chay_khong_bi_tinh_oan():
    """Chạy ngày mùng 5 thì tháng này chỉ có ngày 1-5 — hình dạng y hệt tháng bị lật."""
    kiem = _kiem_lat(_ngay(0, [1, 2, 3, 4, 5]), _ngay(1, [1, 2, 3, 4, 5]))
    assert kiem.trạng_thái == quality.OK


def test_lead_ghi_ngay_tuong_lai_van_bi_soi():
    """Lật ngày đẩy phần lớn dòng sang tháng CHƯA TỚI — bỏ qua là để lọt lỗi."""
    kiem = _kiem_lat(_ngay(-2, [1, 2, 3, 4, 5]), _ngay(-3, [1, 2, 3, 4, 5]))
    assert kiem.trạng_thái == FAIL


def test_lead_bi_lat_ngay_thang_lam_DUNG_ca_pipeline(bo_ba):
    """Phép kiểm phải chặn được job thật, không chỉ trả về một dòng trạng thái."""
    lead, inv, master = bo_ba
    lat = pd.concat(
        [lead.assign(**{"Ngày Lead": d})
         for d in _ngay(2, [1, 2, 3, 4, 5]) + _ngay(3, [1, 2, 3, 4, 5])],
        ignore_index=True)
    rep = quality.run_checks(lat, inv, master, None, None)
    assert TEN_KIEM_LAT in _ten_cac_loi(rep)
    with pytest.raises(quality.DataQualityError):
        rep.raise_if_failed()
