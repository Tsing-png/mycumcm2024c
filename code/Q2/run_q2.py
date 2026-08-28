from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from code.Q2.q2_scenarios import center, endpoint, generate
from code.Q2.q2_stochastic import solve_shared_scenario_milp
from code.model_common import (
    check_schedule, concentration, environment, evaluate_schedule, file_hash,
    prepare_round, read_data, schedule_overlap, solve_milp_schedule, write_json, write_schedule,
)


def scenario_hash(scenarios: list[dict]) -> str:
    serial = [{f: {"|".join(map(str, k)): v for k, v in sorted(s[f].items())}
               for f in ["demand", "yield", "cost", "price"]} for s in scenarios]
    return hashlib.sha256(json.dumps(serial, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def assess(data, schedule: pd.DataFrame, scenarios: list[dict], alpha: float) -> tuple[dict, np.ndarray]:
    values = np.asarray([evaluate_schedule(data, schedule, alpha, s)["cumulative_profit"] for s in scenarios])
    k = max(1, int(np.ceil(0.05 * len(values))))
    metrics = {
        "mean_profit": float(values.mean()),
        "q05_profit": float(np.quantile(values, 0.05)),
        "lower_tail_mean": float(np.sort(values)[:k].mean()),
        "loss_probability": float(np.mean(values < 0)),
        "minimum_profit": float(values.min()),
        "profit_std": float(values.std()),
    }
    return metrics, values


def draw_figures(out: Path, paired: pd.DataFrame, distributions: dict[tuple[str, float], np.ndarray]) -> list[str]:
    labels = ["Main", "Baseline"]
    half = paired[paired.alpha == 0.5].set_index("method")
    x = np.arange(2)
    width = 0.36
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.bar(x - width / 2, half.loc[labels, "mean_profit"] / 1e6, width, label="Expected profit")
    ax.bar(x + width / 2, half.loc[labels, "lower_tail_mean"] / 1e6, width, label="Worst 5% mean")
    ax.set_xticks(x, labels)
    ax.set_ylabel("Seven-year profit (million yuan)")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    first = out / "figures/q2_expected_tail_comparison.png"
    fig.savefig(first, dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.hist(distributions[("Main", 0.0)] / 1e6, bins=18, alpha=0.58, label="Main, unsold surplus")
    ax.hist(distributions[("Baseline", 0.0)] / 1e6, bins=18, alpha=0.50, label="Baseline, unsold surplus")
    ax.axvline(0, color="black", linewidth=1)
    ax.set_xlabel("Seven-year profit (million yuan)")
    ax.set_ylabel("Scenario count")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    second = out / "figures/q2_loss_risk_comparison.png"
    fig.savefig(second, dpi=220)
    plt.close(fig)
    return [str(first.relative_to(out)), str(second.relative_to(out))]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", default="round2")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--time-limit", type=float, default=300.0)
    args = parser.parse_args()
    started = time.perf_counter()
    data = read_data()
    out = prepare_round("Q2", args.round)
    alpha_train, min_share, max_crops = 0.5, 0.1, 3
    train = generate(data, args.seed, 20, "uniform")
    test = generate(data, args.seed + 1000, 200, "uniform")

    main_schedule, main_solver = solve_shared_scenario_milp(
        data, train, alpha_train, min_share, max_crops, args.time_limit, mip_rel_gap=0.03
    )
    ctr = center(data)
    base_schedule, base_solver = solve_milp_schedule(
        data, alpha_train, ctr["demand"], ctr["yield"], ctr["cost"], ctr["price"],
        min_share, max_crops, args.time_limit,
    )
    schedules = {"Main": main_schedule, "Baseline": base_schedule}
    solvers = {"Main": main_solver, "Baseline": base_solver}
    ids = {"Main": "Q2-M1", "Baseline": "Q2-B1"}
    files = {"Main": "q2_m1_schedule.csv", "Baseline": "q2_b1_schedule.csv"}
    violations = {name: check_schedule(data, schedule) if not schedule.empty else ["empty_schedule"]
                  for name, schedule in schedules.items()}
    for name, schedule in schedules.items():
        write_schedule(out / "tables" / files[name], schedule)

    train_metrics, _ = assess(data, main_schedule, train, alpha_train)
    objective_difference = train_metrics["mean_profit"] - main_solver["sample_mean_objective"]
    objective_ok = abs(objective_difference) <= 1e-5 * max(1.0, abs(train_metrics["mean_profit"]))

    rows, distributions = [], {}
    for alpha in [0.5, 0.0]:
        for name, schedule in schedules.items():
            metrics, values = assess(data, schedule, test, alpha)
            distributions[(name, alpha)] = values
            rows.append({"method": name, "method_id": ids[name], "alpha": alpha, **metrics,
                         **concentration(schedule), "constraint_violations": len(violations[name])})
    paired = pd.DataFrame(rows)
    paired.to_csv(out / "tables/q2_paired_comparison.csv", index=False, encoding="utf-8-sig")

    endpoint_rows = []
    for label in ["adverse", "favorable", "demand_adverse"]:
        scenario = endpoint(data, label)
        for alpha in [0.5, 0.0]:
            for name, schedule in schedules.items():
                profit = evaluate_schedule(data, schedule, alpha, scenario)["cumulative_profit"]
                endpoint_rows.append({"endpoint": label, "alpha": alpha, "method": name, "profit": profit})
    pd.DataFrame(endpoint_rows).to_csv(out / "tables/q2_endpoint_stress.csv", index=False, encoding="utf-8-sig")
    figure_files = draw_figures(out, paired, distributions)

    half_main = paired[(paired.method == "Main") & (paired.alpha == 0.5)].iloc[0]
    unsold_main = paired[(paired.method == "Main") & (paired.alpha == 0.0)].iloc[0]
    endpoint_loss = any(r["method"] == "Main" and r["profit"] < 0 for r in endpoint_rows)
    tail_drop = (half_main.mean_profit - half_main.lower_tail_mean) / abs(half_main.mean_profit)
    fallback = bool(unsold_main.minimum_profit < 0 or endpoint_loss or tail_drop > 0.10)

    metrics = {
        "paired_test": rows,
        "training_objective_verification": {
            "independent_mean_profit": train_metrics["mean_profit"],
            "solver_mean_objective": main_solver["sample_mean_objective"],
            "difference": objective_difference,
            "passed": objective_ok,
        },
        "schedule_overlap": schedule_overlap(main_schedule, base_schedule),
    }
    write_json(out / "metrics/q2_metrics.json", metrics)
    write_json(out / "metrics/q2_solver_metrics.json", solvers)
    write_json(out / "metrics/q2_scenario_config.json", {
        "training": {"count": 20, "seed": args.seed, "shape": "uniform", "hash": scenario_hash(train)},
        "testing": {"count": 200, "seed": args.seed + 1000, "shape": "uniform", "hash": scenario_hash(test)},
        "yearly_changes_are_compounded": True,
    })

    methods = []
    for name in ["Main", "Baseline"]:
        status = "success" if not violations[name] and not schedules[name].empty else "failed"
        if name == "Main" and not objective_ok:
            status = "failed"
        methods.append({
            "method_id": ids[name], "role": "main_candidate" if name == "Main" else "usable_baseline",
            "script": "code/Q2/run_q2.py", "status": status,
            "execution_time_seconds": solvers[name]["execution_time_seconds"],
            "input_files": ["workspace/data_clean/plots.csv", "workspace/data_clean/crops.csv",
                            "workspace/data_clean/planting_2023.csv", "workspace/data_clean/stats_2023.csv",
                            "workspace/data_clean/stats_2023_derived.csv"],
            "output_files": [f"tables/{files[name]}", "tables/q2_paired_comparison.csv",
                             "tables/q2_endpoint_stress.csv"],
            "figure_files": figure_files,
            "metrics_summary": {"solver": solvers[name], "constraint_violations": len(violations[name]),
                                **concentration(schedules[name])},
            "warnings": [] if solvers[name]["success"] else [solvers[name]["message"]],
            "errors": violations[name],
        })
    summary = {
        "schema_version": 1, "question": "Q2", "round": args.round,
        "implementation_target": "python", "random_seed": args.seed,
        "approved_decision_id": "q2_simplified_delivery_contract", "methods": methods,
        "comparison": {"file": "tables/q2_paired_comparison.csv", "metrics": "metrics/q2_metrics.json"},
        "official_template_status": "deferred; main schedule CSV is the canonical fill source",
        "fallback_trigger": {"fallback_id": "Q2-F1", "observed": fallback,
                             "condition": "loss under unsold/endpoint stress or half-price lower-tail drop >10%",
                             "evidence": ["tables/q2_paired_comparison.csv", "tables/q2_endpoint_stress.csv"]},
        "environment": environment(),
        "input_hashes": {p.name: file_hash(p) for p in (ROOT / "workspace/data_clean").glob("*.csv")},
        "execution_time_seconds": time.perf_counter() - started,
    }
    write_json(out / "run_summary.json", summary)
    if any(m["status"] != "success" for m in methods):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
