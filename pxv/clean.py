"""Chuẩn hóa dữ liệu thô: số điện thoại, tiền, ngày, giá trị phân loại."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

# Đầu số di động VN: 03x 05x 07x 08x 09x (10 số). Cố định: 02x (10-11 số).
_VN_MOBILE = re.compile(r"^0[35789]\d{8}$")
_VN_LANDLINE = re.compile(r"^02\d{8,9}$")

PHONE_VN = "vn"
PHONE_INTL = "intl"
PHONE_INVALID = "invalid"
PHONE_EMPTY = "empty"


def _digits(value) -> str | None:
    """Rút phần số. Cắt đuôi '.0' do Excel đọc SĐT thành float."""
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    d = re.sub(r"\D", "", text.split(".")[0])
    return d or None


def clean_phone(value) -> str | None:
    """Chuẩn hóa SĐT thành khóa join.

    - Số VN      -> ``0XXXXXXXXX``
    - Số quốc tế -> ``+<chữ số>``  (giữ lại chứ không bỏ: có khách Việt kiều
      xuất hiện ở cả file lead lẫn hóa đơn, bỏ đi là mất khách khỏi funnel)
    - Rác        -> ``None``  (quá ngắn, hoặc sales gõ ghi chú vào ô SĐT)

    Code cũ làm ``'0' + p`` cho mọi số không bắt đầu bằng 0, khiến số Mỹ
    ``16505550100`` thành ``016505550100`` — một SĐT giả 12 chữ số trông như
    số VN.
    """
    d = _digits(value)
    if d is None:
        return None
    if d.startswith("00"):  # dạng quay quốc tế 00<mã nước>
        d = d[2:]

    for candidate in _vn_candidates(d):
        if _VN_MOBILE.match(candidate) or _VN_LANDLINE.match(candidate):
            return candidate

    if 10 <= len(d) <= 15:
        return "+" + d
    return None


def _vn_candidates(d: str):
    """Các cách diễn giải một chuỗi số thành SĐT VN, theo thứ tự ưu tiên."""
    if d.startswith("84") and len(d) == 11:
        yield "0" + d[2:]
    if d.startswith("0"):
        yield d
    if len(d) == 9:
        yield "0" + d


def phone_kind(value) -> str:
    """Phân loại SĐT để đếm được chất lượng nhập liệu."""
    d = _digits(value)
    if d is None:
        return PHONE_EMPTY
    cleaned = clean_phone(value)
    if cleaned is None:
        return PHONE_INVALID
    return PHONE_INTL if cleaned.startswith("+") else PHONE_VN


def clean_money(value) -> int:
    """'9.420.000' -> 9420000. KiotViet dùng dấu chấm ngăn nghìn."""
    if pd.isna(value):
        return 0
    try:
        return int(float(str(value).replace(".", "").replace(",", "").strip()))
    except (ValueError, TypeError):
        return 0


# Chuỗi chỉ có ngày và tháng, không có năm: '10/01', '22/1', '4/1'.
_DDMM = re.compile(r"^(\d{1,2})\s*[/-]\s*(\d{1,2})$")


def parse_date_vn(value, sau_ngay=None):
    """Parse ngày kiểu Việt (dd/mm/yyyy). Không đoán, không sửa năm.

    Code cũ ép ``year == 2025 and month <= 3`` thành 2026 để vá 35 dòng gõ nhầm.
    Sang 2027 quy tắc đó sẽ âm thầm bóp méo dữ liệu thật, nên bỏ hẳn. Ngày nằm
    ngoài khoảng hợp lệ được báo riêng qua :func:`out_of_window_mask`.

    ``sau_ngay`` — chỉ dùng cho DỮ LIỆU CŨ. Sales từng gõ ngày hẹn thiếu năm
    ('10/01', '22/1'): 327/328 dòng không parse được, khiến mọi biểu đồ theo
    ngày hẹn trống trơn. Truyền ngày lead vào đây thì năm được suy sao cho ngày
    hẹn KHÔNG SỚM HƠN ngày lead — hẹn luôn ở tương lai, nên quy tắc này tự xử
    lý được cả ca hẹn vắt qua năm (lead 28/12, hẹn 05/01 năm sau).

    Không truyền ``sau_ngay`` thì chuỗi thiếu năm trả ``NaT`` như cũ — cố tình,
    để không đoán bừa. Sheet mới đã ép ``dd/MM/yyyy`` nên dữ liệu mới không cần.
    """
    if pd.isna(value):
        return pd.NaT
    text = str(value).strip()
    if not text:
        return pd.NaT

    m = _DDMM.match(text)
    if m:
        if sau_ngay is None or pd.isna(sau_ngay):
            return pd.NaT
        return _suy_nam(int(m.group(1)), int(m.group(2)), pd.Timestamp(sau_ngay))

    return pd.to_datetime(text, dayfirst=True, errors="coerce")


def _suy_nam(ngay: int, thang: int, moc: pd.Timestamp):
    """Chọn năm gần nhất sao cho (ngày, tháng) không sớm hơn mốc."""
    moc = moc.normalize()
    for nam in (moc.year, moc.year + 1):
        try:
            d = pd.Timestamp(year=nam, month=thang, day=ngay)
        except ValueError:      # 31/02 chẳng hạn
            return pd.NaT
        if d >= moc:
            return d
    return pd.NaT


def out_of_window_mask(series: pd.Series, lo: pd.Timestamp, hi: pd.Timestamp) -> pd.Series:
    """Đánh dấu ngày đã parse được nhưng nằm ngoài khoảng hợp lệ (nghi gõ nhầm)."""
    return series.notna() & ((series < lo) | (series > hi))


def parse_lead_dates(ngay: pd.Series, mac_dinh) -> pd.Series:
    """Cột ``Ngày Lead`` cho cả hai backend. Ô ĐỂ TRỐNG được gán ``mac_dinh``.

    Trước đây ô trống thành ``NaT``, mà ``NaT >= window_start`` luôn False nên
    ``build_master`` vứt luôn 20 lead — không bảng nào hiện, không phép kiểm nào
    đếm. Nghiệp vụ chốt gán về đầu kỳ để chúng vẫn nằm trong phễu.

    CHỈ ô trống mới được gán. Ô có nội dung mà không parse được vẫn trả ``NaT``:
    đó là lỗi nhập liệu thật, gán mặc định lên nó vừa bóp méo số vừa giết mất
    phép kiểm "Ngày không đọc được".

    Nhận ``mac_dinh`` qua tham số thay vì đọc ``config`` để module này giữ nguyên
    tính chất hàm thuần — dễ test, và không tạo import vòng.
    """
    ô_trống = ngay.isna() | (ngay.astype(str).str.strip() == "")
    return ngay.apply(parse_date_vn).where(~ô_trống, mac_dinh)


def normalize_text(value) -> str:
    """Chuẩn hóa chuỗi phân loại để so khớp: bỏ khoảng trắng thừa, viết hoa."""
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().upper()


def apply_alias(value, alias_map: dict[str, str]):
    """Sửa chính tả theo bảng ánh xạ ('INSTGRAM' -> 'Instagram').

    Không khớp thì trả nguyên giá trị gốc — việc phát hiện giá trị lạ do
    :mod:`pxv.quality` lo, không phải chỗ này.
    """
    if pd.isna(value):
        return value
    return alias_map.get(normalize_text(value), value)
