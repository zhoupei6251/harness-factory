#!/usr/bin/env python3
"""一次性脚本：把 master 包的版式 HTML 用色重映射到本包色板。

背景（2026-10-08, D17）: `audit_pack_contrast.py` 报出 **561 条 OFF_PALETTE_HEX**,
12 个包全中，每个包 8 个文件各占固定条数。真因不是"用错几个色", 而是
**12 个包的骨架都从 news-coral 复制而来, 换了主色却保留了 coral 的辅助色**:
  - 色板吻合度实测: news-policy 88% / news-coral 72.7% / 其余 8 包 20~30%
    / news-world **7.2%** / news-alert **11.6%**
  - 越界色全是 coral 系: #ebe4d4 #f5f0e8 #e85d5d #6b6b6b #b0b0b0 #ffffff …

映射策略（**按角色，不按色值**）—— 盲目按 hex 替换会把亮色映到暗底上，直接毁掉对比度：
  1. 读目标包 frame.md 的色板表，得到本包真实 token（ground / 面 / 字 / 强调）
  2. 越界色按其自身亮度归类为「暗底 / 亮字 / 中间调 / 强调」
  3. 同角色映射到本包最近的同角色 token
  4. **每个替换点都验一次对比度**：新组合 < 3.0 则保留原值并记入 skipped
     —— 设计系统的底线是"能播"，不是"审计绿"

用法:
    python routes/news/scripts/remap_pack_colors.py --dry-run   # 只看计划
    python routes/news/scripts/remap_pack_colors.py             # 落盘

落盘后必须复跑三道闸:
    python skills/douyin-pro/scripts/audit_pack_contrast.py
    python skills/douyin-pro/scripts/layout_selfcheck.py <各 pack 目录>
    python skills/douyin-pro/scripts/path_b_selftest.py
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKS = ROOT / "skills" / "douyin-pro" / "templates" / "hyperframes_path_b"
HEX = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
PALETTE_HEADER = "| token | 值 |"

#: 对比度下限（改色后新组合必须达到这个值才允许落盘）
MIN_CONTRAST = 3.0


def luminance(hex_color: str) -> float:
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


def role(hex_color: str) -> str:
    """按亮度分四类角色。边界是 WCAG 惯用法, 不是本项目发明的。"""
    lum = luminance(hex_color)
    if lum < 0.06:
        return "ground"      # 底色
    if lum < 0.30:
        return "surface"     # 面 / 深强调
    if lum > 0.72:
        return "ink"         # 亮字
    return "mid"            # 中间调 / 强调


def read_palette(pack_dir: Path) -> dict[str, str]:
    """读 frame.md 的色板表 → {token: hex}。只认 '| token | 值 |' 表头。"""
    text = (pack_dir / "frame.md").read_text(encoding="utf-8")
    if PALETTE_HEADER not in text:
        return {}
    sec = text.split(PALETTE_HEADER, 1)[1].split("\n###", 1)[0]
    out = {}
    for line in sec.splitlines():
        m = re.match(r"\s*\|\s*`([a-z0-9-]+)`\s*\|\s*`?(#[0-9a-fA-F]{3,6})`?\s*\|", line)
        if m:
            out[m.group(1)] = m.group(2).lower()
    return out


def build_map(target_palette: dict[str, str], off_hexes: set[str]) -> tuple[dict[str, str], dict]:
    """越界色 → 本包 token。返回 (映射表, 统计)。"""
    by_role: dict[str, list[tuple[str, str]]] = {}
    for token, hx in target_palette.items():
        by_role.setdefault(role(hx), []).append((token, hx))

    mapping: dict[str, str] = {}
    stats = {"by_role": {}, "no_target": [], "low_contrast_skipped": []}

    # 本包底色: 最暗且 token 名带 ground/底 优先, 否则取最暗
    grounds = by_role.get("ground", [])
    base = None
    for t, hx in grounds:
        if "ground" in t or "底" in t:
            base = hx
            break
    if base is None and grounds:
        base = grounds[0][1]

    for hx in sorted(off_hexes):
        r = role(hx)
        cands = by_role.get(r, [])
        if not cands:
            stats["no_target"].append(hx)
            continue
        # 同角色里挑**对比度最高**的那个（与原色的对比关系尽量接近）
        best = max(cands, key=lambda th: contrast(hx, th[1]))
        # 底色特例: 任何色都该与底可读
        if base:
            ratio = contrast(best[1], base)
            if ratio < MIN_CONTRAST and r != "ground":
                alt = [c for c in cands if contrast(c[1], base) >= MIN_CONTRAST]
                if alt:
                    best = max(alt, key=lambda th: contrast(hx, th[1]))
                else:
                    stats["low_contrast_skipped"].append((hx, best[1], round(ratio, 2)))
                    continue
        mapping[hx] = best[1]
        stats["by_role"].setdefault(r, []).append((hx, best[1], best[0]))
    return mapping, stats


def main() -> int:
    ap = argparse.ArgumentParser(description="把 master 版式用色重映射到本包色板")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default=None, help="只处理某个包")
    args = ap.parse_args()

    all_stats = {}
    for pack_dir in sorted(p for p in PACKS.iterdir() if p.is_dir()):
        name = pack_dir.name
        if args.only and name != args.only:
            continue
        palette = read_palette(pack_dir)
        if not palette:
            print(f"  ! {name}: frame.md 没有可解析的色板表, 跳过")
            continue

        # 收集本包 HTML 里色板外的 hex
        used = {}
        for f in sorted(pack_dir.rglob("*.html")):
            for m in HEX.finditer(f.read_text(encoding="utf-8")):
                hx = m.group(0).lower()
                if hx not in {v.lower() for v in palette.values()}:
                    used.setdefault(hx, set()).add(f.relative_to(pack_dir).as_posix())
        if not used:
            continue

        mapping, stats = build_map(palette, set(used))
        all_stats[name] = (used, mapping, stats)

        total = sum(len(v) for v in used.values())
        print(f"\n{name}: 色板外 {total} 处 / {len(used)} 色 → 映射 {len(mapping)} 色")
        for r, items in stats["by_role"].items():
            detail = ", ".join(f"{a}→{b}({t})" for a, b, t in items[:4])
            print(f"    {r:8} {len(items):2} 色: {detail}{' …' if len(items) > 4 else ''}")
        if stats["no_target"]:
            print(f"    ⚠ 本包色板里没有同角色目标, 保留原值: {stats['no_target']}")
        if stats["low_contrast_skipped"]:
            for hx, tgt, ratio in stats["low_contrast_skipped"]:
                print(f"    ⚠ 对比度不足({ratio}), 保留原值: {hx}（候选 {tgt}）")

        if args.dry_run:
            continue

        # 落盘: 逐文件替换, 大小写不敏感
        changed_files = 0
        for f in sorted(pack_dir.rglob("*.html")):
            text = f.read_text(encoding="utf-8")
            orig = text

            def sub(m):
                hx = m.group(0).lower()
                return mapping.get(hx, m.group(0))

            text = HEX.sub(sub, text)
            if text != orig:
                f.write_text(text, encoding="utf-8")
                changed_files += 1
        print(f"    → 改写 {changed_files} 个文件")

    if args.dry_run:
        print("\n[dry-run] 未写盘。去掉 --dry-run 落盘，然后复跑三道闸。")
    else:
        print("\n[remap] 落盘完成。必须复跑：")
        print("  python skills/douyin-pro/scripts/audit_pack_contrast.py")
        print("  python skills/douyin-pro/scripts/path_b_selftest.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
