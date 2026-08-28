# Q3 Round 2 结果判断摘要

## 主方法与 baseline

中档 Q3-M1 在 0.768% Gap 下完成，硬约束零违反。半价销售的中档相关情景中，Q3-M1 平均七年收益为 68,870,310.31 元，关闭关系结构的 Q2 baseline 为 68,748,943.00 元。Q3-M1 下尾 5% 平均收益为 60,140,249.93 元，baseline 为 60,099,274.32 元，两者亏损概率均为零。

## 关系强度与相关验证

弱、中、强三档最终经济变量最大相关误差分别为 0.0130、0.0300 和 0.0353，均低于 0.08；目标矩阵均正定，价格与需求方向符合设定。三档方案两两收益偏差为 0.061% 至 0.186%，41 维作物总面积相似度为 94.73% 至 96.63%。因此当前证据属于宏观策略稳定、地块层面等价平移。

## Fallback 与限制

Q3-F1 未触发。所有替代、互补和相关结构均为模拟假设，不是附件观测关系；后续仍需针对关系强度、随机种子或边际分布进行稳健性验证。

证据来源为 `results/Q3/experiments/round2/run_summary.json`、`results/Q3/experiments/round2/metrics/q3_metrics.json`、`results/Q3/experiments/round2/metrics/q3_correlation_checks.json` 和 `code/Q3/reviews/q3_python_review.json`。
