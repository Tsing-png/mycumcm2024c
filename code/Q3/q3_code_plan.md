# Q3 Python 代码计划

## 目标与边界

- 实现目标：Python，`round1`。
- 批准决策：`q3_method_choice` 与 `q3_implementation_contract`，并继承 `q2_implementation_contract`。
- 主方法 `Q3-M1`，baseline `Q3-B1`。除关系结构外，两者使用相同边际样本、共同随机数、管理候选、约束、销售规则和评价指标。
- `Q3-F1` 不实现。矩阵非正定、经验相关误差超过 0.08、弱中强方案重合度低于 50%，或轻微关系扰动使收益方向反转时只记录触发。

## 输入与 Q2 接口

复用 Q2 的清洗输入、合法槽位、模型骨架、逐年复利边际生成器和场景摘要。Q3 关系配置必须独立保存为 `results/Q3/experiments/round1/metrics/q3_relation_config.json`，包含作物 ID、关系类型、方向、强度、构造规则、矩阵、响应公式和来源标签 `simulated_assumption`。

## 类别与用途分组规则

关系由作物清单机械映射，不从单年横截面估计：

- 替代组包括干豆类 1–5、主粮谷物 6–11 与 14–16、薯类/淀粉作物 12–13、鲜食豆类 17–19、茄果椒类 21/22/24/31、叶菜类 23/27/28/30/32/33/34、甘蓝类 25/26/35、根茎类 20/36/37、食用菌 38–41。单元素或无法合理归组的作物不强行添加替代边。
- 互补关系仅表达轮作模拟：豆类作物与共享至少一种适宜地块季次的非豆类作物连接。它不是消费需求或实证增产关系，不直接修改物理亩产量。
- 每条关系边及分组必须落盘，便于人工删除或调整后重跑。

## 关系响应与相关情景

1. 先生成与 Q2-B1 完全相同的独立边际样本，再用高斯 copula 的相关正态秩变量映射回原边际分布。
2. 弱、中、强总体相关强度使用已通过探针的 `0.15/0.35/0.55`；生成后的相关矩阵必须对称、对角为 1 且最小特征值为正。
3. 替代矩阵 $S^{(h)}$ 对同组非对角边赋负向系数，互补矩阵 $M^{(h)}$ 对轮作边赋正向系数；系数绝对值由档位强度统一缩放并进行行归一化，保证单个作物的总响应不因组大小膨胀。
4. 响应只调整情景预期销量：以对应作物的标准化销量冲击为输入，经 $S^{(h)}+M^{(h)}$ 得到附加冲击，再裁剪到 Q2 题定销量变化边界。价格、成本的相关性通过 copula 表达，物理亩产量边际保持 Q2 口径。
5. 保存裁剪比例、矩阵最小特征值、目标与经验相关最大误差；关系响应公式和裁剪规则必须同时出现在配置中。

该构造是对用户所选“类别与用途关系”的可复现展开，不表示真实替代弹性、互补效应或因果关系。

## Q3-M1 与 Q3-B1

- `Q3-M1` 对每个强度档位和两种销售规则求解共享决策随机 MILP，目标仍是情景平均累计净收益，下尾指标只报告。
- `Q3-B1` 关闭 $S^{(h)}$、$M^{(h)}$ 和 copula 相关结构，使用 Q2 的独立情景随机 MILP；保持边际样本 ID 不变。
- 两者均在独立测试样本上做配对比较。不得把 Q2 的确定性中心路径当作 Q3 baseline。

## 输出契约

目录为 `results/Q3/experiments/round1/`：

- `tables/q3_m1_{weak,medium,strong}_*_schedule.csv` 与 `q3_b1_*_schedule.csv`。
- `tables/q3_q2_paired_comparison.csv`、`q3_area_transfer.csv`、`q3_relation_edges.csv`、`q3_strength_sensitivity.csv`、`q3_feasibility_checks.csv`。
- `metrics/q3_relation_config.json`、`q3_metrics.json`、`q3_correlation_checks.json`、`q3_solver_metrics.json`。
- `figures/` 可保存关系矩阵热图、面积转移图和配对收益/下尾比较图；所有图必须引用保存的数据表。
- `run_summary.json` 记录方法、档位、种子、样本哈希、输出、warnings、errors 和 fallback 状态。

共同指标为平均累计净收益、5% 分位收益、5% 下尾平均收益、亏损比例、$H_1$、$H_3$、非零作物数、管理复杂度、`N_viol`、Q3/Q2 方案重合度、面积转移、经验相关误差、裁剪比例、运行时间和 gap。Q3 差异只能在配对配置一致时归因于关系结构。

## 运行与复现

- 入口：`uv run code/Q3/run_q3.py --round round1 --seed 2026`。
- 默认按弱、中、强分档顺序运行，使用与 Q2 相同的种子组及样本 ID。
- 单档 15 分钟限时；失败或异常才创建 `logs/`。

## 下游审查

`code/Q3/reviews/q3_python_review.json` 必须完成 `syntax`、`input_contract`、`method_alignment`、`reproducibility`、`output_contract` 五项命名检查，并额外核验 Q2/Q3 边际匹配、共同随机数、矩阵正定、经验误差、响应边界、关系标签、输出集中、配对归因和 fallback 判定。
