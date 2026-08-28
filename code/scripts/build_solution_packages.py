from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]


def load(relative_path: str):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def claim(claim_id, value, unit, source_file, source_locator, frozen_at, decision_id):
    return {
        "claim_id": claim_id,
        "value": value,
        "unit": unit,
        "source_file": source_file,
        "source_locator": source_locator,
        "frozen_at": frozen_at,
        "frozen_by_skill": "solution-package-builder",
        "decision_id": decision_id,
    }


def q1_claims(frozen_at):
    source = "results/Q1/experiments/round2/metrics/q1_metrics.json"
    data = load(source)
    rows = {(row["alpha"], row["config"]): row for row in data["management_grid"]}
    unsold = rows[(0.0, "share0_k3")]
    half = rows[(0.5, "share10_k3")]
    decision = "q1_solution_package_signoff"
    return [
        claim("q1_unsold_official_profit", unsold["cumulative_profit"], "CNY", source, "$.management_grid[?(@.alpha==0.0 && @.config=='share0_k3')].cumulative_profit", frozen_at, decision),
        claim("q1_unsold_official_gap", unsold["mip_gap"], "fraction", source, "$.management_grid[?(@.alpha==0.0 && @.config=='share0_k3')].mip_gap", frozen_at, decision),
        claim("q1_half_official_profit", half["cumulative_profit"], "CNY", source, "$.management_grid[?(@.alpha==0.5 && @.config=='share10_k3')].cumulative_profit", frozen_at, decision),
        claim("q1_half_official_gap", half["mip_gap"], "fraction", source, "$.management_grid[?(@.alpha==0.5 && @.config=='share10_k3')].mip_gap", frozen_at, decision),
        claim("q1_all_hard_violations", max(row["violations"] for row in data["management_grid"]), "count", source, "max($.management_grid[*].violations)", frozen_at, decision),
    ]


def q2_claims(frozen_at):
    source = "results/Q2/experiments/round3/metrics/q2_metrics.json"
    data = load(source)
    rows = {(row["method"], row["alpha"]): row for row in data["paired_test"]}
    main_half, base_half = rows[("Main", 0.5)], rows[("Baseline", 0.5)]
    main_unsold = rows[("Main", 0.0)]
    decision = "q2_solution_package_signoff"
    return [
        claim("q2_half_main_mean_profit", main_half["mean_profit"], "CNY", source, "$.paired_test[?(@.method=='Main' && @.alpha==0.5)].mean_profit", frozen_at, decision),
        claim("q2_half_mean_advantage", main_half["mean_profit"] - base_half["mean_profit"], "CNY", source, "difference(Main,Baseline) at alpha=0.5 mean_profit", frozen_at, decision),
        claim("q2_half_lower_tail_mean", main_half["lower_tail_mean"], "CNY", source, "$.paired_test[?(@.method=='Main' && @.alpha==0.5)].lower_tail_mean", frozen_at, decision),
        claim("q2_unsold_main_mean_profit", main_unsold["mean_profit"], "CNY", source, "$.paired_test[?(@.method=='Main' && @.alpha==0.0)].mean_profit", frozen_at, decision),
        claim("q2_simulated_loss_probability", max(main_half["loss_probability"], main_unsold["loss_probability"]), "fraction over 200 scenarios", source, "max(Main loss_probability for alpha in [0.5,0.0])", frozen_at, decision),
        claim("q2_hard_constraint_violations", max(main_half["constraint_violations"], main_unsold["constraint_violations"]), "count", source, "max(Main constraint_violations for alpha in [0.5,0.0])", frozen_at, decision),
    ]


def q3_claims(frozen_at):
    source = "results/Q3/experiments/round2/metrics/q3_metrics.json"
    data = load(source)
    rows = {(row["strength"], row["alpha"]): row for row in data["comparison"]}
    half, unsold = rows[("medium", 0.5)], rows[("medium", 0.0)]
    correlation_source = "results/Q3/experiments/round2/metrics/q3_correlation_checks.json"
    correlations = load(correlation_source)
    macro_source = "results/Q3/experiments/round2/metrics/q3_macro_micro_attribution.json"
    macro = load(macro_source)["pairwise_checks"]
    profit_differences = [row["relative_profit_difference"] for row in macro]
    similarities = [row["crop_area_vector_similarity"] for row in macro]
    decision = "q3_solution_package_signoff"
    return [
        claim("q3_medium_half_mean_profit", half["q3_mean_profit"], "CNY", source, "$.comparison[?(@.strength=='medium' && @.alpha==0.5)].q3_mean_profit", frozen_at, decision),
        claim("q3_medium_half_mean_advantage", half["paired_mean_difference"], "CNY", source, "$.comparison[?(@.strength=='medium' && @.alpha==0.5)].paired_mean_difference", frozen_at, decision),
        claim("q3_medium_unsold_mean_advantage", unsold["paired_mean_difference"], "CNY", source, "$.comparison[?(@.strength=='medium' && @.alpha==0.0)].paired_mean_difference", frozen_at, decision),
        claim("q3_medium_simulated_loss_probability", max(half["q3_loss_probability"], unsold["q3_loss_probability"]), "fraction over 200 scenarios", source, "max(medium q3_loss_probability for alpha in [0.5,0.0])", frozen_at, decision),
        claim("q3_correlation_error_max", max(row["maximum_absolute_correlation_error"] for row in correlations.values()), "correlation coefficient", correlation_source, "max($.*.maximum_absolute_correlation_error)", frozen_at, decision),
        claim("q3_macro_profit_difference_min", min(profit_differences), "fraction", macro_source, "min($.pairwise_checks[*].relative_profit_difference)", frozen_at, decision),
        claim("q3_macro_profit_difference_max", max(profit_differences), "fraction", macro_source, "max($.pairwise_checks[*].relative_profit_difference)", frozen_at, decision),
        claim("q3_macro_area_similarity_min", min(similarities), "fraction", macro_source, "min($.pairwise_checks[*].crop_area_vector_similarity)", frozen_at, decision),
        claim("q3_macro_area_similarity_max", max(similarities), "fraction", macro_source, "max($.pairwise_checks[*].crop_area_vector_similarity)", frozen_at, decision),
    ]


def write_freeze(question: str, claims: list[dict], frozen_at: str) -> None:
    output = ROOT / f"results/{question}/reports/frozen_numbers.json"
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing freeze: {output}")
    payload = {
        "schema_version": 1,
        "question": question,
        "frozen_at": frozen_at,
        "frozen_by_skill": "solution-package-builder",
        "package_signoff_decision_id": f"{question.lower()}_solution_package_signoff",
        "claims": claims,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mark_signed(question: str, frozen_at: str) -> None:
    package = ROOT / f"results/{question}/reports/{question.lower()}_solution_package_for_writer.md"
    text = package.read_text(encoding="utf-8")
    text = text.replace(
        "状态为 `PENDING_PACKAGE_SIGNOFF`。论文手在签署并生成 `frozen_numbers.json` 后使用本文件",
        f"状态为 `SIGNED_AND_FROZEN`，冻结时间为 {frozen_at}。论文手使用本文件及同目录 `frozen_numbers.json`",
        1,
    )
    package.write_text(text, encoding="utf-8")


def main():
    frozen_at = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")
    builders = {"Q1": q1_claims, "Q2": q2_claims, "Q3": q3_claims}
    for question, builder in builders.items():
        write_freeze(question, builder(frozen_at), frozen_at)
        mark_signed(question, frozen_at)
        print(question, "SIGNED_AND_FROZEN")


if __name__ == "__main__":
    main()
