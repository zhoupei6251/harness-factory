# harness-factory v2.1 设计（原地重建）

- 日期：2026-09-11
- 状态：**设计完成，待实施**（未开始写实现）
- 前身：harness-foundry（退役）/ harness-kit（退役）/ harness-factory v1（原地推翻）/ **v2 设计文档**（`../../docs/plans/2026-09-11-harness-factory-v2-design.md`，已标 superseded）
- v2.1 = v2 全部结构决策 **+ 10 处修订**（8 处因新查证的事实，2 处因用户决定）。v2 的 §10「已否决方案」**全量继承**，不重开。

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
| 10 | 无 agent 层（v2 §4 的 engine/ 里没有 `agents/`） | **两层组织模型**：CEO = 用户、director = 主线程 agent、职员 = 三个 subagent（§8.1 §8.2） | 查证：subagent 一律拿不到 `AskUserQuestion` → 持门禁权者不能是 subagent；`Agent(type)` 白名单仅对主线程 agent 生效；嵌套默认三层 |

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

## 4. 中央仓三层

完整文件级目录见 **§5.1**（此处不再重复一份树——设计文档自身也不许有两份同一事实）。

| 层 | 目录 | 身份 | 改它的规则 |
|---|---|---|---|
| 规则源 | `engine/` | 编译唯一输入，全 markdown，AI 读的正文 | 只在「改进对所有项目都好」时改，改完 push |
| 正文库 | `.agents/skills/` | 按需加载的技能，Trae/Codex 直读 | 同上；且必须被 ≥1 条 route 引用（§11） |
| 机制 | `compiler/` | TS；**唯一允许存在平台差异的地方** | 加机制时改，规则变动不应惊动它 |
| 私有数据 | `.workspaces/` | gitignored 运行时状态，等同 `.git/` | 每项目各管各的，永不出仓 |

`engine` 与 `skills` 的区别是**目录级身份**——前者编译进一页纸，后者只被索引——不是仓库级。
单仓，不分第二仓（v2 §10 已否决，继承）。

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
├── engine/                          [T] 全 markdown；一页纸输入源 ≤225 行（§11）
│   ├── START.md                     一页纸母版：R1–R8（R7=记忆边界令）+ 收尾自检 + agent 索引  70 ✓
│   ├── gates.md                     S/M/L 唯一定义 + 三个 4 行可抽取块              60 ✓
│   ├── routes/code.md               四件套（§8）                                      ≤60
│   ├── routes/novel.md                                                                     ≤60
│   ├── routes/news.md                                                                      ≤60
│   ├── agents/director.md             主线程编排者：有 Agent 无写权限（§8.2）           ≤15
│   ├── agents/explorer.md implementer.md reviewer.md  角色+禁用工具，各 ≤15（§8.1）
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

引擎侧 tracked 文件总量目标：**engine 21 + compiler ~20 + skills ≤100 + tests ~8 + 根 6 ≈ 155**，对照 v1 的 316（其中 skills 占 316 里的绝大多数）。
（engine 21 = START 1 + gates 1 + routes 3 + agents 4 + contracts 4 + runbooks 4 + platforms 4）

### 5.2 全貌：业务项目侧（`aigc_platfrom_back/`）

**全部经 `.git/info/exclude` 隐藏，业务仓 0 个 tracked 文件因 harness 而新增**；唯一一处 tracked 改动是 `CLAUDE.md` 的 harness 节改引产物。

```
aigc_platfrom_back/
├── harness-factory/            [excluded]  引擎。当前是 untracked(??)，Step 1 起进 exclude
├── AGENTS.md                   [excluded]  渲染产物，Codex/Trae 读
├── CLAUDE.md                   [tracked]   改 3 行：harness 节 → @.claude/rules/HARNESS.md
├── .claude/rules/HARNESS.md    [excluded]  渲染产物
├── .claude/skills/             [excluded]  sync-skills 拷贝
├── .claude/agents/             [excluded]  explorer/implementer/reviewer 三份 subagent + director 一份主线程角色（§8.1 §8.2），格式由 compiler 生成
├── .claude/commands/           [excluded]  Step 3：/harness-status、/harness-mode（§10.1）
├── .claude/settings.json       [半产物]    只追加 harness 的 hooks 段
├── .codex/hooks.json           [excluded]  渲染产物
├── .codebuddy/                 [excluded]  rules + skills + settings
└── (harness-foundry/ harness-kit/ 已删；.claude/HARNESS-RULES.md 删)
```

novel / news 目录同构，只是通常非 git 仓 → 无 `info/exclude` 可用，产物裸放在目录里（本就不提交）。

### 5.3 v1 → v2 退役映射

| v1 | 文件数 | 归宿 |
|---|---|---|
| `core/`（含 specs/、orchestration/、traps.md） | 34 | → `engine/{START,gates,routes,contracts,runbooks}`。**砍 specs/ 与 orchestration/ 两个独立层**：orchestration 收薄为 `runbooks/multi-task.md`（v1 的 dispatcher-workflow 183 行是「入口链过长」的主要成因）。其中七份角色定义按 §8.2 归位：**leader → director**（换层：从 subagent 改为主线程角色）；**coder + implementer → implementer**（两份合一，v1 的重复即角色膨胀实证）；**reviewer 留**；**debugger / test-engineer → 技能**（`systematic-debugging` / `tdd` 已在候选池，二者无独立权限形状）；**web-investigator → explorer**（同一能力，只是范围大）；specs/ 的尾盘/worktree 并入 contracts |
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

START.md 母版骨架（**行数一律以 `wc -l` 为准**，`lint.ts` 亦按此执法；渲染产物构成如下）：

| 段 | 行数 | 来源 |
|---|---|---|
| 生成头（DO NOT EDIT + engine 路径@commit + workspace + 改源指引） | 4 | render |
| 身份 + 门禁声明（工作区 / 路线 / 档 / 开工第一句格式） | 4 | `config.md` + `gates.md` |
| R1–R8 行为规则（R7 即记忆边界令，不再单列） | 10 | `engine/START.md` |
| 本档要求 4 行块（动笔前/干活中/交付时/证据形态） | 4 | `gates.md` 的 `<!-- gate:X -->` 块 |
| **本路线管线不变量**（不随档升降） | ≤6 | `engine/routes/<line>.md` |
| 项目事实摘要 | ≤10 | `.workspaces/<proj>/facts/profile.md` |
| 技能索引（名称 + 一行触发词，≤15 条） | ≤15 | route 档案 skills 段 |
| 收尾自检 | 4 | `engine/START.md` |
| 可用 agent 两行（名单 + CEO/director 分层；细节仅 L 档展开，§8.1 §8.2） | 2 | `engine/agents/` |
| 段落标题与空行（9 段 × 2） | 18 | render |
| **合计** | **≈77 / ≤120** | 余量 43 行 |

预算成立的两个前提，写进 `lint.ts`：`gates.md` 每个 `<!-- gate:X -->` 块**恰好 4 行**（已实测 4/4/4），
`routes/<line>.md` 的 pipeline 段 ≤6 行、skills 段 ≤15 条。超了不是渲染截断，是 CI 红。

## 7. 门禁三档

> 权威正文是 **`engine/gates.md`**；本节只记为什么这么定，实施时以引擎文件为准。

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

### 8.1 agent 不是技能

| | 技能（`.agents/skills/`） | agent（`engine/agents/`） |
|---|---|---|
| 是什么 | **怎么用**某能力的正文 | **由谁来跑**的执行者定义 |
| 上下文 | 加载进当前上下文，同一个人格继续 | 独立上下文窗口、受限工具集、可换模型 |
| 是否跨工具收敛 | **是**（agentskills.io），一份四家吃 | **否**，各家格式互不相认 |
| 因此身份 | 源（canonical，直接共享） | **编译产物**（canonical 是薄的角色描述，四份格式由 `compiler/platforms/*.ts` 生成，§2b 的第二个实例） |

判据：**agent 存在的唯一理由是权限隔离。** 只换提示词不收紧工具集的 agent = 一段没必要的独立上下文，应该写成技能。`subagent-driven-development`、`dispatching-parallel-agents` 留在 `shared/` 技能里——它们是「怎么用 agent」，本身不是 agent。

「权限隔离」隔离的是**能力**，不是**话题**。这条判据顺带否掉「一件事一个 agent」的写法：v1 的 `core/orchestration/agents/` 有七份角色文件共 838 行（leader / coder / implementer / reviewer / debugger / test-engineer / web-investigator），其中 `coder.md`(205) 与 `implementer.md`(121) 是同一件事的两份定义——**角色膨胀在 v1 已经漂移过一次**。v2.1 按能力划，只留三个「职员」agent，每个以「禁止什么」定义：

| agent | 工具集 | 为何不能降级成技能 |
|---|---|---|
| `explorer` | 只读（Read/Grep/Glob），**禁写** | 摸底阶段烧掉主上下文；且它物理上写不了，不必靠 R2 自律 |
| `implementer` | 可写 + 必跑验证 | 执行与编排分离：plan 交下去，回来的只有 diff 与证据 |
| `reviewer` | 只读，**物理禁写** | 挑刺的人改不了代码才是真 reviewer——这是机制，提示词给不了 |

canonical 定义放 `engine/agents/`（不放 `.agents/agents/`：那是凭空发明规范里没有的子目录，且 `.agents/` 这个名字已足够让人误以为它装 agent）。每份 ≤15 行。一页纸的 agent 段共两行——一行名单（四个）、一行分层（§8.2），细节仅 L 档从 `runbooks/multi-task.md` 展开，预算实测 ≈77/≤120（§6）。

### 8.2 组织分层：CEO 不是 agent，director 是，职员是

「CEO / leader / 职员」是**委派拓扑**（谁 spawn 谁、谁向谁汇报、谁拥有哪个文件）；上面三个是**职能**（对文件能做什么）。两根正交的轴，不能混成一张名单。展开成两层结构，每层由一条**已查证的机制事实**定位：

| 层 | 是谁 | 为什么在这一层 |
|---|---|---|
| **CEO** | **用户本人** | v1 `leader.md` 写的职责是「对甲方汇报」——甲方不是 agent。拍板权不可下放，因为下面两条 |
| **director** | `engine/agents/director.md` → 渲染成**主线程 agent**（Claude：`--agent` / `agent` 设置），**不是**被 spawn 的 subagent | ① 它要问用户要确认，而 **`AskUserQuestion` 对所有 subagent 一律移除，无论 `tools` 怎么写**（官方原文），所以持有门禁权的角色不可能做成 subagent；② 只有主线程 agent 才支持 `tools: Agent(director, explorer, implementer, reviewer)` 白名单语法（官方：subagent 定义里的类型列表被忽略）；③ 权限隔离成立且唯一：**它有 `Agent`，没有 `Write`/`Edit`** |
| **职员** | `explorer` / `implementer` / `reviewer`（§8.1） | 各自隔离一种能力：禁写 / 必跑验证 / 物理禁写 |

**director 的价值不是「多一个人格」，是把 v1 的一句自律变成物理约束**：v1 `dispatcher-workflow.md` 写「**禁止** Leader 在主线程直接修改业务代码」——靠提示词守；v2.1 给 director 的工具集里没有 `Write`/`Edit`，它想顺手改也改不了。这正是 §8.1 判据要的样子，也是它不违反 §17「第四个 agent」那条否决的理由：那条否的是**第四种职能**（tester/planner），而 director 是**另一种权限形状**。

**为什么不做成三层组织图（CEO+leader+staff 都是 agent）**——三条已查证的代价：

1. 子 agent 只回一段摘要（原文：*Only the top-level subagent's summary returns to you*）。多套一层 = 主会话离证据远一层，而 R3「没有证据不得声称完成」要求主会话能贴出原始输出。**层级每深一层，证据的保真度掉一次。**
2. 官方明确列出不该委派的场景：「任务需要频繁来回」「多阶段共享上下文——planning、implementation、testing」。L 档批次恰好两者都是。
3. 委派链上每个环节都问不了用户，于是 spec/plan 的「等确认」要经两段传话回到用户面前。**门禁的确认通道会变长且不可靠。**

**降级与方言**：`--agent` 主线程切换是 Claude Code 的机制。Codex / Trae / WorkBuddy 是否有等价物 = §18 待验。按下界设计：**没有主线程 agent 切换的平台不渲染 director**，其规矩退化为 `runbooks/multi-task.md` 的文本纪律（能派发就派发，不能就顺序执行），结构不变（§2b）。director 是**第四个 agent，也是最后一个**：再加先回答「它隔离了哪种能力」。

两条落地细节，避免实现时踩歧义：

- **同一个目录，不同的调用路径**。`director.md` 与三个职员一起渲染进 `.claude/agents/`——差别不在文件位置，在于它由 `--agent director` / `agent` 设置**选为主线程角色**，而不是被 `Agent` 工具 spawn。渲染器要在文件头注释里写明这一点，否则下一个读引擎的人会以为漏配了 spawn 关系。
- **director 身份只在 L 档生效**。S/M 档主会话就是干活的人（S 档定义即「直接改」）。所以这条规矩写在 `gates.md` 的 L 块「干活中」行里（该行同时写明**不亲自改业务文件**），不写进 R1–R8——写进 R 表等于要求 S 档也先派发再改一个错别字。

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

### 10.1 从 ponytail 借的两件（它没有组织图，但有两件我们没有的机制）

ponytail 是「模式 + hook + benchmark」型 harness，**grep 全文无 CEO/leader/staff 概念**（`ceo|orchestrat|dispatcher|leader|crew|worker|staff` 只命中 4 个非角色文件），所以 §8.2 的组织模型不来自它。可借的是它的机制形状：

1. **档位声明要可观测，不靠自律**（借它 `hooks/ponytail-mode-tracker.js` + statusline 的形状）。现状：`开工第一句必须声明 Harness: X` 是一句提示词，没有东西在检查。改法：`UserPromptSubmit`（三家共有）扫首轮是否出现声明 → 未出现则 `additionalContext` 补一句「未声明档」并记入 `state.json`；statusline 显示当前档。**门禁的第一道执法从「AI 自觉」变成「有人看着」**——与 §17 里 `.bak/` 兜底是同一条原则（机制优先于规则密度）。
2. **薄 slash command 作为用户侧入口**（借它 `commands/ponytail*.toml` 逐平台一份的形状）。本设计「无命令化」否的是**用户要记 CLI**，但把「接入 harness」「切 director」留给自由文本，等于把可靠性押在 AI 认得出话术上。补一类产物：`/harness-status`（当前档 + pin + 产物是否脏）与 `/harness-mode`（切档 / 切 director），每家 ≤10 行，由 `compiler/platforms/*.ts` 生成。**排 Step 3**：Step 0/1 只验证渲染链路，不引入新的产物类别。

不借的：12 平台镜像目录（平台数是预算，§17）、A/B benchmark 台架（§17）、它的 markdown 正文风格（与本仓中文规则文风不合）。

## 11. lint 硬数字（构建闸门）

超了即失败，写进 `compiler/lint.ts`：

- 渲染产物 ≤120 行；`gates.md` 每个 `<!-- gate:X -->` 块恰好 4 行；`routes/*.md` ≤60 行（pipeline 段 ≤6、skills 段 ≤15）
- **一页纸输入源**（`START.md` + `gates.md` + 单个 `routes/<line>.md`）总量 ≤225 行 —— 实测 70 + 60 + ≤60 = ≤190
  （`contracts/` `runbooks/` `platforms/` 不计：前两者只在 L 档或人读时展开，方言每家 ≤25）
- `.agents/skills/` 技能总数 ≤100，**且每个被 ≥1 条 route 引用**（未被引用 = 失败）
- `engine/agents/*.md` 每份 ≤15 行（**共 4 份，硬上限 4**，第五份要先进 §17 讨论），且**必须显式声明被禁的工具类别**；未声明 = 失败——不声明即默认全给，agent 就退化成换皮的技能（§8.1 判据）
- `director.md` 必须同时声明「拥有 `Agent`」与「禁用 `Write`/`Edit`」两项（§8.2 的权限形状就是它存在的全部理由；缺任一项 = 失败）
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
- **Step 3 · 铺面**：novel 线（`novel/` 五文件 + 三个机检脚本 + 11 技能 + 快照）、news 线（5 技能链）、`platforms/trae.md` 与 `workbuddy.md` 定稿、写作库与新闻目录各跑一次 onboarding。**agent 层此时才扩**：① 在真平台验 `--agent` 式主线程切换有几家支持（§18），据结果决定 `director.md` 渲染给谁（§8.2）；② 加两个 slash command 与「档位声明可观测」hook（§10.1）——它们引入 `commands/` 这一新产物类别，故排在渲染链路证明之后。

## 17. 已否决方案（防未来反复）

v2 §10 全量继承，另加本设计自己的 15 条：

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
| canonical agent 放 `.agents/agents/` | 该目录受 agentskills.io 规范管辖，只定义 `skills/`；凭空发明子目录 = 假装存在一个不存在的规范 |
| 第四个**职员** agent（tester / planner / debug-engineer…） | 权限隔离是 agent 的唯一理由，三个职员已覆盖只读摸底 / 可写执行 / 只读挑刺。再加先回答「它隔离了哪种能力，为什么不写成技能」。v1 七份角色 838 行里 `coder.md` 与 `implementer.md` 重复即为此病 |
| director 做成**被 spawn 的 subagent**（三层组织图 CEO→leader→staff 全是 agent） | 三条已查证代价（§8.2）：subagent 一律拿不到 `AskUserQuestion`，问不了用户 = 守不了需要「等确认」的门禁；只回一段摘要，层级越深证据保真度越低；官方点名 planning/implementation/testing 三阶段共享上下文时不该委派 |
| ponytail 式 A/B benchmark（`--arms baseline,caveman,ponytail --models haiku --runs 4`） | 那是给「公开卖点」准备的。单人工具、无 CI、被测物每 commit 在动，跑一次的 token 成本高于它给出的信息量。改留 §15 的 golden render + 真平台手测 |
| 12 平台镜像目录（ponytail 有 `.cursor` `.qoder` `.windsurf` `.kiro` `.clinerules` `.grok` `.devin` `.opencode` `.github`…） | 每多一家 = 多一份要人维护的镜像，正是 v1 的死因。平台数是本设计的一等预算，v2.1 硬锁 4 家；第 5 家先讨论预算 |

## 18. 遗留开放问题（不阻塞 Step 0/1）

- `MEMORY.md` 与 Claude auto-memory 的读写竞态细节：先按边界令执行，跑一个批次再收。
- Codex skills 系统的实际发现路径（`.agents/skills/` 直读 or 需 `config.toml` 声明）：Step 0 在真 Codex 上验，若需声明则 `compiler/platforms/codex.ts` 加一行清单。
- Trae `Include AGENTS.md in context` 与 `.agents` 开关是**用户级 UI 开关**，无法由文件写入完成：onboarding runbook 里列为人工两步 checklist。
- 快照保留 20 份这个数是拍的：跑一段真实小说工作后按 `.bak/` 命中率调。
- **director 的平台支持面**：Codex / Trae / WorkBuddy 有无「把整个会话切成某个 agent 定义」的等价物（Claude 侧是 `--agent` / `agent` 设置）。三家全缺则 director 退化为 claude 独家方言（§8.2 已给不阻塞的下界）；若 ≥2 家有，则 `compiler/platforms/*.ts` 各加一份产物。Step 3 在真平台验。
