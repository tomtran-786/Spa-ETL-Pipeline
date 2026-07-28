"""Đọc và chuẩn hóa bảng chi phí quảng cáo.

Không có bảng này thì dashboard chỉ trả lời được "kênh nào ra NHIỀU lead",
không trả lời được "kênh nào HIỆU QUẢ". Một kênh mang 200 lead tốn 50 triệu
kém hơn kênh mang 80 lead tốn 5 triệu, mà nhìn số lượng thì tưởng ngược lại.

Marketing nhập ~10 dòng mỗi tháng, 4 cột:
    tháng | kênh | mã bài QC | chi phí
"""
from __future__ import annotations

import re

import pandas as pd

from .clean import clean_money, normalize_text

COLUMNS = ["tháng", "kênh", "mã bài QC", "chi phí"]
EMPTY = pd.DataFrame(columns=["tháng", "kênh", "mã bài QC", "chi phí"])


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa bảng thô thành dạng dùng được. Bảng rỗng cũng hợp lệ."""
    if df is None or df.empty:
        return EMPTY.copy()

    missing = [c for c in ("tháng", "kênh", "chi phí") if c not in df.columns]
    if missing:
        raise ValueError(
            f"Bảng {COLUMNS} thiếu cột {missing}. Cột đang có: {list(df.columns)}"
        )

    out = df.copy()
    out["tháng"] = out["tháng"].apply(parse_thang)
    out["kênh"] = out["kênh"].apply(
        lambda v: str(v).strip() if pd.notna(v) else None)
    out["chi phí"] = out["chi phí"].apply(clean_money)
    out["mã bài QC"] = (out["mã bài QC"].fillna("")
                        if "mã bài QC" in out.columns else "")

    out = out.dropna(subset=["tháng", "kênh"])
    out = out[out["chi phí"] > 0]
    return out[COLUMNS].reset_index(drop=True)


def parse_thang(value) -> str | None:
    """Nhận '2026-01', '01/2026', '1/2026', hoặc ngày bất kỳ -> 'YYYY-MM'.

    Cố tình chấp nhận nhiều kiểu vì marketing gõ tay, không nên bắt họ nhớ
    đúng một định dạng rồi im lặng bỏ qua dòng gõ khác kiểu.
    """
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None

    m = re.match(r"^(\d{4})[-/](\d{1,2})$", text)          # 2026-01
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    m = re.match(r"^(\d{1,2})[-/](\d{4})$", text)          # 01/2026
    if m:
        return f"{m.group(2)}-{int(m.group(1)):02d}"

    d = pd.to_datetime(text, dayfirst=True, errors="coerce")
    return None if pd.isna(d) else f"{d.year}-{d.month:02d}"


def unknown_channels(costs: pd.DataFrame, known: set[str]) -> list[str]:
    """Kênh có chi phí nhưng không khớp kênh nào trong dữ liệu lead.

    Gõ sai tên kênh sẽ khiến chi phí đó biến mất khỏi mọi phép tính mà không
    ai biết — phải báo ra.
    """
    if costs.empty:
        return []
    known_norm = {normalize_text(k) for k in known}
    return sorted({
        k for k in costs["kênh"].unique()
        if normalize_text(k) not in known_norm
    })
