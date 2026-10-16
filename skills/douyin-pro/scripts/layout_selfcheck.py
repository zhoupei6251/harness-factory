"""Path B 版式自检 —— 在 hyperframes check / render 之前拦住发射器看不见的结构缺陷。

（对每个 pack 通用: 参数就是含 ``compositions/*.html`` 的版式目录, 现已覆盖
news-coral 与 news-policy —— 规则本身不认包名, 只认契约与不变量。）

为什么要这个脚本（每条不变量都对应一次真实事故，不是想象中的规则）：

1. MISSING_TWEEN_TARGET —— ``rail.html`` 的 ``.rl-head`` 容器漏写 ``id``，而时间轴里写的是
   ``tl.to("#rl-head", ...)``。GSAP 把解析成空数组的目标打成 console 警告
   （``GSAP target  not found.``，两个空格 = 空目标），``--strict`` 因此不过；
   更糟的是"表头不再呼吸"这件事在静态截图里完全看不出来。
2. SURFACE_OPACITY_TWEEN —— ``check --json`` 实测：白底眉标片 ``#h-eb`` 在 α≈0.72 时
   有效底色被合成成 ``rgb(246,213,213)``，珊瑚字对比掉到 2.5:1（要求 3:1）判为
   ``contrast_aa_failure``。审计器**前景色取原值、自身背景按 alpha 与地面混色**，
   所以带 ``background`` 的元素一律禁止 opacity 补间（纯文字淡入不受影响，实测通过）。
   取样网格还会随片长漂移（18s → [1,5,9,13,17]；9s → [0.5,2.5,…]），
   因此不能靠"淡入赶在取样点之前结束"，只能从构造上禁掉。

其余不变量来自 frame.md 与 sub-composition 契约（引擎只克隆 ``<template>`` 内容、
宿主 ``data-composition-id`` == 子合成根 id == ``window.__timelines`` 键名）。

用法::

    python layout_selfcheck.py <版式目录> [<版式目录> ...] [--quiet]

返回码：0 = 全部版式通过；1 = 有违规（逐条打印 文件:规则:说明），**或**某个显式传入的目录
里一个版式文件都没有 —— 那是用法错误（把 pack 名当成目录传了），不许算成"通过"。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- 常量（禁止魔法值）

#: 竖屏 9:16 基准下 frame.md 法则 1 规定的底部字幕禁入区（cqh 单位，1920px → 384px）。
#: 20 这个数是量出来的，不是定的：烧录字幕块底固定在 h−MarginV=1748、行距=字号=60px，
#: 三行字幕的顶边实测在 1568px（81.7cqh，t001-v2 final.mp4 逐行像素扫描），
#: 旧值 16cqh(1613px) 直接压在它下面 —— 发射器同时把每条字幕封顶两行。
CAPTION_RESERVE_CQH = 20.0

#: 每个版式都必须声明的镜头时长变量名（动量预算依赖它）
SLOT_VARIABLE = "slotSeconds"

#: 编译包（path_c）的字幕收进 HyperFrames 后，发射器每镜生成一个 ``subtitle-<i>.html``
#: 子合成挂在 2 轨。**文件名词干**是唯一识别口径（发射器 `path_b_build.SUBTITLE_FILE_PREFIX`
#: 用同一个串拼文件名，两处分家 = 字幕文件被当成普通版式、动量/禁入区两条误判红）。
#: 字幕子合成天然不守两条版式不变量：① 动量预算（字幕是文字层，不做整段位移呼吸）；
#: ② 底部字幕禁入区（字幕**就住在**那条带里，那 20cqh 本就是给它留的）。其余不变量全核。
SUBTITLE_FILE_STEM = "subtitle"

#: P3 §6 示意标注子合成挂在 3 轨（比字幕更高，压在所有元素上）。它与字幕同属**底部静态文字叠加层**：
#: 不做整段位移呼吸、住在画面下缘，因此同样豁免①动量预算、②底部禁入区两条不变量（它按
#: ``CAPTION_RESERVE+1cqh`` 落位，本就贴在禁入区上沿，不该被当成侵入）。发射器
#: `path_b_build.SCHEMATIC_FILE_PREFIX` 用同一个串拼文件名 —— 两处分家 = 标注文件被当普通版式误判红。
SCHEMATIC_FILE_STEM = "schematic"

#: 动量预算必须写成具名常数，不许把数字直接塞进 Math.min/Math.max
BUDGET_CONSTANTS = ("INTRO_END", "MIN_DRIFT")

#: 引擎自带的拉丁显示族：写 local() 会让自动下载失效，必须留裸族名
CANONICAL_LATIN_FAMILIES = ("League Gothic", "JetBrains Mono", "Inter")

#: 中文族：字体审计按文件走，每个版式必须自带其中之一的 @font-face。
#: **必须精确族名匹配** —— 旧判定 `CJK_FAMILY in block` 是子串，而
#: `"HF CJK" in "HF CJK Serif"` 为 True（2026-10-09 P0 实测），自造前缀式族名会被静默放行。
#: `HF Serif CJK` 是 news-policy 5 个版式已在用的宋体（裁决 7 的杂志族要它，不能打进红区）。
CJK_FAMILY = "HF CJK"
CJK_FAMILIES = (CJK_FAMILY, "HF Serif CJK")

#: 本机确证在装的中文 `local()` 名。口径: 2026-10-09 用 System.Drawing.InstalledFontCollection
#: 点了 16 个候选名，只有这 5 个命中（`NotoSansSC-VF`/`Source Han Sans SC`/`Noto Sans CJK SC`/
#: `PingFang SC`/`Source Han Serif SC`/`Songti SC`/`思源宋体` 等全部 absent）。
#: 规则只能是"**至少一个**候选在装"，不能要求全装 —— 存量 face 的候选名里本来就混着没装的。
CJK_INSTALLED_LOCALS = ("Noto Sans SC", "Microsoft YaHei", "Noto Serif SC", "SimSun", "DengXian")

#: CSS `font-family` 列表尾部的通用关键字，不是具体族名，不参与声明核对
GENERIC_FAMILY_KEYWORDS = ("sans-serif", "serif", "monospace", "cursive", "fantasy", "system-ui")

#: 允许出现 px 的属性（纹理渐变里的 20px/40px 是合法的装饰尺度，不参与排版）
PX_ALLOWED_PROPS = ("background", "background-image", "background-color", "mask-image")

#: 必须用容器单位的排版属性
PX_FORBIDDEN_PROPS = (
    "font-size",
    "line-height",
    "letter-spacing",
    "padding",
    "margin",
    "inset",
    "top",
    "right",
    "bottom",
    "left",
    "width",
    "height",
    "gap",
    "border-top",
    "border-bottom",
    "border-left",
    "border-right",
)

#: 补间调用（tl./gsap. 前缀），第 1 个参数是目标选择器
TWEEN_CALL_RE = re.compile(r"(?:tl|gsap|_this|master)\.(fromTo|from|to|set|fromTo)\s*\(")
#: 元素标签上的 id / class
TAG_ID_RE = re.compile(r"\bid=\"([A-Za-z0-9_-]+)\"")
TAG_CLASS_RE = re.compile(r"\bclass=\"([^\"]*)\"")
#: CSS 规则块
CSS_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)
#: CSS 注释
CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
#: 子合成契约：根元素上的合成 id 与注册的 timeline 键
ROOT_COMP_ID_RE = re.compile(r"<div[^>]*id=\"root\"[^>]*data-composition-id=\"([^\"]+)\"")
TIMELINE_KEY_RE = re.compile(r"window\.__timelines\[\"([^\"]+)\"\]")
FONT_FACE_BLOCK_RE = re.compile(r"@font-face\s*\{[^}]*\}", re.S)
#: @font-face 块里的族名（引号内精确值）
FONT_FACE_FAMILY_RE = re.compile(r"font-family\s*:\s*\"([^\"]+)\"")
#: @font-face 块里的本机字体名
LOCAL_NAME_RE = re.compile(r"local\(\s*\"([^\"]+)\"\s*\)")
#: CSS 里的 font-family 声明值（整串，再按逗号拆）
FONT_FAMILY_DECL_RE = re.compile(r"font-family\s*:\s*([^;}]+)")
TEMPLATE_BLOCK_RE = re.compile(r"<template>(.*)</template>", re.S)
STYLE_BLOCK_RE = re.compile(r"<style>(.*?)</style>", re.S)
SCRIPT_BLOCK_RE = re.compile(r"<script>(.*?)</script>", re.S)
CQH_VALUE_RE = re.compile(r"^(\d+(?:\.\d+)?)cqh$")
VAR_DECL_RE = re.compile(r"\{\"id\":\s*\"([A-Za-z0-9_]+)\"")

# ---------------------------------------------------------------- 数据结构


class Violation:
    """一条不变量违规：版式文件 + 规则码 + 人话说明。"""

    def __init__(self, file_name: str, code: str, detail: str) -> None:
        self.file_name = file_name
        self.code = code
        self.detail = detail

    def __str__(self) -> str:
        return f"{self.file_name}: {self.code} — {self.detail}"


# ---------------------------------------------------------------- 解析工具


def strip_css_comments(css: str) -> str:
    return CSS_COMMENT_RE.sub("", css)


def font_families_used(css: str) -> set[str]:
    """CSS 里**用到**的具体族名：先剔掉 `@font-face` 声明块，再拆逗号、去引号、丢通用关键字。"""
    used: set[str] = set()
    for value in FONT_FAMILY_DECL_RE.findall(FONT_FACE_BLOCK_RE.sub("", css)):
        for token in value.split(","):
            token = token.strip().strip("\"'").strip()
            if token and token.lower() not in GENERIC_FAMILY_KEYWORDS:
                used.add(token)
    return used


def declared_font_faces(css: str) -> dict[str, str]:
    """{族名: @font-face 块}，族名取自块内的精确值（同一个块声明多个族名时都收）。"""
    declared: dict[str, str] = {}
    for block in FONT_FACE_BLOCK_RE.findall(css):
        for name in FONT_FACE_FAMILY_RE.findall(block):
            declared[name] = block
    return declared


def parse_css_rules(css: str) -> list[tuple[str, dict[str, str]]]:
    """返回 [(选择器, {属性: 值})]，同一规则内重复属性以最后一条为准（CSS 语义一致）。"""
    rules: list[tuple[str, dict[str, str]]] = []
    for raw_selector, body in CSS_RULE_RE.findall(strip_css_comments(css)):
        selector = raw_selector.strip()
        if not selector or selector.startswith("@"):
            continue
        decls: dict[str, str] = {}
        for decl in body.split(";"):
            if ":" not in decl:
                continue
            prop, _, value = decl.partition(":")
            decls[prop.strip().lower()] = value.strip()
        rules.append((selector, decls))
    return rules


def split_call_args(text: str, open_paren: int) -> list[str]:
    """从 ``(`` 处按括号/引号深度切出实参列表（JS 里嵌套 {} 与函数调用都会带括号）。"""
    args: list[str] = []
    depth = 0
    quote = ""
    start = open_paren + 1
    for i in range(open_paren, len(text)):
        ch = text[i]
        if quote:
            if ch == quote:
                quote = ""
            continue
        if ch in "\"'":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                args.append(text[start:i])
                return args
        elif ch == "," and depth == 1:
            args.append(text[start:i])
            start = i + 1
    args.append(text[start:])
    return args


def unquote(token: str) -> str:
    token = token.strip()
    if len(token) >= 2 and token[0] in "\"'" and token[-1] == token[0]:
        return token[1:-1]
    return token


def enumerate_tweens(js: str) -> list[tuple[str, str, str]]:
    """产出 (方法, 目标选择器, 参与补间的变量文本)；变量文本合并 from/to 两侧以便查 opacity。"""
    out: list[tuple[str, str, str]] = []
    for match in TWEEN_CALL_RE.finditer(js):
        args = split_call_args(js, match.end() - 1)
        if not args:
            continue
        target = unquote(args[0])
        # fromTo 有 3+ 个参数（target, from, to, position），to/from/set 只有 2 个
        vars_text = " ".join(args[1:3]) if len(args) >= 3 else " ".join(args[1:2])
        out.append((match.group(1), target, vars_text))
    return out


def collect_elements(html_body: str) -> tuple[set[str], dict[str, str], dict[str, set[str]]]:
    """扫描标签：返回 (全部 id, id → class 集合, class → 是否存在于带 id 的元素)。"""
    ids: set[str] = set()
    id_classes: dict[str, set[str]] = {}
    classes: set[str] = set()
    for tag_attrs in re.findall(r"<[a-zA-Z][^>]*>", html_body):
        found_id = TAG_ID_RE.search(tag_attrs)
        found_class = TAG_CLASS_RE.search(tag_attrs)
        tag_classes = set(found_class.group(1).split()) if found_class else set()
        classes |= tag_classes
        if found_id:
            ids.add(found_id.group(1))
            id_classes[found_id.group(1)] = tag_classes
    return ids, id_classes, classes


def declarations_for_classes(classes: set[str], rules: list[tuple[str, dict[str, str]]]) -> dict[str, str]:
    """把元素 class 命中的所有规则的属性并到一起（后写覆盖前写，与 CSS 顺序一致的近似）。"""
    merged: dict[str, str] = {}
    for selector, decls in rules:
        for part in selector.split(","):
            part = part.strip()
            for cls in classes:
                if f".{cls}" in part:
                    merged.update(decls)
    return merged


def inset_bottom(value: str) -> str | None:
    """按 CSS ``inset`` 简写取下边界值（1~4 个值都支持）。"""
    parts = [p for p in value.split() if p]
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return parts[0]
    if len(parts) == 3:
        return parts[2]
    return parts[2]


def bottom_is_intruding(value: str) -> bool:
    """下边界落在 (0, CAPTION_RESERVE_CQH) 之间 = 文字挤进烧录字幕区；0/auto 是拉伸盒，允许。"""
    match = CQH_VALUE_RE.match(value)
    if not match:
        return False
    cqh = float(match.group(1))
    return 0.0 < cqh < CAPTION_RESERVE_CQH


# ---------------------------------------------------------------- 可共享的三条规则体
# 抽出来的唯一理由：Vue-only 版式没有 compositions/*.html，但它有 <style> 与 <script>，
# 这三条的判据对两种工件**是同一句话**。分两份实现 = 迟早一份漂（D13 的口径）。


def check_momentum_budget(fail, script_blocks: str) -> None:
    """规则 6：动量预算具名常数 + 至少一条用 driftDur 的持续位移。"""
    for constant in BUDGET_CONSTANTS:
        if not re.search(rf"\bconst\s+{constant}\s*=", script_blocks):
            fail("MAGIC_BUDGET_VALUE", f"动量预算常数 {constant} 必须具名声明")
    if "driftDur" not in script_blocks or not re.search(r"\bconst\s+driftDur\s*=", script_blocks):
        fail("MISSING_DRIFT_DURATION", "必须按 frame.md 预算算出 driftDur")
    drift_tweens = [t for t in enumerate_tweens(script_blocks) if "driftDur" in t[2]]
    if not drift_tweens:
        fail("MISSING_CONTINUOUS_MOTION", "没有任何补间使用 driftDur —— 该镜头尾段会冻住")


def check_font_rules(fail, style_blocks: str) -> None:
    """规则 8：中文 face 必备、用到的中文族必须本文件声明、声明的中文族必须有真落点。"""
    clean_styles = strip_css_comments(style_blocks)
    font_faces = FONT_FACE_BLOCK_RE.findall(clean_styles)
    declared = declared_font_faces(clean_styles)
    cjk_declared = [name for name in CJK_FAMILIES if name in declared]
    if not cjk_declared:
        fail(
            "MISSING_CJK_FONT_FACE",
            f'缺少中文 @font-face（允许的族名: {" / ".join(CJK_FAMILIES)}；审计按文件走）',
        )
    undeclared = (font_families_used(clean_styles) & set(CJK_FAMILIES)) - set(declared)
    for name in sorted(undeclared):
        fail(
            "CJK_FAMILY_USED_NOT_DECLARED",
            f'正文用了 font-family:"{name}" 但本文件没有它的 @font-face —— '
            "浏览器静默回落到系统默认字，字体降档不会有任何人报错",
        )
    for name in cjk_declared:
        candidates = LOCAL_NAME_RE.findall(declared[name])
        if not set(candidates) & set(CJK_INSTALLED_LOCALS):
            fail(
                "CJK_FONT_LOCAL_NOT_INSTALLED",
                f'{name} 的 local() 候选（{candidates}）在本机一个都没装'
                f"（在装口径: {list(CJK_INSTALLED_LOCALS)}）—— "
                "这条 @font-face 形同虚设，中文会回落",
            )
    for block in font_faces:
        for family in CANONICAL_LATIN_FAMILIES:
            if family in block and "local(" in block:
                fail(
                    "CANONICAL_FONT_LOCAL_OVERRIDE",
                    f"{family} 被写成 local() 会让引擎自动下载失效，只留裸族名",
                )


def check_px_typography(fail, rules: list[tuple[str, dict[str, str]]]) -> None:
    """规则 9：排版属性不许 px（纹理渐变例外）。"""
    for selector, decls in rules:
        for prop, value in decls.items():
            if prop in PX_ALLOWED_PROPS or not any(prop.startswith(p) for p in PX_FORBIDDEN_PROPS):
                continue
            if re.search(r"\d+(\.\d+)?px", value):
                fail("PX_TYPOGRAPHY", f"{selector} 的 {prop}:{value} 用了 px —— 换分辨率会崩版")


# ---------------------------------------------------------------- 单文件检查


def check_layout(path: Path) -> list[Violation]:
    file_name = path.name
    text = path.read_text(encoding="utf-8")
    violations: list[Violation] = []
    # 字幕 / P3 示意标注子合成只豁免两条对**底部静态文字叠加层**无意义的不变量（动量预算 /
    # 底部禁入区），见 SUBTITLE_FILE_STEM / SCHEMATIC_FILE_STEM。两条各自按前缀认，别混。
    is_bottom_overlay = file_name.startswith(
        (f"{SUBTITLE_FILE_STEM}-", f"{SCHEMATIC_FILE_STEM}-"))

    def fail(code: str, detail: str) -> None:
        violations.append(Violation(file_name, code, detail))

    template_match = TEMPLATE_BLOCK_RE.search(text)
    if not template_match:
        fail("NO_TEMPLATE", "版式必须把 style/script/根节点包在 <template> 里（引擎只克隆模板内容）")
        return violations
    template_html = template_match.group(1)

    head_region = text[: template_match.start()]
    style_blocks = "".join(STYLE_BLOCK_RE.findall(template_html))
    script_blocks = "".join(SCRIPT_BLOCK_RE.findall(template_html))
    rules = parse_css_rules(style_blocks)
    ids, id_classes, classes = collect_elements(template_html)
    style_blocks = "".join(STYLE_BLOCK_RE.findall(template_html))
    script_blocks = "".join(SCRIPT_BLOCK_RE.findall(template_html))
    rules = parse_css_rules(style_blocks)
    ids, id_classes, classes = collect_elements(template_html)

    # 1) 契约：内容必须在模板里，<head> 会被引擎丢弃
    for block in re.finditer(r"<(style|script)\b", head_region):
        fail(
            "CONTENT_OUTSIDE_TEMPLATE",
            f"<{block.group(1)}> 出现在 <template> 之外，运行时会被丢弃",
        )

    # 2) 子合成契约：根 data-composition-id 必须等于注册的 timeline 键
    root_ids = ROOT_COMP_ID_RE.findall(template_html)
    timeline_keys = TIMELINE_KEY_RE.findall(script_blocks)
    if not root_ids:
        fail("NO_ROOT_COMPOSITION_ID", '根节点缺少 <div id="root" data-composition-id="…">')
    if not timeline_keys:
        fail("NO_TIMELINE_REGISTER", '脚本必须写 window.__timelines["<id>"] = tl')
    if root_ids and timeline_keys and set(root_ids) != set(timeline_keys):
        fail(
            "CONTRACT_ID_MISMATCH",
            f"根合成 id {sorted(set(root_ids))} 与 timeline 键 {sorted(set(timeline_keys))} 不一致",
        )

    # 3) 变量契约：slotSeconds 决定动量预算
    declared_vars = set(VAR_DECL_RE.findall(text))
    if SLOT_VARIABLE not in declared_vars:
        fail("MISSING_SLOT_VARIABLE", f"data-composition-variables 必须声明 {SLOT_VARIABLE}")

    # 4) 补间目标必须能在本文件解析到元素
    for method, target, _ in enumerate_tweens(script_blocks):
        if target.startswith("#"):
            if target[1:] not in ids:
                fail("MISSING_TWEEN_TARGET", f'{method}("{target}") 找不到同文件的 id（GSAP 会打空目标警告）')
        elif target.startswith("."):
            if target[1:] not in classes:
                fail("MISSING_TWEEN_TARGET", f'{method}("{target}") 找不到同文件的 class')

    # 5) 自带 background 的面禁止 opacity 补间
    for method, target, vars_text in enumerate_tweens(script_blocks):
        if "opacity" not in vars_text:
            continue
        if target.startswith("#"):
            element_classes = id_classes.get(target[1:], set())
        elif target.startswith("."):
            element_classes = {target[1:]}
        else:
            continue
        decls = declarations_for_classes(element_classes, rules)
        if "background" in decls or "background-color" in decls:
            fail(
                "SURFACE_OPACITY_TWEEN",
                f'{method}("{target}") 用了 opacity，但该元素自带 background'
                f"（{decls.get('background') or decls.get('background-color')}）—— "
                "半透明会与地面混色导致对比不过，改用 scaleX/scaleY 擦入",
            )

    # 6) 动量预算：具名常数 + 至少一条用 driftDur 的持续位移
    #    （字幕 / 示意标注子合成豁免：静态文字层不做整段位移呼吸，见 SUBTITLE/SCHEMATIC_FILE_STEM）
    if not is_bottom_overlay:
        check_momentum_budget(fail, script_blocks)

    # 7) 底部字幕禁入区（字幕/示意标注子合成豁免：那 20cqh 本就是底部叠加层的家，见两 STEM 常量）
    if not is_bottom_overlay:
        for selector, decls in rules:
            if "bottom" in decls and bottom_is_intruding(decls["bottom"]):
                fail("CAPTION_RESERVE_INTRUDED", f"{selector} 的 bottom:{decls['bottom']} 侵入 {CAPTION_RESERVE_CQH}cqh 字幕区")
            if "inset" in decls:
                bottom_value = inset_bottom(decls["inset"])
                if bottom_value and bottom_is_intruding(bottom_value):
                    fail("CAPTION_RESERVE_INTRUDED", f"{selector} 的 inset 下边界 {bottom_value} 侵入字幕区")

    # 8) 字体：中文 face 必备、用到的中文族必须本文件声明、声明的中文族必须有真落点
    check_font_rules(fail, style_blocks)

    # 9) 排版禁止 px（纹理渐变例外）
    check_px_typography(fail, rules)

    return violations


SFC_STYLE_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.S)
SFC_SCRIPT_RE = re.compile(r"<script[^>]*>(.*?)</script>", re.S)
SFC_TEMPLATE_RE = re.compile(r"<template[^>]*>(.*?)</template>", re.S)
#: 组件里补间目标的写法：`chipEl.value!` / `chipEl.value`
REF_TARGET_RE = re.compile(r"^([A-Za-z0-9_]+)\.value!?$")


def check_component(path: Path) -> list[Violation]:
    """Vue-only 版式的结构不变量面 —— **跑的是 `check_layout` 同一批谓词，不重写**。

    静态支的工件是 `compositions/*.html`，组件支的工件是 SFC：`<style>` 与 `<script>`
    都是原生 CSS / JS，所以动量预算、字体、px、法则 8 这四组判据对两者是同一句话。
    分两份实现迟早一份漂（D13 的口径），因此这里只换**取文本的口子**和**目标解析**，
    谓词一律调 `check_*` 那几个函数。

    两处刻意不同，都是组件形态决定的：
    - 补间目标不是 `"#id"` / `".class"` 而是 `xEl.value!` —— 选择器字符串在组件里是
      被禁的（跨镜串目标），所以这里把 ref 解析成同标签的 class 再走同一个
      `declarations_for_classes`；出现选择器反而要红。
    - 规则 7（字幕禁入区）**不在这里跑**：它读 CSS 的 `bottom:`/`inset:`，成立前提是
      偏移相对满幅 `#root`，而组件的偏移相对内层 stage（`.fd-place{bottom:6cqh}` 在
      `.fd-stage{inset:0 0 36cqh 0}` 里，实际 42cqh）⇒ 文本口径会假红。
      那条只能按像素几何口径做，见 `VUE_GUARDS`。
    """
    violations: list[Violation] = []

    def fail(code: str, detail: str) -> None:
        violations.append(Violation(path.name, code, detail))

    text = path.read_text(encoding="utf-8")
    style_blocks = "".join(SFC_STYLE_RE.findall(text))
    script_blocks = "".join(SFC_SCRIPT_RE.findall(text))
    template = "".join(SFC_TEMPLATE_RE.findall(text))
    if not template:
        fail("NO_TEMPLATE", "SFC 没有 <template> 块")
        return violations
    rules = parse_css_rules(style_blocks)

    refs: dict[str, set[str]] = {}
    for tag in re.findall(r"<[a-zA-Z][^>]*>", template):
        ref = re.search(r'\bref="([A-Za-z0-9_]+)"', tag)
        if not ref:
            continue
        cls = re.search(r'\bclass="([^"]*)"', tag)
        refs[ref.group(1)] = set(cls.group(1).split()) if cls else set()

    # 4) 补间目标必须解析得到本组件的 ref（GSAP 打空目标只会 WARN，不会停）
    for method, target, vars_text in enumerate_tweens(script_blocks):
        resolved = REF_TARGET_RE.match(target.strip())
        if target.startswith(("#", ".")):
            fail("MISSING_TWEEN_TARGET",
                 f'{method}("{target}") 用选择器找节点 —— 组件只准拿自己的 ref（跨镜串目标）')
            continue
        if not resolved:
            continue                      # 数字/字符串常量等形态不是本条的口径
        if resolved.group(1) not in refs:
            fail("MISSING_TWEEN_TARGET",
                 f"{method}({target}) 的 ref {resolved.group(1)!r} 在模板里没有对应标签")
            continue
        # 5) 法则 8：自带 background 的面禁止 opacity 补间
        if "opacity" in vars_text:
            decls = declarations_for_classes(refs[resolved.group(1)], rules)
            if "background" in decls or "background-color" in decls:
                fail("SURFACE_OPACITY_TWEEN",
                     f'{method}({target}) 用了 opacity，但该元素自带 background'
                     f"（{decls.get('background') or decls.get('background-color')}）—— "
                     "半透明会与地面混色导致对比不过，改用 scaleX/scaleY 擦入")

    check_momentum_budget(fail, script_blocks)
    check_font_rules(fail, style_blocks)
    check_px_typography(fail, rules)
    return violations


#: 17 条不变量在 **Vue 支**由谁守。这张表的存在理由：新角色没有静态文件，
#: 结构闸天然扫不到它 —— 没有登记，就没人知道哪几条是"换了地方守"、哪几条是"没人守"。
#: 状态只有四种，且由 `t_vue_branch_guard_registry_is_complete` 机检：
#:   reused  同一份谓词直接跑在组件工件上（`check_component`）
#:   moved   这条规则的字面前提在组件形态不成立，但它保护的**性质**由点名站点守
#:   unwired 谓词可复用、今天没跑 = 洞（note 必须点名收口的 Task）
#:   none    今天没有任何东西守 = 洞（note 必须点名收口的 Task）
#: 站点写法：`selftest:<t_函数名>` / `vue-build:<check 名子串>` / `contracts:<函数名>` /
#: `component:check_component` / `census:<判据>`。
VUE_GUARDS: dict[str, dict[str, str]] = {
    "NO_TEMPLATE": {
        "state": "reused", "site": "component:check_component",
        "note": "同一条 code 由 check_component 发。对 SFC 它近乎恒真（没有 <template> 先编译失败），"
                "登记成 reused 而不是 moved，是为了让「谁发的这条」在表里只有一个答案。"},
    "CONTENT_OUTSIDE_TEMPLATE": {
        "state": "moved", "site": "vue-build:编译出 dist/vue/assets",
        "note": "组件样式不会「掉进 head」，但它的对应风险是样式没编译出资产或没发 <link>，"
                "由 vue-build 那条 + selftest:t_emit_host_links_vue_css_before_runtime 守。"},
    "NO_ROOT_COMPOSITION_ID": {
        "state": "moved", "site": "selftest:t_vue_only_contract_is_the_registry_for_its_role",
        "note": "组件没有 <div id=\"root\" data-composition-id>：id 挂在发射器写的 clip 上，"
                "取值由 contract.toml 供（那条闸逐字段比契约→条目）。"},
    "NO_TIMELINE_REGISTER": {
        "state": "unwired", "site": "vue-build:时间轴注册键不写死",
        "note": "今天那条 TS 闸只查「键不是字面量」，组件**一条都不注册**时它是绿的 —— "
                "缺「注册必须存在」这一半。收口：Task 5 在 vue-build 里补一条正向断言。"},
    "CONTRACT_ID_MISMATCH": {
        "state": "moved", "site": "vue-build:composition 身份不写死",
        "note": "子合成「根 id == timeline 键」在组件里由同一个变量保证：注册键 = 传入的 "
                "compositionId = clip 的 data-composition-id。写死字面量即红（含反向："
                "selftest:t_two_same_role_vue_mounts_have_unique_targets 守唯一化）。"},
    "MISSING_SLOT_VARIABLE": {
        "state": "moved", "site": "contracts:validate_contract",
        "note": "静态支从 HTML 的 data-composition-variables 里找 slotSeconds；组件支的"
                "变量表在 contract.toml，由 validate_contract 要求同一格存在（动量预算依赖它）。"},
    "MISSING_TWEEN_TARGET": {
        "state": "reused", "site": "component:check_component",
        "note": "目标口径换成 ref：解析不到对应标签就红；用选择器也红（组件禁跨镜串目标）。"},
    "SURFACE_OPACITY_TWEEN": {
        "state": "reused", "site": "component:check_component",
        "note": "ref → 同标签 class → declarations_for_classes → background 判定，"
                "与静态支共用同一个谓词函数。"},
    "MAGIC_BUDGET_VALUE": {"state": "reused", "site": "component:check_component",
                           "note": "跑 SFC 的 <script> 块。口径两分支一样弱：只查具名常数**声明了**，"
                                   "不查它有没有被用（`Math.max(0.6, …)` 绕过 MIN_DRIFT 这里不红）—— "
                                   "要收紧就两边一起收，别只收组件支。"},
    "MISSING_DRIFT_DURATION": {"state": "reused", "site": "component:check_component",
                               "note": "同上。"},
    "MISSING_CONTINUOUS_MOTION": {"state": "reused", "site": "component:check_component",
                                  "note": "enumerate_tweens 对 ref 目标同样产出变量文本，"
                                          "所以 driftDur 出现与否的判据不用改。"},
    "CAPTION_RESERVE_INTRUDED": {
        "state": "none", "site": "none",
        "note": "文本口径对组件会**假红**（偏移相对内层 stage 不是 #root），而引擎的 "
                "--caption-zone 已用活体负例证明不是侵入探测器（地点行渲到 85.6cqh，"
                "check --strict 仍 0 finding，见 evidence/2026-10-16-task5-precheck-findings.md）。"
                "只能按像素几何口径做。收口：Task 5 的普查层像素闸。"},
    "MISSING_CJK_FONT_FACE": {"state": "reused", "site": "component:check_component",
                              "note": "接线时 field-a 真的缺这份 face（混挂时被 hook-a 的"
                                      "「全局 @font-face」遮住了）—— 这条不是假想洞。"},
    "CJK_FAMILY_USED_NOT_DECLARED": {"state": "reused", "site": "component:check_component",
                                     "note": "跑 <style> 原文；Vite 只做压缩不改族名。"},
    "CJK_FONT_LOCAL_NOT_INSTALLED": {"state": "reused", "site": "component:check_component",
                                     "note": "同一份在装口径（本机点测的 5 个名字）。"},
    "CANONICAL_FONT_LOCAL_OVERRIDE": {"state": "reused", "site": "component:check_component",
                                      "note": "同上。"},
    "PX_TYPOGRAPHY": {"state": "reused", "site": "component:check_component",
                      "note": "跑 <style> 原文。⚠ 口径差异要认：Vite 会把 `inset:0 0 36cqh 0`"
                              "展成四条 top/right/bottom/left —— 所以 px 判定用源文更安全，"
                              "而 bottom 类判定（规则 7）用源文反而更不安全。"},
}


def discover_layouts(directory: Path) -> list[Path]:
    compositions = directory / "compositions"
    search_root = compositions if compositions.is_dir() else directory
    return sorted(p for p in search_root.glob("*.html") if p.name != "host.html")


# ---------------------------------------------------------------- CLI


def vue_guard_table() -> str:
    """把 `VUE_GUARDS` 打成 markdown —— 表由数据现生成，抄一份就会和实现分家。"""
    header = ("| 不变量 | 状态 | 站点 | 说明 |\n|---|---|---|---|")
    rows = [f"| `{code}` | {row['state']} | `{row['site']}` | {row['note']} |"
            for code, row in sorted(VUE_GUARDS.items())]
    counts = {s: sum(1 for r in VUE_GUARDS.values() if r["state"] == s)
              for s in ("reused", "moved", "unwired", "none")}
    holes = sorted(c for c, r in VUE_GUARDS.items() if r["state"] in ("unwired", "none"))
    return "\n".join([
        header, *rows, "",
        f"合计 {len(VUE_GUARDS)} 条：reused {counts['reused']} · moved {counts['moved']} · "
        f"洞 {counts['unwired'] + counts['none']}（{', '.join(holes)}）",
    ])


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):  # Windows 控制台默认 cp936，中文说明会变问号
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Path B 版式结构自检（逐 pack 目录跑）")
    parser.add_argument("directories", nargs="*", type=Path, help="含 compositions/*.html 的版式目录")
    parser.add_argument("--quiet", action="store_true", help="只在有违规或用法错误时输出")
    parser.add_argument("--vue-guards", action="store_true",
                        help="打印 17 条不变量在 Vue 支的守卫登记表（markdown），不跑检查")
    args = parser.parse_args(argv)
    if args.vue_guards:
        print(vue_guard_table())
        return 0
    if not args.directories:
        print("版式自检：一个目录都没给 —— 不算检查，也不算通过。"
              "参数要写含 compositions/*.html 的目录（或改用 --vue-guards 打登记表）。")
        return 1

    total_files = 0
    all_violations: list[Violation] = []
    empty_dirs: list[str] = []
    for directory in args.directories:
        layouts = discover_layouts(directory)
        if not layouts:
            print(f"{directory}: 没找到版式文件")
            empty_dirs.append(str(directory))
            continue
        for layout in layouts:
            total_files += 1
            all_violations.extend(check_layout(layout))

    if all_violations:
        for violation in all_violations:
            print(str(violation))
        print(f"\n版式自检不过：{total_files} 个文件里 {len(all_violations)} 条违规")
        return 1
    # 空过比违规更危险：一次打错参数的运行看起来是绿的，实际一条不变量都没查。
    # 闸门（硬规则 6）要的是"查过了"，不是"没报错"，所以这里必须非零退出。
    if empty_dirs:
        print(
            f"\n版式自检不过：显式传入的 {len(empty_dirs)} 个目录里没有任何版式文件"
            f"（{'、'.join(empty_dirs)}）—— 参数要写含 compositions/*.html 的**目录**"
            "（如 skills/douyin-pro/templates/hyperframes_path_b/news-coral），"
            "只写 pack 名不算检查，也不算通过。"
        )
        return 1
    if not args.quiet:
        print(f"版式自检通过：{total_files} 个文件，0 条违规")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
