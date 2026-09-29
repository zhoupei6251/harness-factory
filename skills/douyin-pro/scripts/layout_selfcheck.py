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

#: 动量预算必须写成具名常数，不许把数字直接塞进 Math.min/Math.max
BUDGET_CONSTANTS = ("INTRO_END", "MIN_DRIFT")

#: 引擎自带的拉丁显示族：写 local() 会让自动下载失效，必须留裸族名
CANONICAL_LATIN_FAMILIES = ("League Gothic", "JetBrains Mono", "Inter")

#: 中文族：字体审计按文件走，每个版式必须自带这条 @font-face
CJK_FAMILY = "HF CJK"

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


# ---------------------------------------------------------------- 单文件检查


def check_layout(path: Path) -> list[Violation]:
    file_name = path.name
    text = path.read_text(encoding="utf-8")
    violations: list[Violation] = []

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
    for constant in BUDGET_CONSTANTS:
        if not re.search(rf"\bconst\s+{constant}\s*=", script_blocks):
            fail("MAGIC_BUDGET_VALUE", f"动量预算常数 {constant} 必须具名声明")
    if "driftDur" not in script_blocks or not re.search(r"\bconst\s+driftDur\s*=", script_blocks):
        fail("MISSING_DRIFT_DURATION", "必须按 frame.md 预算算出 driftDur")
    drift_tweens = [t for t in enumerate_tweens(script_blocks) if "driftDur" in t[2]]
    if not drift_tweens:
        fail("MISSING_CONTINUOUS_MOTION", "没有任何补间使用 driftDur —— 该镜头尾段会冻住")

    # 7) 底部字幕禁入区
    for selector, decls in rules:
        if "bottom" in decls and bottom_is_intruding(decls["bottom"]):
            fail("CAPTION_RESERVE_INTRUDED", f"{selector} 的 bottom:{decls['bottom']} 侵入 {CAPTION_RESERVE_CQH}cqh 字幕区")
        if "inset" in decls:
            bottom_value = inset_bottom(decls["inset"])
            if bottom_value and bottom_is_intruding(bottom_value):
                fail("CAPTION_RESERVE_INTRUDED", f"{selector} 的 inset 下边界 {bottom_value} 侵入字幕区")

    # 8) 字体：中文 @font-face 必备，拉丁族禁止 local() 覆盖
    font_faces = FONT_FACE_BLOCK_RE.findall(strip_css_comments(style_blocks))
    has_cjk_face = any(CJK_FAMILY in block for block in font_faces)
    if not has_cjk_face:
        fail("MISSING_CJK_FONT_FACE", f'缺少 @font-face {{ font-family: "{CJK_FAMILY}" }}（审计按文件走）')
    for block in font_faces:
        for family in CANONICAL_LATIN_FAMILIES:
            if family in block and "local(" in block:
                fail(
                    "CANONICAL_FONT_LOCAL_OVERRIDE",
                    f"{family} 被写成 local() 会让引擎自动下载失效，只留裸族名",
                )

    # 9) 排版禁止 px（纹理渐变例外）
    for selector, decls in rules:
        for prop, value in decls.items():
            if prop in PX_ALLOWED_PROPS or not any(prop.startswith(p) for p in PX_FORBIDDEN_PROPS):
                continue
            if re.search(r"\d+(\.\d+)?px", value):
                fail("PX_TYPOGRAPHY", f"{selector} 的 {prop}:{value} 用了 px —— 换分辨率会崩版")

    return violations


def discover_layouts(directory: Path) -> list[Path]:
    compositions = directory / "compositions"
    search_root = compositions if compositions.is_dir() else directory
    return sorted(p for p in search_root.glob("*.html") if p.name != "host.html")


# ---------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):  # Windows 控制台默认 cp936，中文说明会变问号
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Path B 版式结构自检（逐 pack 目录跑）")
    parser.add_argument("directories", nargs="+", type=Path, help="含 compositions/*.html 的版式目录")
    parser.add_argument("--quiet", action="store_true", help="只在有违规或用法错误时输出")
    args = parser.parse_args(argv)

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
