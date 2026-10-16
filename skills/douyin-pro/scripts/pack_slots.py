#!/usr/bin/env python3
"""pack_slots —— 静态版式的有序色位槽与无损还原证明（Phase 1 的地基）。

分层方案的等价性不靠人眼看像素：若「主流模板 + 每包有序 hex + 该包 composition_id」
能逐字节还原每个包的原始文件，则该角色不存在色位与 id 之外的差异，可以安全合并为一个组件。
还原不了就是前提破了，当场报错，不许退化成"差不多"。
"""
from __future__ import annotations

import re
from pathlib import Path

import path_b_build as pb
import pack_variants as pkv

HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}")
SLOT_RE = HEX_RE  # 对外接口名（brief Interfaces 表），与 HEX_RE 同一份编译结果
CID_RE = re.compile(r'data-composition-id="(?P<cid>[^"]+)"')
COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)


def declaration_slot_indices(text: str) -> list[int]:
    """`slot_css` 编号里**落在注释之外**的那些序号 —— 组件该换成 `var(--cNN)` 的那批。

    为什么需要这个函数而不是「按位置数」：槽号由 `HEX_RE.findall` 的**出现序号**决定，
    而静态版式的 CSS 注释里也写着色值（`hook.html` 的 h-sup 注释占掉 c8/c9），
    于是声明槽号是**不连续**的。`news-coral/hook` 的 `color:` 是 c10 不是 c9 ——
    按位置替换会让组件拿到注释里那支已废弃的 WCAG 失败色。
    """
    spans = [(m.start(), m.end()) for m in COMMENT_RE.finditer(text)]
    return [
        i for i, m in enumerate(HEX_RE.finditer(text))
        if not any(start <= m.start() < end for start, end in spans)
    ]



def normalize(text: str) -> str:
    text = re.sub(r'data-composition-id="[^"]*"', 'data-composition-id="ID"', text)
    text = re.sub(r'__timelines\["[^"]*"\]', '__timelines["ID"]', text)
    return "\n".join(line.strip() for line in HEX_RE.sub("HEX", text).splitlines())


def read_raw(pack: str, role: str) -> str:
    """本模块唯一的盘上读取路径 —— 测试也走这条，不在测试里复算读逻辑。

    缺文件按断言式失败点名 pack/role（而不是 FileNotFoundError 冒泡成 ERROR 口径），
    与 selftest 其余项的 FAIL 记录方式保持一致。
    """
    path = Path(pb.pack_dir(pack)) / "compositions" / f"{role}.html"
    if not path.is_file():
        raise AssertionError(f"{pack}/{role} 缺少版式文件: {path}")
    return path.read_text(encoding="utf-8")


def template_of(pack: str, role: str) -> tuple[str, list[str]]:
    text = read_raw(pack, role)
    return normalize(text), HEX_RE.findall(text)


def slot_css(pack: str, role: str) -> str:
    """该 pack/role 的**有序**色位槽 CSS：`--c0:#rrggbb;--c1:#rrggbb;…`。

    两条来源，按"有没有静态文件"分叉：
      · 静态角色 —— 槽位身份 = 该角色文件里 hex 的出现序号（Task 1 逐字节还原的承重前提），
        严格按 `template_of` 的顺序编号；
      · Vue-only 角色（`field`/`rank`/…）—— 没有静态文件可抽，取契约自带的字面值
        （见 `vue_contracts.slot_values`，含显式 per-pack override）。

    发射侧把这段挂到 Vue clip 元素的 `style` 上（作用域在 clip 内，两镜不互覆盖）。
    """
    contract = pb.vue_only_contract(pack, role)
    if contract:
        import vue_contracts as vc
        return "".join(f"--c{i}:{h};" for i, h in enumerate(vc.slot_values(pack, contract)))
    hexes = template_of(pack, role)[1]
    return "".join(f"--c{i}:{h};" for i, h in enumerate(hexes))


def mainstream_base(role: str) -> str:
    """最大簇的代表包：取簇内排序第一个，保证跨进程稳定。"""
    buckets = pkv.cluster_role(role)
    biggest = max(buckets.values(), key=len)
    return sorted(biggest)[0]


def variant_of(pack: str, role: str) -> str:
    base = mainstream_base(role)
    return "a" if normalize(read_raw(pack, role)) == normalize(read_raw(base, role)) else "b"


def reconstruct(base_pack: str, role: str, pack: str,
                hexes: list[str] | None = None, cid: str | None = None) -> str:
    """hexes/cid 为 None 时取目标包自己的值（正向还原）。
    显式传入时用传入值还原 —— 这条参数存在的唯一理由是让「顺序是承重的」能被测试证明；
    不给它开任何"宽容"行为：长度不等于模板槽数照旧 raise。"""
    base = read_raw(base_pack, role)
    target = read_raw(pack, role)
    values = HEX_RE.findall(target) if hexes is None else list(hexes)
    base_cid = CID_RE.search(base).group("cid")
    target_cid = CID_RE.search(target).group("cid") if cid is None else cid
    if len(values) != len(HEX_RE.findall(base)):
        raise ValueError(f"{pack}/{role} 色位数 {len(values)} ≠ 模板 {len(HEX_RE.findall(base))}")
    it = iter(values)
    return CID_RE.sub(lambda m: f'data-composition-id="{target_cid}"',
                      HEX_RE.sub(lambda _m: next(it), base.replace(base_cid, target_cid)))


def verify_pack_role(base_pack: str, role: str, packs: list[str]) -> list[str]:
    out = []
    for pack in packs:
        try:
            got = reconstruct(base_pack, role, pack)
        except ValueError as exc:
            out.append(str(exc))
            continue
        if got != read_raw(pack, role):
            out.append(f"{pack}/{role}: 还原后与原始文件不等（存在色位与 id 之外的差异）")
    return out
