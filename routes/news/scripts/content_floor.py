#!/usr/bin/env python3
"""content_floor —— 量一帧里"最底墨线"落在哪（cqh），用来判两件事：

1. **字幕禁入区有没有被占**（`layout_selfcheck` 规则 7 的像素版）
2. **法则 17 填幅够不够**（`hf_compile` 只在 path_c 的配方几何上实现过，静态 227 份 HTML
   和 Vue 支今天都没有这条闸 —— 见 evidence/2026-10-16-task5-precheck-findings.md）

为什么必须按像素量，不能按 CSS 文本量：规则 7 读 `bottom:`/`inset:`，成立前提是偏移相对
满幅 `#root`；组件的偏移相对内层 stage（`.fd-place{bottom:6cqh}` 在 `.fd-stage{inset:0 0
36cqh 0}` 里，实际 42cqh）⇒ 文本口径对组件**假红**。而引擎的 `--caption-zone` 已用活体负例
证明不是侵入探测器（地点行渲到 85.6cqh，`check --strict` 仍 0 finding）。

口径（三条都是**现取常数**，不在这里抄数）：
  墨 = 与**本帧地面色**构成 ≥ 3:1 对比的像素。3:1 不是新阈值 —— 它是本仓库对比度审计
  与引擎 `contrast_aa_failure` 用的同一条 AA 大字档线，"看得见的字"本就是它的语义。
  地面色 = 本帧像素（按 8 阶量化后）的众数。版式是"文字压在平涂地面上"，背景按面积必赢。
  带 = [80.0 − 0.5 − 8.0, 80.0] = [71.5, 80.0] cqh：上沿不许进字幕区，下沿不许空过法则 17。

**只量无图镜**：照片本身就是画面内容，字幕压在照片上由字幕底衬负责，不是版式的锅；
带图帧的"最底墨线"必然贴到画面底，判它等于判"这张图铺满了" —— 假红。
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills/douyin-pro/scripts"))
import layout_selfcheck as lsc          # noqa: E402  CAPTION_RESERVE_CQH
import hf_compile as hc                 # noqa: E402  MAX_BOTTOM_DEAD_CQH / CONTENT_FLOOR_MARGIN_CQH

#: 判"是不是墨"的对比度线 —— 与 audit_pack_contrast / 引擎 contrast_aa_failure 同源
INK_CONTRAST = 3.0
#: 地面色众数按 8 阶量化，抗抖色与编码噪声
GROUND_QUANT = 8
#: 横向采样步长（像素）。竖屏文字行宽几十 px，4 步长不会漏整行
X_STRIDE = 4

ZONE_TOP_CQH = 100.0 - lsc.CAPTION_RESERVE_CQH
LIMIT_CQH = ZONE_TOP_CQH - hc.CONTENT_FLOOR_MARGIN_CQH
FILL_FLOOR_CQH = LIMIT_CQH - hc.MAX_BOTTOM_DEAD_CQH


def _luminance(rgb: np.ndarray) -> np.ndarray:
    """WCAG 相对亮度（向量化，口径与 sRGB 标准一致）。"""
    c = rgb / 255.0
    lin = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]


def _contrast(l1: np.ndarray, l2) -> np.ndarray:
    hi = np.maximum(l1, l2)
    lo = np.minimum(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def ground_color(img: np.ndarray) -> tuple[int, int, int]:
    """本帧地面色 = 8 阶量化后的众数。版式按面积是"平涂地面 + 少量墨"，众数必是地面。"""
    flat = (img[::4, ::X_STRIDE] // GROUND_QUANT * GROUND_QUANT).reshape(-1, 3)
    keys = flat[:, 0] * 65536 + flat[:, 1] * 256 + flat[:, 2]
    values, counts = np.unique(keys, return_counts=True)
    g = int(values[counts.argmax()])
    return ((g >> 16) & 0xFF, (g >> 8) & 0xFF, g & 0xFF)


def measure(png: Path, ratio: float = INK_CONTRAST) -> dict:
    """返回一帧的量：最底墨线（cqh）、地面色、墨覆盖率最高的那一行。"""
    img = np.asarray(Image.open(png).convert("RGB"), dtype=np.uint8)
    h = img.shape[0]
    ground = ground_color(img)
    lum = _luminance(img.astype(np.float64))
    ink = _contrast(lum, _luminance(np.array(ground, dtype=np.float64))) >= ratio
    per_row = ink[:, ::X_STRIDE].sum(axis=1)
    rows = np.flatnonzero(per_row > 0)
    bottom = int(rows.max()) if rows.size else -1
    return {
        "file": png.name,
        "height_px": h,
        "ground_rgb": list(ground),
        "content_floor_cqh": round(bottom / h * 100.0, 2) if bottom >= 0 else None,
        "ink_row_max": int(per_row.max()) if rows.size else 0,
    }


def intrude_only(content_floor_cqh) -> list[str]:
    """字幕区那一半 —— 31 包实测今天全过，所以普查里它是**硬判据**。"""
    if content_floor_cqh is None:
        return ["整帧找不到任何 ≥3:1 的墨 —— 这一镜是空画面"]
    if content_floor_cqh > ZONE_TOP_CQH:
        return [f"最底墨线 {content_floor_cqh:.1f}cqh 越过字幕禁入区上沿 "
                f"{ZONE_TOP_CQH:.1f}cqh（侵入 {content_floor_cqh - ZONE_TOP_CQH:.1f}cqh）"
                " —— 字幕会压在内容上"]
    return []


def fill_only(content_floor_cqh) -> list[str]:
    """法则 17 的 8cqh 线，套在**成片实文**上 —— 注意这是"报"，不是那条规则的判定点。

    `hf_compile.MAX_BOTTOM_DEAD_CQH` 自己的注释写着：口径是**配方的最坏占位**
    （`Step.height_cqh` 按最大行数算），「这条闸只管"设计意图上就不打算填幅"的那一类，
    短文本要填幅得改配方」。本函数量的却是真实文本渲染后的帧 ⇒ 同一数字换了对称对象，
    所以它只能当**分布指标**看。closer 探针实测：字号 +29% 只买到 +8.75cqh，
    再放大就撞 8 字 CTA 换行 —— 短内容版式在这个数上不可能过，也不该过。
    """
    if content_floor_cqh is None or content_floor_cqh >= FILL_FLOOR_CQH:
        return []
    return [f"最底墨线只到 {content_floor_cqh:.1f}cqh，离内容区下沿 {LIMIT_CQH:.1f}cqh 还空 "
            f"{LIMIT_CQH - content_floor_cqh:.1f}cqh > {hc.MAX_BOTTOM_DEAD_CQH}"
            "（法则 17 填幅）—— 竖屏下半部空转就是「模板感」"]


def judge(content_floor_cqh) -> list[str]:
    """两半合起来的完整判据（工具单独跑时用这条）。"""
    return intrude_only(content_floor_cqh) + fill_only(content_floor_cqh)


SHOT_RE = re.compile(
    r'class="clip"[^>]*?data-composition-id="(?P<cid>[^"]+)"[^>]*?'
    r'data-start="(?P<start>[\d.]+)"[^>]*?data-duration="(?P<dur>[\d.]+)"', re.S)
VALUES_RE = re.compile(r'data-variable-values="(?P<json>[^"]*)"')


def text_only_windows(index_html: Path) -> list[tuple[str, float]]:
    """从 index.html 取**无图镜**的时间窗（名字, 中点秒）。

    带图镜整条跳过，理由见模块 docstring。取中点：入场补间都在前 1.5s 内收完，
    中点必然是"内容就位"的那一帧。
    """
    text = index_html.read_text(encoding="utf-8")
    out = []
    for match in SHOT_RE.finditer(text):
        head = text[match.start(): match.start() + 4000]
        values = VALUES_RE.search(head)
        if values:
            # `data-variable-values` 里的 JSON 是 HTML 转义过的（`&quot;`），
            # 必须先 unescape 再 loads —— 直接子串匹配 "imagePath" 永远不成立，
            # 那样带图镜一条都不会被跳过（第一版就是这么错的，被自己的前提断言抓出来）。
            try:
                payload = json.loads(html.unescape(values.group("json")))
            except json.JSONDecodeError:
                payload = {}
            if str(payload.get("imagePath", "")).strip():
                continue
        start, dur = float(match.group("start")), float(match.group("dur"))
        out.append((match.group("cid"), round(start + dur / 2.0, 3)))
    return out


def measure_video(mp4: Path, keep_dir: Path | None = None) -> list[dict]:
    """逐**无图镜**量一条成片（取每镜中点那一帧）。普查与本工具共用这一份实现。"""
    import subprocess
    import tempfile
    windows = text_only_windows(mp4.parent / "index.html")
    tmp = keep_dir or Path(tempfile.mkdtemp(prefix="floor-"))
    tmp.mkdir(parents=True, exist_ok=True)
    out: list[dict] = []
    for name, at in windows:
        png = tmp / f"{mp4.parent.name}-{name}.png"
        subprocess.run(["ffmpeg", "-y", "-ss", str(at), "-i", str(mp4),
                        "-frames:v", "1", str(png)], check=True, capture_output=True)
        row = measure(png)
        row["shot"], row["at_s"] = name, at
        out.append(row)
        if keep_dir is None:
            png.unlink(missing_ok=True)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="量最底墨线（cqh）并判字幕区 / 法则 17 填幅")
    ap.add_argument("--png", nargs="*", type=Path, help="直接给帧图（各自独立判）")
    ap.add_argument("--video", type=Path, help="给一条 silent.mp4（同目录要有 index.html），逐无图镜量")
    ap.add_argument("--keep-frames", action="store_true", help="把抽出来的帧留在 --out 目录")
    ap.add_argument("--out", type=Path, default=None, help="帧输出目录（默认临时目录）")
    args = ap.parse_args(argv)

    print(f"口径：字幕区上沿 {ZONE_TOP_CQH:.1f}cqh · 填幅下界 {FILL_FLOOR_CQH:.1f}cqh "
          f"· 墨 = 对地面 ≥{INK_CONTRAST}:1")
    problems: list[str] = []
    for png in args.png or []:
        row = measure(png)
        got = judge(row["content_floor_cqh"])
        problems += [f"{png}: {p}" for p in got]
        print(f"  {png.name}: 地面 {row['ground_rgb']} 最底墨线 "
              f"{row['content_floor_cqh']}cqh  {'✗' if got else '✓'}")
    if args.video:
        rows = measure_video(args.video, args.out if args.keep_frames else None)
        if not rows:
            print(f"  {args.video.parent.name}: 没有可量的无图镜（全是带图镜？）")
            return 1
        for row in rows:
            got = judge(row["content_floor_cqh"])
            problems += [f"{args.video.parent.name}/{row['shot']}@{row['at_s']}s: {p}"
                         for p in got]
            print(f"  {args.video.parent.name}/{row['shot']} @{row['at_s']}s: "
                  f"地面 {row['ground_rgb']} 最底墨线 {row['content_floor_cqh']}cqh  "
                  f"{'✗' if got else '✓'}")
    if problems:
        print(f"\n内容下沿不过：{len(problems)} 条")
        for p in problems:
            print(f"  ✗ {p}")
        return 1
    print("\n内容下沿全部达标")
    return 0


if __name__ == "__main__":
    sys.exit(main())
