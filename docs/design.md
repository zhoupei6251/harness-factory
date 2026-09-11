# harness-factory v2.1 设计（原地重建）

- 日期：2026-09-11
- 状态：**设计完成，待实施**（未开始写实现）
- 前身：harness-foundry（退役）/ harness-kit（退役）/ harness-factory v1（原地推翻）/ **v2 设计文档**（`../../docs/plans/2026-09-11-harness-factory-v2-design.md`，已标 superseded）
- v2.1 = v2 全部结构决策 **+ 9 处修订**（7 处因新查证的事实，2 处因用户决定）。v2 的 §10「已否决方案」**全量继承**，不重开。

## 0. 修订记录（相对 v2）

| # | v2 原文 | v2.1 | 依据 |
|---|---|---|---|
| 1 | 新建仓库 `harness-factory-v2` | **原地重建 `harness-factory/`**，保留 135 条 commit 历史，`main` 上一个 `chore(v1): teardown` 提交删掉 251 个 md | 用户决定；v1 历史是「哪里会失败」的唯一实证 |
| 2 | hook 把 `skills/` 拷到各平台原生目录 | **`.agents/skills/` 为唯一技能仓**（agentskills.io 规范）：Trae、Codex 直读，Claude、CodeBuddy 拷贝 | Trae 官方文档有 `Enable .agents Skills Directory` 开关 |
| 3 | 「codex 无技能机制 → 一页纸仅带名称索引」 | **更正：Codex 有 skills 系统 + 12 个生命周期 hook 事件**，codex 方言因此与 claude 同构，索引降级为兜底 | openai/codex `docs/agents_md.md`、developers.openai.com/codex/hooks |
| 4 | 唯一自动入口 = `hook-session-start.ts` | **一份 hook 实现 + 四份清单**，三个入口：`session-start` / `post-tool-use` / `stop` | 三家事件词表与输出契约同源（§10 矩阵） |
| 5 | novel 状态只有 `MEMORY.md`（≤100 行） | novel 线状态**外移为 workspace 的 `novel/` 五文件事实库**，MEMORY 只留两行 | 长篇状态是上千行结构化数据，塞进 100 行预算必然失效 |
| 6 | 工具链未定 | **Node 26.8.2 + TypeScript 7.0.2，零构建、零运行时依赖**（不用 tsx / esbuild / ts-node） | 本机实测通过（§13） |
| 7 | 技能「只收 ~15 个」 | **候选池 ≤100 且每个被 ≥1 条 route 引用（lint 执法）；一页纸每路线引用 ≤15** | 调和用户「≤100 全养料」与 v2 少技能原则 |
| 8 | Trae/WorkBuddy 技能落点「Step 3 到真平台验证」 | 落点**当场定稿**；Trae hook 能力证据矛盾 → **按无 hook 下界设计** | docs.trae.ai/ide/skills 给出 `.trae/skills/` 与 `.agents/skills/`；hook 证据冲突（§10） |
| 9 | 分发 = 每项目 `git clone` 到 `harness/`，项目数据住项目根 `.harness/` | **引擎单实例（就住本仓，无 clone）+ 数据集中在 `harness-factory/.workspaces/<proj>/`（gitignored）+ 产物分散渲染到各项目根（全忽略）** | 用户决定；且「每项目 clone」是给不存在的共享需求设计的 |

## 1. 目标与定位

让 **Claude / Codex / Trae / WorkBuddy** 四个平台，在 **代码 / 长篇小说 / 新闻** 三条线上按同一套流程纪律工作。

v1 的五个死因作为反面约束：入口链过长；同一规则多处重复；引擎与资产混住；分发模型悬而未决；项目实例住在共享仓内导致副本就地分化。

**定位补充**：这套东西是**个人工具，不是团队产物**。不做共享、不做「同事开箱可用」；要用的人自己 clone 到自己机器，他的 `.workspaces/` 是他的。所有跨项目可见性因此出局。

## 2. 世界观

**engine 是程序，workspace 是数据，平台文件是编译产物。**

程序无状态、不许含项目事实；数据跟着工作区走；产物由编译器生成、不许手改。

三条不变量：

- **(a) 内容放在别的工具已经会主动去找的位置。** 不做「canonical + 投影 stub」（v1 之死因），而用两个跨工具收敛规范：规则用根 `AGENTS.md`，技能用 `.agents/skills/`。
- **(b) 平台差异只允许出现在 `compiler/platforms/*.ts`。** 全仓不允许存在第二份 markdown 副本。
- **(c) 共享内容一份，私有数据集中。** `.workspaces/` 是被 git 排除的运行时状态，与仓库的关系等同 `.git/`——它不是 v1 的「共享内容就地分化」（那是 18 份 vendored 技能各写各的），因为它装的从来就不该是共享内容。

## 3. 分发模型：单实例 + 集中数据 + 分散产物

```
引擎    harness-factory/                      本机唯一一份；升级 = 在这里 git pull
数据    harness-factory/.workspaces/<proj>/   集中、gitignored、不建 git
产物    <每个项目根>/AGENTS.md 等              分散（下条墙所致）、全走 .git/info/exclude
```

- **无 clone-per-project**。v2 的「每项目 clone 到 `harness/`」是给团队/多机分发写的，本场景只有 1–3 个 workspace，那份膨胀与 N 次 pull 都不必存在。
- **一条挪不动的墙**：平台从各自项目树向上发现文件（Codex/Trae 找项目根 `AGENTS.md`，Claude 找项目根 `CLAUDE.md` + `.claude/`），所以**产物必须落在每个项目根**，不可集中存放。数据集中、产物分散是这个模型唯一 unavoidable 的两段式。
- **产物一律不提交**：写进项目的 `.git/info/exclude`（100% 本地，连一行 tracked 的 `.gitignore` 改动都不留，业务仓零污染）。产物是纯派生物，源在 `.workspaces/`。
- **引擎定位**：产物头部写死 engine 绝对路径 + 渲染所用 commit。hook 从项目内读自己根下的产物即拿到一切，无需任何全局注册表。
- **版本错开靠 pin，不靠多份 clone**：pin = `.workspaces/<proj>/state.json` 记录的「渲染时引擎 commit」。语义是随**编译产物**进入项目的，引擎只是编译器——小说写到第 40 章时不重渲染，该项目的 `AGENTS.md` 就还停在旧 commit 的语义上。SessionStart 只提示「停在 X，要不要跟」，**绝不自动跟**。
- **数据不建 git，靠快照兜底**：PostToolUse hook 在写 `.workspaces/<proj>/**` 任何事实文件前，把旧版复制到 `.workspaces/<proj>/.bak/<名>.<时间戳>`，只留最近 20 份。伏笔表被覆盖不再不可恢复，且用户不需要记得提交任何东西。

## 4. 中央仓结构

```
harness-factory/
├── README.md                  给人：三层模型 + 5 分钟上手
├── .agents/skills/            ★ 技能唯一仓（Agent Skills 规范），Trae/Codex 直读
│   ├── code/  novel/  news/  shared/
├── engine/                    ── 编译唯一输入，全 markdown，AI 读的规则源 ──
│   ├── START.md               一页纸母版 ≤120 行：R1–R8 + 门禁声明格式 + 记忆边界令
│   ├── gates.md               S/M/L 唯一定义：各档产物、声明、升降档规则
│   ├── routes/{code,novel,news}.md   路线档案 ≤60 行/个（四件套，见 §8）
│   ├── contracts/             L 档才展开：spec.md / plan.md / verification.md / closeout.md
│   ├── runbooks/              onboarding.md / update.md / multi-task.md / maintenance.md
│   └── platforms/             claude.md / codex.md / trae.md / workbuddy.md（平台方言）
├── compiler/                  ── TS，实现细节，不供人读 ──
│   ├── render.ts              纯函数：engine + route + 方言 + workspace 事实 → 产物
│   ├── sync-skills.ts         .agents/skills/ → claude/codebuddy 技能目录（幂等拷贝）
│   ├── lint.ts                CI 闸门（硬数字见 §11）
│   ├── hx.ts                  逃生口（npm run harness）：onboard / render / audit
│   ├── platforms/*.ts         四份薄清单生成器，每家 ~40 行，唯一的差异存放处
│   ├── hooks/                 session-start.ts / post-tool-use.ts / stop.ts（§10）
│   └── verify/                code/ + novel/ 确定性校验（零依赖，不调 LLM）
├── .workspaces/               [本仓 .gitignore] 每项目私有数据，见 §5
├── tests/                     golden render / lint 自测 / hook 契约 / sync 幂等 smoke
└── docs/design.md             本文档
```

`engine`（给 AI 读的规则）与 `skills`（按需加载的正文）的区别是**目录级身份**——前者编译进一页纸，后者只被索引——不是仓库级。单仓，不分第二仓（v2 §10 已否决，继承）。

## 5. workspace 侧目录

```
harness-factory/.workspaces/<proj>/     [数据源，gitignored]
├── config.md            ★ 唯一常手写：项目根绝对路径、路线、启用平台、门禁档覆盖
├── MEMORY.md            工作状态记忆 ≤100 行（novel 见 §9）
├── state.json           机器管：渲染所用引擎 commit、产物清单+hash、last_error
├── facts/profile.md     项目事实卡：技术栈、模块边界、验证命令
├── novel/               novel 线状态库（§9）
└── .bak/                hook 快照，最近 20 份

<项目根>/                                [产物，全进 .git/info/exclude]
├── AGENTS.md                            Codex/Trae 原生零转换
├── .claude/rules/HARNESS.md             claude 一页纸（项目 CLAUDE.md 用一行 @ 引它）
├── .codebuddy/rules/HARNESS/RULE.mdc    workbuddy
├── .claude/skills/  .codebuddy/skills/  sync-skills 拷贝
└── .claude/settings.json  .codex/hooks.json  .codebuddy/settings.json
                             [半产物] harness 只维护自己的 hooks 段，merge 不覆盖别人的
```

`<proj>` 目录名 = 项目根 `basename`。项目搬家 = 改 `config.md` 里的路径 + 重渲染，`.workspaces/` 下的目录名可 `git mv` 式手改（本仓不跟踪它）。

### 5.1 全貌：引擎侧

Step 3 结束时的完整形态。`[T]` = 本仓 tracked，`[I]` = gitignored：

```
harness-factory/
├── README.md                        [T] ≤80 行   三层模型 + 5 分钟上手 + 否决清单指路
├── package.json tsconfig.json       [T]          §13；无构建步骤
├── .gitignore                       [T]          新增 .workspaces/
├── .agents/skills/                  [T] ≤100 个技能目录，每个 SKILL.md ≤150 行
│   ├── shared/    verification-before-completion systematic-debugging brainstorming
│   │              writing-plans executing-plans code-review requesting-code-review
│   │              receiving-code-review subagent-driven-development dispatching-parallel-agents
│   │              using-git-worktrees finishing-a-development-branch doc-review humanizer-zh
│   ├── code/      tdd domain-modeling codebase-design prototype diagnosing-bugs
│   │              resolving-merge-conflicts improve-codebase-architecture lang-java lang-ts
│   ├── novel/     writing-novel novel-protocol novel-36-beats novel-contexts
│   │              novel-foreshadowing-dag novel-voice-profile novel-guardian novel-evaluator
│   │              novel-mechanical-scorer novel-simplify novel-safe-revision
│   └── news/      news-generator news-polish fact-check
├── engine/                          [T] 全 markdown，正文总量 ≤400 行
│   ├── START.md                     一页纸母版：R1–R8 + 记忆边界令 + 证据总则      ≤90
│   ├── gates.md                     S/M/L 定义、声明格式、升降档规则                    ≤45
│   ├── routes/code.md               四件套（§8）                                      ≤60
│   ├── routes/novel.md                                                                     ≤60
│   ├── routes/news.md                                                                      ≤60
│   ├── contracts/spec.md plan.md verification.md closeout.md   仅 L 档展开，4 × ≤40       ≤160
│   ├── runbooks/onboarding.md         人工两步 checklist（Trae UI 开关）+ 新仓接入话术      ≤35
│   ├── runbooks/update.md             pull → 报每个 workspace 的 pin 差异 → 选择性重渲染    ≤25
│   ├── runbooks/multi-task.md         WU 拆分 / 角色 / worktree（自 v1 orchestration 收薄） ≤45
│   ├── runbooks/maintenance.md        加技能/加路线/加平台三条路径                          ≤30
│   └── platforms/claude.md codex.md trae.md workbuddy.md   方言，每家 ≤25
├── compiler/                        [T] TS，唯一允许存在平台差异的地方
│   ├── hx.ts render.ts lint.ts sync-skills.ts
│   ├── platforms/{claude,codex,trae,workbuddy}.ts   清单生成器，每家 ~40 行
│   ├── hooks/{session-start,post-tool-use,stop}.ts  + 共享 decision 模块
│   └── verify/code/*.ts  verify/novel/{check-index,check-continuity,check-voice}.ts
├── tests/                           [T] §15 六层，fixtures 住 tests/fixtures/
├── docs/design.md                   [T] 本文档（唯一设计事实源）
└── .workspaces/                     [I] 私有数据，见 §5；本仓永不跟踪
    ├── aigc_platfrom_back/
    ├── <novel 项目>/  <news 项目>/
    └── 各自 .bak/
```

引擎侧 tracked 文件总量目标：**engine 14 + compiler ~20 + skills ≤100 + tests ~8 + 根 6 ≈ 148**，对照 v1 的 316（其中 skills 占 316 里的绝大多数）。

### 5.2 全貌：业务项目侧（`aigc_platfrom_back/`）

**全部经 `.git/info/exclude` 隐藏，业务仓 0 个 tracked 文件因 harness 而新增**；唯一一处 tracked 改动是 `CLAUDE.md` 的 harness 节改引产物。

```
aigc_platfrom_back/
├── harness-factory/            [excluded]  引擎。当前是 untracked(??)，Step 1 起进 exclude
├── AGENTS.md                   [excluded]  渲染产物，Codex/Trae 读
├── CLAUDE.md                   [tracked]   改 3 行：harness 节 → @.claude/rules/HARNESS.md
├── .claude/rules/HARNESS.md    [excluded]  渲染产物
├── .claude/skills/             [excluded]  sync-skills 拷贝
├── .claude/settings.json       [半产物]    只追加 harness 的 hooks 段
├── .codex/hooks.json           [excluded]  渲染产物
├── .codebuddy/                 [excluded]  rules + skills + settings
└── (harness-foundry/ harness-kit/ 已删；.claude/HARNESS-RULES.md 删)
```

novel / news 目录同构，只是通常非 git 仓 → 无 `info/exclude` 可用，产物裸放在目录里（本就不提交）。

### 5.3 v1 → v2 退役映射

| v1 | 文件数 | 归宿 |
|---|---|---|
| `core/`（含 specs/、orchestration/、traps.md） | 34 | → `engine/{START,gates,routes,contracts,runbooks}`。**砍 specs/ 与 orchestration/ 两个独立层**：orchestration 收薄为 `runbooks/multi-task.md`（v1 的 dispatcher-workflow 183 行是「入口链过长」的主要成因），specs/ 的尾盘/worktree 并入 contracts |
| `routes/{code,novel,news}/MEMORY.md` | 3 | 拆成两半：**规则** → `engine/routes/<line>.md`（唯一真内容），**实例** → `.workspaces/<proj>/`。空模板从此不住共享区 |
| `skills/`（39 active + 50 archive） | 316 | → `.agents/skills/` ≤100，搬运时逐个改写为平台中立。**archive 整层删除**——git 历史就是归档，第二份副本正是 v1 的 18 份 vendored 分化之源 |
| `platforms/*/rules/ENTRY.md`（4 份占位骨架） | 4 | 拆为 `engine/platforms/*.md`（方言正文）+ `compiler/platforms/*.ts`（清单生成）。占位骨架里那句 "Trae hook support is limited" 由 §10 的真矩阵取代 |
| `capabilities/rules/{java,typescript,common}` | 12 | 语言无关的 → `engine/routes/code.md`；**语言细节 → `.agents/skills/code/lang-{java,ts}/`**。按需加载正文不配占一页纸预算 |
| `artifact-templates/` | 16 | → `engine/contracts/` 4 个。其余 12 个是 L 档产物模板且 v1 期间从未被用过 |
| `project/{profile,git,verification}.md` + templates + onboarding | 10 | → `.workspaces/<proj>/{config.md,facts/profile.md}` + `engine/runbooks/onboarding.md`。**★ v1 最大结构错误：项目实例住在共享仓内** |
| `entrypoints/` | 6 | 删。职责由 `compiler/platforms/*.ts` 生成产物承担 |
| `schemas/` | 3 | 删。v2 无 JSON schema 需求——产物是 markdown，lint 查行数与关键词即可 |
| `scripts/bootstrap.ts` 等 | 7 | → `compiler/`。**bootstrap 之死是核心**：投影 stub 的模型整体否决（§2a） |
| `mcp-config/` | 1 | 删。MCP 配置属个人机器，不属规则仓 |
| `ENTRY.md` `ARCHITECTURE.md` | 2 | ENTRY → `engine/START.md`；ARCHITECTURE 并入本文档（一份事实源） |
| `README.md` `package.json` `tsconfig.json` `.gitignore` | 4 | 原地重写/替换 |

teardown 形式：`main` 上一个 `chore(v1): teardown` 提交删掉 251 个 md，映射表在此留档，实施时按 §16 Step 2 逐目录搬运。

## 6. 一页纸启动契约

每平台产物是**自包含**一页纸，硬预算 **≤120 行**，超预算 = CI 失败。**多跳加载只允许发生在 L 档**（那时才读 `contracts/`）；S/M 全程一页纸内闭环。hop count 是一等指标，约束由最弱平台（Trae，无 hook）决定。

产物头打 `GENERATED BY harness — DO NOT EDIT` + engine 绝对路径 + 渲染 commit；harness 只拥有自己生成的文件，不吞项目自有文档。

START.md 母版骨架（实测约 70 行正文 + 生成头）：

| 段 | 行数 | 来源 |
|---|---|---|
| 身份：当前路线 / 当前档 / 项目名 | 4 | `config.md` |
| R1–R8 行为规则 | 8 | `engine/START.md` |
| 门禁声明格式（开工第一句 `Harness: S\|M\|L`） | 3 | `engine/gates.md` |
| 当前档的 动笔前 / 干活中 / 交付时 要求 | 8 | `engine/gates.md` |
| **本路线管线不变量**（不随档升降） | 6 | `engine/routes/<line>.md` |
| 项目事实摘要 | ≤10 | `facts/profile.md` |
| 技能索引（名称 + 一行触发词，≤15 条） | ≤15 | route 档案的 `skills:` |
| 记忆边界令 | 3 | `engine/START.md` |
| 证据总则一句 | 1 | `engine/START.md` |

## 7. 门禁三档

| | S · 直接做 | M · 一页方案 | L · 全阶段流程 |
|---|---|---|---|
| 动笔前 | 无 | 一段话方案，**等确认** | spec 落盘→停→plan 落盘→停 |
| 干活中 | 直接改 | 直接改 | 按 plan；多 task 走 `runbooks/multi-task.md` |
| 交付时 | 口头证据（动了什么/跑了什么/结果） | 证据追加 workspace 日志 | `closeout.md` 落盘；未落盘禁称「批次完成」 |

开工第一句声明 `Harness: S｜M｜L`。用户可显式改档；**agent 禁止悄悄降档**；升档随时。

两条定死原则：

1. **路线管线 ≠ 门禁重量**。news 的事实查证、novel 的文风一致性，任何档位不许跳过；档位只管「方案与收尾的文书重量」。因此 `engine/routes/<line>.md` 里管线与档位在文件内**物理分成两段、各有独立标题**——v1 把两者混写，导致 AI 降档时把查证一起降掉。
2. **证据总则一句全档通用：没有证据不得声称完成。** 档位决定证据形态，不决定证据有无。v1「Tier 0 直接提交零落盘」的口子在 v2 不存在。

## 8. 一条线 = 四件套

`engine/routes/<line>.md`（≤60 行）只准放四样，多一行 lint 红：

1. **默认档 + 强制升档触发** —— 进一页纸
2. **路线管线** —— 无论 S/M/L 都必须跑完，标明「不随档升降」
3. **状态契约** —— `.workspaces/<proj>/` 下必须存在哪些事实文件
4. **技能引用清单** —— 一页纸只带名称 + 一行触发，正文按需加载

**code** —— 默认 M。工作区签名 = 存在 `pom.xml` / `package.json` / `go.mod`。强制升 L：跨模块改动、多 task 派发。管线不变量：改前必读、改后必跑验证、无证据不称完成。

**news** —— 日常成稿 S；一旦「要发出去 / 投出去」强制 L。管线不变量：引语、数据、时间线逐条多源核对，`flagged` 项禁止发布。技能链：`news-generator → fact-check → news-polish → humanizer-zh → document-review`。

**novel** —— 见 §9。

## 9. novel 线（v2.1 新增细化）

**四条判断：**

**一、novel 没有 S 档。** 唯一例外：不改动叙事文本的操作（改错别字、重命名、跑统计）按 S。凡产出或改写正文，最低 M。理由：S 档定义是「动笔前无方案」，而长篇崩坏几乎都始于「没想清楚就落这一章」。

**二、状态不是备忘，是数据库。**

```
.workspaces/<proj>/novel/
├── book.md          书名·题材·目标字数·正文目录指针·本书不可违的三条硬设定   ≤40 行
├── chapters.md      章节索引表：n | 标题 | 一句话 | 字数 | 状态              机器可解析
├── characters.md    人物卡：存亡 | 弧光阶段 | 末次出场章 | 称谓与别名表
├── foreshadowing.md 伏笔表：id | 埋章 | 目标收章 | 状态 open/paid/dropped
└── voice.md         人称与时态 | 节奏样本 | 禁用套路句清单
```

正文路径由 `book.md` 声明（默认项目根 `manuscript/`），因有人按卷分目录、有人按章平铺。
`MEMORY.md` 在 novel 线下只准留两行：**当前章号 + 本章意图**，其余越界 = lint 失败。

**三、一致性归机检，文笔才归 LLM。** 死人开口、伏笔烂尾、章节缺号、字数塌陷——四类全部可确定性检查。用 LLM 审稿抓一致性是 v1 的错（贵、漏、判得不一致）。`compiler/verify/novel/`：

| 脚本 | 抓什么 |
|---|---|
| `check-index.ts` | 章节缺号、状态倒挂（未审标已发布）、字数越界 |
| `check-continuity.ts` | `status=dead` 人物在后续章出场；`目标收章 < 当前章` 且仍 `open` 的伏笔 |
| `check-voice.ts` | `voice.md` 禁用句命中；句长方差过低（机器味的可测量信号） |

零依赖纯文本，`node compiler/verify/novel/check-index.ts` 直接可跑，由 PostToolUse hook 挂在正文写入后自动执行。

**四、文风基线前置。** `voice.md` 是**写前必读**的管线不变量。事后 `humanizer-zh` 是补救——补救意味着已产出要重做的字。`humanizer-zh` 保留，但位置从「流程第五步」降为「终稿可选」。

**技能收敛：30 个 `novel-*` → 11 个。** 留 `writing-novel`（主干方法论）、`novel-protocol`（因果链）、`novel-36-beats`、`novel-contexts`、`novel-foreshadowing-dag`、`novel-voice-profile`、`novel-guardian`、`novel-evaluator`、`novel-mechanical-scorer`、`novel-simplify`、`novel-safe-revision`。
砍两类：**平台绑定的发布自动化**（`fanqie*`、`qidian-writing`、`web-novel-publishing-*`、`inkos`——把「写得好」和「传到哪」焊死且只对单站点有效）与**职责重叠**（三套 orchestrator、两套 generator、两套 batch/quick-write）。被砍技能里的站点知识不当垃圾扔，压成 `voice.md` 注释行。

## 10. Hook：一份实现 + 四份清单

**承重事实（本轮查证）：Claude / Codex / CodeBuddy 使用同一套事件词表与输出契约**（`hookSpecificOutput.additionalContext`、`decision: block`、`continue: false`、exit code 2 = 拦截）。故门禁逻辑只写一遍。

| 我们的动作 | Claude Code | Codex | WorkBuddy(CodeBuddy) | Trae |
|---|---|---|---|---|
| 会话起：引擎有新 commit→提示 + 注入上下文 | `SessionStart` matcher `startup\|resume\|compact` | 同 | 同 | **无 hook**（手动 `npm run harness`） |
| 写文件后：快照 + 跑 verify | `PostToolUse` matcher `Write\|Edit\|MultiEdit` | `PostToolUse` matcher `Write\|Edit\|apply_patch` | `PostToolUse` matcher `Write\|Edit` | 无 |
| 收尾前：无证据不许停 | `Stop` | `Stop` | `Stop` | 无 |

实现层三个入口，共享一个决策模块：`compiler/hooks/session-start.ts`、`post-tool-use.ts`、`stop.ts`。

**已知的三家差异，逐条吸收进代码：**

- Codex 的 `Stop` / `SubagentStop` **要求 stdout 为 JSON，纯文本非法**；Claude/CodeBuddy 允许纯文本 → 按 `hook_event_name` 分支输出。
- Codex `PostToolUse` 对文件编辑的 `tool_name` 实为 `apply_patch`，matcher 别名接受 `Edit`/`Write` → 清单写三个别名。
- Codex 默认 timeout 600s、`SessionEnd`/`Interrupt` 1–3s；我们自设 `SessionStart` 30s、其余 5s。
- CodeBuddy 另有 `PostToolUseFailure` / `StopFailure` 与 `type: prompt|agent|http` 四种 hook；v2.1 只用 `command`，不用 prompt-hook（它在门禁里引入 LLM 不确定性，与「机制兜底」矛盾）。
- Trae 侧走**产物自包含 + 无 hook 降级**（§6 hop 预算、§14 降级）。Trae hook 能力证据矛盾（第三方 issue 称支持同协议，社区文档称 2025-12 仍无）——不赌，按下界设计；日后证实只需把降级升级为拦截，结构不变。

## 11. lint 硬数字（构建闸门）

超了即失败，写进 `compiler/lint.ts`：

- `START.md` 渲染产物 ≤120 行；`routes/*.md` ≤60 行；`engine/` 正文总量 ≤400 行
- `.agents/skills/` 技能总数 ≤100，**且每个被 ≥1 条 route 引用**（未被引用 = 失败）
- 一页纸每路线技能引用 ≤15
- `engine/` 与 `skills/` 中出现具体项目名、绝对路径、技术栈细节 = 失败（项目事实只准住 `.workspaces/`）
- 产物可复现：重渲染 diff 必须为空
- novel 线下 `MEMORY.md` 除「当前章号 + 本章意图」外不得有额外条目

## 12. 防漂移三道防线

1. **上游只读，git 执法**：`engine/` `skills/` `compiler/` 就地改 → `git status` 脏 → hook 警告「这是共享内容，就地改会在下次 pull 时打架」。若确属改进 → 提交并 push 上游；若确属项目特化 → 挪进 `.workspaces/<proj>/`。（v1 死于共享内容就地分化，此为其结构性解法。）
2. **lint 静态执法**：§11 全部数字。
3. **pin 到 workspace**：`.workspaces/<proj>/state.json` 记渲染 commit；不重渲染 = 语义不变；SessionStart 只报不跟（§3）。

记忆边界令（写进 `START.md`）：**「状态进 MEMORY，事实进 profile，教训进平台记忆——三不许越界」**。平台原生记忆（如 Claude auto-memory）只准记「与用户的协作经验」，禁止记工作状态。

## 13. 工具链（本机实测）

```json
{ "type": "module", "engines": { "node": ">=26.8" },
  "devDependencies": { "typescript": "^7.0.2", "@types/node": "^26.5.1" } }
```

- 运行：`node compiler/render.ts`（Node 22.18+ 原生 type stripping，26.8.2 实测输出 `gate=M ok`）
- 检查：`tsc -p .`（TS 7.0.2 原生编译器，`nodenext` + `strict` + `verbatimModuleSyntax` + `erasableSyntaxOnly` 实测通过）
- **没有 tsx、没有 esbuild、没有 ts-node、没有构建步骤**。检出即运行——对 hook 尤其关键：SessionStart 不必先编译再执行，少一层就少一处咬人的东西。
- npm scripts：`"harness": "node compiler/hx.ts"`、`"check": "tsc -p . && node compiler/lint.ts"`
- 写进 `START.md` 的三条 TS 约定：只写可擦除语法（无 `enum`/`namespace`/装饰器/构造器参数属性）；`import` 必须带全 `.ts` 后缀；根 `package.json` 的 `"type": "module"` 不许删（删了 nodenext 把 `.ts` 判成 CJS，`verbatimModuleSyntax` 立即报 TS1287/TS1295）。

## 14. 错误处理与降级

**总原则：工具链坏了不能连带工作坏了。** 四家平台的会话都不该因 harness 报错而卡住。

- hook 内任何异常 → `exit 0` + 一行 `systemMessage`。永不抛出、永不阻塞。
- 探测不到 Node 或版本 < 26.8 → 静默退出，把原因写 `state.json.last_error`，下次 SessionStart 报告**一次**（不重复刷屏）。
- 产物被手改（hash 不匹配）→ 警告并**保留用户改动不覆盖**，提示「这是派生物，改源请改 `.workspaces/`」。
- `.workspaces/<proj>/` 不存在而项目根有产物 → 判定为 workspace 丢失或项目搬家：**拒绝覆盖渲染**，只报错等人确认（此为唯一不允许自动决策的分支，因为方向不明）。
- 无 hook 平台（Trae）→ 一页纸自包含 + 收尾前要求人跑 `npm run harness`；novel 机检在 `closeout` 阶段由 AI 主动执行；快照因此不存在，novel 状态改动靠 `.bak/` 之外的手动备份。
- 项目根不在 `config.md` 登记过 → hook 首行找不到 workspace 即 `exit 0`，未 onboarding 的仓完全无感。

## 15. 测试策略

| 层 | 测什么 | 断言 |
|---|---|---|
| golden render | `render.ts` 是纯函数 | 固定 engine+fixture 输入 → 产物逐字节比对快照 |
| 行数预算 | §11 硬数字 | 渲染产物 ≤120 行；route ≤60 行 |
| lint 自测 | 闸门真的会拦 | 喂故意超预算 / 带项目名的样本，断言失败 |
| hook 契约 | 四家事件语义 | 对每家清单里每个事件名喂固定 stdin JSON，断言 exit code 与 stdout 形状符合该平台规则（重点：Codex `Stop` 必须 JSON） |
| sync 幂等 | 拷贝不制造漂移 | 临时 fixture workspace 跑两次 sync，第二次 diff 必须为空 |
| 快照 | 兜底真的兜住 | 改 `foreshadowing.md` 后 `.bak/` 有旧版；写第 21 次后第 1 份已被回收 |
| verify 金样例 | novel 机检有效 | 预置「死人出场」「伏笔超期」「章节缺号」样本，断言各自命中 |

## 16. 落地路线

顺序原则：**先证引擎、后退旧账、最后铺面**。任何一步失败可停原地，旧体系被替代前始终可用。

- **Step 0 · 内核**（首周 6 个文件）：`engine/START.md`、`engine/gates.md`、`engine/routes/code.md`、`engine/platforms/codex.md`、`compiler/render.ts`、`compiler/hooks/session-start.ts`。
  **先在 Codex 上跑通而不是 Claude**——Codex 是零转换平台（根 `AGENTS.md` 原生读），能最干净地证明「一页纸 + 原生直读」成立；Claude 有插件系统兜底，反而掩盖接线缺陷。
- **Step 1 · 单项目接通**：建 `.workspaces/aigc_platfrom_back/`（config + facts + state）→ 渲染进 `aigc_platfrom_back/` 根 → 写其 `.git/info/exclude` → 两个 hook 全链路跑通（novel/news 档案先占位不启用）。同批改业务仓**唯一一处 tracked 文件**：`CLAUDE.md` harness 节改引产物，并清理 `harness-factory|foundry|kit` 旧引用与 `.claude/HARNESS-RULES.md`。
  **实测前置**：父仓当前未 ignore `harness-factory/`（`git status` 显示 `??`，0 tracked 文件），316 个文件常年挂在业务仓 status 里，一次 `git add .` 即被吞为 gitlink。Step 1 第一件事是把 `harness-factory/` 写进父仓 `.git/info/exclude`。
- **Step 2 · 旧账退役**：foundry 本地删 + GitHub archive；kit（被业务仓 tracked）走业务仓提交删除；v1 技能按 §9/§8 引用清单逐个搬运（**搬时修剪并改写为平台中立**，不原文 vendor）。
- **Step 3 · 铺面**：novel 线（`novel/` 五文件 + 三个机检脚本 + 11 技能 + 快照）、news 线（5 技能链）、`platforms/trae.md` 与 `workbuddy.md` 定稿、写作库与新闻目录各跑一次 onboarding。

## 17. 已否决方案（防未来反复）

v2 §10 全量继承，另加本轮 7 条：

| 否决项 | 理由 |
|---|---|
| 建通用 `hx` CLI 作为命令系统 | 内核是库不是命令系统。v2 反对的是「用户要记命令」，不是「不许有可执行入口」；只留 `npm run harness` / `npm run check` 两个逃生口 |
| 四家各写一份 hook 逻辑 | 事件词表已证实同源，分写 = 制造 v1 式漂移 |
| 按 Trae 可能有 hook 来设计门禁 | 证据矛盾。按下界设计，证实后只升级不重构 |
| ≤100 技能原文 vendor | 会重新长成 v1 的 316 文件。改为「候选池 ≤100 + 每个被引用 + 改写为平台中立」 |
| 用 `MEMORY.md` 装小说状态 | 上千行结构化事实塞进 100 行预算必然失效 |
| 用 LLM 审稿抓小说连续性 | 可确定性检查的东西不该交给不确定、且每次都判得不一样的东西 |
| 每项目 `git clone` 引擎到 `harness/` | 本场景 1–3 个 workspace，clone 是 1 份引擎 × N 份膨胀 + N 次 pull，且「版本隔离」这个卖点用 `state.json` 的 pin 就能拿到 |
| 机器本地项目注册表 + `--pull-all` | 为 N 次 pull 设计，而 N 次 pull 是上一条否决制造出来的问题。引擎单实例后不存在它 |
| 产物提交进项目仓（`track` 开关） | 无共享对象。要用了自己 clone、自管 workspace |
| `.workspaces/` 自己 `git init` | 用户明确「不提交」。误删风险改由 hook 的 `.bak/` 快照兜底——机制兜底优先于人守规矩 |

## 18. 遗留开放问题（不阻塞 Step 0/1）

- `MEMORY.md` 与 Claude auto-memory 的读写竞态细节：先按边界令执行，跑一个批次再收。
- Codex skills 系统的实际发现路径（`.agents/skills/` 直读 or 需 `config.toml` 声明）：Step 0 在真 Codex 上验，若需声明则 `compiler/platforms/codex.ts` 加一行清单。
- Trae `Include AGENTS.md in context` 与 `.agents` 开关是**用户级 UI 开关**，无法由文件写入完成：onboarding runbook 里列为人工两步 checklist。
- 快照保留 20 份这个数是拍的：跑一段真实小说工作后按 `.bak/` 命中率调。
