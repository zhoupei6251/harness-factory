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
import path_b_build as pb  # noqa: E402

ENV = dict(os.environ)
if N22:
    ENV["PATH"] = N22 + os.pathsep + ENV.get("PATH", "")
NPX = "npx.cmd" if os.name == "nt" else "npx"

TRACE = re.compile(r'"totalFrames":(\d+),"framesCompleted":(\d+)')
NOISE = re.compile(r"\bWARN\b|\bERROR\b")

KEEP.mkdir(parents=True, exist_ok=True)


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
                   clips=text.count('class="clip"'), vue=text.count("data-vue-mount"))

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
        row["pass"] = (row.get("emit_exit") == 0 and row.get("html")
                       and row.get("render_exit") == 0 and row.get("mp4_kb", 0) > 100
                       and row.get("warn") == 0
                       and row.get("frames", -1) > 0
                       and row.get("frames") == row.get("frames_done"))
    except Exception as exc:  # noqa: BLE001  普查里异常必须落表，不许静默
        row["pass"] = False
        row["error"] = f"{type(exc).__name__}: {exc}"
    (work / "row.json").write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    return row


rows = []
with cf.ThreadPoolExecutor(max_workers=WORKERS) as pool:
    for row in pool.map(one, pb.ALL_TEMPLATES):
        rows.append(row)
        (KEEP / "_results.jsonl").open("a", encoding="utf-8").close()
        print(json.dumps(row, ensure_ascii=False), flush=True)

(KEEP / "_results.jsonl").write_text(
    "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")

passed = [r for r in rows if r.get("pass")]
lines = [f"# 31 pack 画面轨真渲染普查（{len(passed)}/31 通过）", "",
         "稿件：`.harness-news-runtime/articles/t001-scenes.json`（5 镜）· 零配音（`--skip-render`）· "
         "25fps · draft · `--no-browser-gpu`", "",
         "| pack | clip | vue挂载 | render exit | 帧(完成/总) | mp4 KB | WARN/ERROR | 判定 |",
         "|---|---|---|---|---|---|---|---|"]
for r in rows:
    lines.append(f"| {r['pack']} | {r.get('clips')} | {r.get('vue')} | {r.get('render_exit')} "
                 f"| {r.get('frames_done')}/{r.get('frames')} | {r.get('mp4_kb')} "
                 f"| {r.get('warn')} | {'✅' if r.get('pass') else '❌ ' + str(r.get('error', ''))} |")
lines += ["", "每包产物在同目录 `<pack>/`：`silent.mp4` / `index.html` / `render.log` / `emit.log`。"]
(KEEP / "_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\n=== {len(passed)}/31 通过；汇总: {KEEP / '_summary.md'} ===")
for r in rows:
    if not r.get("pass"):
        print("  FAIL", r)
