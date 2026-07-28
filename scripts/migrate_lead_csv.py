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

    # Bỏ dòng trống hoàn toàn (rác từ file gốc). KHÔNG bỏ dòng thiếu ngày mà
    # vẫn có tên/SĐT — đó là khách thật, xóa đi là mất dữ liệu.
    trong = moi.isna().all(axis=1)
    if trong.any():
        print(f"Bỏ {int(trong.sum())} dòng trống hoàn toàn\n")
        moi = moi[~trong].reset_index(drop=True)
        cu = cu[~trong.values].reset_index(drop=True)

    _bao_cao(cu, moi)
    dich.parent.mkdir(parents=True, exist_ok=True)

    # BOM (utf-8-sig) để Excel nhận ra UTF-8. Thiếu nó thì Excel trên Mac đọc
    # bằng Mac Roman và 'NGÀY' hiện thành 'NG√ÄY' — dữ liệu vẫn đúng, chỉ hiển
    # thị sai, nhưng copy từ màn hình đó sang Sheets là hỏng thật.
    # CSV không có kiểu ngày, chỉ có chữ — nên ghi ISO (yyyy-mm-dd). Đây là
    # dạng duy nhất không lật được ngày/tháng dù locale nào đọc. Xem _ghi_xlsx.
    csv_out = moi.copy()
    for cot in COT_NGAY:
        csv_out[cot] = [d.strftime("%Y-%m-%d") if pd.notna(d := parse_date_vn(v)) else v
                        for v in csv_out[cot]]
    csv_out.to_csv(dich, index=False, encoding="utf-8-sig")

    # Bản .xlsx không có khái niệm bảng mã nên không bao giờ lỗi font. Đây là
    # bản nên dùng để dán vào Sheets.
    dich_xlsx = dich.with_suffix(".xlsx")
    _ghi_xlsx(moi, dich_xlsx)

    print(f"\n✅ Đã ghi {len(moi):,} dòng × {len(moi.columns)} cột:")
    print(f"   {dich_xlsx}   <- DÙNG BẢN NÀY")
    print(f"   {dich}   (CSV kèm BOM, phòng khi cần)")
    print("\n--- Đưa vào sheet LEAD ---")
    print("Cách an toàn nhất (không lo bảng mã, không lo mất số 0 đầu SĐT):")
    print("  Mở PXV_NHẬP_LIỆU > File > Import > Upload > chọn file .xlsx")
    print("  > Import location: 'Replace data at selected cell', chọn ô A2 của tab LEAD")
    print("  > Bỏ tick 'Convert text to numbers, dates and formulas'")
    print("\nHoặc mở .xlsx rồi copy từ hàng 2 (bỏ tiêu đề), dán vào ô A2.")
    print("Đừng dán đè hàng tiêu đề — nó đang khóa và pipeline dựa vào đó kiểm schema.")
    print("\nSau khi import, kiểm nhanh: cột NGÀY phải trải đều T1-T3/2026.")
    print("Thấy dữ liệu rơi vào tháng 4-12 là ngày đã bị lật ngày/tháng — import lại.")
    return 0


COT_NGAY = ("NGÀY", "NGÀY HẸN")
COT_TEXT = ("SỐ ĐT", "GIỜ HẸN")


def _ghi_xlsx(df: pd.DataFrame, dich: Path) -> None:
    """Ghi .xlsx: SĐT dạng text (giữ số 0 đầu), NGÀY dạng NGÀY THẬT.

    Ngày PHẢI là ô ngày thật, không phải chuỗi. Bản cũ ghi '10/01/2026' dạng
    text; khi import vào Sheets với locale Mỹ, chuỗi đó được đọc thành mm/dd —
    10 tháng 1 biến thành 1 tháng 10. Ngày > 12 thì không lật được nên nằm im,
    còn ngày <= 12 thì lật: 1.076/2.419 dòng NGÀY và 112/325 dòng NGÀY HẸN sai
    mà nhìn vẫn ra ngày hợp lệ. Ô ngày thật mang sẵn số serial, không qua bước
    đọc chuỗi, nên đúng dù người import có tick 'Convert text to numbers,
    dates and formulas' hay không.

    Giá trị không parse được thì giữ nguyên chữ — không đoán, để người sửa tay.
    """
    xl = df.copy()
    for cot in COT_NGAY:
        xl[cot] = [d if pd.notna(d := parse_date_vn(v)) else v for v in xl[cot]]

    with pd.ExcelWriter(dich, engine="openpyxl") as w:
        xl.to_excel(w, index=False, sheet_name="LEAD")
        ws = w.sheets["LEAD"]
        for i, c in enumerate(xl.columns, start=1):
            if c not in COT_TEXT and c not in COT_NGAY:
                continue
            dinh_dang = "dd/MM/yyyy" if c in COT_NGAY else "@"
            for hang in range(2, len(xl) + 2):
                o = ws.cell(row=hang, column=i)
                # Ô còn là chữ (ngày không parse được) thì để text, gán định
                # dạng ngày lên chuỗi chỉ làm Excel hiện ###.
                o.number_format = "@" if isinstance(o.value, str) else dinh_dang


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

    # Dòng có dữ liệu thật nhưng thiếu NGÀY: pipeline lọc theo ngày nên chúng
    # sẽ nằm trong sheet mà không bao giờ vào báo cáo. Giữ lại (là khách thật)
    # nhưng phải báo để người nhập điền ngày.
    thieu_ngay = moi["NGÀY"].isna() & moi["TÊN KHÁCH HÀNG"].notna()
    if thieu_ngay.any():
        print(f"\n⚠️  {int(thieu_ngay.sum())} dòng có tên/SĐT nhưng THIẾU NGÀY:")
        for _, r in moi[thieu_ngay].head(8).iterrows():
            sdt = r["SỐ ĐT"] if pd.notna(r["SỐ ĐT"]) else "(không có SĐT)"
            print(f"     {str(r['TÊN KHÁCH HÀNG'])[:34]:36} {sdt}")
        print("   Vẫn giữ trong file (là khách thật), nhưng pipeline lọc theo ngày")
        print("   nên chúng sẽ KHÔNG vào báo cáo. Điền NGÀY trong sheet để dùng được.")

    con_thieu = [c for c in schema.LEAD_REQUIRED if c not in moi.columns]
    print(f"\n--- Khớp schema: {'✅ đủ cột bắt buộc' if not con_thieu else '❌ thiếu ' + str(con_thieu)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    nguon = Path(sys.argv[1])
    dich = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output/LEAD_da_chuyen.csv")
    sys.exit(main(nguon, dich))
