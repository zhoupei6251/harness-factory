#!/usr/bin/env python3
"""节目包色板对比度审计 —— 把 frame.md 里的"实测值"变成一条可复算的命令。

（对 12 个 pack 通用：参数就是含 ``frame.md`` 的版式目录；规则不认包名，只认表格式与
WCAG 2.x 公式。现已覆盖 news-coral 与 news-policy，其余 10 包虽只有占位壳，
但 frame.md 的色板契约同样受本脚本约束 —— 占位不等于色板可以乱写。）

为什么有这个脚本（每条判据都对应一次真实事故，不是想象中的规则）：

1. DOC_RATIO_DRIFT —— ``news-policy`` 落地时（2026-09-29）在 frame.md §2.1 写了
   ``gold / cobalt 3.87 ✗ 连大字档也不过``，而 3.87 **过了**大字线 3.0。手写"实测"表
   没有复算入口，文档里的判读就比真实数学更严 —— 下一个改字阶的人会为一个不存在的约束绕路。
   现在这张表由机器复算，数字错了就红。
2. VERDICT_CONTRADICTS_ARITHMETIC —— 同一格"判定"里混写了两件事：**数学**（过不过线）与
   **包内法则**（gold 一律只作形状）。法则可以比数学严，数学不行；审计按三条硬判据查措辞与数字。
3. OFF_PALETTE_HEX —— coral 的 frame.md 开头就写着"本版式里出现的每一个色值都必须能在这里找到出处"，
   但这条法则此前没有任何脚本执行。版式 HTML 里出现色板外的 hex，等于设计系统开始漏。

精度口径：比对按**文档自己写的小数位数**取整（coral 两位、其余包一位），
因此既能抓真漂移，也不会因四舍五入误报。

用法::

    python audit_pack_contrast.py                          # 全部 pack，复算每一行
    python audit_pack_contrast.py news-policy --matrix     # 追加 token×token 全矩阵（设计新 pack 用）
    python audit_pack_contrast.py news-coral --quiet       # 只在有问题时输出
    python audit_pack_contrast.py --json                   # 机器读（selftest / 验证单引用）

返回码：0 = 色板与文档一致；1 = 有漂移或矛盾（逐条打印 ``pack:规则:说明``）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- 常量（禁止魔法值）

#: WCAG 2.x 正文对比度下限（AA，正常字号）
BODY_MIN_RATIO = 4.5

#: WCAG 2.x 大字对比度下限（AA Large）
LARGE_MIN_RATIO = 3.0

#: 画布短边基准像素（竖屏 9:16 = 1080×1920）
CANVAS_WIDTH_PX = 1080.0

#: WCAG "大字"定义换算到本画布的字号线：24px ÷ 10.8px/cqw
#: （1cqw = 画布宽/100 = 10.8px，所以 24px ≈ 2.22cqw）
LARGE_TEXT_PX = 24.0
LARGE_TEXT_CQW = LARGE_TEXT_PX * 100.0 / CANVAS_WIDTH_PX

#: frame.md 色板表与对比度表的表头指纹（只认列名，不认小节编号）
PALETTE_HEADER_KEYS = ("token", "值")
RATIO_HEADER_KEYS = ("组合", "比值")

#: 十六进制色值（#rgb / #rrggbb），HTML 与 frame.md 共用同一正则
HEX_COLOR_RE = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")

#: 判定列里的"数学没过线"与"包内法则"用词，二者不可混写
FAIL_WORDS = ("✗", "×", "禁止", "不许")
LARGE_CLAIM_RE = re.compile(r"大字|大字号")
NOT_PASS_RE = re.compile(r"不过|不够|不达")

#: 版式目录发现顺序：显式参数 → 兄弟 templates 目录
DEFAULT_PACKS_ROOT = Path(__file__).resolve().parent.parent / "templates" / "hyperframes_path_b"


class Finding:
    """一条审计结论。``rule`` 稳定可 grep，``pack`` 让报错能直接指回某个包。"""

    def __init__(self, pack: str, rule: str, detail: str, *, warning: bool = False):
        self.pack, self.rule, self.detail = pack, rule, detail
        self.warning = warning

    def __str__(self) -> str:
        mark = "警告" if self.warning else "违规"
        return f"{self.pack}:{self.rule}:{mark} —— {self.detail}"


# ---------------------------------------------------------------- WCAG 数学

def _srgb_channel(byte_value: int) -> float:
    """单通道 8bit → 线性光（sRGB 传递函数，低于拐点走线性段）。"""
    c = byte_value / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    """WCAG 相对亮度 L = 0.2126R + 0.7152G + 0.0722B（线性化之后）。"""
    digits = _normalize_hex(hex_color)
    r, g, b = (int(digits[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _srgb_channel(r) + 0.7152 * _srgb_channel(g) + 0.0722 * _srgb_channel(b)


def contrast_ratio(foreground: str, background: str) -> float:
    """对比度 (L_hi + 0.05) / (L_lo + 0.05)，取值 1–21，天然对称（不区分谁在上）。"""
    hi, lo = sorted((relative_luminance(foreground), relative_luminance(background)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def band_of(ratio: float) -> str:
    """比值落在哪一档：任意字号 / 仅大字 / 不达标。"""
    if ratio >= BODY_MIN_RATIO:
        return "任意字号"
    if ratio >= LARGE_MIN_RATIO:
        return "仅大字"
    return "不达标"


def _normalize_hex(hex_color: str) -> str:
    body = hex_color.lstrip("#")
    if len(body) == 3:
        body = "".join(ch * 2 for ch in body)
    return body.lower()


# ---------------------------------------------------------------- frame.md 解析

def _iter_tables(text: str):
    """产出 markdown 表格 ``(header_cells, [row_cells, ...])``；跳过 ``|---|`` 分隔行。"""
    rows: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.count("|") >= 2:
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                continue
            rows.append(cells)
        elif rows:
            yield rows[0], rows[1:]
            rows = []
    if rows:
        yield rows[0], rows[1:]


def _table_by_header(text: str, keys: tuple[str, ...]):
    """按表头列名（不区分大小写、忽略加粗）挑表。"""
    for header, body in _iter_tables(text):
        joined = " ".join(cell.strip("*_ ").lower() for cell in header)
        if all(key.lower() in joined for key in keys):
            return body
    return None


def parse_palette(text: str) -> dict[str, str]:
    """色板表 → ``{token: 归一化 hex}``；表里没有 hex 的行跳过（注释行、合计行）。"""
    palette: dict[str, str] = {}
    for cells in _table_by_header(text, PALETTE_HEADER_KEYS) or []:
        if len(cells) < 2:
            continue
        name = cells[0].strip("`*_ ")
        match = HEX_COLOR_RE.search(cells[1])
        if name and match:
            palette[name] = _normalize_hex(match.group(0))
    return palette


def parse_ratio_claims(text: str) -> list[tuple[str, float, str, int]]:
    """对比度表 → ``[(组合标签, 比值, 判定, 小数位数), ...]``；数字解析不了的行不算声明。"""
    claims: list[tuple[str, float, str, int]] = []
    for cells in _table_by_header(text, RATIO_HEADER_KEYS) or []:
        if len(cells) < 3:
            continue
        raw = cells[1].strip().strip("*_ ")
        try:
            value = float(raw)
        except ValueError:
            continue
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        claims.append((cells[0].strip(), value, cells[2], decimals))
    return claims


def resolve_side(side: str, palette: dict[str, str]) -> str | None:
    """把 ``**cobalt-dark 字**`` / ``paper / cobalt（暗面）`` 这类标签认回 token。

    规则：去掉加粗与括号注解后，取"是这一半的子串"的**最长** token
    （``light-gray`` 必须赢过 ``gray``，否则会把配角字色认成正文字色）。
    """
    cleaned = re.sub(r"（[^）]*）|\([^)]*\)", "", side).strip().strip("*_ ` ")
    hits = [tok for tok in palette if tok.lower() in cleaned.lower()]
    return max(hits, key=len) if hits else None


# ---------------------------------------------------------------- 审计

def audit_pack(pack_dir: Path, *, matrix: bool = False) -> tuple[list[str], list[Finding]]:
    """审计单个 pack：返回 ``(矩阵文本行, 结论列表)``。"""
    name = pack_dir.name
    findings: list[Finding] = []
    frame = pack_dir / "frame.md"
    if not frame.is_file():
        return [], [Finding(name, "NO_FRAME_MD", "缺 frame.md，色板没有出处可查")]

    text = frame.read_text(encoding="utf-8")
    palette = parse_palette(text)
    if not palette:
        return [], [Finding(name, "NO_PALETTE_TABLE",
                            "frame.md 找不到 `| token | 值 |` 色板表，审计无从复算")]

    # 1) 文档声明的比值必须与色板算术一致
    for label, value, verdict, decimals in parse_ratio_claims(text):
        sides = label.split("/")
        if len(sides) != 2:
            findings.append(Finding(name, "DOC_PAIR_UNMATCHED",
                                    f"组合标签「{label}」不是一个 `A / B` 对", warning=True))
            continue
        fg = resolve_side(sides[0], palette)
        bg = resolve_side(sides[1], palette)
        if not fg or not bg:
            missing = [s.strip().strip("*_ ") for s, tok in zip(sides, (fg, bg)) if not tok]
            findings.append(Finding(name, "DOC_PAIR_UNMATCHED",
                                    f"「{label}」里的 {missing} 不在色板 token 表内", warning=True))
            continue
        computed = contrast_ratio("#" + palette[fg], "#" + palette[bg])
        if round(computed, decimals) != round(value, decimals):
            findings.append(Finding(name, "DOC_RATIO_DRIFT",
                                    f"「{label}」文档写 {value}，按色板复算 {computed:.2f}"
                                    f"（{fg} #{palette[fg]} / {bg} #{palette[bg]}）"))
            continue
        findings.extend(_check_verdict(name, f"{fg} / {bg}", computed, value, verdict))

    # 2) 版式 HTML 与宿主里不许出色板外的色值（frame.md 自称"唯一 token 源"）
    #    placeholder.html 例外：占位壳既不进版式选择也不进可渲染计数（与 path_b_build 同口径），
    #    它装的是通用灰壳，真版式一落地就受审 —— 审它只会淹掉真信号。
    palette_hexes = set(palette.values())
    audited = [p for p in (pack_dir / "compositions").glob("*.html")
               if p.name != "placeholder.html"]
    host = pack_dir / "host.html"
    if host.is_file():
        audited.append(host)
    for html in sorted(audited):
        for match in HEX_COLOR_RE.finditer(html.read_text(encoding="utf-8")):
            hex_value = _normalize_hex(match.group(0))
            if hex_value not in palette_hexes:
                findings.append(Finding(name, "OFF_PALETTE_HEX",
                                        f"{html.name} 用了色板外的 {match.group(0)}"))

    lines = _matrix_lines(name, palette, text) if matrix else []
    return lines, findings


def _check_verdict(pack: str, pair: str, computed: float, declared: float,
                   verdict: str) -> list[Finding]:
    """判定列与算术是否互相打架（法则可以比数学严，但必须写明是法则）。"""
    fails_math = any(w in verdict for w in FAIL_WORDS)
    claims_large_pass = bool(LARGE_CLAIM_RE.search(verdict)) and not NOT_PASS_RE.search(verdict)
    claims_any_size = "任意字号" in verdict or "任意大小" in verdict

    out: list[Finding] = []
    if computed >= BODY_MIN_RATIO and fails_math and not NOT_PASS_RE.search(verdict):
        out.append(Finding(pack, "VERDICT_CONTRADICTS_ARITHMETIC",
                           f"「{pair}」{computed:.2f} 已过正文线 {BODY_MIN_RATIO}，判定却写 ✗ —— "
                           "若是包内法则（如 gold 只作形状）请写明『法则』，别写成数学不过"))
    if LARGE_MIN_RATIO <= computed < BODY_MIN_RATIO and claims_any_size:
        out.append(Finding(pack, "VERDICT_CONTRADICTS_ARITHMETIC",
                           f"「{pair}」{computed:.2f} 只在大字档合法（正文线 {BODY_MIN_RATIO} 不过），"
                           "不能写『任意字号』"))
    if computed < LARGE_MIN_RATIO and claims_large_pass:
        out.append(Finding(pack, "VERDICT_CONTRADICTS_ARITHMETIC",
                           f"「{pair}」{computed:.2f} 低于大字线 {LARGE_MIN_RATIO}，"
                           "判定却写成大字可过"))
    return out


def _matrix_lines(name: str, palette: dict[str, str], frame_text: str) -> list[str]:
    """token×token 全矩阵（降序），并标出文档已声明过的对，方便补表。"""
    cited = set()
    for label, _, _, _ in parse_ratio_claims(frame_text):
        sides = label.split("/")
        if len(sides) == 2:
            fg, bg = resolve_side(sides[0], palette), resolve_side(sides[1], palette)
            if fg and bg:
                cited.add(tuple(sorted((fg, bg))))
    tokens = list(palette)
    pairs = [(a, b, contrast_ratio("#" + palette[a], "#" + palette[b]))
             for i, a in enumerate(tokens) for b in tokens[i + 1:]]
    lines = [f"[{name}] 相对亮度 L："
             + " · ".join(f"{t} {relative_luminance('#' + h):.4f}" for t, h in palette.items())]
    lines.append(f"[{name}] 全矩阵（1cqw = {CANVAS_WIDTH_PX / 100:.1f}px，"
                 f"大字线 ≥{LARGE_TEXT_PX:.0f}px ≈ ≥{LARGE_TEXT_CQW:.2f}cqw，"
                 f"正文 ≥{BODY_MIN_RATIO} / 大字 ≥{LARGE_MIN_RATIO}）")
    for a, b, ratio in sorted(pairs, key=lambda p: -p[2]):
        mark = "*" if tuple(sorted((a, b))) in cited else " "
        lines.append(f"  {mark} {a} / {b}: {ratio:.2f}  {band_of(ratio)}")
    lines.append("  （* = frame.md 已声明该对）")
    return lines


def discover_packs(root: Path) -> list[Path]:
    return sorted(p for p in root.iterdir() if (p / "frame.md").is_file())


def resolve_pack_arg(arg: str, root: Path) -> Path:
    candidate = Path(arg)
    if candidate.is_dir():
        return candidate
    sibling = root / arg
    if sibling.is_dir():
        return sibling
    raise SystemExit(f"找不到版式目录（既不是目录也不在 {root} 下）: {arg}")


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):  # Windows 控制台默认 cp936，中文说明会变问号
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Path B 节目包色板对比度审计（逐 pack 的 frame.md 复算）")
    parser.add_argument("packs", nargs="*", help="pack 目录或包名；缺省 = 全部 12 包")
    parser.add_argument("--matrix", action="store_true", help="打印 token×token 全矩阵（含未声明的对）")
    parser.add_argument("--quiet", action="store_true", help="只在有违规时输出")
    parser.add_argument("--json", action="store_true", dest="as_json", help="结构化输出（selftest / 验证单用）")
    args = parser.parse_args(argv)

    root = DEFAULT_PACKS_ROOT
    packs = [resolve_pack_arg(p, root) for p in args.packs] or discover_packs(root)
    if not packs:
        print(f"{root} 下没有任何含 frame.md 的 pack", file=sys.stderr)
        return 1

    report: dict[str, object] = {}
    findings: list[Finding] = []
    warnings: list[Finding] = []
    for pack_dir in packs:
        lines, pack_findings = audit_pack(pack_dir, matrix=args.matrix)
        for line in lines:
            print(line)
        findings += [f for f in pack_findings if not f.warning]
        warnings += [f for f in pack_findings if f.warning]
        report[pack_dir.name] = {
            "violations": [f.rule + ": " + f.detail for f in pack_findings if not f.warning],
            "warnings": [f.rule + ": " + f.detail for f in pack_findings if f.warning],
        }

    if args.as_json:
        print(json.dumps({"ok": not findings, "violations": len(findings),
                          "warnings": len(warnings), "packs": report},
                         ensure_ascii=False, indent=2))
        return 1 if findings else 0
    for finding in findings + warnings:
        print(str(finding))
    if findings:
        print(f"\n对比度审计不过：{len(packs)} 个 pack 里 {len(findings)} 条违规"
              f"（另有 {len(warnings)} 条警告）")
        return 1
    if not args.quiet:
        print(f"对比度审计通过：{len(packs)} 个 pack 的 frame.md 色板与文档一致"
              f"（{len(warnings)} 条警告）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
