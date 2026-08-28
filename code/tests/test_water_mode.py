from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from code.model_common import build_rule_schedule, check_schedule, read_data


def main() -> None:
    data = read_data()
    valid = build_rule_schedule(data)
    valid_errors = check_schedule(data, valid)
    assert not valid_errors, valid_errors

    plot = data.plots[data.plots.plot_type == "水浇地"].iloc[0]
    base = valid[~((valid.plot_id == plot.plot_id) & (valid.year == 2024))].copy()

    rice_with_second = pd.concat(
        [base, pd.DataFrame([
            {"year": 2024, "season": "第一季", "plot_id": plot.plot_id, "plot_type": "水浇地", "crop_id": 16, "area_mu": plot.area_mu},
            {"year": 2024, "season": "第二季", "plot_id": plot.plot_id, "plot_type": "水浇地", "crop_id": 35, "area_mu": plot.area_mu},
        ])], ignore_index=True,
    )
    errors = check_schedule(data, rice_with_second)
    assert any(v.startswith("water_mode:rice_with_second:") for v in errors), errors

    two_second_crops = pd.concat(
        [base, pd.DataFrame([
            {"year": 2024, "season": "第一季", "plot_id": plot.plot_id, "plot_type": "水浇地", "crop_id": 17, "area_mu": plot.area_mu},
            {"year": 2024, "season": "第二季", "plot_id": plot.plot_id, "plot_type": "水浇地", "crop_id": 35, "area_mu": plot.area_mu / 2},
            {"year": 2024, "season": "第二季", "plot_id": plot.plot_id, "plot_type": "水浇地", "crop_id": 36, "area_mu": plot.area_mu / 2},
        ])], ignore_index=True,
    )
    errors = check_schedule(data, two_second_crops)
    assert any(v.startswith("water_mode:second_exactly_one:") for v in errors), errors

    print("water_mode_tests: PASS")


if __name__ == "__main__":
    main()
