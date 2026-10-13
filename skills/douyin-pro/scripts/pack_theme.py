#!/usr/bin/env python3
r"""pack_theme — frame.md 色板表 → theme.toml（Vue 路的主题真源）。

frame.md 是给人读的表（spec §2：31/31 可机器解析），theme.toml 是给发射器和
Vite 读的。真源仍是 frame.md：本模块每次抽取都以 frame.md 为准，串色闸
（Task 3）保证 theme.toml 不漂出它。

只认标题含「色板」的小节：实测 31 包的 398 行色板全在这类小节里，
而 `| \`名字\` | \`#hex\` |` 这个表格形状并不为色板独有——不限定小节，
将来任何一张同形状的表都会被误当成 token 源。
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

THEME_FILENAME = "theme.toml"

#: 形如 | `coral` | `#E85D5D` | 用途 | —— token 名列 + 值列必须是 hex。
_ROW_RE = re.compile(
    r"^\|\s*`(?P<name>[A-Za-z0-9][A-Za-z0-9_-]*)`\s*\|\s*"
    r"`(?P<hex>#[0-9a-fA-F]{3,8})`\s*\|",
    re.MULTILINE,
)

#: 只认标题含「色板」的 `##` 小节。
_PALETTE_KEYWORD = "色板"


def parse_frame_md_palette(text: str) -> dict[str, str]:
    """色板小节 → {token 名: 小写 hex}。同名后出现的覆盖前面的（frame.md 不重复列名）。"""
    palette: dict[str, str] = {}
    in_palette = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_palette = _PALETTE_KEYWORD in line
            continue
        if not in_palette:
            continue
        match = _ROW_RE.match(line)
        if match:
            palette[match.group("name")] = match.group("hex").lower()
    return palette


def write_theme(pack_dir: str) -> str:
    pack = Path(pack_dir)
    palette = parse_frame_md_palette((pack / "frame.md").read_text(encoding="utf-8"))
    if not palette:
        raise ValueError(f"{pack}: frame.md 里没解析到任何色板行（小节标题须含「色板」）")
    lines = [
        "# 编译产物：由 pack_theme.write_theme 从 frame.md 色板表生成，勿手改。",
        "schema = \"news-theme/1\"",
        "",
        "[tokens]",
    ]
    lines += [f'{name} = "{hex_value}"' for name, hex_value in palette.items()]
    out = pack / THEME_FILENAME
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(out)


def load_theme(pack_dir: str) -> dict[str, str]:
    path = Path(pack_dir) / THEME_FILENAME
    with path.open("rb") as fh:
        raw = tomllib.load(fh)
    return {str(k): str(v).lower() for k, v in raw.get("tokens", {}).items()}
