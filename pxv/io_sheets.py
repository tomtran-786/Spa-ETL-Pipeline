"""Đọc/ghi Google Sheets. Cùng interface với ``io_local.py``.

Xác thực bằng Service Account: key JSON nằm ở biến môi trường ``GCP_SA_KEY``
(GitHub Actions lấy từ Secrets). Service account phải được share quyền:
  - PXV_NHẬP_LIỆU   : Viewer
  - PXV_KHO         : Editor
  - PXV_DASHBOARD   : Editor

Chỉ share ĐÚNG 3 file đó, không share cả Drive — key rò rỉ thì thiệt hại giới hạn.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os

import numpy as np
import pandas as pd

from . import config, schema
from .clean import (clean_money, clean_phone, parse_date_vn, parse_lead_dates,
                    phone_kind)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

# Ghi tối đa ngần này dòng mỗi lần gọi API. Sheets giới hạn kích thước payload,
# đẩy 20.000 dòng × 30 cột trong một request sẽ bị từ chối.
BATCH_ROWS = 5000

# Cột phải giữ dạng text, nếu không Sheets nuốt số 0 đầu ('0389...' -> 389...).
TEXT_COLUMNS = {"SĐT Cuối", "SĐT", "Mã hóa đơn", "Mã khách hàng", "Mã hàng"}


def _client():
    import gspread
    from google.oauth2.service_account import Credentials

    raw = os.environ.get("GCP_SA_KEY")
    if not raw:
        raise RuntimeError(
            "Thiếu biến môi trường GCP_SA_KEY. Chạy local thì dùng backend 'local' "
            "(PXV_BACKEND=local); chạy trên GitHub Actions thì kiểm tra Secrets."
        )
    creds = Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    return gspread.authorize(creds)


def _read_sheet(spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
    """Đọc nguyên trạng thành DataFrame chuỗi. Hàng 1 là header."""
    ws = _client().open_by_key(spreadsheet_id).worksheet(sheet_name)
    values = ws.get_all_values()
    if len(values) < 2:
        return pd.DataFrame(columns=values[0] if values else [])
    header = [h.strip() for h in values[0]]
    df = pd.DataFrame(values[1:], columns=header)
    return df.replace("", pd.NA)


# --- Đọc ------------------------------------------------------------------

def load_leads() -> pd.DataFrame:
    df = _read_sheet(config.SHEET_ID_NHAP_LIEU, config.TAB_LEAD).dropna(how="all")
    schema.validate_headers(df, schema.LEAD_REQUIRED, "lead (Google Sheets)")
    df = schema.rename_status_columns(df)
    for c in schema.LEAD_OPTIONAL:      # file cũ thiếu cột nào thì tạo rỗng
        if c not in df.columns:
            df[c] = pd.NA
    df["Phone_Clean"] = df["SỐ ĐT"].apply(clean_phone)
    df["Loại SĐT"] = df["SỐ ĐT"].apply(phone_kind)
    df["Ngày Lead"] = parse_lead_dates(df["NGÀY"], config.LEAD_DATE_DEFAULT)
    return df


def load_appointments(df_lead: pd.DataFrame) -> pd.DataFrame:
    """Hẹn lấy từ chính cột NGÀY HẸN của lead.

    Khác bản local: không còn file ĐĂT HẸN riêng, vì file đó chỉ là tập con của
    lead (98,6% SĐT hẹn đã có trong lead) và bản gửi thêm còn trùng byte với
    bản cũ. Sales nhập một chỗ duy nhất.
    """
    hen = df_lead.loc[
        df_lead["NGÀY HẸN"].notna(), ["SỐ ĐT", "NGÀY HẸN", "Ngày Lead"]].copy()
    hen["Phone_Clean"] = hen["SỐ ĐT"].apply(clean_phone)
    # Truyền ngày lead để suy năm cho ô ghi thiếu năm. Sheet mới đã ép
    # dd/MM/yyyy nên chỉ dữ liệu cũ mới cần, nhưng để đây cho an toàn.
    hen["NGÀY HẸN"] = [parse_date_vn(v, moc)
                       for v, moc in zip(hen["NGÀY HẸN"], hen["Ngày Lead"])]
    hen = hen.dropna(subset=["Phone_Clean"])
    hen = (hen.sort_values(["Phone_Clean", "NGÀY HẸN"], na_position="last")
              .drop_duplicates("Phone_Clean", keep="first"))
    return hen[["Phone_Clean", "NGÀY HẸN"]]


def load_invoices() -> pd.DataFrame:
    """Hóa đơn từ kho INVOICES_RAW (Apps Script nạp vào, chỉ thêm không ghi đè)."""
    df = _read_sheet(config.SHEET_ID_KHO, config.TAB_INVOICES).dropna(how="all")
    schema.validate_headers(df, schema.INVOICE_REQUIRED, "hóa đơn (kho)")

    df["Phone_Clean"] = df["Điện thoại"].apply(clean_phone)
    df["Ngày HĐ"] = df["Thời gian"].apply(parse_date_vn)
    df["_tổng_hóa_đơn"] = df["Khách cần trả"].apply(clean_money)

    # 'Khách cần trả' là TỔNG hóa đơn lặp trên từng dòng mặt hàng -> chỉ giữ
    # tiền ở dòng đầu mỗi hóa đơn, nếu không SUM sẽ nhân đôi.
    df = df.sort_values(["Mã hóa đơn", "Mã hàng"], na_position="last").reset_index(drop=True)
    is_first_line = ~df.duplicated("Mã hóa đơn", keep="first")
    df["Doanh Thu (VNĐ)"] = df["_tổng_hóa_đơn"].where(is_first_line, 0)
    return df.drop(columns=["_tổng_hóa_đơn"])


def load_pancake() -> pd.DataFrame:
    """SĐT Pancake quét được từ hội thoại — dùng vá lead thiếu số.

    Sheet có thể chưa tồn tại (chưa cấu hình xong Pancake) -> trả bảng rỗng
    thay vì làm hỏng cả pipeline.
    """
    try:
        df = _read_sheet(config.SHEET_ID_KHO, config.TAB_PANCAKE).dropna(how="all")
    except Exception:
        return pd.DataFrame(columns=["Phone_Clean", "Tên khách"])
    if df.empty or "SĐT" not in df.columns:
        return pd.DataFrame(columns=["Phone_Clean", "Tên khách"])
    df["Phone_Clean"] = df["SĐT"].apply(clean_phone)
    return df.dropna(subset=["Phone_Clean"]).drop_duplicates("Phone_Clean")


# --- Ghi ------------------------------------------------------------------

def write_table(name: str, df: pd.DataFrame, spreadsheet_id: str | None = None,
                values: list[list] | None = None) -> None:
    """Ghi đè một tab. Tự tạo tab nếu chưa có.

    ``values`` cho phép truyền sẵn mảng ô đã ép kiểu — ``write_all`` dùng để ép
    TOÀN BỘ bảng trước khi gọi API (xem lý do ở đó).
    """
    import gspread

    sh = _client().open_by_key(spreadsheet_id or config.SHEET_ID_DASHBOARD)
    try:
        ws = sh.worksheet(name)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=max(len(df) + 10, 100),
                              cols=max(len(df.columns), 10))

    if df.empty:
        ws.update([["(không có dữ liệu)"]], "A1", value_input_option="RAW")
        return

    ws.resize(rows=len(df) + 1, cols=len(df.columns))
    _set_text_columns(ws, df)

    rows = [list(df.columns)] + (_to_cells(df) if values is None else values)
    for start in range(0, len(rows), BATCH_ROWS):
        chunk = rows[start:start + BATCH_ROWS]
        # value_input_option='RAW' để Sheets không diễn giải lại nội dung —
        # nếu để USER_ENTERED thì '9.420.000' thành 9.42 và '0389...' mất số 0.
        ws.update(chunk, f"A{start + 1}", value_input_option="RAW")


def _set_text_columns(ws, df: pd.DataFrame) -> None:
    """Đặt định dạng text cho cột định danh, giữ số 0 đầu của SĐT."""
    from gspread.utils import rowcol_to_a1

    for i, col in enumerate(df.columns, start=1):
        if col not in TEXT_COLUMNS:
            continue
        a1 = rowcol_to_a1(1, i)[:-1]  # bỏ số hàng, lấy chữ cái cột
        try:
            ws.format(f"{a1}:{a1}", {"numberFormat": {"type": "TEXT"}})
        except Exception:
            pass  # định dạng hỏng không đáng làm gãy cả job


def _o_json_duoc(v):
    """Ép một giá trị lẻ về kiểu ``requests`` gửi JSON được.

    gspread gói payload bằng ``json.dumps(..., allow_nan=False)``, nên bất kỳ
    kiểu nào ngoài str/bool/int/float đều ném ``TypeError`` — kể cả
    ``datetime.date``. Cột dtype ``object`` là chỗ lọt: ``marts.build_daily``
    tạo cột ``ngày`` bằng ``.dt.date``, pandas giữ nguyên dtype object nên vòng
    chuẩn hóa datetime64 phía dưới không đụng tới, và job chết ở FACT_DAILY.
    """
    if v is None:
        return None
    if isinstance(v, (bool, np.bool_)):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (pd.Timestamp, dt.datetime, dt.date)):
        return None if pd.isna(v) else v.strftime("%Y-%m-%d")  # bắt cả NaT
    if isinstance(v, dt.time):
        return v.strftime("%H:%M")
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return float(v) if math.isfinite(v) else None  # inf cũng không hợp lệ
    if isinstance(v, (str, int)):
        return v
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass  # list/array: pd.isna trả mảng, không so được -> để str() lo
    return str(v)


def _to_cells(df: pd.DataFrame) -> list[list]:
    """Chuyển DataFrame thành mảng ô Sheets nhận được.

    Ngày ghi dạng ISO (YYYY-MM-DD) vì Looker Studio đọc ổn định nhất, và không
    lẫn lộn ngày/tháng như dd/mm.
    """
    out = df.copy()
    for col in out.columns:
        s = out[col]
        if pd.api.types.is_datetime64_any_dtype(s):
            out[col] = s.dt.strftime("%Y-%m-%d")
        elif s.dtype == bool:
            out[col] = s.map({True: "TRUE", False: "FALSE"})
        elif pd.api.types.is_float_dtype(s):
            out[col] = s.replace([np.inf, -np.inf], np.nan)
        elif pd.api.types.is_integer_dtype(s):
            pass  # astype(object) ở cuối tự đổi np.int64 -> int
        else:
            # object, period, category, Decimal... — ép từng ô cho chắc. Danh
            # sách kiểu "lạ" chỉ dài thêm theo thời gian, chặn theo whitelist.
            out[col] = s.map(_o_json_duoc)
    return out.where(pd.notna(out), "").astype(object).values.tolist()


def write_all(tables: dict[str, pd.DataFrame]) -> None:
    # Ép kiểu TOÀN BỘ bảng trước khi gọi API. Trước đây một kiểu dữ liệu lạ ở
    # bảng thứ tư làm job chết giữa chừng: MASTER/DIM_KHACH/FUNNEL_MOI đã ghi
    # mới, FACT_DAILY/HIEU_QUA_KENH còn số cũ, mà DQ_STATUS vẫn báo 🟢 ĐẠT.
    # Dashboard sai lệch âm thầm — đúng cái kiểu hỏng đã làm mất T12/2025.
    payloads = {name: _to_cells(df) for name, df in tables.items()}
    for name, df in tables.items():
        write_table(name, df, values=payloads[name])
        print(f"  ghi {name}: {len(df):,} dòng")


def load_ad_costs() -> pd.DataFrame:
    """Chi phí quảng cáo từ tab CHI_PHÍ_QC. Tab chưa có thì trả bảng rỗng."""
    from . import ad_costs
    try:
        df = _read_sheet(config.SHEET_ID_NHAP_LIEU, config.TAB_CHIPHI).dropna(how="all")
    except Exception:
        return ad_costs.EMPTY.copy()
    return ad_costs.normalize(df)


def load_previous_dq() -> pd.DataFrame | None:
    """DQ_STATUS của lần chạy trước. Phải đọc TRƯỚC khi ghi đè bảng mới."""
    try:
        return _read_sheet(config.SHEET_ID_DASHBOARD, config.TAB_DQ)
    except Exception:
        return None
