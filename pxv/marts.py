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


def build_hieu_qua_kenh(master: pd.DataFrame, costs: pd.DataFrame,
                        dim_khach: pd.DataFrame | None = None) -> pd.DataFrame:
    """Một dòng = một cặp (tháng × kênh). Trả lời "kênh nào ĐÁNG tiền".

    Quy kết theo COHORT LEAD, không theo tháng phát sinh hóa đơn: tiền chi
    tháng 1 mà khách chốt tháng 2 vẫn tính về tháng 1. Đây mới là câu
    marketing cần — "bỏ ra X đồng tháng này thì thu về bao nhiêu".

    LƯU Ý KHI ĐỌC SỐ: chỉ quy kết được doanh thu của khách CÓ HỒ SƠ LEAD.
    Khoảng 75% doanh thu đến từ khách vãng lai không rõ nguồn, nên ROAS ở đây
    là cận dưới — đừng dùng nó làm mẫu số cho toàn bộ doanh thu.
    """
    lead_side = master[master["Ngày Lead"].notna()].copy()
    if lead_side.empty:
        return pd.DataFrame()

    lead_side["tháng"] = lead_side["Ngày Lead"].dt.strftime("%Y-%m")
    agg = lead_side.groupby(["tháng", "Kênh Tiếp Cận"]).agg(
        lead=("[F] 1_Có Inbox", "sum"),
        có_sđt=("[F] 2_Có SĐT", "sum"),
        có_hẹn=("[F] 3_Có Đặt Lịch", "sum"),
        khách_mua=("[F] 4_Có Ra Đơn", "sum"),
        doanh_thu=("Doanh Thu (VNĐ)", "sum"),
    ).reset_index().rename(columns={"Kênh Tiếp Cận": "kênh"})

    chi_phi = (costs.groupby(["tháng", "kênh"])["chi phí"].sum().reset_index()
               if not costs.empty else
               pd.DataFrame(columns=["tháng", "kênh", "chi phí"]))
    out = agg.merge(chi_phi, on=["tháng", "kênh"], how="left")
    # to_numeric trước khi fillna: merge với bảng rỗng cho ra cột object dtype,
    # fillna thẳng sẽ dính FutureWarning và vỡ ở pandas bản sau.
    out["chi phí"] = pd.to_numeric(out["chi phí"], errors="coerce").fillna(0).astype(int)

    có_chi_phí = out["chi phí"] > 0
    out["CPL"] = _chia(out["chi phí"], out["lead"], có_chi_phí)
    out["CAC"] = _chia(out["chi phí"], out["khách_mua"], có_chi_phí)
    out["ROAS"] = _chia(out["doanh_thu"], out["chi phí"], có_chi_phí, ndigits=2)
    out["tỷ_lệ_chốt_%"] = _chia(out["khách_mua"] * 100, out["lead"],
                                pd.Series(True, index=out.index), ndigits=2)

    if dim_khach is not None and not dim_khach.empty:
        # CLV lấy từ TOÀN BỘ lịch sử mua (kể cả trước cửa sổ), khác doanh thu
        # trong kỳ ở trên. Nhờ vậy CLV:CAC nói lên điều khác với ROAS.
        clv = (dim_khach.groupby("Kênh Tiếp Cận")["tổng_doanh_thu"].mean()
               .round(0).rename("CLV_TB_kênh"))
        out = out.join(clv, on="kênh")
        out["CLV_trên_CAC"] = _chia(out["CLV_TB_kênh"], out["CAC"],
                                    có_chi_phí, ndigits=2)

    return out.sort_values(["tháng", "doanh_thu"], ascending=[True, False]) \
              .reset_index(drop=True)


def _chia(tu: pd.Series, mau: pd.Series, dieu_kien: pd.Series, ndigits: int = 0):
    """Chia an toàn: mẫu số 0 hoặc không đủ điều kiện thì trả NaN, không trả 0.

    Trả 0 sẽ khiến biểu đồ hiểu nhầm là "hiệu quả bằng 0" thay vì "chưa có
    dữ liệu để tính".
    """
    import numpy as np

    kq = np.where((mau > 0) & dieu_kien, tu / mau.replace(0, np.nan), np.nan)
    return pd.Series(kq, index=tu.index).round(ndigits)
