#!/usr/bin/env python3
"""pack_layouts — 版式登记表（spec §3：发射器现在的版式元数据长在 HTML 里）。

删掉 compositions/*.html 之后，发射器仍需知道每个版式的
composition_id / 变量契约 / 地面色 / 地面明暗。这四样现在由
load_style_pack() 从 HTML 正则抠出来；本模块把它们落成 layouts.toml，
P3 改读这里。真源在 P3 之前仍是 HTML —— verify_pack 负责证明两边没分家。

变量登记的是**整条契约**（`VAR_FIELDS`），不是只登记 id 序列。终审 I-2：
发射器实读的东西不止 id —— `var["type"]`（path_b_build.py:1937，决定走数字分支
还是文本分支）、`var.get("min")` / `var.get("max")`（:1942 / :1948，夹紧上下界）、
`var.get("default")`（:2154-2155，兜底取值）、`var.get("label")`（:1928，报错文案）。
只比 id 的话，HTML 里 type/default 漂了闸不红，而 P3 换源时 layouts.toml 也供不出
这两样 —— spec §6 判据 2 要的是「逐字段相等」，这里就按逐字段登记、逐字段比对。
"""
from __future__ import annotations

import tomllib
from pathlib import Path

LAYOUTS_FILENAME = "layouts.toml"

#: 落到登记表里的版式级字段。HTML 里的 path/file_name 是过渡期才有的东西，不进来。
FIELDS = ("composition_id", "ground_hex", "ground_tone")

#: 每个变量落进登记表的字段 —— 上面 docstring 里那五条就是发射器的实际消费面。
#: 顺序固定，所以产出字节确定；HTML 契约里出现这个集合之外的键时，生成侧直接抛、
#: 比对侧报问题，绝不静默丢字段（丢了就等于给那条漂移开闸）。
VAR_FIELDS = ("id", "type", "label", "default", "min", "max")


def static_layouts(pack: dict) -> dict:
    """把 ``layouts`` 收口到**静态支**（有 ``compositions/<role>.html`` 的那些）。

    Vue-only 版式（地基 Task 2 合并进来的）的真源是组件目录里的 ``contract.toml``，
    不是 HTML。让它进 ``layouts.toml`` 会造成同一份变量契约有两个登记处 —— 而本模块的
    全部意义是「登记表 == HTML」，多一个来源就等于把等价闸改成比抄写。
    所以生成侧直接拒，比对侧按这个口径收口（P3 换源后仍然成立：那时静态支读这张表，
    契约支读 contract.toml，两条各有唯一真源）。
    """
    return {role: layout for role, layout in pack["layouts"].items()
            if not layout.get("vue_only")}


def _toml_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _toml_value(value) -> str:
    """登记表现值域的标量写出（str / int / bool）。别的一律拒，不猜。"""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return _toml_str(value)
    raise ValueError(
        f"layouts.toml 不支持的变量字段类型 {type(value).__name__}: {value!r} —— "
        "契约里冒出了新形态的值，先决定它怎么登记，别让生成器替你猜。"
    )


def _variable_table(var: dict, where: str) -> str:
    extra = sorted(set(var) - set(VAR_FIELDS))
    if extra:
        raise ValueError(
            f"{where}: 变量 {var.get('id')!r} 带登记表覆盖不到的字段 {extra} —— "
            f"把它们补进 VAR_FIELDS 再重生成，否则这条漂移没有任何闸守着。"
        )
    body = ", ".join(f"{key} = {_toml_value(var[key])}" for key in VAR_FIELDS if key in var)
    return "{ " + body + " }"


def write_layouts(pack_dir: str, pack: dict) -> str:
    vue_only = sorted(role for role, layout in pack["layouts"].items()
                      if layout.get("vue_only"))
    if vue_only:
        raise ValueError(
            f"{Path(pack_dir).name}: 试图把 Vue-only 版式 {vue_only} 写进 {LAYOUTS_FILENAME} —— "
            "它们没有 compositions/*.html，契约在 src/web/entries/<bundle>/contract.toml。"
            "一张表两个真源等于把等价闸变成比抄写。")
    lines = [
        "# 编译产物：由 pack_layouts.write_layouts 从 compositions/*.html 抽出，勿手改。",
        "schema = \"news-layouts/2\"",
        "",
    ]
    for role in sorted(pack["layouts"]):
        layout = pack["layouts"][role]
        lines.append(f"[layouts.{role}]")
        for field in FIELDS:
            lines.append(f"{field} = {_toml_str(str(layout[field]))}")
        lines.append("variables = [")
        for var in layout["variables"]:
            lines.append(f"  {_variable_table(var, f'{Path(pack_dir).name}/{role}')},")
        lines.append("]")
        lines.append("")
    out = Path(pack_dir) / LAYOUTS_FILENAME
    out.write_text("\n".join(lines), encoding="utf-8")
    return str(out)


def load_layouts(pack_dir: str) -> dict[str, dict]:
    with (Path(pack_dir) / LAYOUTS_FILENAME).open("rb") as fh:
        raw = tomllib.load(fh)
    return {role: dict(rec) for role, rec in raw.get("layouts", {}).items()}


def _compare_variables(name: str, role: str, got_vars, want_vars) -> list[str]:
    """逐条逐个字段比：条数、顺序（按下标对齐，所以 id 序列也在这条上）、每个字段值。"""
    if not isinstance(got_vars, list):
        return [f"{name}/{role}: 登记表没有 variables 数组（HTML 有 {len(want_vars)} 条）"]
    problems: list[str] = []
    if len(got_vars) != len(want_vars):
        problems.append(
            f"{name}/{role}: 变量条数 登记表={len(got_vars)} != HTML={len(want_vars)}"
            " —— 条数都不等，逐条比对没有意义"
        )
    for index, (got, want) in enumerate(zip(got_vars, want_vars)):
        got_rec = dict(got) if isinstance(got, dict) else {}
        label = want.get("id", f"#{index}")
        place = f"{name}/{role}[{index}] {label}"
        unrecorded = sorted(set(want) - set(VAR_FIELDS))
        if unrecorded:
            problems.append(
                f"{place}: HTML 契约有登记表覆盖不到的字段 {unrecorded} —— "
                f"补进 VAR_FIELDS，否则这类字段永远比不到"
            )
        expected = {key: want[key] for key in VAR_FIELDS if key in want}
        for key in sorted(set(expected) | set(got_rec)):
            if key not in got_rec:
                problems.append(f"{place}: 字段 {key} 登记表缺失（HTML={expected[key]!r}）")
            elif key not in expected:
                problems.append(f"{place}: 字段 {key} 登记表多出来（登记表={got_rec[key]!r}）")
            elif got_rec[key] != expected[key]:
                # 按类型严格比：default = 0 与 default = "0" 是两种契约，不许当成相等放过
                problems.append(
                    f"{place}: {key} 登记表={got_rec[key]!r} != HTML={expected[key]!r}"
                )
    return problems


def verify_pack(pack_dir: str, live_pack: dict) -> list[str]:
    """layouts.toml 与 load_style_pack() 当次读出的**静态支**条目逐字段相等（等价闸）。

    Vue-only 版式按 `static_layouts` 收口在外 —— 它的登记表是 contract.toml，
    由 `t_vue_only_contract_is_the_registry_for_its_role` 单独守。
    """
    path = Path(pack_dir) / LAYOUTS_FILENAME
    if not path.exists():
        return [f"{Path(pack_dir).name}: 缺 {LAYOUTS_FILENAME}"]
    got = load_layouts(pack_dir)
    live = static_layouts(live_pack)
    name = Path(pack_dir).name
    problems = [f"{name}: 登记表缺版式 {role}" for role in set(live) - set(got)]
    problems += [f"{name}: 登记表多出版式 {role}" for role in set(got) - set(live)]
    for role in set(got) & set(live):
        rec, want = got[role], live[role]
        for field in FIELDS:
            if str(rec.get(field)) != str(want[field]):
                problems.append(f"{name}/{role}: {field} "
                                f"登记表={rec.get(field)} != HTML={want[field]}")
        problems += _compare_variables(name, role, rec.get("variables"), want["variables"])
    return problems
