# Q3 图表规划

## 规划原则

Q3 图表必须区分经济结果、宏观结构和相关性验证。关系强度属于模拟设置，图题和图注统一使用“模拟关系强度”，不得写成估计弹性或真实市场相关性。

| ID | 类型 | 形式 | 核心结论 | 数据源 | 目标位置 | 状态与渲染要求 |
|---|---|---|---|---|---|---|
| Q3-FIG-01 | Type 3 paper | 弱、中、强三档敏感性上下双面板图。上图展示平均收益与 5% 分位数，下图展示收益标准差 | 关系强度增强时平均收益变化较小，但收益分布波动和下尾压力增大；三档均未出现模拟亏损 | `results/Q3/experiments/round2/metrics/q3_metrics.json` 中 `comparison` | Q3 关系强度敏感性 | 已生成并通过渲染检查：`paper/figures/q3_relationship_strength_sensitivity.svg`、`.png` |
| Q3-FIG-02 | Type 3 paper | 宏观稳定判据散点图。横轴为 41 维面积相似度，纵轴为相对收益差；绘制 80% 与 1% 判据线 | 三档方案两两比较均落在“收益差低、面积相似度高”的微观等价平移区域，未发生结构性跳变 | `results/Q3/experiments/round2/metrics/q3_macro_micro_attribution.json` | Q3 宏观与微观归因 | 已生成并通过渲染检查：`paper/figures/q3_macro_structure_stability.svg`、`.png` |
| Q3-TAB-01 | Type 3 paper | Q3 中档与 Q2 baseline 的配对指标表 | 在中档相关情景下列示两种销售规则的平均收益、5% 分位数、下尾均值、最低收益、标准差、亏损概率及配对差 | `results/Q3/experiments/round2/tables/q3_q2_paired_comparison.csv` | Q3 与 Q2 深度比较 | 已生成：`paper/tables/q3_medium_q2_comparison.tex`、`.csv` |
| Q3-TAB-02 | Type 4 appendix | 六面板目标与经验相关矩阵热图及精简核验表 | 弱、中、强三档目标矩阵均正定，最终经济变量经验相关误差低于 0.08，方向符合模拟设定 | `results/Q3/experiments/round2/metrics/q3_correlation_checks.json` | 附录，正文简要引用 | 已生成并通过二次渲染检查：`paper/figures/q3_correlation_matrix_validation.svg`、`.png`；表为 `paper/tables/q3_correlation_checks.tex`、`.csv` |

## 不纳入正文的内容

- 不绘制完整替代和互补关系网络。边数量多且均为模拟假设，正文用规则说明，关系边表保留为附录或材料包。
- 不把逐地块方案重合度作为正文主图，因为正式判据已经转为 41 维宏观面积结构。
- 不为零亏损单独画饼图或仪表盘，精确数值由 Q3-TAB-01 给出。

## 结论与决策来源

Type 3 核心结论由 `q3_stability_verdict` 支持，宏观判据由方法卡及 Round 2 的正式归因证据支持。允许陈述跨种子平均收益和宏观结构稳定，不允许暗示下尾全面占优或关系具有真实因果含义。正式数字冻结前，图表状态保持“待生成/待绑定 frozen claim”。
