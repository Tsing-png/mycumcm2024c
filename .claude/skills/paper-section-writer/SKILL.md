---
name: paper-section-writer
description: Draft submission-ready mathematical-modeling paper sections from the approved solution package, frozen numbers, human decision ledger, and verified figures without searching scattered exploratory outputs or inventing interpretation.
---

# Preconditions

- `rigor_profile` is `submission`.
- Final method explanation exists.
- Final result analysis exists.
- Solution package and current frozen numbers exist.
- Required human claim-scope and physical/domain-meaning decisions are recorded.

If any prerequisite is missing, return to its producer rather than drafting around the gap.

# Primary Sources

Use, in order:

1. `qx_solution_package_for_writer.md`
2. `frozen_numbers.json`
3. `qx_decisions.jsonl`
4. verified paper figures/tables
5. final method explanation and robustness report for clarification

Do not hunt through raw experiment folders to invent a narrative.

# Workflow

1. Resolve the requested section and contest format.
2. Build a claim map:
   - claim ID;
   - frozen value/source;
   - robustness support;
   - human decision ID;
   - figure/table reference;
   - limitation.
3. Draft the method description to match the final explanation and code.
4. Draft results with:
   - value and comparison;
   - human-confirmed physical/domain meaning;
   - uncertainty or robustness;
   - limitation and applicable scope.
5. Mention the baseline and eliminated alternatives only when they explain a real decision.
6. Use only Type 2–4 figures as appropriate; never place Type 1 diagnostics in the paper.
7. Save `paper/sections/qx.tex` or the requested Markdown section.

# Human-Owned Content

The AI must not originate:

- why the method was chosen;
- what the headline number means physically;
- confidence and claim scope;
- contribution framing.

Transcribe these from the decision ledger with provenance. If absent, invoke a compact choice card and stop the final draft until answered; do not fill the paper with repeated sentinels.

# Rules

- Every numerical claim must match `frozen_numbers.json`.
- Do not overclaim against untested methods or populations.
- Do not fabricate citations or causal meaning.
- Avoid procedural diary prose and ceremonial detail.
- Keep formulas, symbols, units, captions, and filenames consistent.
- Do not create a new decision artifact.

## 模型假设章节写作规约（强制）

撰写「模型假设」章节时，必须严格区分四类内容，只有「对现实世界的理想化简化前提」才可放入假设小节，其余一律迁移到对应章节。

### 1. 内容四分类（禁止混写）

- ✅ **模型假设（仅此处）**：只写对现实世界的理想化简化前提，即「现实的近似」。典型包括：
  - 不考虑自然灾害或极端冲击；
  - 决策者理性，追求目标函数最优（收益最大化 / 成本最小化）；
  - 价格或需求外生给定（价格接受者）；
  - 不考虑库存与跨期储存；
  - 除已建模约束外的资源（劳动力、资金、水肥等）充足；
  - 参数在建模周期内保持稳定等确定性前提。
  - 判定标准：删掉题目、数据和代码后仍成立的现实前提，才是模型假设。

- ❌ **赛题硬性约束** → 放入「模型约束条件」。题目明文规定的规则（资源上限、排他性约束、连续性约束、比例约束、轮作或重茬要求等）**禁止写进模型假设**。若涉及对题意的解读口径，可在约束处补一句解读说明，但不得放入假设。

- ❌ **数据预处理 / 计算口径** → 放入「模型准备 / 数据预处理」。如销量代理构造、价格取区间中点、数据插值、参数取值方式等，不属于假设。

- ❌ **实验与技术约定** → 放入「实验设置 / 仿真方案」。如随机扰动生成方式、样本外评价规则、固定随机种子、公平对比规则，以及「参数仅用于模拟、不代表真实因果」这类免责声明，都属于实验/仿真约定，不是假设。

### 2. 禁止辩护式、自证清白式语句

模型假设中不得出现面向评委辩解的口吻，例如「为保证对比具有可比性」「不允许利用已知情景调整方案」等，此类表述移到实验说明。

### 3. 优化类模型必须补全隐含现实前提

目标函数与约束成立所依赖的底层现实前提，必须显式写进模型假设，至少覆盖：
- 决策者理性，追求目标函数最优；
- 价格/需求是否外生给定；
- 是否考虑库存、跨期储存；
- 主要约束之外的资源是否充足；
- 除题目给定扰动外，是否忽略极端灾害等冲击。

### 4. 输出格式（二选一）

- **方案 A（推荐，正式竞赛论文）**：
  - 「模型假设」小节只放现实理想化假设；
  - 赛题规则 → 模型约束；
  - 数据处理 → 模型准备·数据预处理；
  - 仿真与对比实验规则 → 实验设置。
- **方案 B（保守，不改章节结构）**：用子标题分组：
  - 模型假设 → 「基础现实假设」（全部现实简化前提）；
  - 另设「建模与仿真口径约定」（仅放解读口径与实验约定，不写现实假设）。

### 5. 校验规则（写完必查）

删掉所有代码、数据和题目规则后，剩下仍成立的现实前提才是模型假设。凡是在描述「我要怎么算、代码怎么做、题目要求什么」的内容，一律移出假设章节。

## 局限性与自我批判写作规约（强制）

写「模型的不足/局限」时，参照以下标准，避免写成套话：

1. **量化具体**：把样本量、误差、效应量等的具体数值写出来，而非泛泛说「样本较少」「变化明显」。
2. **自我批判方法本身**：不只列「未考虑 X」，还要质疑方法的内在局限——如某条关键假设「合理性存疑」、某重采样或近似「统计意义有限」。
3. **诚实指出未解决的问题**：如「数据固有结构引入的伪相关，方法能否完全消除值得讨论」。
4. **每条局限都要有数据/证据支撑**，不能是空泛套话。
5. **不回避最痛的短板**：越是方法的硬伤（样本不足、假设牵强、近似失效），越要明确写出来——这是「可信度」，不是「示弱」。

## 去自证式注释规约（强制）

写作时区分两类附加说明：

- ✅ **领域依据（保留）**：陈述真实领域规律本身，如某物理定律、化学规律、农学规律、经济原理。
- ❌ **自证式 meta 注释（删除）**：解释「为什么这么假设、这么建模、这么取值」的注释，如「这是目标函数成立的前提」「题面未提供数据，故视为…」「故按…建模」「更符合实际」「…是合理的简化」。

判定标准：删掉该句后，内容是否仍完整、结论是否仍成立？若成立，则该句是 meta 注释，应删——领域依据删掉会损失信息，meta 注释删掉只会更简洁。

## 声明、参考文献与附录的排版规约（强制）

按以下结构排版，各成一节、各起一页：

1. 正文结束后，紧跟「AI工具使用声明」作为独立小节（不另起页，紧挨正文末尾）。
2. 参考文献：用 \newpage 另起一页，只放参考文献本身（thebibliography 或 bibtex 的 \bibliography），不再夹带声明等其他内容。
3. 附录：用 \newpage 另起一页。

原则：声明、参考文献、附录三者职责分离，文件名与内容一一对应，不混装在同一文件或同一页。

# Verification

- Three writer prerequisites pass.
- Claim map resolves all numbers and judgments.
- Method, results, and figures match canonical artifacts.
- Physical meaning and contribution are human-owned.
- Limitations and uncertainty are visible.
- No Type 1 figure appears.
