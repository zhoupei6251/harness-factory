#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""风格包编译器（P1-3c）：``spec.toml`` → ``host.html`` + 7 个版式 + ``frame.md``
=================================================================
一句话：把 §6.1 的 spec 与 §6.2 的原语库拼成发射器可以直接装包的版式目录。

编译器**不另造数值**：颜色只从 spec 的面/色对取，动效时长只从
``motion.entrance-seconds`` 取，几何只从下面这张配方表取。于是"改 spec 真的会改版式"
成立 —— 这是 31 套同等质量唯一可能的前提（手抄 ``frame.md`` 色值表那条老路是
D10/D20 的教训，法则 13 要求的"禁忌可执行"也从这里落地）。

四条边界（裁决 14 + `routes/news/evidence/2026-10-09-template-v2-p1-contract.md` §F）：
  1. 产物落 ``templates/hyperframes_path_c/<pack>/{spec.toml, host.html,
     compositions/*.html, frame.md}``；``frame.md`` 是**编译产物**，文件头写明勿手改。
  2. 版式名 == ``hf_style_spec.CANONICAL_LAYOUTS``（7 个）。
  3. 变量 id 只从发射器 ``path_b_build.DERIVERS`` 的词表取（新增 id 必须先加推导器），
     ``imagePath``/``imageCredit`` 在 P3 图片门禁接好前**不声明**（裁决 3）。
  4. 写盘前逐片段过 ``hf_primitives.check_preconditions`` + ``fragment_violations``，
     写盘后逐文件过 ``layout_selfcheck.check_layout``。任一条不过 ⇒ 不落盘并报原因。

同一个 pack 编译两次必须逐字节相同（法则 10 的编译期确定性）：所有随机量都在
``hf_primitives.bake_jitter`` 里以固定种子摇成字面量，本模块自己不摇骰子。
"""

from __future__ import annotations

import argparse
import json
import re
import string
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import hf_primitives as hp  # noqa: E402
import hf_style_spec as hs  # noqa: E402
import layout_selfcheck as lsc  # noqa: E402

SCHEMA = "hf-compile/1"

#: 产物根（裁决 14 双轨：path_b 存量、path_c 编译产物）
PACKS_ROOT = SCRIPT_DIR.parent / "templates" / "hyperframes_path_c"

#: 竖屏 9:16 基准帧。`cqw` 是 1% 帧宽、`cqh` 是 1% 帧高，两者比值恒定，
#: 所以"某个字号占几行高"可以从字号直接算出来，不需要手抄占位高度。
WIDTH, HEIGHT = 1080, 1920
CQH_PER_CQW = WIDTH / HEIGHT          # 1cqw 的字高一行 = 0.5625cqh × line-height

#: WCAG 1.4.3 的大字档下限（非粗体 18pt = 24px）。spec 里声明 `size = "large"`
#: 的色对（暖纸的强调色 4.39:1 只够大字）一旦被放到比这还小，达标线就该按
#: 4.5 数了 —— 那是判据 3 数不到的一条暗道，所以在编译期钉住。
LARGE_MIN_CQW = 24.0 / WIDTH * 100.0  # ≈ 2.222

#: 底部字幕禁入区的上沿（cqh）。由 spec 的 subtitle 几何反算，不是写死的 20。
#: `layout_selfcheck` 只能核 `bottom`/`inset` 两种写法，而原语全用 `top` 定位，
#: 所以"最坏行数会不会怼进字幕区"必须由编译器按占位高度自己核。
CONTENT_FLOOR_MARGIN_CQH = 0.5

#: 法则 17：内容下沿距内容区下沿**至多**空这么多 cqh（P1-3e 出帧实测的反面：
#: 未约束时七套版式空出 3.5–14.6cqh，竖屏下半部空转是"模板感"的主要来源）。
#: 口径是配方的**最坏占位**（`Step.height_cqh` 按最大行数算），所以真实文本更短时
#: 空得比这个数多 —— 这条闸只管"设计意图上就不打算填幅"的那一类，短文本要填幅得改配方。
MAX_BOTTOM_DEAD_CQH = 8.0

#: 呼吸位移量（`yPercent`，相对内容层自身高度）。取 -3 而不是更小：path_b 存量包
#: 的 `#*-field` 漂移都是 -3、实测吃掉 1.7cqh，编译包的内容层同样是内容高度（≈60cqh），
#: -3 吃 1.8cqh —— 与存量口径一致，P1-3e 并排比帧时位移不会一眼深浅不同。
DRIFT_Y_PERCENT = -3.0

#: 发射器的变量词表（`path_b_build.DERIVERS` 的精确 id + `itemN*/stepN*` 形态）。
#: 这里列的是本 pack 用到的那些；测试 `t_hf_compile_variable_ids_are_emitter_derivable`
#: 拿发射器真表核闭合，词表外新增 id 会在那条测试上红。
INDEXED_SHAPE_RE = re.compile(r"^(item|step)([1-9])(Label|Value|Body|Index)$")

#: 契约表：版式 → 变量声明。默认值只是"单版式预览"用的占位词，链路里发射时
#: 一律被 `resolve_variable` 覆盖（发射器绝不用 default 兜事实，见 coerce）。
_VAR_DEFAULTS = {
    "kicker": ("眉标", "NEWS"),
    "headTop": ("标题第一行", "标题第一行"),
    "headBottomLead": ("标题第二行前段", "第二行"),
    "headAccent": ("标题第二行强调", "强调"),
    "support": ("辅助行", "辅助信息"),
    "ordinal": ("镜序", "01"),
    "tone": ("地面明暗", "light"),
    "title": ("小标题", "一个标题"),
    "onscreen": ("屏句(唯一上屏整句, 不进配音)", "没人告诉他这件事"),
    "value": ("主数值", "0"),
    "unit": ("主单位", "元"),
    "label": ("主数值说明", "说明"),
    "compareValue": ("对比数值", "0"),
    "compareUnit": ("对比单位", "元"),
    "compareLabel": ("对比说明", "对比"),
    "quoteBody": ("引文", "引文内容"),
    "attribution": ("归属", "出处"),
    "channel": ("频道/来源行", "来源"),
    "cta": ("行动指令前段", "今天就查一下"),
    "ctaAccent": ("行动指令强调", "社保"),
    "step1Label": ("第1步标题", "第一步"),
    "step1Body": ("第1步说明", "说明一"),
    "step1Index": ("第1步标号", "01"),
    "step2Label": ("第2步标题", "第二步"),
    "step2Body": ("第2步说明", "说明二"),
    "step2Index": ("第2步标号", "02"),
    "step3Label": ("第3步标题", "第三步"),
    "step3Body": ("第3步说明", "说明三"),
    "step3Index": ("第3步标号", "03"),
    "item1Label": ("第1条标签", "标签一"),
    "item1Value": ("第1条事实", "事实一"),
    "item2Label": ("第2条标签", "标签二"),
    "item2Value": ("第2条事实", "事实二"),
    "item3Label": ("第3条标签", "标签三"),
    "item3Value": ("第3条事实", "事实三"),
}

#: 每套版式声明哪些变量。**照 `news-coral` 的同名版式取同一份词表**（只去掉图位），
#: 否则 P1-3e 的"同一份分镜稿并排渲染两套"根本喂不进去。
#: 唯一一条有意的偏离：catalog 多三个 `stepNIndex`（法则 17 之后的条目标号，C3）。
#: 偏离不破坏"同一份稿喂两套"—— 那三个 id 是**结构标号**（行存在就有号），不吃分镜数据，
#: 分镜不需要为编译包多写任何字段。
CONTRACTS: dict = {
    "hook": ["kicker", "headTop", "headBottomLead", "headAccent", "support", "slotSeconds"],
    "stat": ["kicker", "value", "unit", "label",
             "compareValue", "compareUnit", "compareLabel", "slotSeconds"],
    "rail": ["kicker", "title", "ordinal",
             "item1Label", "item1Value", "item2Label", "item2Value",
             "item3Label", "item3Value", "slotSeconds"],
    "quote": ["kicker", "quoteBody", "attribution", "slotSeconds"],
    "catalog": ["kicker", "title", "step1Index", "step1Label", "step1Body",
                "step2Index", "step2Label", "step2Body",
                "step3Index", "step3Label", "step3Body", "slotSeconds"],
    "story": ["kicker", "ordinal", "tone", "title", "onscreen", "slotSeconds"],
    "closer": ["kicker", "cta", "ctaAccent", "channel", "slotSeconds"],
}


class CompileError(RuntimeError):
    """拒编：spec 与配方对不上、或产物过不了闸。唯一的停机原因。"""


# ---------------------------------------------------------------- 小工具

def pack_prefix(pack_id: str) -> str:
    """版式 id 前缀：`news-editorial-warm` → `ew`（去掉 `news-` 头，取各段首字母）。

    作用域只在**本包内部**：合成 id 是 `{prefix}-{layout}`，一次渲染只装一个包，
    所以跨包撞名不会互相干扰；包内七个 layout 名本身就互异，前缀只要稳定即可。
    """
    stem = pack_id[len("news-"):] if pack_id.startswith("news-") else pack_id
    return "".join(part[0] for part in stem.split("-") if part)


def text_height_cqh(size_cqw: float, lines: int, line_height: float) -> float:
    """`lines` 行 `size_cqw` 字号（含行距）占多少 cqh。由帧宽高比推，不抄数。"""
    return size_cqw * CQH_PER_CQW * line_height * lines


def _chip_height(size_cqw: float, pad_v: float) -> float:
    return text_height_cqh(size_cqw, 1, 1.2) + 2 * pad_v


# ---------------- 法则 18 的横向口径（文字位必须声明栏宽） ----------------
#: 每个文字位都要写 ``max_width``。编译器把它落成 CSS 的 ``max-width`` ⇒ 盒宽被
#: **浏览器**钉死：字太长就折行（变高，那是占位行数的事），不会悄悄变宽。
#: 于是"这个位的右沿在哪"从一句排版口述变成一个可判的事实，重叠判定才不是纸面数字。
#: 没声明栏宽的文字位 = 右沿未知 = 拒编（`overlap_violations` 的第一条分支）。
#:
#: 两种来源，别混：
#:   · **字形推出来的**（数字位、眉标片）用下面两个函数，字宽系数是量出来的；
#:   · **设计选的**（整句/标题那一类）直接写栏宽字面量，唯一的硬约束是落在安全区内
#:     （``overlap_violations`` 的第二条分支核这件事）。
KICKER_MAX_CHARS = 8      # 眉标是「栏目·小节」形，产线实测最长 8 字
LATIN_DIGIT_EM = 0.569    # Playfair 数字字宽，P1-3e 量自成片帧：16cqw 两位墨宽 18.20cqw
CJK_CHAR_EM = 1.0         # 汉字字宽 = 1em（拉丁/数字更窄 ⇒ 按 1em 估是偏保守的一侧）


def kicker_width(size_cqw: float, chars: int = KICKER_MAX_CHARS) -> float:
    """眉标片的 ``max_width``：**内容宽**，内边距由原语另加（不进这个数）。

    ``KICKER_MAX_CHARS`` 是本模块的单边声明：发射器现在不截眉标，所以超长眉标会
    在这个盒里折行（变高）。盒右沿仍然成立 —— 这正是法则 18 要的；行数口径对不上
    是 P4 那条"配方行数 vs 发射器字数上限"的账。
    """
    return round(chars * CJK_CHAR_EM * size_cqw, 2)


def numeral_width(size_cqw: float, digits: int = 2) -> float:
    """纯数字位（镜序 / 条目标号）的 ``max_width``：两位 latin 的墨宽。"""
    return round(digits * LATIN_DIGIT_EM * size_cqw, 2)


def variables_for(layout: str) -> list:
    """发射器契约要求的声明形状（每项一个 `{"id": …}` 单行 JSON，见 `declared_vars`）。"""
    out = []
    for var_id in CONTRACTS[layout]:
        if var_id == "slotSeconds":
            out.append({"id": "slotSeconds", "type": "number", "label": "本镜可见秒数",
                        "default": 4, "min": 1})
            continue
        label, default = _VAR_DEFAULTS[var_id]
        out.append({"id": var_id, "type": "string", "label": label, "default": default})
    return out


# ---------------------------------------------------------------- 配方

class Step:
    """一次原语调用 + 它**最坏情况**占的竖向高度（禁入区断言的口径来源）。"""

    def __init__(self, prim: str, ident: str, kwargs: dict, height_cqh: float,
                 text: bool = False) -> None:
        self.prim = prim
        self.ident = ident
        self.kwargs = kwargs
        self.height_cqh = height_cqh
        self.text = text


def _steps(layout: str, tok: hp.Tok, p: str) -> list:
    """七套版式的配方。几何单位：cqw/cqh，横向安全区 6..94，纵向内容区 0..(100−禁入区)。"""
    s = []

    def masthead(tag):
        """报头三件套：通栏发丝线 + 强调色眉标片（杂志族的地面识别符）。

        片的盒宽按 ``kicker_width`` 推（内容宽 22.4cqw），盒右沿落在 32.2cqw ——
        P1-3e 出帧实测的缺陷就是这里没声明栏宽：收缩盒被 8 字眉标撑到 30cqw 开外，
        把下面标题的第一行划了一道背景色横穿（片是**带底色**的，leading 吸收不掉）。
        """
        s.append(Step("hairline", f"{p}-{tag}-rule",
                      dict(top=8.5, width=88.0, surface="rule", thickness=0.35),
                      0.35))
        s.append(Step("block-chip", f"{p}-{tag}-kicker",
                      dict(var_id="kicker", role="on-accent", surface="accent",
                           top=13.0, size=2.8, pad_v=0.85, pad_h=1.9, delay=0.25,
                           max_width=kicker_width(2.8)),
                      _chip_height(2.8, 0.85), text=True))

    if layout == "hook":
        masthead("hk")
        # 三行大标题吃满安全幅（88cqw = 6..94）：栏宽越宽，同样字号装下的字越多，
        # 折行概率越低 —— 在占位口径补实之前（P4），加宽是唯一的免费安全边际。
        s.append(Step("char-rise", f"{p}-hk-top",
                     dict(var_id="headTop", role="display", size=9.8, top=24.0,
                          max_width=88.0, delay=0.45),
                     text_height_cqh(9.8, 1, 1.24), text=True))
        s.append(Step("char-rise", f"{p}-hk-lead",
                     dict(var_id="headBottomLead", role="display", size=9.8, top=38.0,
                          max_width=88.0, delay=0.75),
                     text_height_cqh(9.8, 1, 1.24), text=True))
        s.append(Step("keyword-tint", f"{p}-hk-accent",
                     dict(var_id="headAccent", role="kicker", size=9.8, top=52.5,
                          max_width=88.0, delay=1.05),
                     text_height_cqh(9.8, 1, 1.24), text=True))
        s.append(Step("rule-pull", f"{p}-hk-bar",
                     dict(top=67.0, width=14.0, thickness=1.0, surface="accent",
                          delay=1.3), 1.0))
        s.append(Step("cue-fade", f"{p}-hk-support",
                     dict(var_id="support", role="secondary", size=3.9, top=71.5,
                          max_width=66.0, line_height=1.5, delay=1.5),
                     text_height_cqh(3.9, 1, 1.5), text=True))

    elif layout == "stat":
        # 数字是主角（§5 数据轴的杂志写法）：先把面板推到位置，再往上落字。
        masthead("st")
        s.append(Step("giant-numeral", f"{p}-st-value",
                     dict(value_var="value", unit_var="unit", role="display",
                          top=22.0, size=26.0, unit_size=7.4, max_width=88.0, delay=0.5),
                     text_height_cqh(26.0, 1, 1.12), text=True))
        s.append(Step("cue-fade", f"{p}-st-label",
                     dict(var_id="label", role="body", size=4.2, top=50.0,
                          max_width=66.0, line_height=1.5, delay=0.9),
                     text_height_cqh(4.2, 1, 1.5), text=True))
        s.append(Step("clip-wipe-up", f"{p}-st-panel",
                     dict(top=58.0, height=15.0, surface="panel", delay=1.1), 15.0))
        # `max_width=30` 是**栏位选择**（不是字形推出来的）：9.5 起算右沿 39.5，
        # 正好让在 42 起的对比说明左边，两栏之间留 2.5cqw 的缝 —— 面板里并排两栏
        # 只要有一条没写栏宽，编译器就不知道它的右沿，也就拦不住它们贴到一起。
        s.append(Step("giant-numeral", f"{p}-st-cmp",
                     dict(value_var="compareValue", unit_var="compareUnit",
                          role="panel-body", top=60.5, left=9.5, size=8.6,
                          unit_size=3.6, max_width=30.0, delay=1.25),
                     text_height_cqh(8.6, 1, 1.12), text=True))
        s.append(Step("cue-fade", f"{p}-st-cmp-label",
                     dict(var_id="compareLabel", role="panel-body", size=3.4, top=62.5,
                          left=42.0, max_width=46.0, line_height=1.45, delay=1.4),
                     text_height_cqh(3.4, 2, 1.45), text=True))

    elif layout == "rail":
        masthead("rl")
        # 标题顶边 16.5 → 19.0：眉标片的最坏盒底是 13.0 + `_chip_height(2.8, 0.85)`
        # = 16.59，16.5 起算的标题被那片强调色横穿了一次（P1-3e 并排帧上看得见）。
        # 留 0.41cqh 的余量再抬到整数位，19.0 起两行只到 27.64，仍离脊柱 34.0 远。
        s.append(Step("char-rise", f"{p}-rl-title",
                     dict(var_id="title", role="display", size=6.4, top=19.0, left=6.0,
                          max_width=68.0, line_height=1.2, delay=0.45),
                     text_height_cqh(6.4, 2, 1.2), text=True))
        # 镜序从 2.8cqw 的小字升格成 16cqw 的拉丁大数字（C2）：杂志族的右上标是
        # 版面的一部分而不是注脚。`secondary` 色对 5.43:1，大字更没问题；
        # 不用 `rule` 面当"水印"—— spec 明文 rule 只承载线不承载字，
        # 且 #ddd3bf on #f5efe3 = 1.14:1，判据 3 会当场拒。
        # `left`/`max_width` 都从字宽推（法则 18）：两位 16cqw 的墨宽实测 18.21cqw
        # （`numeral_width`，P1-3e 量自成片帧），于是盒右沿正好落在 94 这条安全边上、
        # 与报头发丝线齐；标题栏宽 68 ⇒ 两盒永不横穿（6+68=74 < 75.79）。
        s.append(Step("giant-numeral", f"{p}-rl-ordinal",
                     dict(value_var="ordinal", role="secondary", top=13.0,
                          left=94.0 - numeral_width(16.0), size=16.0,
                          max_width=numeral_width(16.0), delay=0.6),
                     text_height_cqh(16.0, 1, 1.12), text=True))
        s.append(Step("clip-wipe-up", f"{p}-rl-spine",
                     dict(top=34.0, height=42.0, left=6.0, right=92.6,
                          surface="accent", delay=0.8), 42.0))
        for i, top in enumerate((36.0, 50.0, 64.0), start=1):
            delay = 0.95 + 0.16 * i
            s.append(Step("cue-fade", f"{p}-rl-lab{i}",
                         dict(var_id=f"item{i}Label", role="secondary", size=3.0,
                              top=top, left=12.0, max_width=74.0, line_height=1.3,
                              delay=delay, letter_spacing=0.12),
                         text_height_cqh(3.0, 1, 1.3), text=True))
            s.append(Step("char-rise", f"{p}-rl-val{i}",
                         dict(var_id=f"item{i}Value", role="display", size=5.4,
                              top=top + 4.6, left=12.0, max_width=46.0,
                              line_height=1.2, delay=delay + 0.08, stagger=0.03),
                         text_height_cqh(5.4, 1, 1.2), text=True))

    elif layout == "quote":
        masthead("qt")
        s.append(Step("clip-wipe-up", f"{p}-qt-stripe",
                     dict(top=20.0, height=42.0, left=6.0, right=92.4,
                          surface="accent", delay=0.45), 42.0))
        s.append(Step("cue-fade", f"{p}-qt-body",
                     dict(var_id="quoteBody", role="display", size=6.4, top=22.0,
                          left=12.0, max_width=68.0, line_height=1.5, serif=True,
                          delay=0.7, duration=0.7),
                     text_height_cqh(6.4, 6, 1.5), text=True))
        s.append(Step("rule-pull", f"{p}-qt-bar",
                     dict(top=66.5, width=14.0, thickness=0.8, left=12.0,
                          surface="rule", delay=1.5), 0.8))
        s.append(Step("cue-fade", f"{p}-qt-attr",
                     dict(var_id="attribution", role="secondary", size=3.4, top=70.0,
                          left=12.0, max_width=50.0, line_height=1.4, delay=1.65),
                     text_height_cqh(3.4, 1, 1.4), text=True))

    elif layout == "catalog":
        masthead("ct")
        # 同 rail：顶边抬到 18.5 才离得开眉标片的最坏盒底 16.59（法则 18 的实测起因）。
        s.append(Step("char-rise", f"{p}-ct-title",
                     dict(var_id="title", role="display", size=7.0, top=18.5,
                          max_width=88.0, line_height=1.2, delay=0.45),
                     text_height_cqh(7.0, 2, 1.2), text=True))
        for i, top in enumerate((36.0, 49.0, 62.0), start=1):
            delay = 0.8 + 0.2 * i
            if i > 1:
                s.append(Step("hairline", f"{p}-ct-sep{i}",
                              dict(top=top - 2.0, width=88.0, surface="rule",
                                   thickness=0.28, delay=delay - 0.1), 0.28))
            # 条目标号（C3）：存量包的 catalog 行内本来就印死 01/02/03
            # （`path_b_build.scene_items` 的注释），编译包缺它就读成"列表"而不是"目录"。
            # 号走 `stepNIndex` 这个**结构**变量（行存在就必然有号），不吃分镜数据。
            # 栏宽由字宽推：两位 5.6cqw ⇒ 6.37cqw，盒右沿 12.37 < 行标题的 15，
            # 号与题之间那条缝是算出来的，不是"看着没碰上"。
            s.append(Step("giant-numeral", f"{p}-ct-idx{i}",
                         dict(value_var=f"step{i}Index", role="kicker", top=top - 0.4,
                              left=6.0, size=5.6, max_width=numeral_width(5.6),
                              delay=delay - 0.05),
                         text_height_cqh(5.6, 1, 1.12), text=True))
            s.append(Step("char-rise", f"{p}-ct-lab{i}",
                         dict(var_id=f"step{i}Label", role="display", size=4.6,
                              top=top, left=15.0, max_width=73.0, line_height=1.2,
                              delay=delay, stagger=0.03),
                         text_height_cqh(4.6, 1, 1.2), text=True))
            s.append(Step("cue-fade", f"{p}-ct-body{i}",
                         dict(var_id=f"step{i}Body", role="body", size=3.2,
                              top=top + 5.9, left=15.0, max_width=73.0, line_height=1.5,
                              delay=delay + 0.18),
                         text_height_cqh(3.2, 2, 1.5), text=True))

    elif layout == "story":
        masthead("sy")
        s.append(Step("char-rise", f"{p}-sy-title",
                     dict(var_id="title", role="display", size=8.4, top=24.0,
                          max_width=88.0, line_height=1.24, delay=0.45),
                     text_height_cqh(8.4, 3, 1.24), text=True))
        # 与 rail 同一升格（C2）；翻面时 `TONE_FLIPS` 把这条换成 `on-ink-soft`。
        # 栏宽同一口径（法则 18）：右沿落在 94，标题（6..94）在 24.0 起算，
        # 两盒竖向也不交（13.0 + 10.08 = 23.08 < 24.0）。
        s.append(Step("giant-numeral", f"{p}-sy-ordinal",
                     dict(value_var="ordinal", role="secondary", top=13.0,
                          left=94.0 - numeral_width(16.0), size=16.0,
                          max_width=numeral_width(16.0), delay=0.6),
                     text_height_cqh(16.0, 1, 1.12), text=True))
        s.append(Step("rule-pull", f"{p}-sy-bar",
                     dict(top=58.0, width=14.0, thickness=1.0, surface="accent",
                          delay=1.1), 1.0))
        s.append(Step("cue-fade", f"{p}-sy-onscreen",
                     dict(var_id="onscreen", role="body", size=4.4, top=64.0,
                          max_width=80.0, line_height=1.6, serif=True, delay=1.3),
                     text_height_cqh(4.4, 2, 1.6), text=True))

    elif layout == "closer":
        # 墨底反相：这一套的地面就是 spec 的 `ink` 面，文字全部走 `on-ink*` 三条色对。
        s.append(Step("hairline", f"{p}-cl-rule",
                      dict(top=12.0, width=88.0, surface="rule", thickness=0.35), 0.35))
        s.append(Step("block-chip", f"{p}-cl-kicker",
                     dict(var_id="kicker", role="on-accent", surface="accent",
                          top=17.0, size=2.8, pad_v=0.85, pad_h=1.9, delay=0.25,
                          max_width=kicker_width(2.8)),
                     _chip_height(2.8, 0.85), text=True))
        s.append(Step("char-rise", f"{p}-cl-cta",
                     dict(var_id="cta", role="on-ink", size=7.2, top=30.0,
                          max_width=88.0, line_height=1.24, delay=0.5),
                     text_height_cqh(7.2, 2, 1.24), text=True))
        # 强调段与上一行同栏（88 = 吃满安全幅）：`ctaAccent` 是行动句的后半，
        # 换一个栏宽会让它比前半早折一行，读起来像两句而不是一句。
        s.append(Step("keyword-tint", f"{p}-cl-accent",
                     dict(var_id="ctaAccent", role="on-ink-accent", size=7.2,
                          top=50.0, max_width=88.0, delay=0.9),
                     text_height_cqh(7.2, 2, 1.24), text=True))
        s.append(Step("rule-pull", f"{p}-cl-bar",
                      dict(top=68.0, width=14.0, thickness=1.0, surface="accent",
                           delay=1.2), 1.0))
        s.append(Step("cue-fade", f"{p}-cl-channel",
                     dict(var_id="channel", role="on-ink-soft", size=3.2, top=72.0,
                          max_width=60.0, line_height=1.4, delay=1.35),
                     text_height_cqh(3.2, 1, 1.4), text=True))
    else:
        raise CompileError(f"没有 {layout!r} 的配方（有: {', '.join(CONTRACTS)}）")

    return s


#: 每套版式的地面（spec `color.surfaces` 的面名）。closer 用墨面做书挡，
#: story 靠 `tone` 变量在纸/墨之间翻面 —— 这两条合起来才是"三段混调"里
#: 可机械判定的那半（`path_b_build._tone` 的注释就是这条）。
GROUNDS = {"hook": "paper", "stat": "paper", "rail": "paper", "quote": "paper",
           "catalog": "paper", "story": "paper", "closer": "ink"}

#: 翻面时要换文字色的元素（story 专属）。键是版式 id 后缀，值是 `color.text` 的角色名。
TONE_FLIPS = {
    "story": {"-sy-title": "on-ink", "-sy-onscreen": "on-ink",
              "-sy-ordinal": "on-ink-soft"},
}


# ---------------------------------------------------------------- 装配

def _font_faces(tok: hp.Tok) -> str:
    """本文件用到的中文族的 @font-face。

    族名与本机在装的 `local()` 候选都从 `layout_selfcheck` 取（同一份口径，不抄第二遍）：
    结构闸按文件审计，缺一条就静默回落成系统默认字 —— 字体降档不会有人报错。
    """
    sans = ('@font-face {\n'
            '  font-family: "HF CJK";\n'
            '  src: local("Noto Sans SC"), local("Microsoft YaHei"), local("DengXian");\n'
            '  font-weight: 100 900;\n'
            '}')
    serif = ('@font-face {\n'
             '  font-family: "HF Serif CJK";\n'
             '  src: local("Noto Serif SC"), local("SimSun");\n'
             '  font-weight: 100 900;\n'
             '}')
    faces = []
    if tok.body_family == "HF CJK" or tok.display_family == "HF CJK":
        faces.append(sans)
    if tok.display_family == "HF Serif CJK" or tok.body_family == "HF Serif CJK":
        faces.append(serif)
    missing = ({tok.display_family, tok.body_family} & set(lsc.CJK_FAMILIES)) - \
        {("HF CJK" if "HF CJK" in f else "HF Serif CJK") for f in faces}
    if missing:
        raise CompileError(
            f"中文族 {sorted(missing)} 没有 @font-face 模板 —— 结构闸会打 "
            "CJK_FAMILY_USED_NOT_DECLARED；请把族名加进 `_font_faces` 的分支")
    return "\n\n".join(faces)


def _ground_css(tok: hp.Tok, surface: str) -> str:
    return (f'#root {{ position: absolute; inset: 0; overflow: hidden;\n'
            f'  background: {tok.face(surface)};\n'
            f'  color: {tok.pair("display")["hex"]};\n'
            f'  font-family: "{tok.body_family}", sans-serif;\n'
            f'}}')


def _content_span(steps: list) -> tuple:
    """内容层的竖向区间 `(span_top, span_bottom, full_bleed)`，单位 cqh（仍以 `#root` 为量纲）。

    没有 `top` 的步骤（全幅取图层，P3 才会出现）无法参与收区间，那种版式只能整幅兜住，
    `full_bleed` 置真 —— `geometry_violations` 会因此拒绝它叠加呼吸位移。
    """
    tops = [s.kwargs["top"] for s in steps if "top" in s.kwargs]
    bottoms = [s.kwargs["top"] + s.height_cqh for s in steps if "top" in s.kwargs]
    if len(tops) != len(steps):
        return 0.0, 100.0, True
    return min(tops), min(100.0, max(bottoms)), False


def _col_css(col_id: str, span_top: float, span_bottom: float) -> str:
    """内容包裹层：只圈住**真正有内容的竖向区间**，不是整张画布。

    为什么不给 `inset: 0`：呼吸位移是 `yPercent` 相对自身高度，满幅盒子上移会把
    自己的顶边推出 `#root`（它有 `overflow: hidden`，就是引擎眼里的"clipping layout
    container"），七套版式各报一条 `container_overflow`。信息级不影响 `--strict`
    退出码，但 31 套每套都刷同一条噪音时，真越界就没有信号了 —— 所以把区间收准。
    子元素的 `top` 因此要减去 `span_top`（cqh 的量纲仍按 `#root` 算，不变）。
    """
    return (f'#{col_id} {{ position: absolute; top: {hp._num(span_top)}cqh; left: 0;\n'
            f'  width: 100cqw; height: {hp._num(span_bottom - span_top)}cqh; }}')


def _tone_css(tok: hp.Tok, layout: str, p: str) -> str:
    flips = TONE_FLIPS.get(layout)
    if not flips:
        return ""
    rules = [f'#root[data-tone="dark"] {{ background: {tok.face("ink")}; }}']
    for suffix, role in sorted(flips.items()):
        rules.append(f'#root[data-tone="dark"] #{p}{suffix} {{ '
                     f'color: {tok.pair(role)["hex"]}; }}')
    return "\n".join(rules) + "\n"


def composition_html(spec, tok: hp.Tok, layout: str) -> str:
    """一套版式的完整文件文本（写盘前已被 `lint_composition` 核过）。"""
    p = pack_prefix(spec.id)
    comp_id = f"{p}-{layout}"
    col_id = f"{p}-{layout}-col"
    ground = GROUNDS[layout]
    steps = _steps(layout, tok, p)
    idents = [step.ident for step in steps]
    doubled = sorted({i for i in idents if idents.count(i) > 1})
    if doubled:
        raise CompileError(
            f"{spec.id}/{layout}: 配方里两个元素共用 id {doubled} —— DOM id 重复时 "
            "`getElementById` 只认第一个，后写的那条补间会改到前一个元素上")

    css, html_parts, pre_js, tweens = [], [], [], []
    css.append(_font_faces(tok))
    css.append(_ground_css(tok, ground))
    # 内容区间：`top` 定位的步骤才有边界；没有 top 的（全幅取图层，P3）只能整幅兜住。
    span_top, span_bottom, _ = _content_span(steps)
    css.append(_col_css(col_id, span_top, span_bottom))
    for step in steps:
        prim = hp.PRIMITIVES[step.prim]
        problems = hp.check_preconditions(step.prim, ground=ground,
                                          accent_roles=tuple(a.get("role", "")
                                                             for a in tok.accents))
        if problems:
            raise CompileError(f"{spec.id}/{layout} 取用 {step.prim} 被拒：{'; '.join(problems)}")
        kwargs = step.kwargs
        if span_top and "top" in kwargs:
            # 子元素的 containing block 现在是内容层，纵坐标要跟着减（见 `_col_css`）
            kwargs = {**kwargs, "top": kwargs["top"] - span_top}
        frag = prim.render(tok, step.ident, **kwargs)
        bad = hp.fragment_violations(frag)
        if bad:
            raise CompileError(f"{spec.id}/{layout} 的 {step.prim} 违反法则：{'; '.join(bad)}")
        css.append(frag.css)
        html_parts.append("        " + frag.html)
        pre_js.extend(frag.pre_js)
        tweens.extend(frag.tweens)

    # 呼吸位移：整镜剩余时间持续动，不留静止尾巴（判据 3 的动量预算）。
    drift = hp.PRIMITIVES["drift-y"].render(tok, col_id, percent=DRIFT_Y_PERCENT)
    bad = hp.fragment_violations(drift)
    if bad:
        raise CompileError(f"{spec.id}/{layout} 的 drift-y 违反法则：{'; '.join(bad)}")
    tweens.extend(drift.tweens)

    root_js = ""
    tone_attr = ""
    if layout in TONE_FLIPS:
        tone_attr = ' data-tone="light"'
        root_js = ('const rootEl = document.getElementById("root");\n'
                   '        const tone = String(vars.tone || "light").toLowerCase();\n'
                   '        rootEl.dataset.tone = tone === "dark" ? "dark" : "light";')

    variables = variables_for(layout)
    variables_json = ",\n    ".join(json.dumps(v, ensure_ascii=False) for v in variables)
    if "'" in variables_json:
        raise CompileError(f"{spec.id}/{layout} 的变量契约里有单引号 —— 属性用 ' 包裹，会截断 JSON")

    body = "\n".join(f"          {part.strip()}" for part in html_parts)
    template = string.Template(COMPOSITION_TPL).safe_substitute(
        variables_json=variables_json,
        faces="\n\n".join(css),
        comp_id=comp_id,
        tone_attr=tone_attr,
        width=WIDTH,
        height=HEIGHT,
        col_id=col_id,
        body=body,
        tone_css=_tone_css(tok, layout, p),
        budget=hp.BUDGET_JS.format(intro_end=hp.BUDGET_INTRO_END,
                                   min_drift=hp.BUDGET_MIN_DRIFT).rstrip(),
        root_js=root_js,
        pre_js="\n".join(f"        {line}" for line in pre_js),
        tweens="\n".join(f"        {line}" for line in tweens),
    )
    return template


COMPOSITION_TPL = """<!doctype html>
<html lang="zh-CN" data-composition-variables='[
    $variables_json
  ]'>
  <head>
    <meta charset="UTF-8" />
  </head>
  <body>
    <template>
      <style>
$faces

$tone_css      </style>
      <div id="root" data-composition-id="$comp_id"$tone_attr data-width="$width" data-height="$height">
        <div id="$col_id">
$body
        </div>
      </div>
      <script>
        const vars = window.__hyperframes.getVariables();
$budget
        $root_js
        const tl = gsap.timeline({ paused: true });
$pre_js
$tweens
        window.__timelines["$comp_id"] = tl;
      </script>
    </template>
  </body>
</html>
"""

#: 宿主骨架。发射器 `path_b_build.emit_host` 要求**六个** `{{...}}` 占位符一个不缺
#: （`HOST_PLACEHOLDERS`，少一个直接 EmitterError），所以编译期一个都不许填 ——
#: 画布宽高、合成 id 都由发射器在装包时给，包不携带全片尺寸。
#: 另外注释里不许出现带双花括号的占位符原文：`emit_host` 用 `str.replace`（全局替换），
#: 写了就会在那处也插进挂载片段 —— `emit_host` 只查缺、不查多，拦不住这种多写。
HOST_TPL = """<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      /* 宿主骨架（$PACK_NAME · 编译产物，勿手改）。
         六个双花括号占位符原样留着，由发射器填充：合成 id、画布宽高、
         全片秒数、N 个挂载 clip、N 个挂载 audio。本文件不写任何版式几何，
         地面/版式/时间轴全在各版式的子合成里。 */
      html,
      body {
        margin: 0;
        background: #1a1a1a;
      }
      #root {
        position: relative;
        width: 100%;
        height: 100%;
        overflow: hidden;
        container-type: size;
      }
      .clip {
        position: absolute;
        inset: 0;
      }
      /* 配音轨不参与版面：抽出来给零尺寸，免得它的行盒撑高 #root 把画面顶偏一位。
         时间轴与可见性由 data-start / data-duration 决定，与 CSS 无关。 */
      audio {
        position: absolute;
        width: 0;
        height: 0;
        overflow: hidden;
        pointer-events: none;
      }
    </style>
  </head>
  <body>
    <div
      id="root"
      data-composition-id="{{COMPOSITION_ID}}"
      data-width="{{W}}"
      data-height="{{H}}"
      data-duration="{{TOTAL}}"
    >
{{SCENES}}
{{AUDIOS}}
    </div>
    <script>
      window.__timelines["{{COMPOSITION_ID}}"] = gsap.timeline({ paused: true });
    </script>
  </body>
</html>
"""


def host_html(spec) -> str:
    """宿主只填包名（注释里给人看的），六个占位符**一个都不填**（见 `HOST_TPL` 上方）。"""
    return string.Template(HOST_TPL).safe_substitute(PACK_NAME=spec.name)


# ---------------------------------------------------------------- 禁入区与词表核对

def geometry_violations(spec, tok: hp.Tok, layout: str) -> list:
    """法则 1 的编译期版本：任何元素的**最坏占位**不得进字幕禁入区。

    `layout_selfcheck` 只看 `bottom`/`inset` 两种写法，原语一律 `top` 定位 ⇒ 它看不见
    "顶边在 80cqh 以上、但按行数往下长进禁入区"的那一类。配方因此为每一步声明
    最坏高度（`Step.height_cqh`），这里按 `100 − reserve` 核。
    同一个函数还核呼吸位移的**上**边界 —— 内容层收准后层高是变量，位移量跟着层高走。
    """
    limit = 100.0 - tok.reserve_bottom - CONTENT_FLOOR_MARGIN_CQH
    problems = []
    steps = _steps(layout, tok, pack_prefix(spec.id))
    for step in steps:
        bottom = step.kwargs.get("top", 0.0) + step.height_cqh
        if bottom > limit:
            problems.append(
                f"{spec.id}/{layout} 的 {step.ident} 顶边 {step.kwargs.get('top')}cqh "
                f"+ 最坏占位 {step.height_cqh:.1f}cqh = {bottom:.1f}，超过内容下沿 "
                f"{limit:.1f}（禁入区 {tok.reserve_bottom}cqh 由 spec.subtitle 反算）")
        if step.kwargs.get("top", 0.0) < 0 or bottom > 100:
            problems.append(f"{spec.id}/{layout} 的 {step.ident} 几何越出画布")

    # 法则 15 的另一半：呼吸位移把内容层整体上移，收准区间后仍不许把顶边推出画布。
    span_top, span_bottom, full_bleed = _content_span(steps)
    # 法则 17：填幅。取最重的一条内容下沿，离内容区下沿不许空太多。
    placed = [step.kwargs["top"] + step.height_cqh for step in steps if "top" in step.kwargs]
    if placed and not full_bleed:
        dead = limit - max(placed)
        if dead > MAX_BOTTOM_DEAD_CQH:
            problems.append(
                f"{spec.id}/{layout}: 最重内容下沿只到 {max(placed):.1f}cqh，离内容区下沿 "
                f"{limit:.1f} 还空 {dead:.1f}cqh > {MAX_BOTTOM_DEAD_CQH}（法则 17 填幅）—— "
                "竖屏下半部空转就是「模板感」。把最重的内容往下推、或把字号放大到吃满")
    lift = abs(DRIFT_Y_PERCENT) / 100.0 * (span_bottom - span_top)
    if full_bleed and steps:
        problems.append(
            f"{spec.id}/{layout}: 有无 `top` 的步骤 ⇒ 内容层收不成区间，只能铺满画布，"
            f"而 `drift-y` 会把满幅盒子的顶边推出 `#root`（引擎报 container_overflow）。"
            "P3 挂全幅图层时要么让图层自带内缩，要么把位移改挂在有 `top` 的容器上")
    elif span_top < lift:
        problems.append(
            f"{spec.id}/{layout}: 内容层顶边 {span_top:.2f}cqh < 呼吸位移吃掉的 "
            f"{lift:.2f}cqh（`DRIFT_Y_PERCENT` × 层高 {span_bottom - span_top:.1f}cqh）—— "
            "上移时顶边会离开 `#root` 的裁剪区，引擎报 container_overflow")
    return problems


#: 几何比较的容差：`_num` 只留 4 位小数，栏宽又是推出来的（`94 − numeral_width(16)`），
#: 二进位误差不该被当成"压上了"。0.01cqw ≈ 0.1px，肉眼和 lint 都看不见。
GEOM_EPS = 0.01


def text_box(step: Step, tok: hp.Tok):
    """一个文字位的**盒**（法则 18 口径），返回 `(left, right, top, bottom)`；不是文字位返回 None。

    右沿 = ``left`` + ``max_width``，``block-chip`` 另加左右内边距：CSS 的 ``max-width``
    管的是**内容盒**，片的底色画到边框盒为止（P1-3e 那道横穿标题的色带就是这么来的）。
    """
    if not step.text:
        return None
    max_width = step.kwargs.get("max_width")
    if max_width is None:
        return None
    left = float(step.kwargs.get("left", tok.safe_left))
    right = left + float(max_width) + 2.0 * float(step.kwargs.get("pad_h", 0.0))
    top = float(step.kwargs.get("top", 0.0))
    return left, right, top, top + step.height_cqh


def overlap_violations(spec, tok: hp.Tok, layout: str) -> list:
    """法则 18：文字位必须有栏宽，且两两不得交。

    三条分支各自对应一种实测过的失效：
      1. **没声明栏宽** ⇒ 盒右沿未知。绝对定位只写 ``left`` 时宽度是收缩量
         （上限 ``100 − left``），"这一位会不会伸到下一位头上"在编译期根本不可判 ——
         拒编，因为这条闸一旦只看写了栏宽的那些位，就是假绿。
      2. **越出安全幅**（``left < safe_left`` 或 ``right > 100 − safe_right``）⇒ 版式
         声明的几何与 spec 的网格不符，出帧会贴边或被裁。
      3. **两盒相交** ⇒ 一定看得见。P1-3e 并排帧上的实物：眉标片（带底色）与标题
         行盒交 0.59cqh，那道强调色横穿就是这一条；此前没有任何闸拦得住它。
    """
    steps = _steps(layout, tok, pack_prefix(spec.id))
    problems: list = []
    boxes = []
    for step in steps:
        if not step.text:
            continue
        box = text_box(step, tok)
        if box is None:
            problems.append(
                f"{spec.id}/{layout} 的 {step.ident}（{step.prim}）没声明 max_width —— "
                "文字位的右沿因此未知，法则 18 的横向口径无法成立。字形位用 "
                "`kicker_width()`/`numeral_width()`，整句位写栏宽字面量并保证落在安全幅内")
            continue
        left, right, top, bottom = box
        if left < tok.safe_left - GEOM_EPS or right > (100.0 - tok.safe_right) + GEOM_EPS:
            problems.append(
                f"{spec.id}/{layout} 的 {step.ident} 横向落在 [{left:.2f}, {right:.2f}]cqw，"
                f"越出安全幅 [{tok.safe_left}, {100.0 - tok.safe_right}]（spec.grid.safe）")
        boxes.append((step.ident, box))
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            (a_id, (al, ar, at, ab)), (b_id, (bl, br, bt, bb)) = boxes[i], boxes[j]
            ox = min(ar, br) - max(al, bl)
            oy = min(ab, bb) - max(at, bt)
            if ox > GEOM_EPS and oy > GEOM_EPS:
                problems.append(
                    f"{spec.id}/{layout}: {a_id} 与 {b_id} 的盒相交 {ox:.2f}×{oy:.2f}cqw"
                    f"（法则 18）—— 两个文字位贴在一起，出帧必看得见")
    return problems


def contrast_floor_violations(spec, tok: hp.Tok, layout: str) -> list:
    """`size = "large"` 的色对只许出现在大字档（WCAG 24px ⇒ `LARGE_MIN_CQW`）。

    判据 3 按 spec 声明的档位选达标线（3.0 / 4.5），但"这一处真的有那么大吗"只有
    版式知道。暖纸的强调色 4.39:1 走大字档，写成 1.4cqw 的小字就同时骗过判据 3 和
    色板闸 —— 这条把它拦在出片前。
    """
    problems = []
    for step in _steps(layout, tok, pack_prefix(spec.id)):
        size = step.kwargs.get("size")
        if size is None:
            continue
        role = step.kwargs.get("role") or step.kwargs.get("credit_role")
        if role is None:
            continue
        if tok.pair(role)["size"] == "large" and float(size) < LARGE_MIN_CQW:
            problems.append(
                f"{spec.id}/{layout} 的 {step.ident} 用大字档色对 {role!r} 却只给 "
                f"{size}cqw < {LARGE_MIN_CQW:.2f}cqw（WCAG 大字 = 24px 起）—— "
                "该色对达标线按 3.0 数，缩到小字就按 4.5 数，那是判据 3 数不到的口子")
    return problems


# ---------------------------------------------------------------- 禁忌断言注册表（法则 13）

#: 入场补间的形状：`tl.fromTo("<sel>", {起}, {…, duration: D, …}, <秒>)`。
#: 位置参数**必须是数字字面量** —— 命名位置（`driftStart`）是呼吸位移/衔接，不是入场，
#: 不该吃入场下限。
ENTRANCE_RE = re.compile(
    r'tl\.fromTo\(\s*"(?P<sel>[^"]+)"\s*,\s*\{(?P<from>[^{}]*?)\}\s*,\s*'
    r'\{(?P<to>[^{}]*?)\}\s*,\s*(?P<at>[0-9.]+)\s*\)')
DURATION_RE = re.compile(r'duration:\s*([0-9.]+)')
EASE_VALUE_RE = re.compile(r'ease:\s*"([^"]+)"')
RADIUS_RE = re.compile(r'border(?:-[a-z-]+)?-radius\s*:')
#: 禁忌名里的时长参数（`entrance-not-faster-than-0p5s` ⇒ 0.5；`…-1s` ⇒ 1.0）。
#: 参数写在名字里，是因为下限本身是族级事实（号外族要快、杂志族要稳），
#: 注册表只认这一个口径：`<整数>[p<小数>]s`。
ENTRANCE_FASTER_RE = re.compile(r"^entrance-not-faster-than-(\d+)(?:p(\d+))?s$")


def _ease_head(name: str) -> str:
    """`back.out(2.8)` / `power3.out` / `sine` ⇒ `back` / `power3` / `sine`。

    只取第一段：GSAP 的缓动族名在点号前，参数在括号里。按整串比会漏
    `back`（写进 forbidden 的是 `back.out`），而全文子串比又会把
    `background:` 咬成 `back` —— 所以先取值、再切段，两步都不猜。
    """
    return name.split(".", 1)[0].split("(", 1)[0].strip()


def scan_entrances(texts: dict) -> tuple:
    """把七份文件里的入场补间摊成 `(已识别 [(文件, 选择器, 秒, 缓动)], 漏网描述)`。

    计数拿 `tl.fromTo(` 的**出现次数**对：形状一旦改动（将来原语把起终态写成变量、
    或多行换行）正则会静默少认，而"少认"在禁忌闸里等于通过 —— 那条漏网必须冒出来，
    否则入场下限断言就是假绿。同理：认出来但没有 `duration` 字面量的，GSAP 会按默认
    0.5s 走，闸也数不到，一并算漏网。
    """
    found, misses = [], []
    for name, text in sorted(texts.items()):
        matches = list(ENTRANCE_RE.finditer(text))
        total = text.count("tl.fromTo(")
        if total != len(matches):
            misses.append(f"{name} 有 {total} 条 `tl.fromTo(`，只认出 {len(matches)} 条入场形状")
        for m in matches:
            dur = DURATION_RE.search(m.group("to"))
            if dur is None:
                misses.append(f"{name} 的 {m.group('sel')} 没写 duration 字面量"
                              "（GSAP 默认 0.5s，断言数不到它）")
                continue
            ease = EASE_VALUE_RE.search(m.group("to"))
            found.append((name, m.group("sel"), float(dur.group(1)),
                          ease.group(1) if ease else ""))
    return found, misses


def easing_violations(spec, texts: dict) -> list:
    """补间里用到的每个缓动都必须在自家 `allowed` 里，且不碰 `forbidden`。

    这条无条件跑（不进注册表）：`motion.easing` 是 spec 必填层，法则 13 的"不许从
    forbidden 取值"此前只写在 `hf_primitives` 的模块注释里，实测并没有实现它的代码。
    全文扫 `ease:` 而不止入场 —— 呼吸位移和 P3 的图层补间一起核；但**只比 forbidden**，
    `allowed` 只约束入场：匀速 `ease:"none"` 是位移层的法则级词汇，不该塞进族的偏好表。
    """
    allowed = [_ease_head(e) for e in spec.motion["easing"]["allowed"]]
    forbidden = [_ease_head(e) for e in spec.motion["easing"]["forbidden"]]
    problems = []
    for name, text in sorted(texts.items()):
        for m in EASE_VALUE_RE.finditer(text):
            head = _ease_head(m.group(1))
            if head in forbidden:
                problems.append(f"{spec.id}/{name}: 用了本族禁用的缓动 {m.group(1)!r}")
    for name, sel, _dur, ease in scan_entrances(texts)[0]:
        head = _ease_head(ease)
        if head and head not in allowed:
            problems.append(f"{spec.id}/{name}: 入场 {sel} 的缓动 {ease!r} 不在 "
                            f"allowed {spec.motion['easing']['allowed']} 里")
    return problems


def _taboo_no_overshoot(spec, texts: dict, entrances: list, arg) -> list:
    """过冲 = GSAP 的 `back` / `elastic` / `bounce` 三个族（点号前那段）。"""
    hits = []
    for name, text in sorted(texts.items()):
        for m in EASE_VALUE_RE.finditer(text):
            if _ease_head(m.group(1)) in ("back", "elastic", "bounce"):
                hits.append(f"{name} 的补间用了过冲缓动 {m.group(1)!r}")
    return hits


def _taboo_no_border_radius(spec, texts: dict, entrances: list, arg) -> list:
    hits = []
    for name, text in sorted(texts.items()):
        for m in RADIUS_RE.finditer(text):
            hits.append(f"{name} 写了 {m.group(0)}")
    return hits


def _taboo_entrance_floor(spec, texts: dict, entrances: list, arg) -> list:
    return [f"{name} 的入场 {sel} 只有 {dur}s < 本族下限 {arg}s"
            for name, sel, dur, _ease in entrances if dur < arg]


#: 注册表：`taboos[].check` 的**精确名** → 实现。带参数的禁忌走
#: `ENTRANCE_FASTER_RE` 那条形状（名字里就写着本族的下限），两者都在下面解析。
#: 名字取不到实现 = 这条禁忌是散文（法则 13）。
#: 实现签名一律 `(spec, texts, entrances, arg)`：读得到全文、读得到已识别入场，
#: 参数从禁忌名里解析，不额外开 spec 通道 —— 族差别写在名字里就够了。
TABOO_CHECKS = {
    "no-overshoot": _taboo_no_overshoot,
    "no-border-radius": _taboo_no_border_radius,
}


def taboo_violations(spec, texts: dict) -> list:
    """逐条禁忌跑注册表。空 `texts` 直接返回 —— 上游已经拒编，别在这里报噪音。"""
    if not texts:
        return []
    entrances, misses = scan_entrances(texts)
    problems = [f"{spec.id}: 入场形状认不出（{m}）—— 入场类断言数不到这些补间，"
                f"先把形状改回 `tl.fromTo(sel, {{…}}, {{…, duration: D, …}}, <秒>)`"
                for m in misses]
    for taboo in spec.taboos:
        check, why = taboo["check"], taboo["why"]
        bound = ENTRANCE_FASTER_RE.match(check)
        if bound:
            # `0p5s` → 0.5、`1s` → 1.0：小数点写成 p 是因为 kebab-case 名里不许有 `.`
            #（`hf_style_spec.KEBAB_RE`），解析只认这一种写法。
            impl, arg = _taboo_entrance_floor, float(f"{bound.group(1)}.{bound.group(2) or 0}")
        else:
            impl, arg = TABOO_CHECKS.get(check), None
        if impl is None:
            problems.append(f"{spec.id}: 禁忌 {check!r} 在注册表里没有实现 —— 法则 13 要的是"
                            f"可执行断言，取不到实现就是散文（这条的原话：{why}）")
            continue
        for hit in impl(spec, texts, entrances, arg):
            problems.append(f"{spec.id}: 犯了自家禁忌 {check!r} —— {hit}（{why}）")
    return problems


def contract_violations(spec) -> list:
    """词表闭合：版式名 == 七个具名版式；变量 id == 发射器可推导的 id。"""
    problems = []
    if sorted(spec.layouts) != sorted(hs.CANONICAL_LAYOUTS):
        problems.append(f"{spec.id}: spec.layouts {spec.layouts} 不等于七个具名版式 "
                        f"{list(hs.CANONICAL_LAYOUTS)}")
    if sorted(CONTRACTS) != sorted(hs.CANONICAL_LAYOUTS):
        problems.append(f"CONTRACTS 的键 {sorted(CONTRACTS)} 不等于 CANONICAL_LAYOUTS")
    for layout, ids in CONTRACTS.items():
        if "slotSeconds" not in ids:
            problems.append(f"{layout}: 契约没声明 slotSeconds —— 动量预算会打空")
        for var_id in ids:
            if var_id == "slotSeconds" or INDEXED_SHAPE_RE.match(var_id):
                continue
            if var_id in _VAR_DEFAULTS:
                continue
            problems.append(f"{layout}: 变量 {var_id!r} 不在发射器词表里 —— "
                            "新 id 必须先加推导器再上版式（契约 §F.3）")
    return problems


# ---------------------------------------------------------------- 校验入口

def compile_violations(spec) -> list:
    """一份 spec 能不能编译成 pack。返回全部问题（空表 = 可编译）。"""
    problems = list(hs.precompile_violations(spec))
    problems.extend(contract_violations(spec))
    if problems:
        return problems          # 色板/契约都不成立就别再报几何噪音
    tok = hp.tokens_from_spec(spec, hs.caption_reserve_cqh(spec.subtitle))
    texts = {}
    for layout in hs.CANONICAL_LAYOUTS:
        problems.extend(geometry_violations(spec, tok, layout))
        problems.extend(overlap_violations(spec, tok, layout))
        problems.extend(contrast_floor_violations(spec, tok, layout))
        try:
            texts[layout] = composition_html(spec, tok, layout)
        except CompileError as exc:
            problems.append(str(exc))
    # 产物文本才有的两类核对：缓动词表（无条件）+ 逐条禁忌（法则 13）。
    # 放在这里而不是 `composition_html` 内部：禁忌是**包级**事实，一条违规该报一次，
    # 不该在七套版式里各刷一遍；且七份文件要放在一起看（入场形状漏认的计数才准）。
    problems.extend(easing_violations(spec, texts))
    problems.extend(taboo_violations(spec, texts))
    return problems


# ---------------------------------------------------------------- frame.md（编译产物）

def frame_md(spec, tok: hp.Tok) -> str:
    """把 spec 摊成 frame.md：色板表、字体表、法则、版式清单。

    这份文件从此**只能由编译器产出**（§6.1 的真源是 spec）。老包的手抄色值表
    正是靠"改一处忘三处"烂掉的（D10/D20），所以这里每一行都能从 spec 反推。
    """
    from audit_pack_contrast import BODY_MIN_RATIO, LARGE_MIN_RATIO, contrast_ratio

    ladder = spec.value_ladder
    lines = [
        f"# {spec.name} —— frame.md",
        "",
        "> ⚠️ 本文件由 `hf_compile.py`（schema `hf-compile/1`）从同目录的 `spec.toml` 编译生成，",
        "> **勿手改**：改数值请改 spec，然后重编译。手抄一份色值表就是 D10/D20 复发。",
        "",
        f"- 包 id：`{spec.id}` · 族：`{spec.family}`（网格语法 `{spec.grammar}`）",
        f"- 画布：{WIDTH}×{HEIGHT}（竖屏 9:16）· 单位一律 `cqw/cqh`",
        "- 渲染口径：三道闸 + `hyperframes check --strict`",
        "",
        "## 1. 色板与对比度",
        "",
        "下面两张表的**表头形状**是给 `audit_pack_contrast.py` 认的（`| token | 值 |` 色板表、",
        "`| 组合 | 比值 | 判定 |` 对比度表）：改列名 = 把第三个闸对本包变成空转。",
        "",
        "### 1.1 色板 token（含 HSL 明度与阶梯归属）",
        "",
        "| token | 值 | HSL 明度 | 阶梯档 | 参与阶梯 |",
        "|---|---|---|---|---|",
    ]
    accents = {str(a.get("hex", "")).lower() for a in spec.accents}

    def ladder_rung(hex_value: str) -> str:
        lightness = hs.hsl_lightness(hex_value)
        if str(hex_value).lower() in accents:
            return "—"
        return str(min(ladder, key=lambda step: abs(step - lightness)))

    def token_row(name: str, hex_value: str, participates: str,
                  rung: str | None = None) -> str:
        return (f"| {name} | `{hex_value}` | {hs.hsl_lightness(hex_value):.2f} | "
                f"{ladder_rung(hex_value) if rung is None else rung} | {participates} |")

    for name, hex_value in sorted(spec.surfaces.items()):
        is_accent = str(hex_value).lower() in accents
        lines.append(token_row(name, hex_value,
                               "否（强调色走 saturation-budget）" if is_accent else "是"))
    # 文字角色也进色板表：审计闸的第二条规则是"版式 HTML 里不许出色板外的 hex"，
    # 而版式上屏的字色来自 `color.text`，不在 `surfaces` 里 —— 不声明就会假违规。
    # 阶梯档一律写 "—"：文字色坐在哪个面上才有意义，它自己不构成明度结构（判据 5 数的是面）。
    for pair in spec.text_pairs:
        lines.append(token_row(pair["role"], pair["hex"],
                               "—（文字色，不是地面/面板）", rung="—"))
    lines += ["", f"阶梯 `{' → '.join(str(v) for v in ladder)}`，容差 "
                  f"±{hs.LADDER_TOLERANCE}（口径 `hf_style_spec.value_ladder_violations`）。",
              "", "### 1.2 文字 / 底色对（判据 3，逐对实测）", "",
              "| 组合 | 比值 | 判定 | 两端色值 | spec 档位 |", "|---|---|---|---|---|"]
    verdicts = {"body": f"正文（≥{BODY_MIN_RATIO}）过", "large": f"大字（≥{LARGE_MIN_RATIO}）过"}
    for pair in spec.text_pairs:
        background = spec.surfaces[pair["on"]]
        ratio = contrast_ratio(pair["hex"], background)
        lines.append(f"| {pair['role']} / {pair['on']} | {ratio:.2f} | {verdicts[pair['size']]} | "
                     f"`{pair['hex']}` on `{background}` | {pair['size']} |")
    lines += ["", "## 2. 字体", "",
              "| 位 | 族 | 字重 | 供给方式 |", "|---|---|---|---|",
              f"| 标题 display | `{tok.display_family}` | {tok.display_weight} | "
              "本文件自带 `@font-face` + `local()`（CJK 只能走本机） |",
              f"| 正文 body | `{tok.body_family}` | {tok.body_weight} | 同上 |",
              f"| 拉丁位 | `{tok.latin_display}` | — | 引擎自动供给（裸族名，加 `local()` "
              "反而失效） |",
              "",
              f"拉丁位锁死在引擎捆绑的 {len(hs.LATIN_CANONICAL_FAMILIES)} 个族里"
              "（`hf_style_spec.LATIN_CANONICAL_FAMILIES`）；集合外的名字会打 "
              "`font_family_without_font_face`（error 级）。", ""]

    lines += ["## 3. 网格与安全区", "",
              f"- 语法 `{spec.grammar}`，{spec.raw['grid']['columns']} 栏",
              f"- 横向安全区左右各 `{tok.safe_left}` / `{tok.safe_right}`（cqw），"
              "内容一律落在其间",
              f"- 底部字幕禁入区 `{tok.reserve_bottom}` cqh —— 由 `spec.subtitle` 的"
              "几何反算（不是手写的 20），见 `hf_style_spec.caption_reserve_cqh`", "",
              "## 4. 动效签名", "",
              f"- 签名 `{spec.motion['signature']}` · 缓动 `{tok.ease}"
              f"`（allowed 第 0 个即招牌缓动），禁 "
              f"{', '.join('`%s`' % e for e in spec.motion['easing']['forbidden'])}",
              f"- 招牌入场 `{tok.entrance_seconds}s`，单动作下限 `{tok.entrance_min}s`"
              "（法则 13：原语按 `max(下限, 招牌/2)` 构造，写不进去也就跳不过去）",
              f"- 动量预算常数 `INTRO_END = {hp.BUDGET_INTRO_END}`、"
              f"`MIN_DRIFT = {hp.BUDGET_MIN_DRIFT}`，每镜至少一条挂在 `driftDur` 上的"
              "持续位移（`drift = keep`）",
              "- 一律 `fromTo`（`.from()` 在 seek 回退时失步）；自带 background 的面"
              "禁 `opacity` 补间（法则 8）；无运行时随机（法则 10，抖动编译期烘焙）", "",
              "## 5. 版式清单", ""]
    p = pack_prefix(spec.id)
    for layout in hs.CANONICAL_LAYOUTS:
        steps = _steps(layout, tok, p)
        used = []
        for step in steps:
            if step.prim not in used:
                used.append(step.prim)
        lines += [f"### `{layout}.html` — 合成 id `{p}-{layout}`", "",
                  f"- 地面：`{GROUNDS[layout]}` = `{tok.face(GROUNDS[layout])}`"
                  + ("（`tone` 变量可翻墨面）" if layout in TONE_FLIPS else ""),
                  f"- 变量：{', '.join('`%s`' % v for v in CONTRACTS[layout])}",
                  f"- 原语：{', '.join('`%s`' % u for u in used)} + `drift-y`",
                  ""]

    lines += ["## 6. 禁忌（编译期断言，法则 13）", ""]
    for taboo in spec.taboos:
        lines.append(f"- `{taboo['check']}`：{taboo['why']}")
    lines += ["", "---", "",
              f"编译：`python skills/douyin-pro/scripts/hf_compile.py {spec.id}`",
              f"真源：`templates/hyperframes_path_c/{spec.id}/spec.toml`"
              f"（schema `{hs.SCHEMA_ID}`）", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- 落盘

def lint_composition(text: str, file_name: str) -> list:
    """把产物文本再喂一遍结构闸（不落盘也能看见违规）。"""
    tmp = Path(__file__).resolve().parent / ".hf_compile_probe.html"
    tmp.write_text(text, encoding="utf-8")
    try:
        return [f"{file_name}: {v}" for v in lsc.check_layout(tmp)]
    finally:
        tmp.unlink()


def compile_pack(spec_path: Path, out_root: Path = PACKS_ROOT,
                 write: bool = True) -> list:
    """spec.toml → 一个可装包的目录。返回写出的文件路径（`write=False` 时只返回将写的名字）。"""
    spec = hs.load_spec(Path(spec_path))
    problems = compile_violations(spec)
    if problems:
        raise CompileError(f"{spec.id} 拒编（{len(problems)} 条）:\n  " +
                           "\n  ".join(problems))
    tok = hp.tokens_from_spec(spec, hs.caption_reserve_cqh(spec.subtitle))

    out_dir = Path(out_root) / spec.id
    files = {out_dir / "host.html": host_html(spec),
             out_dir / "frame.md": frame_md(spec, tok)}
    for layout in hs.CANONICAL_LAYOUTS:
        text = composition_html(spec, tok, layout)
        found = lint_composition(text, f"{layout}.html")
        if found:
            raise CompileError(f"{spec.id}/{layout} 过不了结构闸:\n  " +
                               "\n  ".join(found))
        files[out_dir / "compositions" / f"{layout}.html"] = text

    if write:
        for path, text in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
    return sorted(files)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="spec.toml → HyperFrames 版式包（P1-3c）")
    parser.add_argument("pack", nargs="?", help="包 id（如 news-editorial-warm）；"
                                                "不给就编译 path_c 根下所有 spec.toml")
    parser.add_argument("--root", default=str(PACKS_ROOT), help="产物根目录")
    parser.add_argument("--check", action="store_true",
                        help="只核不写盘（CI 口径：spec 改动后确认仍能编译）")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    root = Path(args.root)
    if args.pack:
        specs = [root / args.pack / hs.SPEC_FILENAME]
    else:
        specs = sorted(root.glob(f"*/{hs.SPEC_FILENAME}"))
    if not specs:
        print(f"[hf_compile] {root} 下没有 {hs.SPEC_FILENAME}", file=sys.stderr)
        return 1
    failed = 0
    for spec_path in specs:
        if not spec_path.is_file():
            print(f"[hf_compile] 缺 spec: {spec_path}", file=sys.stderr)
            failed += 1
            continue
        try:
            written = compile_pack(spec_path, out_root=root, write=not args.check)
        except (CompileError, hs.SpecError) as exc:
            print(f"[hf_compile] ✗ {exc}", file=sys.stderr)
            failed += 1
            continue
        verb = "核过（未写盘）" if args.check else f"写出 {len(written)} 个文件"
        print(f"[hf_compile] ✓ {spec_path.parent.name}: {verb}")
        for path in written:
            print(f"    {path.relative_to(root)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
