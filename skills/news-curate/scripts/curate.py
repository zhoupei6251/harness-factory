#!/usr/bin/env python3
"""news-curate — 选题策展层（零成本去重 + 热度排序）。

设计文档: routes/news/DESIGN-dedup.md  |  配套断言: curate_selftest.py

职责边界（硬约束，见设计 §3）:
  - collect.py 一行不改，本模块只**只读** hotboard 快照、只**写** ledger + curated 产物
  - 本层只管"选不选"，不管"真不真" —— fact-check 硬门禁在下游，本层不豁免任何东西
  - 零付费：不引入任何 API key / 按次计费 / 云端模型调用

**L2 永不自动剔除**（设计 D2）：中文短标题的 n-gram 特征无法同时做到"认得出同事件"
与"分得开不同事件"（三轮实测数据见设计 §5），所以 L2 只标 needs_review 交给人看。
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

# ── 常量：阈值全部具名，禁散落字面量（设计 §5 / 测试 8 依赖这一点） ──

#: L2 相似度低于此值 → 不提示（实测 0.167 / 0.083 属此区）
L2_REVIEW_LOW = 0.30
#: L2 相似度高于此值 → needs_review: high（实测 1.174 / 2.435 属此区）
L2_REVIEW_HIGH = 0.60
#: 榜内名次权重上限（rank 越靠前得分越高）
RANK_SCORE_MAX = 6.0
#: **只有这些源的 rank 是热度**。RSS 的 rank 只是 feed 内条目序号，不是热度 ——
#: 2026-10-08 真实数据: 4 个源各有 1 条 rank=1, 实为 4 条不同新闻, 按热度加权会并列。
RANKED_SOURCES = {"baidu-realtime"}
#: 条目新鲜度权重上限（仅对非榜源有意义）
FRESH_SCORE_MAX = 3.0
#: 新鲜度半衰期（天）：age_days 每翻倍扣一半
FRESH_HALFLIFE_DAYS = 3.0
#: 超过这个天数即打 stale 标记（实测 thepaper 297 天 / zaobao 48 天 / bbc-zh 1.2 天）
STALE_AFTER_DAYS = 7.0
#: 连续在榜每天加分
DAYS_SCORE_PER_DAY = 1.2
#: 连续在榜加分上限
DAYS_SCORE_MAX = 3.6
#: 每个额外信源命中加分
CROSS_SOURCE_SCORE_EACH = 1.5
#: 跨源加分上限
CROSS_SOURCE_SCORE_MAX = 3.0

#: 状态 → score 乘子（设计 §6）。0 = 硬剔除，不进 candidates
STATUS_WEIGHT = {
    "published": 0.0,   # 已发布：硬剔除
    "rendered": 0.0,    # 已成片：硬剔除
    "drafted": 0.3,     # 在途：降权但不丢
    "selected": 0.3,    # 已选中：降权但不丢
    "candidate": 0.6,   # 上次进候选没被选：轻微降权，留观察
    "rejected": 1.0,    # 人工否决：不降权（热度回升可重提）
    # 未在台账里的（None）用这个
    "": 1.0,
}

#: 硬剔除的状态 → excluded.reason 文案
HARD_EXCLUDE_REASON = {
    "published": "already_published",
    "rendered": "already_rendered",
}

#: 中文停用字（虚词/常见副词），做实体词抽取时剔除
STOPWORDS = set(
    "的了是在和与及对为把被将从于也就都还又要能有这那我你他她它们个"
    "一二三四五六七八九十个只已并等将不年月日日在上下前后中这那有过会要说"
    "让给但而却又再最很更太非常给据由从向往对于关于通过经过".split()
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LEDGER = REPO_ROOT / "routes" / "news" / "ledger.jsonl"
DEFAULT_RUNTIME = REPO_ROOT / ".harness-news-runtime"


# ── L1 归一化 ─────────────────────────────────────────────────────

def norm_key(title: str) -> str:
    """标题归一化键。沿用 collect.py:216 dedup() 的口径（去标点/空白，保留汉字）。

    注意: Python re 的 \\W 在 Unicode 模式下不删汉字, 这一点由测试 1 锁住。
    """
    if not title:
        return ""
    return re.sub(r"[\W_]+", "", title)


# ── L2 指纹（仅提示层, 见设计 D2） ─────────────────────────────────

def _raw_ngrams(text: str, sizes=(2, 3, 4, 5)) -> set[str]:
    out = set()
    for n in sizes:
        for i in range(len(text) - n + 1):
            out.add(text[i:i + n])
    return out


def _has_digit(tok: str) -> bool:
    return any(c.isdigit() for c in tok)


def _is_stopish(tok: str) -> bool:
    return bool(tok) and all(c in STOPWORDS for c in tok)


def fingerprint(title: str, cap: int = 12) -> list[str]:
    """事件指纹: 字符 bigram + 长实体词(3-5字, 剔停用字)。

    纯 stdlib，不引入分词器。短标题上本就稀疏 —— 这正是 L2 只能当提示层的原因。
    """
    t = norm_key(title)
    if not t:
        return []
    feats = set()
    for i in range(len(t) - 1):          # bigram
        g = t[i:i + 2]
        if not _is_stopish(g):
            feats.add(g)
    for g in _raw_ngrams(t, (3, 4, 5)):  # 长实体词, 判别力最高
        if not _is_stopish(g):
            feats.add("E" + g)
    return sorted(feats)[:cap]


def similarity(a: str, b: str) -> float:
    """加权覆盖度: (3*实体命中 + bigram命中) / min(两侧特征数)。0~N, 越大越像。"""
    fa, fb = set(fingerprint(a)), set(fingerprint(b))
    if not fa or not fb:
        return 0.0
    inter = fa & fb
    if not inter:
        return 0.0
    ent = {x for x in inter if x.startswith("E")}
    bg = inter - ent
    return (3 * len(ent) + len(bg)) / min(len(fa), len(fb))


def review_level(score: float) -> str | None:
    """L2 分 → needs_review 等级。None = 不提示。**永不返回 'exclude'**（D2）。"""
    if score >= L2_REVIEW_HIGH:
        return "high"
    if score >= L2_REVIEW_LOW:
        return "medium"
    return None


# ── 模板清单（从真实源现算, 不手抄 · D20） ──────────────────────────

def _load_all_template_names() -> frozenset[str]:
    """从 path_b_build.ALL_TEMPLATES 读真实模板清单。

    **为什么不写死列表**：本项目已经吃过两次亏 ——
      ① 文档写「2/12 可渲染」而磁盘上 32/32 全有真版式（ARCHITECTURE D15）
      ② decide_pack.py / pack-decision.md 写「31 pack」而实际 32 个
    两次都是"某处手抄了一个数字"然后悄悄过期。手抄的清单一定会漂，
    现算的清单跟得上。缺 path_b_build 时（单文件挪用）退化为空集，
    由调用方的测试负责报出来，不在这里假装有值。
    """
    try:
        scripts = REPO_ROOT / "skills" / "douyin-pro" / "scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        import path_b_build as pb  # noqa: PLC0415  (延迟导入: 避免硬依赖渲染器)
        return frozenset(pb.ALL_TEMPLATES)
    except Exception:  # noqa: BLE001
        return frozenset()


#: 真实模板名集合（32 个 = 12 master + 20 派生变体，2026-10-08 实测）
ALL_TEMPLATE_NAMES = _load_all_template_names()

#: 占位：仅供测试对比"不许退化成手抄列表"。真实值永远是现算的。
_HARDCODED_LIST: frozenset[str] = frozenset()

#: decide_pack 的决策表（跨目录 import；该脚本本身不 import 本模块，无循环依赖）
try:
    sys.path.insert(0, str(REPO_ROOT / "routes" / "news" / "scripts"))
    import decide_pack as _dp  # noqa: PLC0415
    DECIDE_PACK_BUCKETS = _dp.PACK_BUCKETS
except Exception:  # noqa: BLE001
    DECIDE_PACK_BUCKETS = {}


# ── 台账（只追加, 设计 §4.1） ─────────────────────────────────────

def read_ledger(path) -> list[dict]:
    """读台账。文件不存在 = 空台账（测试 15），不崩。"""
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            # R6: 坏行不许静默吞掉, 交给调用方从 failures 里看
            rows.append({"_bad_line": line})
    return rows


def append_ledger(path, entry: dict) -> None:
    """追加一行。永不原地改写（测试 11）。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def max_ledger_num(entries: list[dict]) -> int:
    """台账里出现过的最大主键序号（0 = 空台账）。"""
    mx = 0
    for e in entries:
        lid = str(e.get("id") or "")
        m = re.fullmatch(r"n(\d+)", lid)
        if m:
            mx = max(mx, int(m.group(1)))
    return mx


def next_ledger_id(entries: list[dict]) -> str:
    """下一个主键 —— **只用于单条追加**。

    ⚠️ 批量追加**不许**在循环里反复调它：传进来的 `entries` 是同一份快照，
    每次都会算出同一个 id（2026-10-08 真 bug：45 条不同事件全写成 `n0002`，
    主键撞车后 `matched_ledger_id` / 状态回写都会指向错误的事件）。
    批量场景改用 `max_ledger_num(entries) + 1` 起算，逐条自增。
    """
    return f"n{max_ledger_num(entries) + 1:04d}"


# ── 热度打分（只用免费信号, 设计 §7） ─────────────────────────────

def is_ranked_source(source: str) -> bool:
    """该源的 rank 是否代表热度。只有百度实时榜算（测试 17）。"""
    return source in RANKED_SOURCES


def rank_score(rank, source: str = "baidu-realtime") -> float:
    """榜内名次反向分。**非榜源直接 0 分**（测试 17/18）。

    rank=None(置顶) → 0 分, 不炸（测试 13）。
    置顶 ≠ 第一名（实测百度恰好 1 条 is_top, rank 为 null）。
    """
    if not is_ranked_source(source):
        return 0.0
    if rank is None:
        return 0.0
    try:
        r = int(rank)
    except (TypeError, ValueError):
        return 0.0
    if r < 1:
        return 0.0
    # 名次 1 得满分, 之后线性衰减到 0.05
    return RANK_SCORE_MAX * max(0.05, 1.0 - (r - 1) / 30.0)


def fresh_score(age_days) -> float:
    """新鲜度分: 半衰期衰减。age_days 缺失/解析不了 → 0 分, 不猜。"""
    if age_days is None:
        return 0.0
    try:
        a = float(age_days)
    except (TypeError, ValueError):
        return 0.0
    if a < 0:
        return FRESH_SCORE_MAX
    return FRESH_SCORE_MAX * (0.5 ** (a / FRESH_HALFLIFE_DAYS))


def _days_score(days: int) -> float:
    return min(DAYS_SCORE_MAX, max(0, days) * DAYS_SCORE_PER_DAY)


def _cross_source_score(n_sources: int) -> float:
    return min(CROSS_SOURCE_SCORE_MAX, max(0, n_sources - 1) * CROSS_SOURCE_SCORE_EACH)


def base_score(item: dict, days: int = 0, n_sources: int = 1) -> float:
    """基础热度分。**刻意不读 item['hot']** —— 实测该字段 80/80 恒为空（测试 12）。

    三个免费信号（设计 §7）: 榜内名次(仅百度榜) + 新鲜度(RSS 侧) + 跨源命中。
    """
    src = item.get("source", "")
    return round(
        rank_score(item.get("rank"), source=src)
        + fresh_score(item.get("age_days"))
        + _days_score(days)
        + _cross_source_score(n_sources),
        2,
    )


# ── 策展主流程 ────────────────────────────────────────────────────

def _days_on_board(norm: str, history: dict) -> int:
    return history.get(norm, 0)


def _load_history(d: Path) -> dict:
    """读 hotboard/history.jsonl → {norm_key: 出现天数}。不存在 = 无历史（首次运行）。"""
    p = Path(d) / "history.jsonl"
    hist: dict = {}
    if not p.exists():
        return hist
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        k = row.get("norm_key")
        if k:
            hist[k] = hist.get(k, 0) + 1
    return hist


def _append_history(d: Path, items: list[dict]) -> int:
    """把今日在榜的归一化键追加进 history.jsonl, 返回新增行数。"""
    p = Path(d) / "history.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with p.open("a", encoding="utf-8") as fh:
        for it in items:
            k = norm_key(it.get("title", ""))
            if not k:
                continue
            fh.write(json.dumps({"norm_key": k, "date": it.get("date", "")},
                                ensure_ascii=False) + "\n")
            n += 1
    return n


def curate(hotboard, ledger, history_dir=None, suggest_pack=None) -> dict:
    """策展主函数。纯逻辑, 不打网络。

    返回 curated 文档（设计 §4.2）。退出语义:
      - 正常完成           → exit_code 0
      - hotboard 不可读     → failures 非空, exit_code 1
      - 候选被排空           → **仍是 0**（合法业务结果, 设计 D6）
    """
    failures: list[str] = []
    hb_path = Path(hotboard)
    if not hb_path.exists():
        return {
            "curated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "cost": "zero",
            "input": {"path": str(hb_path), "count": 0},
            "ledger_entries": 0,
            "candidates": [],
            "excluded": [],
            "failures": [f"hotboard 不可读: {hb_path}"],
            "exit_code": 1,
        }

    try:
        doc = json.loads(hb_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "curated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "cost": "zero",
            "input": {"path": str(hb_path), "count": 0},
            "ledger_entries": 0,
            "candidates": [],
            "excluded": [],
            "failures": [f"hotboard 不是合法 JSON: {exc}"],
            "exit_code": 1,
        }

    items = doc.get("items") or []
    entries = [e for e in read_ledger(ledger) if "_bad_line" not in e]
    for bad in read_ledger(ledger):
        if "_bad_line" in bad:
            failures.append(f"台账有坏行已跳过: {bad['_bad_line'][:60]}")

    # 台账是**追加**语义：同一事件会有多行（candidate → published）。
    # 当前状态 = **最后一行**。取首行会让状态永远停在过时的 candidate，
    # 导致已发布的新闻被继续推荐 → 重发已发布视频（真 bug，测试 22 锁住）。
    by_norm: dict[str, dict] = {}
    for e in entries:
        k = e.get("norm_key")
        if k:
            by_norm[k] = e          # 后写覆盖前写 = 最后一行胜出

    hist = _load_history(Path(history_dir)) if history_dir else {}
    today = doc.get("date", "")

    # 跨源命中统计: 同一归一化标题在几个源出现过
    src_count: dict[str, set] = {}
    for it in items:
        src_count.setdefault(norm_key(it.get("title", "")), set()).add(it.get("source", ""))

    candidates, excluded, seen_norms = [], [], set()
    for it in items:
        title = it.get("title", "")
        key = norm_key(title)
        if not key:
            continue
        days = _days_on_board(key, hist)

        # ── L1：归一化精确匹配，唯一允许自动硬剔除的层级 ──
        led = by_norm.get(key)
        if led:
            st = led.get("status", "")
            reason = HARD_EXCLUDE_REASON.get(st)
            if reason:
                excluded.append({
                    "title": title,
                    "reason": reason,
                    "matched_ledger_id": led.get("id"),
                    "matched_norm_key": led.get("norm_key"),
                    "matched_status": st,
                    "level": "L1_exact",
                })
                continue
            if st == "rejected" and led.get("rank_peak"):
                cur_rank = it.get("rank")
                # 热度回升: 当前名次比历史最佳好 50% 以上 → 允许重提
                try:
                    if cur_rank is not None and int(cur_rank) <= max(1, int(led["rank_peak"]) * 0.5):
                        cand = _make_candidate(
                            it, key, days, len(src_count.get(key, ())), st,
                            suggest_pack=suggest_pack,
                            extra={
                                "revived": True,
                                "revive_reason": (
                                    f"曾被否决({led.get('id')}), 热度回升 "
                                    f"rank {led['rank_peak']}→{cur_rank}"
                                ),
                            },
                        )
                        candidates.append(cand)
                        seen_norms.add(key)
                        continue
                except (TypeError, ValueError):
                    pass

        cand = _make_candidate(
            it, key, days, len(src_count.get(key, ())),
            led.get("status", "") if led else "",
            suggest_pack=suggest_pack,
        )

        # ── L2：只提示，永不剔除（D2） ──
        # 比对对象是**台账里最相似的那一条**，不是"L1 撞上的那一条"。
        # 绑在 L1 结果上会漏掉真正该提示的情况：归一化键不同 → led 为 None →
        # 整段跳过，而那正是 L2 唯一存在的场景（同一事件、不同表述）。
        if not led and entries:
            best_id, best_sim = None, 0.0
            for e in entries:
                ek = e.get("norm_key")
                if not ek or ek == key:
                    continue
                sim = similarity(title, e.get("title") or ek)
                if sim > best_sim:
                    best_id, best_sim = e.get("id"), sim
            lvl = review_level(best_sim)
            if lvl and best_id:
                cand["needs_review"] = lvl
                cand["review_matched_id"] = best_id
                cand["review_similarity"] = round(best_sim, 3)
                cand["review_level_kind"] = "L2_similarity"

        candidates.append(cand)
        seen_norms.add(key)

    candidates.sort(key=lambda c: c.get("final_score", c.get("score", 0)), reverse=True)
    for i, c in enumerate(candidates, 1):
        c["position"] = i

    # 全陈旧时给醒目警告: 退出码仍是 0（合法结果）, 但不许静默推僵尸新闻（测试 21）
    fresh_count = sum(1 for c in candidates if not c.get("stale"))
    all_stale = bool(candidates) and fresh_count == 0
    warning = ""
    if all_stale:
        warning = (f"⚠ 今日 {len(candidates)} 条候选**全部陈旧**"
                   f"（> {STALE_AFTER_DAYS:g} 天），多半是采集源滞后而非今天没热点。"
                   f"补源或改看百度榜，别拿这些当今日新闻发。")
    elif candidates and fresh_count == 0:
        warning = "⚠ 无非陈旧候选"

    return {
        "curated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "cost": "zero",
        "date": today,
        "input": {"path": str(hb_path), "count": len(items)},
        "ledger_entries": len(entries),
        "candidates": candidates,
        "excluded": excluded,
        "failures": failures,
        "fresh_count": fresh_count,
        "all_stale": all_stale,
        "warning": warning,
        "exit_code": 0,
    }


def _make_candidate(item, key, days, n_sources, ledger_status, suggest_pack=None, extra=None) -> dict:
    s = base_score(item, days=days, n_sources=n_sources)
    w = STATUS_WEIGHT.get(ledger_status, STATUS_WEIGHT[""])
    cand = {
        "title": item.get("title", ""),
        "source": item.get("source", ""),
        "rank": item.get("rank"),
        "age_days": item.get("age_days"),
        "url": item.get("url", ""),
        "is_top": bool(item.get("is_top")),
        "score": s,
        "status_weight": w,
        "final_score": round(s * w, 2),
        "days_on_board": days,
        "ledger_status": ledger_status or None,
        "norm_key": key,
    }
    if suggest_pack:
        try:
            cand["suggested_pack"] = suggest_pack(item.get("title", ""))
        except Exception:  # noqa: BLE001  建议 pack 失败不许毁掉整条候选
            cand["suggested_pack"] = None
    # 陈旧标记: 靠分数沉底不够, 清单里要能一眼看见（测试 20）
    age = item.get("age_days")
    if age is not None:
        try:
            a = float(age)
            if a > STALE_AFTER_DAYS:
                cand["stale"] = True
                cand["stale_age_days"] = a
        except (TypeError, ValueError):
            pass
    if extra:
        cand.update(extra)
    cand["why"] = _why(cand)
    return cand


def _why(c: dict) -> str:
    bits = []
    src = c.get("source", "")
    if is_ranked_source(src) and c.get("rank") is not None:
        bits.append(f"百度榜 rank={c['rank']}")
    elif is_ranked_source(src):
        bits.append("百度榜置顶条目（rank=null，不当第一名）")
    else:
        bits.append(f"{src} feed 条目（无热度名次）")
    if c.get("age_days") is not None:
        bits.append(f"发布距今 {c['age_days']} 天")
    if c.get("stale"):
        bits.append(f"⚠ 陈旧（>{STALE_AFTER_DAYS:g} 天，别当今日新闻）")
    if c.get("days_on_board"):
        bits.append(f"连续在榜 {c['days_on_board']} 天")
    if c.get("ledger_status"):
        bits.append(f"台账已有记录({c['ledger_status']})→ 降权 ×{c['status_weight']}")
    if c.get("revived"):
        bits.append(c.get("revive_reason", "曾被否决，热度回升"))
    if c.get("needs_review"):
        bits.append(
            f"⚠ L2 相似 {c.get('review_similarity')} 与台账 "
            f"{c.get('review_matched_id')} 疑似同事件（{c['needs_review']}）——需人工确认"
        )
    return "；".join(bits) if bits else "无附加依据"


# ── CLI ───────────────────────────────────────────────────────────

def _load_suggester():
    """复用 routes/news/scripts/decide_pack.py 的推荐（存在才接，不强制）。"""
    p = REPO_ROOT / "routes" / "news" / "scripts" / "decide_pack.py"
    if not p.exists():
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("decide_pack", p)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return getattr(mod, "recommend", None) or getattr(mod, "decide", None)
    except Exception:  # noqa: BLE001
        return None
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="选题策展层：台账去重 + 免费热度排序")
    ap.add_argument("--hotboard", default=None, help="采集快照路径（默认 hotboard/<date>.json）")
    ap.add_argument("--ledger", default=str(DEFAULT_LEDGER), help="台账路径")
    ap.add_argument("--out", default=None, help="策展产物路径（默认 curated/<date>.json）")
    ap.add_argument("--runtime", default=str(DEFAULT_RUNTIME), help="运行时根目录")
    ap.add_argument("--record-history", action="store_true",
                    help="把今日在榜标题追加进 history.jsonl（连续在榜天数用）")
    ap.add_argument("--top", type=int, default=10, help="候选清单条数（默认 10）")
    ap.add_argument("--print", dest="do_print", action="store_true", help="打印候选表")
    args = ap.parse_args(argv)

    runtime = Path(args.runtime)
    today = dt.datetime.now().astimezone().date().isoformat()
    hb = args.hotboard or str(runtime / "hotboard" / f"{today}.json")

    doc = curate(hotboard=hb, ledger=args.ledger, history_dir=runtime)
    if doc["exit_code"] != 0:
        for f in doc["failures"]:
            print(f"  ! {f}", file=sys.stderr)
        print("策展失败: hotboard 不可读（不覆盖上一次结果）", file=sys.stderr)
        return 1

    if args.record_history:
        try:
            raw = json.loads(Path(hb).read_text(encoding="utf-8"))
            for it in raw.get("items", []):
                it.setdefault("date", today)
            n = _append_history(runtime, raw.get("items", []))
            print(f"  history: 追加 {n} 行 → {runtime / 'history.jsonl'}")
        except Exception as exc:  # noqa: BLE001
            doc["failures"].append(f"history 追加失败: {type(exc).__name__}: {exc}")

    # 新出现的候选入台账（只写 candidate —— curate 没有信息判断别的状态, 设计 §6）
    entries = read_ledger(args.ledger)
    known = {e.get("norm_key") for e in entries if "_bad_line" not in e}
    # 同一事件可能来自多个源（百度榜 + RSS）→ 归一化键相同。台账是**事件级**的，
    # 同一事件只许写一行，否则 hits / 状态回写会分裂。按归一化键去重，保首条（已按分排序）。
    new, seen_new = [], set()
    for c in doc["candidates"]:
        k = c["norm_key"]
        if k in known or k in seen_new:
            continue
        seen_new.add(k)
        new.append(c)
    # 主键逐条递增：**不许**在循环里重算 `next_ledger_id(entries)`
    # （同一快照 → 每次同一个 id，见 max_ledger_num 的注释）。
    next_num = max_ledger_num(entries) + 1
    for c in new:
        append_ledger(args.ledger, {
            "id": f"n{next_num:04d}",
            "norm_key": c["norm_key"],
            "title": c["title"],
            "fingerprint": fingerprint(c["title"]),
            "first_seen": today,
            "last_seen": today,
            "status": "candidate",
            "rank_peak": c["rank"] if isinstance(c.get("rank"), int) else None,
            "hits": 1,
        })
        next_num += 1
    if new:
        print(f"  ledger: 新增 {len(new)} 条 candidate → {args.ledger}")

    out = args.out or str(runtime / "curated" / f"{today}.json")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[curate] 输入 {doc['input']['count']} 条 · 台账 {doc['ledger_entries']} 条 · "
          f"候选 {len(doc['candidates'])}（新鲜 {doc.get('fresh_count', '?')}）"
          f" · 剔除 {len(doc['excluded'])}")
    if doc.get("warning"):
        print(f"  {doc['warning']}")
    if doc["failures"]:
        for f in doc["failures"]:
            print(f"  ! {f}", file=sys.stderr)

    if args.do_print:
        print()
        for c in doc["candidates"][: args.top]:
            flag = " ⚠REVIEW" if c.get("needs_review") else ""
            rv = " ✨REVIVED" if c.get("revived") else ""
            st = " ⚠STALE" if c.get("stale") else ""
            print(f"  #{c['position']} [{c['final_score']:>5}] {c['title'][:34]}"
                  f"{flag}{rv}{st}")
            print(f"       {c['why']}")

    print(f"[curate] → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
