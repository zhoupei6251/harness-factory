#!/usr/bin/env python3
r"""pack_theme — frame.md 色板表 → theme.toml（Vue 路的主题真源）。

frame.md 是给人读的表（spec §2：31/31 可机器解析），theme.toml 是给发射器和
Vite 读的。真源仍是 frame.md：本模块每次抽取都以 frame.md 为准，串色闸
（Task 3）保证 theme.toml 不漂出它。

只认标题含「色板」的小节：实测 31 包的 398 行色板全在这类小节里，
而 `| \`名字\` | \`#hex\` |` 这个表格形状并不为色板独有——不限定小节，
将来任何一张同形状的表都会被误当成 token 源。
任意标题行（`#`、`##`、`###`…）都结束当前小节：色板 `##` 下的 `###` 子小节
（如 news-alert 的 `### 2.1 对比度`）里有的是同形状表，不属于 token 源。
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
        if line.startswith("#"):
            # 任意标题行都是小节边界：`### 2.1 对比度` 这类子小节不能留在色板作用域里，
            # 否则它下面的同形状表会被当成 token 源（表格行都以 `|` 开头，不会被误判）。
            in_palette = line.startswith("## ") and _PALETTE_KEYWORD in line
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


def verify_pack(pack_dir: str) -> list[str]:
    """theme.toml 必须与同目录 frame.md 色板表逐条相等（串色闸）。"""
    pack = Path(pack_dir)
    expected = parse_frame_md_palette((pack / "frame.md").read_text(encoding="utf-8"))
    if not expected:
        return [f"{pack.name}: frame.md 色板表解析为空 —— 闸等于没设"]
    if not (pack / THEME_FILENAME).exists():
        return [f"{pack.name}: 缺 {THEME_FILENAME}"]
    actual = load_theme(str(pack))
    problems = []
    for name, hex_value in expected.items():
        got = actual.get(name)
        if got is None:
            problems.append(f"{pack.name}: frame.md 有 `{name}`={hex_value} 但 theme.toml 缺")
        elif got != hex_value:
            problems.append(f"{pack.name}: `{name}` theme.toml={got} != frame.md={hex_value}")
    for name in actual:
        if name not in expected:
            problems.append(f"{pack.name}: theme.toml 有 `{name}` 但 frame.md 色板表里没有（凭空多出的 token）")
    return problems
