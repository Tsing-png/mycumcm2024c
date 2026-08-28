from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from code.Q2.q2_scenarios import center, generate
from code.model_common import (
    YEARS, check_schedule, concentration, deterministic_maps, environment,
    evaluate_schedule, file_hash, parameter_season, prepare_round, read_data,
    schedule_overlap, solve_milp_schedule, write_json, write_schedule,
)


def scenario_hash(scenarios: list[dict]) -> str:
    serial = [
        {
            field: {"|".join(map(str, key)): value for key, value in sorted(scenario[field].items())}
            for field in ["demand", "yield", "cost", "price"]
        }
        for scenario in scenarios
    ]
    payload = json.dumps(serial, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def batch_profit(data, schedule: pd.DataFrame, scenarios: list[dict], alpha: float) -> np.ndarray:
    """Evaluate all scenarios in batches while preserving exact price-priority sales."""
    scenario_count = len(scenarios)
    total = np.zeros(scenario_count)
    rows = list(schedule.itertuples())
    for year in YEARS:
        yearly_rows = [row for row in rows if int(row.year) == year]
        cost = np.zeros(scenario_count)
        for row in yearly_rows:
            crop = int(row.crop_id)
            pseason = parameter_season(crop, row.plot_type, row.season)
            key = (year, crop, row.plot_type, pseason)
            cost += float(row.area_mu) * np.fromiter(
                (scenario["cost"][key] for scenario in scenarios), dtype=float, count=scenario_count
            )
        revenue = np.zeros(scenario_count)
        for crop in range(1, 42):
            crop_rows = [row for row in yearly_rows if int(row.crop_id) == crop]
            if not crop_rows:
                continue
            remaining = np.fromiter(
                (scenario["demand"][(year, crop)] for scenario in scenarios),
                dtype=float,
                count=scenario_count,
            )
            batches = []
            for row in crop_rows:
                pseason = parameter_season(crop, row.plot_type, row.season)
                key = (year, crop, row.plot_type, pseason)
                prices = np.fromiter(
                    (scenario["price"][key] for scenario in scenarios), dtype=float, count=scenario_count
                )
                quantities = float(row.area_mu) * np.fromiter(
                    (scenario["yield"][key] for scenario in scenarios), dtype=float, count=scenario_count
                )
                batches.append((prices, quantities))
            price_matrix = np.vstack([batch[0] for batch in batches])
            quantity_matrix = np.vstack([batch[1] for batch in batches])
            order = np.argsort(-price_matrix, axis=0)
            for rank in range(len(batches)):
                cols = np.arange(scenario_count)
                selected = order[rank, cols]
                prices = price_matrix[selected, cols]
                quantities = quantity_matrix[selected, cols]
                normal = np.minimum(quantities, remaining)
                revenue += prices * (normal + alpha * (quantities - normal))
                remaining -= normal
        total += revenue - cost
    return total


def summarize(values: np.ndarray) -> dict[str, float]:
    k = max(1, int(np.ceil(0.05 * len(values))))
    return {
        "mean_profit": float(values.mean()),
        "q05_profit": float(np.quantile(values, 0.05)),
        "lower_tail_mean": float(np.sort(values)[:k].mean()),
        "loss_probability": float(np.mean(values < 0)),
        "minimum_profit": float(values.min()),
        "profit_std": float(values.std()),
    }


def exact_check(data, schedule: pd.DataFrame, scenarios: list[dict], alpha: float, values: np.ndarray) -> dict:
    indices = sorted(set([0, len(scenarios) // 4, len(scenarios) // 2, 3 * len(scenarios) // 4, len(scenarios) - 1]))
    differences = []
    for index in indices:
        exact = evaluate_schedule(data, schedule, alpha, scenarios[index])["cumulative_profit"]
        differences.append(float(values[index] - exact))
    maximum = max(abs(value) for value in differences)
    return {
        "scenario_indices": indices,
        "differences": differences,
        "maximum_absolute_difference": maximum,
        "passed": maximum <= 1e-6,
    }


def solver_acceptable(solver: dict) -> bool:
    gap = solver.get("mip_gap")
    return gap is not None and gap <= 0.01


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", default="round3")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--time-limit", type=float, default=300.0)
    args = parser.parse_args()
    started = time.perf_counter()
    data = read_data()
    out = prepare_round("Q2", args.round)
    alpha_train, min_share, max_crops = 0.5, 0.1, 3

    trend = center(data)
    static_demand, static_yield, static_cost, static_price = deterministic_maps(data)
    main_schedule, main_solver = solve_milp_schedule(
        data, alpha_train, trend["demand"], trend["yield"], trend["cost"], trend["price"],
        min_share, max_crops, args.time_limit,
    )
    baseline_schedule, baseline_solver = solve_milp_schedule(
        data, alpha_train, static_demand, static_yield, static_cost, static_price,
        min_share, max_crops, args.time_limit,
    )
    schedules = {"Main": main_schedule, "Baseline": baseline_schedule}
    solvers = {"Main": main_solver, "Baseline": baseline_solver}
    method_ids = {"Main": "Q2-M1", "Baseline": "Q2-B1"}
    schedule_files = {"Main": "q2_m1_schedule.csv", "Baseline": "q2_b1_schedule.csv"}
    violations = {
        name: check_schedule(data, schedule) if not schedule.empty else ["empty_schedule"]
        for name, schedule in schedules.items()
    }
    for name, schedule in schedules.items():
        write_schedule(out / "tables" / schedule_files[name], schedule)

    test_scenarios = generate(data, args.seed + 1000, 200, "uniform")
    paired_rows = []
    evaluation_checks = {}
    for alpha in [0.5, 0.0]:
        for name, schedule in schedules.items():
            values = batch_profit(data, schedule, test_scenarios, alpha)
            check = exact_check(data, schedule, test_scenarios, alpha, values)
            evaluation_checks[f"{name}_alpha{alpha}"] = check
            paired_rows.append({
                "method": name,
                "method_id": method_ids[name],
                "alpha": alpha,
                **summarize(values),
                **concentration(schedule),
                "constraint_violations": len(violations[name]),
            })
    paired = pd.DataFrame(paired_rows)
    paired.to_csv(out / "tables/q2_paired_comparison.csv", index=False, encoding="utf-8-sig")

    metrics = {
        "paired_test": paired_rows,
        "schedule_overlap": schedule_overlap(main_schedule, baseline_schedule),
        "evaluation_checks": evaluation_checks,
        "test_scenarios": {
            "count": 200,
            "seed": args.seed + 1000,
            "shape": "uniform",
            "hash": scenario_hash(test_scenarios),
        },
    }
    write_json(out / "metrics/q2_metrics.json", metrics)
    write_json(out / "metrics/q2_solver_metrics.json", solvers)

    evaluation_ok = all(check["passed"] for check in evaluation_checks.values())
    methods = []
    for name in ["Main", "Baseline"]:
        success = (
            not schedules[name].empty
            and not violations[name]
            and solver_acceptable(solvers[name])
            and evaluation_ok
        )
        methods.append({
            "method_id": method_ids[name],
            "role": "main_candidate" if name == "Main" else "usable_baseline",
            "script": "code/Q2/run_q2.py",
            "status": "success" if success else "failed",
            "execution_time_seconds": solvers[name]["execution_time_seconds"],
            "input_files": [
                "workspace/data_clean/plots.csv", "workspace/data_clean/crops.csv",
                "workspace/data_clean/planting_2023.csv", "workspace/data_clean/stats_2023.csv",
                "workspace/data_clean/stats_2023_derived.csv",
            ],
            "output_files": [f"tables/{schedule_files[name]}", "tables/q2_paired_comparison.csv"],
            "figure_files": [],
            "metrics_summary": {
                "solver": solvers[name],
                "constraint_violations": len(violations[name]),
                "evaluation_check": evaluation_ok,
                **concentration(schedules[name]),
            },
            "warnings": [] if solvers[name].get("success") else [solvers[name]["message"]],
            "errors": violations[name],
        })

    main_half = paired[(paired.method == "Main") & (paired.alpha == 0.5)].iloc[0]
    main_unsold = paired[(paired.method == "Main") & (paired.alpha == 0.0)].iloc[0]
    tail_drop = (main_half.mean_profit - main_half.lower_tail_mean) / abs(main_half.mean_profit)
    fallback = bool(
        not solver_acceptable(main_solver)
        or main_half.loss_probability > 0
        or main_unsold.loss_probability > 0
        or tail_drop > 0.10
        or not evaluation_ok
    )
    summary = {
        "schema_version": 1,
        "question": "Q2",
        "round": args.round,
        "implementation_target": "python",
        "random_seed": args.seed,
        "approved_decision_id": "q2_decoupled_evaluation_contract",
        "methods": methods,
        "comparison": {
            "file": "tables/q2_paired_comparison.csv",
            "metrics": "metrics/q2_metrics.json",
        },
        "official_template_status": "deferred; q2_m1_schedule.csv is the canonical fill source",
        "fallback_trigger": {
            "fallback_id": "Q2-F1",
            "observed": fallback,
            "condition": "main gap >1%, simulated loss, half-price lower-tail drop >10%, or evaluation mismatch",
            "evidence": ["metrics/q2_solver_metrics.json", "metrics/q2_metrics.json"],
        },
        "environment": environment(),
        "input_hashes": {
            path.name: file_hash(path) for path in (ROOT / "workspace/data_clean").glob("*.csv")
        },
        "execution_time_seconds": time.perf_counter() - started,
    }
    write_json(out / "run_summary.json", summary)
    if any(method["status"] != "success" for method in methods):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
