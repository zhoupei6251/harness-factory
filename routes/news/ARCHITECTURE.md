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
hot-topic-content-maker (Step 1)
   ↓ 产出: 选题 + 简报
media-short-video-copy / viral-script-writer (Step 2)
   ↓ 产出: 口播稿 (.harness-news-runtime/articles/<id>-script.md)
12 pack 决策树 (Step 2.5)
   ↓ 产出: videos[].template (news-coral | news-ink | ...)
fact-check (Step 3, 硬门禁)
   ↓ 产出: drafts[].fact_check = passed
douyin-pro Path B (Step 4)
   ↓ 产出: .harness-news-runtime/videos/<id>/final.mp4
douyin-upload upload-video (Step 5)
   ↓ 产出: MEMORY.published_at 回填
```

每一步产出都写回 MEMORY.md；流程是 6 步, 但实际写状态只要 4 个字段：
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
│   ├── path_b_build.py             ← 9 步发射器 (解析→配音→发射→自检→门禁→渲染→动量→烧字幕→联络表)
│   ├── layout_selfcheck.py          ← 17 条结构不变量 (渲前拦截)
│   ├── path_b_selftest.py           ← 47 项纯函数断言 (含 12 pack 加载检查)
│   ├── commons_media.py             ← 图片层 (path B 当前未启用, 留作图片型模板扩展)
│   └── install_path_b_deps.py       ← 依赖一键装
├── templates/hyperframes_path_b/   ← 12 个节目包
│   ├── news-coral/                  ← 完整 (frame + host + 7 compositions)
│   ├── news-ink/                    ← frame + host + placeholder (待补 composition)
│   ├── ... (10 more)
│   └── <12 包>/frame.md             ← token 与版面法则 (唯一事实源)
└── skills/video-render-engine/        ← 配音×渲染 详解 (子模块)
skills/douyin-upload/                 ← 发布 (`sau` CLI 包装)
skills/fact-check/                    ← 事实核查 (硬门禁)
skills/media-short-video-copy/        ← 视频脚本生成器 (主)
skills/viral-script-writer/           ← 视频脚本生成器 (备)
skills/hot-topic-content-maker/       ← 选题
```

**核心发射器 `path_b_build.py` 不动**——已经支持 12 pack + `--template` 参数。

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

**当前状态**（自检 `t_full_loadability_progress` 实时报告）：
- `news-coral`: 完整（7 个 composition）
- 其余 11 个: frame.md + host.html + 1 个 placeholder composition
- 后续 composition 一个个补；补完一个，`t_full_loadability_progress` X/12 递增

---

## 5. 关键决策记录

| # | 决策 | 取舍 |
|---|---|---|
| D1 | 单条线 (视频 only) | 用户最终产物是视频；text track 是 dead-end 投入 |
| D2 | Path B only | 用户只做免费；Path A 留在 `douyin-pro/SKILL.md` 标注为"非新闻领域可启用"，不在新闻工作流中 |
| D3 | 12 pack 决策树 | 一份脚本可对应 12 种视觉气质；决策由稿件特征词驱动，不靠人挑 |
| D5 | fact-check 硬门禁 | 不通过 = 不发；多源交叉验证（澎湃/工人日报/搜狐/官方回应）|
| D6 | 屏句 ≠ 配音 | `onscreen:` 行单独成屏上屏上整句，配音未授权走正文；这条结构保证来自 path_b_build.py 的 `check_onscreen` 闸门 |
| D7 | placeholder 不参与选择 | 11 个新 pack 的 placeholder composition 只是让 `load_style_pack` 通过；真正的 hook/closer/内容版式待续 |

---

## 6. 运行时目录约定

所有产物写 `.harness-news-runtime/` (被 `.gitignore` 忽略, 不被 bootstrap 冒烟删):

```
.harness-news-runtime/
├── articles/<id>-script.md     ← 口播稿 (Step 2 产出)
├── videos/<id>/final.mp4       ← 成片 (Step 4 产出)
└── verifications/<date>-*.md   ← 端到端验证记录 (可选)
```

**禁止写 `.ai-runtime-artifacts/`** — 那是 code 路由的运行时域 (news-workflow/SKILL.md 硬性规则 4 已说明)。

---

## 7. 整合后的硬性规则 (新闻域)

1. **fact-check 不可跳过**: drafts[].fact_check 必须 passed 才能进 Step 4
2. **状态随做随记**: 每步结束更新 MEMORY (status / template / output)
3. **模板决策先于脚本**: 不知道选哪个模板就不开始写脚本
4. **产物写 `.harness-news-runtime/`**: 不写 `.ai-runtime-artifacts/` (那是 code 域)
5. **Path B only**: 不要传 `--template` 之外的渲染选项；不要尝试 Path A
6. **12 pack 自检**: 任何新加的 pack 必须先有 frame.md 才能 commit；通过 `path_b_selftest.py` 47 项

---

## 8. 当前进度 (2026-09-29)

```
$ python skills/douyin-pro/scripts/path_b_selftest.py
[selftest] 47 项 · style=news-coral
  ok    t_all_templates_in_constant
  ok    t_every_template_has_frame_md
  ok    t_fully_loaded_packs_have_required_files
  ok    t_partial_packs_logged
  ok    t_default_style_matches_first_template
      12 pack 中已完整加载 (host.html 在位) 的: 12/12
  ok    t_full_loadability_progress
  ...
[selftest] 全绿 47/47
```

集成状态：
- ✅ 12 pack frame.md (token 1面)
- ✅ 12 pack host.html + placeholder composition (loadable)
- ⏳ 11 pack 的真 composition (一个个补, 不在 v2 范围)

---

## 9. 下一步建议 (按 ROI 排序)

1. **先跑一条 t001 验证 v2 整链路**: `--template news-coral`, 跑出来确认 wire 通
2. **补 1-2 个高 ROI 包的 composition**: `news-policy` + `news-stat` (视觉差异最大)
3. **把 news-polish / humanizer-zh 从工作流 skill 引用里删掉**: 它们不在 v2 用, 留着误导新人
4. **Path A 在 douyin-pro/SKILL.md 标 "Coming soon for non-news"**: 不删 (其他领域可能用), 但明示新闻域不用

---

> 任何对本架构的修改先动这里（`routes/news/ARCHITECTURE.md`），再改下游；架构文档是 v2 的唯一事实源。
