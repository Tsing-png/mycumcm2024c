# Q2 Method Card

## Goal and success criteria

在题面给出的销量、亩产量、成本和价格变化范围内，生成唯一一套 2024 至 2030 年逐地块种植面积方案并填入 `result2.xlsx`。正式方案以超额产量按正常价格 50% 销售为主要经营口径，优先提高期望累计收益；同一方案再放入滞销压力口径和样本外随机情景中，核验亏损概率、5% 下尾收益及硬约束可行性。

## Human constraints

- Output form: 只提交一套官方 Q2 模板面积方案；baseline 只作论文比较，不生成第二份正式模板。
- Priority: 半价销售模式下的期望收益优先，滞销模式用于检验下行风险。
- Unacceptable failure: 方案违反物理约束、样本外出现未披露的明显亏损风险，或种植面积高度集中而无告警。
- Experiment budget: 精简。确定性单路径 MILP 求方案，200 个独立蒙特卡洛情景只用于样本外评估；不再进行全情景联合优化、端点表或五种子规模展开。

## Shortlist

| ID | Role | Mathematical idea | Why eligible | Main risk | Implementation cost |
|---|---|---|---|---|---|
| Q2-M1 | main_candidate | 采用题面变化区间中点构造逐年复利的期望趋势多期 MILP，在半价销售规则下输出唯一面积方案 | 模型规模与 Q1 相当，直接体现题面给出的长期趋势，适合稳定生成正式填表方案 | 单一路径优化可能低估情景尾部风险，必须进行样本外评估 | 低至中等 |
| Q2-B1 | usable_baseline | 将 2023 年销量、亩产量、成本和价格保持不变的静态多期 MILP | 完成同一面积规划任务，与主方法的趋势信息增量对比清晰 | 忽略题面给出的未来趋势 | 低 |
| Q2-F1 | conditional_fallback | 预算不确定集下的鲁棒 MILP | 当样本外或端点风险明显失稳时提供不依赖精确概率分布的替代方案 | 可能过度保守 | 中高 |

## Baseline validity

- Real task completed: 是。Q2-B1 使用同一约束和半价销售口径产生完整面积方案，但只作为比较方案。
- Comparable output/metric: Q2-M1 与 Q2-B1 使用相同的 200 个测试情景，比较平均累计收益、5% 分位收益、最差 5% 平均收益、亏损概率、面积集中度和硬约束违规数；两者同时接受滞销压力评估。

## Risk-probe summary

| ID | Executability | Data/assumptions | Degeneracy | Sensitivity | Scale | Verdict |
|---|---|---|---|---|---|---|
| Q2-M1 | 中心趋势确定性模型已在旧 baseline 路径中证明可快速执行且硬约束可满足 | 区间中点是透明建模约定，不是观测预测 | 必须报告面积集中度 | 待在同一 200 情景的半价与滞销口径下评估 | 约 2.24 万变量，不复制情景变量 | CONDITIONAL |
| Q2-B1 | 复用 Q1 已验证的静态确定性模型骨架 | 静态基期只作为 baseline，不代表未来预测 | 必须报告面积集中度 | 待与主方案在同一 200 情景下配对评估 | 与 Q1 同规模 | CONDITIONAL |

## Fallback trigger

- Trigger: 主模型 Gap 超过 1%，200 个测试情景中出现亏损，最差 5% 平均收益相对期望收益下降超过 10%，或批量评估与逐情景精确核对不一致。
- Evidence to evaluate: 求解器指标、200 情景配对收益、亏损概率、5% 下尾平均收益和评估核对误差。

## Compact history

- 2026-08-27: 人工通过 `q2_method_choice` 选择 Q2-M1；Q2-B1 保留为 usable baseline，Q2-F1 保持休眠。
- 2026-08-28: 20 情景共享决策诊断成功，目标复算一致且硬约束零违规。
- 2026-08-28: 人工通过 `q2_simplified_delivery_contract` 选择 C，正式方案主要采用半价销售模式；契约精简为 20 情景优化、200 情景样本外评估和一套 `result2.xlsx`。
- 2026-08-28: 人工通过 `q2_decoupled_evaluation_contract` 将正式架构改为期望趋势确定性 MILP 求方案、200 情景样本外评估；静态基期模型改为 baseline，SAA 模型停用。
