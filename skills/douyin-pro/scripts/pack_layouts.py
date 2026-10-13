#!/usr/bin/env python3
"""pack_layouts — 版式登记表（spec §3：发射器现在的版式元数据长在 HTML 里）。

删掉 compositions/*.html 之后，发射器仍需知道每个版式的
composition_id / 变量契约 id / 地面色 / 地面明暗。这四样现在由
load_style_pack() 从 HTML 正则抠出来；本模块把它们落成 layouts.toml，
P3 改读这里。真源在 P3 之前仍是 HTML —— verify_pack 负责证明两边没分家。
"""
from __future__ import annotations

import tomllib
from pathlib import Path

LAYOUTS_FILENAME = "layouts.toml"

#: 落到登记表里的字段。HTML 里的 path/file_name 是过渡期才有的东西，不进来。
FIELDS = ("composition_id", "ground_hex", "ground_tone")


def _toml_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_layouts(pack_dir: str, pack: dict) -> str:
    lines = [
        "# 编译产物：由 pack_layouts.write_layouts 从 compositions/*.html 抽出，勿手改。",
        "schema = \"news-layouts/1\"",
        "",
    ]
    for role in sorted(pack["layouts"]):
        layout = pack["layouts"][role]
        lines.append(f"[layouts.{role}]")
        for field in FIELDS:
            lines.append(f"{field} = {_toml_str(str(layout[field]))}")
        ids = [var["id"] for var in layout["variables"]]
        lines.append("variable_ids = [" + ", ".join(_toml_str(i) for i in ids) + "]")
        lines.append("")
    out = Path(pack_dir) / LAYOUTS_FILENAME
    out.write_text("\n".join(lines), encoding="utf-8")
    return str(out)


def load_layouts(pack_dir: str) -> dict[str, dict]:
    with (Path(pack_dir) / LAYOUTS_FILENAME).open("rb") as fh:
        raw = tomllib.load(fh)
    return {role: dict(rec) for role, rec in raw.get("layouts", {}).items()}


def verify_pack(pack_dir: str, live_pack: dict) -> list[str]:
    """layouts.toml 与 load_style_pack() 当次读出的逐字段相等（等价闸）。"""
    path = Path(pack_dir) / LAYOUTS_FILENAME
    if not path.exists():
        return [f"{Path(pack_dir).name}: 缺 {LAYOUTS_FILENAME}"]
    got = load_layouts(pack_dir)
    live = live_pack["layouts"]
    problems = [f"{Path(pack_dir).name}: 登记表缺版式 {role}" for role in set(live) - set(got)]
    problems += [f"{Path(pack_dir).name}: 登记表多出版式 {role}" for role in set(got) - set(live)]
    for role in set(got) & set(live):
        rec, want = got[role], live[role]
        for field in FIELDS:
            if str(rec.get(field)) != str(want[field]):
                problems.append(f"{Path(pack_dir).name}/{role}: {field} "
                                f"登记表={rec.get(field)} != HTML={want[field]}")
        if list(rec.get("variable_ids", [])) != [v["id"] for v in want["variables"]]:
            problems.append(f"{Path(pack_dir).name}/{role}: variable_ids 不一致")
    return problems
