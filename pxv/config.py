"""Cấu hình tập trung: đường dẫn, cửa sổ thời gian, ngưỡng cảnh báo.

Giai đoạn 1 đọc file local. Khi chuyển sang Google Sheets chỉ cần đổi
`io_sheets.py`, không đụng vào các module tính toán.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

BASE = Path(os.environ.get("PXV_BASE", Path(__file__).resolve().parent.parent))
OUT_DIR = BASE / "output"

# --- Chọn nguồn: 'local' (file trên máy) hay 'sheets' (Google Sheets) ---
# GitHub Actions đặt PXV_BACKEND=sheets; chạy tay ở máy thì để mặc định local.
BACKEND = os.environ.get("PXV_BACKEND", "local")

# --- Nguồn dữ liệu khi chạy local ---
F_LEAD = BASE / "Sales_Marketing dataset - SALE T1-2-3_2026.csv"
F_HEN = BASE / "ĐĂT HẸN .csv"
F_INV = BASE / "Doanh thu T11.2025 đến 25.02.xlsx"

# --- Nguồn dữ liệu khi chạy trên Google Sheets ---
SHEET_ID_NHAP_LIEU = os.environ.get("PXV_SHEET_NHAP_LIEU", "")
SHEET_ID_KHO = os.environ.get("PXV_SHEET_KHO", "")
SHEET_ID_DASHBOARD = os.environ.get("PXV_SHEET_DASHBOARD", "")

TAB_LEAD = "LEAD"
TAB_INVOICES = "INVOICES_RAW"
TAB_PANCAKE = "PANCAKE_RAW"

# --- Cửa sổ phân tích ---
# Funnel chỉ tính trong khoảng cả 3 nguồn cùng phủ. Hóa đơn trước mốc này vẫn
# được đọc để nhận diện khách mua lặp (phục vụ CLV), nhưng không vào funnel.
#
# Mặc định lấy từ biến môi trường; nếu không có thì dùng mốc cố định của bộ dữ
# liệu hiện tại. KHÔNG suy ra "12 tháng gần nhất" tự động vì dữ liệu là tĩnh —
# khi chuyển sang chạy hằng ngày với Sheets thì đổi sang rolling window.
WINDOW_START = pd.Timestamp(os.environ.get("PXV_WINDOW_START", "2026-01-01"))

# Khoảng ngày được coi là hợp lệ. Ngoài khoảng này thì KHÔNG tự sửa (code cũ
# ép năm 2025 -> 2026, sang 2027 sẽ sai âm thầm) mà đẩy ra báo cáo cho người xử lý.
DATE_VALID_LO = pd.Timestamp(os.environ.get("PXV_DATE_LO", "2025-01-01"))
DATE_VALID_HI = pd.Timestamp(os.environ.get("PXV_DATE_HI", "2027-12-31"))

# --- Dịch vụ mồi/phễu ---
# Quy tắc nghiệp vụ, thay đổi theo chiến dịch -> sẽ chuyển sang sheet DANH_MỤC.
FUNNEL_SERVICE_PATTERN = r"GÓI TIẾT KIỆM|Xóa lần 01|CO2 Fractional"

# Mốc thời gian tính upsell sau khi khách mua dịch vụ mồi (ngày).
UPSELL_WINDOWS = (30, 60, 90)

# --- Ngưỡng cảnh báo chất lượng ---
MAX_INVOICE_AGE_DAYS = 3      # hóa đơn mới nhất cũ hơn ngần này -> cảnh báo
CLOSED_MONTH_DRIFT = 0.01     # doanh thu tháng đã đóng đổi quá 1% -> dừng
MIN_SOURCE_IN_CATALOG = 0.98  # >=98% giá trị NGUỒN phải nằm trong danh mục

# Tháng đã biết là thiếu dữ liệu, bỏ qua khi kiểm "thủng tháng".
# T12/2025: KiotViet không export lại được nữa (xác nhận với nghiệp vụ 07/2026).
KNOWN_DATA_GAPS = ("2025-12",)
