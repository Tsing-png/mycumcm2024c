from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import ndtr

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from code.Q2.q2_scenarios import center
from code.Q2.run_q2 import batch_profit, exact_check, scenario_hash, summarize
from code.model_common import (
    BEANS, YEARS, allowed, check_schedule, concentration, environment, file_hash,
    prepare_round, read_data, schedule_overlap, seasons, solve_milp_schedule,
    write_json, write_schedule,
)

GROUPS = [
    [1, 2, 3, 4, 5], [6, 7, 8, 9, 10, 11, 14, 15, 16], [12, 13],
    [17, 18, 19], [21, 22, 24, 31], [23, 27, 28, 30, 32, 33, 34],
    [25, 26, 35], [20, 36, 37], [38, 39, 40, 41],
]
STRENGTHS = {"weak": 0.15, "medium": 0.35, "strong": 0.55}


def relationship_edges(data) -> pd.DataFrame:
    rows = []
    for group_id, group in enumerate(GROUPS):
        for left_index, source in enumerate(group):
            for target in group[left_index + 1:]:
                rows.append({"source": source, "target": target, "relation_type": "substitute",
                             "direction": -1, "group": group_id, "source_label": "simulated_assumption"})
    beans = sorted(BEANS)
    nonbeans = [crop for crop in range(1, 42) if crop not in BEANS]
    suitability = {
        crop: {(ptype, season) for ptype in data.plots.plot_type.unique()
               for season in seasons(ptype) if crop in allowed(ptype, season)}
        for crop in range(1, 42)
    }
    for source in beans:
        for target in nonbeans:
            if suitability[source] & suitability[target]:
                rows.append({"source": source, "target": target, "relation_type": "complement",
                             "direction": 1, "group": "rotation", "source_label": "simulated_assumption"})
    return pd.DataFrame(rows)


def response_matrix(edges: pd.DataFrame, strength: float) -> np.ndarray:
    matrix = np.zeros((41, 41))
    for row in edges.itertuples():
        i, j = int(row.source) - 1, int(row.target) - 1
        value = float(row.direction)
        matrix[i, j] += value
        matrix[j, i] += value
    row_scale = np.abs(matrix).sum(axis=1)
    for index in range(41):
        if row_scale[index] > 0:
            matrix[index] *= strength / row_scale[index]
    return matrix


def relation_trend(data, matrix: np.ndarray) -> tuple[dict, dict]:
    scenario = center(data)
    demand = {}
    level = dict(data.demand0)
    base_rate = np.array([0.075 if crop in {6, 7} else 0.0 for crop in range(1, 42)])
    adjusted_rate = base_rate + matrix @ base_rate
    lower = np.array([0.05 if crop in {6, 7} else -0.05 for crop in range(1, 42)])
    upper = np.array([0.10 if crop in {6, 7} else 0.05 for crop in range(1, 42)])
    clipped = np.clip(adjusted_rate, lower, upper)
    for year in YEARS:
        for crop in range(1, 42):
            level[crop] *= 1 + clipped[crop - 1]
            demand[(year, crop)] = level[crop]
    scenario["demand"] = demand
    evidence = {
        "base_annual_rates": base_rate.tolist(),
        "adjusted_annual_rates_before_clipping": adjusted_rate.tolist(),
        "adjusted_annual_rates": clipped.tolist(),
        "clipped_crop_count": int(np.sum(np.abs(clipped - adjusted_rate) > 1e-12)),
        "clipping_ratio": float(np.mean(np.abs(clipped - adjusted_rate) > 1e-12)),
    }
    return scenario, evidence


def target_factor_matrix(strength: float) -> np.ndarray:
    # Demand-price co-movement is positive; higher yield weakly offsets price.
    return np.array([
        [1.0, 0.25 * strength, 0.55 * strength],
        [0.25 * strength, 1.0, -0.20 * strength],
        [0.55 * strength, -0.20 * strength, 1.0],
    ])


def correlated_scenarios(data, seed: int, count: int, strength: float, matrix: np.ndarray):
    rng = np.random.default_rng(seed)
    target = target_factor_matrix(strength)
    chol = np.linalg.cholesky(target)
    raw_factors = rng.standard_normal((count * len(YEARS), 3))
    correlated_factors = raw_factors @ chol.T
    empirical = np.corrcoef(correlated_factors, rowvar=False)
    scenarios = [{"demand": {}, "yield": {}, "cost": {}, "price": {}} for _ in range(count)]
    categories = data.crops.set_index("crop_id").crop_category.to_dict()
    demand_levels = [dict(data.demand0) for _ in range(count)]
    yield_levels = [{key: value["yield"] for key, value in data.params.items()} for _ in range(count)]
    price_levels = [{key: value["price"] for key, value in data.params.items()} for _ in range(count)]
    clipping = 0
    total = 0
    for year_index, year in enumerate(YEARS):
        factors = correlated_factors[year_index * count:(year_index + 1) * count]
        demand_factor = factors[:, 0]
        yield_factor = factors[:, 1]
        price_factor = factors[:, 2]
        demand_shocks = np.zeros((count, 41))
        for crop in range(1, 42):
            idiosyncratic = rng.standard_normal(count)
            latent = np.sqrt(strength) * demand_factor + np.sqrt(1 - strength) * idiosyncratic
            uniform = ndtr(latent)
            low, high = ((0.05, 0.10) if crop in {6, 7} else (-0.05, 0.05))
            demand_shocks[:, crop - 1] = low + (high - low) * uniform
        related = demand_shocks + demand_shocks @ matrix.T
        lower = np.array([0.05 if crop in {6, 7} else -0.05 for crop in range(1, 42)])
        upper = np.array([0.10 if crop in {6, 7} else 0.05 for crop in range(1, 42)])
        clipped = np.clip(related, lower, upper)
        clipping += int(np.sum(np.abs(clipped - related) > 1e-12))
        total += clipped.size
        for scenario_id, scenario in enumerate(scenarios):
            for crop in range(1, 42):
                demand_levels[scenario_id][crop] *= 1 + clipped[scenario_id, crop - 1]
                scenario["demand"][(year, crop)] = demand_levels[scenario_id][crop]
            for key0, base in data.params.items():
                crop, ptype, season = key0
                yield_latent = np.sqrt(strength) * yield_factor[scenario_id] + np.sqrt(1 - strength) * rng.standard_normal()
                yield_growth = -0.10 + 0.20 * ndtr(yield_latent)
                yield_levels[scenario_id][key0] *= 1 + yield_growth
                key = (year, crop, ptype, season)
                scenario["yield"][key] = yield_levels[scenario_id][key0]
                scenario["cost"][key] = base["cost"] * 1.05 ** (year - 2023)
                category = categories[crop]
                if "蔬菜" in category:
                    price_levels[scenario_id][key0] *= 1.05
                elif "食用菌" in category:
                    if crop == 41:
                        decline = 0.05
                    else:
                        price_latent = np.sqrt(strength) * price_factor[scenario_id] + np.sqrt(1 - strength) * rng.standard_normal()
                        decline = 0.01 + 0.04 * ndtr(price_latent)
                    price_levels[scenario_id][key0] *= 1 - decline
                else:
                    price_levels[scenario_id][key0] = base["price"]
                scenario["price"][key] = price_levels[scenario_id][key0]
    check = {
        "target_matrix": target.tolist(),
        "empirical_factor_matrix": empirical.tolist(),
        "minimum_eigenvalue": float(np.linalg.eigvalsh(target).min()),
        "positive_definite": bool(np.linalg.eigvalsh(target).min() > 0),
        "maximum_absolute_correlation_error": float(np.max(np.abs(empirical - target))),
        "demand_response_clipping_ratio": float(clipping / total),
        "cost_driver": "deterministic 5% annual growth; no empirical cost correlation is claimed",
    }
    return scenarios, check


def area_transfer(main: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    left = main.groupby("crop_id").area_mu.sum()
    right = baseline.groupby("crop_id").area_mu.sum()
    crops = sorted(set(left.index) | set(right.index))
    return pd.DataFrame({
        "crop_id": crops,
        "q3_area_mu": [float(left.get(crop, 0.0)) for crop in crops],
        "q2_area_mu": [float(right.get(crop, 0.0)) for crop in crops],
        "area_change_mu": [float(left.get(crop, 0.0) - right.get(crop, 0.0)) for crop in crops],
    })


def solver_ok(solver: dict) -> bool:
    return solver.get("mip_gap") is not None and solver["mip_gap"] <= 0.01


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", default="round2")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--time-limit", type=float, default=300.0)
    args = parser.parse_args()
    started = time.perf_counter()
    data = read_data()
    out = prepare_round("Q3", args.round)
    edges = relationship_edges(data)
    edges.to_csv(out / "tables/q3_relation_edges.csv", index=False, encoding="utf-8-sig")
    baseline_path = ROOT / "results/Q2/experiments/round3/tables/q2_m1_schedule.csv"
    baseline = pd.read_csv(baseline_path, encoding="utf-8-sig")
    baseline_violations = check_schedule(data, baseline)

    schedules, solvers, trend_evidence = {}, {}, {}
    center_maps = center(data)
    for label, strength in STRENGTHS.items():
        matrix = response_matrix(edges, strength)
        trend, evidence = relation_trend(data, matrix)
        schedule, solver = solve_milp_schedule(
            data, 0.5, trend["demand"], center_maps["yield"], center_maps["cost"], center_maps["price"],
            0.1, 3, args.time_limit,
        )
        schedules[label], solvers[label], trend_evidence[label] = schedule, solver, evidence
        if label == "medium":
            write_schedule(out / "tables/q3_m1_medium_schedule.csv", schedule)

    correlation_checks, relation_config = {}, {}
    comparison_rows, strength_rows, evaluation_checks = [], [], {}
    q2_medium_values = {}
    for label, strength in STRENGTHS.items():
        matrix = response_matrix(edges, strength)
        scenarios, corr = correlated_scenarios(data, args.seed + 1000, 200, strength, matrix)
        correlation_checks[label] = {**corr, "scenario_hash": scenario_hash(scenarios), "seed": args.seed + 1000}
        relation_config[label] = {
            "strength": strength, "response_matrix": matrix.tolist(),
            "trend_response": trend_evidence[label], "source_label": "simulated_assumption",
        }
        violations = check_schedule(data, schedules[label]) if not schedules[label].empty else ["empty_schedule"]
        for alpha in [0.5, 0.0]:
            main_values = batch_profit(data, schedules[label], scenarios, alpha)
            base_values = batch_profit(data, baseline, scenarios, alpha)
            main_check = exact_check(data, schedules[label], scenarios, alpha, main_values)
            base_check = exact_check(data, baseline, scenarios, alpha, base_values)
            evaluation_checks[f"{label}_main_alpha{alpha}"] = main_check
            evaluation_checks[f"{label}_q2_alpha{alpha}"] = base_check
            main_metrics, base_metrics = summarize(main_values), summarize(base_values)
            differences = main_values - base_values
            comparison_rows.append({
                "strength": label, "alpha": alpha,
                **{f"q3_{key}": value for key, value in main_metrics.items()},
                **{f"q2_{key}": value for key, value in base_metrics.items()},
                "paired_mean_difference": float(differences.mean()),
                "paired_lower_tail_difference": float(np.sort(differences)[:10].mean()),
                "overlap_with_q2": schedule_overlap(schedules[label], baseline),
                "q3_constraint_violations": len(violations),
            })
            if label == "medium":
                q2_medium_values[alpha] = base_values
        strength_rows.append({
            "strength": label, "coefficient": strength,
            "mip_gap": solvers[label].get("mip_gap"),
            "execution_time_seconds": solvers[label]["execution_time_seconds"],
            "overlap_with_q2": schedule_overlap(schedules[label], baseline),
            "overlap_with_medium": schedule_overlap(schedules[label], schedules["medium"]),
            "clipping_ratio": trend_evidence[label]["clipping_ratio"],
            **concentration(schedules[label]),
            "constraint_violations": len(violations),
        })

    pd.DataFrame(comparison_rows).to_csv(out / "tables/q3_q2_paired_comparison.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(strength_rows).to_csv(out / "tables/q3_strength_comparison.csv", index=False, encoding="utf-8-sig")
    area_transfer(schedules["medium"], baseline).to_csv(
        out / "tables/q3_area_transfer.csv", index=False, encoding="utf-8-sig"
    )
    write_json(out / "metrics/q3_relation_config.json", {
        "groups": GROUPS, "edge_count": int(len(edges)), "strengths": relation_config,
        "response_formula": "annual demand shock plus row-normalized substitute/complement response, clipped to Q2 bounds",
    })
    write_json(out / "metrics/q3_correlation_checks.json", correlation_checks)
    write_json(out / "metrics/q3_solver_metrics.json", solvers)
    write_json(out / "metrics/q3_metrics.json", {
        "comparison": comparison_rows, "strength_sensitivity": strength_rows,
        "evaluation_checks": evaluation_checks,
        "medium_area_overlap_with_q2": schedule_overlap(schedules["medium"], baseline),
    })

    correlations_ok = all(
        item["positive_definite"] and item["maximum_absolute_correlation_error"] <= 0.08
        for item in correlation_checks.values()
    )
    evaluations_ok = all(item["passed"] for item in evaluation_checks.values())
    medium_violations = check_schedule(data, schedules["medium"])
    overlaps_ok = all(row["overlap_with_medium"] >= 0.5 for row in strength_rows)
    half_diffs = [row["paired_mean_difference"] for row in comparison_rows if row["alpha"] == 0.5]
    direction_reversal = min(half_diffs) < 0 < max(half_diffs)
    fallback = bool(
        not correlations_ok or not evaluations_ok or not solver_ok(solvers["medium"])
        or medium_violations or not overlaps_ok or direction_reversal
    )
    medium_success = (
        not schedules["medium"].empty and not medium_violations and solver_ok(solvers["medium"])
        and correlations_ok and evaluations_ok and not baseline_violations
    )
    methods = [{
        "method_id": "Q3-M1", "role": "main_candidate", "script": "code/Q3/run_q3.py",
        "status": "success" if medium_success else "failed",
        "execution_time_seconds": sum(item["execution_time_seconds"] for item in solvers.values()),
        "input_files": ["workspace/data_clean/*.csv", str(baseline_path.relative_to(ROOT))],
        "output_files": ["tables/q3_m1_medium_schedule.csv", "tables/q3_q2_paired_comparison.csv",
                         "tables/q3_strength_comparison.csv", "tables/q3_area_transfer.csv",
                         "tables/q3_relation_edges.csv"],
        "figure_files": [],
        "metrics_summary": {"medium_solver": solvers["medium"], **concentration(schedules["medium"]),
                            "constraint_violations": len(medium_violations)},
        "warnings": ["all relationship and correlation structures are simulated assumptions"],
        "errors": medium_violations,
    }, {
        "method_id": "Q3-B1", "role": "usable_baseline", "script": "code/Q3/run_q3.py",
        "status": "success" if not baseline_violations else "failed", "execution_time_seconds": 0.0,
        "input_files": [str(baseline_path.relative_to(ROOT))], "output_files": [], "figure_files": [],
        "metrics_summary": {**concentration(baseline), "constraint_violations": len(baseline_violations)},
        "warnings": ["reuses the reviewed Q2 Round 3 main schedule with relationship structure disabled"],
        "errors": baseline_violations,
    }]
    summary = {
        "schema_version": 1, "question": "Q3", "round": args.round,
        "implementation_target": "python", "random_seed": args.seed,
        "approved_decision_id": "q3_decoupled_relation_contract", "methods": methods,
        "comparison": {"file": "tables/q3_q2_paired_comparison.csv", "metrics": "metrics/q3_metrics.json"},
        "fallback_trigger": {
            "fallback_id": "Q3-F1", "observed": fallback,
            "condition": "invalid correlation, error >0.08, medium gap >1%, overlap <50%, direction reversal, or evaluation mismatch",
            "components": {"correlations_ok": correlations_ok, "evaluations_ok": evaluations_ok,
                           "cross_strength_overlap_ok": overlaps_ok, "profit_direction_reversal": direction_reversal},
            "evidence": ["metrics/q3_correlation_checks.json", "metrics/q3_metrics.json"],
        },
        "environment": environment(),
        "input_hashes": {path.name: file_hash(path) for path in (ROOT / "workspace/data_clean").glob("*.csv")},
        "q2_baseline_hash": file_hash(baseline_path),
        "execution_time_seconds": time.perf_counter() - started,
    }
    write_json(out / "run_summary.json", summary)
    if any(method["status"] != "success" for method in methods):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
