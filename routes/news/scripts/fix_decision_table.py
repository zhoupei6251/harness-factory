#!/usr/bin/env python3
"""一次性脚本：把 MEMORY.md 的模板决策树扩成完整的 32 行表（D20）。

背景（2026-10-08）: MEMORY.md 的决策树表只有 12 行 master，20 个派生变体挤在
表下一段纯文本块里，且那段写着「骨架未独立填实…会报填不满任何版式」——**已作废**
（实测 32/32 全部有 7 个真 composition、load 32/32 成功）。
表格是选包时第一眼看的地方，变体不在表里 = 实际选不到。

同时修掉标题里的手写 pack 数（与 decide_pack.py 同一个病，见 D20）。

表内容**从 decide_pack.PACK_BUCKETS + path_b_build 现算**，不手抄 pack 名，
免得下次加包又漏。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "routes" / "news" / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "douyin-pro" / "scripts"))

import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "decide_pack", ROOT / "routes" / "news" / "scripts" / "decide_pack.py")
dp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dp)
import path_b_build as pb  # noqa: E402

#: 变体的视觉气质一句话（从名字读，不另维护一份表）
VARIANT_NOTE = {
    "news-coral-mono": "coral 基调 · 单色灰（去饱和）",
    "news-ink-graphite": "ink 基调 · 墨石墨（更冷的黑）",
    "news-policy-bold": "policy 基调 · 政策加粗（高对比蓝）",
    "news-stat-grid": "stat 基调 · 数据网格",
    "news-onsite-urgent": "onsite 基调 · 现场紧急（琥珀警示）",
    "news-bulletin-strip": "bulletin 基调 · 速报条状",
    "news-explainer-blueprint": "explainer 基调 · 科普蓝图（亮蓝）",
    "news-alert-warning": "alert 基调 · 警示警告（黄三角）",
    "news-thread-tribute": "thread 基调 · 致敬专题（金）",
    "news-takes-column": "takes 基调 · 观点专栏（深靛）",
    "news-blast-score": "blast 基调 · 比分（绿）",
    "news-world-globe": "world 基调 · 国际地球（亮蓝）",
    "news-mosaic": "coral 基调 · 马赛克拼贴（多色块）",
    "news-dawn": "coral 基调 · 拂晓暖橙",
    "news-dusk": "coral 基调 · 黄昏紫",
    "news-noir": "coral 基调 · 黑色（纯黑）",
    "news-paper": "ink 基调 · 报纸白底",
    "news-podcast": "coral 基调 · 播客紫",
    "news-polarity": "alert 基调 · 极端对比（纯黑白橙）",
}


def build_table() -> str:
    """画全每一行 —— 行数 == `len(pb.ALL_TEMPLATES)`，由下面的 assert 拦，不在文案里写死。

    **primary + secondary 都必须进表**（2026-10-08 踩过：只画 primary = 27 行，
    漏掉 5 个只在 secondary 出现的包 —— 表格是选包第一眼看的地方，
    漏一个等于那个包选不到）。下面的 assert 专门拦这种漏。
    """
    rows = []
    for cat, info in dp.PACK_BUCKETS.items():
        kws = sorted(info["keywords"].items(), key=lambda x: -x[1])
        kws = " / ".join(k for k, _ in kws[:6])
        seq = ([(n, "（主）") for n in info["primary"]]
               + [(n, "（备）") for n in info.get("secondary", [])])
        for i, (name, tag) in enumerate(seq):
            note = VARIANT_NOTE.get(name, "（master · 主气质）")
            rows.append(f"| {kws if i == 0 else ''} | `{name}` {tag} | {note} |")
    missing = set(pb.ALL_TEMPLATES) - {
        n for info in dp.PACK_BUCKETS.values()
        for n in info["primary"] + info.get("secondary", [])}
    assert not missing, f"这些真实模板没进决策表: {sorted(missing)}"
    assert len(rows) == len(pb.ALL_TEMPLATES), (
        f"表里 {len(rows)} 行, 真实模板 {len(pb.ALL_TEMPLATES)} 个 —— 不等就说明"
        f"PACK_BUCKETS 与 ALL_TEMPLATES 脱节了")
    return "\n".join(rows)


def main() -> int:
    p = ROOT / "routes" / "news" / "MEMORY.md"
    lines = p.read_text(encoding="utf-8").splitlines()

    # 替换：从 "## 模板决策树" 那行 到 "**填实流程**" 之前
    start = next((i for i, l in enumerate(lines) if l.startswith("## 模板决策树")), None)
    end = next((i for i, l in enumerate(lines) if l.startswith("**填实流程**")), None)
    if start is None or end is None:
        print("  ! 定位失败: start=%s end=%s" % (start, end))
        return 1

    total = len(pb.ALL_TEMPLATES)
    block = f"""## 模板决策树（{total} 个 pack，数量现算见 D20）

按稿件特征词选视觉气质。t001（拾荒老人）= 人物故事型 → `news-coral`。

**{total}/{total} 全部可渲染**（2026-10-08 实测，本节原写的「2/12 可渲染 + 其余 10 包仅占位」
以及「18 个派生变体骨架未独立填实」**均已作废**）：每个包 `compositions/` 7 个真 composition、
`load_style_pack` {total}/{total} 成功、
`layout_selfcheck.py` 逐包 0 违规（检查的文件数由命令现报，不抄在这里）。派生变体与主题包都补了
`frame.md`（含 `derived_from` 派生声明）。

> ⚠️ 改色板用色时：`audit_pack_contrast.py` 口径是「本包色板 ∪ 共享 token 层」，
> `SHARED_TOKENS` 不许手抄（用 `shared_tokens_need_review()` 核对）；`#root` 地面色另受
> `GROUND_TONE_BY_HEX` 约束，改它等于改整片的底（D18/D19）。

| 触发词 | pack | 视觉气质 |
|---|---|---|
{build_table()}

> **自动决策工具**（推荐，省得自己查表）：`python routes/news/scripts/decide_pack.py "<热点关键词>"`
> 输出推荐 pack + 备选 + 理由，并按 `--length` 给镜数。详见 `routes/news/pack-decision.md`
> （全表 + 关键词分类 + 长度 → 镜数）。它的 pack 集合与真实模板的一致性由
> `skills/news-curate/scripts/curate_selftest.py` 的 `t_decide_pack_covers_every_real_template` 锁。

**派生变体填实流程**（已全部完成，这里留作新增变体时的做法）：
1. 选气质，参考同 master 的 7 个真版式
2. 写 host.html + frame.md（可跑 `routes/news/scripts/gen_variant_frames.py` 按真实用色生成色板表
   + `derived_from` 派生声明；**不要手抄对比度表**，那是 D10 的事故源）
3. 7 个 comp 各写一个 .html，先落 `AUTO_LAYOUT_STEMS` 那 7 个词干（hook/closer/story/stat/quote/catalog/rail）
4. `python skills/douyin-pro/scripts/path_b_selftest.py` + `audit_pack_contrast.py` 必绿
5. 真渲一镜测试，`check --strict` 必须 0 errors / 0 warnings

"""
    lines[start:end] = block.splitlines()
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  MEMORY.md: 决策树 {end - start} 行 → {len(block.splitlines())} 行（{total} 个 pack）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
