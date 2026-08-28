from __future__ import annotations

from code.model_common import deterministic_maps, solve_milp_schedule


def run(data, alpha: float, min_share: float, max_crops: int, time_limit: float = 300.0):
    demand, yld, cost, price = deterministic_maps(data)
    return solve_milp_schedule(data, alpha, demand, yld, cost, price, min_share, max_crops, time_limit)
