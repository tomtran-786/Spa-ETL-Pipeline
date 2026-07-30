"""Sinh chi phí quảng cáo MÔ PHỎNG cho case study, tuyệt đối không dùng vận hành.

Dữ liệu đầu vào là số lead thật đã tổng hợp theo (tháng, kênh); đầu ra không
chứa PII. Chi phí là giả định minh bạch, không phải chi phí marketing của Spa này.

Chạy sau ``python -m pxv.run_daily``:

    python scripts/generate_toy_ad_costs.py

Các file nằm trong ``output/toy/`` (đã bị gitignore) và chỉ dùng cho bản
dashboard case study tách biệt. Không thay thế ``chi_phi_qc.csv`` vận hành.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

# Khi gọi trực tiếp ``python scripts/...``, Python chỉ đặt scripts/ vào
# sys.path. Thêm root để import được package pxv giống các lệnh vận hành khác.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pxv import config


# Các giả định CPL chỉ để minh họa. Chúng được ghi lại trong manifest để mọi
# số CPL/CAC/ROAS sau đó đều có lineage rõ ràng, không bị hiểu là số thật.
BASE_CPL_VND = {
    "Facebook": 70_000,
    "Tiktok": 55_000,
    "Instagram": 90_000,
}

# Kịch bản chỉ thay đổi CHI PHÍ mô phỏng. Doanh thu vẫn là lịch sử thực tế,
# vì vậy ROAS sinh ra là chỉ số scenario, không được diễn giải là kết quả đã
# đạt sau khi chạy chiến dịch.
SCENARIOS = {
    "baseline": {
        "cost_multiplier": 1.00,
        "description": "Ngân sách giả định theo CPL cơ sở của từng kênh.",
    },
    "efficiency": {
        "cost_multiplier": 0.85,
        "description": "Mô phỏng giảm 15% CPL nhờ tối ưu creative/targeting.",
    },
    "growth": {
        "cost_multiplier": 1.25,
        "description": "Mô phỏng tăng 25% ngân sách với cùng cơ cấu kênh.",
    },
}


def paid_leads(master: pd.DataFrame) -> pd.DataFrame:
    """Rút lead thật theo tháng/kênh, chỉ giữ các kênh paid social giả định."""
    lead = master[master["Ngày Lead"].notna()].copy()
    lead["tháng"] = pd.to_datetime(lead["Ngày Lead"]).dt.strftime("%Y-%m")
    lead = lead[lead["Kênh Tiếp Cận"].isin(BASE_CPL_VND)]
    out = (lead.groupby(["tháng", "Kênh Tiếp Cận"], as_index=False)
               .agg(lead=("[F] 1_Có Inbox", "sum"))
               .rename(columns={"Kênh Tiếp Cận": "kênh"}))
    return out[out["lead"] > 0].sort_values(["tháng", "kênh"]).reset_index(drop=True)


def build_costs(lead_by_channel: pd.DataFrame, multiplier: float,
                scenario: str) -> pd.DataFrame:
    """Tạo đúng 4 cột mà ``pxv.ad_costs`` nhận, không thêm dữ liệu nhận diện."""
    out = lead_by_channel.copy()
    out["chi phí"] = [
        int(round(leads * BASE_CPL_VND[channel] * multiplier / 1_000) * 1_000)
        for channel, leads in zip(out["kênh"], out["lead"])
    ]
    out["mã bài QC"] = [
        f"SIM-{scenario.upper()}-{channel[:3].upper()}-{month.replace('-', '')}"
        for month, channel in zip(out["tháng"], out["kênh"])
    ]
    return out[["tháng", "kênh", "mã bài QC", "chi phí"]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--master", type=Path,
        default=config.OUT_DIR / "PXV_DASHBOARD_DATA.xlsx",
        help="Workbook pipeline đã chạy; mặc định output/PXV_DASHBOARD_DATA.xlsx.",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=config.OUT_DIR / "toy",
        help="Thư mục output tách biệt cho case study.",
    )
    args = parser.parse_args()

    master = pd.read_excel(args.master, sheet_name="MASTER")
    lead_by_channel = paid_leads(master)
    if lead_by_channel.empty:
        raise RuntimeError("Không có lead paid social để mô phỏng chi phí.")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, spec in SCENARIOS.items():
        costs = build_costs(lead_by_channel, spec["cost_multiplier"], name)
        costs.to_csv(args.out_dir / f"chi_phi_qc_{name}.csv", index=False,
                     encoding="utf-8-sig")
        manifest.append({
            "scenario": name,
            "data_classification": "TOY / SIMULATED — NOT ACTUAL MARKETING SPEND",
            "cost_multiplier": spec["cost_multiplier"],
            "base_cpl_vnd": "; ".join(f"{k}={v:,}" for k, v in BASE_CPL_VND.items()),
            "description": spec["description"],
            "interpretation_limit": (
                "Revenue remains historical; ROAS is a scenario metric, not an achieved result."
            ),
        })
        print(f"{name:10} {len(costs):>2} dòng | tổng chi phí mô phỏng "
              f"{costs['chi phí'].sum():,.0f} đ")

    pd.DataFrame(manifest).to_csv(args.out_dir / "scenario_manifest.csv",
                                  index=False, encoding="utf-8-sig")
    print(f"Đã ghi toy dataset vào: {args.out_dir}")


if __name__ == "__main__":
    main()
