# Q2 论文写作材料包

状态为 `SIGNED_AND_FROZEN`，冻结时间为 2026-08-28T15:07:22+08:00。论文手使用本文件及同目录 `frozen_numbers.json`。

## 方法与交付

Q2-M1 采用解耦架构。先按题面区间中点构造逐年期望趋势，在半价销售模式下求解唯一面积方案；再把固定方案放入 200 个样本外情景评价平均收益、5% 分位数、最差 5% 平均收益和模拟亏损比例。Q2-B1 使用 2023 基期静态参数，在相同约束和销售模式下生成完整 baseline。方法和交付口径来自 `q2_method_choice` 与 `q2_decoupled_evaluation_contract`。

正式 Excel 为 `results/Q2/deliverables/result2.xlsx`，来源是 `results/Q2/experiments/round3/tables/q2_m1_schedule.csv`。

## 待签署顶层结论

| Claim ID | 数值与单位 | Canonical source | 稳健性与决策依据 | 限制 |
|---|---:|---|---|---|
| `q2_half_main_mean_profit` | 68,971,922.82 元 | `results/Q2/experiments/round3/metrics/q2_metrics.json`，`paired_test[method=Main,alpha=0.5].mean_profit` | `q2_stability_verdict`；五种子平均差均为正 | 仅适用于所设 200 情景概率场 |
| `q2_half_mean_advantage` | 56,788.38 元 | 同文件 Main 与 Baseline 半价均值之差 | 跨五个均匀随机种子方向稳定 | 优势较小，不等于全面风险优势 |
| `q2_half_lower_tail_mean` | 63,177,995.24 元 | 同文件 Main 半价 `.lower_tail_mean` | 下尾下降比例跨种子低于 10% | 配对下尾优势并不跨种子稳定 |
| `q2_unsold_main_mean_profit` | 25,784,546.49 元 | 同文件 `paired_test[method=Main,alpha=0].mean_profit` | 五种子平均差均为正 | 滞销仅作为压力测试，不是正式优化口径 |
| `q2_simulated_loss_probability` | 0 / 200 情景 | 同文件 Main 两种销售模式 `.loss_probability` | 稳健性多种子和端点检查均无负收益 | 不得写成真实亏损概率严格为 0 |
| `q2_hard_constraint_violations` | 0 项 | 同文件 Main `.constraint_violations` | `q2_stability_verdict` | 只覆盖已编码硬约束 |

允许写成：正式方案在测试范围内没有模拟亏损，五个均匀随机种子下平均收益均高于 baseline；半价模式平均优势较小，下尾指标并非全面占优。

不得写成：所有端点均优于 baseline；真实亏损概率为零；Q2-M1 的下尾风险必然低于 baseline。

## 图表与写作入口

- 核心比较图：`paper/figures/q2_expected_tail_comparison.svg`。
- 跨种子图：`paper/figures/q2_seed_mean_profit_difference.svg`。
- 核心表：`paper/tables/q2_risk_metrics.tex`。
- 方法唯一来源：`methods/Q2/q2_final_method_explanation.md`。
- 结果唯一来源：`results/Q2/reports/q2_final_result_analysis.md`。
- 稳健性唯一来源：`robustness/Q2/q2_robustness_report.md`。
