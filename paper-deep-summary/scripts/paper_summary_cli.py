"""CLI helper for the paper-deep-summary skill.

Provides three subcommands to support structured paper summarization:
- scan: Discover the target paper PDF, companion slides/translations/notes,
  and infer the recommended output Markdown path.
- scaffold: Generate a clean 8-section Markdown skeleton.
- validate: Check structural completeness, Obsidian ==highlight== safety,
  Markdown table alignment, Mermaid block closure, and file:// links.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

REQUIRED_SECTION_PATTERNS = [
    ("常用符号与缩写说明", r"^##\s+常用符号与缩写说明"),
    ("一、论文主要内容", r"^##\s+一、论文主要内容"),
    ("二、核心思想", r"^##\s+二、核心思想"),
    ("三、主要贡献", r"^##\s+三、主要贡献"),
    ("四、论文所做的假设", r"^##\s+四、论文所做的假设"),
    ("五、方法适用边界与局限", r"^##\s+五、方法适用边界与局限"),
    ("六、实验设置与实验结果证明的结论", r"^##\s+六、实验设置与实验结果证明的结论"),
    ("七、未来展望与可结合的改进方向", r"^##\s+七、未来展望与可结合的改进方向"),
]

SCAFFOLD_TEMPLATE = """# {paper_name} 论文总结与扩展展望

> **论文题目**：*<Paper Full Title>*
> **作者**：<Authors>
> **发表会议/期刊**：<Venue / Year>
> **开源代码**：<Code URL or N/A>
> **参考材料**：[原文PDF](file:///<abs_pdf_path>)

---

## 常用符号与缩写说明

为便于阅读下文公式推导与实验表格，下表集中列出论文正文与算法中常用的符号及缩写含义：

### 1. 网络模块与核心变量符号
| 符号 | 含义说明 |
| :--- | :--- |
| $<sym_1>$ | <meaning> |

### 2. 概率分布、损失与关键指标符号
| 符号 | 含义说明 |
| :--- | :--- |
| $<sym_2>$ | <meaning> |

### 3. 常见缩写
| 缩写 | 全称与含义 |
| :--- | :--- |
| **<ABBR>** | <full name and meaning> |

---

## 一、论文主要内容

### 1.1 研究背景与技术定位
<用温和客观的语言交代研究背景、核心痛点与技术继承脉络，使用 ==重点高亮== 标出关键术语。>

```mermaid
flowchart LR
    A["前驱工作 A"] --> B["前驱工作 B"]
    B --> C["本文工作 {paper_name}"]
```

### 1.2 方法整体流程
<结合原文算法或框架图，分步骤说明输入、核心步骤与输出。>

---

## 二、核心思想

### 2.1 技术路线的选择与核心洞察
<说明论文切入的路线与关键洞察。>

### 2.2 关键推导与方法递进链
<严格依据论文正文列出核心公式与递进式方法对比表。>

---

## 三、主要贡献

1. **理论层面**：<...>
2. **方法层面**：<...>
3. **评测层面**：<...>

---

## 四、论文所做的假设

| 序号 | 假设内容 | 出现位置 | 作用与意义 |
| :---: | :--- | :--- | :--- |
| **1** | ==**<assumption>**== | <section / theorem> | <role> |

---

## 五、方法适用边界与局限

1. **<适用边界或性能权衡 1>**：<...>
2. **<时间/算力或工程适配边界 2>**：<...>
3. **<当前实证覆盖范围>**：<...>

---

## 六、实验设置与实验结果证明的结论

### 6.1 实验设置（Experimental Setup）

| 实验维度 | 具体设置细节 |
| :--- | :--- |
| **数据集与任务** | <datasets & tasks> |
| **评估模型架构** | <models> |
| **对比基线方法** | <baselines> |
| **核心超参数与硬件** | <hyperparameters & hardware> |

### 6.2 实验结果与所证明的结论

#### 实验一：<主实验名称>
| 方法 | 配置 | 指标 1 | 指标 2 |
| :--- | :---: | :---: | :---: |
| Baseline | - | - | - |
| **{paper_name}** | - | **-** | **-** |

**所证明的结论**：
1. ==**<结论 1>**==：<对照具体数据说明>

---

## 七、未来展望与可结合的改进方向

### 方向一：<结合方向名称>
- **切入依据**：<对应正文或局限中的明确线索>
- **结合方法与新增部分**：<具体如何把方向/方法与本文结合>
- **对论文结论的提升**：<新增模块或实验如何让原结论更强/更完备>
"""


def write_json_output(data: dict, output_path: Path) -> None:
  """Write dictionary data as pretty-printed JSON to output_path."""
  try:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Success! Data written to: {output_path}")
  except (OSError, TypeError) as exc:
    print(f"Error writing JSON to {output_path}: {exc}", file=sys.stderr)
    sys.exit(1)


def _walk_limited(root: Path, max_depth: int = 2) -> list[Path]:
  """Collect files under root up to max_depth levels without following noise dirs."""
  skip_dirs = {".git", "__pycache__", "node_modules", "preview", "preview_150", ".venv"}
  results: list[Path] = []
  root_depth = len(root.parts)
  for current, dirs, files in os.walk(root):
    cur_path = Path(current)
    depth = len(cur_path.parts) - root_depth
    dirs[:] = [d for d in dirs if d not in skip_dirs and depth < max_depth]
    for name in files:
      results.append(cur_path / name)
  return sorted(results)


def _infer_paper_short_name(target: Path, search_dir: Path) -> str:
  """Infer a concise paper short name from target file or enclosing folder."""
  if target.is_file():
    stem = target.stem
    for suffix in ("_完整版", "_official", "_arXiv", "_PPT", "_paper"):
      if suffix in stem:
        stem = stem.split(suffix)[0]
    if "_" in stem and len(stem.split("_")[0]) >= 3:
      return stem.split("_")[0]
    return stem
  return search_dir.name


def _classify_companion_file(path: Path) -> str | None:
  """Classify companion reference files into structured categories."""
  suffix = path.suffix.lower()
  name_lower = path.name.lower()
  parent_lower = path.parent.name.lower()

  if suffix == ".pdf":
    if "ppt" in parent_lower or "ppt" in name_lower or "slide" in name_lower:
      return "slides_pdf"
    if "supp" in name_lower or "appendix" in name_lower:
      return "supplemental_pdf"
    return "paper_pdf"
  if suffix in {".pptx", ".ppt"}:
    return "slides_ppt"
  if suffix == ".md":
    if "论文总结与改进方案" in path.name:
      return "existing_summary_md"
    if any(k in name_lower for k in ("讲稿", "script", "翻译", "译文", "精读", "note")):
      return "companion_md"
    return "other_md"
  if suffix == ".tex" and "ppt" not in parent_lower:
    return "latex_tex"
  return None


def _find_nearest_agents_md(start_dir: Path) -> str | None:
  """Walk upward to locate nearest AGENTS.md rule file if present."""
  cur = start_dir.resolve()
  for parent in [cur, *cur.parents]:
    candidate = parent / "AGENTS.md"
    if candidate.is_file():
      return str(candidate)
    if (parent / ".git").exists():
      break
  return None


def run_scan(target_str: str, output_str: str) -> None:
  """Scan target paper path and companion directory, then write JSON manifest."""
  target = Path(target_str).resolve()
  if not target.exists():
    print(f"Error: target path does not exist: {target}", file=sys.stderr)
    sys.exit(1)

  if target.is_file():
    # If target sits in a subfolder like *_PPT, anchor at parent paper directory if appropriate.
    if "ppt" in target.parent.name.lower() and target.parent.parent.exists():
      paper_dir = target.parent.parent
    else:
      paper_dir = target.parent
  else:
    paper_dir = target

  short_name = _infer_paper_short_name(target, paper_dir)
  recommended_output = paper_dir / f"{short_name}_论文总结与改进方案.md"

  buckets: dict[str, list[str]] = {
      "paper_pdf": [],
      "supplemental_pdf": [],
      "slides_pdf": [],
      "slides_ppt": [],
      "companion_md": [],
      "existing_summary_md": [],
      "other_md": [],
      "latex_tex": [],
  }

  for fpath in _walk_limited(paper_dir, max_depth=2):
    category = _classify_companion_file(fpath)
    if category is not None:
      buckets[category].append(str(fpath))

  manifest = {
      "target": str(target),
      "paper_dir": str(paper_dir),
      "inferred_short_name": short_name,
      "recommended_output_path": str(recommended_output),
      "nearest_agents_md": _find_nearest_agents_md(paper_dir),
      "materials": buckets,
  }
  write_json_output(manifest, Path(output_str))


def run_scaffold(paper_name: str, output_str: str) -> None:
  """Generate an 8-section Markdown skeleton for a paper summary."""
  out_path = Path(output_str)
  try:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    content = SCAFFOLD_TEMPLATE.format(paper_name=paper_name.strip())
    out_path.write_text(content, encoding="utf-8")
    print(f"Success! Scaffold written to: {out_path}")
  except OSError as exc:
    print(f"Error writing scaffold to {out_path}: {exc}", file=sys.stderr)
    sys.exit(1)


def _strip_inline_code(line: str) -> str:
  """Remove inline backtick code spans so == or $ checks ignore literal code."""
  return re.sub(r"`[^`]*`", "", line)


def _check_highlights_on_line(line: str, lineno: int, errors: list[str]) -> int:
  """Validate ==highlight== pairing and forbid == inside inline math $...$."""
  cleaned = _strip_inline_code(line)
  if "==" not in cleaned:
    return 0

  count = cleaned.count("==")
  if count % 2 != 0:
    errors.append(f"Line {lineno}: Unclosed Obsidian highlight '==' (count={count}).")

  # Check whether == appears inside inline math $...$
  parts = cleaned.split("$")
  for idx in range(1, len(parts), 2):
    if "==" in parts[idx]:
      errors.append(f"Line {lineno}: Obsidian highlight '==' placed inside inline math $...$.")

  return count // 2


def _check_table_consistency(lines: list[str], errors: list[str]) -> int:
  """Verify that every Markdown table block has consistent column counts."""
  table_count = 0
  in_table = False
  expected_cols = 0

  for lineno, raw in enumerate(lines, start=1):
    stripped = raw.strip()
    is_row = stripped.startswith("|") and stripped.endswith("|") and len(stripped) > 1
    if is_row:
      # Split only on unescaped pipes so LaTeX `\|` inside cells is preserved.
      cols = len(re.split(r"(?<!\\)\|", stripped)) - 2
      if not in_table:
        in_table = True
        expected_cols = cols
        table_count += 1
      elif cols != expected_cols:
        errors.append(
            f"Line {lineno}: Table column mismatch (expected {expected_cols}, got {cols})."
        )
    else:
      in_table = False
      expected_cols = 0
  return table_count


def run_validate(doc_str: str, output_str: str) -> None:
  """Validate a generated paper summary Markdown document and write report JSON."""
  doc_path = Path(doc_str).resolve()
  if not doc_path.is_file():
    print(f"Error: document does not exist: {doc_path}", file=sys.stderr)
    sys.exit(1)

  text = doc_path.read_text(encoding="utf-8")
  lines = text.splitlines()
  errors: list[str] = []
  warnings: list[str] = []

  # 1. Required sections check
  missing_sections = [
      label
      for label, pat in REQUIRED_SECTION_PATTERNS
      if not re.search(pat, text, flags=re.MULTILINE)
  ]
  if missing_sections:
    errors.append(f"Missing required sections: {', '.join(missing_sections)}")

  # 2. Line-by-line scan for code/mermaid/math blocks, highlights, and file:// links
  in_code_block = False
  in_display_math = False
  mermaid_blocks = 0
  highlight_pairs = 0
  backslash_links = 0

  for lineno, line in enumerate(lines, start=1):
    stripped = line.strip()

    if stripped.startswith("```"):
      if not in_code_block and stripped.startswith("```mermaid"):
        mermaid_blocks += 1
      in_code_block = not in_code_block
      continue

    if stripped == "$$":
      in_display_math = not in_display_math
      continue

    if "file:///" in line and "\\" in line.split("file:///")[1].split(")")[0]:
      backslash_links += 1
      errors.append(f"Line {lineno}: file:/// link contains backslash '\\'; use forward slashes '/'.")

    if in_code_block or in_display_math:
      if "==" in line:
        errors.append(
            f"Line {lineno}: Obsidian highlight '==' should not appear inside code/mermaid/display-math blocks."
        )
      continue

    highlight_pairs += _check_highlights_on_line(line, lineno, errors)

  if in_code_block:
    errors.append("Unclosed fenced code/mermaid block '```' at end of file.")
  if in_display_math:
    errors.append("Unclosed display math block '$$' at end of file.")
  if highlight_pairs == 0:
    warnings.append("No Obsidian ==highlight== markers found; verify important terms are highlighted.")

  # 3. Markdown table consistency
  table_count = _check_table_consistency(lines, errors)

  report = {
      "document": str(doc_path),
      "passed": len(errors) == 0,
      "stats": {
          "line_count": len(lines),
          "required_sections_present": len(REQUIRED_SECTION_PATTERNS) - len(missing_sections),
          "required_sections_total": len(REQUIRED_SECTION_PATTERNS),
          "highlight_pairs": highlight_pairs,
          "table_count": table_count,
          "mermaid_blocks": mermaid_blocks,
      },
      "errors": errors,
      "warnings": warnings,
  }
  write_json_output(report, Path(output_str))
  if errors:
    sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
  """Construct the CLI argument parser with scan, scaffold, and validate subcommands."""
  parser = argparse.ArgumentParser(
      description="CLI helper for paper-deep-summary skill."
  )
  subparsers = parser.add_subparsers(dest="command", required=True)

  p_scan = subparsers.add_parser("scan", help="Scan paper folder and infer output path.")
  p_scan.add_argument("--target", required=True, help="Path to paper PDF or directory.")
  p_scan.add_argument("--output", required=True, help="Output JSON manifest path.")

  p_scaffold = subparsers.add_parser("scaffold", help="Create 8-section Markdown skeleton.")
  p_scaffold.add_argument("--paper-name", required=True, help="Short name of the paper.")
  p_scaffold.add_argument("--output", required=True, help="Output Markdown skeleton path.")

  p_val = subparsers.add_parser("validate", help="Validate summary Markdown structure & syntax.")
  p_val.add_argument("--doc", required=True, help="Path to generated summary Markdown file.")
  p_val.add_argument("--output", required=True, help="Output validation JSON report path.")

  return parser


def main() -> None:
  args = build_parser().parse_args()
  if args.command == "scan":
    run_scan(args.target, args.output)
  elif args.command == "scaffold":
    run_scaffold(args.paper_name, args.output)
  elif args.command == "validate":
    run_validate(args.doc, args.output)


if __name__ == "__main__":
  main()
