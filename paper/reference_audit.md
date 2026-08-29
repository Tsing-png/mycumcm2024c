# Reference Audit Report

审计日期：2026-08-29  
结论：**PASSED**

## 引用清单与来源

正文共使用 15 个唯一引用键，均有对应参考文献条目。`tan2025review`、`shi2025cvar`、`xu2025lp` 和 `zhao2025relation` 有用户提供的本地论文 PDF，并已在 `workspace/papers/related_paper_analysis.md` 中分析。其余经典方法、求解器和轮作规划文献由用户明确确认为人工选择的真实文献，书目信息与 `paper/9.参考文献.tex` 保持一致。

| 引用范围 | 支撑内容 | 状态 |
|---|---|---|
| `tan2025review`, `xu2025lp`, `zhao2025relation`, `shi2025cvar` | 同题建模、风险评价与关系结构应用 | 已核对本地来源 |
| `dantzig1963`, `wolsey1998` | 线性规划与整数规划基础 | 已确认 |
| `metropolis1949`, `rockafellar2000` | 蒙特卡洛与 CVaR 基础 | 已确认 |
| `huangfu2018` | HiGHS 相关求解方法 | 已确认 |
| `golub2013` | Cholesky 与矩阵计算 | 已确认 |
| `haneveld2005`, `alfandari2011`, `aitsahlia2011`, `capitanescu2017`, `benini2023` | 轮作、农场规划及不确定性应用 | 已确认 |

## 完整性检查

- 所有 `\\upcite` 键均出现在 `paper/refs.bib`，并由 `paper/9.参考文献.tex` 调用。
- 参考文献表中没有未被正文引用的条目。
- 正文引用均为 `\\upcite`，没有普通 `\\cite`。
- 未写入未经确认的 DOI。
- 没有占位作者、占位题名或无来源引用。
- 经典方法与同题应用文献同时覆盖，没有为达到数量而添加装饰性引用。

## 风险与建议

未发现疑似编造或阻塞性引用。当前论文使用 `gbt7714-numerical.bst` 和 `paper/refs.bib` 生成参考文献，正文通过 `natbib` 数字模式显示上标编号。完整编译顺序为 XeLaTeX、BibTeX、XeLaTeX、XeLaTeX。
