"""静态支 vs Vue 支的像素对拍：同稿、同包、同 seek 点，逐点比 PSNR。

判据（两条都要满足，逐 seek 点）：
  1. `psnr_avg ≥ 38 dB`（`inf` = 逐像素全等）—— 只当"别明显变样"的下界。
  2. **行带对齐**：该包该角色的每个**声明槽色**在两支里的连续行段，逐段起终点差 ≤ 2px。

为什么这么分（2026-10-14 用户批准方案 A）：像素等同不是本产线的承诺 —— 已合入的
hook-a 同口径也只有 43–46 dB，说明「两支不逐像素等同」是 Vue 挂载路的固有性质
（多出 `.vue-target` 一层 + 容器查询单位），不是某次移植引入的回归。真正要守的是
**版式没动**，所以把"版式对齐"做成机检、把 PSNR 退成下界。
基线 = 同一台机器同一次运行里现产的静态支，**不是**普查留下的旧产物 ——
两支之间只允许「hook 走 Vue 还是走静态」这一个变量。

⚠️ 关于计划原文的第二条「maxdiff ≤ 2/255」：它没写口径（哪个通道、什么度量），
所以这里**不拿它当闸**，只把 `blend=difference` 后的 luma `YMAX` 记进结果供人看。
真要把它升级成闸，得先定口径（见 `_summary.md` 末尾的说明）。

非空过前提（每个包都验，不满足直接判 FAIL 而不是给个漂亮的 inf）：
静态支的 `index.html` 里 `data-vue-mount` 计数必须为 0、Vue 支必须 > 0。
否则两支其实是同一条路，比出来的 `inf` 毫无意义。

跑法（Node ≥ 22；一个包 = 两次真渲染，约 2–4 分钟）：
    HF_NODE22_DIR=<node22 目录> python routes/news/scripts/vue_pixel_ab.py
    python routes/news/scripts/vue_pixel_ab.py --packs news-coral,news-policy
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "skills" / "douyin-pro" / "scripts"
KEEP = REPO / ".harness-news-runtime/tmp/vue-pixel-ab"
N22 = os.environ.get("HF_NODE22_DIR", "")
NPX = "npx.cmd" if os.name == "nt" else "npx"

#: Phase 1 Task 5 的像素预算：hook 轮转到这 5 个包。
#: `news-policy` 是本次追加的第 6 个 —— 它是 hook-b 的源包，而 hook-b 一建出来，
#: news-policy 的 hook 就从「静默回落静态」变成真走 Vue，这是本轮唯一一处
#: **行为改变**，不测它等于没测这次提交。
PACKS_DEFAULT = ["news-coral", "news-world", "news-noir", "news-podcast",
                 "news-alert-warning", "news-policy"]

PSNR_STATS = re.compile(r"psnr_avg:([0-9.inf]+)")
YMAX = re.compile(r"lavfi\.signalstats\.YMAX=(\d+)")
#: 2026-10-14 用户批准（方案 A）：像素等同**不是**本产线的承诺，版式对齐才是。
#: 依据 —— 已合入的 hook-a 同口径也只有 43–46 dB，即「两支不逐像素等同」是 Vue
#: 挂载路的固有性质（多出 `.vue-target` 一层 + 容器查询单位），不是某次移植的回归。
#: 所以 PSNR 退成"别明显变样"的下界，真正的判据交给下面的行带对齐。
THRESHOLD_DB = 38.0
#: 行带配准：同一设计色的行剖面在两支间对齐所需的最佳整数垂直偏移上限。
BAND_MAX_SHIFT_PX = 2
#: 颜色匹配容差（三通道绝对差之和）与"一行算数"的最小像素数 —— 低于它的都是 AA 碎屑。
BAND_COLOR_TOL = 24
BAND_MIN_ROW_PX = 20
#: 搜索窗口；超出即判"偏移过大"，不当成"对不齐"而放过。
BAND_SEARCH_PX = 24


def _rgb(hex_str: str) -> tuple[int, int, int]:
    s = hex_str.lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def row_profile(img, target: tuple[int, int, int]):
    """该设计色的**行剖面**：每行命中像素数（低于 BAND_MIN_ROW_PX 记 0）。

    为什么是剖面而不是"连续段列表"：段列表在 AA 下天然碎成 1–8px 的小段，两支碎法
    不同就被判不等 —— 那是光栅化噪声，不是版式差异（首版就这么误红了 5 个包）。
    但也不能按段高过滤：**烫金线这种真元素只有 5px 高**，过滤会把它一起滤掉。
    剖面两头都占 —— 对 AA 稳，又不丢细元素。
    """
    import numpy as np

    mask = (np.abs(img - np.array(target)).sum(axis=2) < BAND_COLOR_TOL)
    prof = mask.sum(axis=1)
    prof[prof < BAND_MIN_ROW_PX] = 0
    return prof


def band_problems(a_path, b_path, colors) -> list[str]:
    """两支的行剖面逐色配准：偏移超阈值、或配准后形状残差超阈值，都点名。"""
    from PIL import Image
    import numpy as np

    a = np.asarray(Image.open(a_path).convert("RGB")).astype(int)
    b = np.asarray(Image.open(b_path).convert("RGB")).astype(int)
    out = []
    for hex_str in colors:
        pa, pb = row_profile(a, _rgb(hex_str)), row_profile(b, _rgb(hex_str))
        if pa.sum() == 0 and pb.sum() == 0:
            continue  # 该色这一帧根本没上屏，不构成差异
        # 只用**偏移**这一半，不用"配准后形状残差"。实测否掉了残差判据：
        # 真对（6 包 × 3 点）的归一化残差散布 0.001–0.232，而"抹掉整个辅助行"的
        # 反例只有 0.164–0.299 —— 两个分布重叠，任何阈值都分不开
        # （稀疏色如烫金线只有 5px 高，归一后 AA 噪声被放大到与真变化同量级）。
        # 而"元素消失"这一类由上面的 PSNR 闸以巨大量级覆盖：真对 43.6 dB，
        # 抹掉辅助行 20.7 dB，平移 10px 17.4 dB。
        best_shift, best_res = 0, None
        for s in range(-BAND_SEARCH_PX, BAND_SEARCH_PX + 1):
            q = np.roll(pb, s)
            if s > 0:
                q[:s] = 0
            elif s < 0:
                q[s:] = 0  # 滚出画面的边不许从另一端绕回来
            res = float(np.abs(pa - q).sum())
            if best_res is None or res < best_res:
                best_shift, best_res = s, res
        if abs(best_shift) > BAND_MAX_SHIFT_PX:
            out.append(f"{hex_str}: 行剖面最佳偏移 {best_shift}px > {BAND_MAX_SHIFT_PX}px")
    return out


sys.path.insert(0, str(SCRIPTS))
import path_b_build as pb  # noqa: E402
import pack_slots as pks  # noqa: E402

#: 本 Phase 只切了 hook 一个角色（`CUTOVER_ROLES`），对拍锚点就取它。
#: Phase 2 扩角色时这里跟着扩，一角色一条命令。
ROLE = "hook"

ENV = dict(os.environ)
if N22:
    ENV["PATH"] = N22 + os.pathsep + ENV.get("PATH", "")


def _run(cmd: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True,
                          timeout=timeout, cwd=str(cwd), env=ENV)


def emit(pack: str, arm: str, work: Path, script: str) -> Path:
    """产出一支的 index.html。arm="vue" 走现路由；arm="static" 把 CUTOVER_ROLES 清空。

    静态支用临时 bootstrap 脚本清路由，而不是给发射器加一个"关掉 Vue"的旗标：
    那个旗标在生产里没有任何合法用法，加上去只是给误配留门。
    """
    work.mkdir(parents=True, exist_ok=True)
    common = ["--input", script, "--template", pack, "--skip-render",
              "--work-dir", str(work), "--output", str(work / "final.mp4"),
              "--source", "央视新闻", "--kicker", "要闻速读"]
    if arm == "vue":
        cmd = [sys.executable, str(SCRIPTS / "path_b_build.py"), *common]
    else:
        boot = work / "_emit_static.py"
        boot.write_text(
            "import sys\n"
            f"sys.argv = ['path_b_build.py', *{common!r}]\n"
            f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
            "import path_b_build as pb\n"
            "pb.CUTOVER_ROLES = set()   # 整支回落静态：hook 不再路由到 Vue\n"
            "pb.main()\n",
            encoding="utf-8")
        cmd = [sys.executable, str(boot)]
    res = _run(cmd, REPO, 900)
    (work / "emit.log").write_text(res.stdout + res.stderr, encoding="utf-8")
    html = work / "index.html"
    if res.returncode != 0 or not html.is_file():
        raise RuntimeError(f"{pack}/{arm} 发射失败 exit={res.returncode} html={html.is_file()}")
    return html


def render(work: Path) -> Path:
    """画面轨真渲染（零配音：`--skip-render` 已把配音整段跳过）。"""
    res = _run([NPX, "-y", "hyperframes", "render", "-c", "index.html",
                "-o", "arm.mp4", "-f", "25", "--quality=draft", "--no-browser-gpu"],
               work, 2400)
    (work / "render.log").write_text(res.stdout + res.stderr, encoding="utf-8")
    mp4 = work / "arm.mp4"
    if res.returncode != 0 or not mp4.is_file():
        raise RuntimeError(f"{work.name} 渲染失败 exit={res.returncode}")
    return mp4


def frame(mp4: Path, at: float, out: Path) -> Path:
    res = _run(["ffmpeg", "-v", "error", "-y", "-ss", str(at), "-i", str(mp4),
                "-frames:v", "1", str(out)], REPO, 120)
    if res.returncode != 0 or not out.is_file():
        raise RuntimeError(f"取帧失败 t={at} {res.stderr[:200]}")
    return out


def compare(a: Path, b: Path) -> tuple[float, int]:
    """返回 (psnr_avg_dB, luma YMAX)。全等时 psnr 为 inf。"""
    res = _run(["ffmpeg", "-hide_banner", "-i", str(a), "-i", str(b),
                "-lavfi", "psnr=stats_file=-", "-f", "null", "-"], REPO, 120)
    text = res.stdout + res.stderr
    m = PSNR_STATS.search(text)
    if not m:
        raise RuntimeError(f"psnr 解析不出: {text[-300:]}")
    db = float("inf") if m.group(1) == "inf" else float(m.group(1))
    d = _run(["ffmpeg", "-hide_banner", "-i", str(a), "-i", str(b), "-lavfi",
              "[0:v][1:v]blend=all_mode=difference,format=gray,signalstats,"
              "metadata=print:key=lavfi.signalstats.YMAX", "-f", "null", "-"],
             REPO, 120)
    y = YMAX.search(d.stdout + d.stderr)
    if not y:
        raise RuntimeError(f"YMAX 解析不出: {(d.stdout + d.stderr)[-300:]}")
    return db, int(y.group(1))


def one(pack: str, seeks: list[float], script: str) -> dict:
    row: dict = {"pack": pack, "arm_mounts": {}}
    try:
        mp4s = {}
        for arm in ("static", "vue"):
            html = emit(pack, arm, KEEP / pack / arm, script)
            text = html.read_text(encoding="utf-8")
            row["arm_mounts"][arm] = text.count("data-vue-mount")
            mp4s[arm] = render(KEEP / pack / arm)
        # 非空过：两支必须真的不同路，否则 inf 是假的
        assert row["arm_mounts"]["static"] == 0, \
            f"静态支仍带 Vue 挂载 {row['arm_mounts']} —— 对拍无效"
        assert row["arm_mounts"]["vue"] > 0, \
            f"Vue 支没有 Vue 挂载 {row['arm_mounts']} —— 路由没生效，对拍无效"
        points = []
        for t in seeks:
            fa = frame(mp4s["static"], t, KEEP / pack / f"a-{t}.png")
            fb = frame(mp4s["vue"], t, KEEP / pack / f"b-{t}.png")
            db, ymax = compare(fa, fb)
            # 行带对齐：颜色锚点取自该包该角色的**声明槽色**（设计系统真源，不是手挑）
            hexes = pks.template_of(pack, ROLE)[1]
            decl_colors = sorted({hexes[i] for i in pks.declaration_slot_indices(
                pks.read_raw(pack, ROLE))})
            bands = band_problems(fa, fb, decl_colors)
            points.append({"t": t, "psnr_db": db, "luma_maxdiff": ymax,
                           "bands_aligned": not bands,
                           "band_problems": bands,
                           "ok": db >= THRESHOLD_DB and not bands})
        row["points"] = points
        row["pass"] = all(p["ok"] for p in points)
    except Exception as exc:  # noqa: BLE001  对拍里异常必须落表，不许静默
        row["pass"] = False
        row["error"] = f"{type(exc).__name__}: {exc}"
    (KEEP / pack / "row.json").parent.mkdir(parents=True, exist_ok=True)
    (KEEP / pack / "row.json").write_text(json.dumps(row, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description="静态支 vs Vue 支像素对拍")
    ap.add_argument("--packs", default=",".join(PACKS_DEFAULT))
    ap.add_argument("--seeks", default="0.5,2.0,3.5", help="逗号分隔的秒数")
    ap.add_argument("--input", default=str(REPO / ".harness-news-runtime/articles/t001-scenes.json"))
    ap.add_argument("--jobs", type=int, default=3)
    args = ap.parse_args()

    packs = [p.strip() for p in args.packs.split(",") if p.strip()]
    unknown = [p for p in packs if p not in pb.ALL_TEMPLATES]
    if unknown:
        raise SystemExit(f"包名不在 ALL_TEMPLATES 里: {unknown}")
    if not Path(args.input).is_file():
        raise SystemExit(f"稿件不存在: {args.input}")
    probe = subprocess.run([os.path.join(N22, "node.exe") if N22 else "node", "-v"],
                           capture_output=True, text=True)
    if probe.returncode != 0:
        raise SystemExit("找不到 node；用 HF_NODE22_DIR=<Node22 目录> 指定")
    major = int(probe.stdout.strip().lstrip("v").split(".")[0])
    if major < 22:
        raise SystemExit(f"Node {probe.stdout.strip()} 过不了引擎门禁（要 >= 22）；"
                         "设 HF_NODE22_DIR 后重跑")
    seeks = [float(s) for s in args.seeks.split(",") if s.strip()]

    KEEP.mkdir(parents=True, exist_ok=True)
    rows = []
    with cf.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for row in pool.map(lambda p: one(p, seeks, args.input), packs):
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)

    passed = [r for r in rows if r.get("pass")]
    lines = [f"# hook 像素对拍：静态支 vs Vue 支（{len(passed)}/{len(rows)} 通过）", "",
             f"稿件 `{Path(args.input).name}` · 零配音 · 25fps · draft · `--no-browser-gpu`",
             f"闸（两条都要满足）：每个 seek 点 `psnr_avg ≥ {THRESHOLD_DB:.0f} dB` **且** "
             f"声明槽色行带逐段对齐 ≤ {BAND_MAX_SHIFT_PX}px", "",
             "| pack | 静态支 vue挂载 | Vue 支 vue挂载 | " +
             " | ".join(f"t={s}s dB/lumaΔ/带" for s in seeks) + " | 判定 |",
             "|---|---|---|" + "---|" * len(seeks) + "---|"]
    for r in rows:
        cells = " | ".join(f"{p['psnr_db']} / {p['luma_maxdiff']} / "
                           f"{'✅' if p['bands_aligned'] else '❌'}"
                           for p in r.get("points", []))
        verdict = "✅" if r.get("pass") else "❌ " + str(r.get("error") or "见 band_problems")
        m = r.get("arm_mounts", {})
        lines.append(f"| {r['pack']} | {m.get('static')} | {m.get('vue')} | {cells} | {verdict} |")
    lines += ["",
              "## 口径说明",
              "",
              "- `lumaΔ` 是 `blend=difference` 后 gray 的 `signalstats.YMAX`，**只覆盖亮度**，",
              "  不是计划原文那句没写口径的 `maxdiff ≤ 2/255`。它现在只是参考列。",
              "- 两支都由本脚本同一次运行现产；`arm_mounts` 两列证明两支确实走了不同的路。",
              "- 行带锚点 = 该包该角色的**声明槽色**（`pack_slots.declaration_slot_indices`），",
              "  不是人挑的色。判据双向验过：真对（6 包）放行、整体平移 10px 逐色抓到。",
              "- **没有**用「配准后形状残差」当闸：实测真对残差 0.001–0.232 与「抹掉整个辅助行」",
              "  的 0.164–0.299 重叠，分不开；而元素消失由 PSNR 覆盖（真对 43.6 dB vs 20.7 dB）。",
              ""]
    (KEEP / "_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n=== {len(passed)}/{len(rows)} 通过；汇总 {KEEP / '_summary.md'} ===")
    return 0 if len(passed) == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
