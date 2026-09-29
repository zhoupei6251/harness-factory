---
name: news-workflow
description: 新闻域总工作流入口（v2 单轨）：选题 → 模板决策 → 脚本 → 事实核查 → 成片 → 发布。所有 path = Path B（免费·零云费）。route=news 且任务跨多阶段时使用。
version: 2.0.0
when_to_use: route=news 且任务跨多个阶段（选题+脚本+成片+发布）时；单阶段任务直接用对应技能
status: active
tags:
- news
- workflow
domain: news
category: news.workflow
skills:
  - "hot-topic-content-maker"
  - "media-short-video-copy"
  - "viral-script-writer"
  - "fact-check"
  - "douyin-pro"
  - "douyin-upload"
---

# 新闻域总工作流（v2 单轨 · 零云费）

> 单条线，一气呵成：选题 → 模板决策 → 脚本 → 事实核查 → 成片 → 发布。
> 视频是唯一产物；Path A（付费）不在新闻域使用；12 个节目包（template）覆盖视觉形态。

状态记在 `routes/news/MEMORY.md`（topics / drafts / videos / in_progress 槽位），每完成一步回填状态。架构说明见 `routes/news/ARCHITECTURE.md`。

---

## 步骤 0：选题裁决（先做这个决定）

两个选题技能触发词重叠，按"出不出片"裁决：

| 场景 | 用哪个 |
|------|--------|
| 当天采集热点 + 1 条内容到脚本 + 待验证 | **hot-topic-content-maker** |
| 用户自己带来了热点/素材 | 跳过采集，直接进步骤 1 |

裁决后在 MEMORY `topics` 记录 `id + title + source`，**`status: researching`**。

---

## 步骤 1：模板决策（12 节目包）

**在写脚本之前先选模板**——脚本里的 `屏:` 行 / `quote` / `items` 都要对齐到模板的版式契约。

**决策树**（按新闻形态的特征词选；都不命中用 `news-coral`）：

| 形态 | 特征词 | pack 名 | 视觉气质 |
|------|--------|---------|----------|
| 单主角 + 反转 + 召唤 | 故事、人物、钩子、召唤 | `news-coral` | 暖火带 + 无衬线 |
| 调查 + 卧底 + 长文 | 调查、深度、揭露、追踪 | `news-ink` | 烫金报纸 + 全衬线 |
| 政策 + 法规 + 施行 | 新规、政策、办法、通知、施行 | `news-policy` | 公文蓝 + 烫金 |
| 数据 + 排行 + 数字 | 排行、TOP、数据、第一、同比 | `news-stat` | 米白纸 + 衬线巨号 |
| 突发 + 现场 + 时间码 | 突发、现场、直击、抢险、灾害 | `news-onsite` | 黑底 + PRESS 黄 |
| 多事件 + 速报 + 编号 | 今日要闻、整点、合辑、盘点 | `news-bulletin` | 编号条目 + 极简 |
| 科普 + 原理 + 图解 | 为什么、原理、科普、图解、解读 | `news-explainer` | 钢笔蓝 + 衬线 + SVG |
| 警示 + 应急 + 行动 | 紧急、务必、不要、立即、预警 | `news-alert` | 黑底 + 警示红 + 黄三角 |
| 节日 + 纪念 + 致敬 | 纪念、致敬、清明、国庆、周年 | `news-thread` | 国旗红 + 烫金 + 仪式 |
| 观点 + 评论 + 专栏 | 观点、评论、专栏、我观察 | `news-takes` | 单墨 + 浅米 + drop cap |
| 体育 + 比分 + 实时 | 比赛、比分、进球、加时、绝杀 | `news-blast` | 球场绿 + 比分红 |
| 国际 + 战况 + 地理 | 国际、战况、边境、外交、联合国 | `news-world` | 深海军蓝 + 经纬白 |

回填 MEMORY `videos[].template: <pack_name>`。

**当前进度**（12 pack = frame.md / host.html / compositions/*.html 三层齐全度）：
- `news-coral`: 完整（已有 7 个真 composition）
- 其余 11 个: frame.md + host.html + 1 个 placeholder composition（待补真 composition）
- 校验：`python skills/douyin-pro/scripts/path_b_selftest.py` 跑 `t_full_loadability_progress` 看 X/12

---

## 步骤 2：脚本生成

两个脚本生成器二选一（同一份稿件可以两版对比）：

| 用哪个 | 适用场景 |
|---|---|
| **media-short-video-copy** | skillset（6 个技能），含竞品文案提取 + 多平台脚本 + 爆款标题；适合系统化创作 |
| **viral-script-writer** | 单一脚本生成器，黄金 3 秒口播稿方法论；适合快速出稿 |

产物：`.harness-news-runtime/articles/<topic_id>-script.md`，回填 MEMORY `drafts[]`。

**模板契约提示**：脚本里加 `屏: <整句>` 单独行（即 markdown `onscreen:`）让 path_b_build 的 `check_onscreen` 闸门放行（不被配音念出来的那一句单独上屏）。每个 pack 的 frame.md 第 3 节有字阶约定，照着写。

---

## 步骤 3：事实核查（硬门禁）

**任何进入 Step 4 的脚本必须经过 `fact-check`**：

- 多源交叉（≥3 个独立来源）
- 时间/数字/地名/人物称谓必校验
- 不通过 = 标记 `flagged`，回 Step 2 改稿

回填 MEMORY `drafts[].fact_check: passed`。

---

## 步骤 4：成片渲染（Path B）

唯一渲染路径：

```bash
python skills/douyin-pro/scripts/path_b_build.py \
  --input .harness-news-runtime/articles/<topic_id>-script.md \
  --template <videos[].template> \
  --source <署名/频道> \
  --output .harness-news-runtime/videos/<topic_id>/final.mp4
```

**9 步硬链路**（Path B 内部）：
1. 解析输入（.md 或 .json 场景）
2. edge-tts 配音（每段 .mp3 + .vtt）
3. 发射合成 HTML（读 12 pack 之一 + 逐镜挂子合成）
4. layout_selfcheck（17 条结构不变量，渲前拦截）
5. hyperframes check --strict（引擎门禁）
6. HyperFrames 渲染 → silent.mp4
7. scdet 动量审计（每镜尾段必须仍在变化）
8. ffmpeg 合成（拼配音 + 烧 ASS 字幕）
9. 联络表 contact-sheet.jpg（人工验收比对）

回填 MEMORY `videos[].output` + `videos[].render_status: done`。

**注意**：`--template` 与 `--style` 同义（兼容旧用法）；`DEFAULT_TEMPLATE = news-coral`。

---

## 步骤 5：发布（douyin-upload）

主路径 `sau` CLI（本机可执行路径、cookie 目录见 `skills/douyin-upload/references/local-env.md`）。

**前置门禁**（任一不成立就不发）：
- `drafts[].fact_check == passed`
- `sau douyin check --account <name>` 返回 `valid`
- **未登录时不代替用户扫码**，把成品交用户手动发

```bash
# 视频轨（成片必须绝对路径）
sau douyin upload-video --account <name> --file <abs>/final.mp4 \
  --title "<稿内标题>" --desc "<正文+话题>" --tags tag1,tag2
```

发布后回填 `topics.published_at`、`in_progress` 清空。

---

## 硬性规则

1. **fact-check 不可跳过**：任何进入 Step 4 的脚本 `fact_check` 必须是 passed
2. **状态随做随记**：每步结束更新 MEMORY，跨会话不丢进度
3. **模板决策先于脚本**：不知道选哪个模板就不开始写脚本（避免返工）
4. **产物写 `.harness-news-runtime/`**：稿件/成片落 `articles/`、`videos/`，**不要**写 `.ai-runtime-artifacts/`（code 域）
5. **Path B only**：本工作流只使用 Path B（`--template` 即可）；不要尝试 Path A（付费路径，不在新闻域使用）
6. **12 pack 自检先行**：新加的 pack 必须先有 frame.md + host.html + composition 才提交；`path_b_selftest.py` 47 项必绿

---

## 与旧版（v1）的关键差别

| 维度 | v1 (双轨) | v2 (单轨) |
|---|---|---|
| 步骤数 | 7（含两轨切换）| 6 |
| 产物 | 文字 / 视频 | 仅视频 |
| 路径选择 | Path A / Path B | Path B only |
| 模板 | 单一 PPT 模板 | 12 pack 决策树 |
| 单独 polish 阶段 | news-polish + humanizer-zh | 不设阶段（脚本生成器自带）|

详细架构：`routes/news/ARCHITECTURE.md`。
