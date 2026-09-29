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
  - "news-collect"
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

**先采集，再裁决**。采集层是 `news-collect`（零成本：百度热搜 board API + feedx 中文媒体 RSS，
一条命令把线索写进 `.harness-news-runtime/hotboard/<date>.json`）；`hot-topic-content-maker` 只用来做选题裁决与脚本导向。

| 场景 | 用什么 |
|------|--------|
| 手上没素材，要看今天什么在热 | `python skills/news-collect/scripts/collect.py --limit 12 --print`（只要新料再加 `--max-age-days 3`）|
| 从线索里定 1 条并推到脚本 | **hot-topic-content-maker**（裁决/脚本导向；**不调它的热榜查询**，见下）|
| 用户自己带来了热点/素材 | 跳过采集，直接进步骤 1 |

⛔ **新闻域不使用 `hot-topic-content-maker` 的热榜查询**：那一步按次扣 Beatra 付费额度
（抖音热榜 6 credits，抖音/小红书按话题搜索各 60 credits）。本路线硬约束是零付费创作 —— 采集一律走 `news-collect`。

采集到的是**线索，不是事实**，三个实测的坑（细节见 `skills/news-collect/SKILL.md` §4/§5/§9）：
`hot` 字段恒为空（没有真热度值，只能看榜内 `rank`）；百度条目的 url 是搜索结果页不是原文；
feedx 三个源新鲜度从「当天」到「9 个月前」都有 → 按 `feed_stats` / `age_days` 先筛一遍。
裁决结果仍必须进步骤 3 的 fact-check 硬门禁，本层不豁免任何东西。

裁决后在 MEMORY `topics` 记录 `id + title + source`，**`status: researching`**；
`source` 写成可回溯形式，例如 `百度热搜榜 #3（news-collect 采集于 2026-09-29）`。

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
- `news-coral`: 完整（7 个真 composition）
- `news-policy`: 完整（5 个真 composition：hook / story / catalog / rail / closer）
- 上面两包即自检报告的 `可渲染 pack (有真版式): 2/12 —— news-coral, news-policy`
- 其余 10 个: frame.md + host.html + 只有 `placeholder.html`（占位壳，**不参与选择**）
- ⚠️ 决策树命中不可渲染的包时：政策/法规/通知类改落 `news-policy`，其余改落 `news-coral`，
  或按该包 frame.md 契约补真 composition。
  `load_style_pack` 会在**加载阶段**就停机并点名可渲染替代（不会等到渲染第 1 镜）
- 校验（三道闸，全绿才算过；脚本都在 `skills/douyin-pro/scripts/`，仓库根执行）：
  - `path_b_selftest.py` → 末行 `[selftest] 全绿 N/N`（**项数以脚本输出为准**，别在文档里抄数：
    61→63→66 这三级台阶全是加断言造成的手抄漂移），并报告 `可渲染 pack (有真版式): X/12`
  - `audit_pack_contrast.py` → `对比度审计通过：12 个 pack 的 frame.md 色板与文档一致`
  - `layout_selfcheck.py <版式目录…>` → `版式自检通过：N 个文件，0 条违规`。参数是**含
    `compositions/*.html` 的目录**（`skills/douyin-pro/templates/hyperframes_path_b/news-coral`），
    不是 pack 名：显式传入的目录里没有版式文件 = 用法错误，当场 exit 1 并点名该目录
    （旧版会打印「0 个文件，0 条违规」还 exit 0 —— 一次打错参数的绿闸门什么都没查，见 D13）
  - ⚠️ **前提**：`hyperframes` 要 Node ≥ 22；nvm 若指向 20.x，`npx -y hyperframes check` 只会产出
    空的 `check.json` + `requires Node.js >= 22`，那不是版式失败
- ⚠️ **补包前先重映射版式名**：自动选版只认 `path_b_build.AUTO_LAYOUT_STEMS`（hook / closer /
  story / stat / quote / catalog / rail），其余包 frame.md §7 里的 `compare` / `drilldown` /
  `score` / `map` 这类名字建出文件不会报错、但自动模式永远选不到（详见 ARCHITECTURE.md D9）

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
  --input .harness-news-runtime/articles/<topic_id>-scenes.json \
  --template <videos[].template> \
  --source <署名/频道> \
  --aigc-producer <你的频道/主体名> \
  --output .harness-news-runtime/videos/<topic_id>/final.mp4
```

**输入格式**：场景 JSON 数组最稳（每镜 `layout/kicker/title/body/onscreen`）。走 `.md` 脚本时
每镜必须自带 `屏:` 行，否则 `check_onscreen` 闸门拒收；JSON 里的 `onscreen` 要用 `｜` 标记语法
（`parse_input` 按该标记重写 `onscreen`/`onscreenAccent`，直传 accent 字段会被覆盖）。

**9 步硬链路**（Path B 内部）：
1. 解析输入（.md 或 .json 场景）
2. edge-tts 配音（每段 .mp3 + .vtt）
3. 发射合成 HTML（读 12 pack 之一 + 逐镜挂子合成；只有占位壳的包在此停机）
4. layout_selfcheck（17 条结构不变量，渲前拦截）
5. hyperframes check --strict（引擎门禁）
6. HyperFrames 渲染 → silent.mp4
7. scdet 动量审计（每镜尾段必须仍在变化）
8. ffmpeg 合成（拼配音 + 烧 ASS 字幕 + **交付轨才烧开场 4 秒左下角 AIGC 显式角标 + 写 mp4 元数据隐式标识并读回核验**；
   草稿轨两步都跳过 —— 走哪条轨见下面「哪条轨」一段，由旗标 > `routes/news/aigc-mode.json` > 代码默认裁决）
9. 联络表 contact-sheet.jpg（人工验收比对）+ `aigc.json` 标识侧车

回填 MEMORY `videos[].output` + `videos[].render_status: done`。

**哪条轨（2026-09-29 起仓库默认 = 草稿轨）**：`render` 现在在姿态文件里写着 `draft`，所以
**不加旗标渲出来的每一份都是草稿** —— 不烧 ① 角标、不写 ② 元数据，侧车只留 `draft` 一段（出处会写成
`draft(<姿态文件路径> render=draft)`）。这份产物在步骤 5 的闸门里**必然被拒**（读到 `draft` 即 EXIT=1），
所以它可以用来量像素、看留白、比版式，但不论如何发不出去。**要交付就显式加 `--deliver`**
（旗标压过姿态文件，侧车 `switch` 会记 `full(旗标 --deliver)`），长期恢复默认则把 `render` 改回 `full`。

**注意**：`--template` 与 `--style` 同义（兼容旧用法）；`DEFAULT_TEMPLATE = news-coral`。

---

## 步骤 5：发布（douyin-upload）

主路径 `sau` CLI（本机可执行路径、cookie 目录见 `skills/douyin-upload/references/local-env.md`）。

**前置门禁**（任一不成立就不发）：
- `drafts[].fact_check == passed`
- **闸门先过**：`python skills/douyin-pro/scripts/check_publishable.py <abs>/final.mp4` 退出码必须是 0。
  它照 `aigc.json` 核 ①`explicit.burned_in` 与 ②`metadata_key`/`implicit`，草稿与无侧车的老成片都在这里被拒
  （EXIT=1 → 重渲）；③ 那行 `--declaration 内容由AI生成` **给不给由姿态文件的 `declaration` 决定** ——
  现在仓库写着 `undeclared`，闸门只打警告并要求在 `videos[].declaration` 记 `undeclared`。
  要按老规矩带声明：闸门加 `--require-declaration`（本次）或把姿态改回 `required`（长期）
- `sau douyin check --account <name>` 返回 `valid`
- **未登录时不代替用户扫码**，把成品交用户手动发

```bash
# 视频轨（成片必须绝对路径；AI 生成内容必须带自主声明）
# 姿态 declaration=undeclared 期间闸门不给最后一行 —— 那是当前默认；
# 要带声明就照下面写（或先给闸门加 --require-declaration 让它把命令打全）
sau douyin upload-video --account <name> --file <abs>/final.mp4 \
  --title "<稿内标题>" --desc "<正文+话题>" --tags tag1,tag2 \
  --declaration 内容由AI生成
```

`--declaration` 的取值是抖音发布页弹窗的**选项原文**（上游源码实测：`内容由AI生成` /
`内容为转载信息` / `内容为个人观点或见解`）。**上游选不上只 warning、不阻断发布**，
所以成功凭据是日志出现 `自主声明已选择「内容由AI生成」`；没有这行 = 未声明（见
`skills/douyin-upload/references/cli-contract.md` § 自主声明）。

发布后回填 `topics.published_at`、`in_progress` 清空。

---

## 硬性规则

1. **fact-check 不可跳过**：任何进入 Step 4 的脚本 `fact_check` 必须是 passed
2. **状态随做随记**：每步结束更新 MEMORY，跨会话不丢进度
3. **模板决策先于脚本**：不知道选哪个模板就不开始写脚本（避免返工）
4. **产物写 `.harness-news-runtime/`**：稿件/成片落 `articles/`、`videos/`，**不要**写 `.ai-runtime-artifacts/`（code 域）
5. **Path B only**：本工作流只使用 Path B（`--template` 即可）；不要尝试 Path A（付费路径，不在新闻域使用）
6. **12 pack 自检先行**：新加的 pack 必须先有 frame.md + host.html + 真 composition 才提交；三道闸必绿
   （`path_b_selftest.py` 全量断言 + `audit_pack_contrast.py` 色板复算 + `layout_selfcheck.py` 结构不变量；
   项数以脚本输出为准，见步骤 1），
   且版式文件名只许落 `AUTO_LAYOUT_STEMS`（见步骤 1 的重映射提示）
7. **AIGC 标识对交付件不可关**：交付件必须同时有画面内角标（①）+ mp4 元数据 `AIGC` 键（②）+ 平台自主声明（③）。
   ①② 由 `path_b_build.py` 在**交付轨**上无条件产出并自检（读不回元数据即拒绝交付），③ 由发布命令 `--declaration` 提供，
   发之前由 `check_publishable.py` 逐件核。没有 `aigc.json` 侧车的老成片一律视为不合规，**重渲**而不是直发。
   "不要标识"的唯一合法轨道是**草稿轨**（旗标 `--draft` 或姿态文件 `render=draft`，步骤 4），它的产物被闸门判为不可发布 ——
   **开关买到的是调试自由，不是免标识的成品**；③ 可以显式关掉（`--allow-undeclared` 或姿态
   `declaration=undeclared`，2026-09-29 起仓库默认就是关的），关掉必须在 `videos[].declaration` 记 `undeclared`
   留痕 —— ② 过抖音转码即失，③ 是唯一活到平台侧的那一件，代价由发布的人承担，不由脚本承担
8. **采集只走 `news-collect`**：热点线索来自本地可复跑的免费采集器，**不**调用任何按次扣费的榜单/搜索接口
   （Beatra 热榜 6 / 话题搜索 60 credits）。付费不是本路线的可选项，缺源就补免费源而不是花钱

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
