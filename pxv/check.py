"""Kiểm tra kết nối Google Sheets trước khi chạy pipeline thật.

Chạy:
    GCP_SA_KEY="$(cat service-account.json)" PXV_BACKEND=sheets \
    PXV_SHEET_NHAP_LIEU=... PXV_SHEET_KHO=... PXV_SHEET_DASHBOARD=... \
    python -m pxv.check

Mục đích: gỡ lỗi quyền ngay ở máy thay vì đợi mỗi vòng CI 2 phút, và nói rõ
sai ở đâu thay vì ném traceback.
"""
from __future__ import annotations

import json
import os
import sys

from . import config

# (biến ID, tên file, các tab bắt buộc, có cần ghi không)
MUC_TIEU = [
    ("SHEET_ID_NHAP_LIEU", "PXV_NHẬP_LIỆU", [config.TAB_LEAD], False),
    ("SHEET_ID_KHO", "PXV_KHO", [config.TAB_INVOICES], False),
    ("SHEET_ID_DASHBOARD", "PXV_DASHBOARD_DATA", [], True),
]


def main() -> int:
    loi = 0
    print("=" * 66)
    print(" KIỂM TRA KẾT NỐI GOOGLE SHEETS")
    print("=" * 66)

    loi += _kiem_key()
    if loi:
        print("\nDừng vì chưa xác thực được — sửa xong chạy lại.")
        return 1

    from . import io_sheets

    for bien, ten_file, tabs, can_ghi in MUC_TIEU:
        loi += _kiem_mot_file(io_sheets, bien, ten_file, tabs, can_ghi)

    print("\n" + "=" * 66)
    if loi:
        print(f" ❌ {loi} vấn đề — xem hướng dẫn ở từng dòng trên")
        return 1
    print(" ✅ Kết nối tốt. Chạy được: PXV_BACKEND=sheets python -m pxv.run_daily")
    return 0


def _kiem_key() -> int:
    tren_github = os.environ.get("GITHUB_ACTIONS") == "true"
    raw = os.environ.get("GCP_SA_KEY", "")
    if not raw:
        print("\n❌ Thiếu biến môi trường GCP_SA_KEY")
        if tren_github:
            print("   Đang chạy trên GitHub Actions nhưng secret không tới được job.")
            print("   Kiểm tra: Settings > Secrets and variables > Actions")
            print("     - Secret phải nằm ở tab SECRETS, không phải tab Variables")
            print("     - Tên phải đúng y hệt: GCP_SA_KEY (không thừa dấu cách)")
            print("     - Nếu secret đặt trong một Environment thì job phải khai")
            print("       báo `environment:` mới nhìn thấy được")
        else:
            print("   Đang chạy Ở MÁY BẠN, không phải trên GitHub.")
            print()
            print("   GitHub Secrets CHỈ tồn tại bên trong máy chủ chạy Actions —")
            print("   chúng KHÔNG tự đồng bộ về máy. Thêm secret trên GitHub xong")
            print("   thì ở máy vẫn phải tự khai báo biến:")
            print()
            print('     export GCP_SA_KEY="$(cat ~/Downloads/pxv-pipeline-xxxx.json)"')
            print("     python -m pxv.check")
            print()
            print("   Còn muốn kiểm tra secret trên GitHub có đúng không, thì chạy")
            print("   workflow rồi xem bước \"Kiểm tra cấu hình\":")
            print("     Actions > pipeline hằng ngày > Run workflow")
        return 1
    try:
        info = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"\n❌ GCP_SA_KEY không phải JSON hợp lệ: {e}")
        print("   Dán nguyên văn nội dung file JSON, đừng bọc thêm dấu nháy.")
        return 1
    if info.get("type") != "service_account":
        print(f"\n❌ GCP_SA_KEY là JSON nhưng type='{info.get('type')}', "
              "không phải service_account")
        return 1
    print(f"\n✅ Service account: {info.get('client_email')}")
    print("   (email này phải được share quyền ở cả 3 spreadsheet)")
    return 0


def _kiem_mot_file(io_sheets, bien: str, ten_file: str,
                   tabs: list[str], can_ghi: bool) -> int:
    sid = getattr(config, bien, "")
    print(f"\n--- {ten_file} ---")
    if not sid:
        print(f"❌ Thiếu biến môi trường PXV_{bien.replace('SHEET_ID_', 'SHEET_')}")
        return 1

    try:
        sh = io_sheets._client().open_by_key(sid)
    except Exception as e:
        print(f"❌ Không mở được (ID {sid[:14]}…)")
        print(f"   {type(e).__name__}: {str(e)[:160]}")
        print("   Thường do: chưa share cho service account, hoặc sai ID.")
        return 1

    co = [ws.title for ws in sh.worksheets()]
    print(f"✅ Mở được: \"{sh.title}\"  ({len(co)} tab)")
    print(f"   Tab: {', '.join(co)}")

    loi = 0
    for tab in tabs:
        if tab not in co:
            print(f"❌ Thiếu tab bắt buộc \"{tab}\" — chạy dungHeThong() trong "
                  "Bootstrap.gs, hoặc kiểm tra tên tab có gõ đúng không")
            loi += 1
            continue
        ws = sh.worksheet(tab)
        print(f"   \"{tab}\": {ws.row_count} hàng × {ws.col_count} cột, "
              f"có dữ liệu tới hàng {len(ws.get_all_values())}")

    if can_ghi:
        loi += _thu_ghi(sh)
    return loi


def _thu_ghi(sh) -> int:
    """Ghi một ô vào tab tạm rồi xóa. Không đụng dữ liệu thật."""
    ten_tam = "_PXV_KIEM_TRA"
    try:
        try:
            ws = sh.worksheet(ten_tam)
        except Exception:
            ws = sh.add_worksheet(title=ten_tam, rows=2, cols=2)
        ws.update([["ok"]], "A1", value_input_option="RAW")
        doc_lai = ws.acell("A1").value
        sh.del_worksheet(ws)
        if doc_lai != "ok":
            print(f"❌ Ghi được nhưng đọc lại ra {doc_lai!r}")
            return 1
        print("✅ Ghi thử thành công (đã dọn tab tạm)")
        return 0
    except Exception as e:
        print(f"❌ Không ghi được: {type(e).__name__}: {str(e)[:160]}")
        print("   Thường do share nhầm quyền Viewer — file này cần Editor.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
