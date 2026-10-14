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


def normalize(text: str) -> str:
    text = re.sub(r'data-composition-id="[^"]*"', 'data-composition-id="ID"', text)
    text = re.sub(r'__timelines\["[^"]*"\]', '__timelines["ID"]', text)
    return "\n".join(line.strip() for line in HEX_RE.sub("HEX", text).splitlines())


def _read(pack: str, role: str) -> str:
    return (Path(pb.pack_dir(pack)) / "compositions" / f"{role}.html").read_text(encoding="utf-8")


def template_of(pack: str, role: str) -> tuple[str, list[str]]:
    text = _read(pack, role)
    return normalize(text), HEX_RE.findall(text)


def mainstream_base(role: str) -> str:
    """最大簇的代表包：取簇内排序第一个，保证跨进程稳定。"""
    buckets = pkv.cluster_role(role)
    biggest = max(buckets.values(), key=len)
    return sorted(biggest)[0]


def variant_of(pack: str, role: str) -> str:
    base = mainstream_base(role)
    return "a" if normalize(_read(pack, role)) == normalize(_read(base, role)) else "b"


def reconstruct(base_pack: str, role: str, pack: str) -> str:
    base = _read(base_pack, role)
    target = _read(pack, role)
    values = HEX_RE.findall(target)
    base_cid = CID_RE.search(base).group("cid")
    target_cid = CID_RE.search(target).group("cid")
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
        if got != _read(pack, role):
            out.append(f"{pack}/{role}: 还原后与原始文件不等（存在色位与 id 之外的差异）")
    return out
