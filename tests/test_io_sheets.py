"""Mảng ô gửi lên Sheets phải JSON hóa được — nếu không job chết GIỮA CHỪNG.

Bối cảnh: ``requests`` gọi ``json.dumps(..., allow_nan=False)``. Một cột
``datetime.date`` (``marts.build_daily`` sinh ra bằng ``.dt.date``) từng làm
``python -m pxv.run_daily`` với backend sheets ném ``TypeError`` sau khi đã ghi
đè xong MASTER, DIM_KHACH, FUNNEL_MOI.

Test không cần mạng: ``_to_cells`` là hàm thuần.
"""
import datetime as dt
import json

import numpy as np
import pandas as pd

from pxv.io_sheets import _to_cells


def _dumps(cells):
    """Mô phỏng đúng cách requests đóng gói payload."""
    return json.dumps(cells, allow_nan=False)


def test_cot_date_object_json_hoa_duoc():
    """Đúng hình dạng FACT_DAILY: cột 'ngày' là datetime.date, dtype object."""
    df = pd.DataFrame({
        "ngày": [dt.date(2026, 1, 15), dt.date(2026, 2, 1)],
        "Kênh Tiếp Cận": ["Facebook", "Tiktok"],
        "doanh_thu": [1_000_000, 0],
    })
    assert df["ngày"].dtype == object

    cells = _to_cells(df)
    _dumps(cells)  # không được ném TypeError
    assert cells[0][0] == "2026-01-15"


def test_moi_kieu_la_deu_thanh_o_hop_le():
    df = pd.DataFrame({
        "ts": pd.to_datetime(["2026-03-04", None]),
        "date_obj": [dt.date(2026, 3, 4), None],
        "gio": [dt.time(10, 30), None],
        "co": [True, False],
        "so": [np.int64(7), np.int64(-1)],
        "thuc": [float("inf"), float("nan")],
        "chu": ["a", None],
        "period": [pd.Period("2026-03", freq="M"), None],
    })
    cells = _to_cells(df)
    _dumps(cells)

    assert cells[0] == ["2026-03-04", "2026-03-04", "10:30", "TRUE", 7, "", "a", "2026-03"]
    # NaT / None / NaN / inf đều thành ô rỗng, không thành chuỗi "NaT" hay "nan"
    assert cells[1] == ["", "", "", "FALSE", -1, "", "", ""]


def test_gio_ten_cot_va_so_dong():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    assert _to_cells(df) == [[1, "x"], [2, "y"], [3, "z"]]
