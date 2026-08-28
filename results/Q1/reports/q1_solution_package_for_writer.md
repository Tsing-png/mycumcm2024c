# Q1 论文写作材料包

状态为 `PENDING_PACKAGE_SIGNOFF`。论文手在签署并生成 `frozen_numbers.json` 后使用本文件，不从零散实验目录推断数字。

## 方法与交付

主方法为 `Q1-M1`，即 2024 至 2030 年确定性混合整数线性规划。模型分别求解滞销模式 $\alpha=0$ 与半价销售模式 $\alpha=0.5$，同时满足适种、地块容量、连续重茬、三年豆类覆盖、水浇地模式和管理便利约束。方法选择来自 `q1_method_choice`，假设边界来自 `q1_assumption_necessity`。

人工已通过 `q1_official_fill_configuration` 确认正式交付。`result1_1.xlsx` 使用滞销模式 `share0_k3`，`result1_2.xlsx` 使用半价销售模式 `share10_k3`。填写副本位于 `results/Q1/deliverables/`，原始模板未修改。

## 待签署顶层结论

| Claim ID | 数值与单位 | Canonical source | 稳健性与决策依据 | 限制 |
|---|---:|---|---|---|
| `q1_unsold_official_profit` | 40,417,243.27 元 | `results/Q1/experiments/round2/metrics/q1_metrics.json`，`management_grid[alpha=0,config=share0_k3].cumulative_profit` | `q1_zero_surplus_gap_acceptance`；Q1 稳健性 `PASS` | 是确定性代理口径下的可行收益，不是真实收益保证 |
| `q1_unsold_official_gap` | 2.126% | 同上，`.mip_gap` | 滞销验收线 3%，决策 `q1_zero_surplus_gap_acceptance` | 不得称精确全局最优 |
| `q1_half_official_profit` | 63,510,227.94 元 | `results/Q1/experiments/round2/metrics/q1_metrics.json`，`management_grid[alpha=0.5,config=share10_k3].cumulative_profit` | `q1_official_fill_configuration`；Q1 稳健性 `PASS` | 价格和销量仍是题面代理口径 |
| `q1_half_official_gap` | 0.739% | 同上，`.mip_gap` | 半价验收线 1% | 仅说明最优界较紧 |
| `q1_all_hard_violations` | 0 项 | `results/Q1/experiments/round2/metrics/q1_metrics.json`，四个 `management_grid[*].violations` | `q1_stability_verdict` | 只覆盖已实现的硬约束检查 |

允许写成：两份正式方案均通过硬约束检查；在当前确定性参数口径下，主方法可行累计收益高于规则轮作 baseline；两点管理阈值扰动未造成收益或集中度跳变。

不得写成：现实经营必然获得上述收益；滞销方案已经证明精确全局最优；未测试参数下仍然稳健。

## 图表与写作入口

- 正文图：`paper/figures/q1_cumulative_profit_comparison.svg`。
- 正文表：`paper/tables/q1_core_results.tex`。
- 方法唯一来源：`methods/Q1/q1_final_method_explanation.md`。
- 结果唯一来源：`results/Q1/reports/q1_final_result_analysis.md`。
- 稳健性唯一来源：`robustness/Q1/q1_robustness_report.md`。
