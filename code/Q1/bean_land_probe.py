from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from code.model_common import (  # noqa: E402
    BEANS,
    deterministic_maps,
    evaluate_schedule,
    read_data,
    solve_milp_schedule,
)


def main() -> None:
    out = ROOT / "results" / "Q1" / "experiments" / "round3"
    (out / "tables").mkdir(parents=True, exist_ok=True)
    (out / "metrics").mkdir(parents=True, exist_ok=True)
    data = read_data()
    demand, yld, cost, price = deterministic_maps(data)
    rows = []
    for beta in [0, 100, 300, 500, 800]:
        schedule, solver = solve_milp_schedule(
            data, alpha=0.5, demand=demand, yield_map=yld, cost_map=cost,
            price_map=price, min_share=0.1, max_crops=3,
            bean_land_value=beta,
        )
        row = {"beta_cny_per_mu": beta, "solver": solver}
        if solver.get("success"):
            checked = evaluate_schedule(data, schedule, alpha=0.5)
            total_area = float(schedule.area_mu.sum())
            bean_area = float(schedule.loc[schedule.crop_id.isin(BEANS), "area_mu"].sum())
            row.update({
                "status": "success",
                "real_profit_cny": checked["cumulative_profit"],
                "bean_area_share": bean_area / total_area,
                "unique_crop_count": int(schedule.loc[schedule.area_mu > 1e-7, "crop_id"].nunique()),
                "constraint_violations": int(checked.get("constraint_violations", 0)),
            })
            schedule.to_csv(out / "tables" / f"bean_land_beta_{beta}.csv", index=False, encoding="utf-8-sig")
        else:
            row["status"] = "failed"
        rows.append(row)
    pd.DataFrame([{k: v for k, v in r.items() if k != "solver"} for r in rows]).to_csv(
        out / "tables" / "bean_land_value_sensitivity.csv", index=False, encoding="utf-8-sig"
    )
    (out / "metrics" / "bean_land_value_sensitivity.json").write_text(
        json.dumps({"question": "Q1", "experiment": "bean_land_value_sensitivity", "rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    summary = {
        "schema_version": 1, "question": "Q1", "round": "round3",
        "implementation_target": "python", "status": "success",
        "approved_methods": ["Q1-M1"],
        "experiment": "bean_land_value_sensitivity",
        "input_files": ["workspace/data_clean/plots.csv", "workspace/data_clean/crops.csv", "workspace/data_clean/planting_2023.csv", "workspace/data_clean/stats_2023.csv", "workspace/data_clean/stats_2023_derived.csv"],
        "output_files": ["metrics/bean_land_value_sensitivity.json", "tables/bean_land_value_sensitivity.csv"],
        "warnings": ["附加敏感性分析，不改变Q1正式填表方案"],
    }
    (out / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
