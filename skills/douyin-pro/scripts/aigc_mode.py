#!/usr/bin/env python3
"""AIGC 标识开关的**默认姿态**读法 —— 姿态在文件里, 判据在代码里。

为什么要有这个文件: 用户 2026-09-29 要「先把两开关关了」。合规默认值(三件全开)
不该由一次会话的偏好改进代码(ARCHITECTURE D11), 所以代码默认永远是 `full / required`,
"现在想关"落到一份**受版本管理**的姿态文件 `routes/news/aigc-mode.json`:

    {"render": "full" | "no-badge" | "draft", "declaration": "undeclared" | "required", ...}

关掉的这件事因此有路径、有日期、有 `revert` 一行, 能 diff、能在 MEMORY 里点名,
而不是散在两个脚本的默认值里。文件不存在 = 全开(合规基线), 删掉文件就是恢复默认。

**渲染层从两档变三档**(2026-09-29 用户点头放宽判据, 见 ARCHITECTURE D14): 原先 `draft`
一次关掉 ① 角标与 ② 元数据两件, 于是"不要角标"只能得到一份**发不出去**的草稿。现在
① 可以单独关、② 不许关:

    full      ① + ②   交付轨(原样), 三件里只欠 ③ 时仍可按姿态留痕放行
    no-badge  只有 ②  **交付轨**: 产物可发布, 但 ③ 必带 —— ① 关了、② 过抖音转码即失,
                      ③ 是唯一活到平台侧的那一件, 所以这一档买不到「不发声明」的豁免
    draft     ①② 都无 草稿轨: 调版式/量像素用, 发布闸门读到即拒(这条不被任何姿态买到)

两个脚本共用这套裁决:
    path_b_build.py        渲染层 —— 三档旗标 `--deliver` / `--no-badge` / `--draft`
    check_publishable.py   发布层 —— declaration=undeclared ⇒ 不打 ③ 必带参数(但 ① 没烧时不给豁免)

CLI **永远压过姿态文件, 两个方向都能压**: `--deliver` / `--require-declaration`
把关掉的默认重新打开, `--no-badge` / `--draft` / `--allow-undeclared` 把打开的默认关掉。
三个渲染旗标只能挑一个 —— 同时给两个 = 停机, 不做「后者覆盖前者」那种猜。

**关掉的代价不因姿态而减免**: 渲染成草稿的产物, 发布闸门照样 EXIT=1; 渲染成 `no-badge`
的产物虽然可发布, 但声明(③)从此必须带, 关 ① 换不来「什么都不用说」。

退出/异常: 值不合法一律抛 `ModeError` 并点名文件路径, **不回退到任何默认**
(R6) —— 一次拼写错误不该替用户决定合规姿态。
"""
from __future__ import annotations

import json
import os

#: 仓库内固定位置(相对仓库根) —— 从脚本目录往上找, 与 CWD 无关, 换机器 clone 后仍找得到。
MODE_RELPATH = os.path.join("routes", "news", "aigc-mode.json")
#: 渲染层三档(D14): full = ①+② / no-badge = 只有 ②(可发布, 但 ③ 必带) / draft = ①② 都无(不可发布)。
RENDER_MODES = ("full", "no-badge", "draft")
DECLARATION_MODES = ("required", "undeclared")
#: 每段的缺省值 = 合规基线(全开)。写文件时不必两段都给, 少给的那段按全开算。
RENDER_DEFAULT = "full"
DECLARATION_DEFAULT = "required"
#: 档 → 单次旗标(反查用: 报错时要能说出"你给的这两个旗标各是哪一档")
RENDER_FLAGS = {"full": "--deliver", "no-badge": "--no-badge", "draft": "--draft"}
#: 档 → 这档到底做了什么。日志与台账只从这里取话, 别在两个脚本里各抄一遍(抄了就会漂)。
RENDER_WHAT = {
    "full": "交付轨: 烧 ① 角标 + 写 ② 元数据",
    "no-badge": "交付轨(按 D14 不烧 ①): ② 元数据照写 —— 可发布, 但发布必须带 ③",
    "draft": "草稿轨: ①② 都不做, 这份产物不可发布",
}


class ModeError(RuntimeError):
    """姿态文件本身有问题(不是合法 JSON / 值不在允许表里)。调用方必须停机, 不许兜默认。"""


def find_mode_file(start: str | None = None) -> str | None:
    """从 `start`(默认本脚本所在目录)逐级往上找姿态文件, 找不到返回 None。"""
    d = os.path.abspath(start or os.path.dirname(os.path.abspath(__file__)))
    while True:
        p = os.path.join(d, MODE_RELPATH)
        if os.path.isfile(p):
            return p
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def load_mode(path: str | None = None) -> dict:
    """读姿态文件 → dict(带 `_path`)。没有文件 = 空 dict = 两段都按全开走。

    `path` 显式给定却不存在时**停机**: 指了个文件却说"当没有", 是最难查的一类静默失败。
    """
    if path:
        if not os.path.isfile(path):
            raise ModeError(f"指定的 AIGC 姿态文件不存在: {path}")
        p = path
    else:
        p = find_mode_file()
        if not p:
            return {}
    try:
        with open(p, encoding="utf-8") as fh:
            mode = json.load(fh)
    except ValueError as exc:
        raise ModeError(f"{p} 不是合法 JSON: {exc}")
    if not isinstance(mode, dict):
        raise ModeError(f"{p} 必须是对象, 收到 {type(mode).__name__}")
    for field, allowed, dflt in (("render", RENDER_MODES, RENDER_DEFAULT),
                                 ("declaration", DECLARATION_MODES, DECLARATION_DEFAULT)):
        value = mode.get(field, dflt)
        if value not in allowed:
            raise ModeError(
                f"{p} 的 {field}={value!r} 不认 —— 只能是 {' / '.join(allowed)}。"
                "拼错就停机, 不许回退默认(合规姿态不该由一次拼写错误决定)")
    mode["_path"] = p
    return mode


def _resolve(mode: dict, field: str, *, on_value: str, off_value: str,
             off_flag: str, on_flag: str, off_given: bool, on_given: bool,
             file_label: str) -> tuple[str, str]:
    """两档开关的裁决(现在只剩 ③): 旗标 > 姿态文件 > 代码默认(全开)。返回 (取值, 人话原因)。

    ①② 那件已经换成三档的 `resolve_render`, 不走这里 —— 三档的"挑一个"冲突判定
    与两档的"两个相反旗标"判定不是一回事, 硬塞成一个函数会多出没人用的分支(R8)。

    原因串里**必须带真出处** —— 台账/闸门说"没标"却不说是旗标关的还是姿态文件关的,
    事后就查不到是谁把标关的。
    """
    if off_given and on_given:
        raise ModeError(f"{off_flag} 与 {on_flag} 互相矛盾(一个关标识一个开标识), 挑一个")
    if off_given:
        return off_value, f"{off_value}(旗标 {off_flag})"
    if on_given:
        return on_value, f"{on_value}(旗标 {on_flag})"
    if "_path" in mode:
        got = mode.get(field, on_value)
        return (off_value, f"{off_value}({file_label} {field}={off_value})") \
            if got == off_value else \
               (on_value, f"{on_value}({file_label} {field}={got})")
    return on_value, f"{on_value}(代码默认全开 —— 没有姿态文件)"


def resolve_render(mode: dict, *, draft: bool = False, deliver: bool = False,
                   no_badge: bool = False) -> tuple[str, str]:
    """渲染层开关(① 角标 / ② 元数据)最终取什么 → ("full"|"no-badge"|"draft", 原因)。

    三档而不是布尔: 旧的两档里"不要角标"只能选 draft, 而 draft 连 ② 一起砍, 产物发不出去 ——
    用户 2026-09-29 点头放宽判据(D14)后要的就是中间那档: ② 照写、① 不烧、可发布(但 ③ 必带)。
    """
    asked = [value for value, given in ((RENDER_MODES[0], deliver),
                                        (RENDER_MODES[1], no_badge),
                                        (RENDER_MODES[2], draft)) if given]
    if len(asked) > 1:
        raise ModeError(
            "、".join(RENDER_FLAGS[v] for v in asked) +
            " 互相矛盾(一次渲染只能落一轨: 全开 / 只关 ① / 全关), 挑一个")
    if asked:
        value = asked[0]
        return value, f"{value}(旗标 {RENDER_FLAGS[value]})"
    if "_path" in mode:
        value = mode.get("render", RENDER_DEFAULT)
        return value, f"{value}({mode.get('_path')} render={value})"
    return RENDER_DEFAULT, f"{RENDER_DEFAULT}(代码默认全开 —— 没有姿态文件)"


def resolve_declaration(mode: dict, *, allow_undeclared: bool = False,
                        require_declaration: bool = False) -> tuple[str, str]:
    """发布层开关(③ 平台自主声明)最终取什么 → ("undeclared"|"required", 原因)。"""
    return _resolve(mode, "declaration", on_value=DECLARATION_DEFAULT, off_value="undeclared",
                    off_flag="--allow-undeclared", on_flag="--require-declaration",
                    off_given=allow_undeclared, on_given=require_declaration,
                    file_label=mode.get("_path") or "姿态文件")


def describe(mode: dict) -> str:
    """给日志用的一行姿态摘要(不含 _path 噪音)。"""
    if not mode:
        return "姿态文件: 无 —— 两个开关按代码默认全开"
    return (f"姿态文件 {mode['_path']}: render={mode.get('render', RENDER_DEFAULT)} · "
            f"declaration={mode.get('declaration', DECLARATION_DEFAULT)}")
