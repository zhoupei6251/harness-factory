"""风格 spec（``schema = "hf-style/1"``）的载入、校验与**编译前**门禁。

真源上移：每套包一份结构化配置文件（spec §6.1），``frame.md`` 降级为编译产物。本模块只承担
**不需要编译产物**的那半套闸 —— 结构校验、色对预校验（判据 3）、区分度（判据 5）、
字幕禁入区反算（D5）。禁忌断言（法则 13）要读编译出来的 tween/CSS，注册表归编译器。

**格式偏离记录（要报备的一条）**：§6.1 原写 "每套 = 一份 YAML"。本实现用 **TOML +
stdlib `tomllib`** —— 仓库七级决策阶梯里 `原生` 排在 `新增依赖` 之前，而全仓没有任何
YAML 解析先例（唯一的 3 个 .yml 是 GitHub issue 模板，无人解析），引入 PyYAML 就是新增
pip 依赖。代价：Python 下限从 3.10 抬到 **3.11**（`tomllib` 自 3.11 进 stdlib）。
语义未变：七层结构、有限集语法、编译前门禁全部照 §6.1。

设计立场（照 §6.1）：spec 声明**结构**不只声明值。所以 ``grid.grammar`` 是从有限集里
**选**的，不是自由文本；选不出骨架的 grammar 直接拒编。
"""
from __future__ import annotations

import math
import re
import tomllib
from pathlib import Path

SCHEMA_ID = "hf-style/1"
SPEC_FILENAME = "spec.toml"

#: 七个必填层（§6.1）。缺一个就不是这份 schema。
LAYERS = ("grid", "type", "color", "motion", "subtitle", "layouts", "taboos")

#: 9 族 → 网格语法。**一对一**（裁决 6：族=语法差异，变体=语法内参数差异），
#: 所以同族变体必然共用 ``grid.grammar`` —— 判据 5 的其余三轴要自己扛住区分度。
#: 这份表就是 spec §10 Q2 的答案；语法名是编译器的骨架分发键，写错=取不到骨架。
FAMILY_GRAMMARS = {
    "headline": "outline-frame",          # 号外：粗黑描边包幅 + 45° 硬阴影 + 字压线
    "editorial": "asymmetric-columns",    # 杂志：非对称栏 + 首字下沉 + 大负空间
    "data": "figure-dominant",            # 数据：数字主角 + 网格底纹
    "street": "hand-annotated",           # 街采：手绘圈注 + 故意不对齐
    "film": "film-frame",                 # 胶片：颗粒 + 漏光 + 暗角 + 白边
    "neon": "scanline-stack",             # 霓虹：扫描线 + RGB 三层分离
    "swiss": "twelve-column",             # 瑞士：严格 12 栏 + 大留白
    "sports": "clash-blocks",             # 竞技：撞色块 + 记分牌
    "diagram": "bento-modules",           # 图解：模块卡 + 分步流程
}
GRID_GRAMMARS = tuple(sorted(FAMILY_GRAMMARS.values()))

#: 版式名是发射器与版式之间**唯一的契约面**（§6.3），必须与
#: `path_b_build.AUTO_LAYOUT_STEMS` 逐项相等 —— 由测试核，不靠 import（避免 2637 行
#: 的发射器被 spec 层反向依赖）。
CANONICAL_LAYOUTS = ("hook", "stat", "rail", "quote", "catalog", "story", "closer")

#: 强调色角色（现有法则 L1/L2 的泛化，§6.1）
ACCENT_ROLES = ("shape-only", "shape-or-large-text")

#: 文字尺寸档 → 用哪条 WCAG 达标线（阈值不抄第二份，见 `contrast_violations()`）
TEXT_SIZES = ("body", "large")

#: 明度阶梯至少几级才算"有阶梯"（判据 5 的第四轴要它真的不一样）
MIN_LADDER_STEPS = 3

#: `value-ladder` 与实际上桌面色的 HSL 明度之间允许多大偏差（百分点）。
#: 没有这条，"阶梯"只是一串装饰数字 —— §6.1 说它决定"看起来像什么"，那它必须核得上
#: 真实面色，`value_ladder_violations()` 负责这件事。
LADDER_TOLERANCE = 2.0

#: 法则 13：每族禁忌下限
MIN_TABOOS = 3

#: 引擎**自动供给**的拉丁族全集（闭集，不是偏好列表）。
#: 出处是渲染器本体：`node_modules/hyperframes/dist/chunk-HBBJFK6I.js:33-135` 的
#: `FONT_ALIAS_MAP` 首段"Canonical bundled fonts (self-referencing)" 与
#: `CANONICAL_FONT_DISPLAY_NAMES`。不在这一集里的族名会命中
#: `dist/chunk-WY5OODN5.js:6064` 的 `font_family_without_font_face`（severity=**error**），
#: `check --strict` 直接失败，而且字会静默回落到通用族 —— 排版整片走形却没人报错。
#: 别名（Bebas Neue→league-gothic、Georgia→eb-garamond 等）能过闸但渲染成**别人的脸**，
#: 所以 spec 也不许写别名：31 套的区分度不能建立在一次静默替换上。
LATIN_CANONICAL_FAMILIES = (
    "Inter", "Montserrat", "Outfit", "Nunito", "Oswald", "League Gothic",
    "Archivo Black", "Space Mono", "IBM Plex Mono", "JetBrains Mono",
    "EB Garamond", "Playfair Display", "Source Code Pro", "Noto Sans JP",
    "Roboto", "Open Sans", "Lato", "Poppins",
)

#: 字幕禁入区反算的余量（cqh）。口径见 `caption_reserve_cqh()` 文档。
CAPTION_HEADROOM_CQH = 1.0

KEBAB_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class SpecError(ValueError):
    """spec 不合法：编译器必须拒编，且要把全部理由一次报完（不许挤牙膏式报错）。"""


def chroma(hex_color: str) -> float:
    """hex → 彩度 = ``(max通道 − min通道) / 255`` ∈ [0,1]。

    **口径订正（P1 实施时实测，推翻 §6.1 的"从 hex 算 HSL 的 S"）**：HSL 的 S 在近中性
    色上会炸 —— 暖纸地 `#f5efe3` 的 HSL S = **0.474**，而强调橙 `#B45309` 才 0.905，
    两者只差 0.43；照 §6.1 的阈值 `accent-min-S .45 / support-max-S .15` 判，暖纸会被算成
    "高饱和强调色"，闸等于没设（`#7F1D1D` 这类暗底更是怎么判都不对）。
    max−min 口径下：暖纸 0.071 / 面板 0.114 / 墨 0.035 全在 support 侧，强调橙 0.671 在
    accent 侧 —— 与 .45/.15 这两个数**量纲相合**。字段名里的 `-S` 沿用 §6.1，含义以本函数为准。
    """
    channels = _channels(hex_color)
    return (max(channels) - min(channels)) / 255.0


def _channels(hex_color: str) -> list[int]:
    body = hex_color.lstrip("#")
    if len(body) == 3:
        body = "".join(ch * 2 for ch in body)
    return [int(body[i:i + 2], 16) for i in (0, 2, 4)]


def hsl_lightness(hex_color: str) -> float:
    """hex → 明度 = HSL 的 ``L = (max+min)/2``，返回 **0..100**（与 `value-ladder` 同量纲）。

    口径要点名，否则"明度"有三种读法（HSL L / HSV V / WCAG 相对亮度 Y），暖纸 `#f5efe3` 上
    分别给 **92.6 / 96.1 / 86.7** —— 差 9 个点，够把一条 ±2 的闸判反。`value-ladder` 用
    **HSL L**：它是人对"这张纸多亮"的直接口径，而 Y 是感知亮度（对比度用它，另有其位）。
    """
    channels = _channels(hex_color)
    return (max(channels) + min(channels)) / 2.0 / 255.0 * 100.0


def _bad_number(value: object) -> bool:
    """bool 是 int 的子类，而 `true` 当尺寸用一定是写错了。"""
    return not isinstance(value, (int, float)) or isinstance(value, bool)


def _require(cond: bool, problems: list[str], msg: str) -> None:
    if not cond:
        problems.append(msg)


def validate(raw: object, source: str = "<spec>") -> list[str]:
    """返回全部结构问题（空列表 = 合法）。这里只校语法；语义门禁另有三函数。"""
    problems: list[str] = []
    if not isinstance(raw, dict):
        return [f"{source}: 顶层必须是表（table），读到 {type(raw).__name__}"]

    _require(raw.get("schema") == SCHEMA_ID, problems,
             f"{source}: schema 必须是 '{SCHEMA_ID}'，读到 {raw.get('schema')!r}")
    for key in ("id", "family", "name"):
        value = raw.get(key)
        _require(isinstance(value, str) and value.strip() != "", problems,
                 f"{source}: 缺 {key}（非空字符串）")
    pack_id = raw.get("id")
    if isinstance(pack_id, str) and pack_id and not KEBAB_RE.match(pack_id):
        problems.append(f"{source}: id '{pack_id}' 不是 kebab-case")
    family = raw.get("family")
    if family is not None and family not in FAMILY_GRAMMARS:
        problems.append(f"{source}: family '{family}' 不在 9 族里 {sorted(FAMILY_GRAMMARS)}")

    for layer in LAYERS:
        if layer not in raw:
            problems.append(f"{source}: 缺层 '{layer}'（七层必填：{list(LAYERS)}）")

    problems.extend(_validate_grid(raw, source, family))
    problems.extend(_validate_type(raw, source))
    problems.extend(_validate_color(raw, source))
    problems.extend(_validate_motion(raw, source))
    problems.extend(_validate_subtitle(raw, source))

    layouts = raw.get("layouts")
    if layouts is not None:
        _require(isinstance(layouts, list) and sorted(map(str, layouts)) == sorted(CANONICAL_LAYOUTS),
                 problems, f"{source}: layouts 必须正好是 7 个具名版式 {list(CANONICAL_LAYOUTS)}"
                           f"，读到 {layouts!r}（版式名是发射器唯一的契约面，§6.3）")

    problems.extend(_validate_taboos(raw, source))
    return problems


def _validate_grid(raw: dict, source: str, family: object) -> list[str]:
    problems: list[str] = []
    grid = raw.get("grid")
    if not isinstance(grid, dict):
        return [f"{source}: grid 必须是表"]
    grammar = grid.get("grammar")
    _require(grammar in GRID_GRAMMARS, problems,
             f"{source}: grid.grammar '{grammar}' 不在有限集里 —— 编译器按名取骨架，"
             f"不许自由发挥（可选：{list(GRID_GRAMMARS)}）")
    if grammar in GRID_GRAMMARS and family in FAMILY_GRAMMARS:
        _require(grammar == FAMILY_GRAMMARS[family], problems,
                 f"{source}: grid.grammar '{grammar}' 与 family '{family}' 的骨架"
                 f" '{FAMILY_GRAMMARS[family]}' 不一致（裁决 6：族↔语法一对一）")
    safe = grid.get("safe")
    if not isinstance(safe, dict):
        problems.append(f"{source}: grid.safe 必须是表（左右栏位安全区 + bottom）")
        return problems
    if "bottom" not in safe:
        problems.append(f"{source}: grid.safe.bottom 必填（'auto' 或数字）")
    elif not (safe["bottom"] == "auto" or not _bad_number(safe["bottom"])):
        problems.append(f"{source}: grid.safe.bottom 只能是 'auto'（由 subtitle 反算，D5 的根治）"
                        f"或数字，读到 {safe['bottom']!r}")
    for side in ("left", "right"):
        _require(not _bad_number(safe.get(side)), problems,
                 f"{source}: grid.safe.{side} 必须是数字 —— 抖音右侧点赞栏要求左右各留 6%"
                 "（§6.4，与字幕归谁渲染无关的硬约束）")
    return problems


def _validate_type(raw: dict, source: str) -> list[str]:
    typ = raw.get("type")
    if not isinstance(typ, dict):
        return [f"{source}: type 必须是表"]
    problems: list[str] = []
    for key in ("display", "body"):
        value = typ.get(key)
        _require(isinstance(value, str) and value.strip() != "", problems,
                 f"{source}: type.{key} 必须写成可比较的族名/字重串（如 'HF Serif CJK/900'）")
    _require(isinstance(typ.get("latin"), list) and bool(typ.get("latin")), problems,
             f"{source}: type.latin 必须是非空列表（拉丁位由引擎自动供给，写裸族名）")
    if isinstance(typ.get("latin"), list):
        canonical = {name.lower() for name in LATIN_CANONICAL_FAMILIES}
        for name in typ["latin"]:
            _require(str(name).strip().lower() in canonical, problems,
                     f"{source}: type.latin '{name}' 不在引擎自动供给的 {len(LATIN_CANONICAL_FAMILIES)} 个"
                     f"捆绑族里（{', '.join(LATIN_CANONICAL_FAMILIES)}）—— 这个名字会触发 "
                     "font_family_without_font_face（error 级），`check --strict` 拒收，"
                     "并且字面静默回落成通用族")
    return problems


def _validate_color(raw: dict, source: str) -> list[str]:
    color = raw.get("color")
    if not isinstance(color, dict):
        return [f"{source}: color 必须是表"]
    problems: list[str] = []

    surfaces = color.get("surfaces")
    if not isinstance(surfaces, dict) or not surfaces:
        problems.append(f"{source}: color.surfaces 必须是非空表 {{面名 = hex}}（文字对坐在这上面）")
        surfaces = {}
    for name, hex_value in surfaces.items():
        _require(isinstance(hex_value, str) and bool(HEX_RE.match(hex_value)), problems,
                 f"{source}: color.surfaces.{name} 不是 #rrggbb，读到 {hex_value!r}")

    text = color.get("text")
    if not isinstance(text, list) or not text:
        problems.append(f"{source}: color.text 至少一条 {{role,hex,on,size}} —— "
                        "没有任何文字/底色对就没有可校验的对比度")
        text = []
    for i, pair in enumerate(text):
        if not isinstance(pair, dict):
            problems.append(f"{source}: color.text[{i}] 必须是表")
            continue
        for key in ("role", "hex", "on", "size"):
            _require(key in pair, problems, f"{source}: color.text[{i}] 缺 '{key}'")
        hex_value = pair.get("hex")
        _require(isinstance(hex_value, str) and bool(HEX_RE.match(hex_value or "")), problems,
                 f"{source}: color.text[{i}].hex 不是 #rrggbb，读到 {hex_value!r}")
        _require(pair.get("on") in surfaces, problems,
                 f"{source}: color.text[{i}].on '{pair.get('on')}' 不是已声明的面"
                 f"（有：{sorted(surfaces)}）")
        _require(pair.get("size") in TEXT_SIZES, problems,
                 f"{source}: color.text[{i}].size 只能是 {list(TEXT_SIZES)}，"
                 f"读到 {pair.get('size')!r}")

    accents = color.get("accents")
    if accents is None:
        accents = []
    if not isinstance(accents, list):
        problems.append(f"{source}: color.accents 必须是列表（可为空：本包不用强调色）")
        accents = []
    for i, accent in enumerate(accents):
        if not isinstance(accent, dict):
            problems.append(f"{source}: color.accents[{i}] 必须是表 {{hex, role}}")
            continue
        _require(accent.get("role") in ACCENT_ROLES, problems,
                 f"{source}: color.accents[{i}].role 只能是 {list(ACCENT_ROLES)}，"
                 f"读到 {accent.get('role')!r}")
        hex_value = accent.get("hex")
        _require(isinstance(hex_value, str) and bool(HEX_RE.match(hex_value or "")), problems,
                 f"{source}: color.accents[{i}].hex 不是 #rrggbb，读到 {hex_value!r}")

    budget = color.get("saturation-budget")
    if not isinstance(budget, dict):
        problems.append(f"{source}: color.saturation-budget 必填（治 D6：一帧几个高饱和色相）")
    else:
        for key in ("max-hues-per-frame", "accent-min-S", "support-max-S"):
            _require(not _bad_number(budget.get(key)), problems,
                     f"{source}: color.saturation-budget.{key} 必须是数字")
        amin, smax = budget.get("accent-min-S"), budget.get("support-max-S")
        if not _bad_number(amin) and not _bad_number(smax) and amin <= smax:
            problems.append(f"{source}: accent-min-S({amin}) 必须 > support-max-S({smax}) —— "
                            "留判定间隙，否则同一色既算强调又算辅助，闸等于没设")
        if not _bad_number(budget.get("max-hues-per-frame")) and budget["max-hues-per-frame"] < 1:
            problems.append(f"{source}: max-hues-per-frame 至少 1，读到 "
                            f"{budget['max-hues-per-frame']!r}")

    ladder = color.get("value-ladder")
    if not isinstance(ladder, list) or len(ladder) < MIN_LADDER_STEPS:
        problems.append(f"{source}: color.value-ladder 至少 {MIN_LADDER_STEPS} 级明度"
                        f"（判据 5 的第四轴，{MIN_LADDER_STEPS} 级以下不足以叫阶梯）")
    elif any(_bad_number(step) for step in ladder):
        problems.append(f"{source}: color.value-ladder 每项必须是数字（明度百分比）")
    elif list(ladder) != sorted(ladder, reverse=True) or len(set(ladder)) != len(ladder):
        problems.append(f"{source}: color.value-ladder 必须严格递减且不得重复，读到 "
                        f"{list(ladder)}（阶梯是纸→面板→线→墨的明度结构，乱序就不是结构）")
    return problems


def _validate_motion(raw: dict, source: str) -> list[str]:
    motion = raw.get("motion")
    if not isinstance(motion, dict):
        return [f"{source}: motion 必须是表"]
    problems: list[str] = []
    _require(isinstance(motion.get("signature"), str) and motion["signature"].strip() != "",
             problems, f"{source}: motion.signature 必须是具名串 —— 判据 5 的第三轴")
    easing = motion.get("easing")
    if not isinstance(easing, dict) or not isinstance(easing.get("forbidden"), list):
        problems.append(f"{source}: motion.easing.forbidden 必须是列表"
                        "（法则 13 要求禁忌可执行，编译期逐条补间核）")
    if not isinstance(easing, dict) or not _is_nonempty_str_list(easing.get("allowed")):
        problems.append(f"{source}: motion.easing.allowed 必须是非空列表"
                        "（口径：按偏好排序，第 0 个即这一族的招牌缓动，原语从这里取 ease）")
    _require(not _bad_number(motion.get("entrance-min-seconds")), problems,
             f"{source}: motion.entrance-min-seconds 必须是数字")
    _require(not _bad_number(motion.get("entrance-seconds")), problems,
             f"{source}: motion.entrance-seconds 必须是数字 —— 这一族招牌入场的时长，"
             "原语默认拿它，写在版式里就是又一个手抄常数")
    if (not _bad_number(motion.get("entrance-seconds"))
            and not _bad_number(motion.get("entrance-min-seconds"))
            and motion["entrance-seconds"] < motion["entrance-min-seconds"]):
        problems.append(f"{source}: motion.entrance-seconds "
                        f"{motion['entrance-seconds']} < entrance-min-seconds "
                        f"{motion['entrance-min-seconds']} —— 招牌时长比自家下限还短，"
                        "法则 13 的入场下限断言必然拒编")
    _require(motion.get("drift") in ("keep", "none"), problems,
             f"{source}: motion.drift 只能是 keep/none（裁决 9：瑞士族 'none' 是族级例外，"
             "MIN_DRIFT 由全局铁律降为族级默认值）")
    return problems


def _is_nonempty_str_list(value) -> bool:
    return isinstance(value, list) and bool(value) and all(str(v).strip() for v in value)


def _validate_subtitle(raw: dict, source: str) -> list[str]:
    subtitle = raw.get("subtitle")
    if not isinstance(subtitle, dict):
        return [f"{source}: subtitle 必须是表"]
    problems: list[str] = []
    for key in ("margin-bottom-frac", "line-height-frac", "worst-case-lines"):
        _require(not _bad_number(subtitle.get(key)), problems,
                 f"{source}: subtitle.{key} 必须是数字（底部禁入区靠它反算）")
    _require(isinstance(subtitle.get("position"), str) and subtitle["position"].strip() != "",
             problems, f"{source}: subtitle.position 必填（锚位说明，人读）")
    return problems


def _validate_taboos(raw: dict, source: str) -> list[str]:
    taboos = raw.get("taboos")
    if not isinstance(taboos, list):
        return [f"{source}: taboos 必须是列表"]
    problems: list[str] = []
    _require(len(taboos) >= MIN_TABOOS, problems,
             f"{source}: taboos 至少 {MIN_TABOOS} 条（法则 13：31 套会不会长成一套，"
             "取决于禁忌有没有写死）")
    seen: list[str] = []
    for i, taboo in enumerate(taboos):
        if not isinstance(taboo, dict):
            problems.append(f"{source}: taboos[{i}] 必须是表 {{check, why}}")
            continue
        check = taboo.get("check")
        _require(isinstance(check, str) and bool(KEBAB_RE.match(check or "")), problems,
                 f"{source}: taboos[{i}].check 必须是 kebab-case 断言名（编译器按名取断言）")
        _require(isinstance(taboo.get("why"), str) and str(taboo.get("why")).strip() != "",
                 problems, f"{source}: taboos[{i}].why 必填 —— 拒编时要说清为什么")
        if check in seen:
            problems.append(f"{source}: taboos[{i}].check '{check}' 重复")
        elif isinstance(check, str):
            seen.append(check)
    return problems


class Spec:
    """一份已通过结构校验的 spec。字段只读，取值走访问器（避免下游各写一套路径）。"""

    def __init__(self, raw: dict, path: Path | None = None) -> None:
        self.raw = raw
        self.path = path

    @property
    def id(self) -> str:
        return self.raw["id"]

    @property
    def family(self) -> str:
        return self.raw["family"]

    @property
    def name(self) -> str:
        return self.raw["name"]

    @property
    def grammar(self) -> str:
        return self.raw["grid"]["grammar"]

    @property
    def surfaces(self) -> dict[str, str]:
        return dict(self.raw["color"]["surfaces"])

    @property
    def text_pairs(self) -> list[dict]:
        return list(self.raw["color"]["text"])

    @property
    def accents(self) -> list[dict]:
        return list(self.raw["color"].get("accents") or [])

    @property
    def saturation_budget(self) -> dict:
        return dict(self.raw["color"]["saturation-budget"])

    @property
    def value_ladder(self) -> list[float]:
        return [float(step) for step in self.raw["color"]["value-ladder"]]

    @property
    def subtitle(self) -> dict:
        return dict(self.raw["subtitle"])

    @property
    def motion(self) -> dict:
        return dict(self.raw["motion"])

    @property
    def layouts(self) -> list[str]:
        return list(self.raw["layouts"])

    @property
    def taboos(self) -> list[dict]:
        return list(self.raw["taboos"])

    def signature(self) -> tuple:
        """判据 5 的四轴。同族变体在第一轴上**必然相同**（裁决 6），所以另外三轴要自己拉开。"""
        return (
            self.grammar,
            self.raw["type"]["display"],
            self.raw["motion"]["signature"],
            tuple(self.raw["color"]["value-ladder"]),
        )


#: 判据 5 的四轴名（顺序与 `Spec.signature()` 严格对应）
AXIS_NAMES = ("grid.grammar", "type.display", "motion.signature", "color.value-ladder")


def load_spec(path: Path) -> Spec:
    """读 TOML → 结构校验 → 落地。结构问题一次报完。"""
    with open(path, "rb") as handle:
        raw = tomllib.load(handle)
    problems = validate(raw, source=str(path))
    if problems:
        raise SpecError(f"{Path(path).name} 拒编（{len(problems)} 条）:\n  " + "\n  ".join(problems))
    return Spec(raw, Path(path))


def caption_reserve_cqh(subtitle: dict, canvas_height: float = 1920.0) -> float:
    """由字幕几何反算底部禁入区（cqh）—— D5（禁入区写死 20）的根治。

    口径（全部取自 `path_b_build` 的实测几何，本轮不新增数）：
      块底 = h − margin_v，行距 = 字号 = h/32，最坏 `worst-case-lines` 行往上顶；
      顶边以上不许版面压字 → 原始禁入区 = (h − 顶边)/h×100；再加 `CAPTION_HEADROOM_CQH`
      1 个整数 cqh 的余量后**向上取整**。
    现状产线参数（margin 0.09、字号 h/32、按 3 行算最坏）算出来正好 **20.0**，等于
    `layout_selfcheck.CAPTION_RESERVE_CQH` —— 这个相等关系由测试锁死。不锁的话
    "改成 spec 驱动"会顺手把现存 227 个版式的闸口放宽或收紧，而那是没人签字的改动。
    第二个独立校验：按 2 行算得 `top_px = 1627.2`，对上 `path_b_build.py:370-373` 那次
    逐行像素实测的"两行顶边 ≈ 1628px"（同处三行 ≈1568px 也在 `n=3` 下复现）。
    """
    margin_v = subtitle["margin-bottom-frac"] * canvas_height
    line_px = subtitle["line-height-frac"] * canvas_height
    top_px = canvas_height - margin_v - subtitle["worst-case-lines"] * line_px
    raw_reserve = (canvas_height - top_px) / canvas_height * 100.0
    return float(math.ceil(raw_reserve + CAPTION_HEADROOM_CQH))


def contrast_violations(spec: Spec) -> list[str]:
    """判据 3：编译前把 spec 声明的每个文字/底色对核一遍 WCAG，不过即拒编。

    阈值与算法都**从 `audit_pack_contrast` 取**（裁决 11：数学已在 Python，非重写）。
    在这里再写一份 4.5/3.0 就是第二个手抄假数 —— D10 踩过。
    """
    from audit_pack_contrast import BODY_MIN_RATIO, LARGE_MIN_RATIO, contrast_ratio

    surfaces = spec.surfaces
    floors = {"body": BODY_MIN_RATIO, "large": LARGE_MIN_RATIO}
    problems: list[str] = []
    for pair in spec.text_pairs:
        floor = floors[pair["size"]]
        background = surfaces[pair["on"]]
        ratio = contrast_ratio(pair["hex"], background)
        if ratio < floor:
            problems.append(
                f"{spec.id}: {pair['role']}（{pair['hex']} on {pair['on']} {background}）"
                f"对比 {ratio:.2f} < {pair['size']} 下限 {floor}")
    return problems


def saturation_violations(spec: Spec) -> list[str]:
    """`saturation-budget` 的**声明侧**：自称强调色的，彩度够不够。

    只校 accent 下限这一侧。`support-max-S`（面色别太艳）和 `max-hues-per-frame`
    （一帧里几个高饱和色相）都要**逐元素逐帧**数， spec 层数不了 —— 一份色板里同时有
    2 个高彩度色并不矛盾，只要它们不同时上一帧。这两条排在编译器（法则 11/12 配额处）。
    """
    budget = spec.saturation_budget
    problems: list[str] = []
    for accent in spec.accents:
        value = chroma(accent["hex"])
        if value < budget["accent-min-S"]:
            problems.append(f"{spec.id}: 强调色 {accent['hex']} 彩度 {value:.3f} < "
                            f"accent-min-S {budget['accent-min-S']} —— 自称强调却艳不过辅助色")
    return problems


def value_ladder_violations(spec: Spec) -> list[str]:
    """判据 5 第四轴的可执行化：`value-ladder` 必须**核得上真实面色**，两个方向都核。

    为什么要有这条：spec 里那串数字是"这套看起来像什么"的骨架（§6.1），但结构校验只能证
    它递减、够三级 —— 证不了它对应色板上存在的明度档。一个 `value-ladder = [99, 50, 1]`
    的纸面包能过全部结构闸，然后 P5 拿它当"第四轴已经不同"的证据去铺 31 套，区分度是假的。

    口径（与 `hsl_lightness()` 同一条，量纲 0..100）：
    1. 每个**非强调**面色的 HSL L，必须落在阶梯某档 ±`LADDER_TOLERANCE` 内；
    2. 每一档阶梯至少被一个非强调面色命中（档写了却没人坐上去 = 装饰）。

    强调色不参与：它走 `saturation-budget` 与 `accents[].role`，暖纸的 #B45309 明度 37
    本就不该在阶梯里 —— 阶梯描述的是纸面结构（纸/面板/分隔线/墨），不是全部色。
    """
    ladder = spec.value_ladder
    accent_hexes = {str(accent.get("hex", "")).lower() for accent in spec.accents}
    problems: list[str] = []
    matched: set[float] = set()
    for name, hex_value in sorted(spec.surfaces.items()):
        if str(hex_value).lower() in accent_hexes:
            continue
        lightness = hsl_lightness(hex_value)
        nearest = min(ladder, key=lambda step: abs(step - lightness))
        if abs(nearest - lightness) > LADDER_TOLERANCE:
            problems.append(
                f"{spec.id}: 面色 {name}({hex_value}) 明度 {lightness:.1f} 离最近的阶梯档 "
                f"{nearest} 差 {abs(nearest - lightness):.1f} > ±{LADDER_TOLERANCE} —— "
                f"value-ladder {ladder} 与色板对不上")
            continue
        matched.add(nearest)
    for step in ladder:
        if step not in matched:
            problems.append(f"{spec.id}: value-ladder 的 {step} 档没有任何面色落在 "
                            f"±{LADDER_TOLERANCE} 内 —— 阶梯写了却不存在的档")
    return problems


def distinctness_violations(specs: list[Spec]) -> list[str]:
    """判据 5：任意两套之间，四轴至少两项不同。

    这是本设计最重要的一条新增闸（31 套塌回一套历史上发生过，见 §3）。跟裁决 6 咬合后的
    算术后果要点明：同族变体 ``grid.grammar`` 必同 → 剩下三轴里两两汉明距离 ≥2，而 4 个变体
    在 3 维立方里**恰好只有奇偶两类**放得下（000/011/101/110 或 100/010/001/111）——
    不是"尽量不一样"，是必须按这个排布选参数。P5 铺 31 套时这是硬约束，不是审美建议。
    """
    problems: list[str] = []
    for i in range(len(specs)):
        for j in range(i + 1, len(specs)):
            left, right = specs[i], specs[j]
            sa, sb = left.signature(), right.signature()
            same = [AXIS_NAMES[k] for k in range(4) if sa[k] == sb[k]]
            if len(same) > 4 - 2:
                problems.append(
                    f"区分度不足：{left.id} 与 {right.id} 在 {len(same)} 轴上相同"
                    f"（判据 5 要求 ≤2）—— {', '.join(same)}")
    return problems


def precompile_violations(spec: Spec) -> list[str]:
    """编译器取一份 spec 时跑的**全部** spec 级门禁（结构已在 load_spec 里过）。"""
    return (contrast_violations(spec) + saturation_violations(spec)
            + value_ladder_violations(spec))
