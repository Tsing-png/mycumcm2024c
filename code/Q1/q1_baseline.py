from __future__ import annotations

from code.model_common import build_rule_schedule


def run(data):
    return build_rule_schedule(data, {2024, 2027, 2030})
