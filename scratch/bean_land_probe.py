from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from code.model_common import BEANS, deterministic_maps, evaluate_schedule, read_data, solve_milp_schedule

data = read_data()
demand, yld, cost, price = deterministic_maps(data)

print(f"{'地力价值β(元/亩)':>13} | {'真实净收益(万元)':>15} | {'豆类面积占比':>11} | {'作物数':>5} | {'求解(秒)':>7}")
for bv in [0, 100, 300, 500, 800]:
    schedule, metrics = solve_milp_schedule(
        data, alpha=0.5, demand=demand, yield_map=yld, cost_map=cost, price_map=price,
        min_share=0.1, max_crops=3, bean_land_value=bv,
    )
    if not metrics["success"]:
        print(f"{bv:>13} | 不可行 (status={metrics['status']})")
        continue
    real = evaluate_schedule(data, schedule, alpha=0.5)
    real_profit = real["cumulative_profit"]
    n_crops = schedule[schedule.area_mu > 1e-7].crop_id.nunique()
    bean_area = schedule[schedule.crop_id.isin(BEANS)].area_mu.sum()
    total_area = schedule.area_mu.sum()
    print(
        f"{bv:>13} | {real_profit/1e4:>15.2f} | {bean_area/total_area*100:>10.1f}% | "
        f"{n_crops:>5} | {metrics['execution_time_seconds']:>6.1f}"
    )
