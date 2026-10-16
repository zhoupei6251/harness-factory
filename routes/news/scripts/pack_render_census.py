"""31 个 pack 的画面轨真渲染普查 v2。

改 v1 的两处错：
  1. 判据 5 用 re.search 取了日志里**第一条** totalFrames/framesCompleted —— 那是
     capture 起点的 checkpoint（framesCompleted=0），于是所有包被误判 pass=false。
     现在取**最后一条**（assemble 终值），并另存 raw 供人复核。
  2. v1 跑完 rm -rf 临时目录，产物没处看。现在全部落在仓库运行期目录
     .harness-news-runtime/tmp/render-sweep-2026-10-14/<pack>/ 下，
     含 index.html / silent.mp4 / render.log / row.json，另有一份 _summary.md。

判据（逐包机检，全绿才算 pass）：
  emit_exit == 0 且 index.html 生成
  render_exit == 0
  silent.mp4 > 100 KB
  render.log 里 WARN/ERROR 计数 == 0
  终值 framesCompleted == totalFrames 且 > 0
  判据 6（2026-10-16 加）：无图镜最底墨线不许越过字幕区上沿 80cqh。
    填幅半边（法则 17 的 8cqh 线）**只报不判** —— 实测 31 包全在 54.7–58.0cqh，
    今天开成硬闸等于普查永久全红且没人修；它落在 _summary 的「填幅不足镜数」列上当账。
"""
import concurrent.futures as cf
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
#: 引擎要 Node>=22。留空就用 PATH 上的 node（`--doctor` 会报版本不够）。
N22 = os.environ.get("HF_NODE22_DIR", "")
SCRIPT = os.environ.get("HF_CENSUS_INPUT",
                        str(REPO / ".harness-news-runtime/articles/t001-scenes.json"))
KEEP = REPO / ".harness-news-runtime/tmp/render-census"
WORKERS = 3

sys.path.insert(0, str(REPO / "skills/douyin-pro/scripts"))
sys.path.insert(0, str(REPO / "routes/news/scripts"))
import path_b_build as pb  # noqa: E402
import content_floor  # noqa: E402  判据 6：内容下沿（像素口径，与工具共用同一实现）

ENV = dict(os.environ)
if N22:
    ENV["PATH"] = N22 + os.pathsep + ENV.get("PATH", "")
NPX = "npx.cmd" if os.name == "nt" else "npx"

TRACE = re.compile(r'"totalFrames":(\d+),"framesCompleted":(\d+)')
NOISE = re.compile(r"\bWARN\b|\bERROR\b")

#: 汇总行里的镜数与稿件路径一律现算 —— 手抄的"5 镜"在我把 field 镜加进清单的那一刻就会变成假话
#: （D20 治的是同一个病：没人断言的数字就是死数字）。
SCENES = json.loads(Path(SCRIPT).read_text(encoding="utf-8"))
import vue_contracts as _vc                      # noqa: E402
_VUE_ONLY_ROLES = {c["role"] for c in _vc.discover(pb.VUE_ENTRIES_DIR).values()}
N_POINTED = sum(1 for sc in SCENES if sc.get("layout"))
N_VUE_ONLY = sum(1 for sc in SCENES if sc.get("layout") in _VUE_ONLY_ROLES)

KEEP.mkdir(parents=True, exist_ok=True)

#: `--only <pack>` 只跑指定包（调试用）；`--list` 列出可跑的包。
_args = [a for a in sys.argv[1:]]
if "--list" in _args:
    print("\n".join(pb.ALL_TEMPLATES))
    raise SystemExit(0)
_only = _args[_args.index("--only") + 1] if "--only" in _args else None
PACKS = [p for p in pb.ALL_TEMPLATES if not _only or p == _only]
if _only and _only not in pb.ALL_TEMPLATES:
    raise SystemExit(f"--only {_only!r} 不在 ALL_TEMPLATES 里")

#: 预检 Node 版本：引擎硬门槛 `Node.js >= 22`，用 20 跑会 31 包全挂、白等十几分钟，
#: 而且失败原因藏在每包 render.log 里。当场拦在这里，附带修法。
_probe = subprocess.run([os.path.join(N22, "node.exe") if N22 else "node", "-v"],
                        capture_output=True, text=True)
if _probe.returncode != 0:
    raise SystemExit(f"找不到 node（{_probe.stderr.strip() or 'PATH 里没有 node'}）；"
                     "用 HF_NODE22_DIR=<Node22 目录> 指定")
_major = int(_probe.stdout.strip().lstrip("v").split(".")[0])
if _major < 22:
    hint = ("设 HF_NODE22_DIR=<Node22 目录> 重跑" if not N22
            else f"HF_NODE22_DIR 指向的 {_probe.stdout.strip()} 仍 < 22，换目录")
    raise SystemExit(f"Node {_probe.stdout.strip()} 过不了引擎门禁（要 >= 22）；{hint}")



def one(style: str) -> dict:
    work = KEEP / style
    work.mkdir(parents=True, exist_ok=True)
    row = {"pack": style}
    emit_log = work / "emit.log"
    rnd_log = work / "render.log"
    try:
        emit = subprocess.run(
            [sys.executable, str(REPO / "skills/douyin-pro/scripts/path_b_build.py"),
             "--input", SCRIPT, "--template", style, "--skip-render",
             "--work-dir", str(work), "--output", str(work / "final.mp4"),
             "--source", "央视新闻", "--kicker", "要闻速读"],
            capture_output=True, text=True, timeout=900, cwd=str(REPO))
        emit_log.write_text(emit.stdout + emit.stderr, encoding="utf-8")
        html = work / "index.html"
        text = html.read_text(encoding="utf-8") if html.is_file() else ""
        row.update(emit_exit=emit.returncode, html=html.is_file(),
                   clips=text.count('class="clip"'),
                   # 数 `data-vue-bundle` 而不是 `data-vue-mount`：后者还会出现在注入的
                   # loader 脚本里（`querySelectorAll("[data-vue-mount]")`），实测 2 个 Vue clip
                   # 会被数成 3 —— 列名是"挂载数"，多出来的那一次是选择器，不是挂载。
                   vue=text.count("data-vue-bundle"))

        if emit.returncode == 0 and html.is_file():
            rnd = subprocess.run(
                [NPX, "-y", "hyperframes", "render", "-c", "index.html",
                 "-o", "silent.mp4", "-f", "25", "--quality=draft", "--no-browser-gpu"],
                capture_output=True, text=True, timeout=2400, cwd=str(work), env=ENV)
            log = rnd.stdout + rnd.stderr
            rnd_log.write_text(log, encoding="utf-8")
            pairs = TRACE.findall(log)
            total, done = (int(pairs[-1][0]), int(pairs[-1][1])) if pairs else (-1, -1)
            mp4 = work / "silent.mp4"
            row.update(render_exit=rnd.returncode, warn=len(NOISE.findall(log)),
                       frames=total, frames_done=done,
                       mp4_kb=round(mp4.stat().st_size / 1024) if mp4.is_file() else 0)
            # 判据 6：内容下沿。字幕区是硬约束（越了就压字），填幅只报不判 ——
            # 实测 31 包的无图镜最底墨线全在 54.7–58.0cqh，一条都不过法则 17 的 8cqh 线，
            # 今天把它开成硬闸 = 普查永久全红且没人修；先落在表里当账（见 _summary 列）。
            mp4 = work / "silent.mp4"
            if mp4.is_file():
                floors = content_floor.measure_video(mp4)
                row["floor_worst"] = min((f["content_floor_cqh"] for f in floors),
                                         default=None)
                row["intrude"] = sum(1 for f in floors
                                     for p in content_floor.intrude_only(f["content_floor_cqh"]))
                row["thin_fill"] = sum(1 for f in floors
                                       if content_floor.fill_only(f["content_floor_cqh"]))
                row["floor_shots"] = len(floors)
        row["pass"] = (row.get("emit_exit") == 0 and row.get("html")
                       and row.get("render_exit") == 0 and row.get("mp4_kb", 0) > 100
                       and row.get("warn") == 0
                       and row.get("frames", -1) > 0
                       and row.get("frames") == row.get("frames_done")
                       and row.get("intrude", 0) == 0)
    except Exception as exc:  # noqa: BLE001  普查里异常必须落表，不许静默
        row["pass"] = False
        row["error"] = f"{type(exc).__name__}: {exc}"
    (work / "row.json").write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    return row


rows = []
# 逐行增量落盘：整轮普查十几分钟，v1 只在结尾写，中断即全丢。
with (KEEP / "_results.jsonl").open("w", encoding="utf-8") as sink, \
        cf.ThreadPoolExecutor(max_workers=WORKERS) as pool:
    for row in pool.map(one, PACKS):
        rows.append(row)
        sink.write(json.dumps(row, ensure_ascii=False) + "\n")
        sink.flush()
        print(json.dumps(row, ensure_ascii=False), flush=True)

passed = [r for r in rows if r.get("pass")]
lines = [f"# {len(PACKS)} pack 画面轨真渲染普查（{len(passed)}/{len(PACKS)} 通过）", "",
         f"稿件：`{Path(SCRIPT).relative_to(REPO).as_posix()}`"
         f"（{len(SCENES)} 镜，其中 {N_POINTED} 镜点名版式、"
         f"{N_VUE_ONLY} 镜走 Vue-only 契约）· 零配音（`--skip-render`）· "
         "25fps · draft · `--no-browser-gpu`", "",
         "| pack | clip | vue挂载 | render exit | 帧(完成/总) | mp4 KB | WARN/ERROR | "
         f"最底墨线(cqh) | 填幅不足镜数 | 判定 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    lines.append(f"| {r['pack']} | {r.get('clips')} | {r.get('vue')} | {r.get('render_exit')} "
                 f"| {r.get('frames_done')}/{r.get('frames')} | {r.get('mp4_kb')} "
                 f"| {r.get('warn')} | {r.get('floor_worst')} | {r.get('thin_fill')} "
                 f"| {'✅' if r.get('pass') else '❌ ' + str(r.get('error', ''))} |")
lines += ["", "每包产物在同目录 `<pack>/`：`silent.mp4` / `index.html` / `render.log` / `emit.log`。"]
(KEEP / "_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\n=== {len(passed)}/{len(PACKS)} 通过；汇总: {KEEP / '_summary.md'} ===")
for r in rows:
    if not r.get("pass"):
        print("  FAIL", r)
