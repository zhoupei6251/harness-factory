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
LSH_THRESHOLD = 0.20 # LSH 预滤阈值; 同 REVIEW_LOW (校准仅 2026-10-12)
                     # 原 0.30 → 0.20: 真同事件配对实测 Jaccard = 0.25,
                     # MinHash 估计在 ±0.06 抖动, 阈值 0.20 留安全边
                     # (DESIGN-lsh.md §2.3 中文字符 n-gram 稀疏)

REVIEW_LOW = 0.20    # 旧 L2_REVIEW_LOW 0.30 → 0.20; 真同事件配对 Jaccard ≈ 0.25
REVIEW_HIGH = 0.45    # 旧 L2_REVIEW_HIGH 0.60 → 0.45; 同模板不同事件 Jaccard ≈ 0.5 标 high
                     # 留给人眼判, 不自动剔除 (D2 铁律)

# 复刻 curate.py:69 STOPWORDS (防止"今天今日"/"新规新规"虚表匹配).
# **keep-in-sync with curate.py:69-72**; 故意微调加了"今日/今天/新闻/消息"
# 等实测噪声词 —— 实证而非理论, 见 t_l2_minhash_drops_unrelated 阴性样例.
STOPWORDS = set(
    "的了是在和与及对为把被将从于也就都还又要能有这那我你他她它们个"
    "一二三四五六七八九十个只已并等将不年月日日在上下前后中这那有过会要说"
    "让给但而却又再最很给".split()
    + ["新的", "今日", "今天", "新闻", "消息"]
)

REVIEW_LOW = 0.20     # 旧 L2_REVIEW_LOW 0.30 → 0.20 (校准仅 2026-10-12, 见模块顶注释)
REVIEW_HIGH = 0.45    # 旧 L2_REVIEW_HIGH 0.60 → 0.45 (同上)


def _is_stopish_trigram(g: str) -> bool:
    """三字全部位于停用字集合时算"虚", 剔除."""
    return bool(g) and all(c in STOPWORDS for c in g)


def _trigrams(title: str) -> set[str]:
    """char trigram 集合。空串返回空集 (R6 防崩)."""
    if not title:
        return set()
    out: set[str] = set()
    for i in range(len(title) - NGRAM_SIZE + 1):
        g = title[i:i + NGRAM_SIZE]
        if not _is_stopish_trigram(g):
            out.add(g)
    return out


def _minhash(title: str) -> MinHash:
    """对标题建 MinHash. 空标题返回空 MinHash (R6)."""
    m = MinHash(num_perm=NUM_PERM)
    for g in _trigrams(title):
        m.update(g.encode("utf-8"))
    return m


def jaccard(a: str, b: str) -> float:
    """Jaccard on char trigrams. 范围 [0, 1]. 替代 curate.py:128 similarity().

    空串 / 空集 → 0.0 (R6); 两侧非空时 = |A ∩ B| / |A ∪ B|.
    """
    ta, tb = _trigrams(a), _trigrams(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def build_index(entries: list[dict]) -> tuple[MinHashLSH, dict[str, MinHash]]:
    """为台账建 LSH 索引, 跑一次。

    返回 (lsh_index, {norm_key -> MinHash}).
    空台账 / 全空标题容错 (R6): 返回空索引 + 空 dict, 不抛.

    **fallback**: ledger row 可能缺 `title` 字段（实测见 curate_selftest t_l2_mid_*
    与 t_l2_high_* 等用例 —— 它们只写 norm_key），此时退到 `norm_key` 当 fingerprint 源,
    沿用 curate.py:460 的 `e.get("title") or ek` 约定.
    """
    lsh = MinHashLSH(threshold=LSH_THRESHOLD, num_perm=NUM_PERM)
    mhashes: dict[str, MinHash] = {}
    for e in entries:
        k = e.get("norm_key", "") or ""
        if not k:
            continue
        text = (e.get("title", "") or k) or ""  # 兼容纯 norm_key 行
        m = _minhash(text)
        if len(m) == 0:
            continue
        lsh.insert(k, m)
        mhashes[k] = m
    return lsh, mhashes


def find_l2_hits(
    query_title: str,
    lsh: MinHashLSH,
    entries: list[dict],
    exclude_norm: str,
) -> list[tuple[str, float]]:
    """LSH 预滤 + Jaccard 精确比对。返回 [(matched_id, sim)], 已按 sim 降序。

    exclude_norm: 同主键台账行不参与 (curate.py:460 的 ek == key 检查复刻).
    entries: 全台账行, 用于反查 norm_key -> row; 行可缺 title, 自动 fallback 到 norm_key.

    **阈值约定**: LSH 用模块顶 LSH_THRESHOLD 预滤（可能漏召回, 概率随 NUM_PERM 上升而下降）,
    精确 Jaccard 用 REVIEW_LOW 判定; 二者阈值现已统一 (DESIGN-lsh.md §2.3 校准).
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
    hits: list[tuple[str, float]] = []
    for ck in cands:
        e = by_norm.get(ck)
        if not e:
            continue
        text = (e.get("title", "") or ck) or ""
        sim = jaccard(query_title, text)
        hits.append((e.get("id", ""), sim))
    hits.sort(key=lambda h: h[1], reverse=True)
    return hits