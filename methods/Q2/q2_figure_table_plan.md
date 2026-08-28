# Q2 图表规划

## 规划原则

Q2 图表支撑两层结论：正式方案在测试范围内没有模拟亏损；五个均匀随机种子下平均收益稳定高于 baseline。图表必须同时展示下尾边界，避免把“小幅平均优势”误画成“全面风险优势”。

| ID | 类型 | 形式 | 核心结论 | 数据源 | 目标位置 | 状态与渲染要求 |
|---|---|---|---|---|---|---|
| Q2-FIG-01 | Type 3 paper | 双面板点柱组合图。左图为半价销售模式 $\alpha=0.5$，右图为滞销模式 $\alpha=0$；比较 Main、Baseline 的平均收益、5% 分位数和最差 5% 平均收益 | 正式方案在两种销售口径下均保持正收益；半价销售模式平均收益略高，但下尾并非所有指标都占优 | `results/Q2/experiments/round3/metrics/q2_metrics.json` | Q2 样本外评估 | 已生成并通过渲染检查：`paper/figures/q2_expected_tail_comparison.svg`、`.png` |
| Q2-FIG-02 | Type 3 paper | 五种子配对收益差条形图，双面板对应两种销售规则；零线清晰标示 | 五个均匀随机种子下主方案平均收益均高于 baseline；该结论是跨种子稳定而非单次抽样偶然 | `robustness/Q2/q2_robustness_summary.json` 中 `seed_results[*].evaluations[*].paired_mean_difference` | Q2 稳健性分析 | 已生成并通过渲染检查：`paper/figures/q2_seed_mean_profit_difference.svg`、`.png` |
| Q2-TAB-01 | Type 3 paper | 核心风险指标表 | 精确列示两种销售规则下 Main、Baseline 的平均收益、5% 分位数、下尾均值、最低收益、标准差、亏损概率和约束违反数 | `results/Q2/experiments/round3/metrics/q2_metrics.json` | Q2 结果分析，紧随 Q2-FIG-01 | 已生成：`paper/tables/q2_risk_metrics.tex`、`.csv` |
| Q2-DEL-01 | 交付表单 | `result2.xlsx` 官方模板副本 | 唯一正式 2024 至 2030 年种植面积方案 | `results/Q2/experiments/round3/tables/q2_m1_schedule.csv` | 提交附件，不进入论文正文 | 已生成：`results/Q2/deliverables/result2.xlsx`；保留模板结构且原始模板未修改 |

## 附录候选

端点压力和三角分布结果不单独制作正文图。若正文需要说明边界，可把 `robustness/Q2/q2_robustness_summary.json` 中的端点结果整理为 Type 4 附录表，明确部分端点下 baseline 略高。

## 结论与决策来源

Type 3 核心结论由 `q2_stability_verdict` 支持。允许陈述测试范围内无亏损和跨种子平均收益稳定高于 baseline，不允许通过图形暗示所有下尾或端点均占优。材料包已通过 `q2_solution_package_signoff` 签署，正文数字绑定 `results/Q2/reports/frozen_numbers.json`。
