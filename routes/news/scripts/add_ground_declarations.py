#!/usr/bin/env python3
"""一次性脚本：把渲染器已登记、但 frame.md 未声明的地面色补进色板表。

背景（2026-10-08, D19 收尾）: 修复制残留时误把 3 个包的 `#root` 地面色也换了
（`news-blast` 球场绿当整片底、`news-takes` 换成未登记色导致渲染器停机），
回滚后发现这三个地面色 `#1a0808` / `#0c0c10` / `#0a1018`
**在 path_b_build.GROUND_TONE_BY_HEX 里已登记**（渲染器认），
**但在本包 frame.md 色板表里没声明**（审计不认）—— 两套登记表口径不一致。

修法不是改地面色（会让整片视觉变样），也不是改渲染器（会破坏逐镜换地面），
而是**把地面色补进各包色板表**：它本来就是该包合法的设计色，缺的只是文档。
这也正是 D19 里"剩余越界应补进 frame.md 算设计补全"那一条。
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKS = ROOT / "skills" / "douyin-pro" / "templates" / "hyperframes_path_b"

#: pack → (token 名, 色值, 用途)。色值取自 GROUND_TONE_BY_HEX（渲染器已登记）。
ADDITIONS = {
    "news-blast": ("pitch-ground", "#1A0808", "球场深底（绿黑，整片地面）"),
    "news-takes": ("ink-ground", "#0C0C10", "墨黑底（近纯黑，观点域地面）"),
    "news-world": ("navy-ground", "#0A1018", "深海军蓝底（国际域地面）"),
}

ROW_RE = re.compile(r"^\|\s*`[a-z0-9-]+`\s*\|\s*`#[0-9a-fA-F]{3,6}`")


def main() -> int:
    sys.path.insert(0, str(ROOT / "skills" / "douyin-pro" / "scripts"))
    import audit_pack_contrast as apc
    import path_b_build as pb

    for pack, (token, value, use) in ADDITIONS.items():
        hx = apc._normalize_hex(value)
        # 前置校验: 渲染器必须已登记这个色，否则补了也不该渲
        assert hx in {apc._normalize_hex(k) for k in pb.GROUND_TONE_BY_HEX}, (
            f"{pack} 的 {value} 未在 GROUND_TONE_BY_HEX 登记，"
            f"先改渲染器再补文档（顺序反了会渲不出来）")

        frame = PACKS / pack / "frame.md"
        text = frame.read_text(encoding="utf-8")
        if f"`{token}`" in text:
            print(f"  {pack}: {token} 已声明，跳过")
            continue

        lines = text.splitlines()
        # 插在色板表最后一行之后（表头下一行是分隔行，数据行以 "| `token` | `#" 开头）
        last = None
        for i, line in enumerate(lines):
            if ROW_RE.match(line):
                last = i
        if last is None:
            print(f"  ! {pack}: 找不到色板表数据行，跳过")
            continue
        lines.insert(last + 1, f"| `{token}` | `{value}` | {use} |")
        frame.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"  {pack}: 补 {token} {value}")

    print("\n[补声明] 完成，复跑：audit_pack_contrast / path_b_selftest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
