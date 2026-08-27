# Q1 Method Card

## Goal and success criteria

在给定 2023 年实际产量作为预期销量、价格区间中点作为基准价格的口径下，分别生成超额产量滞销和按正常价格 50% 销售两套 2024 至 2030 年完整种植方案。首要指标是累计净收益；所有地块容量、适宜性、重茬、三年豆类覆盖、管理便利和模板约束必须满足。

## Human constraints

- Output form: 两个官方模板中的逐年、逐季、逐地块、逐作物面积，以及净收益和可行性核验。
- Priority: 收益优先，风险和管理便利作为约束。
- Unacceptable failure: 方案不可行、利润口径错误、种植面积高度集中或碎片化而未被识别。
- Experiment budget: 标准，包括多参数扰动、敏感性和输出退化检查。

## Shortlist

| ID | Role | Mathematical idea | Why eligible | Main risk | Implementation cost |
|---|---|---|---|---|---|
| Q1-M1 | main_candidate | 跨 7 年混合整数线性规划，以面积、作物出现和正常销量为变量，并线性化两种超额销售规则 | 能统一表达全部跨期约束，给出可行解、最优界和间隙 | 纯收益目标可能造成作物高度集中；完整规模求解时间待验证 | 中等 |
| Q1-B1 | usable_baseline | 约束感知的确定性轮作规则，按地块类型生成完整方案，再用同一收益口径核算 | 已在 54 个地块和完整 7 年上生成合法方案，可提供真实任务下界 | 规则不利用全局收益信息，可能明显偏离最优 | 低 |
| Q1-F1 | conditional_fallback | 带重叠窗口的滚动时域 MILP，并在窗口交界固定或修复轮作和豆类状态 | 保留精确约束骨架，同时降低单次求解规模 | 分解可能损失全局最优性，交界修复需严格核验 | 中等 |

## Baseline validity

- Real task completed: 是。Q1-B1 生成 2024 至 2030 年 574 条地块季次安排，可转换为两份官方模板，并可按两种销售规则核算。
- Comparable output/metric: 与 Q1-M1 使用相同面积表、累计净收益、约束违反数和集中度指标。

## Risk-probe summary

| ID | Executability | Data/assumptions | Degeneracy | Sensitivity | Scale | Verdict |
|---|---|---|---|---|---|---|
| Q1-M1 | 代表性六类地块 MILP 求解成功 | 125 个合法参数组合均有来源；预期销量和中点价格已由人工确认 | 代表性解前三作物面积占 90.72%，需要管理约束 | 收益系数按作物扰动 ±5% 后分配重合度 1.00 | 868 个二元变量、601 条约束用时约 0.03 秒；完整规模仍需限时验证 | CONDITIONAL |
| Q1-B1 | 全量方案无容量、适宜性、重茬或豆类窗口违反 | 使用相同清洗数据和人工口径 | 40 种作物，前三面积占 31.26%，未退化 | 豆类年份平移后仍可行，方案重合度 0.4034 | 574 条安排，探针总用时低于 1 秒 | PASS |

Q1-M1 的条件是正式实验必须比较最小面积或占比与每地块作物种类上限，并报告集中度、可行性和最优间隙。管理阈值不是论文常数，将在探针中按小规模网格筛选。

## Fallback trigger

- Trigger: 完整 Q1-M1 在既定计算环境运行 15 分钟后仍无可行解，或最优间隙超过 1%，或估计峰值内存超过 2 GB。
- Evidence to evaluate: 求解器状态、首个可行解时间、15 分钟间隙、峰值内存、滚动方案与全局上界的差距。

## Compact history

- 2026-08-27: 根据 `q1_baseline_data_conventions`、`global_optimality_framing` 和 `global_experiment_budget` 建立首轮筛选；尚无人工作出方法选择。
- 2026-08-27: 人工通过 `q1_method_choice` 选择 Q1-M1；Q1-B1 保留为必须实现的 baseline，Q1-F1 未激活。
