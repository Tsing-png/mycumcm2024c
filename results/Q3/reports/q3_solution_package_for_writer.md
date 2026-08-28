# Q3 论文写作材料包

状态为 `PENDING_PACKAGE_SIGNOFF`。论文手在签署并生成 `frozen_numbers.json` 后使用本文件。

## 方法范围

Q3-M1 在 Q2 解耦架构上加入作物替代、互补以及销量、亩产量、价格增长的模拟相关结构。中档系数 0.35 是正式代表方案，弱档 0.15 和强档 0.55 用于敏感性分析；关闭关系结构的 Q2 正式方案作为 baseline。方法来自 `q3_method_choice` 与 `q3_decoupled_relation_contract`。

关系边、方向和强度均是透明模拟假设，不是附件数据估计出的市场弹性。Q3 不另交付官方 Excel。

## 待签署顶层结论

| Claim ID | 数值与单位 | Canonical source | 稳健性与决策依据 | 限制 |
|---|---:|---|---|---|
| `q3_medium_half_mean_profit` | 68,870,310.31 元 | `results/Q3/experiments/round2/metrics/q3_metrics.json`，`comparison[strength=medium,alpha=0.5].q3_mean_profit` | `q3_stability_verdict`；五种子平均差均为正 | 模拟关系场下的期望值 |
| `q3_medium_half_mean_advantage` | 121,367.31 元 | 同记录 `.paired_mean_difference` | 跨种子方向稳定 | 优势较小，下尾优势不稳定 |
| `q3_medium_unsold_mean_advantage` | 624,098.35 元 | 同文件 `comparison[strength=medium,alpha=0].paired_mean_difference` | 五种子平均差均为正 | 滞销为压力测试 |
| `q3_medium_simulated_loss_probability` | 0 / 200 情景 | 中档两种销售模式 `.q3_loss_probability` | 五种子均未出现模拟亏损 | 不是真实概率保证 |
| `q3_correlation_error_max` | 0.0353 | `results/Q3/experiments/round2/metrics/q3_correlation_checks.json`，三档 `.maximum_absolute_correlation_error` 最大值 | 阈值 0.08，跨种子最大值仍低于阈值 | 只验证模拟映射的数值实现 |
| `q3_macro_profit_difference_range` | 0.061% 至 0.186% | `results/Q3/experiments/round2/metrics/q3_macro_micro_attribution.json`，`pairwise_checks[*].relative_profit_difference` | `q3_stability_verdict` | 统一中档相关情景下的两两比较 |
| `q3_macro_area_similarity_range` | 94.73% 至 96.63% | 同文件 `pairwise_checks[*].crop_area_vector_similarity` | 高于 80% 判据，不触发结构性 fallback | 反映全乡村 41 维累计面积，不代表逐地块相同 |

允许写成：在模拟关系设定下，中档方案测试范围内无亏损且跨种子平均收益高于 Q2 baseline；弱中强档宏观面积结构稳定，差异主要表现为地块层面的微观平移；关系增强时收益波动和下尾压力上升。

不得写成：模拟关系具有真实因果含义；所有下尾情景均优于 Q2 baseline；真实亏损概率为零。

## 图表与写作入口

- 关系强度图：`paper/figures/q3_relationship_strength_sensitivity.svg`。
- 宏观判据图：`paper/figures/q3_macro_structure_stability.svg`。
- 相关核验附录图：`paper/figures/q3_correlation_matrix_validation.svg`。
- 配对结果表：`paper/tables/q3_medium_q2_comparison.tex`。
- 方法唯一来源：`methods/Q3/q3_final_method_explanation.md`。
- 结果唯一来源：`results/Q3/reports/q3_final_result_analysis.md`。
- 稳健性唯一来源：`robustness/Q3/q3_robustness_report.md`。
