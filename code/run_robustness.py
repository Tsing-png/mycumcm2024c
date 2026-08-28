from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from code.Q2.q2_scenarios import endpoint, generate
from code.Q2.run_q2 import batch_profit, scenario_hash, summarize
from code.Q3.run_q3 import correlated_scenarios, relationship_edges, response_matrix
from code.model_common import check_schedule, concentration, read_data, schedule_overlap, write_json


SEEDS = [3026, 4026, 5026, 6026, 7026]


def q1_summary() -> None:
    source = ROOT / "results/Q1/experiments/round2"
    metrics = json.loads((source / "metrics/q1_metrics.json").read_text())
    rows = metrics["management_grid"]
    checks = []
    for alpha in [0.0, 0.5]:
        subset = [row for row in rows if row["alpha"] == alpha]
        profits = [row["cumulative_profit"] for row in subset]
        top3 = [row["top3_area_share"] for row in subset]
        gaps = [row["mip_gap"] for row in subset]
        threshold = 0.03 if alpha == 0.0 else 0.01
        checks.append({
            "tested_claim": f"Q1 solutions remain feasible and economically similar across the two approved management settings for alpha={alpha}",
            "input_refs": ["results/Q1/experiments/round2/metrics/q1_metrics.json"],
            "perturbation": "Minimum planted share changes from 0 to 0.1 while max crops per plot-season remains 3.",
            "metric_threshold": {"mip_gap_max": threshold, "hard_constraint_violations": 0},
            "observed": {
                "relative_profit_range": (max(profits) - min(profits)) / max(abs(max(profits)), 1.0),
                "top3_area_share_range": [min(top3), max(top3)],
                "maximum_mip_gap": max(gaps),
                "constraint_violations": [row["violations"] for row in subset],
            },
            "status": "PASS" if max(gaps) <= threshold and all(row["violations"] == 0 for row in subset) else "FAIL",
            "limitation": "Only the approved two-point management grid is tested; this is not a continuous threshold sweep.",
            "fallback_trigger_relevance": "Directly tests the formal alpha-specific gap thresholds and feasibility trigger.",
        })
    output = {
        "schema_version": 1,
        "question_id": "Q1",
        "checks": checks,
        "overall_status": "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL",
    }
    write_json(ROOT / "robustness/Q1/q1_robustness_summary.json", output)


def evaluation_record(data, main, baseline, scenarios, alpha: float) -> dict:
    main_values = batch_profit(data, main, scenarios, alpha)
    baseline_values = batch_profit(data, baseline, scenarios, alpha)
    main_metrics = summarize(main_values)
    baseline_metrics = summarize(baseline_values)
    return {
        "alpha": alpha,
        "main": main_metrics,
        "baseline": baseline_metrics,
        "paired_mean_difference": float(np.mean(main_values - baseline_values)),
        "paired_lower_tail_difference": float(np.mean(np.sort(main_values - baseline_values)[:max(1, int(np.ceil(0.05 * len(scenarios))))])),
        "main_tail_drop_ratio": float((main_metrics["mean_profit"] - main_metrics["lower_tail_mean"]) / abs(main_metrics["mean_profit"])),
    }


def q2_summary(data) -> None:
    source = ROOT / "results/Q2/experiments/round3/tables"
    main = pd.read_csv(source / "q2_m1_schedule.csv", encoding="utf-8-sig")
    baseline = pd.read_csv(source / "q2_b1_schedule.csv", encoding="utf-8-sig")
    seed_rows = []
    for seed in SEEDS:
        scenarios = generate(data, seed, 200, "uniform")
        seed_rows.append({
            "seed": seed,
            "scenario_hash": scenario_hash(scenarios),
            "evaluations": [evaluation_record(data, main, baseline, scenarios, alpha) for alpha in [0.5, 0.0]],
        })
    triangular = generate(data, 8026, 200, "triangular")
    distribution_rows = [{
        "shape": "triangular",
        "seed": 8026,
        "scenario_hash": scenario_hash(triangular),
        "evaluations": [evaluation_record(data, main, baseline, triangular, alpha) for alpha in [0.5, 0.0]],
    }]
    endpoint_rows = []
    for kind in ["adverse", "demand_adverse", "favorable"]:
        scenarios = [endpoint(data, kind)]
        endpoint_rows.append({
            "kind": kind,
            "evaluations": [evaluation_record(data, main, baseline, scenarios, alpha) for alpha in [0.5, 0.0]],
        })
    all_evaluations = [evaluation for row in seed_rows + distribution_rows for evaluation in row["evaluations"]]
    no_loss = all(evaluation["main"]["loss_probability"] == 0 for evaluation in all_evaluations)
    tail_ok = all(evaluation["main_tail_drop_ratio"] <= 0.10 for evaluation in all_evaluations if evaluation["alpha"] == 0.5)
    seed_mean_advantage = all(
        evaluation["paired_mean_difference"] > 0
        for row in seed_rows for evaluation in row["evaluations"]
    )
    half_price_tail_advantage = all(
        evaluation["paired_lower_tail_difference"] >= 0
        for row in seed_rows for evaluation in row["evaluations"] if evaluation["alpha"] == 0.5
    )
    endpoint_advantage = all(
        evaluation["paired_mean_difference"] >= 0
        for row in endpoint_rows for evaluation in row["evaluations"]
    )
    constraints_ok = not check_schedule(data, main) and not check_schedule(data, baseline)
    output = {
        "schema_version": 1,
        "question_id": "Q2",
        "tested_claim": "The fixed expected-trend plan remains profitable and avoids excessive half-price lower-tail deterioration under resampling and alternate bounded distributions.",
        "input_refs": [
            "results/Q2/experiments/round3/tables/q2_m1_schedule.csv",
            "results/Q2/experiments/round3/tables/q2_b1_schedule.csv",
            "results/Q2/experiments/round3/run_summary.json",
        ],
        "perturbations": {
            "uniform_seed_stability": SEEDS,
            "alternate_distribution": "triangular with midpoint mode and seed 8026",
            "endpoint_stress": ["adverse", "demand_adverse", "favorable"],
        },
        "predeclared_thresholds": {"loss_probability": 0.0, "half_price_lower_tail_drop_max": 0.10, "hard_constraint_violations": 0},
        "seed_results": seed_rows,
        "distribution_results": distribution_rows,
        "endpoint_results": endpoint_rows,
        "checks": {
            "no_simulated_loss": no_loss,
            "half_price_tail_drop_within_10pct": tail_ok,
            "hard_constraints_pass": constraints_ok,
            "mean_advantage_across_uniform_seeds": seed_mean_advantage,
            "half_price_lower_tail_advantage_across_uniform_seeds": half_price_tail_advantage,
            "advantage_across_all_endpoint_stresses": endpoint_advantage,
        },
        "concentration": {"main": concentration(main), "baseline": concentration(baseline), "schedule_overlap": schedule_overlap(main, baseline)},
        "overall_status": (
            "FAIL" if not (no_loss and tail_ok and constraints_ok) else
            "PASS" if seed_mean_advantage and half_price_tail_advantage and endpoint_advantage else
            "CONDITIONAL"
        ),
        "claim_scope": "The plan is robustly profitable and has a stable small mean advantage under uniform resampling, but it does not robustly dominate the baseline in the half-price lower tail or at every deterministic endpoint.",
        "limitation": "The stress set follows the problem's bounded uncertainty intervals and does not cover shocks outside those intervals.",
        "fallback_trigger_relevance": "Directly tests Q2-F1 loss, lower-tail and feasibility conditions without re-optimizing the plan.",
    }
    write_json(ROOT / "robustness/Q2/q2_robustness_summary.json", output)


def q3_summary(data) -> None:
    source = ROOT / "results/Q3/experiments/round2"
    main = pd.read_csv(source / "tables/q3_m1_medium_schedule.csv", encoding="utf-8-sig")
    baseline = pd.read_csv(ROOT / "results/Q2/experiments/round3/tables/q2_m1_schedule.csv", encoding="utf-8-sig")
    strength_evidence = json.loads((source / "metrics/q3_macro_micro_attribution.json").read_text())
    edges = relationship_edges(data)
    seed_rows = []
    for seed in SEEDS:
        scenarios, corr = correlated_scenarios(data, seed, 200, 0.35, response_matrix(edges, 0.35))
        seed_rows.append({
            "seed": seed,
            "maximum_absolute_correlation_error": corr["maximum_absolute_correlation_error"],
            "positive_definite": corr["positive_definite"],
            "demand_response_clipping_ratio": corr["demand_response_clipping_ratio"],
            "evaluations": [evaluation_record(data, main, baseline, scenarios, alpha) for alpha in [0.5, 0.0]],
        })
    correlation_ok = all(row["positive_definite"] and row["maximum_absolute_correlation_error"] <= 0.08 for row in seed_rows)
    no_loss = all(evaluation["main"]["loss_probability"] == 0 for row in seed_rows for evaluation in row["evaluations"])
    seed_mean_advantage = all(
        evaluation["paired_mean_difference"] > 0
        for row in seed_rows for evaluation in row["evaluations"]
    )
    half_price_tail_advantage = all(
        evaluation["paired_lower_tail_difference"] >= 0
        for row in seed_rows for evaluation in row["evaluations"] if evaluation["alpha"] == 0.5
    )
    constraints_ok = not check_schedule(data, main) and not check_schedule(data, baseline)
    macro_ok = bool(strength_evidence["verdict"] == "equivalent_micro_reallocation" and not strength_evidence["structural_jump_triggered"])
    output = {
        "schema_version": 1,
        "question_id": "Q3",
        "tested_claim": "The medium relationship plan remains numerically valid across random seeds, while weak-to-strong relationship changes preserve macro crop allocation and expected-return structure.",
        "input_refs": [
            "results/Q3/experiments/round2/tables/q3_m1_medium_schedule.csv",
            "results/Q3/experiments/round2/metrics/q3_macro_micro_attribution.json",
            "results/Q3/experiments/round2/run_summary.json",
        ],
        "perturbations": {"medium_scenario_seeds": SEEDS, "relationship_strengths": [0.15, 0.35, 0.55]},
        "predeclared_thresholds": {"maximum_correlation_error": 0.08, "macro_profit_difference": 0.01, "macro_area_similarity": 0.80, "loss_probability": 0.0},
        "seed_results": seed_rows,
        "strength_evidence": strength_evidence,
        "checks": {
            "correlation_mapping_stable": correlation_ok,
            "no_simulated_loss": no_loss,
            "hard_constraints_pass": constraints_ok,
            "macro_strength_stability": macro_ok,
            "mean_advantage_across_seeds": seed_mean_advantage,
            "half_price_lower_tail_advantage_across_seeds": half_price_tail_advantage,
        },
        "overall_status": (
            "FAIL" if not (correlation_ok and no_loss and constraints_ok and macro_ok) else
            "PASS" if seed_mean_advantage and half_price_tail_advantage else
            "CONDITIONAL"
        ),
        "claim_scope": "The relationship-aware plan is macro-stable, profitable and slightly better in mean across seeds, but its half-price lower-tail advantage over the Q2 baseline is not stable.",
        "limitation": "Relationship edges, directions and strength levels remain simulated assumptions rather than empirically estimated elasticities.",
        "fallback_trigger_relevance": "Tests Q3-F1 correlation, feasibility and structural-jump conditions across seeds and relationship strengths.",
    }
    write_json(ROOT / "robustness/Q3/q3_robustness_summary.json", output)


def main() -> None:
    for question in ["Q1", "Q2", "Q3"]:
        (ROOT / "robustness" / question).mkdir(parents=True, exist_ok=True)
    data = read_data()
    q1_summary()
    q2_summary(data)
    q3_summary(data)


if __name__ == "__main__":
    main()
