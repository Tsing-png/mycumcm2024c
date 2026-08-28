from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from code.Q1 import q1_baseline, q1_main
from code.model_common import (
    check_schedule, concentration, environment, evaluate_schedule, file_hash,
    prepare_round, read_data, schedule_overlap, write_json, write_schedule,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", default="round1")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--time-limit", type=float, default=300.0)
    args = parser.parse_args()
    started = time.perf_counter()
    data = read_data()
    out = prepare_round("Q1", args.round)
    baseline = q1_baseline.run(data)
    base_viol = check_schedule(data, baseline)
    grid = [(0.0, 3), (0.1, 3)]
    grid_rows, method_records = [], []
    schedules = {}
    for alpha in [0.0, 0.5]:
        base_eval = evaluate_schedule(data, baseline, alpha)
        base_name = f"q1_b1_alpha{'0' if alpha == 0 else '05'}_schedule.csv"
        write_schedule(out / "tables" / base_name, baseline)
        method_records.append({
            "method_id": "Q1-B1", "role": "usable_baseline", "script": "code/Q1/q1_baseline.py",
            "status": "success" if not base_viol else "failed", "execution_time_seconds": 0.0,
            "input_files": ["workspace/data_clean/plots.csv", "workspace/data_clean/crops.csv", "workspace/data_clean/planting_2023.csv", "workspace/data_clean/stats_2023.csv", "workspace/data_clean/stats_2023_derived.csv"],
            "output_files": [f"tables/{base_name}"], "figure_files": [],
            "metrics_summary": {**base_eval, **concentration(baseline), "constraint_violations": len(base_viol), "alpha": alpha},
            "warnings": [], "errors": base_viol[:20],
        })
        for min_share, max_crops in grid:
            schedule, solver = q1_main.run(data, alpha, min_share, max_crops, args.time_limit)
            violations = check_schedule(data, schedule) if not schedule.empty else ["empty_schedule"]
            evals = evaluate_schedule(data, schedule, alpha) if not schedule.empty else {"profit_by_year": {}, "cumulative_profit": None}
            conc = concentration(schedule) if not schedule.empty else {}
            config = f"share{int(min_share*100)}_k{max_crops}"
            name = f"q1_m1_alpha{'0' if alpha == 0 else '05'}_{config}_schedule.csv"
            write_schedule(out / "tables" / name, schedule)
            schedules[(alpha, config)] = schedule
            grid_rows.append({"alpha": alpha, "config": config, "min_share": min_share, "max_crops": max_crops,
                              "cumulative_profit": evals["cumulative_profit"], "violations": len(violations), **conc, **solver})
            method_records.append({
                "method_id": "Q1-M1", "role": "main_candidate", "script": "code/Q1/q1_main.py",
                "status": "success" if solver["success"] and not violations else "failed",
                "execution_time_seconds": solver["execution_time_seconds"], "input_files": method_records[0]["input_files"],
                "output_files": [f"tables/{name}"], "figure_files": [],
                "metrics_summary": {**evals, **conc, "constraint_violations": len(violations), "alpha": alpha, "config": config, "solver": solver},
                "warnings": [] if solver["mip_gap"] is None or solver["mip_gap"] <= 0.01 else ["mip_gap_above_1pct"],
                "errors": violations[:20],
            })
    pd.DataFrame(grid_rows).to_csv(out / "tables/q1_management_grid.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"violation": v} for v in base_viol]).to_csv(out / "tables/q1_feasibility_checks.csv", index=False, encoding="utf-8-sig")
    metrics = {"management_grid": grid_rows, "baseline_concentration": concentration(baseline),
               "baseline_violations": base_viol, "main_baseline_overlap": {str(k): schedule_overlap(v, baseline) for k, v in schedules.items()}}
    write_json(out / "metrics/q1_metrics.json", metrics)
    fallback_observed = any((r.get("mip_gap") or 0) > 0.01 or r["execution_time_seconds"] >= args.time_limit for r in grid_rows)
    summary = {
        "schema_version": 1, "question": "Q1", "round": args.round, "implementation_target": "python",
        "random_seed": args.seed, "approved_decision_id": "q1_method_choice", "methods": method_records,
        "comparison": {"management_grid_file": "tables/q1_management_grid.csv", "metrics_file": "metrics/q1_metrics.json"},
        "fallback_trigger": {"fallback_id": "Q1-F1", "condition": "no feasible incumbent after time limit, gap >1%, or memory >2GB", "observed": fallback_observed, "evidence": "tables/q1_management_grid.csv"},
        "environment": environment(), "input_hashes": {p.name: file_hash(p) for p in (ROOT / "workspace/data_clean").glob("*.csv")},
        "execution_time_seconds": time.perf_counter() - started,
    }
    write_json(out / "run_summary.json", summary)


if __name__ == "__main__":
    main()
