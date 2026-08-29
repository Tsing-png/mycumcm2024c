from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from code.model_common import deterministic_maps, read_data, solve_milp_schedule

GRAIN_CROPS = set(range(6, 17))

data = read_data()
demand, yld, cost, price = deterministic_maps(data)

print(f"{'ρ_g':>5} | {'累计净收益(万元)':>16} | {'Gap':>8} | {'作物数':>5} | {'粮食面积占比':>10} | {'求解(秒)':>8}")
for rho_g in [0.0, 0.1, 0.2, 0.3]:
    schedule, metrics = solve_milp_schedule(
        data, alpha=0.5, demand=demand, yield_map=yld, cost_map=cost, price_map=price,
        min_share=0.1, max_crops=3, grain_min_fraction=rho_g,
    )
    if not metrics["success"]:
        print(f"{rho_g:>5} | 不可行/失败 (status={metrics['status']})")
        continue
    profit = -metrics["objective_minimized"]
    n_crops = schedule[schedule.area_mu > 1e-7].crop_id.nunique()
    grain_area = schedule[schedule.crop_id.isin(GRAIN_CROPS)].area_mu.sum()
    total_area = schedule.area_mu.sum()
    print(
        f"{rho_g:>5} | {profit/1e4:>16.2f} | {metrics['mip_gap']*100:>7.3f}% | "
        f"{n_crops:>5} | {grain_area/total_area*100:>9.1f}% | {metrics['execution_time_seconds']:>7.1f}"
    )
