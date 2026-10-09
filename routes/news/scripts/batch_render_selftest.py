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
