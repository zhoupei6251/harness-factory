#!/usr/bin/env python3
"""一次性脚本：清掉 news 域文档里陈旧的"2/12 可渲染"描述（D15）。

背景（2026-10-08）: 32 个 pack 全部填实并实测通过，但 ARCHITECTURE.md /
MEMORY.md / news-workflow/SKILL.md 里还留着"2/12 可渲染""⏳ 10 pack 待补"
"决策树命中不可渲染的包就 fallback"等说法。文档说谎比 bug 更贵 ——
接手的人会照着去干两天模板。

按行号 + 内容断言双重定位替换，不做模糊文本匹配（避免手抄多字/漏字导致替换失败）。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

#: (文件, 起始行含, 结束行含) → 替换块
JOBS = [
    (
        "skills/news-workflow/SKILL.md",
        "**当前进度**（12 pack",
        "- 校验（三道闸",
        """**当前进度**（2026-10-08 实测，32 个 pack 全部齐全）：
- **32/32 全部有真版式**：12 master + 20 派生变体，每个 `compositions/` 7 个真 composition
- `placeholder.html` 全删；`load_style_pack` 32/32 成功；`layout_selfcheck.py` 32 包 234 文件 0 违规
- 20 个派生变体已补 `frame.md`（含 `derived_from` 派生声明）
- **决策树可以放心用** —— 命中任何一格都渲得出来，不再需要"不可渲染就 fallback"那套绕路
- ⚠️ 本节原写「2/12 可渲染、其余 10 包仅占位」是**陈旧数据已作废**（见 ARCHITECTURE.md D15）
- ⚠️ **改版式用色时**：`audit_pack_contrast.py` 口径是「本包色板 ∪ 共享 token 层」，
  `SHARED_TOKENS` 是跨包公共角色色（实测出现 ≥6 次）、**不许手抄** ——
  改完用 `shared_tokens_need_review()` 核对（D18）。`#root` 地面色另受 `GROUND_TONE_BY_HEX`
  约束，改它等于改整片的底。
- 校验（三道闸""",
    ),
    (
        "routes/news/ARCHITECTURE.md",
        "      可渲染 pack (有真版式): 2/12",
        None,
        "      可渲染 pack (有真版式): 32/32 —— 全部 pack 均有 7 个真 composition（D15）",
    ),
]


def main() -> int:
    for rel, start_mark, end_mark, new_text in JOBS:
        p = ROOT / rel
        lines = p.read_text(encoding="utf-8").splitlines()
        start = next((i for i, l in enumerate(lines) if start_mark in l), None)
        if start is None:
            print(f"  ! {rel}: 找不到起始行 {start_mark!r}")
            continue
        if end_mark is None:
            end = start
        else:
            end = next((i for i, l in enumerate(lines)
                        if i > start and end_mark in l), None)
            if end is None:
                print(f"  ! {rel}: 找不到结束行 {end_mark!r}")
                continue
        old = lines[start:end + 1]
        lines[start:end + 1] = new_text.splitlines()
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"  {rel}: 替换 {len(old)} 行 → {len(new_text.splitlines())} 行")
    return 0


if __name__ == "__main__":
    sys.exit(main())
