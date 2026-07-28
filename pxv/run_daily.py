"""Điểm chạy hằng ngày: đọc nguồn → dựng bảng → kiểm chất lượng → ghi ra.

Chạy:  python -m pxv.run_daily
"""
from __future__ import annotations

import sys

import pandas as pd

from . import config, marts, quality, transform


def _io():
    """Chọn nguồn dữ liệu theo cấu hình. Hai module có cùng interface."""
    if config.BACKEND == "sheets":
        from . import io_sheets
        return io_sheets
    from . import io_local
    return io_local


def main(strict: bool = True) -> int:
    io = _io()
    print(f"Đọc nguồn (backend: {config.BACKEND})...")
    df_lead = io.load_leads()
    df_hen = io.load_appointments(df_lead)
    df_inv = io.load_invoices()
    print(f"  lead {len(df_lead):,} dòng | hẹn {len(df_hen):,} SĐT | "
          f"hóa đơn {df_inv['Mã hóa đơn'].nunique():,}")

    costs = io.load_ad_costs()
    if not costs.empty:
        print(f"  chi phí quảng cáo {len(costs):,} dòng")

    print("Dựng bảng...")
    master = transform.build_master(df_lead, df_hen, df_inv)
    dim_khach = marts.build_dim_khach(master, df_inv)
    funnel_moi = marts.build_funnel_moi(df_inv)
    daily = marts.build_daily(master)
    hieu_qua = marts.build_hieu_qua_kenh(master, costs, dim_khach)

    print("Kiểm chất lượng...")
    report = quality.run_checks(df_lead, df_inv, master, costs)
    print(report.to_frame().to_string(index=False))

    tables = {
        "MASTER": master,
        "DIM_KHACH": dim_khach,
        "FUNNEL_MOI": funnel_moi,
        "FACT_DAILY": daily,
        "HIEU_QUA_KENH": hieu_qua,
        "DQ_STATUS": report.to_frame(),
        "CẦN_SỬA": report.cần_sửa,
    }

    print("Ghi kết quả...")
    if config.BACKEND == "sheets":
        # Ghi DQ_STATUS TRƯỚC: nếu các bảng sau lỗi, watchdog vẫn đọc được mốc
        # thời gian và biết pipeline có chạy — im lặng mới là thứ nguy hiểm.
        io.write_table("DQ_STATUS", report.to_frame())
        io.write_all({k: v for k, v in tables.items() if k != "DQ_STATUS"})
    else:
        config.OUT_DIR.mkdir(exist_ok=True)
        out = config.OUT_DIR / "PXV_DASHBOARD_DATA.xlsx"
        with pd.ExcelWriter(out, datetime_format="DD/MM/YYYY") as writer:
            for name, df in tables.items():
                df.to_excel(writer, sheet_name=name[:31], index=False)
        print(f"  {out}")
        for name, df in tables.items():
            print(f"  {name:12} {len(df):>6,} dòng")

    _summary(master, dim_khach, funnel_moi)

    if strict:
        report.raise_if_failed()
    return 0


def _summary(master, dim_khach, funnel_moi) -> None:
    print(f"\n{'=' * 58}")
    print(f"Doanh thu   : {master['Doanh Thu (VNĐ)'].sum():,.0f} đ")
    print(f"Hóa đơn     : {master['Mã hóa đơn'].nunique():,}")
    print("Phễu lead   :")
    prev = None
    for flag in transform.FUNNEL_FLAGS:
        v = int(master[flag].sum())
        step = f"  ({v / prev * 100:5.1f}% bước trước)" if prev else ""
        print(f"  {flag:22}: {v:>6,}{step}")
        prev = v
    f1 = int(master[transform.FUNNEL_FLAGS[0]].sum())
    f4 = int(master[transform.FUNNEL_FLAGS[-1]].sum())
    if f1:
        print(f"  Tỷ lệ chốt trên inbox : {f4 / f1 * 100:.2f}%")
    if not dim_khach.empty:
        print(f"CLV trung bình: {dim_khach['tổng_doanh_thu'].mean():,.0f} đ "
              f"({len(dim_khach):,} khách, "
              f"{dim_khach['là_khách_quay_lại'].mean() * 100:.1f}% quay lại)")
    if not funnel_moi.empty:
        up = funnel_moi["upsell_90d"].mean() * 100
        print(f"Dịch vụ mồi : {len(funnel_moi):,} khách, {up:.1f}% upsell trong 90 ngày")


if __name__ == "__main__":
    sys.exit(main())
