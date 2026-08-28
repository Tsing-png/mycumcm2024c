from __future__ import annotations

import hashlib
import json
import platform
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix


ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "workspace/data_clean"
YEARS = list(range(2024, 2031))
BEANS = set(range(1, 6)) | set(range(17, 20))
SEASON_ORDER = {"单季": 1, "第一季": 1, "第二季": 2}


@dataclass
class DataBundle:
    plots: pd.DataFrame
    crops: pd.DataFrame
    planting: pd.DataFrame
    stats: pd.DataFrame
    params: dict[tuple[int, str, str], dict[str, float]]
    demand0: dict[int, float]


def read_data() -> DataBundle:
    plots = pd.read_csv(CLEAN / "plots.csv", encoding="utf-8-sig")
    crops = pd.read_csv(CLEAN / "crops.csv", encoding="utf-8-sig")
    planting = pd.read_csv(CLEAN / "planting_2023.csv", encoding="utf-8-sig")
    stats = pd.concat(
        [
            pd.read_csv(CLEAN / "stats_2023.csv", encoding="utf-8-sig"),
            pd.read_csv(CLEAN / "stats_2023_derived.csv", encoding="utf-8-sig"),
        ],
        ignore_index=True,
    )
    stats["price_mid"] = (stats.price_low + stats.price_high) / 2
    params = {
        (int(r.crop_id), str(r.plot_type), str(r.season)): {
            "yield": float(r.yield_jin_per_mu),
            "cost": float(r.cost_yuan_per_mu),
            "price": float(r.price_mid),
        }
        for r in stats.itertuples()
    }
    plot_type = plots.set_index("plot_id").plot_type.to_dict()
    demand0 = {j: 0.0 for j in range(1, 42)}
    for r in planting.itertuples():
        p = params[(int(r.crop_id), plot_type[r.plot_id], str(r.season))]
        demand0[int(r.crop_id)] += float(r.area_mu) * p["yield"]
    if len(plots) != 54 or len(crops) != 41 or len(params) != 125:
        raise ValueError("clean data contract failed")
    return DataBundle(plots, crops, planting, stats, params, demand0)


def seasons(plot_type: str) -> list[str]:
    return ["单季"] if plot_type in {"平旱地", "梯田", "山坡地"} else ["第一季", "第二季"]


def allowed(plot_type: str, season: str) -> list[int]:
    if plot_type in {"平旱地", "梯田", "山坡地"}:
        return list(range(1, 16))
    if plot_type == "水浇地":
        return [16] + list(range(17, 35)) if season == "第一季" else [35, 36, 37]
    if plot_type == "普通大棚":
        return list(range(17, 35)) if season == "第一季" else [38, 39, 40, 41]
    if plot_type == "智慧大棚":
        return list(range(17, 35))
    raise ValueError(plot_type)


def previous_crops(data: DataBundle, plot_id: str) -> set[int]:
    rows = data.planting[data.planting.plot_id == plot_id].copy()
    rows["order"] = rows.season.map(SEASON_ORDER)
    last = rows[rows.order == rows.order.max()]
    return set(last.crop_id.astype(int))


def parameter_season(crop: int, plot_type: str, season: str) -> str:
    if crop == 16 and plot_type == "水浇地" and season == "第一季":
        return "单季"
    return season


def initial_bean_area(data: DataBundle, plot_id: str) -> float:
    rows = data.planting[(data.planting.plot_id == plot_id) & data.planting.crop_id.isin(BEANS)]
    return float(rows.area_mu.sum())


def build_rule_schedule(data: DataBundle, bean_years: set[int] | None = None) -> pd.DataFrame:
    bean_years = bean_years or {2024, 2027, 2030}
    rows: list[dict[str, Any]] = []
    for pi, plot in enumerate(data.plots.itertuples()):
        previous = previous_crops(data, plot.plot_id)
        for yi, year in enumerate(YEARS):
            if plot.plot_type == "水浇地":
                first_pool = [j for j in range(17, 35) if j not in previous]
                if year in bean_years:
                    first_pool = [j for j in first_pool if j in BEANS]
                crop1 = first_pool[(pi + yi) % len(first_pool)]
                rows.append(
                    {"year": year, "season": "第一季", "plot_id": plot.plot_id,
                     "plot_type": plot.plot_type, "crop_id": crop1, "area_mu": float(plot.area_mu)}
                )
                second_pool = [j for j in [35, 36, 37] if j != crop1]
                crop2 = second_pool[(pi + yi) % len(second_pool)]
                rows.append(
                    {"year": year, "season": "第二季", "plot_id": plot.plot_id,
                     "plot_type": plot.plot_type, "crop_id": crop2, "area_mu": float(plot.area_mu)}
                )
                previous = {crop2}
                continue
            for si, season in enumerate(seasons(plot.plot_type)):
                pool = allowed(plot.plot_type, season)
                if season in {"单季", "第一季"} and year in bean_years:
                    beans = [j for j in pool if j in BEANS]
                    if beans:
                        pool = beans
                candidates = [j for j in pool if j not in previous] or pool
                crop = candidates[(pi + yi + si) % len(candidates)]
                rows.append(
                    {"year": year, "season": season, "plot_id": plot.plot_id,
                     "plot_type": plot.plot_type, "crop_id": crop, "area_mu": float(plot.area_mu)}
                )
                previous = {crop}
    return pd.DataFrame(rows)


def check_schedule(data: DataBundle, schedule: pd.DataFrame) -> list[str]:
    violations: list[str] = []
    capacities = data.plots.set_index("plot_id").area_mu.to_dict()
    types = data.plots.set_index("plot_id").plot_type.to_dict()
    for (plot, year, season), group in schedule.groupby(["plot_id", "year", "season"]):
        if group.area_mu.sum() > capacities[plot] + 1e-6:
            violations.append(f"capacity:{plot}:{year}:{season}")
        for crop in group[group.area_mu > 1e-7].crop_id.astype(int):
            if crop not in allowed(types[plot], season):
                violations.append(f"suitability:{plot}:{year}:{season}:{crop}")
    for plot in data.plots.plot_id:
        rows = schedule[(schedule.plot_id == plot) & (schedule.area_mu > 1e-7)].copy()
        rows["so"] = rows.season.map(SEASON_ORDER)
        prev = previous_crops(data, plot)
        ptype = types[plot]
        if ptype == "水浇地":
            for year in YEARS:
                first = rows[(rows.year == year) & (rows.season == "第一季")]
                second = rows[(rows.year == year) & (rows.season == "第二季")]
                first_crops = set(first.crop_id.astype(int))
                second_crops = set(second.crop_id.astype(int))
                if 16 in first_crops:
                    if first_crops != {16}:
                        violations.append(f"water_mode:rice_mixed_first:{plot}:{year}")
                    if second.area_mu.sum() > 1e-7:
                        violations.append(f"water_mode:rice_with_second:{plot}:{year}")
                else:
                    if not first_crops or not first_crops.issubset(set(range(17, 35))):
                        violations.append(f"water_mode:invalid_first_vegetables:{plot}:{year}")
                    if len(second_crops) != 1 or not second_crops.issubset({35, 36, 37}):
                        violations.append(f"water_mode:second_exactly_one:{plot}:{year}")
                    if abs(second.area_mu.sum() - capacities[plot]) > 1e-6:
                        violations.append(f"water_mode:second_area:{plot}:{year}")
        for year in YEARS:
            for season in seasons(ptype):
                so = SEASON_ORDER[season]
                crops = set(rows[(rows.year == year) & (rows.season == season)].crop_id.astype(int))
                common = prev & crops
                for crop in common:
                    violations.append(f"rotation:{plot}:{year}:{so}:{crop}")
                prev = crops
        area = capacities[plot]
        bean_2023_2025 = initial_bean_area(data, plot) + rows[
            (rows.year >= 2024) & (rows.year <= 2025) & rows.crop_id.isin(BEANS)
        ].area_mu.sum()
        if bean_2023_2025 + 1e-6 < area:
            violations.append(f"bean_window:{plot}:2023")
        for start in range(2024, 2029):
            bean_area = rows[(rows.year >= start) & (rows.year <= start + 2) & rows.crop_id.isin(BEANS)].area_mu.sum()
            if bean_area + 1e-6 < area:
                violations.append(f"bean_window:{plot}:{start}")
    return violations


def evaluate_schedule(
    data: DataBundle,
    schedule: pd.DataFrame,
    alpha: float,
    scenario: dict[str, dict[tuple[int, int, str, str], float] | dict[tuple[int, int], float]] | None = None,
) -> dict[str, Any]:
    production_batches: dict[tuple[int, int], list[tuple[float, float]]] = {}
    cost_by_year = {year: 0.0 for year in YEARS}
    for r in schedule.itertuples():
        pseason = parameter_season(int(r.crop_id), r.plot_type, r.season)
        base = data.params[(int(r.crop_id), r.plot_type, pseason)]
        key4 = (int(r.year), int(r.crop_id), r.plot_type, pseason)
        yld = base["yield"] if scenario is None else scenario["yield"][key4]
        cost = base["cost"] if scenario is None else scenario["cost"][key4]
        price = base["price"] if scenario is None else scenario["price"][key4]
        production_batches.setdefault((int(r.year), int(r.crop_id)), []).append((float(r.area_mu) * yld, price))
        cost_by_year[int(r.year)] += float(r.area_mu) * cost
    profit_by_year: dict[int, float] = {}
    for year in YEARS:
        revenue = 0.0
        for crop in range(1, 42):
            demand = data.demand0[crop] if scenario is None else scenario["demand"][(year, crop)]
            remaining_normal = demand
            for quantity, price in sorted(production_batches.get((year, crop), []), key=lambda item: item[1], reverse=True):
                normal = min(quantity, remaining_normal)
                surplus = quantity - normal
                revenue += price * (normal + alpha * surplus)
                remaining_normal -= normal
        profit_by_year[year] = revenue - cost_by_year[year]
    return {"profit_by_year": profit_by_year, "cumulative_profit": float(sum(profit_by_year.values()))}


def concentration(schedule: pd.DataFrame) -> dict[str, Any]:
    by_crop = schedule[schedule.area_mu > 1e-7].groupby("crop_id").area_mu.sum().sort_values(ascending=False)
    shares = by_crop / by_crop.sum()
    return {
        "unique_crop_count": int(len(by_crop)),
        "top1_area_share": float(shares.iloc[0]),
        "top3_area_share": float(shares.iloc[:3].sum()),
        "gini_simpson": float(1 - np.square(shares).sum()),
    }


def schedule_overlap(a: pd.DataFrame, b: pd.DataFrame) -> float:
    keys = ["year", "season", "plot_id", "crop_id"]
    left = a.groupby(keys).area_mu.sum()
    right = b.groupby(keys).area_mu.sum()
    idx = left.index.union(right.index)
    x = left.reindex(idx, fill_value=0).to_numpy()
    y = right.reindex(idx, fill_value=0).to_numpy()
    denom = np.maximum(x, y).sum()
    return float(np.minimum(x, y).sum() / denom) if denom else 1.0


def environment() -> dict[str, Any]:
    import scipy
    return {"python": platform.python_version(), "platform": platform.platform(), "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__}


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_round(question: str, round_name: str = "round1") -> Path:
    root = ROOT / "results" / question / "experiments" / round_name
    for child in ["tables", "metrics", "figures"]:
        (root / child).mkdir(parents=True, exist_ok=True)
    return root


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_schedule(path: Path, schedule: pd.DataFrame) -> None:
    schedule.sort_values(["year", "plot_id", "season", "crop_id"]).to_csv(path, index=False, encoding="utf-8-sig")


def timed() -> float:
    return time.perf_counter()


def solve_milp_schedule(
    data: DataBundle,
    alpha: float,
    demand: dict[tuple[int, int], float],
    yield_map: dict[tuple[int, int, str, str], float],
    cost_map: dict[tuple[int, int, str, str], float],
    price_map: dict[tuple[int, int, str, str], float],
    min_share: float = 0.0,
    max_crops: int = 3,
    time_limit: float = 300.0,
    grain_min_fraction: float = 0.0,
    bean_land_value: float = 0.0,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    started = time.perf_counter()
    mip_rel_gap = 0.03 if alpha == 0.0 else 0.01
    slots: list[tuple[int, str, str, str, float]] = []
    for plot in data.plots.itertuples():
        for year in YEARS:
            for season in seasons(plot.plot_type):
                slots.append((year, plot.plot_id, plot.plot_type, season, float(plot.area_mu)))
    vars_x: list[tuple[int, int]] = []
    for si, slot in enumerate(slots):
        for crop in allowed(slot[2], slot[3]):
            vars_x.append((si, crop))
    nx = len(vars_x)
    xidx = {v: i for i, v in enumerate(vars_x)}
    zidx = {v: nx + i for i, v in enumerate(vars_x)}
    qidx = {v: 2 * nx + i for i, v in enumerate(vars_x)}
    water_modes: dict[tuple[str, int], int] = {}
    cursor = 3 * nx
    for plot in data.plots[data.plots.plot_type == "水浇地"].plot_id:
        for year in YEARS:
            water_modes[(plot, year)] = cursor
            cursor += 1
    nvar = cursor
    objective = np.zeros(nvar)
    lower_bounds = np.zeros(nvar)
    upper_bounds = np.full(nvar, np.inf)
    integrality = np.zeros(nvar)
    for v in vars_x:
        si, crop = v
        year, _, ptype, season, area = slots[si]
        pseason = parameter_season(crop, ptype, season)
        key = (year, crop, ptype, pseason)
        yld, cost, price = yield_map[key], cost_map[key], price_map[key]
        objective[xidx[v]] = cost - alpha * yld * price
        if crop in BEANS:
            objective[xidx[v]] -= bean_land_value
        objective[qidx[v]] = -(1 - alpha) * price
        upper_bounds[xidx[v]] = area
        upper_bounds[zidx[v]] = 1
        integrality[zidx[v]] = 1
        upper_bounds[qidx[v]] = area * yld
    for idx in water_modes.values():
        upper_bounds[idx] = 1
        integrality[idx] = 1
    rows: list[list[tuple[int, float]]] = []
    lows: list[float] = []
    highs: list[float] = []

    def add(entries: list[tuple[int, float]], low: float = -np.inf, high: float = np.inf) -> None:
        rows.append(entries); lows.append(low); highs.append(high)

    for si, slot in enumerate(slots):
        year, plot, ptype, season, area = slot
        candidates = allowed(ptype, season)
        area_entries = [(xidx[(si, j)], 1.0) for j in candidates]
        if ptype == "水浇地" and season == "第二季":
            mode = water_modes[(plot, year)]
            add(area_entries + [(mode, area)], area, area)
        else:
            add(area_entries, area, area)
        add([(zidx[(si, j)], 1.0) for j in candidates], -np.inf, float(max_crops))
        for crop in candidates:
            add([(xidx[(si, crop)], 1.0), (zidx[(si, crop)], -area)], -np.inf, 0.0)
            if min_share > 0:
                add([(xidx[(si, crop)], 1.0), (zidx[(si, crop)], -min_share * area)], 0.0, np.inf)
            pseason = parameter_season(crop, ptype, season)
            key = (year, crop, ptype, pseason)
            add([(qidx[(si, crop)], 1.0), (xidx[(si, crop)], -yield_map[key])], -np.inf, 0.0)
        if ptype == "水浇地":
            mode = water_modes[(plot, year)]
            if season == "第一季":
                add([(zidx[(si, 16)], 1.0), (mode, -1.0)], -np.inf, 0.0)
                veg = [j for j in candidates if j != 16]
                add([(zidx[(si, j)], 1.0) for j in veg] + [(mode, float(max_crops))], -np.inf, float(max_crops))
            else:
                add([(zidx[(si, j)], 1.0) for j in candidates] + [(mode, 1.0)], 1.0, 1.0)
    for year in YEARS:
        for crop in range(1, 42):
            entries = [(qidx[(si, crop)], 1.0) for si in range(len(slots)) if slots[si][0] == year and (si, crop) in qidx]
            if entries:
                add(entries, -np.inf, demand[(year, crop)])
    by_plot: dict[str, list[int]] = {}
    for si, slot in enumerate(slots):
        by_plot.setdefault(slot[1], []).append(si)
    for plot, sis in by_plot.items():
        sis.sort(key=lambda si: (slots[si][0], SEASON_ORDER[slots[si][3]]))
        prior = previous_crops(data, plot)
        first = sis[0]
        for crop in prior:
            if (first, crop) in zidx:
                add([(zidx[(first, crop)], 1.0)], 0.0, 0.0)
        for left, right in zip(sis, sis[1:]):
            for crop in set(allowed(slots[left][2], slots[left][3])) & set(allowed(slots[right][2], slots[right][3])):
                add([(zidx[(left, crop)], 1.0), (zidx[(right, crop)], 1.0)], -np.inf, 1.0)
        area = slots[sis[0]][4]
        initial = initial_bean_area(data, plot)
        entries = []
        for si in sis:
            if 2024 <= slots[si][0] <= 2025:
                for crop in set(allowed(slots[si][2], slots[si][3])) & BEANS:
                    entries.append((xidx[(si, crop)], 1.0))
        add(entries, max(0.0, area - initial), np.inf)
        for start in range(2024, 2029):
            entries = []
            for si in sis:
                if start <= slots[si][0] <= start + 2:
                    for crop in set(allowed(slots[si][2], slots[si][3])) & BEANS:
                        entries.append((xidx[(si, crop)], 1.0))
            add(entries, area, np.inf)
    if grain_min_fraction > 0:
        total_area = sum(slot[4] for slot in slots)
        grain_crops = set(range(6, 17))
        grain_entries = [(xidx[(si, crop)], 1.0) for (si, crop) in vars_x if crop in grain_crops]
        add(grain_entries, grain_min_fraction * total_area, np.inf)
    matrix = lil_matrix((len(rows), nvar))
    for ri, entries in enumerate(rows):
        for ci, val in entries:
            matrix[ri, ci] += val
    result = milp(
        objective,
        integrality=integrality,
        bounds=Bounds(lower_bounds, upper_bounds),
        constraints=LinearConstraint(matrix.tocsr(), np.array(lows), np.array(highs)),
        options={"time_limit": time_limit, "mip_rel_gap": mip_rel_gap, "presolve": True},
    )
    schedule_rows = []
    if result.x is not None:
        for (si, crop), idx in xidx.items():
            value = float(result.x[idx])
            if value > 1e-6:
                year, plot, ptype, season, _ = slots[si]
                schedule_rows.append({"year": year, "season": season, "plot_id": plot, "plot_type": ptype, "crop_id": crop, "area_mu": value})
    schedule = pd.DataFrame(schedule_rows, columns=["year", "season", "plot_id", "plot_type", "crop_id", "area_mu"])
    metrics = {
        "success": bool(result.success), "status": int(result.status), "message": str(result.message),
        "objective_minimized": None if result.fun is None else float(result.fun),
        "mip_gap": None if getattr(result, "mip_gap", None) is None else float(result.mip_gap),
        "mip_node_count": None if getattr(result, "mip_node_count", None) is None else int(result.mip_node_count),
        "mip_rel_gap_target": mip_rel_gap,
        "variables": nvar, "area_variables": nx, "constraints": len(rows),
        "execution_time_seconds": time.perf_counter() - started,
    }
    return schedule, metrics


def deterministic_maps(data: DataBundle) -> tuple[dict, dict, dict, dict]:
    demand = {(year, crop): data.demand0[crop] for year in YEARS for crop in range(1, 42)}
    yld: dict[tuple[int, int, str, str], float] = {}
    cost: dict[tuple[int, int, str, str], float] = {}
    price: dict[tuple[int, int, str, str], float] = {}
    for year in YEARS:
        for (crop, ptype, season), p in data.params.items():
            key = (year, crop, ptype, season)
            yld[key], cost[key], price[key] = p["yield"], p["cost"], p["price"]
    return demand, yld, cost, price
