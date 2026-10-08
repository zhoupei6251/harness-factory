# 设计：新闻去重台账 + 候选策展层

> 状态：草案，待拍板后进入实施计划
> 日期：2026-10-08
> 关联：`routes/news/ARCHITECTURE.md`（v2 单轨）、`skills/news-workflow/SKILL.md`（步骤 0）、`skills/news-collect/SKILL.md`

---

## 1. 问题陈述

用户诉求是「把最近火的吸引人的新闻，用模板生成好看的视频，发到抖音，并且**不能重复**」。

当前链路（`news-workflow` 步骤 0–5）六步齐全、AIGC 合规闭环完整，但**「不能重复」这一条在系统里不存在实现**：

| 环节 | 现状 | 证据 |
|---|---|---|
| 单次采集内去重 | 有，但只在内存里 | `collect.py:216 dedup(items)` — 按 `re.sub(r"[\W_]+","",title)` 比对，函数返回即出作用域 |
| 跨天/跨会话去重 | **无** | `.harness-news-runtime/hotboard/<date>.json` 是每日快照，SKILL.md §9 明写「不翻页、不做今天 vs 昨天的榜变化检测」|
| 已发布台账 | **无** | `routes/news/MEMORY.md` 的 `topics[]` 靠手写，目前仅 `t001` 一条 |

后果：明天重跑采集，同一事件会重新进入候选；agent 无历史感知，**会当作新选题重新提案**。去重不是"锦上添花"，它是这条产线可持续运行的前提条件。

## 2. 目标与非目标

### 目标

1. **G1 跨会话去重**：任一新闻事件在其进入台账后，不再被推荐为新选题
2. **G2 状态分级**：按台账状态决定"硬剔除 / 降权 / 不剔除"，而不是一刀切
3. **G3 事件级识别**：标题表述不同但指向同一事件时能被认出（「某地暴雨」vs「暴雨已致 3 人死亡」）
4. **G4 热度排序**：只用免费信号给出可解释的排序依据
5. **G5 零付费**：不引入任何 API key / 按次计费 / 云端模型调用
6. **G6 静默失败禁令**：任何剔除都必须带可读理由，不许悄悄丢

### 非目标

- 不做正文抓取、不做翻页、不做 web 爬虫
- 不做跨机器的分布式台账同步（单仓单机，`git` 即同步）
- **不改渲染链路**：`path_b_build.py` / 12 pack / AIGC 标识一律不碰
- 不引入 embedding 模型（违反 G5）
- 不替代 `fact-check` 硬门禁（本层只管"选不选"，不管"真不真"）

## 3. 方案总览

```
collect.py（不动）          .harness-news-runtime/hotboard/<date>.json
        │
        │  新增
        ▼
news-curate（新增 skill）    .harness-news-runtime/curated/<date>.json
        │
        │  读 + 更新
        ▼
routes/news/ledger.jsonl（新增，受版本管理）
```

三层职责切分：

| 层 | 职责 | 是否改动既有文件 |
|---|---|---|
| `collect.py` | 只管抓，一行不改 | 否 |
| `curate.py`（新） | 去重 / 打分 / 排序 / 输出候选 + 写台账 | 否（只读 hotboard，写 ledger） |
| `news-workflow/SKILL.md` | 步骤 0 从"采集"改为"策展"，插入新步骤 | 是（改一段） |

**`collect.py` 一行不改**是硬设计约束：它是已被实测验证过的采集层（真失败策略、真陈旧度统计），改它等于把一个能跑的东西变脆。新功能全部落在下游。

## 4. 数据设计

### 4.1 台账 `routes/news/ledger.jsonl`

每行一个 JSON 对象，**追加写入**，永不原地改写（除状态迁移写新行）。

```jsonl
{"id":"n0007","norm_key":"暴雨致3人死亡","fingerprint":["暴雨","3人","死亡"],"first_seen":"2026-10-08","last_seen":"2026-10-10","status":"published","rank_peak":4,"hits":3,"topic_id":"t002","video_id":"v009","output":".harness-news-runtime/videos/t002/final.mp4","published_at":"2026-10-10","aigc_ok":true}
```

| 字段 | 类型 | 语义 | 写者 |
|---|---|---|---|
| `id` | string | 稳定主键 `n%04d`，跨会话不变 | curate |
| `norm_key` | string | 标题归一化键（L1 去重用） | curate |
| `fingerprint` | string[] | 事件关键词集合（L2 去重用） | curate |
| `first_seen` / `last_seen` | date | 首次 / 最近一次在榜 | curate |
| `hits` | int | 累计上榜次数 | curate |
| `rank_peak` | int\|null | 历史最佳榜位（越小越热，null = 非百度榜） | curate |
| `status` | enum | `candidate` / `selected` / `drafted` / `rendered` / `published` / `rejected` | curate + workflow |
| `topic_id` / `video_id` | string\|null | 关联的 MEMORY 实体 | workflow |
| `output` | path\|null | 成片路径 | workflow |
| `published_at` | date\|null | 发布日期 | workflow |
| `aigc_ok` | bool\|null | AIGC 标识是否合规 | workflow |

**为什么 JSONL 而不是 SQLite/JSON**：
- 受版本管理 → `git diff` 能看出"发过什么、什么时候发的"，这是本项目的既定口径（见 ARCHITECTURE.md §6：契约证据不许依赖 gitignore）
- 追加语义天然匹配"事件只会越来越完整"这个事实
- 人可读、可手改、零依赖
- 单机单仓，不需要并发写

**为什么台账不写进 `MEMORY.md`**：MEMORY 是"当前在做什么"（工作态，频繁改）；台账是"做过什么"（历史，只增）。两者生命周期不同，混在一起会把 MEMORY 撑成流水账。

### 4.2 策展产物 `.harness-news-runtime/curated/<date>.json`

```json
{
  "curated_at": "2026-10-08T09:12:00+08:00",
  "cost": "zero",
  "input": {"path": "hotboard/2026-10-08.json", "count": 80},
  "ledger_entries": 7,
  "candidates": [
    {"rank": 1, "title": "…", "source": "baidu-realtime", "score": 8.2,
     "fingerprint": ["…"], "suggested_pack": "news-onsite",
     "ledger_id": "n0007", "ledger_status": "candidate",
     "why": "榜内 rank=1；连续在榜 3 天；同事件已在台账(candidate)→ 降权保留"},
    {"rank": 5, "title": "…", "score": 7.1, "ledger_status": null,
     "why": "榜内 rank=5；首次出现；台账无记录"}
  ],
  "excluded": [
    {"title": "…", "reason": "already_published", "matched_ledger_id": "n0003",
     "matched_norm_key": "拾荒老人每月3700元养老金"}
  ],
  "failures": []
}
```

**`excluded[]` 是这个设计的核心**：剔除不是静默的，每条都要写"为什么被剔"和"跟哪条台账撞了"。这是 R6「no silent failures」的直接落地，也是事后复盘"为什么今天没推这条"的唯一凭据。

## 5. 去重算法（两级）与它的能力边界

### L1 — 标题归一化精确匹配

沿用 `collect.py` 已有口径，保证同一套归一化语义：

```python
norm_key = re.sub(r"[\W_]+", "", title)          # 去标点空白
```

**注意**：Python `re` 的 `\W` 在 Unicode 模式下对中文是"非单词字符"，中文汉字**不会**被去掉。这一点必须写进自测（见 §8），否则会误以为"归一化把中文也清了"。

L1 命中 → 直接判为同一事件。**这一级是可靠的，覆盖"同一媒体隔天复读"这个最高频场景。**

### L2 — 事件指纹相似度：实测结论与能力边界

L2 要解决的是「同一事件、不同表述」。**这一级的实测结果不理想，必须先摊开说清楚，而不是靠调参假装解决。**

#### 三轮实测（`/tmp` 一次性脚本，可复跑）

| 方案 | 同一事件得分区间 | 不同事件得分区间 | 结论 |
|---|---|---|---|
| ① n-gram(2–4) Jaccard | 0.000 ~ 0.286 | 0.000 | **不可用**。原设计的 0.45 阈值会把同一事件 100% 漏判 |
| ② 覆盖度（交集/较短方） | 0.000 ~ 0.556 | 0.000 | 部分改善，但「发布新规」vs「新规施行」仅 0.083 |
| ③ bigram + 实体加权（实体权重 3） | 0.000 ~ 2.435 | 0.000 ~ **1.615** | 判别力最强，但**误杀严重** |

#### 根因

1. **中文短标题的 n-gram 极度稀疏**：「某地暴雨」4 字只能切出 2–3 个特征，「暴雨已致 3 人死亡」9 字切出十几个，**并集被稀释**。
2. **同一事件的中文表述往往用词完全不同**：「发布新规」vs「新规施行」共享的只有稀疏关键词，n-gram 交集近乎为零。这是中文的特性，不是实现问题。
3. **方案③ 的 1.615 分负例是致命伤**：「某地暴雨致 3 人死亡」vs「某地暴雨致 3 人失踪」——同一事件的不同进展，真会重发；「上海地铁 21 号线」vs「22 号线」被高权重实体词误判为同事件。**把权重调高会同时放大这两类错误。**

#### 定案：L2 降级为「提示层」，不参与自动剔除

这是本设计最重要的一次修正。**L2 不再作为自动剔除的依据，只作为排序降权 + 人工确认提示。**

| 层级 | 职责 | 可靠度 | 处置 |
|---|---|---|---|
| **L1 精确匹配** | 自动硬剔除 | 高 | 直接剔除，写 `excluded` |
| **L2 相似度** | **仅提示** | 中低 | 命中区间 `[0.30, 0.60)` → 标记 `needs_review` + 写明撞了哪条台账；**不进 `excluded`**；分数 ≥0.60 视为可能同事件高风险，人工看一眼再定 |

**为什么这样而不硬调阈值**：中文新闻的事件指纹问题需要语义理解才能根治，本地无模型方案做不到。继续调阈值只会在"漏判同事件"和"误杀不同事件"之间来回摆，且**每个阈值都要在真实台账上验证**——而台账现在还是空的（§4.1 只有 t001 一条）。**先建台账、攒够 50+ 条真实事件，再用真实数据校准阈值**，比现在拍一个数字写进代码靠谱得多。

**这意味着什么（必须对用户讲清）**：
> 系统能可靠挡住「同一个媒体重复推送同一标题」（L1）。
> 跨媒体同事件的「换句话说」挡不住，会以 `needs_review` 提示形式出现在候选清单里，由你一眼确认。
> **这是零 API 费约束下的诚实上限，不是 bug。** 想要真语义去重就得引入 embedding 模型 = 违反 G5。

**阈值不写进代码**：`L2_REVIEW_LOW = 0.30` / `L2_REVIEW_HIGH = 0.60` 作为具名常量放在配置段，等真实台账满 50 条后按 §11 D2 的复算流程校准。测试锁住的是**行为**（0.28 不提示、0.45 提示、0.65 高风险），不是这两个数字本身。

## 6. 状态机与分级策略（G2）

```
candidate ──选中──> selected ──出稿──> drafted ──渲染──> rendered ──发布──> published
     │                  │                  │                 │
     └──人工否决──────────┴──────────────────┴─────────────────┘
                        ↓
                    rejected
```

| 台账状态 | 再次出现时的处理 | 理由 |
|---|---|---|
| `published` | **硬剔除**（L1 命中即剔） | 已发过，重复就是自伤账号权重 |
| `rendered` | **硬剔除** | 已成片，重复劳动 |
| `drafted` / `selected` | **降权**（score × 0.3） | 在途不重复推进，但事件热度确实高时保留可见性 |
| `candidate` | **降权**（score × 0.6） | 上次进了候选没被选；可能是竞品关系，也可能上次判断有误，留观察 |
| `rejected` | **不降权** | 人工否决过，若热度显著上升（`rank_peak` 提升 ≥ 50%）允许重新出现，并在 `why` 注明"曾被否决，因热度回升重提" |

**L1 硬剔除对所有状态一致**：`published`/`rendered` 是"别再发了"，其余状态是"别再推荐同一个事件"——两种语义都用 L1 精确匹配实现，**不依赖 L2**。L2 只在 L1 未命中时提供 `needs_review` 提示。

**状态迁移由谁写**：
- `curate.py` 只写 `candidate`（它没有信息判断别的状态）
- `selected` 之后的迁移由 `news-workflow` 在步骤 0/2/4/5 结束时回写
- **回写必须显式**，不允许 curate 猜测

## 7. 热度打分（G4，只用免费信号）

百度热搜 `platform=wise` 响应里**没有** `hotScore` 字段（实测 80/80 条 `hot` 为空），所以**不能编造热度值**。可用信号只有三个：

| 信号 | 来源 | 权重 | 说明 |
|---|---|---|---|
| 榜内名次 `rank` | 百度榜 | 反向：`score_rank = (max_rank + 1 - rank) / max_rank`，乘 6.0 | 榜内相对位置，越靠前越热 |
| 连续在榜天数 | 追加 `hotboard/history.jsonl` | 每天 +1.2，上限 3.6 | 持续热度比瞬时爆点更值钱 |
| 跨源命中 | 多源出现同一归一化标题 | +1.5 每额外源，上限 3.0 | 多媒体同时报道 = 真热点 |

**总分上限 12.6**，`score = round(rank_score + days_score + cross_source_score, 2)`

**不使用的信号**（会在文档里写明为什么）：
- `hot` 字段：实测恒空
- 百度 `is_top`：实测恰好 1 条且 `rank` 为 null，是置顶不是第一名，混进排序会错位
- 任何 Beatra / 抖音站内榜：付费

**降权乘子**在加权后应用：`final_score = score * status_weight`

## 8. TDD 计划（先红后绿）

按 superpowers 强制 RED → GREEN。测试文件 `tests/test_news_curate.py`（新建，与现有 3 个测试并列）。

| # | 测试名 | 断言 |
|---|---|---|
| 1 | `t_norm_key_keeps_chinese_chars` | 归一化**不删汉字**（锁住 `re` 的 `\W` 语义，防"以为中文被清了"的误修） |
| 2 | `t_norm_key_strips_punctuation` | `「暴雨！致3人？」` → `暴雨致3人` |
| 3 | `t_fingerprint_extracts_entities` | 指纹含数字与实体词，不含停用词 |
| 4 | `t_l1_exact_match_excludes` | 同标题第二次出现 → `excluded` 含 `already_published`（**L1 硬剔除，不依赖 L2**） |
| 5 | `t_l2_marks_needs_review_not_excluded` | 「某地暴雨」vs「暴雨已致3人死亡」（实测 0.167，**低于提示区 0.30**）→ 仍进 `candidates`，**不进 excluded**。锁住"L2 永不自动剔除"这条铁律 |
| 6 | `t_l2_mid_similarity_flags_review` | 「拾荒老人每月3700元养老金」vs「71岁老人不知自己每月有3700元养老金」（实测 1.174）→ 标 `needs_review` + 写明撞了哪条台账，**且仍在 candidates 里** |
| 7 | `t_l2_high_similarity_flags_high_risk` | 同题两次（实测 2.435，≥ `L2_REVIEW_HIGH`）→ `needs_review: high` |
| 8 | `t_l2_never_silently_drops` | **L2 相似度无论多高都不产生 `excluded` 条目**（用极端相似输入验证，锁死 §5 的定案） |
| 9 | `t_rejected_allowed_when_rank_improves` | rejected + rank 改善 ≥50% → 重提 |
| 10 | `t_excluded_carries_reason` | **每条** excluded 都有 reason + matched_ledger_id（G6） |
| 11 | `t_ledger_append_never_rewrites_history` | 同 id 写两次 → 两行，历史不丢 |
| 12 | `t_score_uses_no_paid_signal` | 打分函数不读 `hot` 字段（塞一个假 hot 值进去，断言分数不变） |
| 13 | `t_score_null_rank_safe` | 置顶条目 `rank: null` 不炸、不参与排序 |
| 14 | `t_empty_candidates_writes_empty_list` | 台账把候选全排完 → 写空 candidates + 全部理由，**退出码 0**（不是 1） |
| 15 | `t_missing_ledger_treated_as_empty` | 台账文件不存在 → 当空台账，不崩 |
| 16 | `t_status_weight_table` | 五种状态的乘子按 §6 表 |

**先红的理由**：测试 5/6/7/8 在实现前必然失败——它们断言的是当前系统**完全不具备**的能力（尤其是测试 8，它锁的是"L2 永不自动剔除"这条**设计决策**，防止后来的 agent 为了"让去重更严"而偷偷加回自动剔除）。这正是 TDD 的意义：先证明问题真实存在，并��**把设计约束变成可执行断言**。

## 9. 实施步骤（拍板后执行）

| 步 | 动作 | 产出 | 验收 |
|---|---|---|---|
| 1 | 写 `tests/test_news_curate.py` 15 条断言 | 红灯（多数 FAIL） | 看到红 |
| 2 | 实现 `skills/news-curate/scripts/curate.py` | 纯函数 + CLI | 15 条全绿 |
| 3 | 建 `routes/news/ledger.jsonl` 种子 | 补录 t001 + 已发过的历史条目 | `git diff` 可读 |
| 4 | 跑真采集 + 真策展 | `curated/2026-10-08.json` | 80 条 → candidates 有值、excluded 带理由 |
| 5 | 改 `news-workflow/SKILL.md` 步骤 0 | 插入策展步骤 | 文档与实现一致 |
| 6 | 建 `skills/news-curate/SKILL.md` + `_meta.json` | 新技能 | `npm run index && npm run validate` 绿 |
| 7 | 更新 `ARCHITECTURE.md` / `MEMORY.md` | 架构变更入档 | 无陈旧描述残留 |

**不在本次范围**（避免 scope creep，另开）：20 个变体 `frame.md` 补全、`news-alert` 色板违规、`t_*` 三条 obsolete 断言重写、DailyHotApi 部署。

## 10. 风险与已知张力

| 风险 | 影响 | 对策 |
|---|---|---|
| L2 阈值 0.45 拍脑袋 | 误杀或漏网 | 阈值提为常量 + 测试 6 锁负例；上线后用真实台账校准一次并记在文档 |
| 台账与 `MEMORY.md` 双写 | 状态漂移 | 台账是历史、`MEMORY` 是工作态；**状态迁移只有 workflow 写台账一处**（§6） |
| 候选全被排空 | 策展产出空清单 | 退出码 0 + 空 candidates + 全部理由；不静默失败，也不谎报有货 |
| 百度榜改版 | `rank` 拿不到 | 与 `collect.py` 既有策略一致：解析成功但零条目即判源失败，记 `failures` |
| 指纹算法被后续 agent 误改 | 静默漂移 | 测试 3/5/6 锁行为，改算法必须先改测试（红） |

## 11. 决策记录

| # | 决策 | 取舍 |
|---|---|---|
| D1 | 台账落 `routes/news/ledger.jsonl`，受版本管理 | 换来可 `git diff`、换机器不丢；代价是仓库多一个文件需维护 |
| D2 | **L2 降级为提示层，不做自动剔除**；阈值 0.30/0.60 暂定，等真实台账满 50 条再校准 | 换来"绝不误杀/绝不静默丢"的诚实行为；代价是跨媒体同事件仍需你人工确认一次。**这条是三轮实测逼出来的**：n-gram Jaccard、覆盖度、实体加权三版全部无法同时做到"认得出同事件"和"分得开不同事件"（实测数据见 §5）。**不要再试第四种阈值然后硬调**——先攒真实台账再校准 |
| D3 | 状态分级而非一刀切硬剔除 | 换来"高热事件不因流程丢"；代价是策略表本身要维护（已上测试 16） |
| D4 | `collect.py` 一行不改，策展另起 | 保住已实测的采集层；代价是热板里有一条 CLI（可接受） |
| D5 | 台账不进 `MEMORY.md` | 两者生命周期不同；代价是多一处要回写的写入点（§6 已定单一写者） |
| D6 | 候选排空时退出码 0 而非 1 | 排空是合法业务结果（今天确实没新料），不是工具失败；错误才用非零码 |
| D7 | 测试 8 专门锁"L2 永不自动剔除" | 防止后来的 agent 为了"让去重更严"而偷偷加回自动剔除，绕过 D2 的实测结论 |

## 12. 实测脚本归档

三轮阈值实验的脚本落在 `/tmp`（不入库，因为它们是**一次性跑动产物**，不是契约证据——见 `ARCHITECTURE.md` §6 的留存口径）。**结论已写进 §5 与 D2**，脚本本身无需保留。

若要复现本文档的分数，在项目根跑：

```bash
python -c "
import re
STOP=set('的了是在和与及对为把被将从于也就都还又要能有这那我你他她它们个一二三四五六七八九十个只已并等将不年月日日在'.split())
def feats(t):
    t=re.sub(r'[\W_]+','',t); f=set()
    for i in range(len(t)-1): f.add(t[i:i+2])
    for n in (3,4,5):
        for i in range(len(t)-n+1):
            g=t[i:i+n]
            if g in STOP or any(c in STOP for c in g): continue
            f.add('E'+g)
    return f
def score(a,b):
    A,B=feats(a),feats(b); inter=A&B
    if not inter: return 0.0
    ent={x for x in inter if x.startswith('E')}
    return (3*len(ent)+len(inter-ent))/max(1,min(len(A),len(B)))
for pair in [('某地暴雨','暴雨已致3人死亡'),('拾荒老人每月3700元养老金','71岁老人不知自己每月有3700元养老金')]:
    print(round(score(*pair),3), pair)
"
```
