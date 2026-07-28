"""Kiểm chất lượng dữ liệu.

Nguyên tắc: GitHub Actions chỉ gửi mail khi job crash, nên pipeline phải chủ
động crash lúc dữ liệu sai. Lỗi im lặng chính là thứ đã làm mất trọn tháng
12/2025 mà không ai biết.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from . import config, mappings, transform
from .clean import PHONE_INVALID, out_of_window_mask

FAIL = "🔴 DỪNG"
WARN = "🟠 CẢNH BÁO"
OK = "🟢 ĐẠT"


@dataclass
class Check:
    tên: str
    trạng_thái: str
    giá_trị: str
    ghi_chú: str = ""


@dataclass
class QualityReport:
    checks: list[Check] = field(default_factory=list)
    cần_sửa: pd.DataFrame = field(default_factory=pd.DataFrame)

    def add(self, tên, trạng_thái, giá_trị, ghi_chú=""):
        self.checks.append(Check(tên, trạng_thái, str(giá_trị), ghi_chú))

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if c.trạng_thái == FAIL]

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([vars(c) for c in self.checks])

    def raise_if_failed(self) -> None:
        if self.failed:
            lines = [f"  - {c.tên}: {c.giá_trị} ({c.ghi_chú})" for c in self.failed]
            raise DataQualityError(
                "Dữ liệu không đạt, dừng pipeline:\n" + "\n".join(lines)
            )


class DataQualityError(RuntimeError):
    """Dữ liệu vi phạm ngưỡng nghiêm trọng — thà không có số còn hơn số sai."""


CHAY_LUC = "Chạy lúc"

# Hai mốc ghi lại mỗi lần chạy để lần sau đối chiếu. Không có chúng thì không
# cách nào phát hiện dữ liệu bị xóa bớt ở nguồn — mọi phép kiểm khác đều so
# nguồn với chính nó, nên xóa 500 dòng lead vẫn cho kết quả xanh.
MOC_SO_DONG_LEAD = "Số dòng lead"
MOC_DT_THANG_DONG = "Doanh thu tháng đã đóng"


def run_checks(df_lead: pd.DataFrame, df_inv: pd.DataFrame,
               master: pd.DataFrame,
               costs: pd.DataFrame | None = None,
               truoc: dict | None = None) -> QualityReport:
    rep = QualityReport()
    # Dòng đầu tiên là mốc thời gian: watchdog bên Apps Script đọc đúng dòng này
    # để biết pipeline có còn chạy không. Nếu GitHub Actions bị tắt thì GitHub
    # không báo gì cả — chỉ watchdog phát hiện được.
    rep.add(CHAY_LUC, OK, pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "mốc để watchdog kiểm pipeline còn sống")
    _check_dates(df_lead, rep)
    _check_phones(df_lead, rep)
    _check_invoice_months(df_inv, rep)
    _check_invoice_freshness(df_inv, rep)
    _check_invoice_preserved(df_inv, master, rep)
    _check_funnel_dedupe(master, rep)
    _check_mece_exhaustive(master, rep)
    _check_source_catalog(df_lead, rep)
    _check_ad_costs(costs, master, rep)
    _check_drift(df_lead, df_inv, rep, truoc)
    return rep


def doanh_thu_thang_da_dong(df_inv: pd.DataFrame) -> int:
    """Doanh thu các tháng ĐÃ KẾT THÚC. Tháng đang chạy còn tăng nên không tính.

    Con số này về nguyên tắc không bao giờ được đổi. Đổi tức là dữ liệu cũ bị
    sửa hoặc bị mất.
    """
    if df_inv.empty or "Ngày HĐ" not in df_inv:
        return 0
    dau_thang_nay = pd.Timestamp.now().normalize().replace(day=1)
    da_dong = df_inv[df_inv["Ngày HĐ"] < dau_thang_nay]
    return int(da_dong["Doanh Thu (VNĐ)"].sum())


def _check_drift(df_lead: pd.DataFrame, df_inv: pd.DataFrame,
                 rep: QualityReport, truoc: dict | None) -> None:
    """So với lần chạy trước: dữ liệu chỉ được thêm, không được mất.

    Đây là phép kiểm DUY NHẤT bắt được việc ai đó xóa dòng ở sheet nguồn. Các
    phép kiểm còn lại đều so nguồn với kết quả — cùng đến từ nguồn đã bị xóa
    nên hai vế vẫn bằng nhau và báo xanh.
    """
    nay_lead = len(df_lead)
    nay_dt = doanh_thu_thang_da_dong(df_inv)

    # Ghi mốc cho lần sau, dù lần này có so được hay không.
    rep.add(MOC_SO_DONG_LEAD, OK, nay_lead, "mốc để lần chạy sau đối chiếu")
    rep.add(MOC_DT_THANG_DONG, OK, nay_dt, "mốc để lần chạy sau đối chiếu")

    if not truoc:
        rep.add("Dữ liệu không bị mất", WARN, "chưa có mốc cũ",
                "lần chạy đầu tiên — từ lần sau sẽ đối chiếu được")
        return

    truoc_lead = truoc.get(MOC_SO_DONG_LEAD)
    if truoc_lead is not None:
        giam = truoc_lead - nay_lead
        rep.add("Số dòng lead không giảm", FAIL if giam > 0 else OK,
                f"{nay_lead} (lần trước {truoc_lead})",
                f"MẤT {giam} dòng — ai đó đã xóa ở sheet nguồn" if giam > 0 else "")

    truoc_dt = truoc.get(MOC_DT_THANG_DONG)
    if truoc_dt:
        lech = abs(nay_dt - truoc_dt) / truoc_dt
        rep.add("Doanh thu tháng đã đóng không đổi",
                FAIL if lech > config.CLOSED_MONTH_DRIFT else OK,
                f"{nay_dt:,} (lần trước {truoc_dt:,})",
                f"lệch {lech * 100:.2f}% — tháng đã đóng thì doanh thu không "
                f"được đổi, nghi mất hoặc sửa dữ liệu cũ"
                if lech > config.CLOSED_MONTH_DRIFT else "")


def doc_moc_cu(dq_truoc: pd.DataFrame | None) -> dict:
    """Rút 2 mốc từ bảng DQ_STATUS của lần chạy trước."""
    moc: dict = {}
    if dq_truoc is None or dq_truoc.empty or "tên" not in dq_truoc.columns:
        return moc
    for ten in (MOC_SO_DONG_LEAD, MOC_DT_THANG_DONG):
        hang = dq_truoc[dq_truoc["tên"] == ten]
        if hang.empty:
            continue
        try:
            moc[ten] = int(str(hang.iloc[0]["giá_trị"]).replace(",", "").strip())
        except (ValueError, TypeError):
            pass
    return moc


def _check_ad_costs(costs, master: pd.DataFrame, rep: QualityReport) -> None:
    """Chi phí quảng cáo có đủ và có khớp tên kênh không.

    Gõ sai tên kênh thì chi phí đó biến mất khỏi mọi phép tính mà không ai
    biết — CPL/CAC/ROAS của kênh sẽ trống trong khi tiền vẫn chi thật.
    """
    from . import ad_costs as ad

    if costs is None or costs.empty:
        rep.add("Chi phí quảng cáo", WARN, "chưa nhập",
                "chưa nhập thì không tính được CPL/CAC/ROAS — chỉ biết kênh nào "
                "ra NHIỀU lead, không biết kênh nào ĐÁNG tiền")
        return

    known = set(master["Kênh Tiếp Cận"].dropna().unique())
    unknown = ad.unknown_channels(costs, known)
    rep.add("Kênh trong bảng chi phí", WARN if unknown else OK,
            unknown or "khớp hết",
            f"chi phí của các kênh này sẽ không được tính: {unknown}" if unknown else "")

    # Tháng có lead nhưng chưa nhập chi phí -> ROAS tháng đó bị trống.
    có_lead = set(master.loc[master["Ngày Lead"].notna(), "Ngày Lead"]
                  .dt.strftime("%Y-%m").unique())
    thiếu = sorted(có_lead - set(costs["tháng"].unique()))
    rep.add("Tháng đã nhập chi phí", WARN if thiếu else OK,
            f"{len(có_lead) - len(thiếu)}/{len(có_lead)}",
            f"chưa nhập cho tháng: {thiếu}" if thiếu else "")


def _check_dates(df_lead: pd.DataFrame, rep: QualityReport) -> None:
    """Ngày parse được nhưng nằm ngoài khoảng hợp lệ -> nghi gõ nhầm năm.

    KHÔNG tự sửa. Code cũ ép 2025-Q1 thành 2026 để vá 35 dòng; sang 2027 quy
    tắc đó sẽ âm thầm bóp méo dữ liệu thật.
    """
    bad = out_of_window_mask(df_lead["Ngày Lead"], config.DATE_VALID_LO, config.DATE_VALID_HI)
    unparsed = df_lead["NGÀY"].notna() & df_lead["Ngày Lead"].isna()

    # Lead có ngày trước cửa sổ phân tích: không sai, nhưng nếu dồn vào đúng
    # một ngày thì nhiều khả năng là gõ nhầm năm hàng loạt -> phải báo.
    before = df_lead["Ngày Lead"].notna() & (df_lead["Ngày Lead"] < config.WINDOW_START)
    n_before = int(before.sum())
    if n_before:
        dates = df_lead.loc[before, "Ngày Lead"].dt.date
        top_date, top_n = dates.value_counts().index[0], dates.value_counts().iloc[0]
        note = (f"{top_n}/{n_before} dòng dồn vào {top_date} — kiểm tra xem có phải "
                f"gõ nhầm năm không, rồi sửa tại nguồn")
        rep.add("Lead trước cửa sổ phân tích", WARN, n_before, note)

    rep.add("Ngày ngoài khoảng hợp lệ", WARN if bad.any() else OK, int(bad.sum()),
            f"ngoài [{config.DATE_VALID_LO:%Y-%m-%d}, {config.DATE_VALID_HI:%Y-%m-%d}]")
    rep.add("Ngày không đọc được", WARN if unparsed.any() else OK, int(unparsed.sum()))

    flagged = df_lead[bad | unparsed | before]
    if not flagged.empty:
        rep.cần_sửa = flagged[["NGÀY", "TÊN KHÁCH HÀNG", "SỐ ĐT"]].assign(
            lý_do="ngày nghi sai")


def _check_phones(df_lead: pd.DataFrame, rep: QualityReport) -> None:
    kinds = df_lead["Loại SĐT"].value_counts()
    n_invalid = int(kinds.get(PHONE_INVALID, 0))
    total = len(df_lead)
    có_sđt = int(total - kinds.get("empty", 0) - n_invalid)
    tỷ_lệ = có_sđt / total * 100 if total else 0

    rep.add("SĐT không đọc được", WARN if n_invalid else OK, n_invalid,
            "sales gõ ghi chú vào ô SĐT hoặc số quá ngắn")
    rep.add("% lead có SĐT dùng được", OK, f"{tỷ_lệ:.1f}%",
            f"{có_sđt}/{total} — chỉ số này là bước [F]2 của phễu")


def _check_invoice_months(df_inv: pd.DataFrame, rep: QualityReport) -> None:
    """Tháng nào nằm giữa khoảng dữ liệu mà không có hóa đơn nào -> thiếu data."""
    dates = df_inv["Ngày HĐ"].dropna()
    if dates.empty:
        rep.add("Thủng tháng hóa đơn", FAIL, "không có hóa đơn nào")
        return
    có = set(dates.dt.to_period("M").astype(str))
    đủ = set(pd.period_range(dates.min(), dates.max(), freq="M").astype(str))
    thiếu = sorted(đủ - có - set(config.KNOWN_DATA_GAPS))
    biết_rồi = sorted((đủ - có) & set(config.KNOWN_DATA_GAPS))

    rep.add("Thủng tháng hóa đơn", FAIL if thiếu else OK, thiếu or "không",
            f"đã biết và bỏ qua: {biết_rồi}" if biết_rồi else "")


def _check_invoice_freshness(df_inv: pd.DataFrame, rep: QualityReport) -> None:
    latest = df_inv["Ngày HĐ"].max()
    if pd.isna(latest):
        return
    tuổi = (pd.Timestamp.now().normalize() - latest.normalize()).days
    rep.add("Độ tươi hóa đơn", WARN if tuổi > config.MAX_INVOICE_AGE_DAYS else OK,
            f"{tuổi} ngày", f"hóa đơn mới nhất {latest:%d/%m/%Y}")


def _check_invoice_preserved(df_inv: pd.DataFrame, master: pd.DataFrame,
                             rep: QualityReport) -> None:
    """Không được rớt hóa đơn nào khi merge — đây là bảo toàn doanh thu."""
    nguồn = df_inv[df_inv["Ngày HĐ"] >= config.WINDOW_START]["Mã hóa đơn"].nunique()
    sau = master["Mã hóa đơn"].nunique()
    rep.add("Bảo toàn hóa đơn", OK if nguồn == sau else FAIL, f"{sau}/{nguồn}",
            "" if nguồn == sau else f"rớt {nguồn - sau} hóa đơn khi merge")

    dt_nguồn = int(df_inv[df_inv["Ngày HĐ"] >= config.WINDOW_START]["Doanh Thu (VNĐ)"].sum())
    dt_sau = int(master["Doanh Thu (VNĐ)"].sum())
    rep.add("Bảo toàn doanh thu", OK if dt_nguồn == dt_sau else FAIL,
            f"{dt_sau:,}", "" if dt_nguồn == dt_sau else f"nguồn có {dt_nguồn:,}")


def _check_funnel_dedupe(master: pd.DataFrame, rep: QualityReport) -> None:
    """Mỗi SĐT chỉ được đếm 1 lần ở mỗi bước phễu."""
    có_sđt = master[master["SĐT Cuối"].notna()]
    lỗi = []
    for flag in transform.FUNNEL_FLAGS:
        mx = có_sđt.groupby("SĐT Cuối")[flag].sum().max()
        if pd.notna(mx) and mx > 1:
            lỗi.append(f"{flag}={int(mx)}")
    rep.add("Chống đếm trùng phễu", FAIL if lỗi else OK, lỗi or "max 1/SĐT")

    # Phễu phải thu hẹp dần, không được nở ra ở bước sau.
    vals = [int(master[f].sum()) for f in transform.FUNNEL_FLAGS]
    nở = [transform.FUNNEL_FLAGS[i] for i in range(1, len(vals)) if vals[i] > vals[i - 1]]
    rep.add("Phễu thu hẹp dần", FAIL if nở else OK, " → ".join(map(str, vals)),
            f"bước nở ra: {nở}" if nở else "")


def _check_mece_exhaustive(master: pd.DataFrame, rep: QualityReport) -> None:
    n = int(master["Phân nhóm MECE"].eq(transform.MECE_UNKNOWN).sum())
    rep.add("MECE vét cạn", FAIL if n else OK, n,
            "có dòng rơi vào nhóm 'Khác' — logic phân nhóm bị hở" if n else "")


def _check_source_catalog(df_lead: pd.DataFrame, rep: QualityReport) -> None:
    from .clean import normalize_text

    nguồn = df_lead["NGUỒN"].dropna()
    if nguồn.empty:
        return
    trong_dm = nguồn.apply(lambda v: normalize_text(v) in mappings.SOURCE_ALIASES)
    tỷ_lệ = trong_dm.mean()
    lạ = sorted(set(nguồn[~trong_dm]))[:5]
    rep.add("NGUỒN nằm trong danh mục",
            OK if tỷ_lệ >= config.MIN_SOURCE_IN_CATALOG else WARN,
            f"{tỷ_lệ * 100:.1f}%", f"giá trị lạ: {lạ}" if lạ else "")
