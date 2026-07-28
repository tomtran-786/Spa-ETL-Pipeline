"""Chuẩn hóa SĐT, tiền, ngày. Dữ liệu trong file này là BỊA, không phải khách thật."""
import numpy as np
import pandas as pd
import pytest

from pxv.clean import (PHONE_EMPTY, PHONE_INTL, PHONE_INVALID, PHONE_VN,
                       clean_money, clean_phone, out_of_window_mask,
                       parse_date_vn, phone_kind)


@pytest.mark.parametrize("raw,expected", [
    # --- số Việt Nam, các kiểu gõ khác nhau đều phải ra cùng một khóa ---
    ("0390000001", "0390000001"),
    ("390000001", "0390000001"),          # sales quên số 0 đầu
    ("84390000001", "0390000001"),        # dạng +84
    ("0084390000001", "0390000001"),      # dạng quay quốc tế 00
    ("+84 390 000 001", "0390000001"),    # có dấu cách và dấu cộng
    (390000001.0, "0390000001"),          # Excel đọc thành float
    ("0283822012", "0283822012"),         # cố định 10 số
    ("02838220123", "02838220123"),       # cố định 11 số

    # --- số quốc tế: GIỮ LẠI, không bỏ ---
    # Có khách Việt kiều xuất hiện ở cả file lead lẫn hóa đơn; bỏ đi là mất
    # khách khỏi funnel. Code cũ biến số này thành "016505550100" trông như số VN.
    ("16505550100", "+16505550100"),
    ("61422003072", "+61422003072"),
    ("4915000000000", "+4915000000000"),

    # --- rác: phải thành None ---
    ("0", None),                          # KiotViet ghi "0" khi không có SĐT
    ("00", None),
    ("12345678", None),                   # 8 chữ số, quá ngắn
    ("data 2018", None),                  # sales gõ ghi chú vào ô SĐT
    ("Khách đã nt vào zalo", None),
    ("", None),
    (None, None),
    (np.nan, None),
])
def test_clean_phone(raw, expected):
    assert clean_phone(raw) == expected


def test_phone_zero_khong_duoc_thanh_khoa_join():
    """Bug cũ: clean_phone('0') trả '0', biến mọi khách không có SĐT thành MỘT người.

    Bốn khách khác nhau (bốn khách khác nhau) đều có
    SĐT ghi '0' trong KiotViet nên bị gộp làm một, làm hỏng CLV và số khách.
    """
    assert clean_phone("0") is None
    assert clean_phone("0.0") is None


@pytest.mark.parametrize("raw,kind", [
    ("0390000001", PHONE_VN),
    ("16505550100", PHONE_INTL),
    ("12345678", PHONE_INVALID),
    ("data 2018", PHONE_INVALID),
    ("", PHONE_EMPTY),
    (None, PHONE_EMPTY),
])
def test_phone_kind(raw, kind):
    assert phone_kind(raw) == kind


@pytest.mark.parametrize("raw,expected", [
    ("9.420.000", 9420000),   # KiotViet dùng dấu chấm ngăn nghìn
    ("900.000", 900000),
    (900000, 900000),
    ("0", 0),
    ("", 0),
    (None, 0),
    ("không phải số", 0),
])
def test_clean_money(raw, expected):
    assert clean_money(raw) == expected


def test_parse_date_uu_tien_ngay_truoc():
    assert parse_date_vn("04/01/2026") == pd.Timestamp("2026-01-04")


def test_parse_date_khong_tu_sua_nam():
    """Code cũ ép year==2025 & month<=3 thành 2026. Sang 2027 sẽ phá dữ liệu thật.

    Giờ parse đúng những gì được ghi; việc phát hiện năm nghi sai là của
    quality.py, và người sửa tại nguồn chứ không phải code đoán.
    """
    assert parse_date_vn("19/01/2025") == pd.Timestamp("2025-01-19")


def test_parse_date_khong_doc_duoc_tra_NaT():
    assert pd.isna(parse_date_vn("không phải ngày"))
    assert pd.isna(parse_date_vn(None))


def test_out_of_window_mask():
    s = pd.Series([pd.Timestamp("2024-05-01"), pd.Timestamp("2026-05-01"),
                   pd.Timestamp("2030-01-01"), pd.NaT])
    mask = out_of_window_mask(s, pd.Timestamp("2025-01-01"), pd.Timestamp("2027-12-31"))
    assert list(mask) == [True, False, True, False]


# --- Suy năm cho ngày thiếu năm (chỉ dùng cho dữ liệu cũ) -----------------

def test_thieu_nam_khong_co_moc_thi_tra_NaT():
    """Không có mốc thì KHÔNG đoán bừa — thà trống còn hơn sai năm."""
    assert pd.isna(parse_date_vn("10/01"))
    assert pd.isna(parse_date_vn("22/1"))


@pytest.mark.parametrize("hen,lead,mong_doi", [
    ("10/01", "2026-01-05", "2026-01-10"),   # hẹn cùng tháng với lead
    ("22/1",  "2026-01-02", "2026-01-22"),   # tháng viết tắt 1 chữ số
    ("05/01", "2025-12-28", "2026-01-05"),   # hẹn vắt qua năm -> phải là năm sau
    ("28/12", "2026-12-01", "2026-12-28"),   # cuối năm, không nhảy sang 2027
])
def test_suy_nam_tu_ngay_lead(hen, lead, mong_doi):
    """Hẹn luôn ở tương lai, nên chọn năm gần nhất mà hẹn >= ngày lead."""
    assert parse_date_vn(hen, pd.Timestamp(lead)) == pd.Timestamp(mong_doi)


def test_ngay_khong_ton_tai_tra_NaT():
    assert pd.isna(parse_date_vn("31/02", pd.Timestamp("2026-01-01")))


def test_co_nam_day_du_thi_bo_qua_moc():
    """Chuỗi đã có năm thì mốc không được phép ghi đè."""
    assert parse_date_vn("19/01/2025", pd.Timestamp("2026-06-01")) == pd.Timestamp("2025-01-19")
