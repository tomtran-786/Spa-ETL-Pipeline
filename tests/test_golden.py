"""Đối chiếu output mới với bản đã nghiệm thu, để chứng minh refactor không lệch số.

`output/Master_Pipeline_2026.xlsx` là kết quả của notebook cũ, đã được đối chiếu
thủ công và dùng để báo cáo. Test này khóa lại MỌI chênh lệch giữa bản mới và
bản đó — mỗi chênh lệch phải là một bug đã sửa có chủ đích, ghi rõ nguyên nhân.

File golden nằm ngoài git (chứa dữ liệu khách), nên test tự bỏ qua khi không có.
"""
import pandas as pd
import pytest

from pxv import config, io_local, transform

GOLDEN = config.OUT_DIR / "Master_Pipeline_2026.xlsx"
pytestmark = pytest.mark.skipif(
    not GOLDEN.exists(),
    reason="Không có file golden (bị .gitignore chặn) — chỉ chạy được ở máy local",
)

# Chênh lệch ĐÃ BIẾT và CÓ CHỦ ĐÍCH so với notebook cũ.
SAI_LECH_CO_CHU_DICH = {
    "lead_ngoài_cửa_sổ": 35,   # bỏ quy tắc ép năm 2025->2026
    "lead_sđt_rác": 8,         # SĐT là ghi chú hoặc số quá ngắn
}


@pytest.fixture(scope="module")
def new_master():
    lead = io_local.load_leads()
    hen = io_local.load_appointments(lead)
    inv = io_local.load_invoices()
    return transform.build_master(lead, hen, inv)


@pytest.fixture(scope="module")
def golden():
    return pd.read_excel(GOLDEN)


def test_doanh_thu_khong_doi(new_master, golden):
    """Chỉ số quan trọng nhất: tiền không được xê dịch dù chỉ 1 đồng.

    Bản mới bỏ SĐT rác nhưng vẫn giữ hóa đơn của khách không có SĐT, nên tổng
    doanh thu phải khớp tuyệt đối với bản cũ.
    """
    assert new_master["Doanh Thu (VNĐ)"].sum() == golden["Doanh Thu (VNĐ)"].sum()


def test_so_hoa_don_khong_doi(new_master, golden):
    assert new_master["Mã hóa đơn"].nunique() == golden["Mã hóa đơn"].nunique()


def test_lead_giam_dung_bang_so_dong_da_giai_thich(new_master, golden):
    giảm = int(golden["[F] 1_Có Inbox"].sum()) - int(new_master["[F] 1_Có Inbox"].sum())
    assert giảm == SAI_LECH_CO_CHU_DICH["lead_ngoài_cửa_sổ"], (
        f"Lead giảm {giảm}, kỳ vọng {SAI_LECH_CO_CHU_DICH['lead_ngoài_cửa_sổ']} "
        "(35 dòng ghi 19/01/2025, trước đây bị ép thành 2026). "
        "Lệch số này nghĩa là có thay đổi ngoài dự kiến."
    )


def test_pheu_ban_moi_thu_hep_dan(new_master):
    vals = [int(new_master[f].sum()) for f in transform.FUNNEL_FLAGS]
    assert vals == sorted(vals, reverse=True)


def test_nhom_vang_lai_khong_doi(new_master, golden):
    """Nhóm 1 phải giữ nguyên: bản mới tách 4 khách bị gộp nhầm dưới SĐT '0',
    nhưng đồng thời gộp lại các hóa đơn không SĐT thành dòng riêng."""
    a = (new_master["Phân nhóm MECE"] == transform.MECE_WALKIN).sum()
    b = golden["Phân nhóm MECE"].str.startswith("Nhóm 1").sum()
    assert a == b


def test_khong_con_sdt_gia_bat_dau_bang_016(new_master):
    """Bug cũ: số quốc tế 11 chữ số bị thêm '0' thành SĐT giả 12 chữ số."""
    sđt = new_master["SĐT Cuối"].dropna().astype(str)
    giả = sđt[sđt.str.match(r"^0\d{11,}$")]
    assert giả.empty, f"còn SĐT giả: {giả.unique()[:5]}"


def test_khong_con_sdt_zero(new_master):
    """SĐT '0' từng gộp 4 khách khác nhau làm một."""
    assert not (new_master["SĐT Cuối"].astype(str) == "0").any()
