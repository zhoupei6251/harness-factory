#!/usr/bin/env python3
"""pack_variants — 每角色的真实结构变体簇（spec §6 判据 0a）。

今天用 md5 抽样量到「每角色 2 变体」，但那是抽样结论。本脚本把它变成逐行证据：
去掉硬编码色值、data-composition-id 字面量、__timelines 键名与首尾空白后聚类，
簇数 = Phase 1 需要的组件数下界。簇数 > 2 的角色照实报，不压缩。
"""
from __future__ import annotations

import difflib
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


def _role_text(role: str, style: str) -> str:
    return (_pack_dir(style) / "compositions" / f"{role}.html").read_text(encoding="utf-8")


def _cluster(role: str, transform) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {}
    for style in pb.ALL_TEMPLATES:
        path = _pack_dir(style) / "compositions" / f"{role}.html"
        if not path.is_file():
            continue
        fingerprint = hashlib.md5(
            transform(path.read_text(encoding="utf-8")).encode("utf-8")
        ).hexdigest()[:12]
        buckets.setdefault(fingerprint, []).append(style)
    return buckets


def cluster_role(role: str) -> dict[str, list[str]]:
    """归一化口径下的簇（口径本体见 normalize / _SUBS，此处不动它）。"""
    return _cluster(role, normalize)


def cluster_role_raw(role: str) -> dict[str, list[str]]:
    """与 cluster_role 同一批包、同一套指纹算法，唯一区别是**不归一化**。

    这条不是第二个口径，是给自测闸用的对照面：「归一化确实在塌东西」必须
    能被逐角色量出来（如 stat 原始 31 簇 → 归一化 2 簇），否则口径被放宽
    或收紧时测试没有区分力（审查发现 F1）。
    """
    return _cluster(role, lambda text: text)


def diff_line_count(a: str, b: str) -> int:
    """两份已归一化文本之间的 diff 行数（增 + 删，difflib.ndiff 的 +/- 行）。"""
    return sum(
        1
        for line in difflib.ndiff(a.splitlines(), b.splitlines())
        if line.startswith("+ ") or line.startswith("- ")
    )


def minority_diff_lines(role: str) -> list[tuple[int, int]]:
    """每个少数簇代表 vs 主流簇代表的归一化 diff 行数：[(少数簇规模, 行数), ...]。

    簇内文本归一化后逐字节相同，所以取哪个代表做 diff 结果都一样（确定性）。
    用途见报告 F2：`stat` 的 policy 簇只差 4 行动画参数、`closer` 差 276 行，
    两者都算「1 个变体」，但工作量完全不是一回事 —— 表里必须把这列摊开。
    """
    buckets = sorted(cluster_role(role).values(), key=len, reverse=True)
    if len(buckets) < 2:
        return []
    major_text = normalize(_role_text(role, buckets[0][0]))
    result = []
    for styles in buckets[1:]:
        minor_text = normalize(_role_text(role, styles[0]))
        result.append((len(styles), diff_line_count(major_text, minor_text)))
    return result


def report() -> str:
    lines = ["# 每角色变体簇（判据 0a）", "",
             "口径：去硬编码色值 / `data-composition-id` 字面量 / `__timelines` 键名 / 首尾空白后聚 md5。",
             "",
             "| 角色 | pack 数 | 簇数 | 簇规模（降序） | 少数簇 vs 主流簇 diff 行数（归一化后） |",
             "|---|---|---|---|---|"]
    total = 0
    for role in ROLE_ORDER:
        buckets = cluster_role(role)
        sizes = sorted((len(v) for v in buckets.values()), reverse=True)
        total += len(buckets)
        gaps = ", ".join(f"{n} 包: {d} 行" for n, d in minority_diff_lines(role)) or "—"
        lines.append(f"| `{role}` | {sum(sizes)} | {len(buckets)} | {sizes} | {gaps} |")
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
