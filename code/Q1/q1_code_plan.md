# Q1 Python 代码计划

## 目标与边界

- 实现目标：Python，当前正式实验为 `round2`。
- 批准决策：`q1_method_choice`，主方法 `Q1-M1`，baseline `Q1-B1`。
- 只实现上述两种方法及共享校验、比较、模板写出逻辑。
- `Q1-F1` 不实现。仅在完整 MILP 运行 15 分钟仍无可行解、滞销模式 gap 超过 3%、半价模式 gap 超过 1%，或预计峰值内存超过 2 GB 时记录触发。

## 输入契约

| 文件 | 必需字段 | 单位或约束 |
|---|---|---|
| `workspace/data_clean/plots.csv` | `plot_id, plot_type, area_mu` | 面积为亩，54 个地块 |
| `workspace/data_clean/crops.csv` | `crop_id, crop_name, crop_category, suitability` | 作物编号 1–41 |
| `workspace/data_clean/planting_2023.csv` | `plot_id, crop_id, area_mu, season` | 2023 初始重茬与豆类窗口状态 |
| `workspace/data_clean/stats_2023.csv` | `crop_id, plot_type, season, yield_jin_per_mu, cost_yuan_per_mu, price_low, price_high` | 斤/亩、元/亩、元/斤 |
| `workspace/data_clean/stats_2023_derived.csv` | 同上及 `derived_from` | 18 条智慧大棚第一季派生记录 |
| `workspace/data_clean/template_structure.json` | 年 sheet、季块、地块和作物列顺序 | 不改变官方模板结构 |

读取后必须验证数据 profile 所述的 54 个地块、41 种作物、125 个合法参数组合和零缺失。基准价格取区间中点，基准销量由 2023 实际面积乘亩产量按作物汇总。

## 共享模型骨架

1. 生成合法槽位 `(year, season, plot, crop)`，只为适宜组合建立 $x$ 与 $z$。
2. 地块季次面积和不超过地块面积；按题面表达旱地单季、水浇地水稻或两季蔬菜互斥、普通大棚和智慧大棚规则。
3. 按已批准边界禁止相邻可种植季重茬，包含 2023 至 2024 及跨年边界。
4. 任意连续三年窗口内，每地块豆类累计面积不低于地块面积；可获得的首个窗口纳入 2023 状态。
5. 用 $x\le A_i z$ 连接面积与出现指示；管理网格分别测试绝对最小面积、相对最小占比及作物种类上限。
6. 按作物、年和季汇总产量，正常销售量不超过产量和年销量上限；超额量等于产量减正常销量。
7. 对 $\alpha=0$ 与 $\alpha=0.5$ 分别最大化 2024–2030 累计净收益。

## 管理阈值校准

不预设论文阈值。由 2023 非零种植记录按地块类型和季次计算面积及面积占比经验分布，以无管理约束、下四分位数和中位数形成最小面积/占比候选；作物种类上限由 2023 地块季次非零作物数的中位数和上四分位数向上取整形成候选。每个候选均运行主方法的小规模或限时版本，保存净收益、可行性、$H_1$、$H_3$、非零作物数、gap 和运行时间。本轮只生成比较证据，不自动冻结最终阈值。

## Q1-M1

- 使用 `scipy.optimize.milp`/HiGHS 建立七年 MILP，固定确定性参数。
- 每种销售规则、每个管理候选独立求解；最终候选尚未由人工裁决时，不覆盖为“最终方案”。
- 保存 incumbent、bound、gap、节点数、求解状态、时间和估计内存。

## Q1-B1

- 复用探针中的约束感知轮作规则并扩展为正式模块。
- 在相同管理候选和两种销售规则下生成完整七年方案，使用与主方法完全相同的收益核算器和可行性检查器。
- baseline 必须输出官方模板可映射的同粒度面积表，不允许只输出聚合比例。

## 输出契约

当前正式目录为 `results/Q1/experiments/round2/`，包含：

- `tables/q1_m1_alpha0_schedule.csv`、`q1_m1_alpha05_schedule.csv` 及 baseline 对应文件；阈值候选结果加配置 ID。
- `tables/q1_management_grid.csv`、`q1_feasibility_checks.csv`、`q1_profit_by_year.csv`。
- `metrics/q1_metrics.json`、`q1_solver_metrics.json`。
- `figures/` 只保存本轮必要的阈值收益-集中度比较图；无图时目录仍可为空。
- `run_summary.json`，符合统一 contract，并列出所有实际文件路径。
- 官方 Excel 结果先写入正式轮次的 `tables/` 副本，禁止修改 `workspace/data_raw/` 模板。

主方法与 baseline 的共同指标为累计净收益、逐年净收益、$H_1$、$H_3$、非零作物数、管理复杂度、`N_viol`、运行时间和主方法 gap。所有数值从正式输出计算，不写死在脚本中。

## 运行与复现

- 入口：`uv run python code/Q1/run_q1.py --round round2 --seed 2026 --time-limit 300`。
- 共享模块建议放在 `code/Q1/`，不创建重复 README。
- 预期 full run 上限 15 分钟；失败或异常才创建 `logs/`。
- `run_summary.json` 的 `approved_decision_id` 为 `q1_method_choice`，同时记录假设决策 ID。

## 下游审查

`code/Q1/reviews/q1_python_review.json` 必须完成 `syntax`、`input_contract`、`method_alignment`、`reproducibility`、`output_contract` 五项检查，并额外核验模板未改形、两种销售规则未混用、连续季重茬和豆类面积窗口实现正确。
