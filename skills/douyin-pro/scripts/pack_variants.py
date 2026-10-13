#!/usr/bin/env python3
"""pack_variants — 每角色的真实结构变体簇（spec §6 判据 0a）。

今天用 md5 抽样量到「每角色 2 变体」，但那是抽样结论。本脚本把它变成逐行证据：
去掉硬编码色值、data-composition-id 字面量、__timelines 键名与首尾空白后聚类，
簇数 = Phase 1 需要的组件数下界。簇数 > 2 的角色照实报，不压缩。
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import path_b_build as pb

ROLE_ORDER = ("hook", "stat", "rail", "quote", "catalog", "story", "closer")

_SUBS = (
    (re.compile(r"#[0-9a-fA-F]{3,8}\b"), ""),
    (re.compile(r"rgba?\([^)]*\)"), ""),
    (re.compile(r'data-composition-id="[^"]*"'), 'data-composition-id="ID"'),
    (re.compile(r'__timelines\["[^"]*"\]'), '__timelines["ID"]'),
)


def normalize(text: str) -> str:
    """去色 / 去 id 字面量 / 逐行首尾空白。空行保留 —— 它们是有结构的空白，不是噪声。"""
    for pattern, repl in _SUBS:
        text = pattern.sub(repl, text)
    return "\n".join(line.strip() for line in text.splitlines())


def _pack_dir(style: str) -> Path:
    return Path(pb.pack_dir(style))


def cluster_role(role: str) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {}
    for style in pb.ALL_TEMPLATES:
        path = _pack_dir(style) / "compositions" / f"{role}.html"
        if not path.is_file():
            continue
        fingerprint = hashlib.md5(
            normalize(path.read_text(encoding="utf-8")).encode("utf-8")
        ).hexdigest()[:12]
        buckets.setdefault(fingerprint, []).append(style)
    return buckets


def report() -> str:
    lines = ["# 每角色变体簇（判据 0a）", "",
             "口径：去硬编码色值 / `data-composition-id` 字面量 / `__timelines` 键名 / 首尾空白后聚 md5。",
             "", "| 角色 | pack 数 | 簇数 | 簇规模（降序） |", "|---|---|---|---|"]
    total = 0
    for role in ROLE_ORDER:
        buckets = cluster_role(role)
        sizes = sorted((len(v) for v in buckets.values()), reverse=True)
        total += len(buckets)
        lines.append(f"| `{role}` | {sum(sizes)} | {len(buckets)} | {sizes} |")
    lines += ["", f"**组件数下界 = {total}**（spec 里写的 14 是抽样推定，以本表为准）。", ""]
    for role in ROLE_ORDER:
        # 列的是**少数簇**（结构偏离主流的那些包）。
        # 不能按 `len(styles) == len(ALL_TEMPLATES)` 判主流：实测每角色都是 [30, 1]，
        # 30 < 31，那个条件永远不成立 —— 会把 30 包的主流簇说成「非主流」，
        # 同时把真正的结构少数派（1 包的 news-policy）用 `<= 1` 滤掉，正好说反。
        # 口径改为「按规模降序，除最大簇外逐条列出」，1 包的孤簇正是要报的发现，不滤。
        buckets = sorted(cluster_role(role).values(), key=len, reverse=True)
        for styles in buckets[1:]:
            lines.append(f"- `{role}` 少数簇（{len(styles)} 包）: {', '.join(sorted(styles))}")
    return "\n".join(lines) + "\n"
