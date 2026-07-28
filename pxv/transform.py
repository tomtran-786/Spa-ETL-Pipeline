"""Gộp 3 nguồn thành bảng MASTER: phân nhóm MECE, cờ funnel, chỉ số phái sinh."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, mappings

MECE_NO_PHONE = "Nhóm 0: Lead chưa có SĐT"
MECE_WALKIN = "Nhóm 1: Vãng lai (chỉ có HĐ)"
MECE_NO_APPT = "Nhóm 2: Lead chưa hẹn & chưa chốt"
MECE_DIRECT = "Nhóm 3: Chốt thẳng không cần hẹn"
MECE_DROPPED = "Nhóm 4: Đặt hẹn nhưng rớt"
MECE_PERFECT = "Nhóm 5: Lead hoàn hảo (đủ 3 bước)"
MECE_ORPHAN_APPT = "Nhóm 6: Hẹn thiếu hồ sơ lead (lỗi data)"
MECE_UNKNOWN = "Khác"

FUNNEL_FLAGS = [
    "[F] 1_Có Inbox",
    "[F] 2_Có SĐT",
    "[F] 3_Có Đặt Lịch",
    "[F] 4_Có Ra Đơn",
]
_DEDUPED_FLAGS = FUNNEL_FLAGS + ["[Vãng lai] Có Ra Đơn", "Số lượng Lead tính"]

LEAD_ATTRS = [
    "Phone_Clean", "Ngày Lead", "TÊN KHÁCH HÀNG", "LOẠI TIN NHẮN", "NHÓM SP",
    "CHATPAGE", "NGUỒN", "QUAN TÂM", "TÌNH TRẠNG", "TRẠNG THÁI",
    "TƯ VẤN - SALE", "BÀI QC", "Loại SĐT",
]
INVOICE_ATTRS = [
    "Phone_Clean", "Mã hóa đơn", "Mã khách hàng", "Tên hàng", "Ngày HĐ",
    "Doanh Thu (VNĐ)",
]


def classify_mece(has_lead: bool, has_appt: bool, has_invoice: bool) -> str:
    """Vét cạn 8 tổ hợp của (Lead, Hẹn, Hóa đơn).

    Code cũ đặt nhánh 'hẹn mồ côi' ở CUỐI nên nó nuốt luôn tổ hợp
    (không lead + có hẹn + CÓ hóa đơn) vào Nhóm 4 — khiến nhóm "đặt hẹn nhưng
    rớt" lại có doanh thu, mâu thuẫn với chính định nghĩa của nó.
    """
    if has_lead:
        if has_appt:
            return MECE_PERFECT if has_invoice else MECE_DROPPED
        return MECE_DIRECT if has_invoice else MECE_NO_APPT
    if has_appt:
        return MECE_ORPHAN_APPT
    return MECE_WALKIN if has_invoice else MECE_UNKNOWN


def build_master(df_lead: pd.DataFrame, df_hen: pd.DataFrame, df_inv: pd.DataFrame,
                 window_start: pd.Timestamp | None = None) -> pd.DataFrame:
    window_start = window_start or config.WINDOW_START

    lead = df_lead[df_lead["Ngày Lead"] >= window_start].copy()
    lead = lead[[c for c in LEAD_ATTRS if c in lead.columns]]

    # Lead chưa có SĐT: giữ từng dòng (mỗi lần inbox = 1 lead).
    lead_no_phone = lead[lead["Phone_Clean"].isna()].copy()
    # Lead có SĐT: gộp về 1 dòng/khách, lấy lần inbox sớm nhất.
    lead_phone = (lead.dropna(subset=["Phone_Clean"])
                      .sort_values("Ngày Lead")
                      .drop_duplicates("Phone_Clean", keep="first"))
    lead_phone["In_Lead"] = True

    hen = df_hen.copy()
    hen["In_Hen"] = True

    # Hóa đơn trong cửa sổ đi vào funnel; hóa đơn trước đó chỉ dùng để biết ai
    # là khách đã mua từ trước (phục vụ CLV / phân biệt khách mới - khách cũ).
    inv_window_all = df_inv[df_inv["Ngày HĐ"] >= window_start][INVOICE_ATTRS]
    prior_buyers = set(
        df_inv[(df_inv["Ngày HĐ"] < window_start) & df_inv["Phone_Clean"].notna()]["Phone_Clean"]
    )

    # Hóa đơn KHÔNG có SĐT hợp lệ (KiotViet ghi "0", hoặc số quá ngắn) vẫn phải
    # được tính doanh thu, chỉ là không join được với lead. Tách ra xử lý riêng
    # vì hai lý do:
    #   1. Bỏ đi sẽ mất doanh thu thật (81tr trong cửa sổ T1-T2/2026).
    #   2. Gộp chung sẽ sai: pandas coi mọi NaN là TRÙNG NHAU khi duplicated(),
    #      nên các hóa đơn không SĐT sẽ bị khử trùng thành một. Code cũ còn tệ
    #      hơn — nó biến "0" thành SĐT hợp lệ nên hàng chục khách khác nhau bị
    #      gộp làm một người, bóp méo CLV và số khách unique.
    inv_window = inv_window_all[inv_window_all["Phone_Clean"].notna()]
    inv_orphan = inv_window_all[inv_window_all["Phone_Clean"].isna()]

    m = lead_phone.merge(inv_window, on="Phone_Clean", how="outer")
    m = m.merge(hen, on="Phone_Clean", how="outer")

    m["Phân nhóm MECE"] = [
        classify_mece(l is True, h is True, pd.notna(i))
        for l, h, i in zip(m["In_Lead"], m["In_Hen"], m["Mã hóa đơn"])
    ]
    m = _enrich(m)
    m = _add_funnel_flags(m)

    m["Thời gian ra đơn (Ngày)"] = (
        (m["Ngày HĐ"] - m["Ngày Lead"]).dt.total_seconds() / 86400
    ).round(1)
    m.loc[m["Thời gian ra đơn (Ngày)"] < 0, "Thời gian ra đơn (Ngày)"] = 0
    m["Khách mua trước cửa sổ"] = m["Phone_Clean"].isin(prior_buyers)
    m["SĐT Cuối"] = m["Phone_Clean"]

    master = pd.concat(
        [m, _prepare_no_phone(lead_no_phone), _prepare_orphan_invoices(inv_orphan)],
        ignore_index=True,
    )
    master = master.drop(columns=[c for c in ("In_Lead", "In_Hen", "Phone_Clean")
                                  if c in master.columns])
    ordered = [c for c in _MASTER_ORDER if c in master.columns]
    return master[ordered + [c for c in master.columns if c not in ordered]]


def _enrich(m: pd.DataFrame) -> pd.DataFrame:
    is_walkin = m["Phân nhóm MECE"].eq(MECE_WALKIN)
    m["Kênh Tiếp Cận"] = [
        mappings.classify_channel(cp, ng, w)
        for cp, ng, w in zip(m["CHATPAGE"], m["NGUỒN"], is_walkin)
    ]
    m["NHÓM SP_Clean"] = [
        mappings.classify_product_group(g, t)
        for g, t in zip(m["NHÓM SP"], m["Tên hàng"])
    ]
    m["Phân loại sản phẩm"] = [
        mappings.classify_product(t, q) for t, q in zip(m["Tên hàng"], m["QUAN TÂM"])
    ]
    m["[Dịch vụ mồi]"] = (m["Tên hàng"].astype(str)
                          .str.contains(config.FUNNEL_SERVICE_PATTERN,
                                        case=False, na=False))
    return m


def _add_funnel_flags(m: pd.DataFrame) -> pd.DataFrame:
    """Cờ funnel, mỗi SĐT chỉ đếm một lần.

    Phễu chỉ tính trên khách TỪNG INBOX. Khách vãng lai chưa từng nhắn tin nên
    không thuộc phễu marketing — để chung sẽ làm F4 phình to hơn F3, tức phễu
    nở ra ở bước sau, vô lý. Doanh thu vãng lai đếm riêng ở cột dành cho nó.
    """
    m = m.sort_values(["Phone_Clean", "Ngày HĐ"], na_position="first")
    is_first_row = ~m.duplicated("Phone_Clean", keep="first")
    is_lead = m["In_Lead"] == True  # noqa: E712 — cột có NaN, `is True` không vector hóa được
    has_invoice = m["Mã hóa đơn"].notna()

    m["[F] 1_Có Inbox"] = np.where(is_lead, 1, 0)
    m["[F] 2_Có SĐT"] = np.where(is_lead & m["Phone_Clean"].notna(), 1, 0)
    m["[F] 3_Có Đặt Lịch"] = np.where(is_lead & (m["In_Hen"] == True), 1, 0)  # noqa: E712
    m["[F] 4_Có Ra Đơn"] = np.where(is_lead & has_invoice, 1, 0)
    m["[Vãng lai] Có Ra Đơn"] = np.where(~is_lead & has_invoice, 1, 0)
    m["Số lượng Lead tính"] = 1
    m.loc[~is_first_row, _DEDUPED_FLAGS] = 0
    return m


def _prepare_no_phone(lead_no_phone: pd.DataFrame) -> pd.DataFrame:
    df = lead_no_phone.assign(**{
        "Phân nhóm MECE": MECE_NO_PHONE,
        "[F] 1_Có Inbox": 1, "[F] 2_Có SĐT": 0,
        "[F] 3_Có Đặt Lịch": 0, "[F] 4_Có Ra Đơn": 0,
        "[Vãng lai] Có Ra Đơn": 0, "Số lượng Lead tính": 1,
        "Doanh Thu (VNĐ)": 0, "[Dịch vụ mồi]": False,
        "Khách mua trước cửa sổ": False,
    })
    df["Kênh Tiếp Cận"] = [
        mappings.classify_channel(cp, ng) for cp, ng in zip(df["CHATPAGE"], df["NGUỒN"])
    ]
    df["NHÓM SP_Clean"] = [mappings.classify_product_group(g, None) for g in df["NHÓM SP"]]
    df["Phân loại sản phẩm"] = [mappings.classify_product(None, q) for q in df["QUAN TÂM"]]
    return df


def _prepare_orphan_invoices(inv_orphan: pd.DataFrame) -> pd.DataFrame:
    """Hóa đơn không có SĐT hợp lệ: tính doanh thu, xếp vãng lai, không join.

    Mỗi hóa đơn là một khách riêng biệt — không được khử trùng theo SĐT vì
    SĐT rỗng không phải là danh tính chung.
    """
    if inv_orphan.empty:
        return inv_orphan
    df = inv_orphan.copy()
    is_first_line = ~df.duplicated("Mã hóa đơn", keep="first")
    df = df.assign(**{
        "Phân nhóm MECE": MECE_WALKIN,
        "Kênh Tiếp Cận": mappings.CHANNEL_WALKIN,
        "[F] 1_Có Inbox": 0, "[F] 2_Có SĐT": 0,
        "[F] 3_Có Đặt Lịch": 0, "[F] 4_Có Ra Đơn": 0,
        "Số lượng Lead tính": 0,
        "Khách mua trước cửa sổ": False,
        "Loại SĐT": "empty",
    })
    df["[Vãng lai] Có Ra Đơn"] = np.where(is_first_line, 1, 0)
    df["NHÓM SP_Clean"] = [mappings.classify_product_group(None, t) for t in df["Tên hàng"]]
    df["Phân loại sản phẩm"] = [mappings.classify_product(t, None) for t in df["Tên hàng"]]
    df["[Dịch vụ mồi]"] = (df["Tên hàng"].astype(str)
                           .str.contains(config.FUNNEL_SERVICE_PATTERN, case=False, na=False))
    return df.drop(columns=["Phone_Clean"])


_MASTER_ORDER = [
    "SĐT Cuối", "Ngày Lead", "Ngày HĐ", "NGÀY HẸN", "Phân nhóm MECE",
    "Kênh Tiếp Cận", "Doanh Thu (VNĐ)", "Số lượng Lead tính",
    "Thời gian ra đơn (Ngày)",
]
