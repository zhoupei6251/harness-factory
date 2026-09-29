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
└── (无产物目录, 运行时落 .harness-news-runtime/)

skills/news-workflow/SKILL.md        ← 入口: 6 步工作流
skills/douyin-pro/                   ← 渲染器 (Path B)
├── SKILL.md                         ← 通用 Skill (Path A 仍标注为"非新闻可用")
├── scripts/
│   ├── path_b_build.py             ← 9 步发射器 (解析→配音→发射→自检→门禁→渲染→动量→烧字幕+AIGC→联络表)
│   ├── layout_selfcheck.py          ← 17 条结构不变量 (渲前拦截)
│   ├── path_b_selftest.py           ← 58 项纯函数断言 (含 12 pack 加载 + AIGC 标识合规)
│   ├── commons_media.py             ← 图片层 (path B 当前未启用, 留作图片型模板扩展)
│   └── install_path_b_deps.py       ← 依赖一键装
├── templates/hyperframes_path_b/   ← 12 个节目包
│   ├── news-coral/                  ← 完整 (frame + host + 7 compositions)
│   ├── news-ink/                    ← frame + host + placeholder (待补 composition)
│   ├── ... (10 more)
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

**核心发射器 `path_b_build.py`**——支持 12 pack + `--template`，并无条件产出 AIGC 标识（画面角标 + mp4 元数据 + `aigc.json` 侧车）。

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
- `news-coral`: 完整（7 个 composition）—— **当前唯一可渲染的包**（`可渲染 pack (有真版式): 1/12`）
- 其余 11 个: frame.md + host.html + 只有 `placeholder.html`（占位壳，**不参与版式选择**）
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
| D8 | AIGC 标识三件套不可关 | 显式角标（字芯 ≥ 最短边 5%、贯穿全片）+ mp4 元数据 `AIGC`（GB 45438-2025 附录 E）+ 发布时 `--declaration 内容由AI生成`；①② 由发射器无条件产出并读回核验，缺侧车的老成片一律重渲 |

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

---

## 7. 整合后的硬性规则 (新闻域)

1. **fact-check 不可跳过**: drafts[].fact_check 必须 passed 才能进 Step 4
2. **状态随做随记**: 每步结束更新 MEMORY (status / template / output)
3. **模板决策先于脚本**: 不知道选哪个模板就不开始写脚本
4. **产物写 `.harness-news-runtime/`**: 不写 `.ai-runtime-artifacts/` (那是 code 域)
5. **Path B only**: 不要传 `--template` 之外的渲染选项；不要尝试 Path A
6. **12 pack 自检**: 任何新加的 pack 必须先有 frame.md 才能 commit；通过 `path_b_selftest.py` 58 项
7. **AIGC 标识不可关**: ①画面角标 ②mp4 元数据 ③发布自主声明 三件齐活；`aigc.json` 缺失的成片先重渲
8. **不可渲染的包不许选**: 决策树命中只有占位壳的 pack 时, 改落 `news-coral` 或先补真版式
9. **采集零付费**: 热点线索只来自 `skills/news-collect`（stdlib-only，本机可复跑）；不调用任何按次扣费的榜单/话题搜索（Beatra 6/60 credits）。缺源补免费源，不花钱

---

## 8. 当前进度 (2026-09-29)

```
$ python skills/douyin-pro/scripts/path_b_selftest.py
[selftest] 58 项 · style=news-coral
  ok    t_full_loadability_progress
      可渲染 pack (有真版式): 1/12 —— news-coral
  ...
[selftest] 全绿 58/58
```

集成状态：
- ✅ 12 pack frame.md (token 面) + host.html
- ✅ AIGC 标识落地：画面角标（字芯 62px ≥ 最短边 5%、贯穿全片）+ mp4 元数据 `AIGC`（GB 45438-2025 附录 E）+ `aigc.json` 侧车 + 读回核验（读不回即拒绝交付）
- ✅ 发布链路：`--declaration 内容由AI生成` 已对齐上游源码，成功凭据写进 skill
- ✅ 占位包改为**加载期停机**（不再拖到渲染第 1 镜）
- ✅ 进度指标换成可交叉核验的"有真版式 pack 数"（1/12）
- ⏳ 11 pack 的真 composition（一个个补）
- ✅ t001 已按 v003 脚本重渲为 `videos/t001-v4/`（标识三件套 + 三处独立核验通过）；v001/v002/v003 保留为历史
- ⏳ 发布前定 `--aigc-producer` 真实主体名（现在是默认值 harness-news-pathb）
- ⏳ 抖音账号未登录 → 发布这一步只能交用户手动完成

---

## 9. 下一步建议 (按 ROI 排序)

1. ~~按 v003 脚本重渲 t001~~ ✅ 已做（`videos/t001-v4/`，59.3s / 1.97MB，标识三件套 + 三处独立核验通过）。剩下一件人定的事：**发布前把 `--aigc-producer` 换成真实主体名**再渲一次（现在是默认值）
2. **补 1-2 个高 ROI 包的 composition**：`news-policy` + `news-stat`（视觉差异最大，且新闻域真会命中）；补完删掉 `placeholder.html`，可渲染计数自然涨
3. **登录抖音账号（用户本人扫码）**：链路已到"可发布"，缺的只是 cookie；agent 不代替扫码
4. ~~免费采集层 `news-collect`~~ ✅ 已建并接入步骤 0（stdlib-only，无 key 无付费）：百度热搜 board API + feedx RSS 双轨，实测源/新鲜度/字段坑见 `skills/news-collect/SKILL.md`。DailyHotApi 公共实例本机 DNS 解析失败 → 只做 `--base-url` 自建选项，不作默认。`npm run index` 已收录（48 active）
5. ~~news-polish / humanizer-zh 从工作流引用里删掉~~ ✅ 已做（v1 文字轨已从 `core/runbooks.md` / `core/intent-routing.md` 清干净，两条治理文档改为指向 `skills/news-workflow/SKILL.md` 单一事实源）

---

> 任何对本架构的修改先动这里（`routes/news/ARCHITECTURE.md`），再改下游；架构文档是 v2 的唯一事实源。
