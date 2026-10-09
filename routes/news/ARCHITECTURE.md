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
| 模板选择 | 没有（所有视频共用一个 PPT 模板）| 32 pack 决策树（按新闻形态，2026-10-08 补齐变体后从 12 扩到 32，见 D15/D20）|
| 入口步骤数 | 7（含两轨切换 + Path 选择）| 3（含模板决策）|
| 文档位置 | 跨多个文件且互相引用 | 6 步全部在 news-workflow/SKILL.md |

### 为什么整合

- 用户最终产物 = 视频 → text track 是 dead-end 投入
- news-polish + humanizer-zh 是文字稿后处理；视频脚本由脚本生成器自带润色
- Path A（付费）= 你只做免费，从未用过

---

## 2. 数据流（6 步一气呵成）

```
news-collect (Step 0a · 零成本采集，无 key 无付费)
   ↓ 产出: .harness-news-runtime/hotboard/<date>.json（选题线索清单）
news-curate (Step 0b · 台账去重 + 免费热度排序)
   ↓ 产出: .harness-news-runtime/curated/<date>.json（带理由的候选清单 + 剔除明细）
   ↓ 台账: routes/news/ledger.jsonl（追加，已发/在途事件永不再作新选题）
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
   ↓ 姿态: 交付轨(full) / 交付轨不烧角标(no-badge) / 草稿轨(draft) 由 aigc_mode.py 裁决 —— 旗标 > routes/news/aigc-mode.json > 代码默认(全开)
check_publishable.py (Step 4.5 · 发布闸门)
   ↓ 判据: 照 aigc.json 核「② 在 + ① 有交代」(D14), 打出 ③ 必带的 --declaration 参数; ① 没烧时 ③ 不给豁免; 退出码 1 = 不许发
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
├── DESIGN-dedup.md                  ← 去重台账 + 策展层设计（含三轮阈值实测数据）
├── MEMORY.md                        ← 选题 / 草稿 / 成片 / 进度 状态
├── ledger.jsonl                     ← **已发/在途事件台账**（追加语义, 受版本管理）
├── aigc-mode.json                   ← 标识两开关的**当前姿态**(受版本管理; 没有这文件=全开, 见 D12; render 三档 full/no-badge/draft, 见 D14)
└── (无产物目录, 运行时落 .harness-news-runtime/)

skills/news-curate/                   ← 选题策展层（去重 + 免费热度排序 + 台账回写）
├── SKILL.md                         ← 台账写法的单一事实源（硬性规则 9 的细则在这）
├── scripts/curate.py                ← 去重/打分纯函数 + CLI（只写 candidate）
├── scripts/ledger.py                ← 状态回写 CLI：mark（追加迁移, 沿用同事件主键）/ check（主键体检）
└── scripts/curate_selftest.py       ← 纯离线断言集（项数以脚本末行输出为准）
skills/news-workflow/SKILL.md        ← 入口: 6 步工作流
skills/douyin-pro/                   ← 渲染器 (Path B)
├── SKILL.md                         ← 通用 Skill (Path A 仍标注为"非新闻可用")
├── scripts/
│   ├── path_b_build.py             ← 9 步发射器 (解析→配音→发射→自检→门禁→渲染→动量→烧字幕+AIGC→联络表)
│   ├── layout_selfcheck.py          ← 17 条结构不变量 (渲前拦截; 参数是目录, 空目录=用法错误非零退出, 见 D13)
│   ├── audit_pack_contrast.py       ← frame.md 色板与对比度表复算 (文档里的"实测值"不许手抄)
│   ├── verify_aigc_badge.py         ← AIGC 角标真像素复测 (字芯/墨迹/时长三项; 时序基准 = silent 同刻重烧无角标 ASS; 文档数字只认它; 只量 full 档, no-badge 产物它报"没有 AIGC 事件"即 EXIT=1)
│   ├── check_publishable.py         ← 发布闸门 (照 aigc.json 核"② 在 + ① 有交代", D14; 打出 ③ 必带参数, ① 没烧时不给 ③ 豁免; 草稿在这里被拒)
│   ├── aigc_mode.py                 ← 两开关的**默认姿态**裁决 (渲染层三档 full/no-badge/draft + 发布层两档; 旗标 > routes/news/aigc-mode.json > 代码默认; 值不合法即 ModeError)
│   ├── fixtures/badge_probe_shots.json ← 探针**输入** (5 镜 news-policy): 发射器渲它、复测器量它
│   ├── path_b_selftest.py           ← 纯函数断言集 (项数以脚本输出为准, 别在文档里抄数; 覆盖 12 pack 加载
│   │                                  + AIGC 合规 + 三档渲染/发布闸门判据/姿态文件 + 词表
│   │                                  + 三道闸各自的假绿负例: 色板种错数 / 版式传空目录 / 草稿与缺侧车与没交代的 ①)
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

**核心发射器 `path_b_build.py`**——支持 12 pack + `--template`，交付轨产出 AIGC 标识并读回核验：**full 档**烧 ① 画面角标 + 写 ② mp4 元数据 + `aigc.json` 侧车，**no-badge 档**（D14 新增）只写 ②，产物依旧可发布、代价是发布必须带 ③；草稿轨（旗标 `--draft` 或姿态文件 `render=draft`）不烧不写，代价由 `check_publishable.py` 结算：草稿发不出去。② 两档都不许缺，缺侧车的老成片一律重渲。走哪一档由 `aigc_mode.py` 一处裁决（旗标 `--deliver` / `--no-badge` / `--draft` 三选一 > `routes/news/aigc-mode.json` > 代码默认 full），见 D11/D12/D14。

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

**当前状态**（2026-10-08 实测，**推翻旧文档的 2/12 说法**）:
- **32 个 pack 全部有真版式**：12 master + 20 派生变体，每个 `compositions/` 7 个真 composition
- `placeholder.html` 已全删；`load_style_pack` **32/32 成功**；`layout_selfcheck.py` 32 包 234 文件 **0 条违规**
- 20 个派生变体已补 `frame.md`（含 `derived_from` 派生声明，D16）
- ⚠️ **色板审计仍有 24 条 OFF_PALETTE_HEX，是刻意保留的**：这些色自动替换会让对比度从
  ~16:1 掉到 ~1.1:1（把白字换成深底），属于"该补进 frame.md 算设计补全"而非"改色"。
  `t_no_pack_has_off_palette_after_repair` 锁的是"不许有第四类未解释越界"，基线 24（D19）
- 三道闸现状：`path_b_selftest.py` 全绿 78/78 · `layout_selfcheck.py` 234 文件 0 违规 ·
  `audit_pack_contrast.py` 24 条（D19 刻意保留项）

---

## 5. 关键决策记录

| # | 决策 | 取舍 |
|---|---|---|
| D0 | **去重台账 + 策展层**（2026-10-08 落地，设计见 `DESIGN-dedup.md`） | 台账 `routes/news/ledger.jsonl` 追加语义、受版本管理；**当前状态 = 最后一行**。L1 归一化精确匹配才允许自动硬剔除，**L2 相似度永不自动剔除**（中文短标题 n-gram 无法同时做到"认得出同事件/分得开不同事件"，三轮实测 0.00~0.29 vs 阈值 0.45，跨媒体同事件只作 `needs_review` 提示交人确认）。热度只用三个免费信号：百度榜名次 + `age_days` 半衰期 + 跨源命中；**RSS 源的 rank 是 feed 序号不是热度**（实测 4 源各有 rank=1 实为 4 条不同新闻）。`curate.py` 只写 `candidate`，状态迁移由 news-workflow 单一写者追加 |
| D15 | **32 个 pack 全部有真版式**（2026-10-08 实测推翻旧文档的 "2/12"） | `compositions/` 每个包 7 个真 composition、placeholder 已全删、`load_style_pack` 32/32 成功。**旧文档的「2/12 可渲染」「⏳ 10 pack 待补」是错的**，害得接手的人以为要干两天模板。`t_placeholder_pack_stops_at_load` 改成断言"无未就绪包"，停机能力另用临时空壳包验证（能力不丢，只是不再用"必须有未就绪包"这种会长期变红的写法） |
| D16 | **20 个派生变体补 frame.md + 写明派生关系** | 变体缺 frame.md 并不阻断渲染（`load_style_pack` 不要求它，32/32 可加载），所以这是**契约缺口**不是能力缺口：`routes/news/scripts/gen_variant_frames.py` 按各变体 HTML 的**真实用色**生成色板表 + 写 `derived_from: <master>`。生成器不写对比度表（不手抄"实测值"，D10 的教训）。补完后色板审计的覆盖面从 12 个包扩到 32 个 |
| D18 | **OFF_PALETTE_HEX 承认设计系统共享 token 层** | 32 包填实后审计报 **561 条**，逐条查是**跨包共享角色色**（`#e85d5d` 出现 32 次 = 主强调、`#1a1a1a` 50 次 = 卡底、`#6b6b6b` 33 次 = 次级字），不是"从 coral 复制来的垃圾"。**不去改 561 处版式**：干跑证明按亮度机械重映射会毁掉语义（alert 的次级灰会变 ok 绿、ink 的警示红会变灰）——审计从 561 变 0，但播出的是 561 处视觉事故。**审计的判据要跟设计意图一致，不为了让工具变绿而毁掉产物。** 纳入标准是可复算的：实测出现 ≥6 次即入 `SHARED_TOKENS`；`shared_token_calibration()` + `shared_tokens_need_review()` 负责校准（它第一次跑就抓到 `#f0f0f0` 只有 3 次，共享层自己也会变成第二个手抄假数） |
| D19 | **复制残留按 CSS 角色替换，不按亮度** | 共享层把 561 降到 72，剩下精确集中在 10 个包 × 4 个版式（stat/rail/closer/catalog）。判据是**CSS 属性 + class 语义**：`.st-rule` 这类是强调短横线 → 该映射到本包强调/形状色（alert→`warn` 黄，该包色板明确写"warn 只作三角形状"）；其余 `background:` → 映射到面/底色。**两次踩坑换来的**：第一版按亮度四分类（灰字变绿字），第二版按"同亮度本包色"（深底 `#1a0808` 映到深红 `#a11d2e`、橙短横线映到 ok 绿）——**亮度接近 ≠ 角色相同**。每处替换都验"对比度不得低于替换前"（D19 顺带发现 12 个色自动换会把 16:1 的白字变成 1.1:1，**刻意不改**）。脚本 `fix_residual_colors.py` 有 `--apply` 开关，dry-run 必看。⚠️ **踩坑记录**：第一版没排除 `#root` 的地面色，把 3 个包的整片底色换了（球场绿当整片底）——地面色是整片的底，改它等于改掉整个视觉。已回滚并把三个地面色补进各包色板表（`add_ground_declarations.py`，`GROUND_TONE_BY_HEX` 登记过但 frame.md 没声明，两套登记表口径不一致） |
| D20 | **pack 数量一律现算，不许手抄** | 你问「不是 31 个吗」—— 查下来 `decide_pack.py` 的 `PACK_BUCKETS` **正好覆盖 32 个、一个不缺**，错的只是 `--list` 输出与 `pack-decision.md` 标题里手写的「31」。这已是本项目第二次被"手抄数字悄悄过期"咬（D15 的「2/12」同一个病）。修法**不是把 31 改成 32**（下次加包又漂），而是：`decide_pack.py` 加 `all_template_names()` 从 `path_b_build.ALL_TEMPLATES` 现算 + 脱节当场告警；`curate.py` 加 `ALL_TEMPLATE_NAMES` 同源读取；4 条断言锁住 —— 决策表集合必须等于真实模板 / 清单不许退化成手抄 / MEMORY 决策树必须列全 32 行 / 文档里"总量口吻"的 pack 数必须等于真实值（**局部计数如"12 个 master"不管**，混进去只会逼人加豁免名单，形同虚设）。**顺带修一个真缺口**：MEMORY 决策树表原来只画 `primary` = 27 行，**漏掉 5 个只在 `secondary` 出现的包**（表格是选包第一眼看的地方，漏一个等于那个包选不到）—— 修表脚本里的 `assert len(rows)==len(ALL_TEMPLATES)` 专门拦这种漏 |
| D21 | **首次实跑 t002 暴露的 5 个缺口**（2026-10-08，全部已修） | 静态检查全绿的情况下跑通一条真新闻，暴露的都是"检查不出来、只有真跑才会现形"的问题：<br>**① 配图拿 kicker 当检索词** → `image_query` 旧优先级「显式 image > kicker > 没有」，而 kicker 是**栏目名**（"现场数据"/"时间线"），拿它检索 Commons 得出「东航MU5735黑匣子寻获现场」——**2022 年空难图**，且授权闸(CC BY 3.0)、尺寸闸(961x720)、词面闸**三道同时放行**。改成只认显式 `image`（不写就降级无图）。<br>**② 词面闸对中文太松** → `CJK_SHINGLE=2`，任意 1 个二字块命中即放行，而"现场/数据/北京/市场"会出现在任何无关图里。收紧成「≥3 字连续公共子串 或 ≥2 个二字块」。**代价**：2 字地名（"常德"）不再放行 —— 有意取舍，无图比错图好。<br>**③ 渲染工作目录落在系统 temp** → `tempfile.mkdtemp()` + 15 分钟渲染（大半耗在 `npx` 拉包）等包拉好时 Windows 已清空 temp，`index.html` 连同前 4 段音频消失。改落 `.harness-news-runtime/work/`（`DEFAULT_WORK_ROOT`）。<br>**④ 门禁失败不报真话** → hyperframes 失败只说「报告无法解析: check.json」+ 给个 stderr **路径**，而 stderr 当时是空的。现在把 stderr 原文并进异常消息，并打工作目录 + index.html 是否存在。**"报不出原因的拒绝等于没有拒绝"。**<br>**⑤ 静默丢内容** → `title` 不进配音、而 `stat`/`closer`/`quote` 没有标题位 ⇒ 标题既不上屏也不出声，只有一条 ⚠。根因是**写稿时没看版式契约**，所以新增 `routes/news/scripts/check_scene_contract.py` 把这件事挪到写稿那一刻（`--demo` 自带 3 反例 + 1 不误报）。 |
| D22 | **台账主键撞车修复 + 状态回写 CLI**（2026-10-08） | 用户诉求「每次把发的新闻记住，不能重复生成」的落地点是**台账主键**，而它从第一天就是坏的：`curate.py` 的 `main()` 里 `entries` 只读一次，循环内反复调 `next_ledger_id(entries)` —— 同一份快照每次算出同一个 id，于是同批 43 个**不同事件全写成 `n0002`**（实测 `ledger.py check` 报「主键 n0002 被 43 个不同事件共用」）。去重靠 `norm_key` 没塌，但 `matched_ledger_id`、状态回写、`--sync-from-memories` 这类按 id 的引用会**指向错误的事件**。修法：`max_ledger_num(entries)+1` 起算的**运行时计数器**逐条自增 + 同一事件多源命中去重（按 `norm_key` 保首条）；顺手把「发布后回写 `published`」从手抄 `python -c` 固化成 `scripts/ledger.py mark`（沿用同事件主键、值拼错即停机、找不到目标不凭空追加）。已经存在的脏数据做了一次**一次性迁移**（按首现顺序重编，同事件沿用同 id，45 行 44 事件 → `n0001…n0044`）—— 这是唯一一次对台账原地改写，理由是"修坏掉的主键"不可能靠追加完成。断言 `t_new_candidates_get_unique_incrementing_ids` 锁住批量追加不许撞车，`t_ledger_mark_*` / `t_ledger_check_detects_id_collision` 锁住回写语义 |
| D1 | 单条线 (视频 only) | 用户最终产物是视频；text track 是 dead-end 投入 |
| D2 | Path B only | 用户只做免费；Path A 留在 `douyin-pro/SKILL.md` 标注为"非新闻领域可启用"，不在新闻工作流中 |
| D3 | 12 pack 决策树 | 一份脚本可对应 12 种视觉气质；决策由稿件特征词驱动，不靠人挑 |
| D5 | fact-check 硬门禁 | 不通过 = 不发；多源交叉验证（澎湃/工人日报/搜狐/官方回应）|
| D6 | 屏句 ≠ 配音 | `onscreen:` 行单独成屏上屏上整句，配音未授权走正文；这条结构保证来自 path_b_build.py 的 `check_onscreen` 闸门 |
| D7 | placeholder 不参与选择 | 11 个新 pack 的 placeholder composition 被 `load_style_pack` **直接跳过**；只剩占位壳的包视为不可渲染，在加载阶段停机点名替代包（2026-09-29 审计后收紧，旧口径"只是让加载通过"会误导到渲染期才崩）|
| D8 | AIGC 标识三件套对**交付件**不可关 | 显式角标（**左下角、字芯 ≥ 最短边 5%、开场常驻 4 秒**）+ mp4 元数据 `AIGC`（GB 45438-2025 附录 E）+ 发布时 `--declaration 内容由AI生成`；①② 由发射器无条件产出并读回核验，缺侧车的老成片一律重渲。**法律底线与自我加码要分清**：《标识办法》§ 4-四 的"应当"只落在**起始画面**与**播放周边**，末尾/中间是"可以"；左上角、贯穿全片、7.9% 字高都是我们自己加的，2026-09-29 按用户取舍退到线上（左下角 + 擦边字号 + 4 秒）。退掉的两档代价记在这里：①**播放周边**不再由贯穿全片的角标承担，改由 ② 元数据 + ③ 发布端声明承担；②左下角正是抖音标题/头像/进度条那一层的叠加区，平台 UI 会盖在角标上面（旧实现落左上角避开的就是这一层）；③擦边字号**没有余量**兜字体回退，换字体/换机器必须重量一次字面率（重量入口 `skills/douyin-pro/scripts/verify_aigc_badge.py`，量真实渲染像素而不是模型自己）。**判据在 D14 放宽过一次**：本行的"三件套对交付件不可关"改成"②③ 不可关、① 由开关决定" |
| D11 | 标识的开关只能把东西变成**发不出去**，不能把它变成**没标** | 用户 2026-09-29 先要"默认关掉"、同日改口"还是默认都打开"，于是开关按**分层**落地，默认三件全开：渲染层 `--draft`（不烧 ①、不写 ②，侧车只留 `draft` 一段）与发布层 `check_publishable.py --allow-undeclared`（③ 可以不带，但要警告 + 在 `videos[].declaration` 留痕）。**关键设计不是"能不能关"，而是关完之后这份东西是什么**：草稿的台账**不含** `explicit` / `metadata_key` / `implicit` 三段（缺什么记什么缺，不写一堆 `false` 装作"标识在只是没开"），发布闸门读到即 EXIT=1 —— 所以"关掉标识"买到的是"能调版式、能量像素、不许发"，而不是"无标的成品"。合规默认值不许由一次会话的偏好改动：两个开关的**代码默认**永远是全开（不敲旗标、没有姿态文件 = 全开），"现在想关"落在 D12 的姿态文件里。**D14 把本行收窄为"draft 档只把东西变成发不出去"**：中间档 `no-badge` 买到的是"① 没烧但可发布"，代价换成"③ 从此必带"，不再是"不许发" |
| D12 | 关标识这件事**落在文件里，不落在代码里** | 用户 2026-09-29 又说「先帮我把两开关先关了吧」。把 `path_b_build.py` 的默认值改成草稿 = 让一次会话的偏好固化成合规基线（D11 正是为堵这个定的），所以改成三层裁决：**旗标 > 姿态文件 `routes/news/aigc-mode.json` > 代码默认（full / required）**。姿态文件受版本管理，于是"关掉了什么、谁关的、哪天关的、怎么回退"都能 `git diff` 出来（`since` / `by` / `revert` 三段是硬要求，由 `t_repo_aigc_mode_file_is_valid_and_recorded` 上闸）；两个方向都有单次旗标可压：渲染 `--draft`/`--deliver`、发布 `--allow-undeclared`/`--require-declaration`，同时给 = 报错。值拼错（`render: off`）或 JSON 坏了 **停机不回退默认**（R6）—— 一次拼写错误不该替用户决定合规姿态。日志、`aigc.json` 的 `switch` 与 `draft.reason`、闸门输出都**带真出处**（`draft(<路径> render=draft)` / `draft(旗标 --draft)`），事后能查是谁关的。**这条不改 D11 的判据**：姿态把渲染变成草稿后，闸门照旧 EXIT=1 —— 文件能决定"③ 带不带"，决定不了"没标的可以发"；② 元数据过抖音转码即失，③ 是唯一活到平台侧的那一件，所以 `declaration=undeclared` 期间发出去的每一条都要在 `videos[].declaration` 记 `undeclared`。**D14 之后本行的姿态取值变了**：渲染档可以是 `no-badge`（中间档），而 ① 一旦没烧，`declaration` 就**不能**再是 `undeclared` —— 闸门对这类台账拒 EXIT=1，所以仓库当前姿态是 `render=no-badge · declaration=required`（旧写法 `render=draft · declaration=undeclared` 已由用户改选放宽判据）|
| D9 | 版式名只认**文件名词干** | 自动选版的词表是 `path_b_build.AUTO_LAYOUT_STEMS`（`hook / closer / story / stat / quote / catalog / rail`，元组顺序即兜底顺序）；pack 自己起的名字**不能**进自动候选 —— 只能按语义落到 canonical 文件名，映射在 pack 的 frame.md §6 记全，别让人再猜一遍。composition id 由 `MOUNT_TPL` 与文件名解耦，可保留 pack 前缀（`np-*`）维持公文身份。**这条坑是静默的**：2026-09-29 清点出 10 个未落地 pack 的 §7 共计划了 16 个词表外文件名（`evidence`/`lead-detail`/`compare`/`drilldown`/`clock`/`sit`/`list`/`diagram`/`list-steps`/`risk-callout`/`segment`/`chain`/`play`/`score`/`map`/`region`）—— 照那些名字建文件不会报错，只会得到一个自动模式永远选不到的惰性版式。已由 `t_auto_layout_stems_are_the_only_vocabulary` 上闸（点名表 ⊆ 词表 = 词表，可渲染 pack 的词干 ⊆ 词表）|
| D10 | 设计系统里的数字必须有**复算入口** | frame.md 的对比度表是"实测值"，但此前只能靠手抄维护：2026-09-29 首次全量复算抓到 11 个包共 **42 处**漂移，其中 `news-blast` 文档写 `score / pitch 5.0`（真值 **1.18**）而 §3 字阶据此把 22cqw 的主队比分染成红字压绿底 —— 手抄的假数会直接变成**播出后看不清的巨号字**。现在这类数一律由 `audit_pack_contrast.py` 从 §2 色板原值复算（判读线写进常量：正文 4.5 / 大字 3.0，1080 宽下 ≥2.22cqw ≈ 24px），文档只许写命令不许写脚本残留路径，改色板或改判定即红。**法则可以比数学严，数学不行**：gold 只作形状是包内法则，"gold 数学不过线"是假陈述 —— 审计按此区分 `VERDICT_CONTRADICTS_ARITHMETIC` |
| D13 | 闸门**不许空过**：显式传入的目录里没有版式文件 = 用法错误，非零退出 | 三道闸的价值是"查过了"，不是"没报错"。`layout_selfcheck.py` 旧行为：把 pack 名当目录传（`layout_selfcheck.py news-coral news-policy`）时逐条打印「没找到版式文件」，结尾仍输出「版式自检通过：0 个文件，0 条违规」并 **exit 0**（2026-09-29 订正 D12 文档时撞到）。假绿比红危险 —— 红会让人停下，假绿会被当凭据抄进文档与台账，且这是三道闸里唯一"参数握在人手里"的那道。现在显式目录贡献 0 个文件即 exit 1，报错点名是哪个目录并写出正确参数写法，`--quiet` 同样不放过（自测 `t_layout_selfcheck_refuses_a_directory_with_no_layouts` **双向**锁：真目录仍 0、pack 名与不存在目录必须 1）。取舍：没有"传了目录又想跳过检查"的合法写法 —— 要跳过就不传参数（`nargs="+"` 直接拒），不存在第三种。渲染期内部那道 `gate_layout_selfcheck` 走 `check_layout()` 逐文件，本来就不经过 CLI，不受影响。四条命令的真输出（绿/红/quiet/`--check-only`）见 `routes/news/evidence/2026-09-29-layout-selfcheck-no-empty-pass-verification-lite.md` |
| D14 | **判据放宽**：交付件可以不带 ①，②③ 才是可发布的底线 | 用户 2026-09-29 对「把 `path_b_build.py` 里烧角标那段删掉」这个来源无法核实的请求，选的是另一条路：不改能力、改判据 —— 原话「**判据放宽：交付件可以不带 ①** … D8/硬规则 7 从「交付件三件齐活」改成「② 元数据 + ③ 发布声明齐活即可发布，① 由开关决定」。交付轨能出无角标但可发布的片子，烧角标的代码留着（`--deliver` + 姿态 full 随时回来）。改的是判据，不是能力。」于是渲染层从两档变**三档**（`aigc_mode.RENDER_MODES = full / no-badge / draft`）：旧的两档里"不要角标"只能落到 `draft`，而 draft 连 ② 一起砍，产物发不出去 —— 想要的那个中间态根本不存在。**代价怎么结算**：① 没烧 ⇒ ③ 必带，`check_publishable.py` 对这类台账把 `declaration=undeclared` 与 `--allow-undeclared` 一律判 **EXIT=1** 并打印三条出路（不静默替用户改姿态，R6）；道理是 ② 过抖音转码即失，画面没标时 ③ 是唯一活到平台侧的那一件，所以关 ① 买不到"什么都不用说"。**台账原则随之分两条**：draft 依旧"缺什么记什么缺"（只留 `draft` 段），no-badge 是"关了什么记什么关"（`explicit` 段**必须存在**并写 `burned_in: false` + `disabled_by` 真出处 + `to_enable` 回退写法）；只有 `burned_in: false` 而没 `disabled_by` 的空白台账仍被闸门拒 —— 那既可能是旧产物也可能是烧丢了。自测 `t_no_badge_is_publishable_but_demands_declaration` 锁三档表、两个方向的旗标覆盖、三旗标两两互斥、以及判据表本身；真产物凭据（三次渲染 + 四种闸门调用 + `ffprobe` + 像素复测）见 `routes/news/evidence/2026-09-29-aigc-no-badge-rail-D14-verification-lite.md` |

---

## 6. 运行时目录约定

所有产物写 `.harness-news-runtime/` (被 `.gitignore` 忽略, 不被 bootstrap 冒烟删):

```
.harness-news-runtime/
├── hotboard/<date>.json          ← 选题线索 (Step 0a news-collect 产出)
├── curated/<date>.json           ← 候选清单 + 剔除明细 (Step 0b news-curate 产出)
├── history.jsonl                 ← 各标题累计在榜天数 (news-curate --record-history 追加)
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
   `path_b_selftest.py`(项数以脚本输出为准) + `layout_selfcheck.py <pack 目录…>`(17 条结构不变量) +
   `audit_pack_contrast.py`(色板复算, 见 D10)。新 pack 的名字必须落 `AUTO_LAYOUT_STEMS`(见 D9)。
   `layout_selfcheck.py` 的参数是**目录**（含 `compositions/*.html`），不是 pack 名：传进去而里面
   没有任何版式文件 = 用法错误，当场非零退出（旧版打印「0 个文件，0 条违规」还 exit 0，
   一次打错参数的"绿闸门"其实什么都没查 —— 假绿比红更难发现，见 D13）
7. **AIGC 标识的判据是"② + ③ 齐活", ① 由开关决定**(D14 放宽, 原口径"交付件三件齐活"):
   ② mp4 元数据**永远不许缺**，③ 发布自主声明在 ① 没烧时**永远必带**，`aigc.json` 缺失的成片先重渲；
   发之前必须过 `check_publishable.py <成片>`（退出码 1 即不许发）。不要 ① 有两条路且代价不同：
   **no-badge 档**（姿态 `render=no-badge` 或旗标 `--no-badge`）得到可发布的交付件，但闸门对这份台账
   拒绝 `declaration=undeclared` 与 `--allow-undeclared`（EXIT=1）—— 画面没标、② 过转码即失，
   ③ 是唯一活到平台侧的那一件，关 ① 换不来"什么都不用说"；**草稿轨**（`--draft` / `render=draft`）
   的产物本身就不可发布（见 D11）。① 烧着时 ③ 仍可按姿态关，但要在 `videos[].declaration` 留痕（见 D12）。
   台账按"缺什么记什么缺 / 关了什么记什么关"写：no-badge 的 `explicit` 段必须存在并写明
   `disabled_by` 真出处与 `to_enable` 回退写法，没交代的空白照样被拒。**不许**拿"跳过闸门"当日常流程。
   姿态是文件里的一行，不是代码里的默认值：当前 `routes/news/aigc-mode.json` 是
   `render=no-badge · declaration=required`，要 ① 回到画面上加 `--deliver`（或把 render 改回 full）
8. **不可渲染的包不许选**: 决策树命中只有占位壳的 pack 时, 政策/法规类改落 `news-policy`、其余改落 `news-coral`, 或先补真版式
9. **采集零付费**: 热点线索只来自 `skills/news-collect`（stdlib-only，本机可复跑）；不调用任何按次扣费的榜单/话题搜索（Beatra 6/60 credits）。缺源补免费源，不花钱

---

## 8. 当前进度 (2026-09-29)

```
$ python skills/douyin-pro/scripts/path_b_selftest.py
[selftest] 73 项 · style=news-coral
  ok    t_aigc_mode_code_defaults_are_all_on
  ok    t_aigc_mode_file_flips_defaults_and_flags_override_both_ways
  ok    t_aigc_mode_reason_names_the_true_source
  ok    t_aigc_mode_rejects_bad_values_instead_of_defaulting
  ok    t_auto_layout_stems_are_the_only_vocabulary
  ok    t_draft_badge_absent_but_subtitles_kept
      可渲染 pack (有真版式): 32/32 —— 全部 pack 均有 7 个真 composition（D15）
  ok    t_full_loadability_progress
  ok    t_layout_selfcheck_refuses_a_directory_with_no_layouts
  ok    t_no_badge_is_publishable_but_demands_declaration
  ok    t_pack_contrast_docs_match_palette_math
  ok    t_publish_gate_default_requires_declaration
  ok    t_publish_gate_refuses_draft_and_missing_sidecar
      姿态文件 D:\work\xinyue\aigc_platfrom_back\harness-factory\routes\news\aigc-mode.json: render=no-badge · declaration=required
  ok    t_repo_aigc_mode_file_is_valid_and_recorded
[selftest] 全绿 73/73

$ python skills/douyin-pro/scripts/audit_pack_contrast.py
对比度审计通过：12 个 pack 的 frame.md 色板与文档一致（0 条警告）

$ python skills/douyin-pro/scripts/layout_selfcheck.py \
    skills/douyin-pro/templates/hyperframes_path_b/news-coral \
    skills/douyin-pro/templates/hyperframes_path_b/news-policy
版式自检通过：12 个文件，0 条违规

$ python skills/douyin-pro/scripts/layout_selfcheck.py news-coral news-policy   # 参数写成包名
news-coral: 没找到版式文件
news-policy: 没找到版式文件

版式自检不过：显式传入的 2 个目录里没有任何版式文件（news-coral、news-policy）—— 参数要写含
compositions/*.html 的**目录**…只写 pack 名不算检查，也不算通过。            (旧行为: exit 0)

# —— D14 三档真产物（同一篇 5 镜稿子渲三次，Node v23.11.1；完整日志 .harness-news-runtime/tmp/d14/）
$ python skills/douyin-pro/scripts/path_b_build.py … (不加旗标 = 落姿态文件)
[path_b] [aigc] 姿态文件 …\routes\news\aigc-mode.json: render=no-badge · declaration=required
[path_b] [aigc] 渲染层开关 → no-badge(…\aigc-mode.json render=no-badge) → 交付轨(按 D14 不烧 ①): ② 元数据照写 —— 可发布, 但发布必须带 ③
[path_b] ⚠️ 未烧 ① 角标[no-badge(…)]: ② 元数据照写并读回 —— 这份**可发布**, 代价是发布必须带 ③ 自主声明(check_publishable.py 会拒绝 undeclared)
[path_b]   AIGC 隐式标识已核验: ProduceID=97c20ceba5b61b72ae7ed5a4d7fd415a Label=1 ContentProducer=harness-news-pathb

$ python skills/douyin-pro/scripts/path_b_build.py … --deliver
[path_b] [aigc] 渲染层开关 → full(旗标 --deliver) → 交付轨: 烧 ① 角标 + 写 ② 元数据
$ python skills/douyin-pro/scripts/path_b_build.py … --draft
[path_b] [aigc] 渲染层开关 → draft(旗标 --draft) → 草稿轨: ①② 都不做, 这份产物不可发布
[path_b] ⚠️ 草稿模式[draft(旗标 --draft)]: 角标没烧、元数据没写 —— 台账会标成草稿, 发布那一步(check_publishable.py)读到即拒绝

$ ffprobe -v error -show_entries format_tags -of default=noprint_wrappers=1 <no-badge>/final.mp4 | grep -i aigc
TAG:AIGC={"AIGC":{"Label":"1","ContentProducer":"harness-news-pathb","ProduceID":"97c20ceba5b61b72ae7ed5a4d7fd415a",…}}
$ ffprobe … <draft>/final.mp4 | grep -ci aigc
0                                                   # 草稿连 ② 都没有 = 缺什么记什么缺

$ python skills/douyin-pro/scripts/check_publishable.py <no-badge>/final.mp4          # EXIT=0
✅ 可发布(按 D14: ② 在、① 点名关掉): final.mp4
   ① 未烧 —— 出处 no-badge(…\routes\news\aigc-mode.json render=no-badge) · 开回来: 把 …render 改回 full(或渲染时加 --deliver)再重渲一次, 让 ① 落进成片
   ② 元数据键 AIGC · Label=1
③ 必须带: --declaration 内容由AI生成   (开关取值: required(…\aigc-mode.json declaration=required))
$ python skills/douyin-pro/scripts/check_publishable.py <no-badge>/final.mp4 --allow-undeclared   # EXIT=1 ← D14 的代价
❌ 这份 final.mp4 不许不带 ③ —— ① 没烧(出处: no-badge(…render=no-badge)), 而 ② 过抖音转码即失, ③ 是唯一活到平台侧的那一件。开关取值 undeclared(旗标 --allow-undeclared) 在这一档不适用。
   三选一: 加 --require-declaration 重跑本闸门并按打印的命令带 --declaration 内容由AI生成; 或把 routes/news/aigc-mode.json 的 declaration 改回 required; 或用 --deliver 重渲让 ① 回到画面上。
$ python skills/douyin-pro/scripts/check_publishable.py <deliver>/final.mp4           # EXIT=0
✅ ①② 齐活: final.mp4
   ① 角标 AI 生成合成内容 · bottom-left · 字芯 54.7px / 最短边 1080px · 4.0s
$ python skills/douyin-pro/scripts/check_publishable.py <draft>/final.mp4              # EXIT=1
❌ 拒绝发布 final.mp4:
   · 草稿渲染[draft(旗标 --draft)]: ① 画面角标与 ② 隐式元数据都没有 —— 不得发布: 去掉 --draft 重渲一次, 让 ①② 落进成片

$ python skills/douyin-pro/scripts/verify_aigc_badge.py --work <deliver>/work --video <deliver>/final.mp4   # EXIT=0
[aigc_badge] ✓ 三项全过: 字芯 55px(5.09% ≥ 5%) · 墨迹与模型逐侧 ≤1.5px · 角标只在开场 4.0s 出现
$ python skills/douyin-pro/scripts/verify_aigc_badge.py --work <no-badge>/work --video <no-badge>/final.mp4  # EXIT=1 ← 复测器只认 full 档, 这里红是对的
[aigc_badge] 成片 ASS 里没有 AIGC 事件 —— 显式标识根本没烧, 不必再量像素
```

集成状态：
- ✅ 12 pack frame.md (token 面) + host.html
- ✅ **色板复算闸门** `audit_pack_contrast.py`（D10）：11 个包 42 处手抄假数全部订正为算术值，含 `news-blast` 那条会播出 1.18:1 巨号红字的设计错误（改判为 white 数字 + score 下划条形状）。基线 42 与负例 EXIT=1 的复现命令见 `routes/news/evidence/2026-09-29-contrast-audit-and-stem-gate-verification-lite.md`
- ✅ `AUTO_LAYOUT_STEMS` 上闸（D9）：词表从 `choose_layout` 的散装字面量收成单一常量，并锁定"点名表 = 词表 / 可渲染 pack ⊆ 词表"
- ✅ 验证记录的留存口径写进 §6（契约证据进 `scripts/` 受版本管理，文档不再指向 gitignore 路径）
- ✅ AIGC 标识落地：画面角标（**左下角、MarginV 303、字芯实测 55px = 最短边 1080 的 5.09%、
  开场 4.0s**）+ mp4 元数据 `AIGC`（GB 45438-2025 附录 E）+ `aigc.json` 侧车 + 读回核验（读不回即拒绝交付）。
  像素判据由 `verify_aigc_badge.py` 复现：实测含描边阴影墨迹 y **1549–1615** vs 模型
  `ink_bounds(mv=303)` **1549.3–1615.0**（上侧差 0.3px、下侧 0.0px）；距左 49px = 4.54cqw、
  距底 310px = 16.15cqh（仍在底部 20cqh 带内，视觉上就是左下角）；窗口内差异占比 76.6%、窗口外 **0.0%**。
  植入假字号（FontSize 75→60）的负例报 3 条违规并 EXIT=1。命令与完整输出：
  `routes/news/evidence/2026-09-29-aigc-badge-bottom-left-floor-verification-lite.md`
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
  `routes/news/evidence/2026-09-29-aigc-switch-draft-rail-and-publish-gate-verification-lite.md`

- ✅ **两开关的"现在想关"落进姿态文件**（D12，2026-09-29 用户「先帮我把两开关先关了吧」）：
  `skills/douyin-pro/scripts/aigc_mode.py` 单点裁决 **旗标 > `routes/news/aigc-mode.json` > 代码默认**，
  渲染与发布两个脚本共用；反向旗标 `--deliver` / `--require-declaration` 让单次动作照样能全开，
  值拼错（`render: off`）与 JSON 坏了一律 `ModeError` 停机、**不回退默认**。仓库当时的姿态
  `render=draft · declaration=undeclared`（带 `since` / `by` / `revert` 三段，由
  `t_repo_aigc_mode_file_is_valid_and_recorded` 上闸；**同日由 D14 改成 `no-badge · required`**，
  下面那段逐项量的结论是当时那份 draft 姿态的凭据，仍然成立），代价在真实渲染件上逐项量过：默认那一次
  落地就是草稿（台账 `switch` 写的出处是姿态文件路径、`ffprobe` 无 `AIGC` 键、
  `verify_aigc_badge.py` 报"ASS 里没有 AIGC 事件" EXIT=1），加 `--deliver` 那一次角标三项全过
  （字芯 55px = 5.09%）、`Label=1` 读回；闸门对草稿 EXIT=1 拒发、对交付件 EXIT=0 但按姿态打
  ③ 警告，`--allow-undeclared` 与 `--require-declaration` 同时给 = 矛盾停机。记录见
  `routes/news/evidence/2026-09-29-aigc-posture-file-verification-lite.md`
  ⚠️ **订正（同日 D14）**：这条警告「默认渲染不可发布、要交付必须显式 `--deliver`」随 draft 姿态一起失效 ——
  现在默认落 `no-badge`，**默认渲出来的就是可发布交付件**；`--deliver` 的作用变成"把 ① 烧回画面上"
- ✅ **版式闸门不再空过**（D13，同一轮文档订正时撞到）：`layout_selfcheck.py` 收到一个不含
  `compositions/*.html` 的显式目录（典型写法错误：只传 pack 名）从前的收尾是「0 个文件，0 条违规」
  **exit 0**；现在点名该目录并 exit 1，`--quiet` 一样拦。自测新增
  `t_layout_selfcheck_refuses_a_directory_with_no_layouts`（**双向**锁：真目录必须 0、pack 名与不存在目录
  必须 1，`--quiet` 也要拦）；上面 §8 那一对命令就是凭据（一条绿一条红，都是真输出）。
  项数只在 §8 那次真转录里出现，别处不抄（加断言必然让抄进文档的数过期）
- ✅ **判据放宽落地：渲染层加中间档 `no-badge`**（D14，2026-09-29 用户对「删掉烧角标那段」改选
  「判据放宽：交付件可以不带 ①」）：`RENDER_MODES` 从两档变三档、旗标 `--no-badge` 与
  `--deliver` / `--draft` 两两互斥，② 元数据照写并读回，产物**可发布**；代价由闸门结算 ——
  这类台账遇 `declaration=undeclared` 或 `--allow-undeclared` 一律 **EXIT=1** 并打三条出路（不静默改
  用户姿态）。同一轮的四种闸门调用 + 三次真渲染 + `ffprobe` 对比 + 像素复测都在 §8 那段真转录里，
  完整记录见 `routes/news/evidence/2026-09-29-aigc-no-badge-rail-D14-verification-lite.md`。
  ⚠️ **仓库姿态因此从 `draft · undeclared` 改为 `no-badge · required`**：① 关掉的直接后果是 ③
  不能再关 —— 用户先前关的第二个开关在这一档被判据重新打开，这是其所选方案的既有条件，
  一行可回：把 `aigc-mode.json` 的 `render` 改回 `full`（或渲染加 `--deliver`），③ 的开关即恢复可用
- ✅ 发布链路：`--declaration 内容由AI生成` 已对齐上游源码，成功凭据写进 skill
- ✅ 占位包改为**加载期停机**（不再拖到渲染第 1 镜；能力保留，构造空壳包即可验）
- ✅ **32/32 pack 全部有真版式**（2026-10-08 实测，D15）—— 旧记录里的「2/12」「⏳ 10 pack 待补」
  是**陈旧数据**，已作废；真数据见 §4「当前状态」
- ✅ 20 个派生变体补 `frame.md` + 派生声明（D16）；色板审计覆盖面 12 → 32 个包
- ✅ 561 条 OFF_PALETTE 收敛到 24 条（D18 共享 token 层 + D19 按 CSS 角色替换残留）
- ✅ `news-policy` 5 个真版式落地（占位壳已删），五镜探针过 `--check-only` 门禁（记录见 `routes/news/evidence/2026-09-29-news-policy-layouts-verification-lite.md`）
- ⏳ 24 条刻意保留的色板外用色 —— 该补进各包 frame.md 算设计补全，不是改色（D19）
- ⏳ 20 变体的调色板对比度表未生成（`gen_variant_frames.py` 只写 §1 色板，不写 §2.1 对比度表）
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
