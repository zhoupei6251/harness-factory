#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AIGC 显式角标 · 真像素复测器 —— 文档里的角标像素数只认它。

为什么存在: `routes/news/ARCHITECTURE.md` D8/§8 写着「字芯 55px = 最短边 5.09%、
墨迹 1550–1615、开场 4 秒、距底落在底部 20cqh 禁入带内」。这几个数是**合规判据**
而不是排版喜好, 手抄一次就开始漂(同一天 frame.md 复算抓到 42 处假实测值, 见 D10)。
本脚本从一次真实渲染的产物里把它们重新量一遍, 于是「文档数字」变成可执行命令。

    python skills/douyin-pro/scripts/verify_aigc_badge.py \
        --work  <path_b_build 的工作目录> \
        --video <烧完字幕与角标的成片>

`--work` 要含 `subs.ass`(实际烧进去的那份 ASS)与 `silent.mp4`(烧 ASS **之前**的
画面)—— 两者都是发射器第 ⑥/⑧ 步的中间产物, 渲染时指一个固定的 `--work-dir` 就留下。

三项检查, 全部以真实像素为准, 不拿模型自证:

  1 **字芯**  把成片用的同一份 ASS 里只留 AIGC 一条, 在纯黑画布上单独烧一帧。
              白色像素的纵向范围就是字芯(描边是黑的, 不计)。国标量的是**字形实际
              高度**, 所以 5% 这条线必须用字芯比 —— 用含描边的整体墨迹会把 65.7px
              当成 54.7px, 白捡 11px 假余量。
  2 **几何**  同一帧(取自 silent)分别烧 `subs.ass` 与「删掉 AIGC 条」的 ASS 再相减:
              字幕完全抵消, 剩下的就是角标墨迹 bbox。逐侧与
              `path_b_build.aigc_badge_ink_bounds` 比, 容差 INK_TOL_PX。
              **这一项是模型对渲染的核对** —— 2026-09-29 那次底边距算错 8px
              (行盒下空白没扣)是在这里暴露的, 不是读代码读出来的。
  3 **时序**  每个采样点取成片一帧、silent 一帧, silent 那帧再烧一遍**删掉 AIGC 条**
              的 ASS 作基准, 然后在实测墨迹 bbox 内数差异像素: 窗口内必须大面积在变,
              窗口外必须几乎为零。**基准必须是"有字幕、无角标"而不是裸 silent** ——
              角标 bbox 落在字幕带上, 裸 silent 少的是整行字幕, 量到的差异会把字幕算进
              角标(2026-09-29 用 43.0s 探针实测: 窗口外 23.50s 处差 8.5%, 全是字幕笔画)。

依赖: ffmpeg / ffprobe(走 `path_b_build.which()` 解析)、Pillow(量像素)。
退出码: 0 三项全过; 1 任一项不符或产物缺失(打印具体差值, 不静默跳过)。
"""

import argparse
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import path_b_build as pb  # noqa: E402  与发射器共用同一套几何函数, 不许在此重算

try:
    from PIL import Image, ImageChops
except ImportError:  # pragma: no cover
    raise SystemExit("[aigc_badge] 需要 Pillow(逐像素量字芯/墨迹): pip install pillow")

#: 实测墨迹与模型墨迹允许的逐侧偏差(像素)。抗锯齿让白字芯外多算 0–1px, 1.5 是
#: 观测上限(2026-09-29 复测: 上侧 0.7 / 下侧 0.0)。**超过就是几何式子错了**,
#: 不是"差不多" —— 旧模型少扣 8px 行盒空白正落在这个量级上。
INK_TOL_PX = 1.5
#: bbox 内差异像素占 bbox 面积的比例判据: 窗口内 >15% 判「角标在」,
#: 窗口外 <1% 判「角标不在」。两阈值之间留空档, 落进去就是「半」, 按失败处理。
ON_RATIO = 0.15
OFF_RATIO = 0.01
#: 像素比较容差: 同一画面经两次编码的噪声远小于它, 角标笔画的差远大于它。
PX_EPS = 24
#: 纯黑画布上 min(R,G,B) ≥ 此值 = 不透明白色字芯本体(描边黑、阴影黑, 都不会命中)。
WHITE_MIN = 200


def die(msg: str) -> None:
    raise SystemExit(f"[aigc_badge] {msg}")


def ff_bin(tool: str) -> str:
    p = pb.which(tool)
    if not p:
        die(f"找不到 {tool}(PATH 未命中)—— 装 ffmpeg 或把它加进 PATH")
    return p


def probe_size(video: str) -> tuple[int, int]:
    """成片真实像素尺寸 —— 国标 5% 量的是这个, 不是 ASS 的 PlayRes。"""
    out = subprocess.check_output(
        [ff_bin("ffprobe"), "-v", "error", "-show_entries", "stream=width,height",
         "-of", "default=noprint_wrappers=1:nokey=1", video],
        stderr=subprocess.DEVNULL).decode().split()
    if len(out) < 2:
        die(f"ffprobe 取不到 {video} 的宽高")
    return int(out[0]), int(out[1])


def probe_duration(video: str) -> float:
    d = pb.ffprobe_duration(video)
    if d is None:
        die(f"ffprobe 取不到 {video} 的时长")
    return d


def ass_rows(text: str, section: str) -> list[dict]:
    """把 ASS 的 [V4+ Styles]/[Events] 段按各自 Format 行解成 dict 列表。

    只切逗号 —— 这两段的取值里不含逗号(颜色是 &HRRGGBBAA, 时间是 0:00:04.00);
    每行按 Format 列数**上限**切, 保住事件文本里的逗号。
    """
    lines = text.splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == section)
    except StopIteration:
        die(f"ASS 里没有 {section} 段")
    fmt = next((l for l in lines[start:] if l.startswith("Format:")), None)
    if not fmt:
        die(f"{section} 段缺 Format 行")
    fields = [f.strip() for f in fmt.split(":", 1)[1].split(",")]
    tag = "Style:" if section == "[V4+ Styles]" else "Dialogue:"
    rows = []
    for line in lines[start + 1:]:          # 段头本身要跳过, 否则会被当注释break掉
        if line.startswith("["):
            break
        if not line.startswith(tag):
            continue
        vals = line.split(":", 1)[1]        # 首个冒号就是 `Style:`/`Dialogue:` 的那个
        parts = [p.strip() for p in vals.split(",", len(fields) - 1)]
        rows.append(dict(zip(fields, parts)))
    return rows


def aigc_dialogue(text: str) -> dict:
    rows = [r for r in ass_rows(text, "[Events]") if r.get("Style") == "AIGC"]
    if not rows:
        die("成片 ASS 里没有 AIGC 事件 —— 显式标识根本没烧, 不必再量像素")
    if len(rows) > 1:
        die(f"AIGC 事件有 {len(rows)} 条, 本判据只覆盖单条开场角标")
    return rows[0]


def hms_to_s(v: str) -> float:
    h, m, rest = v.split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def frame(ff: str, src: str, t: float, out: str) -> Image.Image:
    """取 src 在 t 秒的一帧。`-ss` 放在 `-i` 前(快 seek), 同刻取两份可比。"""
    p = subprocess.run([ff, "-loglevel", "error", "-y", "-ss", f"{t:.3f}",
                        "-i", src, "-frames:v", "1", out],
                       capture_output=True, text=True)
    if p.returncode or not os.path.exists(out):
        die(f"抽帧失败 {os.path.basename(src)}@{t:.1f}s: {p.stderr[-400:]}")
    return Image.open(out).convert("RGB")


def write_variant(ass_text: str, path: str, *, keep_aigc: bool,
                  only_aigc: bool) -> None:
    """从真 ASS 派生对照版本(样式表一行不改, 只增删事件行)。

    keep_aigc=False → 删掉 AIGC 事件: 几何对照, 烧与不烧相减后只剩角标墨迹
    only_aigc=True  → 只留 AIGC 事件: 黑底上除了它什么都没有, 白像素即字芯
    派生文件与成片必须共用同一份样式, 否则量到的就不是成片里那个角标。
    """
    out = []
    for ln in ass_text.splitlines():
        if ln.startswith("Dialogue:"):
            is_aigc = ",AIGC," in ln
            if only_aigc and not is_aigc:
                continue
            if not keep_aigc and is_aigc:
                continue
        out.append(ln)
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")


def burn(ff: str, ass: str, out: str, base: list[str], tmp: str,
         label: str) -> Image.Image:
    """把 ass 烧到指定底图上的一帧, 返回 RGB。"""
    vf = os.path.join(tmp, f"vf_{label}.txt")
    open(vf, "w", encoding="utf-8").write(f"subtitles={pb.ffmpeg_sub_path(ass)}\n")
    p = subprocess.run([ff, "-loglevel", "error", "-y", *base,
                        "-filter_script:v", vf, "-frames:v", "1", out],
                       capture_output=True, text=True)
    if p.returncode:
        die(f"烧录失败({label}): {p.stderr[-500:]}")
    return Image.open(out).convert("RGB")


def burn_at(ff: str, ass: str, src: str, t: float, out: str, tmp: str,
            label: str) -> Image.Image:
    """把 ass 烧到 **src 在 t 秒那一帧**上(字幕时间轴与成片同刻)。

    不能先抽静帧再对静帧烧: 静帧输入的时间轴从 0 起算, libass 按 local t=0 选字幕,
    烧上去的就不是 t 秒那一行(2026-09-29 实测: 那样得到的基准帧与裸抽帧**逐像素相同**,
    于是 t=23.50s 的 2454 个差异像素全被算成角标, 而同一时刻的真值是 3px)。
    这里让 ffmpeg 一路解码到 t(`select='gte(t,…)'`)再出第一帧, 字幕与成片同刻。
    """
    vf = os.path.join(tmp, f"vf_{label}.txt")
    open(vf, "w", encoding="utf-8").write(
        f"subtitles={pb.ffmpeg_sub_path(ass)},"
        f"select='gte(t\\,{t:.3f})'\n")
    p = subprocess.run([ff, "-loglevel", "error", "-y", "-i", src,
                        "-filter_script:v", vf, "-frames:v", "1", out],
                       capture_output=True, text=True)
    if p.returncode or not os.path.exists(out):
        die(f"同时刻烧录失败({label}): {p.stderr[-500:]}")
    return Image.open(out).convert("RGB")


def _per_channel(img: Image.Image, op) -> Image.Image:
    """三通道两两取 min/max → 单通道灰度图。

    判据要的语义是**逐像素的 min(R,G,B) / max(R,G,B)**, 不是亮度: `convert("L")`
    给的是加权和, 一个 (255,255,0) 的黄点会被算成 ~226, 量白字芯时就把非白像素算了进去。
    """
    ch = img.split()
    return op(op(ch[0], ch[1]), ch[2])


def _bbox(img: Image.Image, keep) -> tuple[int, int, int, int]:
    """二值化后取包围盒, 返回闭区间 (x0,x1,y0,y1)(PIL 的 bbox 右/下是开区间)。"""
    box = img.point(lambda p: 255 if keep(p) else 0).getbbox()
    if not box:
        return ()
    return box[0], box[2] - 1, box[1], box[3] - 1


def white_extent(img: Image.Image) -> tuple[int, int, int, int]:
    """min(R,G,B) ≥ WHITE_MIN 的像素范围 —— 黑底单烧时这就是字芯。"""
    out = _bbox(_per_channel(img, ImageChops.darker), lambda p: p >= WHITE_MIN)
    if not out:
        die("黑底烧录后量不到白色像素(字体缺失? AIGC 样式没生效?)")
    return out


def diff_bbox(a: Image.Image, b: Image.Image) -> tuple[int, int, int, int]:
    """两帧相减 → 逐像素取三通道最大值 → 超阈值的范围 = 只有角标在变的那块墨迹。

    用通道合成 + getbbox() 而不是 Python 双层循环: 1080×1920 逐像素 getpixel 要几十秒,
    同一段判据没有理由慢到没人愿意跑(全帧扫还避开"角标外先变了"的漏检)。
    """
    out = _bbox(_per_channel(ImageChops.difference(a, b), ImageChops.lighter),
                lambda p: p > PX_EPS)
    if not out:
        die("烧与不烧同一帧**毫无差异** —— 角标根本没画出来")
    return out


def count_diff(a: Image.Image, b: Image.Image, box: tuple[int, int, int, int]) -> int:
    d = _per_channel(ImageChops.difference(a.crop(box), b.crop(box)), ImageChops.lighter)
    return d.point(lambda p: 1 if p > PX_EPS else 0).tobytes().count(1)


def main() -> int:
    ap = argparse.ArgumentParser(description="AIGC 角标真像素复测")
    ap.add_argument("--work", required=True, help="含 subs.ass 与 silent.mp4 的工作目录")
    ap.add_argument("--video", required=True, help="成片(final.mp4 / probe.mp4)")
    ap.add_argument("--keep-frames", action="store_true",
                    help="保留 <work>/verify/ 下的中间帧(默认跑完删掉)")
    args = ap.parse_args()

    ass_path = os.path.join(args.work, "subs.ass")
    silent = os.path.join(args.work, "silent.mp4")
    for p in (ass_path, silent, args.video):
        if not os.path.exists(p):
            die(f"缺产物: {p}")
    ass_text = open(ass_path, encoding="utf-8").read()
    ff = ff_bin("ffmpeg")
    tmp = os.path.join(args.work, "verify")
    os.makedirs(tmp, exist_ok=True)

    w, h = probe_size(args.video)
    dur = probe_duration(args.video)
    sdur = probe_duration(silent)
    usable = min(dur, sdur)          # 采样点不许落在任一文件末尾之外
    styles = [r for r in ass_rows(ass_text, "[V4+ Styles]") if r.get("Name") == "AIGC"]
    if not styles:
        die("ASS 样式表里没有 AIGC 样式")
    style = styles[0]
    ev = aigc_dialogue(ass_text)
    fs = int(style["Fontsize"])
    ol = int(style["Outline"])
    sh = int(style["Shadow"])
    mv = int(style["MarginV"])
    ml = int(style["MarginL"])
    t0 = hms_to_s(ev["Start"])
    t1 = hms_to_s(ev["End"])
    shown = t1 - t0

    fails: list[str] = []
    print(f"[aigc_badge] 成片 {os.path.basename(args.video)} {w}×{h} · {dur:.1f}s "
          f"(silent {sdur:.1f}s)")
    print(f"[aigc_badge] ASS: 字号 {fs} 描边 {ol} 阴影 {sh} "
          f"对齐 {style['Alignment']}(1=左下) MarginL {ml} MarginV {mv} "
          f"窗口 {t0:.2f}–{t1:.2f}s")
    model_mv = pb.aigc_badge_margin_v(w, h)
    if mv != model_mv:
        print(f"[aigc_badge] ⚠️ MarginV 成片 {mv} ≠ 当前模型 {model_mv} → "
              f"成片由旧代码渲染; 下面按成片里的 {mv} 比模型墨迹")

    # ---- 1 字芯: 黑底单烧, 只留 AIGC 一条 ----
    core_ass = os.path.join(tmp, "aigc_only.ass")
    write_variant(ass_text, core_ass, keep_aigc=True, only_aigc=True)
    core = burn(ff, core_ass, os.path.join(tmp, "core.png"),
                ["-f", "lavfi", "-i", f"color=black:s={w}x{h}:d=1"], tmp, "core")
    cx0, cx1, cy0, cy1 = white_extent(core)
    glyph = cy1 - cy0 + 1
    short = min(w, h)
    floor_px = short * pb.AIGC_LABEL_FLOOR_FRAC
    dist_bottom_cqh = (h - 1 - cy1) / h * 100
    print(f"\n[1 字芯] 白色像素 x {cx0}–{cx1}={cx1 - cx0 + 1}px · y {cy0}–{cy1}={glyph}px")
    print(f"[1 字芯] 最短边 {short} 的 {glyph / short * 100:.2f}% | 5% 线 {floor_px:.1f}px")
    print(f"[1 字芯] 距左 {cx0}px = {cx0 / w * 100:.2f}cqw(ASS MarginL {ml} → 模型 "
          f"{int(w * pb.AIGC_LABEL_MARGIN_W_FRAC)}px) | 距底 {h - 1 - cy1}px = "
          f"{dist_bottom_cqh:.2f}cqh")
    if glyph < floor_px:
        fails.append(f"字芯 {glyph}px 低于最短边 5% 线 {floor_px:.1f}px → 不合规")
    if dist_bottom_cqh >= 20.0:
        fails.append(f"角标距底 {dist_bottom_cqh:.2f}cqh, 已不在底部 20cqh 带内 —— "
                     "「边角位置」要重新确认")

    # ---- 2 几何: 同一帧烧与不烧相减 ----
    full_ass = os.path.join(tmp, "no_aigc.ass")
    write_variant(ass_text, full_ass, keep_aigc=False, only_aigc=False)
    base_t = min(t0 + 0.2, (t0 + t1) / 2)
    base_png = os.path.join(tmp, "base.png")
    frame(ff, silent, base_t, base_png)
    with_b = burn(ff, ass_path, os.path.join(tmp, "with.png"),
                  ["-i", base_png], tmp, "with")
    without_b = burn(ff, full_ass, os.path.join(tmp, "without.png"),
                     ["-i", base_png], tmp, "without")
    dx0, dx1, dy0, dy1 = diff_bbox(with_b, without_b)
    ink_top, ink_bottom = pb.aigc_badge_ink_bounds(w, h, mv)
    print(f"\n[2 几何] 实测墨迹(含描边阴影) x {dx0}–{dx1} · y {dy0}–{dy1} "
          f"= {dy1 - dy0 + 1}px")
    print(f"[2 几何] 模型 ink_bounds(mv={mv}) = {ink_top:.1f}–{ink_bottom:.1f} "
          f"| 上侧差 {abs(dy0 - ink_top):.1f}px 下侧差 {abs(dy1 - ink_bottom):.1f}px")
    for side, measured, modelled in (("上", dy0, ink_top), ("下", dy1, ink_bottom)):
        if abs(measured - modelled) > INK_TOL_PX:
            fails.append(f"墨迹{side}侧实测 {measured} 与模型 {modelled:.1f} 差 "
                         f"{abs(measured - modelled):.1f}px > 容差 {INK_TOL_PX}px")

    # ---- 3 时序 ----
    box = (dx0, dy0, dx1 + 1, dy1 + 1)
    area = (box[2] - box[0]) * (box[3] - box[1])
    print(f"\n[3 时序] 基准 = silent 同刻帧重烧「无 AIGC 条」ASS vs 成片 · "
          f"bbox {box} = {area}px")
    print(f"{'时刻':>9} | {'bbox 差异':>10} | {'占比':>7} | 判定")
    inside = sorted({round(t0 + 0.2, 2), round((t0 + t1) / 2, 2), round(t1 - 0.15, 2)})
    outside = ([round(t1 + 0.2, 2), round((t1 + usable) / 2, 2), round(usable - 0.2, 2)]
               if usable - t1 > 0.6 else [])
    if not outside:
        print(f"[3 时序] ⚠️ 角标窗口 [{t0:.2f},{t1:.2f}] 贴到片尾({usable:.1f}s), "
              "没有窗口外采样点 —— 只验了「在」, 没验「不在」")
    for t, expect in [(x, True) for x in inside] + [(x, False) for x in outside]:
        if not (0 <= t <= usable - 0.15):
            continue
        a = frame(ff, args.video, t, os.path.join(tmp, f"v{t}.png"))
        b = burn_at(ff, full_ass, silent, t, os.path.join(tmp, f"b{t}.png"),
                    tmp, f"b{t}")
        n = count_diff(a, b, box)
        ratio = n / area
        got = ratio > ON_RATIO
        half = OFF_RATIO <= ratio <= ON_RATIO
        verdict = "半?" if half else ("角标在" if got else "角标不在")
        mark = "✓" if not half and got == expect else \
            f"✗ 期望{'在' if expect else '不在'}"
        print(f"t={t:>7.2f}s | {n:>10} | {ratio * 100:>6.1f}% | {verdict}  {mark}")
        if half:
            fails.append(f"t={t:.2f}s 差异占比 {ratio * 100:.1f}% 落在判据空档 "
                         f"[{OFF_RATIO * 100:.0f}%, {ON_RATIO * 100:.0f}%] —— "
                         "角标在不在判不出来, 按失败处理")
        elif got != expect:
            fails.append(f"t={t:.2f}s 期望角标{'在' if expect else '不在'}, "
                         f"实测差异占比 {ratio * 100:.1f}%")

    print()
    if fails:
        for f in fails:
            print(f"[aigc_badge] ✗ {f}")
        return 1
    print(f"[aigc_badge] ✓ 三项全过: 字芯 {glyph}px({glyph / short * 100:.2f}% ≥ 5%) · "
          f"墨迹与模型逐侧 ≤{INK_TOL_PX}px · 角标只在开场 {shown:.1f}s 出现")
    if not args.keep_frames:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
