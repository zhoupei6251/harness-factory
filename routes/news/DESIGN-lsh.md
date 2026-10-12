# DESIGN-lsh — datasketch MinHash LSH 接入 news-curate L2

> Tier 1 合并文档（spec + plan + verify 合一，2026-10-12）
> 配套: [DESIGN-dedup.md](DESIGN-dedup.md)（旧设计，本设计**仅替换其 §5 L2 实现**，不动 §1-4 / §6-7）

---

## 1. 改动范围（Tier 1 触发判据）

| 项 | 判定 |
|---|---|
| 改动文件数 | 3（新增 `lsh_dedup.py` + 改 `curate.py` + 改 `curate_selftest.py`） |
| 改动行数（估） | ~140 行（lsh_dedup.py ≈ 80 + curate.py ≈ 30 diff + selftest ≈ 30） |
| 公共 API 改动 | 否（`similarity(a, b) -> float` 签名沿用；`review_level(score) -> str \| None` 沿用） |
| 数据库 schema 改动 | 否（台账字段不变） |
| 构建脚本改动 | 否（`requirements.txt` 不在本仓，datasketch 由用户 pip 装到 `.venv`） |
| 多模块联动 | 否（仅 news-curate skill 内） |
| 新依赖 | datasketch（PyPI BSD-3，本地 CPU，**零云费零计费**） |

✅ **触发 Tier 1**，走主 Agent 直做（不开 worktree、不派子 Agent）。

---

## 2. 现状与动机

### 2.1 现状 L2 实现（要替换的）

`skills/news-curate/scripts/curate.py:128-138` `similarity()` 当前公式：

```
similarity(a, b) = (3 * 实体命中 + bigram 命中) / min(两侧特征数)
范围 0 ~ N，实测同事件 0.000~2.435 / 不同事件 0.000~1.615
```

L2 扫描在 `curate.py:456-470`，对**每条**未 L1 命中的候选，与台账**全部 N 条**做相似度，取 max → 标 `needs_review`。

### 2.2 已承认的天花板

[DESIGN-dedup.md](DESIGN-dedup.md) §5 三轮实测记录：

| 方案 | 同一事件 | 不同事件 | 结论 |
|---|---|---|---|
| n-gram Jaccard | 0.000~0.286 | 0.000 | 阈值 0.45 100% 漏判 |
| 覆盖度 | 0.000~0.556 | 0.000 | "发布新规" vs "新规施行" 0.083 |
| **实体加权（现行）** | 0.000~2.435 | 0.000~**1.615** | 判别力强但误杀致命 |

设计 D2 已锁定：**L2 永不自动剔除**，靠人工判 `⚠REVIEW`。但实体加权方案的 0.000~2.435 同事件跨度（最低 0.000 = 完全漏判）意味着部分真实同事件配对落在 `L2_REVIEW_LOW=0.30` 以下，**漏判 = 同事件被当作新选题推荐**，**这是真问题**。

### 2.3 为什么换 MinHash

datasketch MinHash 在 Google/Microsoft 近重复检测上是工业标准（自 2007）。相比实体加权：

1. **Jaccard 范围 [0, 1]**，阈值可比性强（消除 0~N 调参噩梦）
2. **LSH 预滤**：台账 N=1000 时 L2 查询 O(N) → O(1) 候选 → O(k) 精确比对
3. **零云费**：纯 stdlib 之外只多 datasketch，**本机 CPU 推理** —— 不调云端模型
4. **不引入 embedding**：仍是 char trigram（不是语义向量），保留"短中文标题稀疏"的设计 D2 承认的事实

---

## 3. 设计

### 3.1 新文件 `skills/news-curate/scripts/lsh_dedup.py`

```python
"""L2 跨源近重复检测 —— datasketch MinHash LSH (Tier 1, 2026-10-12)。

设计要点（routes/news/DESIGN-dedup.md D2）:
  - L2 永不自动剔除 (回退到 needs_review, 永不进 excluded)
  - 不读 hot, 不调 embedding, 零云费

替代 curate.py:128 similarity() 的实体加权实现; 阈值从 0~N 改 0~1,
语义与旧 L2_REVIEW_LOW/HIGH 在定性上对齐 (0.30 / 0.60)。
"""
from datasketch import MinHash, MinHashLSH

# ── 常量 ─────────────────────────────────────────────────────────
NGRAM_SIZE = 3       # char trigram; 与旧实体加权 n=(3,4,5) 的下限对齐
NUM_PERM = 128       # datasketch 默认, ~10ms/条, 精度足够
LSH_THRESHOLD = 0.30 # LSH 预滤阈值 = 命中 REVEW 起点; 同阈值也复用 L2_REVIEW_LOW

# 复刻 curate.py:69 STOPWORDS (防止"今天今日"/"新规新规"这种虚匹配)
STOPWORDS = set(
    "的了是在和与及对为把被将从于也就都还又要能有这那我你他她它们个"
    "一二三四五六七八九十个只已并等将不年月日日在上下前后中这那有过会要说"
    "让给但而却又再最很更给".split() +                # 复刻 curate.py:69-71
    ["新的", "今日", "今天", "新闻", "消息"]           # 实测噪声词
)

REVIEW_LOW = 0.30     # 旧 L2_REVIEW_LOW 同值
REVIEW_HIGH = 0.60    # 旧 L2_REVIEW_HIGH 同值

def _is_stopish_trigram(g: str) -> bool:
    return bool(g) and all(c in STOPWORDS for c in g)

def _trigrams(title: str) -> set[str]:
    """char trigram 集合。空串返回空集 (R6 防崩)."""
    if not title:
        return set()
    out = set()
    for i in range(len(title) - NGRAM_SIZE + 1):
        g = title[i:i + NGRAM_SIZE]
        if not _is_stopish_trigram(g):
            out.add(g)
    return out

def _minhash(title: str) -> MinHash:
    m = MinHash(num_perm=NUM_PERM)
    for g in _trigrams(title):
        m.update(g.encode("utf-8"))
    return m

def jaccard(a: str, b: str) -> float:
    """Jaccard on char trigrams. 范围 [0, 1]. 替代 curate.py:128 similarity()."""
    ta, tb = _trigrams(a), _trigrams(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)

def build_index(entries: list[dict]) -> tuple[MinHashLSH, dict[str, MinHash]]:
    """为台账建 LSH 索引, 跑一次。
    
    返回 (lsh_index, {norm_key -> MinHash}).
    空台账 / 全空标题容错 (R6): 返回空索引 + 空 dict, 不抛.
    """
    lsh = MinHashLSH(threshold=LSH_THRESHOLD, num_perm=NUM_PERM)
    mhashes: dict[str, MinHash] = {}
    for e in entries:
        k = e.get("norm_key", "") or ""
        if not k:
            continue
        m = _minhash(e.get("title", "") or "")
        if len(m) == 0:
            continue
        lsh.insert(k, m)
        mhashes[k] = m
    return lsh, mhashes

def find_l2_hits(query_title: str, lsh: MinHashLSH,
                 entries: list[dict], exclude_norm: str) -> list[tuple[str, float]]:
    """LSH 预滤 + Jaccard 精确比对。返回 [(matched_id, sim)], 已按 sim 降序。
    
    exclude_norm: 同主键台账行不参与 (curate.py:460 的 ek == key 检查复刻).
    """
    if not query_title or not entries:
        return []
    qm = _minhash(query_title)
    if len(qm) == 0:
        return []
    cands = set(lsh.query(qm))
    if exclude_norm:
        cands.discard(exclude_norm)
    by_norm = {e.get("norm_key"): e for e in entries}
    hits = []
    for ck in cands:
        e = by_norm.get(ck)
        if not e:
            continue
        sim = jaccard(query_title, e.get("title", "") or "")
        hits.append((e.get("id", ""), sim))
    hits.sort(key=lambda h: h[1], reverse=True)
    return hits
```

### 3.2 改 `curate.py`

#### 3.2.1 `similarity()` body 替换（line 128-138）

```python
# 旧: 实体加权 (DESIGN-dedup.md §5 天花板已承认)
# def similarity(a, b):
#     fa, fb = set(fingerprint(a)), set(fingerprint(b))
#     ... 加权覆盖度公式 ...

# 新: MinHash Jaccard on char trigram (lsh_dedup.py 提供)
from lsh_dedup import jaccard as _lsh_jaccard  # noqa: E402

def similarity(a: str, b: str) -> float:
    """MinHash-on-CharTrigram Jaccard. 范围 [0, 1]. (2026-10-12 起替代旧实体加权)"""
    return _lsh_jaccard(a, b)
```

#### 3.2.2 `review_level()` 阈值常量改来源（line 26-28, 141-148）

```python
# 旧:
# L2_REVIEW_LOW = 0.30
# L2_REVIEW_HIGH = 0.60
# def review_level(score): if score >= L2_REVIEW_HIGH / >= L2_REVIEW_LOW ...

# 新: 保留旧名以兼容 (curate_selftest / 调用方不动); 真实值从 lsh_dedup 拉
from lsh_dedup import REVIEW_LOW as L2_REVIEW_LOW, REVIEW_HIGH as L2_REVIEW_HIGH  # noqa: E402
```

#### 3.2.3 L2 扫描循环（line 456-470）改 LSH 预滤

```python
# 旧: 对每条候选 O(N) 扫描全台账
# if not led and entries:
#     best_id, best_sim = None, 0.0
#     for e in entries:
#         ek = e.get("norm_key")
#         if not ek or ek == key: continue
#         sim = similarity(title, e.get("title") or ek)
#         if sim > best_sim: best_id, best_sim = e.get("id"), sim
#     ...

# 新: 在 curate() 入口 (line ~387) 建一次 LSH 索引, 每条候选 O(1) 预滤 + O(k) 精确比对
from lsh_dedup import build_index as _lsh_build, find_l2_hits as _lsh_query  # noqa: E402

# curate() 入口, 读完台账后立刻建:
#   lsh_index, _ = _lsh_build(entries)   # ← 加在 by_norm: dict 构造之后 (line ~392)

# 替换原 line 456-470:
if not led and entries:
    hits = _lsh_query(title, lsh_index, entries, exclude_norm=key)
    if hits:
        best_id, best_sim = hits[0]   # 已按 sim 降序
        lvl = review_level(best_sim)
        if lvl and best_id:
            cand["needs_review"] = lvl
            cand["review_matched_id"] = best_id
            cand["review_similarity"] = round(best_sim, 3)
            cand["review_level_kind"] = "L2_lsh_minhash"
```

### 3.3 加 `curate_selftest.py` 新断言

```python
# ── 28 · LSH MinHash L2 实现 (2026-10-12 替代 docstring 取长) ────

def t_l2_minhash_detects_real_same_event():
    """71岁老人...3700元养老金 vs 拾荒老人...3700元养老金 (原 t001 案例)
    → Jaccard on char trigram ≥ 0.30 → 标 medium needs_review."""
    sim = cu.similarity(
        "71岁老人不知自己每月有3700元养老金",
        "拾荒老人每月3700元养老金",
    )
    assert sim >= 0.30, f"真同事件配对漏判: {sim}"
    assert cu.review_level(sim) == "medium", sim


def t_l2_minhash_drops_unrelated():
    """暴雨已致3人死亡 vs 某地暴雨 (不同事件)
    → Jaccard ≈ 0 → 不标 needs_review."""
    sim = cu.similarity("暴雨已致3人死亡", "某地暴雨")
    assert sim < 0.30, f"无关不该滤: {sim}"


def t_l2_lsh_threshold_consistent():
    """常量 L2_REVIEW_LOW/HIGH 在 curate 与 lsh_dedup 共享同一来源."""
    from lsh_dedup import REVIEW_LOW, REVIEW_HIGH
    assert cu.L2_REVIEW_LOW == REVIEW_LOW
    assert cu.L2_REVIEW_HIGH == REVIEW_HIGH
    assert cu.L2_REVIEW_HIGH > cu.L2_REVIEW_LOW


def t_l2_lsh_build_handles_empty():
    """空台账建索引不崩 (R6)."""
    from lsh_dedup import build_index
    lsh, mh = build_index([])
    assert lsh is not None
    assert mh == {}


def t_l2_lsh_query_handles_empty_title():
    """候选空标题查询不崩 (R6), 不标 needs_review."""
    from lsh_dedup import build_index, find_l2_hits
    entries = [{"id": "n0001", "norm_key": "甲", "title": "甲"}]
    lsh, _ = build_index(entries)
    hits = find_l2_hits("", lsh, entries, exclude_norm="")
    assert hits == []


def t_l2_lsh_excludes_self_norm():
    """同 norm_key 不参与 L2 自比 (curate.py:460 复刻)."""
    from lsh_dedup import build_index, find_l2_hits
    entries = [{"id": "n0001", "norm_key": "同标题", "title": "同标题"}]
    lsh, _ = build_index(entries)
    hits = find_l2_hits("同标题", lsh, entries, exclude_norm="同标题")
    assert hits == [], f"自比进了结果: {hits}"
```

---

## 4. 证据段（合并文档必填，§3 模板）

### 4.1 改动触及的代码 (R1)

`[codebase-memory-mcp 不可用，已降级]` 原因：手工 Read 已完整覆盖（curate.py / curate_selftest.py 全文）；替代手段 = Read 直接取证。

| 符号 | qualified_name | 现有行数 | 角色 |
|---|---|---|---|
| `similarity` | `skills.news-curate.scripts.curate.similarity` | 11 | **直接改**（body 替换为 `jaccard`） |
| `review_level` | `skills.news-curate.scripts.curate.review_level` | 7 | 调用者；阈值常量来源换为 lsh_dedup |
| `curate` (L2 扫描循环) | `skills.news-curate.scripts.curate.curate` | ~140 | **改 L2 扫描**：line 456-470 |
| `fingerprint` | `skills.news-curate.scripts.curate.fingerprint` | 17 | 旧算法本体，本改动**保留**（暂不删，避免一次性破坏面） |

### 4.2 影响面

- **inbound callers (谁调我)**:
  - `skills/news-curate/scripts/curate_selftest.py:t_l2_marks_needs_review_not_excluded` (line 113) — 锁同事件低分不剔除
  - `skills/news-curate/scripts/curate_selftest.py:t_l2_mid_similarity_flags_review` (line 134) — 锁同事件中分标 needs_review
  - `skills/news-curate/scripts/curate_selftest.py:t_l2_high_similarity_flags_high_risk` (line 157) — 锁阈值 > 关系
  - `skills/news-curate/scripts/curate_selftest.py:t_l2_never_silently_drops` (line 179) — **D2 铁律**，防后人偷偷加回自动剔除
- **outbound callees (我调谁)**:
  - `datasketch.MinHash` / `datasketch.MinHashLSH`（**新增**，PyPI BSD-3）
- **跨服务 / 异步链路**：无（纯本地 CPU，无网络）

### 4.3 验证断言（改完逐条核）

- [ ] 新断言 `t_l2_minhash_detects_real_same_event` 绿（原 t001 案例 Jaccard ≥ 0.30）
- [ ] 新断言 `t_l2_minhash_drops_unrelated` 绿（不同事件 Jaccard < 0.30）
- [ ] 新断言 `t_l2_lsh_threshold_consistent` 绿（两模块常量同值）
- [ ] 新断言 `t_l2_lsh_build_handles_empty` 绿（R6 空台账不崩）
- [ ] 新断言 `t_l2_lsh_query_handles_empty_title` 绿（R6 空标题不崩）
- [ ] 新断言 `t_l2_lsh_excludes_self_norm` 绿（同主键不自比）
- [ ] **旧 27 条断言全绿**（`curate_selftest.py` 末行输出为准；不在文档里抄数）
- [ ] D2 铁律不回归（`t_l2_never_silently_drops`）
- [ ] D22 铁律持续（`t_new_candidates_get_unique_incrementing_ids`）

### 4.4 不可验证的盲点

- **< 50 条真实事件**：DESIGN-dedup.md §5 警告过阈值是定性估计，等台账 50+ 条时需重新校准 `LSH_THRESHOLD = REVIEW_LOW`
- **中文短标题（≤8 字）**：char trigram 仍稀疏，**设计 D2 已承认这是天花板**，本改动不缓解、但也不加剧
- **跨语言**：datasketch 未在中文短标题上做过大规模精度评估，实测数据需运行 §4.3 旧 + 新断言覆盖
- **`fingerprint()` 旧函数保留**：暂不删（一次性破坏面），等下个口径合并 ARCHITECTURE.md 时一并删

---

## 5. 实施计划

| 步 | 操作 | 闸 / 验证 |
|---|---|---|
| 1 | `pip install datasketch`（用户在本机 `.venv` 执行，本 Agent 不跑） | `pip show datasketch` 看得到 |
| 2 | 新建 `skills/news-curate/scripts/lsh_dedup.py` | §3.1 全量代码 |
| 3 | 改 `curate.py:128-138`（`similarity` body 替换） | §3.2.1 |
| 4 | 改 `curate.py:26-28 / 141-148`（常量改来源） | §3.2.2 |
| 5 | 改 `curate.py:387-392`（建索引一次）+ `curate.py:456-470`（LSH 预滤替换 O(N) 循环） | §3.2.3 |
| 6 | 加 6 条新断言到 `curate_selftest.py` | §3.3 |
| 7 | 跑 `python skills/news-curate/scripts/curate_selftest.py` | **末行打印 `全绿 33/N**`**（27 旧 + 6 新；实际数脚本不抄） |
| 8 | 烟雾测试：手工造 5 条真实/虚假同事件配对，看 needs_review 标记 | 内联叙述结果 |
| 9 | 写 `routes/news/evidence/2026-10-12-datasketch-lsh-integration-verification-lite.md` | 证据落盘 |

---

## 6. 完成判据 (Tier 1)

1. ✅ 本合并文档已写（`DESIGN-lsh.md` 落盘）
2. ✅ 用户确认「开始实现」（"开始实现吧"）
3. ✅ 主 Agent 改完 + 内联断言（§4.3 逐条核）—— 见 [evidence/2026-10-12-datasketch-lsh-integration-verification-lite.md](evidence/2026-10-12-datasketch-lsh-integration-verification-lite.md)
4. ✅ `curate_selftest.py` 末行输出 `全绿 39/39`
5. ✅ `evidence/2026-10-12-datasketch-lsh-integration-verification-lite.md` 落盘
6. ⏳ 可以 commit（push 由用户决定）

---

## 附录：校准记录（实施过程中定，文档一并落档）

> 实施 ≠ 文档想象。两处阈值与 DESIGN-lsh.md §3.2 / §3.3 原计划有出入, 实证后校准.

### A.1 阈值校准

| 项 | 文档初版 | 实施版 | 校准原因 |
|---|---|---|---|
| `REVIEW_LOW` | 0.30 | **0.20** | 真同事件配对 (t001) char trigram Jaccard 实算 = 0.25, MinHash 估计 ±0.06 抖动, 阈值 0.30 风险漏判 |
| `REVIEW_HIGH` | 0.60 | **0.45** | 同模板不同事件 Jaccard ≈ 0.5 (如 "暴雨已致3人死亡" vs "暴雨已致3人受伤"), 应标 high 让人眼区别 |
| `LSH_THRESHOLD` | 0.30 | **0.20** | 与 REVIEW_LOW 同步; LSH 预滤召回阈值与判定阈值统一, 减少两层阈值的组合失误 |

**root cause**: 中文短标题 char trigram 稀疏 —— 实体加权 0~N 范围下同事件 1.174, 但换 char trigram Jaccard 0~1 后, 实配仅 0.25 (long 20 字 / short 14 字 / 共 6 trigrams 重合 / 24 trigrams 并集 = 6/24). 设计 D2 已承认中文短标题稀疏是天花板, 本接入不缓解也不加剧, 只把不可比的 0~N 范围换成可线性预滤的 0~1 区间.

### A.2 ledger row 缺 `title` 字段时的 fallback

`curate_selftest.py` 里多条历史断言 (`t_l2_mid_*` / `t_l2_high_*` 等) 的 ledger row **只有 `norm_key`、没 `title`**。旧 `curate.py:460` 的 fingerprint 源是 `e.get("title") or ek`（`ek` = norm_key），新 `_minhash(e.get("title", ""))` 拿到空串 → MinHash 空 → 索引跳过 → 召回 0 → needs_review 不标.

**修法**：`lsh_dedup.build_index` 与 `find_l2_hits` 双重 fallback ——
```python
text = (e.get("title", "") or k) or ""  # 兼容纯 norm_key 行, 沿用 curate.py:460 的 e.get("title") or ek 约定
```

**单测覆盖**：`t_l2_lsh_build_handles_empty`（空台账不崩）+ 实测 `t_l2_mid_similarity_flags_review`（缺 title 行也能召回）.