# harness-factory v3 设计（蓝图采纳）

- 日期：2026-09-11
- 状态：**设计完成，待实施**（v3 = 相对 v2.1 的全面重写，骨架已建好，正文待 Step 0）
- 前身：v2.1（保留于 `docs/archive/v2.1-design.md`），v1（已退役）
- 工作区：v3 = v2.1 的 6 层骨架 + 蓝图采纳；保留 v2.1 的好决策（§1 目标 / §3 分发 / §7 门禁 / §10 Hook / §13 工具链 / §14 降级），重写其它部分以适配蓝图

## 0. 修订记录（相对 v2.1）

| # | v2.1 原文 | v3 | 依据 |
|---|---|---|---|
| 1 | 单一 `engine/` 装全部规则 | **6 个并列目录**：core / tasks / skills / agents / workflows / templates | 用户蓝图；入口链法的六层模型更直观 |
| 2 | `engine/routes/<line>.md` ≤60 行（四件套） | **`tasks/<line>/*.md` 按任务类型分多份**，每份 ≤80 行 | 用户蓝图；不同任务类型本就该独立文档 |
| 3 | `agents/` 按权限形状切（leader + 8 职员） | **`agents/` 按话题切**（11 个角色：code-architect / code-implementer / debugger / code-reviewer / test-engineer / performance-engineer / researcher / writer / editor / fact-checker / news-editor） | 用户蓝图；按角色分配是 harness 教科书写法 |
| 4 | `compiler/platforms/*.ts` 40 行生成器 | **`platform/<name>/` 携带 skills / agents / commands 子目录** | 用户蓝图；接受 v1 315 文件镜像的漂移风险 |
| 5 | `.agents/skills/` 唯一技能仓（agentskills.io 收敛） | **`skills/` 在根**（去掉 `.agents/` 前缀） | 用户：「`.agents` 应该是不要的」 |
| 6 | 引擎仓内不放 `project/` `memory/`（v1 最大错误） | **`project/` `memory/` 在引擎仓内** | 用户蓝图；接受多 workspace 时的覆盖风险 |
| 7 | `config.md` 一份 markdown 配置 | **`config/{harness,models,platforms}.yaml` 三份 YAML** | 用户蓝图；接受 markdown + yaml 双格式 |
| 8 | `engine/gates.md` 唯一定义档位 | **`core/quality-gates.md` + `core/task-lifecycle.md`**；L 档产物落 `.harness/code/{specs,plans,verifications,retros}/`（模板住 `engine/contracts/`） | 概念保留，路径换位 |
| 9 | 一页纸源 ≤225 行（START + gates + routes） | **一页纸源 ≤240 行**（constitution + operating-principles + quality-gates + task-lifecycle + tasks/<line>/workflow） | 多文件并入 |
| 10 | `engine/agents/<name>.md` ≤15 行（薄角色描述） | **`agents/<name>.md` ≤150 行**（按话题的 agent 需要更多上下文） | 蓝图自带事实标准 |

v3 共 **10 处修订**（首版），**2 处补充修订**：

| # | v3 (旧) | v3 (新) | 依据 |
|---|---|---|---|
| 11 | 蓝图 `workflows/<route>/<scenario>.md` 与 `tasks/<route>/<task>.md` 共存 | **删除 `workflows/`，全部并入 `tasks/`**。`workflows/coding/bug-fix.md` → `tasks/coding/scenarios/bug-fix.md`，以子目录区分「单步任务」与「多步场景」 | 蓝图自己 diagram 里 tasks→skills→workflows 是单链路——两份是同一件事；用户：「有些功能作用重合的目录名可以去掉」 |
| 12 | 状态住 `harness-factory/.workspaces/<proj>/`（gitignored，引擎集中） | **状态住 `<项目根>/.harness/`（tracked in 项目仓）** | 用户：「`.workspaces` 改成 `.harness` 放到对应的项目」；且项目仓跟踪状态让 `git diff` 能看见自己记忆的演进 |
| 13 | v3 第二版：`.harness/` tracked in 项目仓 | **`.harness/` gitignored——是 AI 目录而非人类状态**。`rendered/` 子目录装引擎渲染产物；项目根有平台入口 shim（一行 @import） | 用户：「`.harness` 应该是 ai 产出的目录吧」 |
| 14 | v3 第三版：`<项目根>/.ai-runtime-artifacts/` 单独装工作产物 | **`.ai-runtime-artifacts/` 删除**——其子目录（specs/ plans/ verifications/ reviews/ retros/ tracking/ scratch/）整体并入 `.harness/`。`.harness/` 成为 AI 全部产出（持久 + 任务级）的唯一目录 | 用户：「`.ai-runtime-artifacts/` 后面我不用了，后续的一些中间产物计划我想用 `.harness/`」 |
| 15 | 蓝图原样的目录与文件粒度 | **精简**：删 `project/` `memory/` `presets/`（蓝图壳层）；`tasks/coding/` 13 → 6（删 7 个跟 skills/agents 重复）；`agents/` 11 → 7（合并 code-architect+code-implementer；删 performance-engineer；合并 writer+editor+news-editor）；`templates/` 10 → 7（删 3 个重复）；`evals/` 删 `cases/` `expected/` `scoring/` 三个评测框架壳。`.harness/reviews/` 合并到 `verifications/`；`.harness/facts/profile.md` 摊平为 `profile.md` | 用户：「harness-factory和.harness的目录还是要精简下吧」 |
| 16 | v3.5 缺 references/ + `.harness/` 全顶层平铺 | **加 `references/`**：顶层 `traps.md` `glossary.md`；每个 skill 目录内 `references/<topic>.md`（按需加载不进主 SKILL.md）。**`.harness/` 加层级**：`state/`（持久）、`tasks/current/<task-id>/`（当前批次）+ `tasks/archive/<task-id>/`（已完成）、`rendered/`、`scratch/`、`.bak/` | 用户：「是不是少了references等等你可以看 D:\work\xinyue\aigc_platfrom_back」「.harness是不是要有层级啊」 |
| 17 | v3.6 按 task-id 子目录（L-档批次隔离） | **`.harness/` 按 route 分工作区**：code/ novel/ news/ 各自平铺 specs/plans/... 或 drafts/archive；；**取消 `tasks/<task-id>/`**——按 route 自然分流就够了 | 用户：「.harness我还是希望前面那样的能区分不同文件放的目录啊，只是要区分code和novel和news」 |
| 18 | v3.7 只有 `scripts/`（引擎机制），缺一次性「项目 clone 后建 `.harness/`」入口 | **加 `init/`**：`init.sh` / `init.ps1`（跨平台 bootstrap）+ `verify.sh`（体检）+ `templates/`（`.harness/` 骨架源）+ README.md。`init/` 给**人**用一次性；`scripts/` 给**引擎**用持续 | 用户：「加个init的目录，用于项目clone初始化用的」 |
| 19 | `.harness/.bak/` 一个全局目录（v3.7） | **`.bak/` 按子目录分**——不同层的快照保留诉求不同：`state/.bak/` 50 份（珍贵不易重建）/ `novel/.bak/` 30 份（正文改坏一次代价高）/ `code/.bak/` `news/.bak/` 20 份 / `rendered/.bak/` 5 份（引擎产物一键重生成）；`scratch/` 删除（未用过；`.bak/` 覆盖安全网职责） | 用户：「.harness和harness-factory这两个目录你做的更好吧」 |

## 1. 目标与定位

让 **Claude / Codex / Trae / WorkBuddy** 四个 AI 平台，在 **代码 / 长篇小说 / 新闻** 三条线上按同一套流程纪律工作。

v1 的五个死因作为反面约束（v2.1 原文继承）：入口链过长；同一规则多处重复；引擎与资产混住；分发模型悬而未决；项目实例住在共享仓内导致副本就地分化。

**定位补充**：这套东西是**个人工具**，不做共享、不做「同事开箱可用」。要用的人自己 clone 到自己机器，他的 `.harness/` 是他的。

## 2. 世界观（v3）

**四类身份：程序 / 状态 / 产物 / 度量。**

| 类 | 装什么 | 住哪 | git | 谁写 |
|---|---|---|---|---|
| **程序** | 大脑 + 适配 + 入口 | `harness-factory/` | tracked | 人 |
| **AI 全部产出** | 持久状态 + 渲染产物 + 任务级产物 + 临时草稿 | **`<项目根>/.harness/`** | **gitignored** | **AI**（引擎 + 主会话） |
| **平台入口 shim** | 一行 @import | `<项目根>/AGENTS.md` 等 | `info/exclude` | 引擎生成 |

**v3 与 v2.1 的根本不同**（三次迭代）：
- v2.1 把状态集中住 `harness-factory/.workspaces/<proj>/`（gitignored，引擎内），多项目共享一个引擎仓
- v3 第一版按蓝图**把状态搬到每个项目自己的 `.harness/`**，由项目仓正常跟踪（用户原话）
- v3 第二版明确 `.harness/` 是 **AI 的目录**——人类只看不动，gitignored；状态与代码彻底分开
- v3 第三版**删除 `.ai-runtime-artifacts/`**，其子目录（specs/ plans/ verifications/ reviews/ retros/ tracking/ scratch/）整体并入 `.harness/`——AI 全部产出集中在一个目录下，nuke 即可一键重置
- `config/harness.yaml` 的 `workspace_filter` 字段指明：哪些项目路径不渲染进产物（默认：整个 `.harness/` 都不进）

## 3. 分发模型

**引擎单实例（`harness-factory/`，本机唯一一份）+ AI 全部产出每项目一份（`<项目根>/.harness/`，gitignored）+ 平台入口 shim 每项目一份（各项目根，全走 `.git/info/exclude`）。**

- 一条挪不动的墙：平台从项目根向上发现文件，所以 shim 必须在项目根。
- 升级引擎 = 在 `harness-factory/` 拉代码；不动项目仓
- 项目仓动业务代码；不动 `.harness/`（gitignored，AI 自己的事）
- 渲染产物住 `.harness/rendered/`，平台 shim 一行 @import 指过去
- 任务级产物（specs/ plans/ ...）住 `.harness/` 内；任务结束可扔
- 版本错开靠 `.harness/state.json` 记录的「渲染时引擎 commit」。SessionStart 只提示「停在 X，要不要跟」，**绝不自动跟**。

## 4. 中央仓蓝图

完整文件级目录见 **§5**（此处不复述）。顶层分类速记：

| 层 | 目录 | 回答什么 |
|---|---|---|
| 大脑 | core/ | AI 应该**怎么工作**（原则、决策、门禁、任务生命周期） |
| 任务 | tasks/ | 这件事**是什么**（按 route 拆，按子类型分文件；多步场景进 `scenarios/`） |
| 技能 | skills/ | 这能力**怎么做**（SKILL.md，按需加载） |
| 执行者 | agents/ | 这角色**是谁**（按话题切的 7 个角色——精简合并） |
| 模板 | templates/ | 输出物**长什么样** |
| 适配 | platform/ | 平台特定文件（skills/agents/commands/rules/ENTRY） |
| 度量 | evals/ | 好不好用（行为评测，case 直接住 coding/writing/news/） |
| 入口 | scripts/ | shell 入口（install/sync/validate/lint） |
| 配置 | config/ | YAML 配置（harness/models/platforms） |
| 测试 | tests/ | 单元 + golden render |

## 5. 目录法

§2 四类身份对应文件系统：

```
harness-factory/                          [T] tracked
├── README.md                              入口：地图 + 5 分钟上手 + 蓝图概览
├── VERSION
├── CHANGELOG.md
├── LICENSE
├── package.json tsconfig.json             scripts：harness / check（§13 零运行时依赖）
├── .gitignore .gitattributes              LF 锁
│
├── core/                                  9 文件：原则与决策框架
│   ├── constitution.md                     最高优先级行为原则
│   ├── operating-principles.md            AI 工作原则
│   ├── decision-making.md                 遇到不确定性如何决策
│   ├── context-management.md              上下文管理策略
│   ├── task-lifecycle.md                  任务从开始到结束的生命周期
│   ├── quality-gates.md                   质量门禁（≥3 档）
│   ├── verification.md                    验证原则
│   ├── failure-recovery.md                失败/回滚/重新尝试
│   └── communication.md                   与用户沟通规则
│
├── tasks/                                 按任务类型拆（route × 子类型；多步场景进 `scenarios/`）
│   ├── coding/  README.md workflow.md requirement-analysis.md implementation.md
│   │            testing.md debugging.md code-review.md        (6 单步 + scenarios)
│   │            scenarios/                new-feature.md bug-fix.md refactor.md code-review.md performance-optimization.md
│   ├── writing/ README.md workflow.md research.md outlining.md drafting.md rewriting.md
│   │             proofreading.md fact-checking.md style.md
│   │             scenarios/                article.md long-form.md rewrite.md
│   └── news/    README.md workflow.md research.md source-selection.md fact-verification.md
│                cross-checking.md chronology.md attribution.md uncertainty.md citation.md
│                scenarios/                breaking-news.md news-report.md investigative.md fact-check.md
│
├── skills/                                按需加载的具体能力
│   ├── coding/  analyze-requirement/ explore-codebase/ design-feature/ implement-feature/
│   │            debug/ review-code/ refactor/        (各 SKILL.md + references/)
│   ├── writing/ research-topic/ write-article/ rewrite/ proofread/ fact-check/
│   └── news/    research-news/ verify-claims/ compare-sources/ write-news/
│
├── agents/                                按话题切的 7 个角色（精简合并）
│   ├── implementer.md                       原 code-architect + code-implementer 合并
│   ├── code-reviewer.md                     物理禁写（§lint 执法）
│   ├── debugger.md
│   ├── test-engineer.md
│   ├── researcher.md                        跨路线
│   ├── editor.md                            原 writer + editor + news-editor 合并
│   └── fact-checker.md
│
├── templates/                             输出物模板（精简后）
│   ├── coding/  design.md bug-report.md
│   ├── writing/ article.md outline.md
│   └── news/    news-article.md source-list.md fact-check.md
│
├── platform/                              四个平台适配层
│   ├── claude/    CLAUDE.md settings.json  skills/ agents/ commands/
│   ├── codex/     AGENTS.md                skills/ agents/
│   ├── trae/      project-rules/           skills/ agents/
│   └── workbuddy/ CODEBUDDY.md rules/      skills/ agents/ commands/
│
├── evals/                                 行为评测（精简：case 直接住 route 目录，无外壳框架）
│   ├── coding/ writing/ news/             case + rubric.yaml + expected.md
│   └── README.md                            「跑什么 / 不跑什么 / 何时跑」

├── references/                           全引擎参考材料（v3.6 新增）
│   ├── traps.md                             跨路线常见踩坑（不变量、禁句、机制兜底边界）
│   └── glossary.md                         术语表（跨域缩写、平台名映射、内部黑话）
│
│   # 各 skill 目录下还有自己的 references/：
│   # skills/<route>/<skill>/references/<topic>.md
│   # 按需加载不进主 SKILL.md（避免主文件膨胀）

├── init/                                 项目初始化工具集（v3.7 新增；给**人**用一次性）
│   ├── README.md                            使用说明（5 分钟上手 + 三个 mode）
│   ├── init.sh  init.ps1                  跨平台 bootstrap：建 `.harness/` 骨架
│   ├── verify.sh                            初始化后体检（独立可调用）
│   └── templates/                          `.harness/` 初始骨架源
│       ├── state/{config,profile,MEMORY,state.json}
│       ├── code/{specs,plans,verifications,retros,tracking}
│       ├── novel/{drafts,archive}
│       ├── news/{drafts,archive}
│       └── rendered/.claude/rules/HARNESS.md 等

├── scripts/                               引擎机制（给**引擎**用持续）
│
├── scripts/                               shell 入口
│   ├── install.sh install.ps1 sync-platforms.sh validate.sh lint-prompts.sh
│
├── config/                                YAML 配置
│   ├── harness.yaml                        总配置（含 workspace_filter）
│   ├── models.yaml                         模型配置
│   └── platforms.yaml                      平台特定配置
│
├── docs/                                  设计文档
│   └── design.md                           本文档（唯一设计事实源）
│
├── tests/                                 单元 + golden render
```

**三本账纪律**（§2 的判据）：会不会被下次任务当事实读。**会** → `.harness/state/`；**不会** → `.harness/{code,novel,news}/`；**是程序** → 在这里。

### 5.5 项目侧 `.harness/` 目录（每项目一份，**gitignored，是 AI 的全部产出**）

**v3.7：按 route 分工作区**——`code/` `novel/` `news/` 各自平铺 specs/plans/... 或 drafts/archive；跨路线共享状态进 `state/`；引擎渲染进 `rendered/`。

```
<项目根>/.harness/                          [I] gitignored；**AI 全部产出**

├── state/                                 ## 跨路线共享（持久）
│   ├── config.md                          ★ 初始 human-seed，AI 可改
│   ├── MEMORY.md                          AI 工作中积累的笔记 ≤100 行
│   ├── state.json                         ★ 机器管：渲染 commit pin / 产物清单 hash / last_error
│   └── profile.md                         ★ 初始人类 seed + AI 增量（技术栈、模块边界、验证命令）

├── code/                                  ## code 线工作区
│   ├── specs/                              L 档方案（落盘：`engine/contracts/` 模板住这里）
│   ├── plans/                              L 档实施计划（含 WU 拆分）
│   ├── verifications/                      验证证据（每条验收项的运行输出）
│   ├── retros/                             尾盘收尾（含 closeout）
│   ├── tracking/                           PROGRESS.md / DISPATCH-TRACK-*.md / HANDOFF.md
│   └── .bak/                  ## 20 份（specs plans verifications 等任务快照）

├── novel/                                 ## novel 线工作区
│   ├── book.md  chapters.md  characters.md  foreshadowing.md  voice.md   持久状态
│   ├── drafts/                                                       草稿
│   ├── archive/                                                      完成稿件
│   └── .bak/                  ## 30 份（正文快照比任务快照珍贵——万字稿改坏一次代价高）

├── news/                                  ## news 线工作区
│   ├── sources.md  beat-log.md                                       持久状态
│   ├── drafts/                                                       稿件草稿
│   ├── archive/                                                      已发布
│   └── .bak/                  ## 20 份

├── rendered/                              ## 引擎渲染（平台入口）
│   ├── AGENTS.md                          Codex 入口
│   ├── CLAUDE.md                          Claude 入口
│   ├── CODEBUDDY.md                       WorkBuddy 入口
│   ├── .claude/rules/HARNESS.md           Claude 一页纸
│   ├── .codex/hooks.json                  Codex hooks
│   ├── .codebuddy/settings.json           CodeBuddy hooks
│   ├── .trae/rules/project_rules.md       Trae 一页纸
│   └── .bak/                  ## 5 份（引擎产物一键重生成）
```

state/.bak/ 50 份（人类 seed + MEMORY 珍贵不易重建）；scratch/ 已删（未用过）。

<项目根>：
```
├── AGENTS.md                               [excluded] 平台入口 shim（一行 @import）
├── CLAUDE.md                               [excluded]
├── CODEBUDDY.md                            [excluded]
├── .claude/rules/HARNESS.md                [excluded]
└── (业务代码；项目仓的 tracked 部分)
```

**为什么 `.harness/` 是 AI 目录（gitignored）**：跟踪 AI 的脑状态进 git 等于把 AI 工作细节变成 review 噪音。

**约定**：
- **人类写**：仅初始 seed 文件（`state/config.md` 第一次写、`state/profile.md`），之后**不再手改** `.harness/`
- **AI 写**：`state/` 增量更新、`{code,novel,news}/` 全权负责、`.bak/` 快照
- `.harness/` 严禁出现在产物渲染路径外（`config/harness.yaml` 的 `workspace_filter` 默认包含 `.harness/**`）
- 严禁写进 `tasks/` `skills/` `agents/` `core/`（程序无状态）
- hook 覆盖 `.harness/**` 任一文件前**必须**把旧版复制进 `.harness/.bak/`（机制兜底，比要求人记得提交更可靠）

**v3.3：`.harness/` 是 AI 全部产出的唯一目录**——持久状态（config/MEMORY/profile/novel/news）、渲染产物（rendered/）、任务产物（specs/plans/verifications/retros/tracking/）、临时草稿（scratch/）、快照（.bak/）全部住这里。原 `.ai-runtime-artifacts/` 不再存在。

**nuke & reset**：删掉整个 `.harness/` 即可让 AI 从头开始这个项目（保留所有 AI 产出）；然后重跑一次 `npm run harness` 重建 `rendered/`。

**项目间迁移**：`mv <旧项目根>/.harness <新项目根>/.harness`，跑 `npm run harness` 重渲染。注意：渲染 commit pin 跟着 `.harness/` 走，迁移后第一次启动会提示「渲染时用的是旧引擎 commit，跟不跟」。

## 6. 一页纸启动契约

一页纸源 = `core/constitution.md` + `core/operating-principles.md` + `core/quality-gates.md` + `core/task-lifecycle.md` + `tasks/<line>/workflow.md`。**硬预算 ≤240 行**（lint 执法）。

**渲染目的地 = `<项目根>/.harness/rendered/`**（v3.3 修订：从项目根迁移到 `.harness/` 内，平台入口由项目根的 shim 一行 @import 指向）：

| 平台 | 入口文件 | 渲染产物（实文件） | 项目根 shim（一行 @import） |
|---|---|---|---|
| Claude | `platform/claude/CLAUDE.md` | `.harness/rendered/CLAUDE.md` | `CLAUDE.md` → `.harness/rendered/CLAUDE.md` |
| Claude 一页纸 | — | `.harness/rendered/.claude/rules/HARNESS.md` | `.claude/rules/HARNESS.md` → 该文件 |
| Codex | `platform/codex/AGENTS.md` | `.harness/rendered/AGENTS.md` | `AGENTS.md` → 该文件 |
| WorkBuddy | `platform/workbuddy/CODEBUDDY.md` | `.harness/rendered/CODEBUDDY.md` | `CODEBUDDY.md` → 该文件 |
| Trae | `platform/trae/project-rules/*.md` | `.harness/rendered/.trae/rules/project_rules.md` | `.trae/rules/project_rules.md` → 该文件 |

**为什么渲染产物从项目根迁到 `.harness/rendered/`**：nuke `.harness/` 一键重置（状态、记忆、渲染产物一起清），平台入口 shim 引擎同步写，git 不会脏；规则文件**只允许 AI 改**，人类只看不动。

多跳加载只在 L 档允许，那时读 `core/quality-gates.md` 的 L 档展开段 + `tasks/<route>/scenarios/<scenario>.md`。

## 7. 门禁三档

源在 `core/quality-gates.md`（档位本身）+ `core/task-lifecycle.md`（阶段映射）。沿用 v2.1 的 S/M/L：

- **S · 直接做**：单点改动、问答、查询、不动叙事文本的整理
- **M · 一页方案**：多文件改动、新功能、重构
- **L · 全阶段流程**：跨模块、多 task 派发、对外发布

novel 路线无 S 档（理由同 v2.1）。路线管线不随档位升降。证据总则一句全档通用：「没有证据不得声称完成」。

## 8. 任务 / 技能 / Agent / 工作流（蓝图的核心贡献）

四个并列的认知层，每层回答不同问题——**正交关系**：

| 层 | 回答 | 路径 | 谁加载 |
|---|---|---|---|
| `tasks/<route>/<task>.md` | 这件事**是什么** | 任务类型 | 主会话读对应 task |
| `skills/<route>/<skill>/SKILL.md` | 这能力**怎么做** | skill 目录 | 加载到当前上下文 |
| `agents/<name>.md` | 这角色**是谁** | agent 文件 | 平台按需 spawn |
| `tasks/<route>/scenarios/<scenario>.md` | 多步骤任务**怎么串** | scenario 文件 | L 档加载 |

**例：debug 一段 Java 代码**
- 任务文档 `tasks/coding/debugging.md` 定义 debug 的步骤与产物
- 技能 `skills/coding/debug/SKILL.md` 给出 hypothesis-driven 的执行细节
- Agent `agents/debugger.md` 是负责执行的实体
- Workflow `tasks/coding/scenarios/bug-fix.md` 把上面串成完整的 bug 修复批次

**与 v2.1 的不同**：v2.1 把所有这些塞进 `engine/routes/<line>.md` 一份 ≤60 行文件；蓝图按认知层拆开成多份，每份独立维护。这是我从蓝图里学到的最大提升。

## 9. 平台方言

`platform/<name>/` 装平台特定文件。

**承认这是 v1 315 文件镜像模型的复活**：每家 skills/ agents/ commands/ 各自一份，漂移是默认行为。**唯一护栏**：`scripts/sync-platforms.sh` 每个 release 跑一次，给出 4 份 platform/ 的 diff，超出阈值 fail。这个缓解不消除漂移。

各平台入口文件：
- Claude：`CLAUDE.md`（项目根）+ `settings.json`（hooks 段 merge）
- Codex：`AGENTS.md`（项目根，零转换）
- WorkBuddy：`CODEBUDDY.md`（项目根，已查证支持）
- Trae：`project-rules/`（项目根，无 hook 降级，见 §10）

## 10. Hook：一份实现 + 四份清单（同 v2.1）

**承重事实**：Claude / Codex / CodeBuddy 使用同一套事件词表与输出契约（`hookSpecificOutput.additionalContext`、`decision: block`、`continue: false`、exit code 2 = 拦截）。故门禁逻辑只写一遍。

| 我们的动作 | Claude Code | Codex | WorkBuddy(CodeBuddy) | Trae |
|---|---|---|---|---|
| 会话起：渲染产物有变→提示 + 注入上下文 | `SessionStart` matcher `startup\|resume\|compact` | 同 | 同 | **无 hook**（手动跑 `scripts/install.sh`） |
| 写文件后：跑 verify | `PostToolUse` matcher `Write\|Edit\|MultiEdit` | `apply_patch` 别名 | `Write\|Edit` | 无 |
| 收尾前：无证据不许停 | `Stop` | `Stop` | `Stop` | 无 |

实现位于 `scripts/` 下的 shell + 共享 decision 模块（按 §11 文件预算拆，暂未落）。

## 11. lint 硬数字

超了即失败，由 `scripts/lint-prompts.sh` 执法（shell + awk，行数 + 关键词即可）：

| 文件类型 | 行数上限 |
|---|---|
| `core/*.md` | ≤150 |
| `tasks/<route>/*.md` | ≤80 |
| `tasks/<route>/scenarios/*.md` | ≤100 |
| `skills/<route>/<skill>/SKILL.md` | ≤150 |
| `agents/*.md` | ≤150 |
| `templates/<route>/*.md` | ≤100 |
| `platform/<name>/*` 每文件 | ≤50 |
| 一页纸产物（渲染后） | ≤240 |
| YAML `config/*.yaml` | 不进 lint（§18 待验） |

**不变量**：任何文件出现具体项目名、绝对路径、技术栈细节 = 失败（项目事实只准住 `.harness/`）。`core/`, `tasks/`, `skills/`, `agents/`, `templates/`, `config/` 出现具体项目名 = 失败。`platform/` 例外：Claude `CLAUDE.md` 等入口文件可以引用具体项目结构（它是描述「怎么发现」的文件，不是事实文件）。

## 12. 防漂移三道防线

1. **git 执法**：核心内容（`core/` `tasks/` `skills/` `agents/` `templates/`）就地改 → `git status` 脏 → 警告「这是共享内容，就地改会在下次 pull 时打架」。改进 → 提交并 push 上游；项目特化 → 挪进 `.harness/`。
2. **lint 静态执法**：§11 全部数字。
3. **`scripts/sync-platforms.sh`**：每个 release 跑一次，对比 `platform/claude/`、`platform/codex/`、`platform/trae/`、`platform/workbuddy/` 的内容 diff，超阈值 fail。

**承认**：`platform/` 内 4 份镜像、YAML 配置是已知漂移/覆盖风险源，**护栏（sync-platforms、workspace_filter）只降低风险，不保证安全**。多人共用同一仓时务必改名或过滤（§18 待验）。

## 13. 工具链（同 v2.1）

Node 26.8.2 + TypeScript 7.0.2，零运行时依赖。`scripts/*.sh` 用 POSIX sh 写，`scripts/*.ps1` 是 Windows 镜像。设计命令系统是 `npm run harness` / `npm run check` 两个逃生口，不设独立 CLI。

## 14. 错误处理与降级（同 v2.1）

L 档计划未落盘 → 拒称「批次完成」。`scripts/install.sh` 失败 → 回滚产物。Trae 无 hook → 降级为产物自包含 + 人工两步 checklist。

## 15. 测试策略

- **`tests/`**：单元 + golden render（v2.1 同款）
- **`evals/`**：行为评测骨架
  - `coding/` `writing/` `news/`：按路线的 case 目录
  - `cases/`：跨路线共享 case 池
  - `expected/`：期望产物模板
  - `scoring/`：rubric 与评分脚本

评测**不上 CI 自动跑**（LLM-as-judge 的 token 成本高于信息量），发版时手跑一次贴到 CHANGELOG。rubric 分数**不准引用做「质量更好」的断言**——只贴分，结论看分差且附原始 rubric。

## 16. 落地路线

- **Step 0 · 大脑**：写 `core/constitution.md` `core/operating-principles.md` `core/quality-gates.md` `core/task-lifecycle.md` `tasks/coding/workflow.md` `platform/codex/AGENTS.md` `platform/claude/CLAUDE.md`。在 Codex 上跑通，理由同 v2.1（零转换平台，掩盖最少接线缺陷）。
- **Step 1 · 任务文档 + 单项目接通**：写 `tasks/coding/{requirement-analysis,implementation,testing,debugging,code-review}.md` 首批 5 文件。在 aigc_platfrom_back 项目根建 `.harness/`（config.md + profile.md + state.json）→ 渲染进 `.harness/rendered/` → 写项目根的 `.git/info/exclude`（排除接线 shim）→ 跑通 hook 全链路（novel/news 档案先占位不启用）。同批改业务仓唯一一处 tracked 文件：`CLAUDE.md` harness 节改引产物，清理 `harness-factory|foundry|kit` 旧引用与 `.claude/HARNESS-RULES.md`。
  **实测前置**：父仓当前未 ignore `harness-factory/`（git status 显示 `??`，0 tracked 文件），316 个文件常年挂在业务仓 status 里，一次 `git add .` 即被吞为 gitlink。Step 1 第一件事是把 `harness-factory/` 写进父仓 `.git/info/exclude`。
- **Step 2 · 技能**：写 `skills/coding/{analyze-requirement,explore-codebase,design-feature,implement-feature,debug,review-code,refactor}/SKILL.md` 首批 7 个。
- **Step 3 · Agent + Scenario**：写 `agents/*.md` 11 个 + `tasks/coding/scenarios/{new-feature,bug-fix,refactor,code-review,performance-optimization}.md`。
- **Step 4 · 模板**：写 `templates/<route>/*.md`（coding 2 / writing 2 / news 3）。
- **Step 5 · 平台完整内容**：补齐 `platform/{claude,codex,trae,workbuddy}/` 的 skills/ / commands/ / rules/ 子目录。
- **Step 6 · 评测**：写 `evals/coding/bug-fix-001/` 首个 case（含 input/expected/rubric），跑一遍验证骨架可用。
- **Step 7 · writing + news 路线**：与 code 路线并行，分批填充。

顺序原则：**先大脑、再技能、再执行者、最后评测**——大脑定义了评判标准，技能按大脑的评判标准产出内容，Agent 包装技能，评测度量整体。

## 17. 已否决方案（v3）

v2.1 的 §17（15 条）中**反转** 7 条（蓝图采纳了被否决的方案），新增 5 条：

**v2.1 否决、v3 采纳的（用户决定）**：

| 否决项 | 理由 |
|---|---|
| v2.1 的 4 件套 ≤60 行 route 文件 | 蓝图按任务类型拆多份，每份独立维护 |
| v2.1 的「agent 按权限形状切」（leader + 8 职员） | 蓝图按话题切 11 个角色 |
| v2.1 的 `compiler/platforms/*.ts` 生成器 | 蓝图 `platform/<name>/` 直接放文件 |
| v2.1 的 `.agents/skills/` 唯一 | 用户：「`.agents` 应该是不要的」 |
| v2.1 的引擎仓内不放 `project/` `memory/`（v1 最大错误） | 用户蓝图：放在引擎仓内（v3.5 已删——精简采纳时一并删除） | 用 `config/harness.yaml` 的 `workspace_filter` 字段作护栏 |
| v2.1 的 markdown 配置单一文件 | 蓝图：YAML 配置三份 |
| v2.1 的 225 行一页纸预算 | 蓝图：240 行 |

**v3 新增的否决**：

| 否决项 | 理由 |
|---|---|
| 单一 `core/constitution.md` 涵盖所有原则 | 一份宪法读不完。蓝图拆 9 个文件，每文件回答一个明确问题 |
| `agents/` 与 `tasks/` 合并 | agents 回答「谁」，tasks 回答「什么」——正交 |
| `templates/` 与 `core/` 合并 | templates 是输出物骨架（具体到字段），core 是原则（抽象到判断） |
| YAML 进 lint | shell+awk 解析 YAML 复杂；排 §18，待 Step 5 评估用 jq/yq 替代 |

**v3 第二次修订新增的取舍**（用户：「有些功能作用重合的目录名可以去掉」「`.workspaces` 改成 `.harness`」）：

| `workflows/` 与 `tasks/` 共存 | 蓝图里 tasks→skills→workflows 是单链路——两份是同一件事。删除 `workflows/`，全部并入 `tasks/<route>/scenarios/`，以子目录区分单步任务 vs 多步场景 | 用户决定；功能作用重合 |
| 状态住 `harness-factory/.workspaces/<proj>/`（gitignored，引擎集中） | 状态住 `<项目根>/.harness/`（**gitignored——AI 的目录**） | 用户决定；`.harness/` 是 AI 产出而不是人类状态 |
| `.harness/` tracked in 项目仓 | **`.harness/` 必须 gitignored**——它是 AI 目录而非项目身份的一部分 | 跟踪 AI 的脑状态进 git 等于把 AI 工作细节变成 review 噪音；改回 gitignored |
| `.harness/.bak/` 单独存所有快照 | **`.harness/.bak/` 唯一**——保护所有 AI 产出（状态、渲染、任务产物） | 没有第二个 `.ai-runtime-artifacts/.bak/` 跟它分家 |

**v2.1 的 8 条否决继承**（v3 仍未变）：四家各写一份 hook 逻辑、Trae 按可能有 hook 设计门禁、`<100` 技能原文 vendor、用 `MEMORY.md` 装小说状态、用 LLM 审稿抓小说连续性、build/产品分级、harness 命令变成 CLI、产物的全平台镜像（这个**不继承**——v3 接受了 platform/ 镜像，列为已知风险）。

## 18. 遗留开放问题（不阻塞 Step 0）

- **`platform/<name>/` 4 份镜像的漂移治理**：`scripts/sync-platforms.sh` 是缓解不是根治；阈值与触发频率需要 Step 5 在真平台验证
- **`project/` `memory/` 在引擎仓内**（已删）：v3.5 精简时一并删除，理由是它们与 `.harness/config.md` + `profile.md` 功能重叠；保留只会让人以为「这里有真状态」，其实只是空模板
- **`config/*.yaml` 何时进 lint**：先以 `scripts/lint-prompts.sh` 的 shell 兜底（结构校验）；Step 5 评估 jq/yq 替代 awk
- **`skills/` 不在 `.agents/` 下**：Trae/Codex 自动发现失效；需 `platform/trae/project-rules/` 与 `platform/codex/AGENTS.md` 显式指路
- **`agents/` 11 个角色按话题切的粒度合理性**：v2.1 给出过 v1 838 行的实证反驳，v3 接受后需 Step 3 验证是否真出现重复（code-architect vs code-implementer、writer vs news-editor）
- **`.harness/.bak/` 的轮转策略**：默认 20 份来自 v2.1 经验值；真实使用后按命中率调
- **`.harness/` tracked 是否会被工程代码评审工具当成业务文件对待**：需在真实项目中跑一次验证

## v2.1 vs v3 关系

v2.1 设计文档保留于 `docs/archive/v2.1-design.md`，标注「已被 v3 取代」。v3 不重复 v2.1 的通用决策（目标 / 分发 / 门禁 / Hook / 工具链 / 降级），只描述蓝图采纳后的差异。**v3 是 v2.1 + 蓝图补丁 = 蓝图；v2.1 是 v3 的骨架设计底座**。