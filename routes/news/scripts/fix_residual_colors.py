#!/usr/bin/env python3
"""一次性脚本：把 master / 变体版式里的**复制残留色**换成本包色板的色。

背景（2026-10-08, D19）: 共享 token 层（D18）把 OFF_PALETTE 从 561 降到 72，
剩下的 72 条收敛得极其整齐 —— 10 个包 × 4 个版式（stat/rail/closer/catalog），
每包每文件 2 条，实测 27 个**去重色值**。逐条看语义后判定：

  - **26 个是复制残留**。例：`news-alert`（警示红包）的 `st-rule` 强调短横线写成
    `#ea580c`（橙）—— 该包色板里根本没有橙色，强调色是 `alert` 红 `#D7263D`。
    这类色与本包某色的**亮度差 < 0.12、对比 1.0~1.7**，即"本来就该是那个色，
    复制时忘了改主色"。
  - **1 个需要单独判断**：`news-bulletin` 的 `#6366f1`（靛蓝），该包 27 个色里
    最接近的是 `#9a9a9a`（灰），亮度差 0.138 偏大 → 不自动换，见 --manual。

替换口径（**按 CSS 角色，不按亮度** —— 这是两次踩坑换来的）:

  早先第一版按"亮度分四类角色"全局重映射（remap_pack_colors.py），dry-run 就暴露它会毁掉语义：
  `news-alert` 的次级灰 `#6b6b6b` 被映成 ok 绿 `#3fa34d`、`news-ink` 的警示红被映成灰。
  第二版改成"同亮度本包色"，**又踩一次**：`#1a0808`(深底) 按亮度映到 `#a11d2e`(深红)、
  `#ea580c`(橙色强调短横线) 映到 `#3fa34d`(ok 绿) —— 亮度接近但**角色完全不同**。

  实测 CSS 结构给出的正解（2026-10-08）: 残留色全部出现在
  `background:` 上，且分两类，与类名对应得很干净:
    · `.st-rule` / `.rl-*` 之类 → **强调色**（短横线、分隔标），该映射到本包
      「强调 / 形状」类 token（alert→alert 红, onsite→time-on, stat→gold）
    · 其余 `background:` → **面 / 底色**，该映射到本包 ground / surface 类 token
  所以判据是 **CSS 属性 + token 名的语义**，亮度只用作同角色内的候选排序。
  任何映射后对比度不得低于替换前（不许越改越看不清）。

用法:
    python routes/news/scripts/fix_residual_colors.py --dry-run
    python routes/news/scripts/fix_residual_colors.py --apply
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKS = ROOT / "skills" / "douyin-pro" / "templates" / "hyperframes_path_b"
HEX = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")

#: 已定位的 4 个版式（D19 实测：残留全部集中在这里，别的文件干净）
TARGET_LAYOUTS = ("stat.html", "rail.html", "closer.html", "catalog.html")

#: token 名 → 语义角色。**只认这些词**，认不出就跳过（不猜）。
#: 依据是各包 frame.md 的实际命名（black-soft/ground/rule/pitch/paper …）。
ROLE_GROUND = "ground"      # 底
ROLE_SURFACE = "surface"    # 面 / 卡底
ROLE_ACCENT = "accent"      # 强调（只作形状的那一类）
ROLE_INK = "ink"            # 文字

TOKEN_ROLE_RULES = (
    # 顺序有意义: 先匹配更具体的, 避免 "black-soft" 里的 soft 之类误判
    (("ground", "底色", "ink", "bg-main"), ROLE_GROUND),
    (("surface", "card", "black-soft", "panel", "navy-soft", "pitch", "ink-soft"),
     ROLE_SURFACE),
    (("rule", "line", "divider", "alert", "warn", "press", "time-on", "gold",
      "accent", "score", "crimson", "red", "ok", "pen", "coral", "warn", "gilt"),
     ROLE_ACCENT),
    (("white", "paper", "cream", "ink-bright", "fg", "text", "muted", "mute",
      "gray", "grey", "cool-gray", "dim", "secondary"), ROLE_INK),
)


def token_role(token: str) -> str | None:
    t = token.lower()
    for keys, role in TOKEN_ROLE_RULES:
        if any(k in t for k in keys):
            return role
    return None


def css_role_of_occurrence(text: str, hex_value: str) -> str:
    """看这个 hex 在 CSS 里扮演什么角色。

    判据是**声明所在行 + 其上方最近的 class**：`.st-rule { background: #ea580c }`
    是强调短横线 → accent；`background: #1a0808` 出现在别的 class → surface。
    """
    lines = text.splitlines()
    target = norm(hex_value)
    for i, line in enumerate(lines):
        if target not in norm(line):
            continue
        # 往上找最近的 class 名（形如 `.xxx {`）
        cls = ""
        for j in range(i - 1, max(-1, i - 12), -1):
            m = re.search(r"\.(?:[a-z0-9-]+)\s*(?:,|\{)", lines[j], re.I)
            if m:
                cls = re.search(r"\.([a-z0-9-]+)", lines[j], re.I).group(1).lower()
                break
        # rule / line / divider 语义 = 强调形状
        if any(k in cls for k in ("rule", "line", "divider", "bar", "accent", "under")):
            return "accent"
        prop = "background" if "background" in line else (
            "color" if "color" in line else "other")
        if prop == "background":
            return "surface"
        if prop == "color":
            return "ink"
        return "surface"
    return "surface"


def lum(h: str) -> float:
    b = h.lstrip("#")
    if len(b) == 3:
        b = "".join(c * 2 for c in b)
    r, g, bl = (int(b[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(bl)


def ratio(a: str, b: str) -> float:
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def norm(h: str) -> str:
    b = h.lstrip("#")
    if len(b) == 3:
        b = "".join(c * 2 for c in b)
    return b.lower()


def local_palette(pack_dir: Path) -> dict[str, str]:
    text = (pack_dir / "frame.md").read_text(encoding="utf-8")
    parts = text.split("| token | 值 |", 1)
    if len(parts) < 2:
        return {}
    body = parts[1].split("\n###", 1)[0]
    out = {}
    for m in re.finditer(r"\|\s*`([a-z0-9-]+)`\s*\|\s*`?(#[0-9a-fA-F]{3,6})`?\s*\|",
                         body):
        out[norm(m.group(2))] = m.group(1)
    return out


def ground_of(pack_dir: Path, pal: dict[str, str]) -> str:
    """本包底色 = token 名带 ground/底 优先，否则取最暗。"""
    named = [h for h, t in pal.items() if "ground" in t or "底" in t]
    if named:
        return min(named, key=lum)
    return min(pal, key=lum) if pal else "#000000"


def collect_violations() -> dict[str, set[str]]:
    out = subprocess.run(
        ["python", str(ROOT / "skills/douyin-pro/scripts/audit_pack_contrast.py")],
        capture_output=True, text=True, encoding="utf-8", cwd=ROOT).stdout
    viol: dict[str, set[str]] = {}
    for line in out.splitlines():
        m = re.match(r"([a-z0-9-]+):OFF_PALETTE_HEX:违规 —— \S+ 用了色板外的 (#[0-9a-fA-F]{3,6})",
                     line)
        if m:
            viol.setdefault(m.group(1), set()).add(norm(m.group(2)))
    return viol


def main() -> int:
    ap = argparse.ArgumentParser(description="把复制残留色换成本包色板色")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true", help="真落盘（必须显式给）")
    args = ap.parse_args()
    if not (args.dry_run or args.apply):
        ap.error("必须显式给 --dry-run 或 --apply")

    viol = collect_violations()
    if not viol:
        print("没有 OFF_PALETTE_HEX，无需处理")
        return 0

    plan, manual, skipped = [], [], []
    for pack, hexes in sorted(viol.items()):
        pack_dir = PACKS / pack
        pal = local_palette(pack_dir)
        if not pal:
            skipped.append(f"{pack}: frame.md 色板表解析不到")
            continue
        base = ground_of(pack_dir, pal)
        # 本包里按语义角色分组的 token
        by_role: dict[str, list[str]] = {}
        for hx, tok in pal.items():
            r = token_role(tok)
            if r:
                by_role.setdefault(r, []).append(hx)

        for hx in sorted(hexes):
            # 收集该色在本包版式里扮演的角色（可能出现在多个 class）
            roles_seen = set()
            for name in TARGET_LAYOUTS:
                f = pack_dir / "compositions" / name
                if f.is_file():
                    roles_seen.add(css_role_of_occurrence(
                        f.read_text(encoding="utf-8"), hx))
            if not roles_seen:
                roles_seen = {"surface"}

            # 面/底角色允许同时用 surface + ground（深底也可能是卡底）
            want = set()
            for r in roles_seen:
                want.add(r)
                if r == "surface":
                    want.add(ROLE_GROUND)

            cands: list[str] = []
            for r in want:
                cands.extend(by_role.get(r, []))
            cands = [c for c in cands if c != hx]
            if not cands:
                manual.append((pack, hx, "/".join(sorted(want)), "本包无同角色 token"))
                continue

            before = ratio(hx, base)
            # 同角色内按"对比度不降 + 亮度最接近"排序
            def score(c: str) -> tuple:
                r_after = ratio(c, base)
                ok = r_after >= before
                return (0 if ok else 1, -r_after, abs(lum(c) - lum(hx)))
            cands.sort(key=score)
            best = cands[0]
            after = ratio(best, base)
            if after < before:
                skipped.append(f"{pack} #{hx}: 换成 {best}({pal[best]}) 对比度下降 "
                               f"{before}→{after}")
                continue
            plan.append((pack, hx, best, pal[best], before, after,
                         ",".join(sorted(roles_seen))))

    print(f"可安全替换 {len(plan)} 色 · 需人工判断 {len(manual)} 色 · 跳过 {len(skipped)} 色\n")
    for pack, hx, tgt, token, before, after, roles in plan:
        print(f"  {pack:20} #{hx} → #{tgt} ({token:14}) 角色={roles:14} "
              f"对比 {before}→{after}")
    if manual:
        print("\n需人工判断:")
        for row in manual:
            print(f"  {row[0]:20} #{row[1]}  {row[2]}")
    if skipped:
        print("\n跳过:")
        for s in skipped:
            print(f"  ! {s}")

    if not args.apply:
        print("\n[dry-run] 未写盘。确认后加 --apply。")
        return 0

    changed = 0
    for pack, hx, tgt, *_ in plan:
        pack_dir = PACKS / pack
        for name in TARGET_LAYOUTS:
            f = pack_dir / "compositions" / name
            if not f.is_file():
                continue
            text = f.read_text(encoding="utf-8")
            new = HEX.sub(lambda m: tgt if norm(m.group(0)) == hx else m.group(0), text)
            if new != text:
                f.write_text(new, encoding="utf-8")
                changed += 1
    print(f"\n[fix] 改写 {changed} 个版式文件")
    print("复跑三道闸：audit_pack_contrast / layout_selfcheck / path_b_selftest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
