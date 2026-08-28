# Q1 图表规划

## 规划原则

Q1 图表只支撑三项已验证结论：主方法在两种销售规则下给出高于规则轮作 baseline 的可行收益；管理阈值变化对收益影响较小；四套主方案均满足正式 Gap 和硬约束要求。销量代理和价格中点的现实有效性不通过图表扩大解释。

| ID | 类型 | 形式 | 核心结论 | 数据源 | 目标位置 | 状态与渲染要求 |
|---|---|---|---|---|---|---|
| Q1-FIG-01 | Type 3 paper | 双面板分组柱状图。左图为半价销售模式，右图为滞销模式；比较 baseline、`share0_k3`、`share10_k3` 的七年累计净收益 | 两种销售规则下主方法可行收益均高于 baseline，管理阈值切换只造成小幅收益变化 | `results/Q1/experiments/round2/metrics/q1_metrics.json`；baseline 数值来自 `results/Q1/experiments/round2/run_summary.json` | Q1 结果分析 | 已生成并通过渲染检查：`paper/figures/q1_cumulative_profit_comparison.svg`、`.png` |
| Q1-TAB-01 | Type 3 paper | 精简结果表 | 同时给出各配置累计收益、MIP Gap、作物数、$H_1$、$H_3$ 和硬约束违反数，明确滞销 3%、半价 1% 验收口径 | `results/Q1/experiments/round2/metrics/q1_metrics.json` | Q1 结果分析，紧随 Q1-FIG-01 | 已生成：`paper/tables/q1_core_results.tex`、`.csv` |
| Q1-DEL-01 | 交付表单 | 官方结果 Excel 副本 | 输出两种销售模式的逐年、逐季、逐地块、逐作物面积 | `results/Q1/experiments/round2/tables/q1_m1_alpha0_share0_k3_schedule.csv`、`q1_m1_alpha05_share10_k3_schedule.csv` | 提交附件，不进入论文正文 | 已按 `q1_official_fill_configuration` 生成：`results/Q1/deliverables/result1_1.xlsx`、`result1_2.xlsx`；原始模板未修改 |

## 不纳入正文的内容

- 不绘制 54 个地块的完整甘特图，信息密度过低，面积表由 Excel 承担。
- 不把逐年利润曲线作为独立正文图。累计收益比较已足以支持 Q1 核心结论，逐年值可放附录表或材料包。
- 不制作仅展示“约束违反数为 0”的装饰性图，改在 Q1-TAB-01 中列示。

## 结论与决策来源

Type 3 核心结论由 `q1_stability_verdict` 和 `q1_zero_surplus_gap_acceptance` 支持。材料包已通过 `q1_solution_package_signoff` 签署，正文数字绑定 `results/Q1/reports/frozen_numbers.json`。
