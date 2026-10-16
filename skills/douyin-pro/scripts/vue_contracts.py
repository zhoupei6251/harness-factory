#!/usr/bin/env python3
"""vue_contracts —— 只有 Vue 组件、没有静态 HTML 的版式，它的契约从哪来。

Phase 1 的地基是「静态 HTML 是唯一真源，Vue 组件靠逐字节还原证明等价」。
新结构（`field`/`rank`/`versus`/`cause`）**没有静态前身**，所以三样东西没有来源：
`layouts` 里的键、槽位值、`composition_id` —— 三者今天都从 `compositions/*.html` 抽。

契约放在**组件目录**里（`src/web/entries/<bundle>/contract.toml`），不放各包 `layouts.toml`：
一个组件服务 31 个包，抄 31 遍必然漂移；且 `layouts.toml` 自己写着「编译产物，勿手改」。
per-pack 只有两样：**槽位值**（来自该包 `theme.toml`）与 **`composition_id` 前缀**（从该包
已有 layout 的 id 反推，不新增配置 —— 前缀是 `nc-` / `nc-stat2-` / `np-` 这种不规则历史串）。
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

import path_b_build as pb

CONTRACT_NAME = "contract.toml"
REQUIRED_VAR_FIELDS = ("id", "type", "label")


class ContractError(RuntimeError):
    """契约不合法。抛出来，不降级 —— 悄悄补默认色等于拿假常数当判据。"""


def validate_contract(contract: dict, where: str = "<inline>") -> dict:
    """契约的最小形状检查：role/variant 有，variables 每条有 id/type/label 且不重复。

    和 HTML 的 `data-composition-variables` 同 schema —— 校验必须在这里做完，
    不能留到 `resolve_variable`，否则要等发射阶段才炸（那已经白花了一次配音）。
    """
    for key in ("role", "variant"):
        value = contract.get(key)
        if not (isinstance(value, str) and value.strip()):
            raise ContractError(f"{where}: 契约缺 {key!r}")
    if contract["variant"] not in ("a", "b"):
        raise ContractError(f"{where}: variant 只能是 'a' 或 'b'，实为 {contract['variant']!r}")
    variables = contract.get("variables")
    if not isinstance(variables, list) or not variables:
        raise ContractError(f"{where}: 契约没有 variables 数组")
    seen: set[str] = set()
    for var in variables:
        missing = [f for f in REQUIRED_VAR_FIELDS if not (isinstance(var, dict) and var.get(f))]
        if missing:
            raise ContractError(f"{where}: 变量 {var!r} 缺字段 {missing}")
        if var["id"] in seen:
            raise ContractError(f"{where}: 变量 id 重复 {var['id']!r}")
        seen.add(var["id"])
    return contract


def load(path: Path) -> dict:
    contract = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    contract["_bundle"] = Path(path).parent.name
    contract["_dir"] = str(Path(path).parent)
    contract.setdefault("slots", {})
    return validate_contract(contract, where=str(path))


def discover(entries_dir: Path) -> dict[tuple[str, str], dict]:
    """扫组件目录 → {(role, variant): 契约}。路由按 f"{role}-{variant}" 推导，
    所以同一键出现两个组件必然静默选错 —— 当场抛，不挑一个。"""
    found: dict[tuple[str, str], dict] = {}
    for path in sorted(Path(entries_dir).glob(f"*/{CONTRACT_NAME}")):
        contract = load(path)
        key = (contract["role"], contract["variant"])
        if key in found:
            raise ContractError(
                f"(role, variant)={key} 被两个契约同时声明: "
                f"{found[key]['_bundle']} 与 {contract['_bundle']} —— 路由靠它推 bundle 名，撞了必选错")
        found[key] = contract
    return found


def composition_id_for(pack: str, role: str) -> str:
    """新角色的 `composition_id` = `f"{role}-{pack}"`（如 `field-news-coral`）。

    **刻意不从已有 layout 的 id 反推包前缀。** 试过，量出来是 92 个少数派：
    30 个包的 `hook`/`quote`/`story` 三个角色的 id 全都是 `nc-night-*`
    （v008 批量从 `news-coral-night` 复制骨架留下的血统）—— 也就是说
    `news-alert/hook`、`news-coral/hook`、`news-stat/hook` 的 `composition_id`
    **是同一个字符串**。静态支没炸是因为每镜独立 document、`__timelines` 不共享；
    Vue 支一个 host 只有一份 `window.__timelines`，Task 4 被迫给每条 Vue 镜加唯一后缀，
    撞上的就是这类东西。拿它当 slug 来源 = 把这笔债续给新角色。

    包名本身唯一且可读，不需要再造一层前缀。
    """
    return f"{role}-{pack}"


def slot_values(pack: str, contract: dict) -> list[str]:
    """该包该角色的有序槽位值 = 契约 `[slots]` 的字面 hex，套上 `[slots.overrides].<pack>`。

    **不查 `theme.toml`。** 两条实测把那条路堵死了：31 包共 68 个 token、
    在所有包都存在的有 **0 个**；且 **0/31 包有"单一地面"**（每包在 7 个版式上用多个地面），
    所以"从包主题推导槽位"没有可推导的对象。随包变只能显式写 override ——
    那是**设计决定**，不是猜出来的；写错包名当场抛（拼错会静默不生效，最难查）。
    """
    slots = contract.get("slots") or {}
    if not slots:
        raise ContractError(f"{pack}/{contract['role']}: 契约没有 [slots]，槽位无来源")
    overrides = contract.get("overrides") or {}
    unknown = sorted(set(overrides) - set(pb.ALL_TEMPLATES))
    if unknown:
        raise ContractError(
            f"{contract['role']} 的 [slots.overrides] 写了不存在的包 {unknown} —— "
            "这条 override 永远不会生效；拼包名请从 ALL_TEMPLATES 里取")
    merged = dict(slots)
    merged.update(overrides.get(pack) or {})
    ordered = sorted(merged, key=lambda s: _slot_index(s, pack, contract))
    values = []
    for name in ordered:
        hex_value = str(merged[name]).lower()
        if not re.fullmatch(r"#[0-9a-f]{6}", hex_value):
            raise ContractError(
                f"{pack}/{contract['role']}: 槽位 {name} = {merged[name]!r} 不是 #rrggbb —— "
                "槽位值必须是字面色值，别名/变量名一律不认（取错是静默的）")
        values.append(hex_value)
    return values


def _slot_index(name: str, pack: str, contract: dict) -> int:
    try:
        return int(name[1:])
    except ValueError:
        raise ContractError(
            f"{pack}/{contract['role']}: 槽位名 {name!r} 不是 cNN 形式") from None
