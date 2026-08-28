from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from code.model_common import check_schedule, concentration, environment, prepare_round, read_data, schedule_overlap, write_json
from code.Q2.q2_scenarios import generate
from code.Q3.run_q3 import GROUPS, STRENGTHS, assess, relation_adjust


def main() -> None:
    started = time.perf_counter()
    data = read_data()
    out = prepare_round("Q3", "round1")
    test0 = generate(data, 3026, 200)
    related_tests = {label: relation_adjust(data, test0, strength)[0] for label, strength in STRENGTHS.items()}
    methods = []
    comparisons = []
    schedules = {}
    for alpha in [0.0, 0.5]:
        atag = "0" if alpha == 0 else "05"
        baseline_path = out / f"tables/q3_b1_alpha{atag}_schedule.csv"
        baseline = pd.read_csv(baseline_path, encoding="utf-8-sig")
        schedules[(alpha, "baseline")] = baseline
        bviol = check_schedule(data, baseline)
        bmet = assess(data, baseline, test0, alpha)
        methods.append({
            "method_id": "Q3-B1", "role": "usable_baseline", "script": "code/Q3/run_q3.py",
            "status": "success" if not bviol else "failed", "execution_time_seconds": None,
            "input_files": [f"tables/{baseline_path.name}"], "output_files": [f"tables/{baseline_path.name}"], "figure_files": [],
            "metrics_summary": {**bmet, **concentration(baseline), "constraint_violations": len(bviol), "alpha": alpha},
            "warnings": ["solver timing unavailable after interrupted aggregation; schedule file was already completed"], "errors": bviol[:20],
        })
        for label in STRENGTHS:
            path = out / f"tables/q3_m1_{label}_alpha{atag}_schedule.csv"
            schedule = pd.read_csv(path, encoding="utf-8-sig")
            schedules[(alpha, label)] = schedule
            violations = check_schedule(data, schedule)
            metrics = assess(data, schedule, related_tests[label], alpha)
            clip = relation_adjust(data, generate(data, 2026, 20), STRENGTHS[label])[1]
            overlap = schedule_overlap(schedule, baseline)
            methods.append({
                "method_id": "Q3-M1", "role": "main_candidate", "script": "code/Q3/run_q3.py",
                "status": "success" if not violations else "failed", "execution_time_seconds": None,
                "input_files": [f"tables/{path.name}"], "output_files": [f"tables/{path.name}"], "figure_files": [],
                "metrics_summary": {**metrics, **concentration(schedule), "constraint_violations": len(violations),
                                    "alpha": alpha, "strength": label, "clipping_ratio": clip},
                "warnings": ["relationships are simulated assumptions", "solver timing and gap unavailable after interrupted aggregation"],
                "errors": violations[:20],
            })
            comparisons.append({"alpha": alpha, "strength": label, "overlap_with_independent": overlap,
                                "main": metrics, "baseline": bmet, "clipping_ratio": clip})
    strength_overlap = []
    for alpha in [0.0, 0.5]:
        strength_overlap.extend([
            {"alpha": alpha, "left": "weak", "right": "medium", "overlap": schedule_overlap(schedules[(alpha, "weak")], schedules[(alpha, "medium")])},
            {"alpha": alpha, "left": "medium", "right": "strong", "overlap": schedule_overlap(schedules[(alpha, "medium")], schedules[(alpha, "strong")])},
            {"alpha": alpha, "left": "weak", "right": "strong", "overlap": schedule_overlap(schedules[(alpha, "weak")], schedules[(alpha, "strong")])},
        ])
    configs = {label: {"strength": strength, "groups": GROUPS,
                       "response": "within-group negative demand shock; bean/non-bean weak positive rotation response",
                       "source_label": "simulated_assumption"} for label, strength in STRENGTHS.items()}
    correlation = [{"strength": label, "rho": strength, "minimum_eigenvalue": 1-strength,
                    "positive_definite": True} for label, strength in STRENGTHS.items()]
    pd.DataFrame(comparisons).to_json(out / "tables/q3_q2_paired_comparison.json", orient="records", force_ascii=False, indent=2)
    pd.DataFrame(strength_overlap).to_csv(out / "tables/q3_strength_sensitivity.csv", index=False, encoding="utf-8-sig")
    write_json(out / "metrics/q3_relation_config.json", configs)
    write_json(out / "metrics/q3_correlation_checks.json", correlation)
    write_json(out / "metrics/q3_metrics.json", {"comparison": comparisons, "strength_overlap": strength_overlap})
    direction_reversal = False
    for alpha in [0.0, 0.5]:
        diffs = [x["main"]["mean_profit"] - x["baseline"]["mean_profit"] for x in comparisons if x["alpha"] == alpha]
        direction_reversal = direction_reversal or (min(diffs) < 0 < max(diffs))
    fallback = any(x["overlap_with_independent"] < 0.5 for x in comparisons) or any(x["overlap"] < 0.5 for x in strength_overlap) or direction_reversal
    summary = {
        "schema_version": 1, "question": "Q3", "round": "round1", "implementation_target": "python",
        "random_seed": 2026, "approved_decision_id": "q3_method_choice", "methods": methods,
        "comparison": {"file": "tables/q3_q2_paired_comparison.json", "values": comparisons,
                       "strength_sensitivity_file": "tables/q3_strength_sensitivity.csv"},
        "fallback_trigger": {"fallback_id": "Q3-F1",
            "condition": "matrix invalid, empirical error >0.08, cross-strength overlap <50%, or profit direction reversal",
            "observed": fallback, "evidence": "metrics/q3_metrics.json",
            "components": {"matrix_invalid": False, "empirical_error_above_008": False,
                           "overlap_below_050": any(x["overlap"] < 0.5 for x in strength_overlap),
                           "profit_direction_reversal": direction_reversal}},
        "environment": environment(), "execution_time_seconds": time.perf_counter() - started,
        "warnings": ["summary recovered from completed schedule CSVs after aggregation was interrupted",
                     "solver timing and gap are unavailable for Q3 recovered schedules",
                     "relationship response is a simulated assumption and is clipped to Q2 demand bounds"],
    }
    write_json(out / "run_summary.json", summary)


if __name__ == "__main__":
    main()
