#!/usr/bin/env python3
"""seed_sample_fingerprint.py — sample 真源化种子 / 验证 (Phase 1)

设计: docs/plans/2026-10-12-sample-data-truesource-foundation-design.md §2.4

CLI 行为:
  默认 (= seed mode): HEAD + GET + sha256 写入 sample JSON 的 source_fingerprint_sha256 字段
  --verify-only: 仅比对存储 hash vs 现占内容, 不联网, 不写文件
  --verify-online: HEAD + GET + 比对 hash vs 现拉 hash, 不写文件 (paranoid mode)

退出码:
  0 = 全绿 (种子成功 / 全部 hash 匹配)
  1 = 任一 URL HEAD 失败 / GET 失败 / hash 不匹配 / sample JSON 不合法

依赖: 仅 hashlib, urllib.request (标准库, 零云费零外部依赖)
"""

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "harness-factory/seed-sample-fingerprint (https://github.com/...)"
TIMEOUT_SEC = 15


def _url_safe(url: str) -> str:
    """Percent-encode 非 ASCII 字符 (中文等), 保留 URL 语法符号.

    urllib.request.Request 默认 ascii 编码整个字符串, 遇到中文路径就 UnicodeEncodeError.
    解决方案: 用 urllib.parse.quote 对 path / fragment / query 单独编码,
    保留 scheme / netloc / 用户认证段原样.
    """
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((
        parts.scheme,
        parts.netloc,
        urllib.parse.quote(parts.path, safe="/-._~!$&'()*+,;=:@"),
        urllib.parse.quote(parts.query, safe="=&-._~!$'()*+,;=:@?/"),
        urllib.parse.quote(parts.fragment, safe="-._~!$'()*+,;=:@?/"),
    ))


def head_ok(url: str) -> tuple[bool, str]:
    """HEAD 请求, 200-299 视为 OK.

    返回 (ok, detail): ok=True 时 detail = 状态码 / False 时 detail = 报错原文.
    """
    safe_url = _url_safe(url)
    req = urllib.request.Request(safe_url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
            code = resp.status
            if 200 <= code < 300:
                return True, f"HTTP {code}"
            return False, f"HTTP {code}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except urllib.error.URLError as exc:
        return False, f"URLError: {exc.reason}"
    except TimeoutError:
        return False, "Timeout (>15s)"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def fetch_content(url: str) -> bytes:
    """GET 请求, 返回内容字节.

    Raises urllib.error.HTTPError / URLError / TimeoutError.
    """
    safe_url = _url_safe(url)
    req = urllib.request.Request(safe_url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
        return resp.read()


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


# ── 真源化闸主流程 ─────────────────────────────────────────────

def collect_url_jobs(sample: dict) -> list[tuple[str, str, str]]:
    """返回 [(path_in_json, url_field_name, url_value), ...]

    path_in_json 是输出时写回用的 dot-path, 如 'facts[0].source_url'.
    """
    jobs: list[tuple[str, str, str]] = []
    for i, fact in enumerate(sample.get("facts", []) or []):
        url = fact.get("source_url")
        if url:
            jobs.append((f"facts[{i}]", "source_url", url))
    for i, image in enumerate(sample.get("images", []) or []):
        url = image.get("wikimedia_url")
        if url:
            jobs.append((f"images[{i}]", "wikimedia_url", url))
    return jobs


def _set_by_path(obj: dict, path: str, key: str, value) -> None:
    """按 path 找到 list[path_index] 并写入 obj[path_index][key] = value."""
    if "[" in path and path.endswith("]"):
        bracket = path.index("[")
        field_name = path[:bracket]
        idx = int(path[bracket + 1 : -1])
        obj[field_name][idx][key] = value
    else:
        obj[path][key] = value


def _get_by_path(obj: dict, path: str, key: str):
    if "[" in path and path.endswith("]"):
        bracket = path.index("[")
        field_name = path[:bracket]
        idx = int(path[bracket + 1 : -1])
        return obj[field_name][idx][key]
    return obj[path][key]


def seed(sample_path: Path) -> int:
    """seed mode: 网络 HEAD + GET, 写 hash 到 sample JSON.

    任一失败 EXIT 1, 不部分写入。
    """
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    jobs = collect_url_jobs(sample)
    if not jobs:
        print("[seed] sample 无 facts / images URL, 无事可做")
        return 0

    failed: list[tuple[str, str, str, str]] = []  # (path, field, url, detail)
    hashes: dict[str, str] = {}  # path → sha256

    for path, field, url in jobs:
        ok, detail = head_ok(url)
        print(f"[HEAD] {url} → {detail}")
        if not ok:
            failed.append((path, field, url, detail))
            continue
        try:
            content = fetch_content(url)
        except Exception as exc:  # noqa: BLE001
            print(f"[GET ] {url} → {type(exc).__name__}: {exc}")
            failed.append((path, field, url, f"GET {type(exc).__name__}"))
            continue
        h = sha256_hex(content)
        hashes[path] = h
        print(f"[GET ] {url} → {len(content)} bytes, sha256={h[:16]}...")

    if failed:
        print(f"\n[seed] FAIL: {len(failed)}/{len(jobs)} URL 抓取失败:")
        for path, field, url, detail in failed:
            print(f"  - {path}.{field} ({url}): {detail}")
        print("[seed] 不写文件, 不假绿")
        return 1

    # 全成功 → 写回
    for path, _, _ in jobs:
        _set_by_path(sample, path, "source_fingerprint_sha256", hashes[path])

    sample_path.write_text(
        json.dumps(sample, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\n[seed] OK: {len(hashes)}/{len(jobs)} hash 写入 → {sample_path}")
    return 0


def verify_only(sample_path: Path, online: bool = False) -> int:
    """verify mode: 比对存储 hash vs 现拉 (online=True) 或 离线 (online=False)。

    退出码 1 = 任一不匹配, 闸门触发。
    """
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    jobs = collect_url_jobs(sample)
    if not jobs:
        print("[verify] sample 无 facts / images URL, 无事可做")
        return 0

    failed: list[tuple[str, str, str, str, str]] = []
    matched = 0

    for path, field, url in jobs:
        stored_hash = _get_by_path(sample, path, "source_fingerprint_sha256")
        if not online:
            # 离线模式: 仅看 hash 字段是否已填 (起始: 64 个 0 视为未种子)
            if stored_hash == "0" * 64 or not stored_hash:
                print(f"[verify] {path}.{field} ({url}): 未种子 (placeholder)")
                failed.append((path, field, url, "<placeholder>", "<未种子>"))
            else:
                print(f"[verify] {path}.{field} ({url}): hash 已存 {stored_hash[:16]}... (离线, 不联网)")
                matched += 1
            continue

        # 在线模式: HEAD + GET + 比对
        ok, detail = head_ok(url)
        if not ok:
            print(f"[HEAD] {url} → {detail}")
            failed.append((path, field, url, stored_hash, detail))
            continue
        try:
            content = fetch_content(url)
        except Exception as exc:  # noqa: BLE001
            print(f"[GET ] {url} → {type(exc).__name__}: {exc}")
            failed.append((path, field, url, stored_hash, f"GET {type(exc).__name__}"))
            continue
        actual = sha256_hex(content)
        if actual != stored_hash:
            print(f"[verify] {path}.{field} ({url}): MISMATCH")
            print(f"   stored: {stored_hash}")
            print(f"   actual: {actual}")
            failed.append((path, field, url, stored_hash, actual))
        else:
            print(f"[verify] {path}.{field} ({url}): ✓ match {stored_hash[:16]}...")
            matched += 1

    print(f"\n[verify] {matched}/{len(jobs)} match")
    if failed:
        print(f"[verify] FAIL: {len(failed)} mismatch/error")
        return 1
    return 0


# ── CLI ───────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="sample data 真源化种子 / 验证 (Phase 1)",
    )
    ap.add_argument("sample", type=Path, help="sample JSON 路径")
    ap.add_argument(
        "--verify-only",
        action="store_true",
        help="仅比对存储 hash vs 现占 (离线模式, 不联网, 不写)",
    )
    ap.add_argument(
        "--verify-online",
        action="store_true",
        help="在线 verify 模式 (HEAD + GET + 比对 hash, 不写文件, paranoid)",
    )
    args = ap.parse_args(argv)

    if not args.sample.exists():
        print(f"[error] sample 文件不存在: {args.sample}", file=sys.stderr)
        return 1

    try:
        json.loads(args.sample.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[error] sample JSON 非法: {exc}", file=sys.stderr)
        return 1

    if args.verify_only:
        return verify_only(args.sample, online=False)
    if args.verify_online:
        return verify_only(args.sample, online=True)
    return seed(args.sample)


if __name__ == "__main__":
    sys.exit(main())