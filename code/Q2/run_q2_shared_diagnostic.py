from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from code.Q2.q2_scenarios import generate
from code.Q2.q2_stochastic import solve_shared_scenario_milp
from code.model_common import (
    check_schedule,
    concentration,
    environment,
    evaluate_schedule,
    file_hash,
    prepare_round,
    read_data,
    write_json,
    write_schedule,
)


def scenario_hash(scenarios: list[dict]) -> str:
    serializable = []
    for scenario in scenarios:
        serializable.append(
            {
                field: {"|".join(map(str, key)): value for key, value in sorted(scenario[field].items())}
                for field in ["demand", "yield", "cost", "price"]
            }
        )
    payload = json.dumps(serializable, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", default="round_shared20")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--time-limit", type=float, default=300.0)
    args = parser.parse_args()
    started = time.perf_counter()
    data = read_data()
    out = prepare_round("Q2", args.round)
    alpha = 0.5
    min_share = 0.1
    max_crops = 3
    scenarios = generate(data, args.seed, 20, "uniform")
    schedule, solver = solve_shared_scenario_milp(
        data,
        scenarios,
        alpha=alpha,
        min_share=min_share,
        max_crops=max_crops,
        time_limit=args.time_limit,
        mip_rel_gap=0.03,
    )
    violations = check_schedule(data, schedule) if not schedule.empty else ["empty_schedule"]
    profits = np.asarray(
        [evaluate_schedule(data, schedule, alpha, scenario)["cumulative_profit"] for scenario in scenarios]
    ) if not schedule.empty else np.asarray([])
    recomputed_mean = None if profits.size == 0 else float(profits.mean())
    solver_mean = solver["sample_mean_objective"]
    objective_difference = None if recomputed_mean is None or solver_mean is None else recomputed_mean - solver_mean
    objective_check = bool(
        objective_difference is not None
        and abs(objective_difference) <= 1e-5 * max(1.0, abs(recomputed_mean))
    )
    schedule_name = "q2_m1_shared20_alpha05_share10_k3_schedule.csv"
    write_schedule(out / "tables" / schedule_name, schedule)
    verification = {
        "hard_constraint_violations": violations,
        "hard_constraint_check": len(violations) == 0,
        "independent_sample_mean_profit": recomputed_mean,
        "solver_sample_mean_objective": solver_mean,
        "objective_difference": objective_difference,
        "objective_recomputation_check": objective_check,
        "scenario_profit_min": None if profits.size == 0 else float(profits.min()),
        "scenario_profit_max": None if profits.size == 0 else float(profits.max()),
        "scenario_profit_std": None if profits.size == 0 else float(profits.std()),
    }
    write_json(out / "metrics" / "q2_shared20_verification.json", verification)
    write_json(out / "metrics" / "q2_shared20_solver_metrics.json", solver)
    status = "success" if not schedule.empty and not violations and objective_check else "failed"
    summary = {
        "schema_version": 1,
        "question": "Q2",
        "round": args.round,
        "implementation_target": "python",
        "diagnostic_scope": "20-scenario shared-decision extensive-form MILP; one sale rule and one management configuration",
        "random_seed": args.seed,
        "approved_decision_id": "q2_method_choice",
        "scenario_config": {
            "count": 20,
            "shape": "uniform",
            "hash": scenario_hash(scenarios),
        },
        "methods": [
            {
                "method_id": "Q2-M1",
                "role": "main_candidate",
                "script": "code/Q2/run_q2_shared_diagnostic.py",
                "status": status,
                "configuration": {
                    "alpha": alpha,
                    "min_share": min_share,
                    "max_crops": max_crops,
                },
                "execution_time_seconds": solver["execution_time_seconds"],
                "input_files": [
                    "workspace/data_clean/plots.csv",
                    "workspace/data_clean/crops.csv",
                    "workspace/data_clean/planting_2023.csv",
                    "workspace/data_clean/stats_2023.csv",
                    "workspace/data_clean/stats_2023_derived.csv",
                ],
                "output_files": [
                    f"tables/{schedule_name}",
                    "metrics/q2_shared20_verification.json",
                    "metrics/q2_shared20_solver_metrics.json",
                ],
                "metrics_summary": {
                    **solver,
                    **verification,
                    **(concentration(schedule) if not schedule.empty else {}),
                },
                "warnings": [] if solver["success"] else [solver["message"]],
                "errors": violations,
            }
        ],
        "fallback_trigger": {
            "fallback_id": "Q2-F1",
            "observed": False,
            "reason": "not evaluated in this structural diagnostic",
        },
        "environment": environment(),
        "input_hashes": {
            path.name: file_hash(path) for path in (ROOT / "workspace/data_clean").glob("*.csv")
        },
        "execution_time_seconds": time.perf_counter() - started,
    }
    write_json(out / "run_summary.json", summary)
    if status != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
