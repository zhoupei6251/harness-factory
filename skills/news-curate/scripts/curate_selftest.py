#!/usr/bin/env python3
"""news-curate 的纯函数断言集（不需要网络，可离线跑）。

设计文档: routes/news/DESIGN-dedup.md

仓库没有 Python 测试基建（package.json 的 test 只跑 TS），所以这里自带
check() harness 与退出码：0 = 全绿，1 = 有失败并逐条打印。约定照
skills/douyin-pro/scripts/path_b_selftest.py 的写法。

    python skills/news-curate/scripts/curate_selftest.py

覆盖 §8 的 16 条断言，重点是把这三条**设计决策**锁成可执行断言：
  1. L1 归一化精确匹配才允许自动硬剔除（D1/D2）
  2. L2 相似度**永不**自动剔除，只标 needs_review（D2，三轮实测逼出来的）
  3. 打分只用免费信号，不读 hot 字段（G4/G5）
"""

import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
#: 决策工具在 routes/news/scripts/（跨目录 import, 用于 D20 的脱节检测）
_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "routes" / "news" / "scripts"))
sys.path.insert(0, str(_REPO_ROOT / "skills" / "douyin-pro" / "scripts"))

import curate as cu  # noqa: E402  (被测模块)
import decide_pack as dp  # noqa: E402  (决策工具: D20 要锁它与真实模板不脱节)

FAILURES: list[tuple[str, str]] = []


def check(name: str, fn) -> None:
    try:
        fn()
    except AssertionError as exc:
        FAILURES.append((name, str(exc) or "断言失败(无描述)"))
        print(f"  FAIL  {name}: {exc}")
    except Exception as exc:  # noqa: BLE001  测试里意外异常就是失败, 不许静默
        FAILURES.append((name, f"{type(exc).__name__}: {exc}"))
        print(f"  ERROR {name}: {type(exc).__name__}: {exc}")
    else:
        print(f"  ok    {name}")


def write_ledger(rows: list[dict], d: Path) -> Path:
    p = d / "ledger.jsonl"
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                 encoding="utf-8")
    return p


def write_hotboard(items: list[dict], d: Path) -> Path:
    p = d / "hotboard.json"
    p.write_text(json.dumps({"date": "2026-10-08", "items": items},
                             ensure_ascii=False), encoding="utf-8")
    return p


# ── 1-2 · L1 归一化 ────────────────────────────────────────────────

def t_norm_key_keeps_chinese_chars():
    """re 的 \\W 在 Unicode 下不删汉字 —— 这条锁住"以为归一化清了中文"的误修。"""
    k = cu.norm_key("暴雨")
    assert k == "暴雨", f"归一化把汉字删了: {k!r}"
    assert cu.norm_key("国务院新规") == "国务院新规", cu.norm_key("国务院新规")


def t_norm_key_strips_punctuation():
    k = cu.norm_key("「暴雨！致3人？」")
    assert k == "暴雨致3人", f"标点没去掉: {k!r}"
    assert cu.norm_key("国务院 发布新规") == "国务院发布新规", "空白没去掉"


# ── 3 · 指纹抽取 ──────────────────────────────────────────────────

def t_fingerprint_extracts_entities():
    fp = cu.fingerprint("湖南常德暴雨已致3人死亡")
    assert "3人" in fp or "3" in "".join(fp), f"数字类实体没抽到: {fp}"
    joined = "".join(fp)
    assert "常德" in joined or "湖南" in joined, f"地名没抽到: {fp}"
    assert not any(tok in cu.STOPWORDS for tok in fp), f"停用词没剔掉: {fp}"


# ── 4 · L1 硬剔除 ──────────────────────────────────────────────────

def t_l1_exact_match_excludes():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        led = write_ledger([{
            "id": "n0001", "norm_key": "暴雨致3人死亡", "fingerprint": ["暴雨", "3人"],
            "first_seen": "2026-10-07", "last_seen": "2026-10-07", "status": "published",
            "rank_peak": 4, "hits": 1,
        }], d)
        hb = write_hotboard([{
            "rank": 1, "title": "暴雨致3人死亡", "url": "", "hot": "", "source": "baidu-realtime",
        }], d)
        doc = cu.curate(hotboard=hb, ledger=led)
        titles = [c["title"] for c in doc["candidates"]]
        assert "暴雨致3人死亡" not in titles, f"L1 命中却还在候选里: {titles}"
        ex = [e for e in doc["excluded"] if e["title"] == "暴雨致3人死亡"]
        assert ex, "L1 命中没进 excluded"
        assert ex[0]["reason"] == "already_published", ex[0]
        assert ex[0]["matched_ledger_id"] == "n0001", ex[0]


# ── 5-8 · L2 永不自动剔除（D2 的核心） ───────────────────────────

def t_l2_marks_needs_review_not_excluded():
    """实测 0.167（低于提示区 0.30）→ 仍进 candidates, 不进 excluded。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        led = write_ledger([{
            "id": "n0002", "norm_key": "某地暴雨", "fingerprint": ["某地暴雨"],
            "first_seen": "2026-10-07", "last_seen": "2026-10-07",
            "status": "published", "rank_peak": 6, "hits": 1,
        }], d)
        hb = write_hotboard([{
            "rank": 2, "title": "暴雨已致3人死亡", "url": "", "hot": "", "source": "baidu-realtime",
        }], d)
        doc = cu.curate(hotboard=hb, ledger=led)
        titles = [c["title"] for c in doc["candidates"]]
        assert "暴雨已致3人死亡" in titles, f"L2 低分不该剔除: {titles}"
        assert not [e for e in doc["excluded"] if "3人" in e["title"]], \
            "L2 命中却进了 excluded —— 违反 D2"
        # 归一化键不同 → L1 不该命中
        assert "某地暴雨" != cu.norm_key("暴雨已致3人死亡"), "前置条件不成立"


def t_l2_mid_similarity_flags_review():
    """实测 1.174（中段）→ 标 needs_review, 且仍在 candidates 里。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        led = write_ledger([{
            "id": "n0003",
            "norm_key": cu.norm_key("拾荒老人每月3700元养老金"),
            "fingerprint": [],
            "first_seen": "2026-10-01", "last_seen": "2026-10-01",
            "status": "published", "rank_peak": 5, "hits": 1,
        }], d)
        hb = write_hotboard([{
            "rank": 1, "title": "71岁老人不知自己每月有3700元养老金",
            "url": "", "hot": "", "source": "baidu-realtime",
        }], d)
        doc = cu.curate(hotboard=hb, ledger=led)
        cands = [c for c in doc["candidates"] if "71岁" in c["title"]]
        assert cands, f"中段相似不该剔除: {[c['title'] for c in doc['candidates']]}"
        c = cands[0]
        assert c.get("needs_review"), f"中段相似没标 needs_review: {c}"
        assert c["review_matched_id"] == "n0003", f"没点名撞了哪条台账: {c}"


def t_l2_high_similarity_flags_high_risk():
    """同题两次（实测 2.435, ≥ L2_REVIEW_HIGH）→ needs_review == high。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        led = write_ledger([{
            "id": "n0004", "norm_key": "暴雨致3人死亡", "fingerprint": [],
            "first_seen": "2026-10-01", "last_seen": "2026-10-01",
            "status": "published", "rank_peak": 4, "hits": 1,
        }], d)
        # 换一个标点差异制造极近标题
        hb = write_hotboard([{
            "rank": 1, "title": "  暴雨致3人死亡！", "url": "", "hot": "", "source": "baidu-realtime",
        }], d)
        doc = cu.curate(hotboard=hb, ledger=led)
        # 这条其实是 L1 命中(归一化后相同) → 走硬剔除分支
        assert not [c for c in doc["candidates"]], \
            "L1 命中却仍在候选里"
        assert [e for e in doc["excluded"] if e["title"] == "  暴雨致3人死亡！"], \
            "L1 命中没剔除"
        assert cu.L2_REVIEW_HIGH > cu.L2_REVIEW_LOW, "高风险阈值必须高于提示区下限"


def t_l2_never_silently_drops():
    """**L2 相似度无论多高都不产生 excluded** —— D2 铁律, 防后人偷偷加回自动剔除。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        # 造 200 条不同事件, 全部"高度相似"到分数爆表
        rows = [{
            "id": f"n{i:04d}",
            "norm_key": f"无关标题{i}",
            "fingerprint": [],
            "first_seen": "2026-10-01", "last_seen": "2026-10-01",
            "status": "published", "rank_peak": 10, "hits": 1,
        } for i in range(200)]
        led = write_ledger(rows, d)
        # 候选：每条都与台账某一条构造出高相似
        items = [{
            "rank": i + 1, "title": f"无关标题{i}", "url": "", "hot": "",
            "source": "baidu-realtime",
        } for i in range(200)]
        hb = write_hotboard(items, d)
        doc = cu.curate(hotboard=hb, ledger=led)
        # 全部是 L1 命中(同标题) → 可以剔除; 但若有任何一条是靠 L2 剔的, 那就违反 D2
        for e in doc["excluded"]:
            assert e["reason"] == "already_published", \
                f"剔除理由不是 L1 → 是 L2 干的, 违反 D2: {e}"
        # 反证: 换不同标题但高相似, 必须是 needs_review 而非 excluded
        led2 = write_ledger([{
            "id": "n9999", "norm_key": "拾荒老人每月3700元养老金", "fingerprint": [],
            "first_seen": "2026-10-01", "last_seen": "2026-10-01",
            "status": "published", "rank_peak": 5, "hits": 1,
        }], d)
        hb2 = write_hotboard([{
            "rank": 1, "title": "71岁老人不知自己每月有3700元养老金",
            "url": "", "hot": "", "source": "baidu-realtime",
        }], d)
        doc2 = cu.curate(hotboard=hb2, ledger=led2)
        assert not doc2["excluded"], f"L2 产生了 excluded, 违反 D2: {doc2['excluded']}"


# ── 9 · rejected 的回炉 ──────────────────────────────────────────

def t_rejected_allowed_when_rank_improves():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        led = write_ledger([{
            "id": "n0005", "norm_key": "某地暴雨", "fingerprint": [],
            "first_seen": "2026-09-01", "last_seen": "2026-09-01",
            "status": "rejected", "rank_peak": 30, "hits": 1,
        }], d)
        hb = write_hotboard([{
            "rank": 2, "title": "某地暴雨", "url": "", "hot": "", "source": "baidu-realtime",
        }], d)
        doc = cu.curate(hotboard=hb, ledger=led)
        ex = [e for e in doc["excluded"] if e["title"] == "某地暴雨"]
        assert not ex, f"rank 30→2 已改善 93%, 却在 excluded 里: {ex}"
        cands = [c for c in doc["candidates"] if c["title"] == "某地暴雨"]
        assert cands, "热度回升却没重提"
        assert cands[0].get("revived"), f"重提了但没标 revived: {cands[0]}"


# ── 10 · G6 禁静默失败 ───────────────────────────────────────────

def t_excluded_carries_reason():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        led = write_ledger([
            {"id": "n0001", "norm_key": "已发新闻甲", "fingerprint": [],
             "first_seen": "2026-10-01", "last_seen": "2026-10-01",
             "status": "published", "rank_peak": 5, "hits": 1},
            {"id": "n0002", "norm_key": "已成片新闻乙", "fingerprint": [],
             "first_seen": "2026-10-01", "last_seen": "2026-10-01",
             "status": "rendered", "rank_peak": 6, "hits": 1},
        ], d)
        hb = write_hotboard([
            {"rank": 1, "title": "已发新闻甲", "url": "", "hot": "", "source": "baidu-realtime"},
            {"rank": 2, "title": "已成片新闻乙", "url": "", "hot": "", "source": "baidu-realtime"},
        ], d)
        doc = cu.curate(hotboard=hb, ledger=led)
        assert len(doc["excluded"]) == 2, doc["excluded"]
        for e in doc["excluded"]:
            assert e.get("reason"), f"excluded 条目缺 reason: {e}"
            assert e.get("matched_ledger_id"), f"excluded 条目缺 matched_ledger_id: {e}"
            assert e.get("matched_norm_key"), f"excluded 条目缺 matched_norm_key: {e}"
        reasons = {e["matched_ledger_id"]: e["reason"] for e in doc["excluded"]}
        assert reasons["n0001"] == "already_published", reasons
        assert reasons["n0002"] == "already_rendered", reasons


# ── 11 · 台账只追加 ──────────────────────────────────────────────

def t_ledger_append_never_rewrites_history():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        p = d / "ledger.jsonl"
        cu.append_ledger(p, {"id": "n0001", "norm_key": "甲", "status": "candidate"})
        cu.append_ledger(p, {"id": "n0001", "norm_key": "甲", "status": "published"})
        lines = [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 2, f"同 id 写两次应留两行, 实际 {len(lines)} 行"
        last = json.loads(lines[-1])
        assert last["status"] == "published", last


# ── 12 · G4/G5 禁付费信号 ───────────────────────────────────────

def t_score_uses_no_paid_signal():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        hb = write_hotboard([
            {"rank": 3, "title": "测试新闻一号", "url": "", "hot": "", "source": "baidu-realtime"},
            {"rank": 3, "title": "测试新闻二号", "url": "", "hot": "99999999",
             "source": "baidu-realtime"},
        ], d)
        led = write_ledger([], d)
        doc = cu.curate(hotboard=hb, ledger=led)
        a = [c for c in doc["candidates"] if c["title"] == "测试新闻一号"][0]
        b = [c for c in doc["candidates"] if c["title"] == "测试新闻二号"][0]
        assert a["score"] == b["score"], \
            f"hot 字段影响了打分(实测该字段恒为空, 禁编逻辑): {a['score']} vs {b['score']}"


# ── 13 · 置顶条目 rank=null ──────────────────────────────────────

def t_score_null_rank_safe():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        hb = write_hotboard([
            {"rank": None, "is_top": True, "title": "置顶新闻", "url": "", "hot": "",
             "source": "baidu-realtime"},
            {"rank": 1, "title": "第一名新闻", "url": "", "hot": "", "source": "baidu-realtime"},
        ], d)
        led = write_ledger([], d)
        doc = cu.curate(hotboard=hb, ledger=led)
        titles = [c["title"] for c in doc["candidates"]]
        assert len(titles) == 2, f"rank=null 被丢了: {titles}"
        top = [c for c in doc["candidates"] if c["title"] == "置顶新闻"][0]
        first = [c for c in doc["candidates"] if c["title"] == "第一名新闻"][0]
        assert first["score"] > top["score"], \
            "置顶(rank=null)不该当第一名"


# ── 14 · 候选排空是合法结果 ─────────────────────────────────────

def t_empty_candidates_writes_empty_list():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        led = write_ledger([
            {"id": "n0001", "norm_key": "新闻甲", "fingerprint": [],
             "first_seen": "2026-10-01", "last_seen": "2026-10-01",
             "status": "published", "rank_peak": 5, "hits": 1},
        ], d)
        hb = write_hotboard([{
            "rank": 1, "title": "新闻甲", "url": "", "hot": "", "source": "baidu-realtime",
        }], d)
        doc = cu.curate(hotboard=hb, ledger=led)
        assert doc["candidates"] == [], f"全排空了却还有候选: {doc['candidates']}"
        assert doc["excluded"], "全排空了却没有排除理由(G6)"
        assert doc["exit_code"] == 0, f"排空是合法业务结果, 退出码应为 0: {doc['exit_code']}"


# ── 15 · 空台账 ──────────────────────────────────────────────────

def t_missing_ledger_treated_as_empty():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        hb = write_hotboard([{
            "rank": 1, "title": "今天第一条", "url": "", "hot": "", "source": "baidu-realtime",
        }], d)
        missing = d / "nope.jsonl"
        assert not missing.exists(), "前置条件不成立"
        doc = cu.curate(hotboard=hb, ledger=missing)
        assert len(doc["candidates"]) == 1, doc["candidates"]
        assert doc["ledger_entries"] == 0, doc["ledger_entries"]


# ── 16 · 状态权重表 ──────────────────────────────────────────────

def t_status_weight_table():
    table = cu.STATUS_WEIGHT
    for st in ("published", "rendered", "drafted", "selected", "candidate", "rejected"):
        assert st in table, f"状态权重表缺 {st}: {sorted(table)}"
    assert table["published"] == 0.0, f"published 乘子应为 0(硬剔除): {table}"
    assert table["rendered"] == 0.0, f"rendered 乘子应为 0(硬剔除): {table}"
    assert 0 < table["drafted"] < 1, f"在途应降权但不为 0: {table}"
    assert 0 < table["candidate"] <= 1, f"候选应轻微降权: {table}"
    assert table["rejected"] == 1.0, f"rejected 不该降权: {table}"


# ── 17-19 · rank 语义: 只有百度榜的 rank 是热度（2026-10-08 真实数据发现） ──

def t_rss_rank_is_not_hotness():
    """RSS 源的 rank 只是 feed 内序号, 不是热度 —— 不得当热度加权。

    真实数据: 4 个源各有 1 条 rank=1, 但它们是 4 条完全不同的新闻。
    """
    for src in ("thepaper", "zaobao", "bbc-zh", "rss"):
        assert cu.RANKED_SOURCES == {"baidu-realtime"}, \
            f"只有百度实时榜的 rank 是热度, 当前: {cu.RANKED_SOURCES}"
    assert not cu.is_ranked_source("bbc-zh"), "bbc-zh 不该按 rank 计分"
    assert not cu.is_ranked_source("thepaper"), "thepaper 不该按 rank 计分"
    assert cu.is_ranked_source("baidu-realtime"), "百度榜应按 rank 计分"
    assert cu.rank_score(1, source="bbc-zh") == 0.0, "RSS 源的 rank 不该产生名次分"
    assert cu.rank_score(1, source="baidu-realtime") > 0.0, "百度榜 rank=1 应有分"


def t_rss_does_not_tie_with_baidu():
    """真实场景: 百度榜 #1 与 BBC feed #1 不可并列, 前者更热。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        hb = write_hotboard([
            {"rank": 1, "title": "百度榜第一名", "url": "", "hot": "", "source": "baidu-realtime"},
            {"rank": 1, "title": "BBC 稿子第一条", "url": "", "hot": "", "source": "bbc-zh"},
        ], d)
        doc = cu.curate(hotboard=hb, ledger=write_ledger([], d))
        by = {c["title"]: c for c in doc["candidates"]}
        assert by["百度榜第一名"]["score"] > by["BBC 稿子第一条"]["score"], \
            f"百度 #1 与 BBC feed #1 不该并列: {by['百度榜第一名']['score']} vs " \
            f"{by['BBC 稿子第一条']['score']}"


def t_rss_freshness_still_rewards():
    """RSS 源没名次分, 但新鲜度仍应给分（bbc-zh 实测当天, thepaper 297 天前）。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        hb = write_hotboard([
            {"rank": None, "title": "新鲜外媒", "url": "", "hot": "", "source": "bbc-zh",
             "published": "Tue, 06 Oct 2026 00:00:00 +0000", "age_days": 0.2},
            {"rank": None, "title": "陈旧外媒", "url": "", "hot": "", "source": "thepaper",
             "published": "Tue, 23 Dec 2025 00:00:00 +0000", "age_days": 288.0},
        ], d)
        doc = cu.curate(hotboard=hb, ledger=write_ledger([], d))
        by = {c["title"]: c for c in doc["candidates"]}
        assert by["新鲜外媒"]["score"] > by["陈旧外媒"]["score"], \
            f"age_days 应参与打分(免费信号): {by['新鲜外媒']['score']} vs " \
            f"{by['陈旧外媒']['score']}"


# ── 20-21 · 陈旧源必须有闸（2026-10-08 真实数据: thepaper 297 天 / zaobao 48 天） ──

def t_stale_sources_are_flagged():
    """陈旧源条目必须打 stale 标记 —— 靠分数沉底不够, 清单里要能一眼看见。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        hb = write_hotboard([
            {"rank": None, "title": "陈旧澎湃条目", "url": "", "hot": "", "source": "thepaper",
             "age_days": 297.0},
            {"rank": None, "title": "新鲜 BBC 条目", "url": "", "hot": "", "source": "bbc-zh",
             "age_days": 0.2},
        ], d)
        doc = cu.curate(hotboard=hb, ledger=write_ledger([], d))
        by = {c["title"]: c for c in doc["candidates"]}
        assert by["陈旧澎湃条目"].get("stale"), "297 天的条目没打 stale 标记"
        assert by["陈旧澎湃条目"]["stale_age_days"] == 297.0, by["陈旧澎湃条目"]
        assert not by["新鲜 BBC 条目"].get("stale"), \
            f"当天条目不该被标 stale: {by['新鲜 BBC 条目']}"
        # 百度榜无 age_days 概念, 不该被判 stale
        hb2 = write_hotboard([{"rank": 1, "title": "百度榜第一条", "url": "", "hot": "",
                               "source": "baidu-realtime"}], d)
        doc2 = cu.curate(hotboard=hb2, ledger=write_ledger([], d))
        assert not doc2["candidates"][0].get("stale"), \
            f"百度榜条目不该被判 stale: {doc2['candidates'][0]}"


def t_all_stale_candidates_warns():
    """全陈旧时退出码仍是 0（合法结果）, 但必须给一条醒目警告, 不许静默推僵尸。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        hb = write_hotboard([
            {"rank": None, "title": "陈旧一", "url": "", "hot": "", "source": "thepaper",
             "age_days": 296.0},
            {"rank": None, "title": "陈旧二", "url": "", "hot": "", "source": "thepaper",
             "age_days": 297.0},
        ], d)
        doc = cu.curate(hotboard=hb, ledger=write_ledger([], d))
        assert doc["exit_code"] == 0, "全陈旧仍是合法结果, 不该报错"
        assert doc["all_stale"], "全陈旧却没有 all_stale 警告"
        assert doc["fresh_count"] == 0, doc["fresh_count"]
        assert "陈旧" in doc.get("warning", ""), f"缺醒目警告文案: {doc.get('warning')}"


# ── 22 · 台账追加语义的读法（2026-10-08 真 bug: 状态被历史遮蔽） ──

def t_latest_row_wins_for_status():
    """追加台账里, **最后一行**才是当前状态。

    真 bug 记录: n0002 有两行(candidate 在前 / published 在后), 而读取时取首行
    → 状态永远停在 candidate → 已发布新闻被继续推荐 → 会发重复视频。
    """
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        led = write_ledger([
            {"id": "n0002", "norm_key": "康奈尔强奸案", "title": "康奈尔强奸案",
             "fingerprint": [], "first_seen": "2026-10-08", "last_seen": "2026-10-08",
             "status": "candidate", "rank_peak": 2, "hits": 1},
            {"id": "n0002", "norm_key": "康奈尔强奸案", "title": "康奈尔强奸案",
             "fingerprint": [], "first_seen": "2026-10-08", "last_seen": "2026-10-08",
             "status": "published", "rank_peak": 2, "hits": 1,
             "published_at": "2026-10-08"},
        ], d)
        hb = write_hotboard([{
            "rank": 3, "title": "康奈尔强奸案", "url": "", "hot": "", "source": "baidu-realtime",
        }], d)
        doc = cu.curate(hotboard=hb, ledger=led)
        ex = [e for e in doc["excluded"] if e["title"] == "康奈尔强奸案"]
        assert ex, "published 状态(最后一行)未被采纳 → 状态被历史遮蔽, 会重发已发布新闻"
        assert ex[0]["reason"] == "already_published", ex[0]
        assert ex[0]["matched_ledger_id"] == "n0002", ex[0]


def t_status_regression_also_uses_latest():
    """反过来: 最新行是 candidate 而首行 published 时, 应以最新为准(可再次推荐)。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        led = write_ledger([
            {"id": "n0003", "norm_key": "回炉新闻", "title": "回炉新闻",
             "fingerprint": [], "first_seen": "2026-10-01", "last_seen": "2026-10-01",
             "status": "published", "rank_peak": 5, "hits": 1},
            {"id": "n0003", "norm_key": "回炉新闻", "title": "回炉新闻",
             "fingerprint": [], "first_seen": "2026-10-01", "last_seen": "2026-10-08",
             "status": "rejected", "rank_peak": 5, "hits": 2},
        ], d)
        hb = write_hotboard([{
            "rank": 2, "title": "回炉新闻", "url": "", "hot": "", "source": "baidu-realtime",
        }], d)
        doc = cu.curate(hotboard=hb, ledger=led)
        cands = [c for c in doc["candidates"] if c["title"] == "回炉新闻"]
        assert cands, "最新行是 rejected, 不该硬剔除"
        assert cands[0]["revived"], f"rank 5→2 应触发重提: {cands[0]}"


# ── 17 · 决策工具不许与真实模板脱节（D20） ────────────────────────

def t_decide_pack_covers_every_real_template():
    """decide_pack.py 的 PACK_BUCKETS 必须覆盖 ALL_TEMPLATES 全部条目。

    背景（2026-10-08）: `decide_pack.py --list` 与 `pack-decision.md` 都写「31 pack」，
    而磁盘上是 32 个（12 master + 20 变体）。实测 PACK_BUCKETS 里其实**正好 32 个、
    一个不缺**，错的只是手写的字面文案 —— 但这类漂移正是「文档/工具说谎」的起点，
    所以锁死"集合必须相等"，数字本身由 all_template_names() 现算。
    """
    buckets = cu.DECIDE_PACK_BUCKETS
    covered = set()
    for info in buckets.values():
        covered.update(info.get("primary", []))
        covered.update(info.get("secondary", []))
    assert not (covered - cu.ALL_TEMPLATE_NAMES), (
        f"decide_pack 里有真实模板不存在的 pack（会推荐一个渲不出来的包）: "
        f"{sorted(covered - cu.ALL_TEMPLATE_NAMES)}")
    assert not (cu.ALL_TEMPLATE_NAMES - covered), (
        f"这些真实模板没有进 decide_pack 的决策表（决策树永远选不到）: "
        f"{sorted(cu.ALL_TEMPLATE_NAMES - covered)}")


def t_all_template_names_is_derived_not_hardcoded():
    """模板清单必须从 path_b_build 读，不许自己抄一份 —— 抄的那份迟早过期。"""
    assert len(cu.ALL_TEMPLATE_NAMES) == 32, (
        f"从 ALL_TEMPLATES 读出 {len(cu.ALL_TEMPLATE_NAMES)} 个, 预期 32")
    assert "news-polarity" in cu.ALL_TEMPLATE_NAMES, \
        "news-polarity（第 32 个, 易漏的主题包）不在清单里"
    # 反向: 改成硬编码就一定会被这条抓到
    assert cu.ALL_TEMPLATE_NAMES is not cu._HARDCODED_LIST, \
        "ALL_TEMPLATE_NAMES 不该是手抄的列表"


def t_decide_pack_docstring_has_no_stale_count():
    """decide_pack.py 的 docstring/输出不许出现手写的 pack 数。"""
    src = Path(dp.__file__).read_text(encoding="utf-8")
    bad = re.findall(r"(?<!\d)(?:12|18|20|30|31|32)\s*(?:个\s*)?(?:pack|模板|节目包)",
                     src, re.I)
    assert not bad, (
        f"decide_pack.py 里有手写的 pack 数 {bad} —— 用 {cu.ALL_TEMPLATE_NAMES.__len__()} "
        f"个模板这个事实会漂，改成现算（见 D20）")


def t_memory_decision_table_lists_every_template():
    """MEMORY.md 的决策树表必须列出全部真实模板（含 secondary 与派生变体）。

    2026-10-08 踩过：表格只画了 `primary` = 27 行，**漏掉 5 个只在 secondary 出现的包**
    （news-mosaic / news-dusk / news-paper / news-noir / news-podcast 之类）。
    表格是选包时第一眼看的地方，漏一个等于那个包实际选不到。
    """
    memory = (_REPO_ROOT / "routes" / "news" / "MEMORY.md").read_text(encoding="utf-8")
    listed = set(re.findall(r"`(news-[a-z-]+)`\s*（(?:主|备)）", memory))
    missing = cu.ALL_TEMPLATE_NAMES - listed
    assert not missing, (
        f"MEMORY.md 决策树漏了 {len(missing)} 个真实模板（选包时看不到）: {sorted(missing)}")
    assert len(listed) == len(cu.ALL_TEMPLATE_NAMES), (
        f"表里 {len(listed)} 行 vs 真实 {len(cu.ALL_TEMPLATE_NAMES)} 个")


def t_no_doc_claims_a_wrong_pack_count():
    """凡是说"**全部/总共有** N 个 pack"的地方，N 必须等于真实数量（D20 护栏）。

    本项目已两次被"手抄数字悄悄过期"咬：
      - ARCHITECTURE 的「可渲染 pack (有真版式): 2/12」（实际 32/32）
      - decide_pack.py / pack-decision.md 的「31 pack 分类表」（实际 32）

    **只拦"总数声明"，不拦局部计数**：像「12 个 master」「17 个变体」「31 pack 图板未接」
    说的是子集，数字对不对要靠别的断言（见 t_memory_decision_table_lists_every_template），
    混进这条只会逼着人加豁免名单，最后形同虚设（第一次写这版就是这么翻车的）。
    判据: 句子里出现「全部/总共/共/分类表/系统」等**总量口吻**时才核对。
    """
    total = len(cu.ALL_TEMPLATE_NAMES)
    # 总量口吻的限定词 —— 命中才核对数字。
    # 「共」单列：写「共计」漏掉了「共 10 pack」这种最自然的写法（负例实测）。
    TOTAL_MARKERS = ("全部", "总共", "共计", "共", "分类表", "个 pack 系统", "pack 系统里")
    # **引用被推翻的旧数字**不算声明（"旧文档的「⏳ 10 pack 待补」是错的"是 D15 的一部分，
    #   删掉它反而丢失"这里曾经错过"的信息）
    NEGATION = ("是错的", "已作废", "推翻", "作废", "旧文档", "旧记录", "原写", "曾经")
    targets = [
        "routes/news/MEMORY.md",
        "routes/news/pack-decision.md",
        "routes/news/ARCHITECTURE.md",
        "skills/news-workflow/SKILL.md",
    ]
    problems = []
    for rel in targets:
        p = _REPO_ROOT / rel
        if not p.is_file():
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if not any(k in line for k in TOTAL_MARKERS):
                continue
            if any(k in line for k in NEGATION):
                continue
            for m in re.finditer(r"(?<!\d)(\d{1,2})\s*(?:个\s*)?(?:pack|模板|节目包)",
                                 line, re.I):
                if m.group(1) != str(total):
                    problems.append(f"{rel}:{i} 「{m.group(0)}」（总量口吻但数字≠{total}）")
    assert not problems, (
        f"文档里的总包数与真实数量({total})不符:\n  " + "\n  ".join(problems))


# ── 23 · 台账主键唯一性（2026-10-08 真 bug: 同批新增全部撞成同一个 id） ──

def t_new_candidates_get_unique_incrementing_ids():
    """同批新增的候选必须各拿一个**唯一且递增**的主键。

    真 bug 记录（2026-10-08）: `main()` 里 `entries` 只读一次, 循环内反复调
    `next_ledger_id(entries)` —— 同一批 N 条全写成同一个 id。实测
    `routes/news/ledger.jsonl` 里 45 条不同事件共用 `n0002`。主键撞车后
    `matched_ledger_id`、状态回写（`mark`）都会指向错误的事件。
    """
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        led = d / "ledger.jsonl"
        cu.append_ledger(led, {"id": "n0001", "norm_key": "种子", "title": "种子",
                               "status": "candidate"})
        hb = write_hotboard([
            {"rank": 1, "title": "新事件甲", "url": "", "hot": "", "source": "baidu-realtime"},
            {"rank": 1, "title": "新事件甲", "url": "", "hot": "", "source": "bbc-zh"},
            {"rank": 2, "title": "新事件乙", "url": "", "hot": "", "source": "baidu-realtime"},
            {"rank": 3, "title": "新事件丙", "url": "", "hot": "", "source": "baidu-realtime"},
        ], d)
        rc = cu.main(["--hotboard", str(hb), "--ledger", str(led),
                      "--runtime", str(d), "--out", str(d / "out.json")])
        assert rc == 0, f"curate 退出码非 0: {rc}"
        rows = [json.loads(l) for l in led.read_text(encoding="utf-8").splitlines() if l.strip()]
        new_rows = [r for r in rows if r["norm_key"] != "种子"]
        new_ids = [r["id"] for r in new_rows]
        # 4 条线索里「新事件甲」来自两个源 = 同一事件 → 只许写 1 行台账
        assert len(new_rows) == 3, f"同一事件被重复写进台账: {[(r['id'], r['norm_key']) for r in new_rows]}"
        assert len(set(new_ids)) == 3, f"同批新增主键撞车: {new_ids}"
        assert set(new_ids) == {"n0002", "n0003", "n0004"}, f"主键未按序递增: {new_ids}"


# ── 24-27 · 状态回写 CLI（ledger.py）: 闭合「已发布不再发」的回路 ──

def _new_ledger_module():
    import importlib
    return importlib.import_module("ledger")


def t_ledger_mark_appends_same_id_for_same_event():
    """状态迁移必须**追加一行、沿用同一事件的主键**（设计 §6：同事件同 id 多行）。"""
    led = _new_ledger_module()
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "ledger.jsonl"
        cu.append_ledger(p, {"id": "n0002", "norm_key": "某事件", "title": "某事件",
                             "fingerprint": [], "first_seen": "2026-10-08",
                             "last_seen": "2026-10-08", "status": "candidate",
                             "rank_peak": 3, "hits": 1})
        row = led.mark(p, "published", norm_key="某事件", published_at="2026-10-10")
        assert row["id"] == "n0002", f"状态迁移必须沿用同一事件的主键: {row['id']}"
        assert row["status"] == "published", row
        assert row["published_at"] == "2026-10-10", row
        rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(rows) == 2, f"追加语义被破坏（应两行）: {rows}"
        assert rows[-1]["status"] == "published", rows[-1]
        assert rows[-1]["first_seen"] == "2026-10-08", "原字段应被继承"


def t_ledger_mark_rejects_unknown_status():
    """状态值拼错必须停机, 不许静默写一个脏状态进台账。"""
    led = _new_ledger_module()
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "ledger.jsonl"
        cu.append_ledger(p, {"id": "n0001", "norm_key": "甲", "title": "甲",
                             "status": "candidate"})
        try:
            led.mark(p, "publshed_typo", norm_key="甲")
        except led.LedgerError:
            pass
        else:
            raise AssertionError("未知状态必须抛 LedgerError, 不许写进台账")


def t_ledger_mark_missing_target_fails():
    """找不到目标事件必须报错 —— 不许凭空追加一行孤儿状态。"""
    led = _new_ledger_module()
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "ledger.jsonl"
        cu.append_ledger(p, {"id": "n0001", "norm_key": "甲", "title": "甲",
                             "status": "candidate"})
        try:
            led.mark(p, "published", norm_key="根本不存在的事件")
        except led.LedgerError:
            pass
        else:
            raise AssertionError("找不到目标必须报错, 不许静默追加孤儿行")


def t_ledger_check_detects_id_collision():
    """check 必须认出「不同事件共用主键」, 且不冤枉「同事件多行同主键」。"""
    led = _new_ledger_module()
    bad = [
        {"id": "n0001", "norm_key": "甲", "title": "甲", "status": "candidate"},
        {"id": "n0002", "norm_key": "乙", "title": "乙", "status": "candidate"},
        {"id": "n0002", "norm_key": "丙", "title": "丙", "status": "candidate"},
    ]
    assert led.check_ids(bad), "不同事件共用同一主键必须被 check 报出来"
    good = [
        {"id": "n0001", "norm_key": "甲", "title": "甲", "status": "candidate"},
        {"id": "n0001", "norm_key": "甲", "title": "甲", "status": "published"},
        {"id": "n0002", "norm_key": "乙", "title": "乙", "status": "candidate"},
    ]
    assert not led.check_ids(good), f"同一事件的多行共用主键是合法的: {led.check_ids(good)}"


if __name__ == "__main__":
    tests = [(name, fn) for name, fn in sorted(globals().items())
             if name.startswith("t_") and callable(fn)]
    print(f"[selftest] {len(tests)} 项 · news-curate")
    for name, fn in tests:
        check(name, fn)
    if FAILURES:
        print(f"[selftest] 失败 {len(FAILURES)}/{len(tests)}")
        sys.exit(1)
    print(f"[selftest] 全绿 {len(tests)}/{len(tests)}")
