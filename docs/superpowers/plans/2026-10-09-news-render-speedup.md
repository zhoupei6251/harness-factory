# 新闻域出片提速（吞吐摊薄 ≤ 3 分钟/条）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把「脚本定稿 → 成片 mp4」的批量吞吐摊薄到 ≤ 3 分钟/条（零云费不变）。

**Architecture:** 保 hyperframes 渲染链路不动，做三件事：① 分段计时立基线；② hyperframes 可执行定位（消掉每次 `npx -y` 重装 5-15 分钟）；③ `batch_render.py` N 路并行发射（失败隔离）。字体开销由实测数据决定处置分支。阶段 0 有决策门：热跑单条 > 12 分钟即停，转方案 B 评估。

**Tech Stack:** Python 3.10+（stdlib）、hyperframes 0.8.141（npx 缓存已有）、edge-tts、ffmpeg。

**规格来源:** `docs/superpowers/specs/2026-10-09-news-render-speedup-design.md`（已批准）

**环境注意（本仓库实况）:**
- 测试框架是自研 selftest（`def t_*` 函数 + `check()` 运行器），不是 pytest。`path_b_selftest.py` 末段从 `globals()` 收集 `t_*` 执行，加测试函数即自动入列。
- 所有命令在 PowerShell 跑：**用 `;` 串联，不用 `&&`**（本机 PS 不支持）。
- 全程简体中文注释与提交信息；提交风格见 `git log`（`feat(news): …` / `docs(news): …`）。
- 不改 32 pack 模板资产；不放松任何闸门。

---

## File Structure

| 文件 | 动作 | 职责 |
|------|------|------|
| `skills/douyin-pro/scripts/path_b_build.py` | 修改 | 计时埋点（`timed` / `write_timings` / `--timing-out`）；hyperframes 可执行定位（`hyperframes_candidates` / `resolve_hyperframes` / `hf_init` / `hf_argv` / `--hyperframes-bin`）；替换 3 处写死的 `npx -y hyperframes` 调用点 |
| `skills/douyin-pro/scripts/path_b_selftest.py` | 修改 | 新增 4 条断言（探针顺序与回落、调用点不写死 npx、计时落盘） |
| `routes/news/scripts/batch_render.py` | 新建 | 批量并行发射器：清单解析、命令拼装、N 路并发、失败隔离、摊薄汇总 |
| `routes/news/scripts/batch_render_selftest.py` | 新建 | `batch_render` 纯离线断言集（5 条） |
| `routes/news/RUNBOOK-first-run.md` | 修改 | 验收后回写 P0 #1/#2/#3 状态（#3 的"没查 edge-tts"陈述已过期，见 Task 6） |
| `routes/news/MEMORY.md` | 修改 | 验收后回写提速状态与摊薄实测值 |
| `.harness-news-runtime/tmp/timing/*.json` | 产出 | 冷/热跑分段计时报告（gitignore 内，一次性跑动产物） |
| `.harness-news-runtime/verifications/2026-10-09-render-speedup-*.md` | 产出 | 吞吐验收验证单（**契约证据，`git add -f` 拉进版本管理**） |

---

### Task 1: 渲染链路分段计时埋点

**Files:**
- Modify: `skills/douyin-pro/scripts/path_b_build.py`（imports 区、`run()` 之后新增两个小件、`main()` 的阶段包裹与 argparse、`main()` 尾部既有 `finally`）
- Test: `skills/douyin-pro/scripts/path_b_selftest.py`

- [ ] **Step 1: 写失败测试**

在 `path_b_selftest.py` 末段（`if __name__ == "__main__":` 之前）追加；文件头如未 `import json / os / tempfile` 则补上：

```python
def t_timed_records_stages_and_writes_json():
    """分段计时: 每个 stage 记一次耗时, write_timings 落 JSON 且合计 >= 0。"""
    import tempfile
    before = len(pb._TIMINGS)
    with pb.timed("demo-stage"):
        pass
    assert len(pb._TIMINGS) == before + 1, "timed 上下文退出后必须记一条"
    assert pb._TIMINGS[-1][0] == "demo-stage", "stage 名不许被改写"
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "timing.json")
        pb.write_timings(out)
        data = json.loads(open(out, encoding="utf-8").read())
        assert data["stages"], "timing.json 必须有 stages 数组"
        assert data["total_seconds"] >= 0
        assert any(s["stage"] == "demo-stage" for s in data["stages"])
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python skills/douyin-pro/scripts/path_b_selftest.py`
Expected: FAIL —— `AttributeError: module ... has no attribute 'timed'`（新测试入列并报红，旧测试不受影响）。

- [ ] **Step 3: 最小实现**

在 `path_b_build.py` 的 `import` 区补 `import time`（已有则跳过）；在 `run_exe()` 之后（约 470 行附近）追加：

```python
# ------------------------- 分段计时 (提速实测基线, 规格 2026-10-09) -------------------------
_TIMINGS: list[tuple[str, float]] = []


class timed:
    """阶段计时上下文: with timed("dub"): ... → 退出时把 (stage, 秒) 记进 _TIMINGS。"""

    def __init__(self, stage: str):
        self.stage = stage

    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        _TIMINGS.append((self.stage, time.perf_counter() - self.t0))
        return False


def write_timings(out_path: str) -> None:
    """把分段计时落 JSON 并打一行摘要。"""
    total = sum(t for _, t in _TIMINGS)
    payload = {
        "stages": [{"stage": s, "seconds": round(t, 2)} for s, t in _TIMINGS],
        "total_seconds": round(total, 2),
    }
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    write_text(out_path, json.dumps(payload, ensure_ascii=False, indent=2))
    log("⏱ 分段计时: " + " | ".join(f"{s}={t:.1f}s" for s, t in _TIMINGS)
        + f" | 合计 {total:.1f}s → {out_path}")
```

给 `main()` 的 argparse（`--keep` 之后）加：

```python
    ap.add_argument("--timing-out", help="分段计时 JSON 落点(默认 <成片目录>/timing.json)")
```

在 `main()` 里按阶段包裹（只加 `with timed(...):` 行、不改阶段内部逻辑，各阶段整块缩进一级）：

| 阶段名 | 包裹范围（现有行号锚点） |
|--------|--------------------------|
| `parse` | `scenes = parse_input(...)` 到 `register_indexed_derivers(...)`（2353–2362） |
| `dub` | `if args.skip_render: ... else: synthesize_audio(...)` 整块（2364–2369） |
| `images` | 逐镜取图整块（2378–2391） |
| `emit` | `shots = emit_composition(...)` + 合成 HTML 日志（2392–2394） |
| `gate` | `gate_layout_selfcheck(work)` 到 `gate_hyperframes_check(work)` 含 check_only/skip 分支（2396–2407） |
| `render` | `silent = ...` 到渲染 returncode 判断（2410–2424） |
| `motion` | `audit_motion(...)`（2427） |
| `mux` | `# ⑧ 拼音频 + 烧字幕` 到 `aigc.json` 写盘（2429–2505） |
| `finalize` | media-credits 归档 + 联络表 + shots.json（2507–2523） |

最后改 `main()` 尾部既有 `finally`（2528–2532）——**计时必须写在清理之前**（默认落点在成片目录，不受 rmtree 影响，但顺序仍按此写）：

```python
    finally:
        write_timings(args.timing_out
                      or os.path.join(os.path.dirname(os.path.abspath(args.output)), "timing.json"))
        if not args.keep and not args.work_dir:
            shutil.rmtree(work, ignore_errors=True)
        else:
            log(f"中间文件保留在: {work}")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python skills/douyin-pro/scripts/path_b_selftest.py`
Expected: 全绿（旧项 + 新增 `t_timed_records_stages_and_writes_json`）。

- [ ] **Step 5: 提交**

```powershell
git add skills/douyin-pro/scripts/path_b_build.py skills/douyin-pro/scripts/path_b_selftest.py
git commit -m "feat(news): 渲染链路分段计时（timing.json），为提速实测立基线"
```

---

### Task 2: hyperframes 可执行定位（消 npx 重装）

**Files:**
- Modify: `skills/douyin-pro/scripts/path_b_build.py`（新增定位四件套 + `import glob`；替换 3 处调用点：`gate_hyperframes_check` 1804 行、`main()` render_cmd 2414 行、`doctor()` 1984 行附近；argparse 加 `--hyperframes-bin`）
- Test: `skills/douyin-pro/scripts/path_b_selftest.py`

- [ ] **Step 1: 写失败测试**

在 `path_b_selftest.py` 末段追加（`import os` 需在文件头已有）：

```python
def t_hyperframes_probe_order_and_fallback():
    """可执行定位: 旗标 > 项目 node_modules > npx 缓存 > 回落 npx -y, 每档带真出处。"""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = os.path.join(td, "proj")
        npx = os.path.join(td, "npx")
        os.makedirs(os.path.join(root, "node_modules", ".bin"))
        os.makedirs(os.path.join(npx, "h1", "node_modules", ".bin"))
        local_bin = os.path.join(root, "node_modules", ".bin", "hyperframes.cmd")
        cache_bin = os.path.join(npx, "h1", "node_modules", ".bin", "hyperframes.cmd")
        for p in (local_bin, cache_bin):
            open(p, "w").close()

        cands = pb.hyperframes_candidates(None, root=root, npx_root=npx)
        assert cands[0][0] == [local_bin], "项目 node_modules 必须排在 npx 缓存之前"
        assert any(c[0] == [cache_bin] for c in cands), "npx 缓存里的可执行必须被发现"
        assert all(c[1] for c in cands), "每档候选都要有真出处"

        forced = pb.hyperframes_candidates("X:/custom/hf", root=root, npx_root=npx)
        assert forced[0][0] == ["X:/custom/hf"], "旗标必须压过一切探测"
        assert "旗标" in forced[0][1]

        empty = os.path.join(td, "empty")
        os.makedirs(empty)
        argv, source = pb.resolve_hyperframes(None, root=empty, npx_root=empty)
        assert argv == ["npx", "-y", "hyperframes"], "探测全缺时回落 npx -y"
        assert "回落" in source


def t_no_call_site_hardcodes_npx():
    """check / render / doctor 三处调用点不许再写死 npx -y hyperframes。"""
    import inspect
    gate_src = inspect.getsource(pb.gate_hyperframes_check)
    main_src = inspect.getsource(pb.main)
    for name, src in (("gate_hyperframes_check", gate_src), ("main", main_src)):
        assert '"-y", "hyperframes"' not in src, f"{name} 还在写死 npx -y hyperframes"
    assert 'hf_argv("check"' in gate_src, "gate_hyperframes_check 必须走 hf_argv"
    assert 'hf_argv("render"' in main_src, "渲染命令必须走 hf_argv"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python skills/douyin-pro/scripts/path_b_selftest.py`
Expected: 两条新测试 FAIL（`AttributeError: hyperframes_candidates`；写死 npx 断言红）。

- [ ] **Step 3: 最小实现**

`import` 区补 `import glob`（无则加）。在 Task 1 的计时小件之后追加：

```python
# ------------------------- hyperframes 可执行定位 (提速组件①, 规格 2026-10-09) -------------------------
_HF_PREFIX: list[str] | None = None
_HF_SOURCE: str = ""


def hyperframes_candidates(force_bin: str | None = None,
                           root: str | None = None,
                           npx_root: str | None = None) -> list[tuple[list[str], str]]:
    """候选调用前缀, 按优先级: 旗标 > 项目 node_modules > npx 缓存(逐个)。全空 = 空表。"""
    out: list[tuple[list[str], str]] = []
    if force_bin:
        out.append(([force_bin], f"旗标 --hyperframes-bin={force_bin}"))
    root = root or os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
    for name in ("hyperframes.cmd", "hyperframes"):
        cand = os.path.join(root, "node_modules", ".bin", name)
        if os.path.isfile(cand):
            out.append(([cand], f"项目 node_modules ({name})"))
            break
    npx_root = npx_root or os.path.join(os.environ.get("LOCALAPPDATA", ""),
                                        "npm-cache", "_npx")
    for name in ("hyperframes.cmd", "hyperframes"):
        for b in sorted(glob.glob(os.path.join(npx_root, "*", "node_modules", ".bin", name))):
            out.append(([b], f"npx 缓存 ({b})"))
    return out


def resolve_hyperframes(force_bin: str | None = None,
                        root: str | None = None,
                        npx_root: str | None = None) -> tuple[list[str], str]:
    """返回 (调用前缀, 真出处)。探测全缺时回落 npx -y(现场拉包, 每次 5-15 分钟)。"""
    cands = hyperframes_candidates(force_bin, root=root, npx_root=npx_root)
    if cands:
        return cands[0]
    return ["npx", "-y", "hyperframes"], "回落 npx -y hyperframes (每次重装, 慢)"


def hf_init(force_bin: str | None = None) -> list[str]:
    """初始化并缓存调用前缀; 每次真跑只打一行出处日志。"""
    global _HF_PREFIX, _HF_SOURCE
    if _HF_PREFIX is None or force_bin:
        _HF_PREFIX, _HF_SOURCE = resolve_hyperframes(force_bin)
        log(f"[hf] hyperframes 出处: {_HF_SOURCE}")
    return _HF_PREFIX


def hf_argv(*args: str) -> list[str]:
    return hf_init() + [str(a) for a in args]
```

替换 3 处调用点（`main()` 内 render_cmd 的 `--gpu` 分支追加逻辑不动）：

```python
# gate_hyperframes_check 内 (原 ["npx", "-y", "hyperframes", "check", ...]):
        r = run(hf_argv("check", ".", "--strict", "--json",
                        f"--caption-zone={CAPTION_ZONE}"), cwd=work_dir, stdout=out, stderr=err)

# main() 内 (原 render_cmd = ["npx", "-y", "hyperframes", "render", ...]):
        render_cmd = hf_argv("render", "-c", "index.html",
                             "-o", "silent.mp4", "-f", str(args.fps),
                             f"--quality={args.quality}")

# doctor() 内 (原 run(["npx", "-y", "hyperframes", "doctor"])):
        run(hf_argv("doctor"))
```

argparse 加（`--work-dir` 之后）：

```python
    ap.add_argument("--hyperframes-bin",
                    help="显式指定 hyperframes 可执行(跳过自动探测); 排查与新机器用")
```

`main()` 解析完 args 后（`args.doctor` 判断之前）加一行：

```python
    if args.hyperframes_bin:
        hf_init(args.hyperframes_bin)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python skills/douyin-pro/scripts/path_b_selftest.py`
Expected: 全绿（含两条新增）。

- [ ] **Step 5: 提交**

```powershell
git add skills/douyin-pro/scripts/path_b_build.py skills/douyin-pro/scripts/path_b_selftest.py
git commit -m "feat(news): hyperframes 可执行定位，消掉每次 npx 重装（旗标>本地>缓存>回落）"
```

---

### Task 3: 冷/热跑实测 + 决策门（无代码，拿数据）

**Files:** 无代码改动；产出 `.harness-news-runtime/tmp/timing/` 两份 JSON。

前置：Task 1 已合入（有 `--timing-out`）。输入用现成探针稿：`skills/douyin-pro/scripts/fixtures/badge_probe_shots.json`（5 镜场景 JSON，免得依赖在途稿件）。

- [ ] **Step 1: 冷跑（第一次，含一切缓存现状）**

```powershell
python skills/douyin-pro/scripts/path_b_build.py --input skills/douyin-pro/scripts/fixtures/badge_probe_shots.json --template news-policy --source 提速验收 --output .harness-news-runtime/tmp/timing/cold/final.mp4 --timing-out .harness-news-runtime/tmp/timing/cold.json
```
Expected: 成片出 + `cold.json` 落盘，末行日志打 `⏱ 分段计时: …`。

- [ ] **Step 2: 热跑（紧接着第二次，同参数只换输出名）**

```powershell
python skills/douyin-pro/scripts/path_b_build.py --input skills/douyin-pro/scripts/fixtures/badge_probe_shots.json --template news-policy --source 提速验收 --output .harness-news-runtime/tmp/timing/hot/final.mp4 --timing-out .harness-news-runtime/tmp/timing/hot.json
```
Expected: `hot.json` 落盘。对照 `cold.json` 逐段记差值（npx 定位 / dub / gate / render / mux 各自省了多少）。

- [ ] **Step 3: 决策门判定（照实记录，不许脑补）**

把两份 JSON 的数字抄进 `.harness-news-runtime/tmp/timing/summary.md`，按规格判：
- 热跑 `total_seconds` **≤ 720** → 继续 Task 4/5（并行 3 路即可进 3 分钟/条）；
- 热跑 **> 720** → **停**，向用户汇报数字并提方案 B 评估（渲染引擎旁路），Task 4/5 不做。

---

### Task 4: 字体开销处置（数据驱动分支，三选一）

**Files:** 视分支而定（见下）。判据来自 `hot.json` 的 `render` 段秒数。

- [ ] **Step 1: 看数据定分支**

打开 `.harness-news-runtime/tmp/timing/hot.json`，读 `render` 段：
- **分支 A（热跑 render ≤ 180 秒）**：字体缓存（`~/.cache/hyperframes/fonts`，已有 inter / jetbrains-mono / league-gothic）已命中，**无需代码**。在 summary.md 记一行「字体已缓存命中，组件②免做」，跳到 Task 5。
- **分支 B（热跑 render > 180 秒且怀疑仍在拉网络字体）**：走 Step 2 定位。
- **分支 C（瓶颈根本不在 render 段）**：在 summary.md 记录真实大头段名，跳到 Task 5 并在汇报里点名（例如 gate 慢 → 查 check 门禁是否重复跑）。

- [ ] **Step 2（仅分支 B）: 定位渲染器字体机制**

```powershell
Get-ChildItem "$env:LOCALAPPDATA\npm-cache\_npx\702923228c2ce1e6\node_modules\hyperframes\dist" -Recurse -Filter *.js | Select-String -Pattern "fonts.googleapis|fontsource|woff2" -List | Select-Object -First 5 Path
```
Expected: 找到字体下载逻辑所在文件；把 URL 来源（Google Fonts / fontsource）记进 summary.md。

- [ ] **Step 3（仅分支 B）: 处置**

按 Step 2 结果只做一件最小的事：
- 渲染器有离线/缓存开关 → 在 `hf_argv` 调用点带上该开关（一行）；
- 无开关但重复下载同一字体 → 把 `~/.cache/hyperframes/fonts` 三个字族视为受保护缓存，写进 RUNBOOK「不许清理该目录」；
- **不许改 `_npx` 缓存里第三方包的 dist 源码**（升级即被覆盖，且属于改别人的代码）。
处置后重跑 Step 2 of Task 3 的热跑命令验证 `render` 段下降；**凡动到字体（换族/换文件/换加载方式），必须再跑一次角标字面率复测**：
`python skills/douyin-pro/scripts/verify_aigc_badge.py`（D8 擦边字号无余量，换字体可能让字芯跌破合规线）。

- [ ] **Step 4（有代码改动才做）: 提交**

```powershell
git add -u
git commit -m "perf(news): 字体开销处置（按热跑实测定分支）"
```

---

### Task 5: batch_render.py 并行发射器

**Files:**
- Create: `routes/news/scripts/batch_render.py`
- Test: `routes/news/scripts/batch_render_selftest.py`

- [ ] **Step 1: 写失败测试**

新建 `routes/news/scripts/batch_render_selftest.py`（完整内容）：

```python
#!/usr/bin/env python3
"""batch_render 纯离线断言: 清单解析 / 命令拼装 / 失败隔离 / 汇总口径。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import batch_render as br  # noqa: E402

FAILURES: list[str] = []


def check(name, fn):
    try:
        fn()
        print(f"  ok    {name}")
    except AssertionError as exc:
        FAILURES.append(name)
        print(f"  FAIL  {name}: {exc}")
    except Exception as exc:
        FAILURES.append(name)
        print(f"  ERROR {name}: {type(exc).__name__}: {exc}")


def t_parse_manifest_roundtrip():
    jobs = br.parse_manifest(json.dumps({"jobs": [
        {"input": "a.json", "template": "news-coral", "output": "v/a/final.mp4"},
        {"input": "b.json", "template": "news-ink", "output": "v/b/final.mp4", "source": "测试源"},
    ]}))
    assert len(jobs) == 2, "两条任务都该解析出来"


def t_parse_manifest_names_bad_job():
    try:
        br.parse_manifest(json.dumps({"jobs": [
            {"input": "a.json", "template": "news-coral"}]}))
    except br.BatchError as exc:
        assert "第 1 条" in str(exc) and "output" in str(exc), f"要当场点名缺什么: {exc}"
    else:
        raise AssertionError("缺 output 的任务没被拒收")


def t_build_command_passes_template_and_flags():
    cmd = br.build_command({"input": "a.json", "template": "news-ink",
                            "output": "v/a/final.mp4", "source": "某某频道"},
                           timing_out="t.json")
    assert cmd[cmd.index("--template") + 1] == "news-ink"
    assert cmd[cmd.index("--source") + 1] == "某某频道"
    assert cmd[cmd.index("--timing-out") + 1] == "t.json"


def t_run_jobs_isolates_failure():
    def fake_runner(job, index, timing_dir):
        if job.get("boom"):
            raise RuntimeError("模拟炸了")
        return {"index": index, "input": job["input"], "output": job["output"],
                "ok": True, "returncode": 0, "seconds": 1.0, "log": ""}
    jobs = [{"input": "a", "template": "t", "output": "o1"},
            {"input": "b", "template": "t", "output": "o2", "boom": True},
            {"input": "c", "template": "t", "output": "o3"}]
    results = br.run_jobs(jobs, 2, runner=fake_runner, timing_dir=".")
    assert [r["ok"] for r in results] == [True, False, True], "单条失败不许拖垮批次"
    assert results[1]["index"] == 2, "异常条目也要保留真实序号"


def t_summary_includes_per_item_and_amortized():
    results = [{"index": 1, "input": "a", "output": "o1", "ok": True,
                "returncode": 0, "seconds": 10.0, "log": ""},
               {"index": 2, "input": "b", "output": "o2", "ok": False,
                "returncode": 1, "seconds": 5.0, "log": "L"}]
    text = br.summarize(results, 12.0)
    assert "1/2 成功" in text, "汇总要有成败计数"
    assert "摊薄 6.0s/条" in text, "汇总要有摊薄值"
    assert "❌" in text and "L" in text, "失败条目要给日志落点"


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("t_") and callable(f)]
    print(f"[batch-selftest] {len(tests)} 项")
    for n, f in tests:
        check(n, f)
    if FAILURES:
        print(f"[batch-selftest] 失败 {len(FAILURES)}/{len(tests)}")
        sys.exit(1)
    print(f"[batch-selftest] 全绿 {len(tests)}/{len(tests)}")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python routes/news/scripts/batch_render_selftest.py`
Expected: FAIL —— `ModuleNotFoundError: No module named 'batch_render'`。

- [ ] **Step 3: 最小实现**

新建 `routes/news/scripts/batch_render.py`（完整内容）：

```python
#!/usr/bin/env python3
"""批量并行发射 path_b_build —— 新闻域出片吞吐的调度层。

一条命令吃 N 条稿件清单并行渲染, 单条失败不拖垮批次;
每条产物照旧落 videos/<id>/ 并独立过 check_publishable.py(闸门不因批量化放松)。
设计规格: docs/superpowers/specs/2026-10-09-news-render-speedup-design.md
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "skills",
                                     "douyin-pro", "scripts", "path_b_build.py"))
DEFAULT_TIMING_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..",
                                                  ".harness-news-runtime", "tmp", "timing"))


class BatchError(Exception):
    pass


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def parse_manifest(text: str) -> list[dict]:
    """清单 = {"jobs": [{"input","template","output", 可选 source/aigc-producer/kicker}]}。
    坏清单当场点名第几条缺什么, 不带着坏数据进渲染(R6)。"""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BatchError(f"清单不是合法 JSON: {exc}") from exc
    jobs = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(jobs, list) or not jobs:
        raise BatchError('清单必须是 {"jobs": [...]} 且至少一条')
    for i, job in enumerate(jobs, 1):
        missing = [k for k in ("input", "template", "output") if not job.get(k)]
        if missing:
            raise BatchError(f"第 {i} 条任务缺字段 {missing}: {job}")
    return jobs


def build_command(job: dict, timing_out: str | None = None) -> list[str]:
    cmd = [sys.executable, BUILD, "--input", job["input"],
           "--template", job["template"], "--output", job["output"]]
    for key, flag in (("source", "--source"),
                      ("aigc-producer", "--aigc-producer"),
                      ("kicker", "--kicker")):
        if job.get(key):
            cmd += [flag, str(job[key])]
    if timing_out:
        cmd += ["--timing-out", timing_out]
    return cmd


def run_one(job: dict, index: int, timing_dir: str) -> dict:
    """单条发射: 输出追加进 <成片旁>/build.log, 返回结果字典(自身不抛)。"""
    timing_out = os.path.join(timing_dir, f"job{index:02d}.json")
    cmd = build_command(job, timing_out)
    log_path = os.path.join(os.path.dirname(os.path.abspath(job["output"])), "build.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    t0 = time.perf_counter()
    with open(log_path, "a", encoding="utf-8") as lf:
        proc = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT)
    return {"index": index, "input": job["input"], "output": job["output"],
            "ok": proc.returncode == 0, "returncode": proc.returncode,
            "seconds": round(time.perf_counter() - t0, 1), "log": log_path}


def run_jobs(jobs: list[dict], workers: int, runner=run_one,
             timing_dir: str = DEFAULT_TIMING_DIR) -> list[dict]:
    """N 路并发; 单条失败不拖垮批次, 连 runner 自身炸掉都留痕(按原序号)。"""
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [(i, pool.submit(runner, job, i, timing_dir))
                   for i, job in enumerate(jobs, 1)]
        for i, fut in futures:
            try:
                results.append(fut.result())
            except Exception as exc:
                results.append({"index": i, "input": "?", "output": "?", "ok": False,
                                "returncode": -1, "seconds": 0.0,
                                "log": f"runner 异常: {type(exc).__name__}: {exc}"})
    return sorted(results, key=lambda r: r["index"])


def summarize(results: list[dict], wall_seconds: float) -> str:
    ok = [r for r in results if r["ok"]]
    lines = [f"批次完成: {len(ok)}/{len(results)} 成功 | 墙钟 {wall_seconds:.1f}s | "
             f"摊薄 {wall_seconds / max(len(results), 1):.1f}s/条"]
    for r in results:
        mark = "✅" if r["ok"] else "❌"
        tail = "" if r["ok"] else f" | rc={r.get('returncode')} | {r.get('log')}"
        lines.append(f"  {mark} #{r['index']} {r.get('output', '?')} "
                     f"{r.get('seconds', 0)}s{tail}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="新闻域批量并行渲染 (path_b_build 调度层)")
    ap.add_argument("--manifest", required=True, help="任务清单 JSON")
    ap.add_argument("--jobs", type=int, default=3, help="并发路数 (默认 3)")
    ap.add_argument("--timing-dir", default=DEFAULT_TIMING_DIR,
                    help="分段计时 JSON 落点目录")
    args = ap.parse_args()
    if args.jobs < 1:
        print("[batch] ❌ --jobs 必须 >= 1", file=sys.stderr)
        return 2
    try:
        jobs = parse_manifest(read_text(args.manifest))
    except (OSError, BatchError) as exc:
        print(f"[batch] ❌ {exc}", file=sys.stderr)
        return 2
    os.makedirs(args.timing_dir, exist_ok=True)
    t0 = time.perf_counter()
    results = run_jobs(jobs, args.jobs, timing_dir=args.timing_dir)
    print(summarize(results, time.perf_counter() - t0))
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python routes/news/scripts/batch_render_selftest.py`
Expected: `[batch-selftest] 全绿 5/5`。

- [ ] **Step 5: 提交**

```powershell
git add routes/news/scripts/batch_render.py routes/news/scripts/batch_render_selftest.py
git commit -m "feat(news): batch_render 并行发射器（失败隔离 + 摊薄计时）"
```

---

### Task 6: 吞吐验收 + 文档回写

**Files:**
- 产出: `.harness-news-runtime/verifications/2026-10-09-render-speedup-verification.md`（`git add -f` 进版本管理）
- Modify: `routes/news/RUNBOOK-first-run.md`、`routes/news/MEMORY.md`

- [ ] **Step 1: 真批渲 4 条计时**

写清单 `.harness-news-runtime/tmp/timing/batch4.json`（4 条用 `badge_probe_shots.json` 同一输入、不同输出目录，避免依赖在途稿件的授权/内容问题）：

```json
{
  "jobs": [
    {"input": "skills/douyin-pro/scripts/fixtures/badge_probe_shots.json", "template": "news-policy", "output": ".harness-news-runtime/tmp/timing/batch/b1/final.mp4", "source": "提速验收", "aigc-producer": "提速验收"},
    {"input": "skills/douyin-pro/scripts/fixtures/badge_probe_shots.json", "template": "news-coral", "output": ".harness-news-runtime/tmp/timing/batch/b2/final.mp4", "source": "提速验收", "aigc-producer": "提速验收"},
    {"input": "skills/douyin-pro/scripts/fixtures/badge_probe_shots.json", "template": "news-onsite", "output": ".harness-news-runtime/tmp/timing/batch/b3/final.mp4", "source": "提速验收", "aigc-producer": "提速验收"},
    {"input": "skills/douyin-pro/scripts/fixtures/badge_probe_shots.json", "template": "news-stat", "output": ".harness-news-runtime/tmp/timing/batch/b4/final.mp4", "source": "提速验收", "aigc-producer": "提速验收"}
  ]
}
```

> `source` 必给：引文/收口版式是必需署名位，缺了会被拒收（`check_onscreen` 闸门）；`aigc-producer` 给真值以免默认值混进验收产物。

Run:
```powershell
python routes/news/scripts/batch_render.py --manifest .harness-news-runtime/tmp/timing/batch4.json --jobs 3 --timing-dir .harness-news-runtime/tmp/timing/batch
```
Expected: 汇总行「批次完成: 4/4 成功 | 墙钟 …s | 摊薄 …s/条」，**摊薄值 ≤ 180s/条** 才算过。

- [ ] **Step 2: 逐条过发布闸门 + 三道闸复核**

```powershell
python skills/douyin-pro/scripts/check_publishable.py .harness-news-runtime/tmp/timing/batch/b1/final.mp4
python skills/douyin-pro/scripts/check_publishable.py .harness-news-runtime/tmp/timing/batch/b2/final.mp4
python skills/douyin-pro/scripts/check_publishable.py .harness-news-runtime/tmp/timing/batch/b3/final.mp4
python skills/douyin-pro/scripts/check_publishable.py .harness-news-runtime/tmp/timing/batch/b4/final.mp4
python skills/douyin-pro/scripts/path_b_selftest.py
python routes/news/scripts/batch_render_selftest.py
```
Expected: 4 条闸门全退出码 0（提示带 `--declaration 内容由AI生成` 属正常）；两个 selftest 全绿。

- [ ] **Step 3: 验证单落盘（契约证据，必须进版本管理）**

写 `.harness-news-runtime/verifications/2026-10-09-render-speedup-verification.md`，含：冷/热跑逐段秒数表、Task 3 决策门结论、字体处置分支（A/B/C + 依据）、4 条批渲的墙钟与摊薄值、闸门输出摘要。用 `git add -f` 显式拉入：

```powershell
git add -f .harness-news-runtime/verifications/2026-10-09-render-speedup-verification.md
```

- [ ] **Step 4: 文档回写**

`routes/news/RUNBOOK-first-run.md` §二 P0 表：
- #1（hyperframes 极慢）→ 状态改「已实测+已处置（数字见验证单）」或「部分处置，剩余在 render 段」（照实写）；
- #2（npx 每次重装）→ 状态改「已修：`hf_argv` 可执行定位（Task 2）」；
- #3（edge-tts 不在校验范围）→ 状态改「陈述过期：`install_path_b_deps.py` 第 [2/5] 步本就校验 edge-tts（2026-10-09 复核）」——**不改代码**。

`routes/news/MEMORY.md`：在「In progress」附近加一行提速状态（摊薄实测值 + 验证单路径 + `batch_render` 用法一句话），`last_updated` 改 2026-10-09。

- [ ] **Step 5: 提交**

```powershell
git add routes/news/RUNBOOK-first-run.md routes/news/MEMORY.md
git add -f .harness-news-runtime/verifications/2026-10-09-render-speedup-verification.md
git commit -m "docs(news): 出片提速验收回写（摊薄实测 + RUNBOOK P0 状态修正）"
```

---

## 附：清单文件模板（供日常使用，Task 6 之外不入库）

```json
{
  "jobs": [
    {"input": ".harness-news-runtime/articles/t00X-scenes.json", "template": "news-coral",
     "output": ".harness-news-runtime/videos/t00X/final.mp4",
     "source": "来源署名", "aigc-producer": "真实主体名"}
  ]
}
```

注意：`--aigc-producer` 建议在清单里给真实主体名（GB 45438-2025 要求可追溯到发布主体；默认值 `harness-news-pathb` 只够跑探针）。
