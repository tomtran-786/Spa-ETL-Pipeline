"""Chuyển file lead CSV cũ sang đúng định dạng sheet LEAD mới.

    python scripts/migrate_lead_csv.py "Sales_Marketing dataset - SALE T1-2-3_2026.csv"

Ghi ra CSV để bạn XEM TRƯỚC rồi tự dán vào sheet, cố tình không ghi thẳng qua
API: sai thì chỉ việc bỏ file đi, không phải dọn sheet.

VÌ SAO CẦN: file cũ 23 cột, sheet mới 17 cột, chỉ 12 cột trùng tên và thứ tự
khác nhau. Dán thẳng thì schema.validate_headers() chặn ngay.

Riêng vùng cột trạng thái bị lệch khi export: sinh ra ba cột cùng tên
'TRẠNG THÁI', pandas đánh số .1/.2. Đối chiếu nội dung cho thấy:

    TRẠNG THÁI      0 dòng      -> cột thừa, bỏ
    TRẠNG THÁI.1    2 dòng      -> cột TRẠNG THÁI thật
    TRẠNG THÁI.2    1.280 dòng  -> chứa TÊN NHÂN VIÊN, tức cột TƯ VẤN - SALE
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pxv import schema                                    # noqa: E402
from pxv.clean import clean_phone, parse_date_vn, phone_kind  # noqa: E402

# Cột sheet mới -> cột file cũ. None nghĩa là để trống.
ANH_XA = {
    "NGÀY": "NGÀY",
    "TÊN KHÁCH HÀNG": "TÊN KHÁCH HÀNG",
    "SỐ ĐT": "SỐ ĐT",
    "LÝ DO CHƯA CÓ SĐT": None,      # cột mới, sales điền từ giờ trở đi
    "LOẠI TIN NHẮN": "LOẠI TIN NHẮN",
    "NHÓM SP": "NHÓM SP",
    "CHATPAGE": "CHATPAGE",
    "NGUỒN": "NGUỒN",
    "BÀI QC": "BÀI QC",
    "QUAN TÂM": "QUAN TÂM",
    "TÌNH TRẠNG": "TÌNH TRẠNG",
    "TRẠNG THÁI": "TRẠNG THÁI.1",
    "TƯ VẤN - SALE": "TRẠNG THÁI.2",
    "THÔNG TIN KHÁCH": "THÔNG TIN KHÁCH",
    "GIỜ HẸN": "GIỜ HẸN",
    "NGÀY HẸN": "NGÀY HẸN",
    "GHI CHÚ": None,                # gộp từ nhiều cột lẻ, xem GOP_VAO_GHI_CHU
}

# Cột gần như rỗng nhưng vẫn là dữ liệu thật -> gộp vào GHI CHÚ kèm nhãn.
GOP_VAO_GHI_CHU = [
    "GHI CHÚ CHI TIẾT",
    "CHỐT/RỚT/HỦY LỊCH",
    "DỊCH VỤ/KHÓA HỌC MUA",
    "TÊN CHUYÊN GIA\nTƯ VẤN",
]

# Cột bỏ hẳn, kèm lý do để người sau không tưởng là sót.
BO_HAN = {
    "Cột 1": "cột đánh dấu của Sheets, không mang thông tin",
    "TRẠNG THÁI": "rỗng hoàn toàn (0 dòng) — cột thừa do export lệch",
    "LÝ DO KHÔNG CHỐT SALE": "rỗng hoàn toàn (0 dòng)",
    # Doanh thu là của KiotViet. Có con số doanh thu thứ hai nằm cạnh lead là
    # mời người ta dùng nhầm, mà pipeline không có cách nào phát hiện.
    "DOANH THU": "doanh thu chỉ lấy từ KiotViet, không để bản sao cạnh lead",
}


def main(nguon: Path, dich: Path) -> int:
    cu = pd.read_csv(nguon, dtype=str)
    print(f"Đọc {nguon.name}: {len(cu):,} dòng × {len(cu.columns)} cột\n")

    thieu = [c for c in ANH_XA.values() if c and c not in cu.columns]
    if thieu:
        print(f"❌ File nguồn thiếu cột: {thieu}")
        print("   Có thể file được export khác lần trước. Kiểm tra lại header.")
        return 1

    moi = pd.DataFrame(index=cu.index)
    for cot_moi, cot_cu in ANH_XA.items():
        moi[cot_moi] = cu[cot_cu] if cot_cu else pd.NA

    moi["GHI CHÚ"] = _gop_ghi_chu(cu)
    moi["NGÀY HẸN"] = _sua_ngay_hen(cu)

    _bao_cao(cu, moi)
    dich.parent.mkdir(parents=True, exist_ok=True)
    moi.to_csv(dich, index=False)
    print(f"\n✅ Đã ghi: {dich}")
    print(f"   {len(moi):,} dòng × {len(moi.columns)} cột")
    print("\nDán vào sheet LEAD: mở file, copy TỪ HÀNG 2 (bỏ dòng tiêu đề),")
    print("dán vào ô A2 của tab LEAD. Đừng dán đè hàng tiêu đề.")
    return 0


def _gop_ghi_chu(cu: pd.DataFrame) -> pd.Series:
    """Gộp mấy cột lẻ vào GHI CHÚ, mỗi phần kèm nhãn để còn biết gốc ở đâu."""
    phan = []
    for cot in GOP_VAO_GHI_CHU:
        if cot not in cu.columns:
            continue
        nhan = cot.replace("\n", " ").strip()
        phan.append(cu[cot].apply(
            lambda v, n=nhan: f"{n}: {str(v).strip()}" if pd.notna(v) else ""))
    if not phan:
        return pd.Series([pd.NA] * len(cu), index=cu.index)
    gop = phan[0]
    for p in phan[1:]:
        gop = gop.str.cat(p, sep=" | ")
    return (gop.str.strip(" |").replace("", pd.NA)
               .str.replace(r"\s*\|\s*\|\s*", " | ", regex=True))


def _sua_ngay_hen(cu: pd.DataFrame) -> pd.Series:
    """Suy năm cho ngày hẹn ghi thiếu năm ('10/01', '22/1').

    327/328 dòng không parse được nếu để nguyên. Năm suy từ ngày lead: hẹn
    luôn ở tương lai nên chọn năm gần nhất mà ngày hẹn >= ngày lead.
    """
    ngay_lead = cu["NGÀY"].apply(parse_date_vn)
    ket_qua = [parse_date_vn(v, moc) for v, moc in zip(cu["NGÀY HẸN"], ngay_lead)]
    # Ghi lại dạng dd/MM/yyyy cho khớp định dạng cột trong sheet mới.
    return pd.Series(
        [d.strftime("%d/%m/%Y") if pd.notna(d) else pd.NA for d in ket_qua],
        index=cu.index)


def _bao_cao(cu: pd.DataFrame, moi: pd.DataFrame) -> None:
    """In đối chiếu để tự kiểm chuyển đổi không làm mất hay méo dữ liệu."""
    print("--- Đối chiếu ---")
    print(f"  Số dòng            : {len(cu):,} -> {len(moi):,} "
          f"{'✅' if len(cu) == len(moi) else '❌ LỆCH'}")

    sdt_cu = cu["SỐ ĐT"].apply(clean_phone).notna().sum()
    sdt_moi = moi["SỐ ĐT"].apply(clean_phone).notna().sum()
    print(f"  SĐT dùng được      : {sdt_cu:,} -> {sdt_moi:,} "
          f"{'✅' if sdt_cu == sdt_moi else '❌ LỆCH'}")

    hen_cu = cu["NGÀY HẸN"].apply(parse_date_vn).notna().sum()
    hen_moi = moi["NGÀY HẸN"].apply(parse_date_vn).notna().sum()
    print(f"  Ngày hẹn đọc được  : {hen_cu:,} -> {hen_moi:,} "
          f"{'✅ cứu được ' + str(hen_moi - hen_cu) if hen_moi > hen_cu else ''}")

    for cot_moi, cot_cu in (("TÌNH TRẠNG", "TÌNH TRẠNG"),
                            ("TƯ VẤN - SALE", "TRẠNG THÁI.2"),
                            ("THÔNG TIN KHÁCH", "THÔNG TIN KHÁCH")):
        a, b = cu[cot_cu].notna().sum(), moi[cot_moi].notna().sum()
        print(f"  {cot_moi:<18} : {a:,} -> {b:,} {'✅' if a == b else '❌ LỆCH'}")

    print("\n--- Cột bỏ đi ---")
    for cot, ly_do in BO_HAN.items():
        n = cu[cot].notna().sum() if cot in cu.columns else 0
        print(f"  {cot:<24} {n:>5} dòng — {ly_do}")

    print("\n--- Cột gộp vào GHI CHÚ ---")
    for cot in GOP_VAO_GHI_CHU:
        if cot in cu.columns:
            print(f"  {cot.replace(chr(10), ' '):<24} {cu[cot].notna().sum():>5} dòng")

    # Ngày lead nghi gõ nhầm năm — KHÔNG tự sửa, chỉ báo để người quyết định.
    ngay = cu["NGÀY"].apply(parse_date_vn)
    ngoai = ngay.notna() & (ngay < pd.Timestamp("2026-01-01"))
    if ngoai.any():
        cac_ngay = ngay[ngoai].dt.date.value_counts()
        print(f"\n⚠️  {int(ngoai.sum())} dòng có NGÀY trước 2026, dồn vào: "
              f"{dict(list(cac_ngay.items())[:3])}")
        print("   Nhiều khả năng gõ nhầm năm. Script KHÔNG tự sửa — xem lại rồi")
        print("   sửa trong sheet, vì đoán sai năm sẽ làm lệch cả báo cáo theo tháng.")

    lead_moi = moi.rename(columns={})
    con_thieu = [c for c in schema.LEAD_REQUIRED if c not in lead_moi.columns]
    print(f"\n--- Khớp schema: {'✅ đủ cột bắt buộc' if not con_thieu else '❌ thiếu ' + str(con_thieu)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    nguon = Path(sys.argv[1])
    dich = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output/LEAD_da_chuyen.csv")
    sys.exit(main(nguon, dich))
