# News domain · 整合架构（v2 单轨 · 零云费）

> 单条线, 一条到底: 选题 → 模板 → 脚本 → 核查 → 渲染 → 发布。
> 视频是唯一产物; Path A 已不在新闻域使用; 12 pack 是视觉正交轴。

---

## 1. 设计目标

| 维度 | 旧 (v1 双轨) | 新 (v2 单轨) |
|---|---|---|
| 产物 | 文字 / 视频 二选一 | 只视频 |
| 路径 | Path A / Path B 二选一 | 只 Path B（免费·零云费）|
| 脚本润色 | 单独 news-polish + humanizer-zh 阶段 | 并入脚本生成器（不另设阶段）|
| 模板选择 | 没有（所有视频共用一个 PPT 模板）| 12 pack 决策树（按新闻形态）|
| 入口步骤数 | 7（含两轨切换 + Path 选择）| 3（含模板决策）|
| 文档位置 | 跨多个文件且互相引用 | 6 步全部在 news-workflow/SKILL.md |

### 为什么整合

- 用户最终产物 = 视频 → text track 是 dead-end 投入
- news-polish + humanizer-zh 是文字稿后处理；视频脚本由脚本生成器自带润色
- Path A（付费）= 你只做免费，从未用过

---

## 2. 数据流（6 步一气呵成）

```
news-collect (Step 0 · 零成本采集，无 key 无付费)
   ↓ 产出: .harness-news-runtime/hotboard/<date>.json（选题线索清单）
hot-topic-content-maker (Step 1 · 只做裁决/脚本导向，不调它的付费热榜)
   ↓ 产出: 选题 + 简报
media-short-video-copy / viral-script-writer (Step 2)
   ↓ 产出: 口播稿 (.harness-news-runtime/articles/<id>-script.md)
12 pack 决策树 (Step 2.5)
   ↓ 产出: videos[].template (news-coral | news-ink | ...)
fact-check (Step 3, 硬门禁)
   ↓ 产出: drafts[].fact_check = passed
douyin-pro Path B (Step 4)
   ↓ 产出: .harness-news-runtime/videos/<id>/final.mp4 + aigc.json (标识侧车)
   ↓ 姿态: 交付轨 or 草稿轨由 aigc_mode.py 裁决 —— 旗标 > routes/news/aigc-mode.json > 代码默认(全开)
check_publishable.py (Step 4.5 · 发布闸门)
   ↓ 判据: 照 aigc.json 核 ①②, 打出 ③ 必带的 --declaration 参数(姿态关了则改为警告+留痕); 退出码 1 = 不许发
douyin-upload upload-video (Step 5)
   ↓ 产出: MEMORY.published_at 回填
```

每一步产出都写回 MEMORY.md；流程是 6 步（步骤 0–5，采集层是步骤 0 的输入，不另算一步）, 但实际写状态只要 4 个字段：
- `topics[].status` (researching → drafting → fact_check → rendering → published)
- `drafts[].fact_check` (pending → passed / flagged)
- `videos[].template` (12 选 1)
- `videos[].output` (.mp4 路径)

---

## 3. 文件分层

```
routes/news/                         ← 新闻域状态层
├── ARCHITECTURE.md                  ← 本文件 (单轨设计)
├── MEMORY.md                        ← 选题 / 草稿 / 成片 / 进度 状态
├── aigc-mode.json                   ← 标识两开关的**当前姿态**(受版本管理; 没有这文件=全开, 见 D12)
└── (无产物目录, 运行时落 .harness-news-runtime/)

skills/news-workflow/SKILL.md        ← 入口: 6 步工作流
skills/douyin-pro/                   ← 渲染器 (Path B)
├── SKILL.md                         ← 通用 Skill (Path A 仍标注为"非新闻可用")
├── scripts/
│   ├── path_b_build.py             ← 9 步发射器 (解析→配音→发射→自检→门禁→渲染→动量→烧字幕+AIGC→联络表)
│   ├── layout_selfcheck.py          ← 17 条结构不变量 (渲前拦截)
│   ├── audit_pack_contrast.py       ← frame.md 色板与对比度表复算 (文档里的"实测值"不许手抄)
│   ├── verify_aigc_badge.py         ← AIGC 角标真像素复测 (字芯/墨迹/时长三项; 时序基准 = silent 同刻重烧无角标 ASS; 文档数字只认它)
│   ├── check_publishable.py         ← 发布闸门 (照 aigc.json 核 ①② + 打出 ③ 必带参数; 草稿在这里被拒)
│   ├── aigc_mode.py                 ← 两开关的**默认姿态**裁决 (旗标 > routes/news/aigc-mode.json > 代码默认; 值不合法即 ModeError)
│   ├── fixtures/badge_probe_shots.json ← 探针**输入** (5 镜 news-policy): 发射器渲它、复测器量它
│   ├── path_b_selftest.py           ← 71 项纯函数断言 (12 pack 加载 + AIGC 合规 + 草稿轨/发布闸门/姿态文件 + 词表 + 上面两闸门的负例)
│   ├── commons_media.py             ← 图片层 (path B 当前未启用, 留作图片型模板扩展)
│   └── install_path_b_deps.py       ← 依赖一键装
├── templates/hyperframes_path_b/   ← 12 个节目包
│   ├── news-coral/                  ← 完整 (frame + host + 7 compositions)
│   ├── news-policy/                 ← 完整 (frame + host + 5 compositions)
│   ├── news-ink/                    ← frame + host + placeholder (待补 composition)
│   ├── ... (9 more)
│   └── <12 包>/frame.md             ← token 与版面法则 (唯一事实源)
└── skills/video-render-engine/        ← 配音×渲染 详解（douyin-pro **内部**子模块，
                                         全路径 skills/douyin-pro/skills/video-render-engine/，
                                         不在仓库 skills/ 顶层）
skills/douyin-upload/                 ← 发布 (`sau` CLI 包装)
skills/fact-check/                    ← 事实核查 (硬门禁)
skills/media-short-video-copy/        ← 视频脚本生成器 (主)
skills/viral-script-writer/           ← 视频脚本生成器 (备)
skills/news-collect/                  ← 步骤 0 采集层（stdlib-only：百度热搜 board + feedx RSS；无 key 无付费）
skills/hot-topic-content-maker/       ← 选题裁决（**其付费热榜查询在本域禁用**）
```

**核心发射器 `path_b_build.py`**——支持 12 pack + `--template`，交付轨无条件产出 AIGC 标识（画面角标 + mp4 元数据 + `aigc.json` 侧车）；草稿轨（旗标 `--draft` 或姿态文件 `render=draft`）不烧不写，代价由 `check_publishable.py` 结算：草稿发不出去。走哪条轨由 `aigc_mode.py` 一处裁决（旗标 > `routes/news/aigc-mode.json` > 代码默认全开），见 D11/D12。

---

## 4. 12 pack 模板（视觉正交轴）

| # | pack | 视觉气质 | 适用稿件特征词 |
|---|---|---|---|
| 1 | `news-coral` | 暖火带 + 无衬线 | 单主角 / 反转 / 故事 / 钩子 |
| 2 | `news-ink` | 烫金报纸 + 全衬线 | 调查 / 深度 / 卧底 / 揭露 |
| 3 | `news-policy` | 公文蓝 + 烫金 + 衬线 | 新规 / 政策 / 法规 / 通知 |
| 4 | `news-stat` | 米白纸 + 衬线巨号 | 排行 / 数据 / 第一 / 同比 |
| 5 | `news-onsite` | 黑底 + PRESS 黄 + 时间码 | 突发 / 现场 / 直击 / 抢险 |
| 6 | `news-bulletin` | 编号条目 + 极简直条 | 今日要闻 / 整点 / 合辑 |
| 7 | `news-explainer` | 钢笔蓝 + 衬线 + SVG | 为什么 / 原理 / 科普 / 图解 |
| 8 | `news-alert` | 黑底 + 警示红 + 黄三角 | 紧急 / 务必 / 不要 / 预警 |
| 9 | `news-thread` | 国旗红 + 烫金 + 仪式 | 纪念 / 节日 / 致敬 / 周年 |
| 10 | `news-takes` | 单墨 + 浅米 + drop cap | 观点 / 评论 / 专栏 |
| 11 | `news-blast` | 球场绿 + 比分红 | 比赛 / 比分 / 进球 / 实时 |
| 12 | `news-world` | 深海军蓝 + 经纬白 | 国际 / 战况 / 边境 / 地理 |

每个 pack 都是自含的设计系统（**frame.md 单一事实源** + host.html + 多个 composition）：
- `frame.md`: 色板 + 字阶 + 版面法则 + 动量预算 + 地面清单
- `host.html`: 画布骨架 + 5 个占位符 (COMPOSITION_ID / W / H / TOTAL / SCENES / AUDIOS)
- `compositions/*.html`: 实际版式（hook / closer / 内容卡 …）

**当前状态**（自检 `t_full_loadability_progress` 实时报告——名字沿用，口径已改成"有真版式"而不是"能加载不抛"，后者在 12/12 放好占位壳后就是饱和指标）：
- `news-coral`: 完整（7 个真 composition）
- `news-policy`: 完整（5 个真 composition：hook / story / catalog / rail / closer；`quote` 被该包法则 4 排除、`stat` 归 `news-stat`，刻意不 author）
- 上面两包即 `可渲染 pack (有真版式): 2/12 —— news-coral, news-policy`
- 其余 10 个: frame.md + host.html + 只有 `placeholder.html`（占位壳，**不参与版式选择**）
- 只有占位壳的包在 `load_style_pack` **加载阶段**停机并点名可渲染替代，不会拖到渲染第 1 镜
- 后续 composition 一个个补；补完一个（并删除 placeholder.html），可渲染计数递增

---

## 5. 关键决策记录

| # | 决策 | 取舍 |
|---|---|---|
| D1 | 单条线 (视频 only) | 用户最终产物是视频；text track 是 dead-end 投入 |
| D2 | Path B only | 用户只做免费；Path A 留在 `douyin-pro/SKILL.md` 标注为"非新闻领域可启用"，不在新闻工作流中 |
| D3 | 12 pack 决策树 | 一份脚本可对应 12 种视觉气质；决策由稿件特征词驱动，不靠人挑 |
| D5 | fact-check 硬门禁 | 不通过 = 不发；多源交叉验证（澎湃/工人日报/搜狐/官方回应）|
| D6 | 屏句 ≠ 配音 | `onscreen:` 行单独成屏上屏上整句，配音未授权走正文；这条结构保证来自 path_b_build.py 的 `check_onscreen` 闸门 |
| D7 | placeholder 不参与选择 | 11 个新 pack 的 placeholder composition 被 `load_style_pack` **直接跳过**；只剩占位壳的包视为不可渲染，在加载阶段停机点名替代包（2026-09-29 审计后收紧，旧口径"只是让加载通过"会误导到渲染期才崩）|
| D8 | AIGC 标识三件套对**交付件**不可关 | 显式角标（**左下角、字芯 ≥ 最短边 5%、开场常驻 4 秒**）+ mp4 元数据 `AIGC`（GB 45438-2025 附录 E）+ 发布时 `--declaration 内容由AI生成`；①② 由发射器无条件产出并读回核验，缺侧车的老成片一律重渲。**法律底线与自我加码要分清**：《标识办法》§ 4-四 的"应当"只落在**起始画面**与**播放周边**，末尾/中间是"可以"；左上角、贯穿全片、7.9% 字高都是我们自己加的，2026-09-29 按用户取舍退到线上（左下角 + 擦边字号 + 4 秒）。退掉的两档代价记在这里：①**播放周边**不再由贯穿全片的角标承担，改由 ② 元数据 + ③ 发布端声明承担；②左下角正是抖音标题/头像/进度条那一层的叠加区，平台 UI 会盖在角标上面（旧实现落左上角避开的就是这一层）；③擦边字号**没有余量**兜字体回退，换字体/换机器必须重量一次字面率（重量入口 `skills/douyin-pro/scripts/verify_aigc_badge.py`，量真实渲染像素而不是模型自己）|
| D11 | 标识的开关只能把东西变成**发不出去**，不能把它变成**没标** | 用户 2026-09-29 先要"默认关掉"、同日改口"还是默认都打开"，于是开关按**分层**落地，默认三件全开：渲染层 `--draft`（不烧 ①、不写 ②，侧车只留 `draft` 一段）与发布层 `check_publishable.py --allow-undeclared`（③ 可以不带，但要警告 + 在 `videos[].declaration` 留痕）。**关键设计不是"能不能关"，而是关完之后这份东西是什么**：草稿的台账**不含** `explicit` / `metadata_key` / `implicit` 三段（缺什么记什么缺，不写一堆 `false` 装作"标识在只是没开"），发布闸门读到即 EXIT=1 —— 所以"关掉标识"买到的是"能调版式、能量像素、不许发"，而不是"无标的成品"。合规默认值不许由一次会话的偏好改动：两个开关的**代码默认**永远是全开（不敲旗标、没有姿态文件 = 全开），"现在想关"落在 D12 的姿态文件里 |
| D12 | 关标识这件事**落在文件里，不落在代码里** | 用户 2026-09-29 又说「先帮我把两开关先关了吧」。把 `path_b_build.py` 的默认值改成草稿 = 让一次会话的偏好固化成合规基线（D11 正是为堵这个定的），所以改成三层裁决：**旗标 > 姿态文件 `routes/news/aigc-mode.json` > 代码默认（full / required）**。姿态文件受版本管理，于是"关掉了什么、谁关的、哪天关的、怎么回退"都能 `git diff` 出来（`since` / `by` / `revert` 三段是硬要求，由 `t_repo_aigc_mode_file_is_valid_and_recorded` 上闸）；两个方向都有单次旗标可压：渲染 `--draft`/`--deliver`、发布 `--allow-undeclared`/`--require-declaration`，同时给 = 报错。值拼错（`render: off`）或 JSON 坏了 **停机不回退默认**（R6）—— 一次拼写错误不该替用户决定合规姿态。日志、`aigc.json` 的 `switch` 与 `draft.reason`、闸门输出都**带真出处**（`draft(<路径> render=draft)` / `draft(旗标 --draft)`），事后能查是谁关的。**这条不改 D11 的判据**：姿态把渲染变成草稿后，闸门照旧 EXIT=1 —— 文件能决定"③ 带不带"，决定不了"没标的可以发"；② 元数据过抖音转码即失，③ 是唯一活到平台侧的那一件，所以 `declaration=undeclared` 期间发出去的每一条都要在 `videos[].declaration` 记 `undeclared` |
| D9 | 版式名只认**文件名词干** | 自动选版的词表是 `path_b_build.AUTO_LAYOUT_STEMS`（`hook / closer / story / stat / quote / catalog / rail`，元组顺序即兜底顺序）；pack 自己起的名字**不能**进自动候选 —— 只能按语义落到 canonical 文件名，映射在 pack 的 frame.md §6 记全，别让人再猜一遍。composition id 由 `MOUNT_TPL` 与文件名解耦，可保留 pack 前缀（`np-*`）维持公文身份。**这条坑是静默的**：2026-09-29 清点出 10 个未落地 pack 的 §7 共计划了 16 个词表外文件名（`evidence`/`lead-detail`/`compare`/`drilldown`/`clock`/`sit`/`list`/`diagram`/`list-steps`/`risk-callout`/`segment`/`chain`/`play`/`score`/`map`/`region`）—— 照那些名字建文件不会报错，只会得到一个自动模式永远选不到的惰性版式。已由 `t_auto_layout_stems_are_the_only_vocabulary` 上闸（点名表 ⊆ 词表 = 词表，可渲染 pack 的词干 ⊆ 词表）|
| D10 | 设计系统里的数字必须有**复算入口** | frame.md 的对比度表是"实测值"，但此前只能靠手抄维护：2026-09-29 首次全量复算抓到 11 个包共 **42 处**漂移，其中 `news-blast` 文档写 `score / pitch 5.0`（真值 **1.18**）而 §3 字阶据此把 22cqw 的主队比分染成红字压绿底 —— 手抄的假数会直接变成**播出后看不清的巨号字**。现在这类数一律由 `audit_pack_contrast.py` 从 §2 色板原值复算（判读线写进常量：正文 4.5 / 大字 3.0，1080 宽下 ≥2.22cqw ≈ 24px），文档只许写命令不许写脚本残留路径，改色板或改判定即红。**法则可以比数学严，数学不行**：gold 只作形状是包内法则，"gold 数学不过线"是假陈述 —— 审计按此区分 `VERDICT_CONTRADICTS_ARITHMETIC` |

---

## 6. 运行时目录约定

所有产物写 `.harness-news-runtime/` (被 `.gitignore` 忽略, 不被 bootstrap 冒烟删):

```
.harness-news-runtime/
├── hotboard/<date>.json          ← 选题线索 (Step 0 news-collect 产出)
├── articles/<id>-script.md     ← 口播稿 (Step 2 产出)
├── videos/<id>/final.mp4       ← 成片 (Step 4 产出)
├── videos/<id>/aigc.json       ← AIGC 标识侧车 (无此文件 = 成片不合规)
├── videos/<id>/contact-sheet.jpg ← 人工验收联络表
└── verifications/<date>-*.md   ← 端到端验证记录
```

**禁止写 `.ai-runtime-artifacts/`** — 那是 code 路由的运行时域 (news-workflow/SKILL.md 硬性规则 4 已说明)。

`verifications/` 默认随目录一起被忽略，这是一处**已知张力**：验证记录是"这件事真做过"的证据，
证据却在 git 外，换机器即等于没做过（2026-09-29 的 `tmp/contrast_policy.py` 就是活例 —— 复算脚本
落在忽略目录里，frame.md 只能指向一个 clone 后不存在的路径）。口径：
- **一次性**的跑动产物（草稿、日志、临时脚本）留在忽略目录，不进仓库；
- **契约证据**（能否证文档数字的脚本、判定基线、验证单）不许依赖 gitignore —— 脚本一律落到
  `skills/douyin-pro/scripts/` 受版本管理，文档只写仓库内命令；确有留存价值的验证单用
  `git add -f` 显式拉进版本管理，而不是让文档指向忽略路径。

---

## 7. 整合后的硬性规则 (新闻域)

1. **fact-check 不可跳过**: drafts[].fact_check 必须 passed 才能进 Step 4
2. **状态随做随记**: 每步结束更新 MEMORY (status / template / output)
3. **模板决策先于脚本**: 不知道选哪个模板就不开始写脚本
4. **产物写 `.harness-news-runtime/`**: 不写 `.ai-runtime-artifacts/` (那是 code 域)
5. **Path B only**: 不要传 `--template` 之外的渲染选项；不要尝试 Path A
6. **12 pack 自检**: 任何新加的 pack 必须先有 frame.md 才能 commit；三道闸全绿才算过 ——
   `path_b_selftest.py`(71 项) + `layout_selfcheck.py <pack 目录…>`(17 条结构不变量) +
   `audit_pack_contrast.py`(色板复算, 见 D10)。新 pack 的名字必须落 `AUTO_LAYOUT_STEMS`(见 D9)
7. **AIGC 标识对交付件不可关**: 交付件三件齐活 —— ①画面角标 ②mp4 元数据 ③发布自主声明，`aigc.json` 缺失的成片先重渲；
   发之前必须过 `check_publishable.py <成片>`（退出码 1 即不许发）。想不要标识只有**草稿轨**一条路
   （旗标 `--draft` 或姿态文件 `render=draft`），而它的产物本身就不可发布（见 D11）；③ 可以由
   姿态文件 `declaration=undeclared` 或旗标 `--allow-undeclared` 关掉，但关掉要在 `videos[].declaration`
   留痕（见 D12）—— **不许**拿"跳过闸门"当日常流程。姿态是文件里的一行，不是代码里的默认值：
   当前 `routes/news/aigc-mode.json` 关着，所以**交付必须显式加 `--deliver`**，别把草稿当成品发
8. **不可渲染的包不许选**: 决策树命中只有占位壳的 pack 时, 政策/法规类改落 `news-policy`、其余改落 `news-coral`, 或先补真版式
9. **采集零付费**: 热点线索只来自 `skills/news-collect`（stdlib-only，本机可复跑）；不调用任何按次扣费的榜单/话题搜索（Beatra 6/60 credits）。缺源补免费源，不花钱

---

## 8. 当前进度 (2026-09-29)

```
$ python skills/douyin-pro/scripts/path_b_selftest.py
[selftest] 71 项 · style=news-coral
  ok    t_aigc_mode_code_defaults_are_all_on
  ok    t_aigc_mode_file_flips_defaults_and_flags_override_both_ways
  ok    t_aigc_mode_reason_names_the_true_source
  ok    t_aigc_mode_rejects_bad_values_instead_of_defaulting
  ok    t_auto_layout_stems_are_the_only_vocabulary
  ok    t_draft_badge_absent_but_subtitles_kept
      可渲染 pack (有真版式): 2/12 —— news-coral, news-policy
  ok    t_full_loadability_progress
  ok    t_pack_contrast_docs_match_palette_math
  ok    t_publish_gate_default_requires_declaration
  ok    t_publish_gate_refuses_draft_and_missing_sidecar
      姿态文件 D:\work\...\harness-factory\routes\news\aigc-mode.json: render=draft · declaration=undeclared
  ok    t_repo_aigc_mode_file_is_valid_and_recorded
[selftest] 全绿 71/71

$ python skills/douyin-pro/scripts/audit_pack_contrast.py
对比度审计通过：12 个 pack 的 frame.md 色板与文档一致（0 条警告）

$ python skills/douyin-pro/scripts/layout_selfcheck.py \
    skills/douyin-pro/templates/hyperframes_path_b/news-coral \
    skills/douyin-pro/templates/hyperframes_path_b/news-policy
版式自检通过：12 个文件，0 条违规
```

集成状态：
- ✅ 12 pack frame.md (token 面) + host.html
- ✅ **色板复算闸门** `audit_pack_contrast.py`（D10）：11 个包 42 处手抄假数全部订正为算术值，含 `news-blast` 那条会播出 1.18:1 巨号红字的设计错误（改判为 white 数字 + score 下划条形状）。基线 42 与负例 EXIT=1 的复现命令见 `.harness-news-runtime/verifications/2026-09-29-contrast-audit-and-stem-gate-verification-lite.md`
- ✅ `AUTO_LAYOUT_STEMS` 上闸（D9）：词表从 `choose_layout` 的散装字面量收成单一常量，并锁定"点名表 = 词表 / 可渲染 pack ⊆ 词表"
- ✅ 验证记录的留存口径写进 §6（契约证据进 `scripts/` 受版本管理，文档不再指向 gitignore 路径）
- ✅ AIGC 标识落地：画面角标（**左下角、MarginV 303、字芯实测 55px = 最短边 1080 的 5.09%、
  开场 4.0s**）+ mp4 元数据 `AIGC`（GB 45438-2025 附录 E）+ `aigc.json` 侧车 + 读回核验（读不回即拒绝交付）。
  像素判据由 `verify_aigc_badge.py` 复现：实测含描边阴影墨迹 y **1549–1615** vs 模型
  `ink_bounds(mv=303)` **1549.3–1615.0**（上侧差 0.3px、下侧 0.0px）；距左 49px = 4.54cqw、
  距底 310px = 16.15cqh（仍在底部 20cqh 带内，视觉上就是左下角）；窗口内差异占比 76.6%、窗口外 **0.0%**。
  植入假字号（FontSize 75→60）的负例报 3 条违规并 EXIT=1。命令与完整输出：
  `.harness-news-runtime/verifications/2026-09-29-aigc-badge-bottom-left-floor-verification-lite.md`
  **订正（同日）**：那条记录 §2.2 引用的 `fixtures/badge_probe_shots.json` 当时是**发射器产出的 shots 文件**
  （只有 `values`、没有 `body`），照原命令重跑会在分镜 1 停机报"正文为空"—— 几何结论不受影响
  （字芯/墨迹只由分辨率与 ASS 样式决定，已用改成真输入的 fixture 重渲复测，上列数字逐字复现），
  但**时序那几行的 `t=27.00s / 49.79s` 是 50.0s 探针的采样点**，换输入后总时长变 43.0s，采样点随之变。
  复现命令的机器前提也补一句：`hyperframes` 要 **Node ≥ 22**（本机 nvm 默认曾切到 20.9.0，
  `npx -y hyperframes` 会报 `requires Node.js >= 22` 且 `check.json` 为空 —— 那不是版式失败）
  **订正 2（同日，重跑开关那次发现）**：同一条记录 §2.3 的**时序基准是裸 `silent.mp4`**（烧 ASS 之前），
  当时那句"所以差异只可能来自角标"不成立 —— 角标 bbox 落在字幕带上，窗口外那一行少的是**整行字幕**，
  43.0s 探针上 `t=23.50s` 量到 2454px = 8.5% 全被算进角标差异，而旧代码只按 `>15%` 判在不在，
  于是 8.5% 落进 `[1%,15%]` 判据空档却被打了 `✓`（脚本注释写着"落进空档按失败处理"，代码没做）。
  基准已改为**同刻重烧**：把"删掉 AIGC 条"的 ASS 烧到 `silent` 在同一时刻的帧上，两边只剩角标之差
  （不能先抽静帧再烧 —— 静帧输入的时间轴从 0 起算，libass 按 local t=0 选字幕，量不到 t 秒那一行）；
  空档同时改为**按失败停机**。改后同一行 **2454px → 3px**，上面那句"窗口外 **0.0%**"从此才真是
  由构造成立的事实。命令与完整输出见开关那份记录 §4
- ✅ **标识开关按层落地，代码默认全开**（D11）：渲染 `--draft` 出草稿（无 ①②，台账只留 `draft` 段）、
  发布 `check_publishable.py` 结算 —— 草稿 EXIT=1 拒发，交付件 EXIT=0 打印 ③ 必带的
  `--declaration 内容由AI生成`。两条轨都在真实渲染件上验过（同一条 fixture、同一台机器）：
  草稿的 `ffprobe` 里查不到 `AIGC` 键、`verify_aigc_badge.py` 直接报"ASS 里没有 AIGC 事件"并 EXIT=1，
  交付件则 `Label=1` 读回 + 角标三项几何全过。记录见
  `.harness-news-runtime/verifications/2026-09-29-aigc-switch-draft-rail-and-publish-gate-verification-lite.md`

- ✅ **两开关的"现在想关"落进姿态文件**（D12，2026-09-29 用户「先帮我把两开关先关了吧」）：
  `skills/douyin-pro/scripts/aigc_mode.py` 单点裁决 **旗标 > `routes/news/aigc-mode.json` > 代码默认**，
  渲染与发布两个脚本共用；反向旗标 `--deliver` / `--require-declaration` 让单次动作照样能全开，
  值拼错（`render: off`）与 JSON 坏了一律 `ModeError` 停机、**不回退默认**。仓库当前姿态
  `render=draft · declaration=undeclared`（带 `since` / `by` / `revert` 三段，由
  `t_repo_aigc_mode_file_is_valid_and_recorded` 上闸），代价在真实渲染件上逐项量过：默认那一次
  落地就是草稿（台账 `switch` 写的出处是姿态文件路径、`ffprobe` 无 `AIGC` 键、
  `verify_aigc_badge.py` 报"ASS 里没有 AIGC 事件" EXIT=1），加 `--deliver` 那一次角标三项全过
  （字芯 55px = 5.09%）、`Label=1` 读回；闸门对草稿 EXIT=1 拒发、对交付件 EXIT=0 但按姿态打
  ③ 警告，`--allow-undeclared` 与 `--require-declaration` 同时给 = 矛盾停机。记录见
  `.harness-news-runtime/verifications/2026-09-29-aigc-posture-file-verification-lite.md`
  ⚠️ **姿态开着就等于"默认渲染不可发布"**：现在要交付必须显式 `--deliver`，别顺着默认渲完就发
- ✅ 发布链路：`--declaration 内容由AI生成` 已对齐上游源码，成功凭据写进 skill
- ✅ 占位包改为**加载期停机**（不再拖到渲染第 1 镜）
- ✅ 进度指标换成可交叉核验的"有真版式 pack 数"（2/12）
- ✅ `news-policy` 5 个真版式落地（占位壳已删），五镜探针过 `--check-only` 门禁（记录见 `.harness-news-runtime/verifications/2026-09-29-news-policy-layouts-verification-lite.md`）
- ⏳ 10 pack 的真 composition（一个个补）
- ✅ t001 已按 v003 脚本重渲为 `videos/t001-v4/`（标识三件套 + 三处独立核验通过）；v001/v002/v003 保留为历史
- ⏳ 发布前定 `--aigc-producer` 真实主体名（现在是默认值 harness-news-pathb）
- ⏳ 抖音账号未登录 → 发布这一步只能交用户手动完成

---

## 9. 下一步建议 (按 ROI 排序)

1. ~~按 v003 脚本重渲 t001~~ ✅ 已做（`videos/t001-v4/`，59.3s / 1.97MB，标识三件套 + 三处独立核验通过）。剩下一件人定的事：**发布前把 `--aigc-producer` 换成真实主体名**再渲一次（现在是默认值）
2. **补 1-2 个高 ROI 包的 composition**：`news-policy` ✅ 已落地，下一个是 `news-stat`（视觉差异最大，且新闻域真会命中）。**动手前先按 D9 把该包 frame.md §7 的计划名重映射到 canonical 词干**（`news-stat` 的 `compare` / `drilldown` 都不在词表里），补完删掉 `placeholder.html`，可渲染计数自然涨；色板表随后过 `audit_pack_contrast.py`
3. **登录抖音账号（用户本人扫码）**：链路已到"可发布"，缺的只是 cookie；agent 不代替扫码
4. ~~免费采集层 `news-collect`~~ ✅ 已建并接入步骤 0（stdlib-only，无 key 无付费）：百度热搜 board API + feedx RSS 双轨，实测源/新鲜度/字段坑见 `skills/news-collect/SKILL.md`。DailyHotApi 公共实例本机 DNS 解析失败 → 只做 `--base-url` 自建选项，不作默认。`npm run index` 已收录（48 active）
5. ~~news-polish / humanizer-zh 从工作流引用里删掉~~ ✅ 已做（v1 文字轨已从 `core/runbooks.md` / `core/intent-routing.md` 清干净，两条治理文档改为指向 `skills/news-workflow/SKILL.md` 单一事实源）

---

> 任何对本架构的修改先动这里（`routes/news/ARCHITECTURE.md`），再改下游；架构文档是 v2 的唯一事实源。
