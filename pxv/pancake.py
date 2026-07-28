"""Vá số điện thoại còn thiếu của lead bằng SĐT Pancake quét từ hội thoại.

BỐI CẢNH: 46% lead không có SĐT nên không join được với hóa đơn — không biết
họ có mua hay không. Pancake tự quét SĐT khách nhắn trong nội dung hội thoại,
nên về lý thuyết vá được phần này.

RỦI RO — đọc kỹ trước khi bật:

Khóa join duy nhất giữa Pancake và lead là TÊN KHÁCH. Mà tên Facebook cực kỳ
lộn xộn: 'lovingtheoceanbecauseofu - Overthinker tập sống vô tri',
'Xuân Yến (BV Phương Châu)', 'Hương Trần (fb Huong Tran)'. Ghép nhầm tên =
gán SĐT của người này cho người khác = hỏng phễu và CLV mà KHÔNG AI BIẾT,
vì kết quả trông vẫn hợp lý.

Vì vậy quy tắc ở đây cố tình chặt tới mức bỏ sót còn hơn ghép sai:

* Chỉ ghép khi tên chuẩn hóa xuất hiện ĐÚNG MỘT LẦN ở CẢ HAI phía. Trùng tên
  thì bỏ qua hoàn toàn, không đoán theo ngày hay theo page.
* So khớp CHÍNH XÁC sau chuẩn hóa, không dùng so gần đúng. 'Xuân Yến' và
  'Xuân Yến (BV Phương Châu)' coi như hai người khác nhau.
* KHÔNG BAO GIỜ ghi đè SĐT đã có.
* Dòng nào được vá thì gắn cờ ``SĐT_từ_Pancake`` để truy vết và loại ra khi
  cần phân tích chặt.

Mặc định TẮT (``config.PANCAKE_ENABLED``). Chỉ bật khi có dữ liệu thật và đo
được tỷ lệ vá đủ lớn — xem :func:`fill_missing_phones` trả về thống kê để
quyết định.
"""
from __future__ import annotations

import re

import pandas as pd

from .clean import clean_phone, phone_kind

COT_CO = "SĐT_từ_Pancake"


def khoa_ten(value) -> str | None:
    """Chuẩn hóa tên để so khớp: gộp khoảng trắng, bỏ phân biệt hoa thường.

    Cố tình KHÔNG bỏ phần trong ngoặc hay ký tự đặc biệt — làm vậy sẽ gộp
    'Xuân Yến (BV Phương Châu)' với 'Xuân Yến' thành một người, đúng kiểu sai
    lầm mà module này muốn tránh.
    """
    if pd.isna(value):
        return None
    ten = re.sub(r"\s+", " ", str(value)).strip().casefold()
    return ten or None


def fill_missing_phones(df_lead: pd.DataFrame,
                        df_pancake: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Điền SĐT cho lead còn trống. Trả về ``(lead_đã_vá, thống_kê)``.

    Thống kê là thứ dùng để quyết định có nên giữ tính năng này không, nên
    đếm cả các ca bỏ qua chứ không chỉ đếm ca thành công.
    """
    out = df_lead.copy()
    if COT_CO not in out.columns:
        out[COT_CO] = False

    thieu = out["Phone_Clean"].isna()
    tk = {
        "pancake_dòng": len(df_pancake),
        "lead_thiếu_sđt": int(thieu.sum()),
        "vá_được": 0,
        "bỏ_qua_trùng_tên_lead": 0,
        "bỏ_qua_trùng_tên_pancake": 0,
        "không_tìm_thấy_tên": 0,
    }
    if df_pancake.empty or not thieu.any():
        return out, tk

    pk = df_pancake.copy()
    pk["_khóa"] = pk["Tên khách"].apply(khoa_ten) if "Tên khách" in pk else None
    pk = pk.dropna(subset=["_khóa", "Phone_Clean"])

    # Tên xuất hiện nhiều lần ở phía Pancake -> không biết chọn số nào.
    dem_pk = pk["_khóa"].value_counts()
    ten_duy_nhat_pk = set(dem_pk[dem_pk == 1].index)
    tra_cuu = pk[pk["_khóa"].isin(ten_duy_nhat_pk)].set_index("_khóa")["Phone_Clean"]

    out["_khóa"] = out["TÊN KHÁCH HÀNG"].apply(khoa_ten)
    # Tên xuất hiện nhiều lần ở phía lead -> gán cho ai cũng có thể sai.
    dem_lead = out.loc[thieu, "_khóa"].value_counts()
    ten_duy_nhat_lead = set(dem_lead[dem_lead == 1].index)

    for idx in out.index[thieu]:
        khoa = out.at[idx, "_khóa"]
        # Phải dùng isinstance chứ không phải `khoa is None`: tùy phiên bản,
        # pandas biến None thành NaN khi apply() trên cột object. Lúc đó
        # `is None` trả False và dòng KHÔNG CÓ TÊN bị đếm nhầm sang nhánh
        # trùng tên — lỗi chỉ lộ ra trên CI vì máy dev cài pandas bản khác.
        if not isinstance(khoa, str):
            tk["không_tìm_thấy_tên"] += 1
            continue
        if khoa not in ten_duy_nhat_lead:
            tk["bỏ_qua_trùng_tên_lead"] += 1
            continue
        if khoa not in tra_cuu.index:
            if khoa in dem_pk.index:
                tk["bỏ_qua_trùng_tên_pancake"] += 1
            else:
                tk["không_tìm_thấy_tên"] += 1
            continue

        sdt = clean_phone(tra_cuu.loc[khoa])
        if not sdt:
            continue
        out.at[idx, "Phone_Clean"] = sdt
        out.at[idx, "Loại SĐT"] = phone_kind(sdt)
        out.at[idx, COT_CO] = True
        tk["vá_được"] += 1

    tk["tỷ_lệ_vá_%"] = round(tk["vá_được"] / tk["lead_thiếu_sđt"] * 100, 1) \
        if tk["lead_thiếu_sđt"] else 0.0
    return out.drop(columns=["_khóa"]), tk


def tom_tat(tk: dict) -> str:
    """Một dòng in ra log, đủ để quyết định giữ hay bỏ tính năng."""
    return (f"Pancake: vá {tk['vá_được']}/{tk['lead_thiếu_sđt']} lead thiếu SĐT "
            f"({tk['tỷ_lệ_vá_%']}%) — bỏ qua "
            f"{tk['bỏ_qua_trùng_tên_lead']} trùng tên ở lead, "
            f"{tk['bỏ_qua_trùng_tên_pancake']} trùng tên ở Pancake, "
            f"{tk['không_tìm_thấy_tên']} không khớp tên nào")
