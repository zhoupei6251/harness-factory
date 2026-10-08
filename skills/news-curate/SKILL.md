---
name: news-curate
description: 选题策展层：按台账去重已发/在途事件（零成本，不重复生成），只用免费信号给线索排序，产出带理由的今日候选清单。route=news 且采集跑完、选稿之前使用。产出是候选，不是已核实事实。
version: 1.0.0
when_to_use: route=news 需要"今天从线索里选哪条"时；尤其在已发过一批、怕重复的时候
status: active
tags:
- news
- dedup
- curate
- ledger
- zero-cost
domain: news
category: news.research
---

# 选题策展层（news-curate）

`news-collect` 负责抓线索，**本技能负责"选哪条"**。核心是两件事：

1. **去重** —— 台账里已有的事件不再作为新选题推荐（这是「不能重复生成」的落地点）
2. **排序** —— 用三个免费信号给线索打分，输出带理由的候选清单

**不花钱**：不调任何按次计费接口（Beatra 热榜 6 / 话题搜索 60 credits），不用 embedding 模型。

## 1. 快速开始

```bash
# 采集（先跑，见 news-collect）→ 策展 → 看候选
python skills/news-collect/scripts/collect.py --limit 12
python skills/news-curate/scripts/curate.py --record-history --top 10 --print
```

**状态回写用 `ledger.py`，别手敲 `python -c`**（`python -c` 抄字段一多就漏，`norm_key`
一手抖 L1 去重就静默失效）。三种回写时机见 `news-workflow` 硬性规则 9：

```bash
# 发布后：把事件标成已发布 → 明天不再推荐它（这是「不重复生成」真正落地的那一行）
python skills/news-curate/scripts/ledger.py mark --status published \
  --norm-key "$(python -c "import sys;sys.path.insert(0,'skills/news-curate/scripts');import curate;print(curate.norm_key('完整标题'))")" \
  --video-id v009 --published-at 2026-10-10

# 台账主键体检（不同事件共用同一 id = 撞车；同事件多行同 id = 合法）
python skills/news-curate/scripts/ledger.py check
```

> `mark` 只支持两种定位：`--norm-key`（**完整标题**算出的归一化键）或 `--id`。
> 状态值拼错、找不到目标事件一律**非零退出**，不静默追加孤儿行（R6）。
> 迁移后**沿用同一事件的主键**（设计 §6：同事件同 id 多行），不会另起一个新 id。

首次使用先补录历史已发事件（**没有这一步，台账是空的，等于没去重**）：

```bash
python -c "
import sys; sys.path.insert(0,'skills/news-curate/scripts')
import curate as cu
cu.append_ledger(cu.DEFAULT_LEDGER, {
  'id':'n0001','norm_key':cu.norm_key('<完整标题，不要截断>'),
  'title':'<完整标题>','fingerprint':cu.fingerprint('<完整标题>'),
  'first_seen':'YYYY-MM-DD','last_seen':'YYYY-MM-DD',
  'status':'rendered','rank_peak':5,'hits':1,
})"
```

⚠️ `norm_key` **必须由完整标题算出来**（`cu.norm_key(title)`），手敲一个前缀会导致 L1 匹配不上、去重静默失效。

## 2. 输出长什么样

```
[curate] 输入 43 条 · 台账 44 条 · 候选 43（新鲜 21） · 剔除 0

  #1 [  7.2] 尊界刹车踏板支架断裂 江淮汽车跌停
       百度榜 rank=1；连续在榜 1 天
  #2 [  4.2] 美国加州一对夫妇被控虐待至少14名代孕子女
       bbc-zh feed 条目（无热度名次）；发布距今 0.0 天
  #3 [  4.32] 航天人紧急营救北斗卫星
       百度榜 rank=2；连续在榜 1 天；台账已有记录(candidate)→ 降权 ×0.6
```

每条候选都带 `why` 字段说明依据。**`why` 是这个技能的核心产出，不是装饰** —— 排序被质疑时它就是答案。

标记含义：

| 标记 | 含义 | 怎么办 |
|---|---|---|
| ⚠STALE | 陈旧（>7 天），多半是采集源滞后 | 别当今日新闻，换源或看百度榜 |
| ⚠REVIEW | L2 相似度高，疑似台账里已有同一事件 | **你确认一下**，别直接发 |
| ✨REVIVED | 曾被你否决，但热度显著回升 | 值得重新考虑 |

## 3. 三个免费信号（打分口径）

| 信号 | 范围 | 说明 |
|---|---|---|
| 榜内名次 | 0 ~ 6.0 | **只有百度实时榜**算热度 |
| 新鲜度 | 0 ~ 3.0 | 按 `age_days` 半衰期衰减（半衰期 3 天） |
| 跨源命中 | 0 ~ 3.0 | 同一标题在几个源出现过 |

**RSS 源的 `rank` 不是热度**，只是 feed 内条目序号 —— 实测 4 个源各有 1 条 rank=1，
它们是 4 条完全不同的新闻，按热度加权会并列成一片。所以 RSS 侧只给新鲜度分。

**不用 `hot` 字段**：百度 `platform=wise` 响应里实测 80/80 条为空，别在它上面编逻辑。

## 4. 去重：两级，且只有一级能自动剔除

| 层级 | 做法 | 可靠度 | 处置 |
|---|---|---|---|
| **L1** | 归一化后精确匹配（去标点空白，保留汉字） | 高 | **硬剔除**，写进 `excluded[]` |
| **L2** | 字符 bigram + 实体词加权相似度 | 中低 | **只标 needs_review，永不自动剔除** |

### 为什么 L2 不自动剔除

实测三轮（数据见 `routes/news/DESIGN-dedup.md` §5）：

| 方案 | 同一事件 | 不同事件 | 结论 |
|---|---|---|---|
| n-gram Jaccard | 0.000~0.286 | 0.000 | 阈值 0.45 会 100% 漏判 |
| 覆盖度 | 0.000~0.556 | 0.000 | 「发布新规」vs「新规施行」仅 0.083 |
| 实体加权 | 0.000~2.435 | 0.000~**1.615** | 判别力强但误杀致命 |

根因：中文短标题的 n-gram 极度稀疏，且**同一事件的中文表述用词往往完全不同**。
这是纯本地无模型方案的天花板，不是实现问题。

**诚实的能力边界**：
- ✅ 挡得住「同一个媒体重复推同一标题」（L1）
- ⚠️ 跨媒体同事件的「换句话说」挡不住，会以 `⚠REVIEW` 提示，**由你一眼确认**
- 想真语义去重就得引入 embedding 模型 = 违反零付费约束

阈值 `L2_REVIEW_LOW=0.30` / `L2_REVIEW_HIGH=0.60` 是**暂定值**，等台账攒够 50 条真实事件后校准。

## 5. 台账 `routes/news/ledger.jsonl`

**追加**语义，永不原地改写。**当前状态 = 最后一行**（不是首行）。

| 状态 | 再次出现时 |
|---|---|
| `published` | **硬剔除**（`already_published`） |
| `rendered` | **硬剔除**（`already_rendered`） |
| `drafted` / `selected` | 降权 ×0.3 |
| `candidate` | 降权 ×0.6 |
| `rejected` | ×1.0 不降权，且名次比 `rank_peak` 改善 ≥50% 时标 `revived` |

状态迁移**只有 `news-workflow` 写**（curate 只写 `candidate`）——单一写者，避免双写漂移。
回写走 `ledger.py mark`（见 §1），它保证**同一事件沿用同一主键**、值拼错即停机。

**主键唯一性**：`id` 是事件的稳定主键，两条铁律 ——
① **不同事件不许共用同一个 id**（撞车会让 `matched_ledger_id` 与状态回写指向错误事件）；
② **同一事件的多行必须共用同一个 id**（candidate → published 的状态迁移）。
`ledger.py check` 就是照这两条体检的。
> 2026-10-08 修过一次真 bug：`curate.py` 在批量追加时反复用同一份 `entries` 快照算
> `next_ledger_id()`，导致同批 43 个不同事件全写成 `n0002`（见 `ARCHITECTURE.md` D22）。
> 断言 `t_new_candidates_get_unique_incrementing_ids` 已把它锁死。

## 6. 退出码

| 情形 | 退出码 |
|---|---|
| 正常完成（含**候选全被排空**） | 0 |
| hotboard 不可读 / JSON 坏 | 1（且不覆盖上一次策展结果） |

候选排空是合法业务结果（今天确实没新料），不是工具失败。

**G6 禁静默失败**：每条被剔除的都必须在 `excluded[]` 里带 `reason` + `matched_ledger_id` + `matched_norm_key`。

## 7. 断言集

```bash
python skills/news-curate/scripts/curate_selftest.py     # 纯离线，项数以末行输出为准
```

**项数以脚本末行输出为准**，别在别处抄数。几条值得记的：

- `t_l2_never_silently_drops` —— 锁死「L2 永不自动剔除」，防止后人为"让去重更严"偷偷加回
- `t_latest_row_wins_for_status` —— 锁死「追加台账取最后一行」，这条曾是一个会**静默重发已发布视频**的真 bug
- `t_rss_rank_is_not_hotness` / `t_stale_sources_are_flagged` —— 锁死 RSS 名次与陈旧源语义
- `t_new_candidates_get_unique_incrementing_ids` —— 锁死「同批新增主键唯一且递增」+「同一事件多源命中只写一行」（D22）
- `t_ledger_mark_*` / `t_ledger_check_detects_id_collision` —— 锁死状态回写 CLI 的追加语义、主键沿用、错误即停机

## 8. 已知限制

- **只管选不选，不管真不真** —— 每条候选进渲染前仍必须过 `fact-check` 硬门禁，本层不豁免任何东西
- `norm_key` 手敲前缀会让 L1 静默失效（§1 已警告）
- 连续在榜天数依赖 `history.jsonl`，首次运行没有历史 → 全部按 1 天算
- 不做榜变化 diff、不翻页、不抓正文 —— 那些是 `news-collect` 的边界，本层不越界
