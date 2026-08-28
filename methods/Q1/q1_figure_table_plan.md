# Q1 图表规划

## 规划原则

Q1 图表只支撑三项已验证结论：主方法在两种销售规则下给出高于规则轮作 baseline 的可行收益；管理阈值变化对收益影响较小；四套主方案均满足正式 Gap 和硬约束要求。销量代理和价格中点的现实有效性不通过图表扩大解释。

| ID | 类型 | 形式 | 核心结论 | 数据源 | 目标位置 | 状态与渲染要求 |
|---|---|---|---|---|---|---|
| Q1-FIG-01 | Type 3 paper | 双面板分组柱状图。左图为滞销模式，右图为半价模式；比较 baseline、`share0_k3`、`share10_k3` 的七年累计净收益 | 两种销售规则下主方法可行收益均高于 baseline，管理阈值切换只造成小幅收益变化 | `results/Q1/experiments/round2/metrics/q1_metrics.json`；baseline 数值来自 `results/Q1/experiments/round2/run_summary.json` | Q1 结果分析 | 待生成。纵轴统一标注“七年累计净收益/万元”，不使用截断纵轴制造差异；冻结后绑定 claim ID |
| Q1-TAB-01 | Type 3 paper | 精简结果表 | 同时给出各配置累计收益、MIP Gap、作物数、$H_1$、$H_3$ 和硬约束违反数，明确滞销 3%、半价 1% 验收口径 | `results/Q1/experiments/round2/metrics/q1_metrics.json` | Q1 结果分析，紧随 Q1-FIG-01 | 已有机器数据，待排版。只保留四个主方法配置和两个 baseline 汇总行 |
| Q1-DEL-01 | 交付表单 | 官方结果 Excel 副本 | 输出两种销售模式的逐年、逐季、逐地块、逐作物面积 | `results/Q1/experiments/round2/tables/q1_m1_alpha0_*_schedule.csv`、`q1_m1_alpha05_*_schedule.csv` | 提交附件，不进入论文正文 | 阻塞于 Q1 正式管理配置签署。不得修改 `workspace/data_raw/` 原模板 |

## 不纳入正文的内容

- 不绘制 54 个地块的完整甘特图，信息密度过低，面积表由 Excel 承担。
- 不把逐年利润曲线作为独立正文图。累计收益比较已足以支持 Q1 核心结论，逐年值可放附录表或材料包。
- 不制作仅展示“约束违反数为 0”的装饰性图，改在 Q1-TAB-01 中列示。

## 结论与决策来源

Type 3 核心结论由 `q1_stability_verdict` 和 `q1_zero_surplus_gap_acceptance` 支持。正式数字冻结前，图表状态保持“待生成/待绑定 frozen claim”。
