from __future__ import annotations

import numpy as np

from code.model_common import YEARS


def generate(data, seed: int, n: int, shape: str = "uniform"):
    rng = np.random.default_rng(seed)
    scenarios = []
    categories = data.crops.set_index("crop_id").crop_category.to_dict()
    for _ in range(n):
        demand, yld, cost, price = {}, {}, {}, {}
        demand_level = dict(data.demand0)
        yield_level = {(j, g, s): p["yield"] for (j, g, s), p in data.params.items()}
        price_level = {(j, g, s): p["price"] for (j, g, s), p in data.params.items()}
        for year in YEARS:
            for crop in range(1, 42):
                if shape == "triangular":
                    draw = lambda lo, hi: float(rng.triangular(lo, (lo + hi) / 2, hi))
                else:
                    draw = lambda lo, hi: float(rng.uniform(lo, hi))
                dr = draw(0.05, 0.10) if crop in {6, 7} else draw(-0.05, 0.05)
                demand_level[crop] *= 1 + dr
                demand[(year, crop)] = demand_level[crop]
            for (crop, g, season), p in data.params.items():
                key0 = (crop, g, season)
                yield_level[key0] *= 1 + draw(-0.10, 0.10)
                key = (year, crop, g, season)
                yld[key] = yield_level[key0]
                cost[key] = p["cost"] * (1.05 ** (year - 2023))
                cat = categories[crop]
                if "蔬菜" in cat:
                    price_level[key0] *= 1.05
                elif "食用菌" in cat:
                    decline = 0.05 if crop == 41 else draw(0.01, 0.05)
                    price_level[key0] *= 1 - decline
                else:
                    price_level[key0] = p["price"]
                price[key] = price_level[key0]
        scenarios.append({"demand": demand, "yield": yld, "cost": cost, "price": price})
    return scenarios


def center(data):
    scenarios = generate(data, 2026, 1, "uniform")
    sc = scenarios[0]
    # Replace random quantities by the approved interval midpoints.
    categories = data.crops.set_index("crop_id").crop_category.to_dict()
    demand_level = dict(data.demand0)
    yield_level = {(j, g, s): p["yield"] for (j, g, s), p in data.params.items()}
    for year in YEARS:
        for crop in range(1, 42):
            demand_level[crop] *= 1.075 if crop in {6, 7} else 1.0
            sc["demand"][(year, crop)] = demand_level[crop]
        for (crop, g, season), p in data.params.items():
            key = (year, crop, g, season)
            sc["yield"][key] = yield_level[(crop, g, season)]
            sc["cost"][key] = p["cost"] * 1.05 ** (year - 2023)
            cat = categories[crop]
            if "蔬菜" in cat:
                pf = 1.05 ** (year - 2023)
            elif "食用菌" in cat:
                pf = (0.95 if crop == 41 else 0.97) ** (year - 2023)
            else:
                pf = 1.0
            sc["price"][key] = p["price"] * pf
    return sc


def endpoint(data, kind: str):
    """Build deterministic endpoint scenarios for compact stress testing."""
    if kind not in {"adverse", "favorable", "demand_adverse"}:
        raise ValueError(kind)
    categories = data.crops.set_index("crop_id").crop_category.to_dict()
    demand, yld, cost, price = {}, {}, {}, {}
    demand_level = dict(data.demand0)
    yield_level = {(j, g, s): p["yield"] for (j, g, s), p in data.params.items()}
    price_level = {(j, g, s): p["price"] for (j, g, s), p in data.params.items()}
    for year in YEARS:
        for crop in range(1, 42):
            if crop in {6, 7}:
                growth = 0.05 if kind in {"adverse", "demand_adverse"} else 0.10
            else:
                growth = -0.05 if kind in {"adverse", "demand_adverse"} else 0.05
            demand_level[crop] *= 1 + growth
            demand[(year, crop)] = demand_level[crop]
        for (crop, g, season), p in data.params.items():
            key0 = (crop, g, season)
            yield_growth = -0.10 if kind == "adverse" else (0.10 if kind == "favorable" else 0.0)
            yield_level[key0] *= 1 + yield_growth
            key = (year, crop, g, season)
            yld[key] = yield_level[key0]
            cost[key] = p["cost"] * 1.05 ** (year - 2023)
            cat = categories[crop]
            if "蔬菜" in cat:
                price_level[key0] *= 1.05
            elif "食用菌" in cat:
                decline = 0.05 if crop == 41 or kind == "adverse" else 0.01
                price_level[key0] *= 1 - decline
            else:
                price_level[key0] = p["price"]
            price[key] = price_level[key0]
    return {"demand": demand, "yield": yld, "cost": cost, "price": price}
