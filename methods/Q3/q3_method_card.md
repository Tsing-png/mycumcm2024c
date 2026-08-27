# Q3 Method Card

## Goal and success criteria

在 Q2 相同边际变化、时间范围、销售规则和约束下，仅引入明确标为模拟假设的作物替代、互补及经济变量相关结构，生成完整方案、策略规则和与 Q2 的深度比较。不得把模拟关系解释为观测因果规律。

## Human constraints

- Output form: 完整逐年、逐季、逐地块方案，关系矩阵和模拟设置，代表性方案、策略规则以及与 Q2 的收益、风险、配置和管理比较。
- Priority: 收益优先；通过弱、中、强关系情景解释相关结构造成的变化。
- Unacceptable failure: 相关矩阵非法、模拟不可复现、方案不可行、高度集中，或无法将 Q3 与 Q2 的差异归因于关系结构。
- Experiment budget: 标准，包括多随机种子、三档关系强度、端点和退化检查。

## Shortlist

| ID | Role | Mathematical idea | Why eligible | Main risk | Implementation cost |
|---|---|---|---|---|---|
| Q3-M1 | main_candidate | 匹配 Q2 的相关情景随机 MILP，用正定相关矩阵生成经济变量情景，并以显式响应矩阵表达替代或互补影响 | 只改变关系结构，可与 Q2 做受控深度比较，并输出完整方案 | 关系方向和强度均非观测估计，可能人为主导结论 | 高 |
| Q3-B1 | usable_baseline | Q2 的独立情景随机 MILP，保持相同边际分布、销售规则、种子和指标，但关闭作物关系 | 完成同一任务，是识别“加入关系结构”边际影响的直接 baseline | 独立性同样是模拟假设，不能代表真实市场 | 中高 |
| Q3-F1 | conditional_fallback | 非概率的关系压力测试网格，对替代、互补和经济相关方向逐项施加弱中强确定性扰动 | 当联合随机结构不可信时仍可保留可解释的比较 | 不给出概率意义，只能形成条件性压力测试结论 | 中等 |

## Baseline validity

- Real task completed: 是。Q3-B1 输出与 Q3-M1 相同格式的 7 年完整方案，只关闭关系结构。
- Comparable output/metric: 使用相同随机种子和边际样本，比较面积转移、方案重合度、期望净收益、5% 下尾收益、集中度及管理复杂度。

## Risk-probe summary

| ID | Executability | Data/assumptions | Degeneracy | Sensitivity | Scale | Verdict |
|---|---|---|---|---|---|---|
| Q3-M1 | 12 维弱、中、强相关情景均可生成 | 三档等相关矩阵最小特征值分别为 0.85、0.65、0.45，均为正定；关系仍属模拟假设 | 必须检查关系加入后 top-k 面积和利润是否异常集中 | 2000 样本下最大经验相关误差分别为 0.0563、0.0521、0.0356 | 应复用 Q2 种植变量；关系和情景维度增加，需要分档求解 | CONDITIONAL |
| Q3-B1 | 独立情景生成和代表性 MILP 均可执行 | 使用 Q2 相同边际假设，便于受控比较 | 继承 Q2 的集中风险和管理阈值 | 5 个种子下情景统计稳定，但需以相同样本与 Q3-M1 配对比较 | 与 Q2-M1 同阶 | CONDITIONAL |

Q3-M1 的条件是关系矩阵、方向、强度、种子和响应公式全部保存；论文结论只能写成“在所设模拟关系下”。若关系强度改变导致方案剧烈跳变，应触发备用路线而不是宣称稳定规律。

## Fallback trigger

- Trigger: 任一关系矩阵非正定，经验相关误差超过 0.08，或弱中强三档之间推荐面积的重合度低于 50%，或收益方向随轻微关系扰动反转。
- Evidence to evaluate: 最小特征值、经验相关误差、配对样本下的方案重合度、收益和尾部风险变化方向。

## Compact history

- 2026-08-27: 根据 `q3_output_form`、`q2_q3_risk_simulation_boundary` 和 `global_experiment_budget` 建立首轮筛选；尚无人工作出方法选择。
- 2026-08-27: 人工通过 `q3_method_choice` 选择 Q3-M1；Q3-B1 保留为必须实现的 baseline，Q3-F1 未激活。
