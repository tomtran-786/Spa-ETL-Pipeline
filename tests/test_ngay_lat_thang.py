"""Ngày bị lật ngày/tháng khi đưa dữ liệu cũ lên Sheets.

Sheets locale Mỹ đọc chuỗi '10/01/2026' thành 1 tháng 10. Ngày > 12 không lật
được nên nằm im, ngày <= 12 thì lật — kết quả VẪN là ngày hợp lệ, nên mắt
thường không thấy và mọi phép kiểm khoảng ngày đều xanh.

Hai lớp phòng thủ, test cả hai:
  1. migrate_lead_csv ghi .xlsx bằng Ô NGÀY THẬT -> không còn chuỗi để mà lật
  2. quality bắt 'hẹn sớm hơn lead' -> nếu vẫn lọt bằng đường khác thì job đỏ

Dữ liệu trong file này TOÀN BỘ LÀ BỊA.
"""
import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pxv import quality                              # noqa: E402
from pxv.clean import clean_phone, phone_kind        # noqa: E402
from scripts.migrate_lead_csv import _ghi_xlsx       # noqa: E402

openpyxl = pytest.importorskip("openpyxl")


# --- Lớp 1: file migrate ---------------------------------------------------

def test_xlsx_ghi_ngay_bang_o_ngay_that(tmp_path):
    """Ô ngày mang số serial, không phải chuỗi -> locale nào đọc cũng đúng."""
    df = pd.DataFrame({
        "NGÀY": ["10/01/2026", "28/07/2026"],
        "TÊN KHÁCH HÀNG": ["Khách Bịa Một", "Khách Bịa Hai"],
        "SỐ ĐT": ["0390000001", "0390000002"],
        "NGÀY HẸN": ["11/01/2026", None],
        "GIỜ HẸN": ["10h", None],
    })
    dich = tmp_path / "LEAD.xlsx"
    _ghi_xlsx(df, dich)

    ws = openpyxl.load_workbook(dich)["LEAD"]
    # Hàng 2 = dòng dữ liệu đầu. Cột 1 = NGÀY, cột 4 = NGÀY HẸN.
    assert ws.cell(row=2, column=1).value == dt.datetime(2026, 1, 10)
    assert ws.cell(row=2, column=4).value == dt.datetime(2026, 1, 11)
    assert ws.cell(row=2, column=1).number_format == "dd/MM/yyyy"
    # SĐT vẫn phải là text, nếu không mất số 0 đầu.
    assert ws.cell(row=2, column=3).value == "0390000001"
    assert ws.cell(row=2, column=3).number_format == "@"


def test_ngay_khong_doc_duoc_thi_giu_nguyen_chu(tmp_path):
    """Không đoán. Giữ chữ để người sửa tay, đừng biến thành ngày bừa."""
    df = pd.DataFrame({
        "NGÀY": ["chưa rõ", None],
        "TÊN KHÁCH HÀNG": ["Khách Bịa Ba", "Khách Bịa Bốn"],
        "SỐ ĐT": [None, None],
        "NGÀY HẸN": [None, None],
        "GIỜ HẸN": [None, None],
    })
    dich = tmp_path / "LEAD.xlsx"
    _ghi_xlsx(df, dich)

    o = openpyxl.load_workbook(dich)["LEAD"].cell(row=2, column=1)
    assert o.value == "chưa rõ"
    assert o.number_format == "@"


# --- Lớp 2: phép kiểm trong pipeline ---------------------------------------

def _lead_co_hen(ngay, hen):
    df = pd.DataFrame({
        "NGÀY": ngay,
        "NGÀY HẸN": hen,
        "TÊN KHÁCH HÀNG": [f"Khách Bịa {i}" for i in range(len(ngay))],
        "SỐ ĐT": ["039000000" + str(i % 10) for i in range(len(ngay))],
    })
    df["Ngày Lead"] = pd.to_datetime(df["NGÀY"], dayfirst=True)
    df["Phone_Clean"] = df["SỐ ĐT"].apply(clean_phone)
    df["Loại SĐT"] = df["SỐ ĐT"].apply(phone_kind)
    return df


def test_du_lieu_dung_thi_khong_bao_gi():
    ngay = ["05/01/2026", "06/01/2026", "20/01/2026"]
    hen = ["10/01/2026", "06/01/2026", "25/01/2026"]   # hẹn cùng ngày vẫn hợp lệ
    rep = quality.QualityReport()
    quality._check_dates(_lead_co_hen(ngay, hen), rep)

    check = next(c for c in rep.checks if c.tên == "Hẹn sớm hơn lead")
    assert check.trạng_thái == quality.OK
    assert check.giá_trị == "0/3"


def test_ngay_bi_lat_thi_job_do():
    """Lỗi lộ ra ở chỗ LẬT KHÔNG ĐỀU: ngày <= 12 lật, ngày > 12 nằm im.

    Lead 10/01 hóa thành 01/10 (tháng 10) trong khi hẹn 22/01 giữ nguyên
    tháng 1 — thành ra hẹn nằm trước lead 9 tháng.

        NGÀY      10/01/2026 -> 01/10/2026   NGÀY HẸN  22/01/2026 -> y nguyên
        NGÀY      11/01/2026 -> 01/11/2026   NGÀY HẸN  25/01/2026 -> y nguyên
        NGÀY      20/01/2026 -> y nguyên     NGÀY HẸN  25/01/2026 -> y nguyên
        NGÀY      05/01/2026 -> 01/05/2026   NGÀY HẸN  10/01/2026 -> 01/10/2026
    """
    ngay = ["01/10/2026", "01/11/2026", "20/01/2026", "01/05/2026"]
    hen = ["22/01/2026", "25/01/2026", "25/01/2026", "01/10/2026"]

    rep = quality.QualityReport()
    quality._check_dates(_lead_co_hen(ngay, hen), rep)

    check = next(c for c in rep.checks if c.tên == "Hẹn sớm hơn lead")
    assert check.trạng_thái == quality.FAIL
    assert "lật ngày/tháng" in check.ghi_chú
    assert (rep.cần_sửa["lý_do"] == "ngày hẹn sớm hơn ngày lead").any()


def test_hen_thieu_nam_thi_bo_qua_khong_bao_oan():
    """Dữ liệu cũ ghi '10/01' — parse không ra năm, không được tính là lỗi."""
    rep = quality.QualityReport()
    quality._check_dates(_lead_co_hen(["05/01/2026"], ["10/01"]), rep)

    check = next(c for c in rep.checks if c.tên == "Hẹn sớm hơn lead")
    assert check.giá_trị == "0/0"
    assert check.trạng_thái == quality.OK
