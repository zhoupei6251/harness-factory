#!/usr/bin/env python3
"""台账状态回写 CLI —— 把「已发布的不再发」这一步从手敲 python -c 变成一条命令。

设计: routes/news/DESIGN-dedup.md §6（状态迁移只有 news-workflow 写 · 追加语义 · 同事件同 id）
配套断言: skills/news-curate/scripts/curate_selftest.py（t_ledger_mark_* / t_ledger_check_*）

子命令:
  mark   追加一行状态迁移（**沿用同一事件的主键**，追加语义，永不原地改）
  check  校验主键完整性（不同事件共用主键 = 撞车；同事件多行同主键 = 合法）

退出码: 0 = 成功；1 = 用法/数据错误（R6：禁静默失败，找不到目标不许凭空追加）

为什么需要它: 「每次把发的新闻记住、不重复生成」的落地点，就是发布后往台账追加一行
`status: published`。此前这一步只有一段手抄的 `python -c`（news-workflow 硬性规则 9），
字段一多就会漏、`norm_key` 一手抖去重就静默失效。这里把它固化成带校验的命令。
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import curate as cu  # noqa: E402  (复用 append_ledger / read_ledger / DEFAULT_LEDGER)

#: 合法状态（与 DESIGN §6 状态机一致）
VALID_STATUSES = ("candidate", "selected", "drafted", "rendered", "published", "rejected")
#: 可从 MEMORY 回填的可选字段
OPTIONAL_FIELDS = ("topic_id", "draft_id", "video_id", "output", "published_at",
                   "declaration", "aigc_ok", "fact_check", "rank_peak", "note")


class LedgerError(Exception):
    """台账用法/数据错误 —— 一律停机，不回退默认（R6）。"""


def check_ids(entries: list[dict]) -> list[str]:
    """主键完整性校验。

    判据:
      - 不同 `norm_key` 共用同一个 `id` → **撞车**（报问题）
      - 同一 `norm_key` 多行共用同一个 `id` → **合法**（同事件的状态迁移，设计 §6）
      - 行缺 `id` → 报问题
    """
    problems: list[str] = []
    by_id: dict[str, set] = {}
    for e in entries:
        if "_bad_line" in e:
            continue
        lid = e.get("id")
        if not lid:
            problems.append(f"行缺主键 id（title={str(e.get('title'))[:30]!r}）")
            continue
        by_id.setdefault(str(lid), set()).add(e.get("norm_key"))
    for lid, keys in by_id.items():
        keys.discard(None)
        if len(keys) > 1:
            problems.append(
                f"主键 {lid} 被 {len(keys)} 个不同事件共用（撞车）: {sorted(keys)[:3]}")
    return problems


def _latest(entries: list[dict], *, id=None, norm_key=None) -> dict | None:
    """台账当前状态 = **最后一行**（设计 §6）。按 id 或 norm_key 找最后匹配的一行。"""
    hit = None
    for e in entries:
        if "_bad_line" in e:
            continue
        if id is not None and str(e.get("id")) == str(id):
            hit = e
        elif norm_key is not None and e.get("norm_key") == norm_key:
            hit = e
    return hit


def mark(path, status: str, *, id=None, norm_key=None, today=None, **fields) -> dict:
    """追加一行状态迁移，**沿用同一事件的主键**。

    返回写入的行。任何用法错误抛 `LedgerError`（调用方转成退出码 1）。
    """
    if status not in VALID_STATUSES:
        raise LedgerError(
            f"未知状态 {status!r} —— 合法值: {' / '.join(VALID_STATUSES)}")
    if (id is None) == (norm_key is None):
        raise LedgerError("必须且只能给一个定位条件: --id 或 --norm-key")

    entries = cu.read_ledger(path)
    target = _latest(entries, id=id, norm_key=norm_key)
    if target is None:
        which = f"id={id}" if id is not None else f"norm_key={norm_key!r}"
        # norm_key 手敲前缀会让这里找不到 —— 明确提示（SKILL §1 的老坑）
        raise LedgerError(
            f"台账里找不到该事件（{which}）。若用 --norm-key 定位，"
            f"必须是**完整标题**算出的归一化键，手敲前缀匹配不上。")

    row = dict(target)                      # 继承首见日期 / 主键 / 主题关联等
    row["status"] = status
    if status == "published":
        row.setdefault("published_at", None)
        row["published_at"] = row.get("published_at") or (today or _today())
    for k, v in fields.items():
        if v is not None:
            row[k] = v
    cu.append_ledger(path, row)
    return row


def _today() -> str:
    return dt.datetime.now().astimezone().date().isoformat()


# ── CLI ───────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="台账状态回写：mark（追加迁移）/ check（主键校验）")
    ap.add_argument("--ledger", default=str(cu.DEFAULT_LEDGER), help="台账路径")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pm = sub.add_parser("mark", help="追加一行状态迁移")
    pm.add_argument("--status", required=True, help=" | ".join(VALID_STATUSES))
    pm.add_argument("--id", default=None, help="按主键定位")
    pm.add_argument("--norm-key", dest="norm_key", default=None, help="按归一化键定位（完整标题算出）")
    pm.add_argument("--topic-id", dest="topic_id", default=None)
    pm.add_argument("--draft-id", dest="draft_id", default=None)
    pm.add_argument("--video-id", dest="video_id", default=None)
    pm.add_argument("--output", default=None)
    pm.add_argument("--published-at", dest="published_at", default=None)
    pm.add_argument("--declaration", default=None)
    pm.add_argument("--note", default=None)

    sub.add_parser("check", help="校验主键完整性")

    args = ap.parse_args(argv)
    ledger = args.ledger

    if args.cmd == "check":
        problems = check_ids(cu.read_ledger(ledger))
        if problems:
            print(f"❌ 台账主键校验不过（{ledger}）:")
            for p in problems:
                print(f"   · {p}")
            return 1
        print(f"✅ 台账主键完整（{ledger}）")
        return 0

    fields = {k: getattr(args, k) for k in OPTIONAL_FIELDS if hasattr(args, k)}
    try:
        row = mark(ledger, args.status, id=args.id, norm_key=args.norm_key, **fields)
    except LedgerError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    print(f"✅ {row['id']} → {row['status']} · {row.get('title', '')[:30]} → {ledger}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
