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
# SCRIPT_DIR = <根>/routes/news/scripts, 上溯 3 级才到仓库根
BUILD = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "skills",
                                     "douyin-pro", "scripts", "path_b_build.py"))
DEFAULT_TIMING_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..",
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
