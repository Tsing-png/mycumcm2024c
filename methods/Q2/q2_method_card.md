# Q2 Method Card

## Goal and success criteria

在题面给出的销量、亩产量、成本和价格变化范围内生成 2024 至 2030 年完整方案，分别比较超额产量滞销和按正常价格 50% 销售。首要目标是期望累计净收益，同时识别极端亏损、不可行和高度集中风险。

## Human constraints

- Output form: 官方 Q2 模板所需完整面积方案，以及两种销售规则下的期望收益、尾部损失和集中度比较。
- Priority: 收益优先，尾部风险作为约束或显式报告项。
- Unacceptable failure: 极端亏损、方案在任一参数情景下违反物理约束、或高度集中而无告警。
- Experiment budget: 标准，包括 5 个随机种子、端点情景、参数敏感性和退化检查。

## Shortlist

| ID | Role | Mathematical idea | Why eligible | Main risk | Implementation cost |
|---|---|---|---|---|---|
| Q2-M1 | main_candidate | 样本平均近似的情景随机 MILP，共享种植决策，最大化情景平均净收益并限制或报告下尾损失 | 与收益优先和风险约束一致，可在相同情景下比较两种销售规则 | 题面没有概率分布；场景设定可能主导方案 | 中高 |
| Q2-B1 | usable_baseline | 按题面变化范围的中心路径建立确定性跨期 MILP，再在与主方法相同的随机和端点情景上事后评估 | 完成同一逐地块任务，保留 Q1 的精确约束骨架，比较清晰 | 中心路径可能低估尾部风险，也可能高度集中 | 中等 |
| Q2-F1 | conditional_fallback | 预算不确定集下的鲁棒 MILP，以可解释的不利偏离预算控制最坏损失 | 不依赖精确概率分布，适合场景结论不稳定时启用 | 可能过度保守，收益损失取决于不确定预算 | 中高 |

## Baseline validity

- Real task completed: 是。Q2-B1 输出同一 2024 至 2030 年地块季次面积表，并分别应用两种销售规则。
- Comparable output/metric: 与 Q2-M1 在同一测试情景上比较期望累计净收益、5% 下尾收益、亏损情景比例、约束违反数和面积集中度。

## Risk-probe summary

| ID | Executability | Data/assumptions | Degeneracy | Sensitivity | Scale | Verdict |
|---|---|---|---|---|---|---|
| Q2-M1 | 共享约束骨架的代表性 MILP 可执行；200 情景可重复生成 | 题面范围覆盖完整，但均匀抽样只是透明探针约定，不是实证分布 | 继承精确收益模型的集中风险，必须加入管理约束并报告 top-k 占比 | 5 个种子下均值 CV 0.000902、下尾 CV 0.002057；仍须做端点与替代分布形状 | 种植变量不随情景复制；收益辅助变量随场景增长，需做 100/200/500 场景规模测试 | CONDITIONAL |
| Q2-B1 | 代表性确定性 MILP 求解成功 | 中心路径由题面范围构造，须明确标为假设 | 代表性精确解前三作物面积占 90.72%，管理阈值不可省略 | 收益系数 ±5% 扰动后代表性分配稳定，但需在全量方案复核 | 代表性 868 个二元变量、601 条约束约 0.03 秒 | CONDITIONAL |

Q2-M1 和 Q2-B1 均可进入人工选择，但条件是所有随机分布只作为情景假设，并同时运行端点压力测试；两者必须使用相同测试情景和销售规则。

## Fallback trigger

- Trigger: 主方法在替代分布或端点情景下的 5% 下尾收益变化超过中心估计的 10%，或推荐种植面积的跨设定重合度低于 70%。
- Evidence to evaluate: 分布形状敏感性、端点压力测试、下尾收益、方案重合度和鲁棒方法的平均收益损失。

## Compact history

- 2026-08-27: 根据 `q2_q3_risk_simulation_boundary`、`q2_surplus_sale_convention` 和 `global_experiment_budget` 建立首轮筛选；尚无人工作出方法选择。
