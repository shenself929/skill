---
name: paper-deep-summary
description: >-
  Generate a structured, objective deep summary and extension plan Markdown
  document for a single research paper (including symbol glossary, 7 core
  sections, full experimental setup/conclusions, and Obsidian ==highlights==).
  Use when the user asks to summarize a paper, extract main content, ideas,
  contributions, assumptions, limitations, experimental setups/conclusions, and
  future combination directions from a paper PDF (and companion PPT/notes).
---

# Paper Deep Summary

把单篇科研论文（及其同目录下的 PPT、讲稿、译文等配套材料）整理成一份**忠于正文、语气温和客观、结构完备、重点高亮**的深度总结与改进方案文档，默认输出至论文同目录下的 `<论文简称>_论文总结与改进方案.md`。

## Overview

本 Skill 产出的文档固定包含 **8 个标准模块**：
0. **常用符号与缩写说明**（按网络变量、概率损失、超参因子、常见缩写分类）
1. **一、论文主要内容**（技术脉络 Mermaid 图、继承/改动边界、算法流程）
2. **二、核心思想**（路线抉择、前作近似剖析、核心公式与递进方法链）
3. **三、主要贡献**（理论、方法、评测三条证据链）
4. **四、论文所做的假设**（显式理论前提与隐式实验前提对照表）
5. **五、方法适用边界与局限**（温和客观的权衡分析与当前实证范围）
6. **六、实验设置与实验结果证明的结论**（完整实验协议 + 数据全表 + 结论映射）
7. **七、未来展望与可结合的改进方向**（紧扣正文线索提出可落地的结合方案与结论增益）

## Dependencies

撰写时应复用以下已安装技能的语法与绘图规范，无需重复定义：
- **`obsidian-markdown`**：遵循 Obsidian Markdown 规范编写表格、引用块、可点击 `file:///` 链接及 `==重点高亮==`。
- **`mermaid-visualizer`**：绘制技术演进图与机制流程图，含括号/特殊字符的节点标签须加双引号以防渲染报错。

## Core Principles（必须遵守的写作准则）

1. **正文有的才写**：所有公式、定理、假设、边界和实验数字必须源自论文正文、附录或同目录配套材料，严禁凭空编造数字或对论文未涉及的方面强加苛责。
2. **语气温和客观、避免连续否定句**：积极肯定论文的核心洞察与实证价值；将“假设”和“局限”表述为“理论成立前提”“效率-精度权衡”与“当前实证覆盖范围”。
3. **全量保留关键实验证据**：不要只写“显著提升”，必须完整整理实验设置表、主实验对比表、消融实验表及具体数字，并在每张表后逐条写明“该组数据证明了什么结论”。
4. **Obsidian `==高亮==` 规范**：默认对核心术语、核心发现、关键实验数字与重要结论添加 `==...==` 高亮，但**严禁**将 `==` 写入 `$...$`/`$$...$$` 数学公式或 ```` ```mermaid ```` / 代码块内部（详细标尺见 [template_structure.md](./references/template_structure.md)）。

## Utility Scripts

本 Skill 附带零外部依赖的 Python 3 CLI 工具 [paper_summary_cli.py](./scripts/paper_summary_cli.py)，全程使用 `uv run` 调用，且结果均通过 `--output` 写入文件（不向 stdout 输出大段 JSON）：

1. **扫描材料与推断路径（`scan`）**：
   ```powershell
   uv run scripts/paper_summary_cli.py scan --target "<论文PDF或目录路径>" --output "<scan_manifest.json>"
   ```
   自动扫描同目录（深度 $\le 2$）的论文 PDF、附录 PDF、PPT、讲稿、中英译文及最近的 `AGENTS.md`（检查是否存在 Git 自动快照约定），并推断 `<论文简称>_论文总结与改进方案.md` 推荐输出路径。

2. **生成 8 段式标准骨架（`scaffold`）**：
   ```powershell
   uv run scripts/paper_summary_cli.py scaffold --paper-name "<论文简称>" --output "<目标md路径>"
   ```

3. **文档结构与高亮安全校验（`validate`）**：
   ```powershell
   uv run scripts/paper_summary_cli.py validate --doc "<目标md路径>" --output "<validation_report.json>"
   ```
   自动核验 8 大必需章节是否存在、`==...==` 是否成对且未误入公式/代码块、Markdown 表格列数是否一致、Mermaid 块是否闭合以及 `file:///` 链接是否使用正斜杠。校验不通过时返回退出码 `1`。

## Workflow

1. **材料扫描（`scan`）**：
   - 运行 `paper_summary_cli.py scan`，将结果写入临时 JSON 文件（如会话 scratch 目录的 `scan_manifest.json`）并读取。
   - 若同目录存在 PPT、讲稿、中英译文或附录 PDF，将其作为重要辅助材料一并纳入阅读，与主论文相互印证。
2. **精读与信息抽取**：
   - 仔细阅读 [template_structure.md](./references/template_structure.md) 对照写作要点。
   - 抽取论文的常用符号、技术祖先链、核心数学推导与公式编号、显隐式假设、边界权衡、完整实验配置与全量表格数字。
3. **构建骨架与撰写正文（`scaffold` + 撰写）**：
   - 按需要运行 `scaffold` 初始化目标文档，随后填充全部 8 个模块。
   - 第七章「未来展望与可结合的改进方向」须紧扣正文或边界中已体现的线索（如正交组件结合、效率瓶颈优化、任务头简化补全、跨模态/跨架构迁移等），按五段式展开写清：**切入依据 $\rightarrow$ 主要思想 $\rightarrow$ 沿用哪篇论文的什么机制 $\rightarrow$ 改进了什么地方 $\rightarrow$ 渴望得到什么结果（对原论文结论的提升）**。
   - 为全文重点词句与关键指标添加适度、精准的 `==高亮==`。
4. **校验与收尾（`validate` + Git 快照）**：
   - 运行 `paper_summary_cli.py validate` 检查文档；若报错，根据报告行号修复后再次验证直至 `"passed": true`。
   - 若 `scan` 结果显示所在仓库的 `AGENTS.md` 包含 Git 自动快照规范，按规范对新增/修改文档执行针对性的本地提交（注意避免误提交工作区中无关的历史变动）。

## Common Mistakes

- **误把沿用组件当创新**：务必在第一章分清“继承自前作的框架/组件”与“本文唯一改动的核心模块”。
- **只写结论不列设置与数字**：第六章必须先写清楚数据集、模型、量化/训练协议与硬件等设置，再附数据表并逐条总结数据证明了什么结论。
- **在数学公式或 Mermaid 块内加 `==`**：会导致 KaTeX 或 Mermaid 渲染失败；务必通过 `validate` 子命令把关。
- **脱离正文苛刻批评**：避免使用大量否定句挑刺，应基于正文实际范围客观陈述前提与适用边界。
