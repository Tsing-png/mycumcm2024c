from __future__ import annotations

import time
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

from code.model_common import (
    BEANS,
    SEASON_ORDER,
    YEARS,
    DataBundle,
    allowed,
    initial_bean_area,
    parameter_season,
    previous_crops,
    seasons,
)


def solve_shared_scenario_milp(
    data: DataBundle,
    scenarios: list[dict[str, dict]],
    alpha: float,
    min_share: float,
    max_crops: int,
    time_limit: float,
    mip_rel_gap: float = 0.03,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Solve an extensive-form MILP with shared planting decisions.

    Planting areas x and crop indicators z are common to every scenario.
    Normal-sale quantities q are scenario-specific, so the objective is the
    exact sample mean of the piecewise surplus-sale profit.
    """
    if not scenarios:
        raise ValueError("at least one scenario is required")
    started = time.perf_counter()
    slots = [
        (year, p.plot_id, p.plot_type, season, float(p.area_mu))
        for p in data.plots.itertuples()
        for year in YEARS
        for season in seasons(p.plot_type)
    ]
    vars_x = [
        (si, crop)
        for si, (_, _, ptype, season, _) in enumerate(slots)
        for crop in allowed(ptype, season)
    ]
    nx = len(vars_x)
    xidx = {v: i for i, v in enumerate(vars_x)}
    zidx = {v: nx + i for i, v in enumerate(vars_x)}
    water_modes: dict[tuple[str, int], int] = {}
    cursor = 2 * nx
    for plot in data.plots[data.plots.plot_type == "水浇地"].plot_id:
        for year in YEARS:
            water_modes[(plot, year)] = cursor
            cursor += 1
    qidx: dict[tuple[int, int, int], int] = {}
    for scenario_id in range(len(scenarios)):
        for si, crop in vars_x:
            qidx[(scenario_id, si, crop)] = cursor
            cursor += 1
    nvar = cursor

    objective = np.zeros(nvar)
    lower = np.zeros(nvar)
    upper = np.full(nvar, np.inf)
    integrality = np.zeros(nvar)
    scenario_weight = 1.0 / len(scenarios)
    for si, crop in vars_x:
        year, _, ptype, season, area = slots[si]
        pseason = parameter_season(crop, ptype, season)
        key = (year, crop, ptype, pseason)
        expected_cost = float(np.mean([sc["cost"][key] for sc in scenarios]))
        expected_surplus_revenue = float(
            np.mean([sc["yield"][key] * sc["price"][key] for sc in scenarios])
        )
        objective[xidx[(si, crop)]] = expected_cost - alpha * expected_surplus_revenue
        upper[xidx[(si, crop)]] = area
        upper[zidx[(si, crop)]] = 1.0
        integrality[zidx[(si, crop)]] = 1
        for scenario_id, scenario in enumerate(scenarios):
            q = qidx[(scenario_id, si, crop)]
            objective[q] = -scenario_weight * (1.0 - alpha) * scenario["price"][key]
            upper[q] = area * scenario["yield"][key]
    for mode in water_modes.values():
        upper[mode] = 1.0
        integrality[mode] = 1

    row_ids: list[int] = []
    col_ids: list[int] = []
    values: list[float] = []
    lows: list[float] = []
    highs: list[float] = []

    def add(entries: list[tuple[int, float]], low: float = -np.inf, high: float = np.inf) -> None:
        row = len(lows)
        for col, value in entries:
            row_ids.append(row)
            col_ids.append(col)
            values.append(value)
        lows.append(low)
        highs.append(high)

    for si, (year, plot, ptype, season, area) in enumerate(slots):
        candidates = allowed(ptype, season)
        area_entries = [(xidx[(si, crop)], 1.0) for crop in candidates]
        if ptype == "水浇地" and season == "第二季":
            add(area_entries + [(water_modes[(plot, year)], area)], area, area)
        else:
            add(area_entries, area, area)
        add([(zidx[(si, crop)], 1.0) for crop in candidates], -np.inf, float(max_crops))
        for crop in candidates:
            add([(xidx[(si, crop)], 1.0), (zidx[(si, crop)], -area)], -np.inf, 0.0)
            if min_share > 0:
                add(
                    [(xidx[(si, crop)], 1.0), (zidx[(si, crop)], -min_share * area)],
                    0.0,
                    np.inf,
                )
            pseason = parameter_season(crop, ptype, season)
            key = (year, crop, ptype, pseason)
            for scenario_id, scenario in enumerate(scenarios):
                add(
                    [
                        (qidx[(scenario_id, si, crop)], 1.0),
                        (xidx[(si, crop)], -scenario["yield"][key]),
                    ],
                    -np.inf,
                    0.0,
                )
        if ptype == "水浇地":
            mode = water_modes[(plot, year)]
            if season == "第一季":
                add([(zidx[(si, 16)], 1.0), (mode, -1.0)], -np.inf, 0.0)
                vegetables = [crop for crop in candidates if crop != 16]
                add(
                    [(zidx[(si, crop)], 1.0) for crop in vegetables]
                    + [(mode, float(max_crops))],
                    -np.inf,
                    float(max_crops),
                )
            else:
                add(
                    [(zidx[(si, crop)], 1.0) for crop in candidates] + [(mode, 1.0)],
                    1.0,
                    1.0,
                )

    for scenario_id, scenario in enumerate(scenarios):
        for year in YEARS:
            for crop in range(1, 42):
                entries = [
                    (qidx[(scenario_id, si, crop)], 1.0)
                    for si in range(len(slots))
                    if slots[si][0] == year and (si, crop) in xidx
                ]
                if entries:
                    add(entries, -np.inf, scenario["demand"][(year, crop)])

    by_plot: dict[str, list[int]] = {}
    for si, slot in enumerate(slots):
        by_plot.setdefault(slot[1], []).append(si)
    for plot, sis in by_plot.items():
        sis.sort(key=lambda si: (slots[si][0], SEASON_ORDER[slots[si][3]]))
        first = sis[0]
        for crop in previous_crops(data, plot):
            if (first, crop) in zidx:
                add([(zidx[(first, crop)], 1.0)], 0.0, 0.0)
        for left, right in zip(sis, sis[1:]):
            common = set(allowed(slots[left][2], slots[left][3])) & set(
                allowed(slots[right][2], slots[right][3])
            )
            for crop in common:
                add([(zidx[(left, crop)], 1.0), (zidx[(right, crop)], 1.0)], -np.inf, 1.0)
        area = slots[sis[0]][4]
        initial = initial_bean_area(data, plot)
        entries = [
            (xidx[(si, crop)], 1.0)
            for si in sis
            if 2024 <= slots[si][0] <= 2025
            for crop in set(allowed(slots[si][2], slots[si][3])) & BEANS
        ]
        add(entries, max(0.0, area - initial), np.inf)
        for start in range(2024, 2029):
            entries = [
                (xidx[(si, crop)], 1.0)
                for si in sis
                if start <= slots[si][0] <= start + 2
                for crop in set(allowed(slots[si][2], slots[si][3])) & BEANS
            ]
            add(entries, area, np.inf)

    matrix = coo_matrix(
        (np.asarray(values), (np.asarray(row_ids), np.asarray(col_ids))),
        shape=(len(lows), nvar),
    ).tocsr()
    result = milp(
        objective,
        integrality=integrality,
        bounds=Bounds(lower, upper),
        constraints=LinearConstraint(matrix, np.asarray(lows), np.asarray(highs)),
        options={"time_limit": time_limit, "mip_rel_gap": mip_rel_gap, "presolve": True},
    )
    rows = []
    if result.x is not None:
        for (si, crop), idx in xidx.items():
            area = float(result.x[idx])
            if area > 1e-6:
                year, plot, ptype, season, _ = slots[si]
                rows.append(
                    {
                        "year": year,
                        "season": season,
                        "plot_id": plot,
                        "plot_type": ptype,
                        "crop_id": crop,
                        "area_mu": area,
                    }
                )
    schedule = pd.DataFrame(
        rows, columns=["year", "season", "plot_id", "plot_type", "crop_id", "area_mu"]
    )
    metrics = {
        "success": bool(result.success),
        "status": int(result.status),
        "message": str(result.message),
        "objective_minimized": None if result.fun is None else float(result.fun),
        "sample_mean_objective": None if result.fun is None else float(-result.fun),
        "mip_gap": None if getattr(result, "mip_gap", None) is None else float(result.mip_gap),
        "mip_node_count": None
        if getattr(result, "mip_node_count", None) is None
        else int(result.mip_node_count),
        "mip_rel_gap_target": mip_rel_gap,
        "scenario_count": len(scenarios),
        "variables": nvar,
        "shared_area_variables": nx,
        "shared_binary_variables": nx + len(water_modes),
        "scenario_normal_sale_variables": len(qidx),
        "constraints": len(lows),
        "matrix_nonzeros": int(matrix.nnz),
        "execution_time_seconds": time.perf_counter() - started,
    }
    return schedule, metrics
