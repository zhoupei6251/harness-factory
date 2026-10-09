#!/usr/bin/env python3
"""一次性脚本：为 20 个派生变体生成 frame.md（色板表 + 派生声明）。

背景（2026-10-08, D16）: 32 个 pack 全部有真版式且全部能 load, 但 20 个派生变体没有
frame.md —— `t_every_template_has_frame_md` 因此一直红。实测变体缺 frame.md **并不**
阻断渲染（load_style_pack 不要求它, 32/32 可加载）, 所以这不是能力缺口, 是**契约缺口**:
变体改了色板却没有任何文件记录"我派生自谁、改了什么", 于是 561 条 OFF_PALETTE_HEX
既抓不到它、也没人能复核。

本脚本按**变体 HTML 里的真实用色**生成色板表（不编造色值）, 并写明派生关系。
生成后仍要过三道闸:
    python skills/douyin-pro/scripts/audit_pack_contrast.py     # 色板复算
    python skills/douyin-pro/scripts/layout_selfcheck.py <dir>   # 结构不变量
    python skills/douyin-pro/scripts/path_b_selftest.py          # 全量断言

口径:
  - 色板表只列该包 frame.md/HTML 里**真正出现**的色值, 按角色归类(底/面/字/强调/次强调)
  - 对比度表由 audit_pack_contrast 复算后手写填入 → 不手抄"实测值"(D10 的教训),
    所以本脚本**只生成 §1/§2 色板表 + 派生声明, 不写 §2.1 对比度表**,
    对比度表在生成后由 `fill_ratio_tables.py` 补齐
  - 派生声明写 `derived_from: <master>`; 变体与 master 的差异色单独标注

用法:
    python routes/news/scripts/gen_variant_frames.py [--dry-run]
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKS = ROOT / "skills" / "douyin-pro" / "templates" / "hyperframes_path_b"
HEX = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")

#: 12 个 master（各有完整 frame.md）
MASTERS = [
    "news-coral", "news-ink", "news-policy", "news-stat",
    "news-onsite", "news-bulletin", "news-explainer", "news-alert",
    "news-thread", "news-takes", "news-blast", "news-world",
]

#: 变体 → 派生自哪个 master。命名惯例后缀决定归属, 例: -mono → news-coral。
#: （2026-10-09 删除 news-coral-night: 它是唯一"零独有色"的变体, 13 色全被其他包覆盖,
#:  暗底能力由同样派生自 news-coral 的 news-dusk / news-noir 承接。见 ARCHITECTURE D23。）
VARIANT_BASE = {
    "news-coral-mono": "news-coral",
    "news-ink-graphite": "news-ink", "news-policy-bold": "news-policy",
    "news-stat-grid": "news-stat", "news-onsite-urgent": "news-onsite",
    "news-bulletin-strip": "news-bulletin",
    "news-explainer-blueprint": "news-explainer",
    "news-alert-warning": "news-alert", "news-thread-tribute": "news-thread",
    "news-takes-column": "news-takes", "news-blast-score": "news-blast",
    "news-world-globe": "news-world",
    "news-mosaic": "news-coral", "news-dawn": "news-coral",
    "news-dusk": "news-coral", "news-noir": "news-coral",
    "news-paper": "news-ink", "news-podcast": "news-coral",
    "news-polarity": "news-alert",
}

#: 变体的视觉气质一句话（写进 frame.md 供选包时读）
VARIANT_NOTE = {
    "news-coral-mono": "单色灰（coral 基调 + 去饱和）",
    "news-ink-graphite": "墨石墨（ink 基调 + 更冷的黑）",
    "news-policy-bold": "政策加粗（policy 基调 + 高对比蓝）",
    "news-stat-grid": "数据网格（stat 基调 + 网格线感）",
    "news-onsite-urgent": "现场紧急（onsite 基调 + 琥珀警示）",
    "news-bulletin-strip": "速报条状（bulletin 基调 + 极简条）",
    "news-explainer-blueprint": "科普蓝图（explainer 基调 + 亮蓝）",
    "news-alert-warning": "警示警告（alert 基调 + 黄三角）",
    "news-thread-tribute": "致敬专题（thread 基调 + 金）",
    "news-takes-column": "观点专栏（takes 基调 + 深靛）",
    "news-blast-score": "比分（blast 基调 + 绿）",
    "news-world-globe": "国际地球（world 基调 + 亮蓝）",
    "news-mosaic": "马赛克拼贴（多色块拼接）",
    "news-dawn": "拂晓暖橙（coral 基调 + 暖橙）",
    "news-dusk": "黄昏紫（coral 基调 + 紫）",
    "news-noir": "黑色（coral 基调 + 纯黑）",
    "news-paper": "报纸白底（ink 基调 + 白）",
    "news-podcast": "播客紫（coral 基调 + 紫）",
    "news-polarity": "极端对比（alert 基调 + 纯黑白橙）",
}

#: 语义角色 → 名称前缀。按"用法"猜角色, 猜不出就归 misc。
#: 这是**从色值本身推断**的启发式, 只影响 token 命名, 不影响色值正确性。
NEUTRAL_HINTS = {
    "#ffffff": "纯白", "#000000": "纯黑", "#f5f0e8": "暖白", "#ebe4d4": "米白",
    "#ece8df": "浅米", "#fafaf6": "近白", "#f9f5ed": "纸白", "#f8f4ee": "浅纸",
    "#faf9f6": "米白", "#fbfaf5": "本白", "#f0f0f0": "冷白", "#fefefe": "白",
    "#f0f5fa": "浅蓝白", "#f0f4fa": "浅蓝白", "#fff8e7": "暖白", "#fef3c7": "琥珀白",
    "#f0fdf4": "浅绿白", "#dcdcdc": "浅灰", "#b0b0b0": "中灰", "#6b6b6b": "深灰",
    "#555555": "暗灰", "#8b8b8b": "灰",
}

BORDER = "=" * 72


def hexes(text: str) -> Counter:
    c = Counter()
    for m in HEX.finditer(text):
        c[m.group(0).lower()] += 1
    return c


def luminance(hex_color: str) -> float:
    """WCAG 相对亮度。用来猜"这个色是底还是字"。"""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def classify(hex_color: str, base: str) -> tuple[str, str]:
    """给色值一个 (token 名, 用途) —— 纯启发式, 猜不准也不影响正确性。"""
    lum = luminance(hex_color)
    ratio = contrast(hex_color, base)
    if hex_color in NEUTRAL_HINTS:
        return ("ink-light" if lum > 0.5 else "ink-dim",
                NEUTRAL_HINTS[hex_color] + ("（亮）" if lum > 0.5 else "（暗）"))
    if lum < 0.06:
        return "ground", "主底"
    if lum < 0.25:
        return ("ground-alt" if ratio < 3 else "accent-deep"), "面/深强调"
    if lum > 0.85:
        return "ink-bright", "主文字"
    return "accent", "强调"


def build(name: str, base: str) -> str:
    pack_dir = PACKS / name
    used = Counter()
    for f in sorted(pack_dir.rglob("*.html")):
        used += hexes(f.read_text(encoding="utf-8"))

    # 主底 = 出现最多且最暗的色（版式的底通常是它）
    dark = [(h, n) for h, n in used.items() if luminance(h) < 0.1]
    base_hex = max(dark, key=lambda x: x[1])[0] if dark else "#0a0a0d"

    roles: dict[str, tuple[str, str]] = {}
    for h in sorted(used, key=lambda x: -used[x]):
        token, use = classify(h, base_hex)
        # 同 token 冲突时加序号, 不覆盖
        if token in roles:
            i = 2
            while f"{token}-{i}" in roles:
                i += 1
            token = f"{token}-{i}"
        roles[token] = (h, use)

    rows = "\n".join(
        f"| `{t}` | `{h.upper()}` | {u}（用 {used[h]} 次） |"
        for t, (h, u) in roles.items()
    )
    note = VARIANT_NOTE.get(name, "")
    diff = [h for h in sorted(used) if h not in hexes((PACKS / base / "frame.md").read_text(encoding="utf-8"))]

    return f"""{BORDER}
# {name} · frame.md（派生变体）

> 派生自 **`{base}`**。{note}
> 骨架（host.html + 7 个 composition）来自 master，本文件只覆盖**色板**。
> 派生关系记录在案，这样"这个变体为什么长这样"有据可查 —— 详见
> `routes/news/ARCHITECTURE.md` D16。

## 0. 派生声明

| 项 | 值 |
|---|---|
| `derived_from` | `{base}` |
| 变体名 | `{name}` |
| 视觉气质 | {note or '（见名称）'} |
| 与 master 的差异色 | {', '.join(f'`{h.upper()}`' for h in diff) if diff else '无（仅继承）'} |

## 1. 色板（本包真实用色）

> 色板表由 `routes/news/scripts/gen_variant_frames.py` 按本包 HTML 里的**真实色值**生成，
> 不手抄、不预填（ARCHITECTURE D10 的教训：手抄的"实测值"会直接变成播出事故）。
> 改版式用色后重跑该脚本 + `audit_pack_contrast.py`。

| token | 值 | 用途 |
|---|---|---|
{rows}

### 1.1 强制规则

1. **本表是本包色板的唯一事实源** —— 版式里出现表外的 hex 就是设计系统开始漏，
   `audit_pack_contrast.py` 会抓 `OFF_PALETTE_HEX` 并红。
2. **底色是 `{base_hex.upper()}`**（本包用得最多的暗色）；强调色见上表 `accent*` 行。
3. 派生变体**不覆盖 master 的版面法则**（字阶、动量预算、屏句规则一律沿用 `{base}` 的 frame.md），
   本文件只管色板 —— 版面契约的唯一事实源仍是 `{base}/frame.md`。
{BORDER}
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="为派生变体生成 frame.md")
    ap.add_argument("--dry-run", action="store_true", help="只打印要写什么, 不落盘")
    args = ap.parse_args()

    missing = [n for n in VARIANT_BASE if not (PACKS / n / "frame.md").is_file()]
    if not missing:
        print("20 个变体的 frame.md 都已存在, 无事可做")
        return 0

    for name in sorted(missing):
        base = VARIANT_BASE[name]
        if not (PACKS / base / "frame.md").is_file():
            print(f"  ! 跳过 {name}: master {base} 没有 frame.md")
            continue
        text = build(name, base)
        if args.dry_run:
            print(f"--- {name} (from {base}) ---")
            print(text[:300])
        else:
            (PACKS / name / "frame.md").write_text(text, encoding="utf-8")
            print(f"  wrote {name}/frame.md")

    if not args.dry_run:
        print(f"\n[gen_variant_frames] 写 {len(missing)} 个 frame.md")
        print("下一步:")
        print("  python skills/douyin-pro/scripts/audit_pack_contrast.py   # 色板复算")
        print("  python skills/douyin-pro/scripts/path_b_selftest.py        # 全量断言")
    return 0


if __name__ == "__main__":
    sys.exit(main())
