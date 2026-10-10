#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""视觉原语库 · P0 十二个（spec §6.2）
============================================================
原语是 **Python 函数**，返回"这段版式要落进文件的三段文本"（CSS / HTML / JS），
不是 HTML 串模板 —— 因为法则 10 要求随机数在**编译期**烘焙成字面量，运行时不许再摇。

三条硬约束（`fragment_violations` 与 `path_b_selftest` 共用同一份判据）：
  · 补间一律 ``fromTo``（``from()`` 在 seek 回退时失步，D3 就是这么死的）；
  · 不许 ``onStart`` / ``onUpdate`` / ``onComplete``（seek 模型里它们不触发）；
  · 自带 ``background`` 的元素禁止 ``opacity`` 补间（法则 8：半透明面与地面混色实测把
    对比度拖到 2.5:1）。本模块的处理是**结构性避开**：要淡入的只能是纯文字或 ``<img>``
    asset，有色面一律 ``clip-path`` / ``scaleX`` / ``scaleY``。

前置条件（``requires`` / ``contrast`` / ``budget``）在这里是**数据**，编译器按数据取原语、
按数据拒编；``requires`` 的每个名字必须有实现（见 ``check_preconditions``），否则拒编。
``contrast`` 的值集在 §6.2 的
``inherits|self-proofs|requires-chip`` 之外**加了一个 ``none``**（纯形状/纹理，
根本不承载文字）—— 已记入 spec 的 P1 实施记录。

几何口径：一律 ``cqw/cqh``（结构闸 ``PX_TYPOGRAPHY`` 禁 px 排版）；被补间的元素
CSS 里不许出现 ``transform``（法则 7，起始值交给 ``fromTo`` 的 from 侧）。
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Callable, Tuple

SCHEMA = "hf-primitives/1"

#: 法则 10：编译期摇出的抖动只能是字面量。固定种子 ⇒ 同稿必得同串数。
BAKE_SEED = 20261009

#: 结构闸 `layout_selfcheck` 认这两个具名常数（MAGIC_BUDGET_VALUE），
#: 所以预算块只能长这样：改数字可以，改名不行。
BUDGET_INTRO_END = 1.5
BUDGET_MIN_DRIFT = 0.6

#: 每个版式脚本体开头必发的动量预算（§4 动量预算，与 news-coral/frame.md 同式）。
BUDGET_JS = """\
        const slot = Number(vars.slotSeconds) || 4;
        const INTRO_END = {intro_end};
        const MIN_DRIFT = {min_drift};
        const driftStart = Math.max(0, Math.min(INTRO_END, slot - MIN_DRIFT));
        const driftDur = Math.max(MIN_DRIFT, slot - driftStart);
"""


@dataclass(frozen=True)
class Tok:
    """一次编译的 token 束：全部来自 spec，编译器不许在函数里另造数。"""

    surfaces: dict
    text: dict
    accents: list
    display_family: str
    display_weight: int
    body_family: str
    body_weight: int
    latin_display: str
    ease: str
    entrance_seconds: float
    entrance_min: float
    safe_left: float
    safe_right: float
    reserve_bottom: float

    def pair(self, role: str) -> dict:
        if role not in self.text:
            raise KeyError(f"spec 里没有 {role!r} 这个文字角色（有: {sorted(self.text)}）")
        return self.text[role]

    def face(self, surface: str) -> str:
        if surface not in self.surfaces:
            raise KeyError(f"spec 里没有 {surface!r} 这个面（有: {sorted(self.surfaces)}）")
        return self.surfaces[surface]


def _split_font(value: str) -> Tuple[str, int]:
    family, _, weight = str(value).rpartition("/")
    return family.strip(), int(weight.strip() or 400)


def tokens_from_spec(spec, reserve_bottom: float, ease_index: int = 0) -> Tok:
    """把 ``hf_style_spec.Spec`` 压成原语好用的形状。

    ``ease`` 取 ``motion.easing.allowed[ease_index]``，口径是"allowed 按偏好排序，
    第 0 个即这一族的招牌缓动"。这不是隐式猜：校验强制 allowed 非空，
    而 forbidden 里的缓动另有一道断言（编译器不许从 forbidden 取值）。
    """
    typ = spec.raw["type"]
    motion = spec.raw["motion"]
    display_family, display_weight = _split_font(typ["display"])
    body_family, body_weight = _split_font(typ["body"])
    allowed = motion["easing"]["allowed"]
    return Tok(
        surfaces=dict(spec.surfaces),
        text={pair["role"]: pair for pair in spec.text_pairs},
        accents=list(spec.accents),
        display_family=display_family,
        display_weight=display_weight,
        body_family=body_family,
        body_weight=body_weight,
        latin_display=str(typ["latin"][0]),
        ease=str(allowed[min(int(ease_index), len(allowed) - 1)]),
        entrance_seconds=float(motion["entrance-seconds"]),
        entrance_min=float(motion["entrance-min-seconds"]),
        safe_left=float(spec.raw["grid"]["safe"]["left"]),
        safe_right=float(spec.raw["grid"]["safe"]["right"]),
        reserve_bottom=float(reserve_bottom),
    )


def _num(value: float) -> str:
    """22.0 → ``22``、1.25 → ``1.25``。版式文件是给人读的，别拖尾零。"""
    text = f"{float(value):.4f}".rstrip("0").rstrip(".")
    return text or "0"


#: JS 合法标识符（`$` 允许但不产生）。`fragment_violations` 用它核 `const` 声明名。
JS_IDENT_RE = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")
#: 带初值的声明语句头部（`const ew-hk-topChars = …`）—— 只数有 `=` 的，
#: 因为原语里的局部名一律是"算出来的值"，而 `const x;` 那种写法不该由这条闸管。
JS_DECL_NAME_RE = re.compile(r"\b(?:const|let|var)\s+([^\s=;]+)(?=\s*=)")


def js_name(ident: str) -> str:
    """DOM id → 合法 JS 局部名：``ew-hk-top`` → ``ewHkTop``。

    为什么必须换：编译器的 ident 是 kebab（``{前缀}-{版式}-{位}``），直接拼进
    ``const ew-hk-topChars = …`` 会让**整个** inline script 语法不合法 —— 引擎的
    ``invalid_inline_script_syntax`` 是 error 级，一处坏、五个版式一起被判死。
    驼峰化对 kebab 词法是无损的（分段内容与段数都保留），所以同框的两个 char-rise
    不会撞局部名。代价是词法必须统一：`ew-hk-top` 与 `ew_hk_top` 会撞成同一个名字，
    因此 ident 只许 kebab —— `hf_compile` 那边由命名规则保证。
    """
    parts = [p for p in re.split(r"[^0-9A-Za-z]+", ident) if p]
    if not parts:
        parts = ["el"]
    name = parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])
    return name if JS_IDENT_RE.match(name) else "el" + name



def bake_jitter(count: int, amplitude: float, seed: int = BAKE_SEED) -> list:
    """编译期摇出 ``count`` 个 ±amplitude 的偏移，返回**字面量**列表。

    运行时不许再摇（法则 10）。种子串把三个入参都编进去，所以同 count/amplitude/seed
    必得同一串 —— "同稿同片"不受影响。手绘族的抖、纸屑的落点从这里取数。
    """
    rng = random.Random(f"{seed}:{count}:{amplitude}")
    return [round(rng.uniform(-amplitude, amplitude), 3) for _ in range(max(0, int(count)))]


@dataclass(frozen=True)
class Fragment:
    """一个原语落到版式文件里的文本片段。"""

    primitive: str
    css: str = ""
    html: str = ""
    pre_js: tuple = ()
    tweens: tuple = ()
    text_bearing: bool = False
    face: bool = False        # 自带 background 的面 —— 法则 8 的管辖对象

    @property
    def js(self) -> str:
        return "\n".join(list(self.pre_js) + list(self.tweens))


@dataclass(frozen=True)
class Primitive:
    name: str
    requires: tuple                                # 前置条件名，见 check_preconditions
    contrast: str                                  # inherits|self-proofs|requires-chip|none
    seek_safe: str
    budget: tuple
    render: Callable[..., Fragment] = field(repr=False)


# ------------------------------------------------------------------ P0 十二个

def clip_wipe_up(tok: Tok, ident: str, *, top: float, height: float, left: float = None,
                 right: float = None, surface: str = "panel", delay: float = 0.0,
                 duration: float = None) -> Fragment:
    """有色面上涌揭示：盒子**已在位**，用 ``clip-path`` 从下往上放墨。

    同时满足法则 8（不动 opacity）与法则 15（不从画外滑进来）。
    P0-2 实测：界内遮罩揭示在 ``check --strict`` 下 0 违规；但越界盒藏不住
    （检测器量 layout box），所以几何全落在安全区内。
    ``left``/``right`` 是栏位偏移（非对称栏语法要的就是这个）：不给就用安全区两侧。
    """
    dur = tok.entrance_seconds if duration is None else duration
    x = tok.safe_left if left is None else left
    r = tok.safe_right if right is None else right
    return Fragment(
        primitive="clip-wipe-up",
        css=(f"#{ident} {{ position: absolute; top: {_num(top)}cqh; "
             f"left: {_num(x)}cqw; right: {_num(r)}cqw; "
             f"height: {_num(height)}cqh; background: {tok.face(surface)}; }}\n"),
        html=f'<div id="{ident}"></div>',
        tweens=(f'tl.fromTo("#{ident}", {{ clipPath: "inset(100% 0 0 0)" }}, '
                f'{{ clipPath: "inset(0 0 0 0)", duration: {_num(dur)}, '
                f'ease: "{tok.ease}" }}, {_num(delay)});',),
        face=True,
    )


def char_rise(tok: Tok, ident: str, *, var_id: str, role: str, size: float,
              top: float, left: float = None, weight: int = None, serif: bool = True,
              line_height: float = 1.24, stagger: float = 0.045,
              rise: float = 14.0, per_char: float = None,
              delay: float = 0.0, max_width: float = 88.0) -> Fragment:
    """逐字上涌（杂志族招牌）。

    切分在脚本体内同步做（``Array.from`` 按码点），**不是** onStart ——
    补间在时间轴创建时就必须已存在，seek 才能回退（P0-1 的稳态结论：18 码点、
    ``stagger:0.045``、单字 0.7s，两次抽帧逐字节一致）。
    单字时长默认 ``entrance-seconds`` 的一半，但**不低于禁忌下限** ``entrance-min-seconds``，
    这样法则 13 的 ``entrance-not-faster-than-0p5s`` 是按构造成立的。
    容器里留一个静态 ``<span class="{ident}-ch">`` 占位：空镜兜底，且让结构闸在
    **真标记**上看到这个类，而不是靠 JS 字符串里的形状。
    运行时先 ``removeAttribute("data-var-text")`` 再清空：引擎的变量写入对**有元素子节点**
    的容器走 append 支路（``hyperframe-runtime.js:350`` 的 ``_1``），会把整串另塞成一个
    文本节点 ⇒ 文字渲染两遍（P1-3e 实测）。摘掉属性后脚本是唯一写入者，且对"引擎先写"
    的旧顺序同样成立（先写的文本会被 ``textContent = ""`` 抹平）。
    """
    pair = tok.pair(role)
    each = per_char if per_char is not None else max(tok.entrance_min, tok.entrance_seconds * 0.5)
    cls = f"{ident}-ch"
    name = js_name(ident)
    family = tok.display_family if serif else tok.body_family
    x = tok.safe_left if left is None else left
    return Fragment(
        primitive="char-rise",
        css=(f"#{ident} {{ position: absolute; top: {_num(top)}cqh; "
             f"left: {_num(x)}cqw; max-width: {_num(max_width)}cqw; "
             f"font-family: {family}, serif; font-size: {_num(size)}cqw; "
             f"font-weight: {weight or tok.display_weight}; line-height: {_num(line_height)}; "
             f"letter-spacing: -0.01em; color: {pair['hex']}; }}\n"
             f".{cls} {{ display: inline-block; }}\n"),
        html=f'<div id="{ident}" data-var-text="{var_id}"><span class="{cls}"></span></div>',
        pre_js=(f'const {name}Chars = Array.from(String(vars["{var_id}"] || "").trim());',
                f'const {name}Box = document.getElementById("{ident}");',
                f'{name}Box.removeAttribute("data-var-text");',
                f'{name}Box.textContent = "";',
                f'{name}Chars.forEach(function (ch) {{',
                f'  const {name}Span = document.createElement("span");',
                f'  {name}Span.className = "{cls}";',
                f'  {name}Span.textContent = ch;',
                f'  {name}Box.appendChild({name}Span);',
                f'}});'),
        tweens=(f'tl.fromTo(".{cls}", {{ y: {_num(rise)}, opacity: 0 }}, '
                f'{{ y: 0, opacity: 1, duration: {_num(each)}, stagger: {_num(stagger)}, '
                f'ease: "{tok.ease}" }}, {_num(delay)});',),
        text_bearing=True,
    )


def rule_pull(tok: Tok, ident: str, *, top: float, width: float = 14.0,
              left: float = None, thickness: float = 1.1, surface: str = "accent",
              origin: str = "0% 50%", delay: float = 0.0,
              duration: float = 0.45) -> Fragment:
    """短标尺横向擦入。强调色的合法用法之一：只做形状（L1 的泛化）。

    时长按 ``max(下限, 传入)`` 抬到本包 ``entrance-min-seconds`` 以上（与
    ``cue-fade``/``char-rise`` 同一口径）：族要快就给 spec 写个小下限，
    而不是在这里写死数字 —— 那样法则 13 的禁忌对每个族都按构造成立。
    """
    x = tok.safe_left if left is None else left
    dur = max(tok.entrance_min, duration)
    return Fragment(
        primitive="rule-pull",
        css=(f"#{ident} {{ position: absolute; top: {_num(top)}cqh; "
             f"left: {_num(x)}cqw; width: {_num(width)}cqw; "
             f"height: {_num(thickness)}cqh; background: {tok.face(surface)}; "
             f"transform-origin: {origin}; }}\n"),
        html=f'<div id="{ident}"></div>',
        tweens=(f'tl.fromTo("#{ident}", {{ scaleX: 0 }}, '
                f'{{ scaleX: 1, duration: {_num(dur)}, ease: "{tok.ease}" }}, '
                f'{_num(delay)});',),
        face=True,
    )


def hairline(tok: Tok, ident: str, *, top: float, width: float = 88.0,
             left: float = None,
             surface: str = "rule", thickness: float = 0.35,
             delay: float = 0.0, duration: float = 0.6) -> Fragment:
    """通栏发丝线：几何不动，用 ``clip-path`` 从左往右画。

    与 ``rule-pull`` 的分工有实据：长条 ``scaleX`` 会把端点粗细一起缩放，
    编辑排版的细线要的正是均匀粗细 —— 长线走遮罩、短线走生长。
    """
    x = tok.safe_left if left is None else left
    return Fragment(
        primitive="hairline",
        css=(f"#{ident} {{ position: absolute; top: {_num(top)}cqh; "
             f"left: {_num(x)}cqw; width: {_num(width)}cqw; "
             f"height: {_num(thickness)}cqh; background: {tok.face(surface)}; }}\n"),
        html=f'<div id="{ident}"></div>',
        tweens=(f'tl.fromTo("#{ident}", {{ clipPath: "inset(0 100% 0 0)" }}, '
                f'{{ clipPath: "inset(0 0 0 0)", duration: {_num(duration)}, '
                f'ease: "{tok.ease}" }}, {_num(delay)});',),
        face=True,
    )


def block_chip(tok: Tok, ident: str, *, var_id: str, role: str, top: float,
               size: float, left: float = None, surface: str = "accent",
               default_text: str = "", max_width: float = None,
               pad_v: float = 1.0, pad_h: float = 2.0, origin: str = "0% 50%",
               delay: float = 0.0, duration: float = 0.4) -> Fragment:
    """片块 + 片上文字：自带底色 ⇒ **只能** ``scaleX`` 擦入（法则 8）。

    片上文字的对比度由 spec ``color.text`` 里 ``on=<surface>`` 那条色对担保，
    所以这个原语是 ``self-proofs``：选到配对角色就安全；选不到（强调色当正文）
    早在 ``contrast_violations`` 那关拒编了。

    ``max_width`` 是**法则 18 的口径来源**，不是装饰：写了它，盒宽就被 CSS 钉死，
    超长的字宁可折行（变高）也不变宽 —— 于是编译期算出来的横向边界在浏览器里
    仍然成立，重叠判定不是纸面数字。不写 ⇒ 编译器的 ``overlap_violations`` 按
    "无栏宽口径的文字位" 拒编。

    时长同 ``rule-pull``：抬到本包 ``entrance-min-seconds`` 以上，族差别留在 spec 里。
    """
    pair = tok.pair(role)
    x = tok.safe_left if left is None else left
    dur = max(tok.entrance_min, duration)
    cap = "" if max_width is None else f"max-width: {_num(max_width)}cqw; "
    return Fragment(
        primitive="block-chip",
        css=(f"#{ident} {{ position: absolute; top: {_num(top)}cqh; "
             f"left: {_num(x)}cqw; {cap}background: {tok.face(surface)}; "
             f"color: {pair['hex']}; font-size: {_num(size)}cqw; "
             f"font-weight: {tok.display_weight}; padding: {_num(pad_v)}cqh {_num(pad_h)}cqw; "
             f"transform-origin: {origin}; }}\n"),
        html=f'<div id="{ident}" data-var-text="{var_id}">{default_text}</div>',
        tweens=(f'tl.fromTo("#{ident}", {{ scaleX: 0 }}, '
                f'{{ scaleX: 1, duration: {_num(dur)}, ease: "{tok.ease}" }}, '
                f'{_num(delay)});',),
        text_bearing=True, face=True,
    )


def giant_numeral(tok: Tok, ident: str, *, value_var: str, unit_var: str = None,
                  role: str, top: float, left: float = None, size: float = 30.0,
                  unit_size: float = 7.4, max_width: float = None,
                  line_height: float = 1.12, delay: float = 0.0,
                  duration: float = None) -> Fragment:
    """巨号数字（数据位主角）。只做 clip 揭示，**不做数字滚动** ——
    滚动要 ``onUpdate``，seek 模型里不触发（D3 同一死因）；它排在 P1 档，
    且必须先解决 seek 可回退才允许进产线。

    ``max_width`` 在这里尤其不是可选项：绝对定位只写 ``left`` 时盒宽是收缩量，
    上限 ``100−left``，所以"右沿落在哪"完全取决于数字位数 —— 钉住它才有法则 18
    的横向口径。
    """
    dur = tok.entrance_seconds if duration is None else duration
    pair = tok.pair(role)
    x = tok.safe_left if left is None else left
    cap = "" if max_width is None else f"max-width: {_num(max_width)}cqw; "
    css = (f"#{ident} {{ position: absolute; top: {_num(top)}cqh; "
           f"left: {_num(x)}cqw; {cap}font-family: {tok.latin_display}, sans-serif; "
           f"font-size: {_num(size)}cqw; line-height: {_num(line_height)}; "
           f"color: {pair['hex']}; }}\n")
    if unit_var:
        css += (f".{ident}-unit {{ font-family: {tok.body_family}, sans-serif; "
                f"font-size: {_num(unit_size)}cqw; font-weight: {tok.body_weight}; }}\n")
    unit = (f'<span class="{ident}-unit" data-var-text="{unit_var}"></span>'
            if unit_var else "")
    return Fragment(
        primitive="giant-numeral",
        css=css,
        html=(f'<div id="{ident}"><span class="{ident}-value" '
              f'data-var-text="{value_var}"></span>{unit}</div>'),
        tweens=(f'tl.fromTo("#{ident}", {{ clipPath: "inset(0 0 100% 0)" }}, '
                f'{{ clipPath: "inset(0 0 0 0)", duration: {_num(dur)}, '
                f'ease: "{tok.ease}" }}, {_num(delay)});',),
        text_bearing=True,
    )


def cue_fade(tok: Tok, ident: str, *, var_id: str, role: str, top: float, size: float,
             left: float = None, serif: bool = False, letter_spacing: float = None,
             delay: float = 0.0, duration: float = 0.5, max_width: float = 74.0,
             rise: float = 22.0, line_height: float = 1.55) -> Fragment:
    """纯文字淡入（"墨才允许淡入"那一半法则）：无 background ⇒ opacity 合法。

    ``serif=True`` 把这一条交给显示族（杂志族的引文/屏句要宋体）；
    ``letter_spacing`` 只在眉标一类的小字上给，正文不许拉字距。
    """
    pair = tok.pair(role)
    each = max(tok.entrance_min, duration)
    x = tok.safe_left if left is None else left
    family = tok.display_family if serif else tok.body_family
    spacing = "" if letter_spacing is None else f" letter-spacing: {_num(letter_spacing)}em;"
    return Fragment(
        primitive="cue-fade",
        css=(f"#{ident} {{ position: absolute; top: {_num(top)}cqh; "
             f"left: {_num(x)}cqw; max-width: {_num(max_width)}cqw; "
             f"font-family: {family}, sans-serif; font-size: {_num(size)}cqw; "
             f"font-weight: {tok.body_weight};{spacing} line-height: {_num(line_height)}; "
             f"color: {pair['hex']}; }}\n"),
        html=f'<div id="{ident}" data-var-text="{var_id}"></div>',
        tweens=(f'tl.fromTo("#{ident}", {{ opacity: 0, y: {_num(rise)} }}, '
                f'{{ opacity: 1, y: 0, duration: {_num(each)}, ease: "{tok.ease}" }}, '
                f'{_num(delay)});',),
        text_bearing=True,
    )


def keyword_tint(tok: Tok, ident: str, *, var_id: str, role: str, top: float,
                 size: float, left: float = None, max_width: float = None,
                 delay: float = 0.0, duration: float = None) -> Fragment:
    """关键词染色：杂志族不用色块，用色本身。

    强调色能不能坐在字上由 ``color.accents[].role`` 决定（``shape-or-large-text`` 才允许，
    且字号必须走大字档）—— 这条前置条件由 ``check_preconditions`` 拦，
    而"色对是否达标"由 spec 的判据 3 拦（两条独立，都过才出字）。

    ``max_width`` 同 ``block-chip``：它是法则 18 的横向口径，不写就等于"这个位子的
    右边界编译器不知道"。
    """
    pair = tok.pair(role)
    dur = tok.entrance_seconds if duration is None else duration
    x = tok.safe_left if left is None else left
    cap = "" if max_width is None else f"max-width: {_num(max_width)}cqw; "
    return Fragment(
        primitive="keyword-tint",
        css=(f"#{ident} {{ position: absolute; top: {_num(top)}cqh; left: {_num(x)}cqw; "
             f"{cap}font-family: {tok.display_family}, serif; font-size: {_num(size)}cqw; "
             f"font-weight: {tok.display_weight}; color: {pair['hex']}; }}\n"),
        html=f'<div id="{ident}" data-var-text="{var_id}"></div>',
        tweens=(f'tl.fromTo("#{ident}", {{ opacity: 0 }}, '
                f'{{ opacity: 1, duration: {_num(dur)}, ease: "{tok.ease}" }}, '
                f'{_num(delay)});',),
        text_bearing=True,
    )


def photo_duotone(tok: Tok, ident: str, *, path_var: str, credit_var: str,
                  credit_role: str = "secondary", tint_surface: str = "accent",
                  opacity: float = 0.42, delay: float = 0.0,
                  duration: float = 0.8) -> Fragment:
    """图片双色化：图先转灰再叠一层面色。图是**纹理**不是证据（裁决 3）。

    ``<img>`` 是 asset 不是 background-color 面块，opacity 淡入合法
    （news-coral 同口径，实测过 ``check --strict``）。层底边停在禁入区上沿。
    图注是**会出现在画面上的文字**，所以颜色必须从 spec 的色对里取（credit_role），
    留空继承会让判据 3 数不到这一对 —— 那是"每对都列全"这条契约的漏洞。
    """
    credit = tok.pair(credit_role)
    name = js_name(ident)
    return Fragment(
        primitive="photo-duotone",
        css=(f"#{ident} {{ position: absolute; top: 0; left: 0; right: 0; "
             f"bottom: {_num(tok.reserve_bottom)}cqh; overflow: hidden; display: none; }}\n"
             f"#{ident} .{ident}-img {{ width: 100%; height: 100%; display: block; "
             f"object-fit: cover; filter: grayscale(1) contrast(1.08); }}\n"
             f"#{ident} .{ident}-tint {{ position: absolute; inset: 0; "
             f"background: {tok.face(tint_surface)}; mix-blend-mode: multiply; "
             f"opacity: {_num(opacity)}; pointer-events: none; }}\n"
             f"#{ident}-credit {{ position: absolute; right: {_num(tok.safe_right)}cqw; "
             f"bottom: {_num(tok.reserve_bottom)}cqh; font-size: 1.4cqw; color: {credit['hex']}; "
             f"line-height: 1.3; letter-spacing: 0.08em; }}\n"),
        html=(f'<figure id="{ident}"><img class="{ident}-img" alt="" />'
              f'<span class="{ident}-tint"></span></figure>'
              f'<figcaption id="{ident}-credit" data-var-text="{credit_var}"></figcaption>'),
        pre_js=(f'const {js_name(ident)}Path = String(vars["{path_var}"] || "").trim();',
                f'if ({js_name(ident)}Path) {{',
                f'  document.getElementById("{ident}").style.display = "block";',
                f'  document.querySelector("#{ident} .{ident}-img").src = {js_name(ident)}Path;',
                f'}}'),
        tweens=(f'tl.fromTo("#{ident}", {{ opacity: 0 }}, '
                f'{{ opacity: 1, duration: {_num(duration)}, ease: "{tok.ease}" }}, '
                f'{_num(delay)});',),
    )


def photo_local_crop(tok: Tok, ident: str, *, path_var: str, top: float, height: float,
                     width: float = 44.0, position: str = "50% 40%",
                     delay: float = 0.0, duration: float = 0.7) -> Fragment:
    """局部裁切：只取图的一小块当纹理，用 ``clip-path`` 方形揭示。

    几何在安全区内，所以不需要 ``data-layout-allow-overflow``（法则 11：
    遮罩藏不住越界 layout box，能不用就不用）。
    """
    name = js_name(ident)
    return Fragment(
        primitive="photo-local-crop",
        css=(f"#{ident} {{ position: absolute; top: {_num(top)}cqh; "
             f"left: {_num(tok.safe_left)}cqw; width: {_num(width)}cqw; "
             f"height: {_num(height)}cqh; overflow: hidden; display: none; }}\n"
             f"#{ident} img {{ width: 100%; height: 100%; display: block; "
             f"object-fit: cover; object-position: {position}; }}\n"),
        html=f'<figure id="{ident}"><img alt="" /></figure>',
        pre_js=(f'const {name}Src = String(vars["{path_var}"] || "").trim();',
                f'if ({name}Src) {{',
                f'  document.getElementById("{ident}").style.display = "block";',
                f'  document.querySelector("#{ident} img").src = {name}Src;',
                f'}}'),
        tweens=(f'tl.fromTo("#{ident}", {{ clipPath: "inset(0 100% 0 0)" }}, '
                f'{{ clipPath: "inset(0 0 0 0)", duration: {_num(duration)}, '
                f'ease: "{tok.ease}" }}, {_num(delay)});',),
    )


def ken_burns_in(tok: Tok, ident: str, *, from_scale: float = 1.0,
                 to_scale: float = 1.06, ease: str = "power1.inOut") -> Fragment:
    """缓慢推镜。连续位移的一种，时长必须挂在 ``driftDur`` 上 ——
    结构闸 ``MISSING_CONTINUOUS_MOTION`` 数的就是这个。
    """
    return Fragment(
        primitive="ken-burns-in",
        tweens=(f'tl.fromTo("#{ident}", {{ scale: {_num(from_scale)} }}, '
                f'{{ scale: {_num(to_scale)}, duration: driftStart + driftDur, '
                f'ease: "{ease}" }}, 0);',),
    )


def drift_y(tok: Tok, ident: str, *, percent: float = -3.0) -> Fragment:
    """呼吸位移：每个版式至少要有一条，否则尾段冻住（判据 3 的动量预算）。

    作用对象必须是**内容容器**，不能是带 ``.clip`` 的挂载元素
    （lint ``gsap_animates_clip_element``）。
    """
    return Fragment(
        primitive="drift-y",
        tweens=(f'tl.to("#{ident}", {{ yPercent: {_num(percent)}, duration: driftDur, '
                f'ease: "none" }}, driftStart);',),
    )


PRIMITIVES: dict = {
    p.name: p
    for p in (
        Primitive("clip-wipe-up", ("solid-ground",), "none",
                  "by-construction", ("paint:high", "frames:1"), clip_wipe_up),
        Primitive("char-rise", (), "inherits",
                  "by-construction", ("paint:low", "dom:chars"), char_rise),
        Primitive("rule-pull", ("solid-ground",), "none",
                  "by-construction", ("paint:mid", "frames:1"), rule_pull),
        Primitive("hairline", ("solid-ground",), "none",
                  "by-construction", ("paint:low", "frames:1"), hairline),
        Primitive("block-chip", ("paired-text-role",), "self-proofs",
                  "by-construction", ("paint:mid", "frames:1"), block_chip),
        Primitive("giant-numeral", (), "inherits",
                  "by-construction", ("paint:low", "frames:1"), giant_numeral),
        Primitive("cue-fade", (), "inherits",
                  "by-construction", ("paint:low", "frames:1"), cue_fade),
        Primitive("keyword-tint", ("accent-allows-large-text",), "requires-chip",
                  "by-construction", ("paint:low", "frames:1"), keyword_tint),
        Primitive("photo-duotone", ("asset", "image-gate-ready"), "none",
                  "by-construction", ("paint:high", "frames:1"), photo_duotone),
        Primitive("photo-local-crop", ("asset", "image-gate-ready"), "none",
                  "by-construction", ("paint:mid", "frames:1"), photo_local_crop),
        Primitive("ken-burns-in", ("image-gate-ready",), "none",
                  "by-construction", ("motion:continuous",), ken_burns_in),
        Primitive("drift-y", ("container-not-clip",), "none",
                  "by-construction", ("motion:continuous",), drift_y),
    )
}

P0_NAMES = tuple(PRIMITIVES)

#: P3（图片门禁）落地前，任何取图的原语都不许被编译器选中 —— 这条不是占位：
#: ``check_preconditions`` 在 ``image_gate_ready=False`` 时直接拒，实测有效。
GATED_REQUIRES = frozenset({"image-gate-ready"})

#: 检查器能直接判的前置条件（入参就是判据所需的事实）。
#: `asset` **不在这里** —— 编译期拿不到"这一镜最终取不取到图"（构建期 Commons 抖动会
#: 让同稿两跑一次有图一次无图）。留在 CHECKED 里就是个恒 False 的假接口（老形态：
#: `hf_compile.py` 不传，`check_preconditions` 一律拒）。asset 迁到 CALLSITE_REQUIRES，
#: 强制点在 pre_js 的"空路径塌槽"分支（`hf_primitives.py:474-478` 已实现）。
CHECKED_REQUIRES = ("solid-ground", "image-gate-ready", "accent-allows-large-text")

#: 由**调用点/别处的闸构造性满足**的前置条件：值集在这里列全，强制点在说明里点名。
#: 不进 ``check_preconditions`` 的入参，是因为那两个事实它拿不到（色对角色要到取参数时
#: 才知道，挂载元素是不是 ``.clip`` 要到版式落盘后结构闸才看得见）。
CALLSITE_REQUIRES = {
    "paired-text-role": "Tok.pair()/face() 认不到就抛 KeyError 并列出全部可用角色",
    "container-not-clip": "结构闸 layout_selfcheck 的 gsap_animates_clip_element 拒补间挂在 .clip 挂载元素上",
    "asset": "构建期 _resolve_shot_image 落 image_record；无图 → resolve_variable 的 "
             "imagePath='' → photo-duotone/photo_local_crop 的 pre_js 空路径塌槽 "
             "(hf_primitives.py:474-478)，版式退化为无图态。图存在与否不是编译期事实。",
}

#: ``solid-ground`` 的口径：地面必须是 spec 声明的实色面，不能是照片/纹理。
#: 形状（chip/标尺/发丝线）压在噪声上时，边缘对比度不可算，判据 3 数不到它。
SOLID_GROUNDS = ("ink", "paper")

#: 法则 10 / D3 的反面写法。回调只写裸词（``onStart`` 而不是 ``.onStart(``）——
#: GSAP 里它们是**补间参数表的键**（``{ onUpdate: tick }``），带点的形状一条也抓不到，
#: 老 hook.html:224 的死法就是键形式。误伤方向是拒编，比放行安全。
#: ``.from(`` 只用正则拦，且豁免 ``Array.from(`` —— 那是**按码点切字**，
#: 拿子串判会把招牌原语自己打死（第一版就是这么踩到的）。
FORBIDDEN_JS = ("Math.random(", "onStart", "onUpdate", "onComplete")
GAP_FROM_RE = re.compile(r"(?<!Array)\.from\(")

CONTRAST_KINDS = ("inherits", "self-proofs", "requires-chip", "none")

#: `budget` 词条的形状是 ``维度:值``，维度值集钉在这里（编译器按维度排序取数）。
#: "本原语要图" 归 requires 的 ``asset``，不在 budget 里重复一遍 —— 同 ``ground`` 那一删，
#: 两条机制表达同一件事时必有一条会烂掉。
BUDGET_DIMENSIONS = ("paint", "frames", "dom", "motion")

#: 法则 16 的判据（P1-3e 实测的缺陷形状）：引擎写变量时对**有元素子节点**的容器
#: 走 append 支路 —— `hyperframe-runtime.js:350` 的 `_1(e,t)` 只在
#: `childElementCount===0` 时 `textContent=t`，否则往第一个 TEXT_NODE 写、
#: 没有就 `insertBefore(createTextNode…)`，**不动已有元素子节点** ⇒ 文字两遍。
VAR_TEXT_TAG_RE = re.compile(
    r'<(?P<tag>[a-zA-Z][a-zA-Z0-9]*)\b(?P<attrs>[^>]*\bdata-var-text="[^"]*"[^>]*)>'
    r'(?P<inner>.*?)</(?P=tag)>',
    re.DOTALL)
ELEMENT_CHILD_RE = re.compile(r"<[a-zA-Z]")
#: 同一片段自己声明"脚本是唯一写入者"的合法写法。
VAR_TEXT_RELEASE_RE = re.compile(r"""removeAttribute\(\s*['"]data-var-text['"]\s*\)""")


def var_text_shape_violations(fragment: Fragment) -> list:
    """带 ``data-var-text`` 的容器不得有元素子节点（法则 16）。

    豁免条件只认同一 fragment 的脚本里摘掉属性：静态标记留在 HTML（色板/契约闸要读），
    运行时摘掉，引擎就不会碰这个容器。
    """
    problems: list = []
    released = bool(VAR_TEXT_RELEASE_RE.search(fragment.js))
    for match in VAR_TEXT_TAG_RE.finditer(fragment.html):
        if ELEMENT_CHILD_RE.search(match.group("inner")) and not released:
            problems.append(
                f"{fragment.primitive}: data-var-text 容器里有元素子节点"
                f"（{match.group('inner').strip()[:40]!r}），且脚本没摘属性 —— "
                "引擎会走 append 支路把整串另塞一个文本节点，文字渲染两遍"
                "（hyperframe-runtime.js:350 `_1`，法则 16）。"
                "要么容器留空，要么在 pre_js 里 removeAttribute(\"data-var-text\")")
    return problems


def fragment_violations(fragment: Fragment) -> list:
    """单个 Fragment 的法则自检 —— 编译器写盘前跑，测试跑同一份，不另立口径。"""
    problems: list = []
    js = fragment.js
    for token in FORBIDDEN_JS:
        if token in js:
            problems.append(f"{fragment.primitive}: 出现禁用写法 {token!r}（法则 10 / D3）")
    for tween in fragment.tweens:
        head, _, rest = tween.partition("}")
        if fragment.face and "opacity" in rest:
            problems.append(f"{fragment.primitive}: 自带 background 的面用 opacity 入场（法则 8）"
                            f" —— {head[:40]}…")
        if ".to(" in tween and "driftDur" not in tween:
            problems.append(f"{fragment.primitive}: to() 的时长没挂在 driftDur 上，"
                            "写死数字或只给 driftStart 都会与时长脱钩（seek 回退失步，D3）")
    if GAP_FROM_RE.search(js):
        problems.append(f"{fragment.primitive}: 出现 GSAP .from( 写法（D3 死因：seek 回退失步）"
                        " —— 一律 fromTo")
    for match in JS_DECL_NAME_RE.finditer(js):
        if not JS_IDENT_RE.match(match.group(1)):
            problems.append(
                f"{fragment.primitive}: 声明了非法 JS 标识符 {match.group(1)!r} —— "
                "由 ident 派生的局部名必须走 `js_name()`：ident 是 kebab，直接拼进 "
                "`const ew-hk-topChars = …` 会让整段脚本被判 "
                "invalid_inline_script_syntax（error 级，一处坏、全版式死）")
    if "transform:" in fragment.css and fragment.tweens:
        problems.append(f"{fragment.primitive}: CSS 写了 transform 又被补间（法则 7）；"
                        "transform-origin 是安全的，起始值交给 fromTo 的 from 侧")
    problems.extend(var_text_shape_violations(fragment))
    return problems


def check_preconditions(name: str, *, ground: str = "any",
                        accent_roles: tuple = (), image_gate_ready: bool = False) -> list:
    """编译器取原语前的前置条件检查（§6.2："声明前置条件而非只有参数"）。

    ``requires`` 里的每个名字都必须落到三条路之一：本函数能判（``CHECKED_REQUIRES``）、
    别处的闸强制（``CALLSITE_REQUIRES``），否则**报问题**。没有这条兜底，"前置条件"就会
    长成第二个 frame.md 色值表那种东西 —— 写着，但没人核。

    ``image_gate_ready`` 的**来源**是 `image_gate.capability_ok()`（P3 §4：不是硬编码，
    是运行时能力判定）。cv2 装不上或 cascade 缺失 → 门保持关，photo-* 一律拒编。
    """
    prim = PRIMITIVES.get(name)
    if prim is None:
        return [f"原语 {name!r} 不在 P0 清单里（可用: {', '.join(P0_NAMES)}）"]
    problems: list = []
    for require in prim.requires:
        if require == "image-gate-ready" and not image_gate_ready:
            problems.append(f"{name}: 图片门禁（P3）未接入，产线现在不放图进版式")
        elif require == "solid-ground" and ground not in SOLID_GROUNDS:
            problems.append(f"{name}: 要实色地面（{list(SOLID_GROUNDS)}），读到 {ground!r} —— "
                            "形状坐在照片/纹理上时边缘对比不可算")
        elif require == "accent-allows-large-text" and "shape-or-large-text" not in accent_roles:
            problems.append(f"{name}: 强调色 role 全是 shape-only，不能坐在字上（L1 的泛化）")
        elif require not in CHECKED_REQUIRES and require not in CALLSITE_REQUIRES:
            problems.append(f"{name}: 前置条件 {require!r} 没有任何实现 —— "
                            "要么在检查器里判，要么进 CALLSITE_REQUIRES 点名强制它的闸")
    return problems
