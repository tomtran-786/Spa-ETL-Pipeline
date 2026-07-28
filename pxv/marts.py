"""Các bảng tổng hợp sẵn cho dashboard.

Vì sao phải tính ở đây thay vì để Looker Studio tự tính: bảng MASTER có mỗi
dòng là một cặp (SĐT × hóa đơn), nên một khách mua 5 lần chiếm 5 dòng. Trên
cấu trúc đó Looker tính AVG(CLV) sẽ chia cho mẫu số bị đếm 5 lần, và tỷ lệ
upsell thì cần so ngày mua đầu với các lần mua sau — Looker không làm được.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def build_dim_khach(master: pd.DataFrame, df_inv: pd.DataFrame,
                    window_start: pd.Timestamp | None = None) -> pd.DataFrame:
    """Một dòng = một khách hàng (một SĐT). Nền cho CLV và retention.

    Khách không có SĐT hợp lệ không vào bảng này — không có danh tính thì không
    thể nói về giá trị trọn đời của họ. Doanh thu của họ vẫn nằm ở MASTER.
    """
    window_start = window_start or config.WINDOW_START

    inv = df_inv.dropna(subset=["Phone_Clean"]).copy()
    inv = inv[inv["Doanh Thu (VNĐ)"] > 0]  # chỉ dòng đầu mỗi hóa đơn mang tiền

    agg = inv.groupby("Phone_Clean").agg(
        tổng_doanh_thu=("Doanh Thu (VNĐ)", "sum"),
        số_hóa_đơn=("Mã hóa đơn", "nunique"),
        ngày_mua_đầu=("Ngày HĐ", "min"),
        ngày_mua_cuối=("Ngày HĐ", "max"),
    ).reset_index()

    agg["số_ngày_gắn_bó"] = (agg["ngày_mua_cuối"] - agg["ngày_mua_đầu"]).dt.days
    agg["là_khách_quay_lại"] = agg["số_hóa_đơn"] > 1
    agg["mua_trước_cửa_sổ"] = agg["ngày_mua_đầu"] < window_start
    agg["cohort_tháng"] = agg["ngày_mua_đầu"].dt.to_period("M").astype(str)
    agg["giá_trị_đơn_TB"] = (agg["tổng_doanh_thu"] / agg["số_hóa_đơn"]).round(0)

    # Dịch vụ đầu tiên khách mua — để biết cửa ngõ nào dẫn khách vào.
    first_item = (inv.sort_values("Ngày HĐ")
                     .drop_duplicates("Phone_Clean", keep="first")
                     .set_index("Phone_Clean")["Tên hàng"])
    agg["dịch_vụ_đầu_tiên"] = agg["Phone_Clean"].map(first_item)
    agg["vào_bằng_dịch_vụ_mồi"] = (agg["dịch_vụ_đầu_tiên"].astype(str)
        .str.contains(config.FUNNEL_SERVICE_PATTERN, case=False, na=False))

    # Thuộc tính lead (kênh, nhóm MECE) lấy từ MASTER.
    lead_attrs = (master[master["SĐT Cuối"].notna()]
                  .drop_duplicates("SĐT Cuối", keep="first")
                  .set_index("SĐT Cuối")[["Kênh Tiếp Cận", "Phân nhóm MECE", "NGUỒN"]])
    agg = agg.join(lead_attrs, on="Phone_Clean")

    agg["phân_khúc_CLV"] = _tercile(agg["tổng_doanh_thu"])
    return agg.rename(columns={"Phone_Clean": "SĐT"}).sort_values(
        "tổng_doanh_thu", ascending=False).reset_index(drop=True)


def _tercile(s: pd.Series) -> pd.Series:
    """Chia khách thành 3 mức giá trị. Dùng rank để không vỡ khi nhiều giá trị trùng."""
    if s.empty:
        return pd.Series(dtype=object)
    ranked = s.rank(method="first", pct=True)
    return pd.cut(ranked, [0, 1 / 3, 2 / 3, 1.0],
                  labels=["Thấp", "Trung bình", "Cao"], include_lowest=True)


def build_funnel_moi(df_inv: pd.DataFrame,
                     window_start: pd.Timestamp | None = None) -> pd.DataFrame:
    """Một dòng = một khách từng mua dịch vụ mồi.

    Trả lời: khách vào bằng dịch vụ mồi có nâng cấp lên dịch vụ chính không,
    sau bao lâu, và mang về bao nhiêu tiền.
    """
    window_start = window_start or config.WINDOW_START
    inv = df_inv.dropna(subset=["Phone_Clean"]).copy()
    inv = inv[inv["Doanh Thu (VNĐ)"] > 0]
    inv["là_mồi"] = (inv["Tên hàng"].astype(str)
                     .str.contains(config.FUNNEL_SERVICE_PATTERN, case=False, na=False))

    moi = inv[inv["là_mồi"]]
    if moi.empty:
        return pd.DataFrame()

    first_moi = (moi.sort_values("Ngày HĐ")
                    .drop_duplicates("Phone_Clean", keep="first")
                    [["Phone_Clean", "Ngày HĐ", "Tên hàng", "Doanh Thu (VNĐ)"]]
                    .rename(columns={"Ngày HĐ": "ngày_mua_mồi",
                                     "Tên hàng": "dịch_vụ_mồi",
                                     "Doanh Thu (VNĐ)": "doanh_thu_mồi"}))

    rows = []
    non_moi = inv[~inv["là_mồi"]]
    by_phone = dict(tuple(non_moi.groupby("Phone_Clean")))

    for r in first_moi.itertuples(index=False):
        later = by_phone.get(r.Phone_Clean)
        rec = {
            "SĐT": r.Phone_Clean,
            "ngày_mua_mồi": r.ngày_mua_mồi,
            "dịch_vụ_mồi": r.dịch_vụ_mồi,
            "doanh_thu_mồi": r.doanh_thu_mồi,
        }
        if later is None or later.empty:
            after = later
        else:
            after = later[later["Ngày HĐ"] > r.ngày_mua_mồi]

        if after is None or after.empty:
            rec.update({f"upsell_{d}d": False for d in config.UPSELL_WINDOWS})
            rec.update({"doanh_thu_upsell": 0, "số_ngày_đến_upsell": np.nan,
                        "dịch_vụ_upsell_đầu": None})
        else:
            gap = (after["Ngày HĐ"] - r.ngày_mua_mồi).dt.days
            for d in config.UPSELL_WINDOWS:
                rec[f"upsell_{d}d"] = bool((gap <= d).any())
            rec["doanh_thu_upsell"] = int(after["Doanh Thu (VNĐ)"].sum())
            rec["số_ngày_đến_upsell"] = int(gap.min())
            rec["dịch_vụ_upsell_đầu"] = after.loc[after["Ngày HĐ"].idxmin(), "Tên hàng"]
        rows.append(rec)

    return pd.DataFrame(rows).sort_values("ngày_mua_mồi").reset_index(drop=True)


def build_daily(master: pd.DataFrame) -> pd.DataFrame:
    """Một dòng = một cặp (ngày × kênh). Cho biểu đồ chuỗi thời gian nhẹ."""
    lead_side = master[master["Ngày Lead"].notna()].copy()
    lead_side["ngày"] = lead_side["Ngày Lead"].dt.date
    leads = lead_side.groupby(["ngày", "Kênh Tiếp Cận"]).agg(
        lead=("[F] 1_Có Inbox", "sum"),
        có_sđt=("[F] 2_Có SĐT", "sum"),
        có_hẹn=("[F] 3_Có Đặt Lịch", "sum"),
        có_đơn=("[F] 4_Có Ra Đơn", "sum"),
    )

    inv_side = master[master["Ngày HĐ"].notna()].copy()
    inv_side["ngày"] = inv_side["Ngày HĐ"].dt.date
    sales = inv_side.groupby(["ngày", "Kênh Tiếp Cận"]).agg(
        doanh_thu=("Doanh Thu (VNĐ)", "sum"),
        số_hóa_đơn=("Mã hóa đơn", "nunique"),
    )

    out = leads.join(sales, how="outer").fillna(0).reset_index()
    for c in ["lead", "có_sđt", "có_hẹn", "có_đơn", "doanh_thu", "số_hóa_đơn"]:
        out[c] = out[c].astype(int)
    return out.sort_values(["ngày", "Kênh Tiếp Cận"]).reset_index(drop=True)
