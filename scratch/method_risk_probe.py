import json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix


ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "workspace/data_clean"
YEARS = list(range(2024, 2031))
BEANS = set(range(1, 6)) | set(range(17, 20))


plots = pd.read_csv(CLEAN / "plots.csv", encoding="utf-8-sig")
crops = pd.read_csv(CLEAN / "crops.csv", encoding="utf-8-sig")
planting = pd.read_csv(CLEAN / "planting_2023.csv", encoding="utf-8-sig")
stats = pd.read_csv(CLEAN / "stats_2023.csv", encoding="utf-8-sig")
derived = pd.read_csv(CLEAN / "stats_2023_derived.csv", encoding="utf-8-sig")

stats["price_mid"] = (stats["price_low"] + stats["price_high"]) / 2
derived["price_mid"] = (derived["price_low"] + derived["price_high"]) / 2
profit = {
    (int(row.crop_id), row.plot_type, row.season):
        float(row.yield_jin_per_mu * row.price_mid - row.cost_yuan_per_mu)
    for row in pd.concat([stats, derived], ignore_index=True).itertuples()
}


def allowed(plot_type, season):
    if plot_type in {"平旱地", "梯田", "山坡地"}:
        return list(range(1, 16))
    if plot_type == "水浇地":
        return list(range(17, 35)) if season == "第一季" else [35, 36, 37]
    if plot_type == "普通大棚":
        return list(range(17, 35)) if season == "第一季" else [38, 39, 40, 41]
    if plot_type == "智慧大棚":
        return list(range(17, 35))
    raise ValueError(plot_type)


def seasons(plot_type):
    return ["单季"] if plot_type in {"平旱地", "梯田", "山坡地"} else ["第一季", "第二季"]


def previous_2023(plot_id):
    rows = planting[planting.plot_id == plot_id]
    order = {"单季": 1, "第一季": 1, "第二季": 2}
    return int(max(rows.itertuples(), key=lambda row: order[row.season]).crop_id)


def choose(pool, forbidden, offset):
    candidates = [crop for crop in pool if crop != forbidden]
    return candidates[offset % len(candidates)]


def build_rule_schedule(bean_years):
    schedule = []
    for plot_index, plot in enumerate(plots.itertuples()):
        previous = previous_2023(plot.plot_id)
        for year_index, year in enumerate(YEARS):
            for season_index, season in enumerate(seasons(plot.plot_type)):
                pool = allowed(plot.plot_type, season)
                if season in {"单季", "第一季"} and year in bean_years:
                    bean_pool = [crop for crop in pool if crop in BEANS]
                    if bean_pool:
                        pool = bean_pool
                crop = choose(pool, previous, plot_index + year_index + season_index)
                schedule.append({
                    "plot_id": plot.plot_id,
                    "plot_type": plot.plot_type,
                    "area_mu": float(plot.area_mu),
                    "year": year,
                    "season": season,
                    "crop_id": crop,
                })
                previous = crop
    return pd.DataFrame(schedule)


def check_schedule(schedule):
    violations = []
    grouped = schedule.groupby(["plot_id", "year", "season"]).area_mu.sum()
    capacities = plots.set_index("plot_id").area_mu.to_dict()
    for (plot_id, year, season), area in grouped.items():
        if area > capacities[plot_id] + 1e-9:
            violations.append(f"capacity:{plot_id}:{year}:{season}")
    for plot in plots.itertuples():
        rows = schedule[schedule.plot_id == plot.plot_id].copy()
        season_order = {"单季": 1, "第一季": 1, "第二季": 2}
        rows["season_order"] = rows.season.map(season_order)
        rows = rows.sort_values(["year", "season_order"])
        previous = previous_2023(plot.plot_id)
        for row in rows.itertuples():
            if row.crop_id == previous:
                violations.append(f"rotation:{plot.plot_id}:{row.year}:{row.season}")
            if row.crop_id not in allowed(plot.plot_type, row.season):
                violations.append(f"suitability:{plot.plot_id}:{row.year}:{row.season}")
            previous = row.crop_id
        for start in range(2024, 2029):
            window = rows[(rows.year >= start) & (rows.year <= start + 2)]
            bean_area = window[window.crop_id.isin(BEANS)].area_mu.sum()
            if bean_area + 1e-9 < plot.area_mu:
                violations.append(f"bean_window:{plot.plot_id}:{start}")
    return violations


def concentration(schedule):
    area_by_crop = schedule.groupby("crop_id").area_mu.sum().sort_values(ascending=False)
    total = area_by_crop.sum()
    shares = area_by_crop / total
    return {
        "unique_crop_count": int(len(area_by_crop)),
        "top1_area_share": round(float(shares.iloc[0]), 4),
        "top3_area_share": round(float(shares.iloc[:3].sum()), 4),
        "gini_simpson": round(float(1 - np.square(shares).sum()), 4),
    }


def representative_milp():
    started = time.perf_counter()
    representatives = plots.groupby("plot_type", sort=False).first().reset_index()
    slots = []
    for plot in representatives.itertuples():
        for year in YEARS:
            for season in seasons(plot.plot_type):
                slots.append((plot.plot_id, plot.plot_type, float(plot.area_mu), year, season))
    variables = []
    for slot_index, slot in enumerate(slots):
        for crop_id in allowed(slot[1], slot[4]):
            variables.append((slot_index, crop_id))
    index = {item: idx for idx, item in enumerate(variables)}
    rows = []
    lower = []
    upper = []
    for slot_index, slot in enumerate(slots):
        entries = [(index[(slot_index, crop)], 1.0) for crop in allowed(slot[1], slot[4])]
        rows.append(entries); lower.append(1.0); upper.append(1.0)
    by_plot = defaultdict(list)
    for slot_index, slot in enumerate(slots):
        by_plot[slot[0]].append(slot_index)
    for plot_id, slot_indices in by_plot.items():
        for left, right in zip(slot_indices, slot_indices[1:]):
            common = set(allowed(slots[left][1], slots[left][4])) & set(allowed(slots[right][1], slots[right][4]))
            for crop in common:
                rows.append([(index[(left, crop)], 1.0), (index[(right, crop)], 1.0)])
                lower.append(-np.inf); upper.append(1.0)
        first = slot_indices[0]
        prior = previous_2023(plot_id)
        if (first, prior) in index:
            rows.append([(index[(first, prior)], 1.0)])
            lower.append(0.0); upper.append(0.0)
        for start in range(2024, 2029):
            entries = []
            for slot_index in slot_indices:
                if start <= slots[slot_index][3] <= start + 2:
                    for crop in set(allowed(slots[slot_index][1], slots[slot_index][4])) & BEANS:
                        entries.append((index[(slot_index, crop)], slots[slot_index][2]))
            rows.append(entries); lower.append(slots[slot_indices[0]][2]); upper.append(np.inf)
    matrix = lil_matrix((len(rows), len(variables)))
    for row_index, entries in enumerate(rows):
        for column_index, value in entries:
            matrix[row_index, column_index] = value
    objective = np.zeros(len(variables))
    for idx, (slot_index, crop_id) in enumerate(variables):
        slot = slots[slot_index]
        objective[idx] = -profit[(crop_id, slot[1], slot[4])] * slot[2]
    constraints = LinearConstraint(matrix.tocsr(), np.array(lower), np.array(upper))
    solve_args = {
        "integrality": np.ones(len(variables)),
        "bounds": Bounds(0, 1),
        "constraints": constraints,
        "options": {"time_limit": 20},
    }
    result = milp(objective, **solve_args)
    selected = [(slots[slot_index], crop_id) for (slot_index, crop_id), value in zip(variables, result.x) if value > 0.5]
    area_by_crop = defaultdict(float)
    for slot, crop_id in selected:
        area_by_crop[crop_id] += slot[2]
    shares = np.array(sorted(area_by_crop.values(), reverse=True)) / sum(area_by_crop.values())
    perturbation = np.array([1 + 0.05 * np.sin(crop_id) for _, crop_id in variables])
    perturbed_result = milp(objective * perturbation, **solve_args)
    selected_indices = {idx for idx, value in enumerate(result.x) if value > 0.5}
    perturbed_indices = {idx for idx, value in enumerate(perturbed_result.x) if value > 0.5}
    overlap = len(selected_indices & perturbed_indices) / len(selected_indices | perturbed_indices)
    return {
        "status": "PASS" if result.success and len(selected) == len(slots) else "FAIL",
        "solver_status": int(result.status),
        "representative_plots": int(len(representatives)),
        "slots": int(len(slots)),
        "binary_variables": int(len(variables)),
        "constraints": int(len(rows)),
        "runtime_seconds": round(time.perf_counter() - started, 4),
        "selected_slots": int(len(selected)),
        "output_degeneracy": {
            "unique_crop_count": int(len(area_by_crop)),
            "top1_area_share": round(float(shares[0]), 4),
            "top3_area_share": round(float(shares[:3].sum()), 4),
            "gini_simpson": round(float(1 - np.square(shares).sum()), 4),
        },
        "profit_coefficient_perturbation": {
            "magnitude": "+/-5% deterministic crop-wise",
            "perturbed_solver_status": int(perturbed_result.status),
            "assignment_jaccard_overlap": round(float(overlap), 4),
            "status": "PASS" if perturbed_result.success else "FAIL",
        },
    }


def scenario_probe():
    seed_means = []
    tail_means = []
    for seed in [17, 29, 43, 71, 101]:
        rng = np.random.default_rng(seed)
        demand = rng.uniform(0.95, 1.10, size=(200, 41))
        yield_factor = rng.uniform(0.90, 1.10, size=(200, 41))
        price_factor = rng.uniform(0.95, 1.05, size=(200, 41))
        cost_factor = rng.uniform(1.03, 1.06, size=(200, 41))
        score = (demand * yield_factor * price_factor / cost_factor).mean(axis=1)
        seed_means.append(float(score.mean()))
        tail_means.append(float(np.sort(score)[:10].mean()))
    return {
        "replications_per_seed": 200,
        "seeds": [17, 29, 43, 71, 101],
        "mean_score_cv_across_seeds": round(float(np.std(seed_means) / np.mean(seed_means)), 6),
        "lower_5pct_score_cv_across_seeds": round(float(np.std(tail_means) / np.mean(tail_means)), 6),
        "distribution_status": "CONDITIONAL",
        "condition": "Uniform draws are a transparent probe convention, not observed probability laws; endpoint and alternative-shape sensitivity remains mandatory.",
    }


def correlation_probe():
    results = []
    dimension = 12
    for strength in [0.15, 0.35, 0.55]:
        correlation = np.full((dimension, dimension), strength)
        np.fill_diagonal(correlation, 1.0)
        eigen_min = float(np.linalg.eigvalsh(correlation).min())
        rng = np.random.default_rng(2024)
        samples = rng.multivariate_normal(np.zeros(dimension), correlation, size=2000)
        empirical = np.corrcoef(samples, rowvar=False)
        error = float(np.max(np.abs(empirical - correlation)))
        results.append({
            "strength": strength,
            "minimum_eigenvalue": round(eigen_min, 6),
            "max_empirical_correlation_error": round(error, 4),
            "status": "PASS" if eigen_min >= -1e-10 and error < 0.08 else "FAIL",
        })
    return results


started = time.perf_counter()
baseline = build_rule_schedule({2024, 2027, 2030})
perturbed = build_rule_schedule({2025, 2028})
baseline_violations = check_schedule(baseline)
perturbed_violations = check_schedule(perturbed)
baseline_keys = set(zip(baseline.plot_id, baseline.year, baseline.season, baseline.crop_id))
perturbed_keys = set(zip(perturbed.plot_id, perturbed.year, perturbed.season, perturbed.crop_id))

evidence = {
    "generated_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
    "data_rows": {
        "plots": int(len(plots)),
        "crops": int(len(crops)),
        "statistics_observed": int(len(stats)),
        "statistics_derived": int(len(derived)),
        "planting_2023": int(len(planting)),
    },
    "full_horizon_rule_baseline": {
        "schedule_rows": int(len(baseline)),
        "violations": baseline_violations,
        "status": "PASS" if not baseline_violations else "FAIL",
        "concentration": concentration(baseline),
    },
    "management_timing_perturbation": {
        "bean_years_base": [2024, 2027, 2030],
        "bean_years_perturbed": [2025, 2028],
        "perturbed_violations": perturbed_violations,
        "schedule_overlap": round(len(baseline_keys & perturbed_keys) / len(baseline_keys | perturbed_keys), 4),
        "base_concentration": concentration(baseline),
        "perturbed_concentration": concentration(perturbed),
        "status": "PASS" if not perturbed_violations else "FAIL",
    },
    "representative_exact_milp": representative_milp(),
    "uncertainty_scenario_probe": scenario_probe(),
    "correlation_structure_probe": correlation_probe(),
    "estimated_full_formulation": {
        "area_variables_upper_bound": 54 * 2 * 7 * 41,
        "binary_variables_upper_bound": 54 * 2 * 7 * 41,
        "note": "Actual count is smaller after removing incompatible plot-season-crop combinations; scenario expansion should reuse here-and-now planting variables.",
    },
    "runtime_seconds": round(time.perf_counter() - started, 4),
}

output = ROOT / "scratch/method_risk_probe_evidence.json"
output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(evidence, ensure_ascii=False, indent=2))
