# Skill 索引

> 自动生成的 Skill 索引 — 共 84 个 Skill，采用扁平目录结构。
> 最后更新：2026-08-06
> 生成方式：`bash scripts/gen-skill-index.sh`

## 按字母顺序索引

| 序号 | Skill 目录 | 说明 |
|------|-----------|------|
| 1 | `agent-browser` | Browser automation for AI agents via inference.sh. Navigate web pages, interact with elements using @e refs, take screenshots, record video. Capabilities: web scraping, form filling, clicking, typing, |
| 2 | `agent-shield` | 安全审计：扫描配置漏洞、注入风险、MCP 安全问题。保护 Harness Foundry 免受提示注入、权限过度、Hook 注入等攻击。 |
| 3 | `analyze-architecture` | 深入分析项目架构，回答架构相关问题。触发：询问设计原因、技术选型、模块职责、架构决策。 |
| 4 | `analyze-impact` | 评估代码变更的影响范围。触发：重构前、修改核心方法、批量修改前。 |
| 5 | `architecture-patterns` | ## WHAT |
| 6 | `auto-compact` | 智能上下文压缩：在最佳时机触发压缩，保留关键状态，清理冗余上下文。 |
| 7 | `backend-doc-generator` | 生成标准后端技术文档，包含Mermaid流程图、时序图、类图、状态图。Invoke when user needs to create backend technical documentation or draw system architecture diagrams. |
| 8 | `brainstorming` | You MUST use this before any creative work - creating features, building |
| 9 | `ceo-orchestration` | CEO 角色主 Skill — 跨域协调入口，调用子 Skill 完成各项职责 |
| 10 | `code-insight-stack` | 编排 codebase-memory + ripgrep + LSP 三层查询栈，按场景选择最便宜的工具组合。触发：探索陌生代码库、定位修改点、调查 bug、准备 refactor、计划实现、跨文件影响分析。 |
| 11 | `code-review` | Systematic code review patterns covering security, performance, maintainability, |
| 12 | `cursor-orchestration` | Cursor 多 subagent 并行编排，等价于 omx ultrawork。在用户已批准 plan 并说「开始实现」后，通过 harness-coder（代码）、harness-implementer（轻量）、harness-test-engineer、harness-web-investigator（research）等并行派发 WU。触发词：并行实现、多 task、开始实现、cursor |
| 13 | `document-review` | Use when reviewing any document (spec, design, plan) for completeness, clarity, and quality — especially environment preparation completeness. Triggers: review document, check document, audit spec, au |
| 14 | `fact-check` | 事实核查 skill，对新闻内容进行多源交叉验证 |
| 15 | `fanqie` | 用途与边界 |
| 16 | `fanqie-novel-auto-publish` | 番茄小说创作发布一条龙技能，整合 AI 创作与番茄发布，支持全自动批量上传、断点续传、错误重试、发布报告生成 |
| 17 | `find-skills` | Helps users discover and install agent skills when they ask questions |
| 18 | `frontend-design` | Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications (examples inclu |
| 19 | `get-callees` | 获取指定符号调用的所有代码。触发：想知道某个方法内部调用了什么、分析实现细节。 |
| 20 | `get-callers` | 获取调用指定符号的所有代码。触发：想知道谁在调用某个方法、分析依赖、评估影响。 |
| 21 | `git-xywh` | 组织级 Git 工作流：三主干（main / test / develop）、五类临时分支、多环境隔离、Angular 提交与 MR 流程；涵盖合并、变基、冲突、恢复。任务涉及分支、提测、热修、版本标签、提交规范或 MR 时使用。 |
| 22 | `harness-health` | 系统健康度检查 Skill — 一键输出所有子系统的健康状态 |
| 23 | `humanizer` | Remove signs of AI-generated writing from text. Use when editing or reviewing |
| 24 | `humanizer-zh` | 中文 AI 文风清洗，消除 AI 生成特征，去套路化，句式重构，人物声音分化 |
| 25 | `index-project` | 为项目建立代码索引。触发：大型项目、需要精准定位符号、快速查找调用关系。 |
| 26 | `inkos` | Autonomous novel writing CLI agent with web workbench (InkOS Studio) |
| 27 | `junli-ai-novel` | 长篇网文核心写作引擎，支持章节续写、扩写、重写，维护人物状态和伏笔追踪 |
| 28 | `karpathy-guidelines` | 写代码、审查代码、重构代码时的行为准则：先想再写、保持简单、只改必要的，目标驱动。code 域默认基线，P0 优先级。 |
| 29 | `lsp-query` | 通过 Language Server Protocol（typescript-language-server / pyright / gopls 等）做结构化代码查询：定义、引用、悬停信息、符号、代码诊断。触发：找定义、找引用、找类型、看类型签名、go to definition、find references、hover、diagnostics、rename、检查类型错误。 |
| 30 | `memory-manager` | 小说项目记忆管理引擎，双轨架构+Mem0增强模式，伏笔状态机，Agent交接压缩协议 |
| 31 | `news-generator` | 新闻写作技能包：根据热点/素材生成新闻稿件 |
| 32 | `news-polish` | 新闻稿件润色技能：去AI味、提升可读性、专业化表达 |
| 33 | `novel-36-beats` | 结构化节拍写作框架，基于 36-beat 三幕式结构，为长篇网文提供完整的情节骨架与节奏控制指南 |
| 34 | `novel-ai-wash` | 深度文风清洗引擎，四层清洗体系（词级→句式→叙事→人物声音），用于批量深度去AI味 |
| 35 | `novel-batch-write` | 批量写作模式，当用户说写到第N章时触发，自动并行/串行写作 |
| 36 | `novel-checkpoint` | 创建、验证写作进度检查点，确保批量写作不丢失上下文 |
| 37 | `novel-contexts` | 小说上下文管理，维护角色设定、世界观、时间线的全局一致性 |
| 38 | `novel-dashboard` | 小说进度仪表板，显示当前书籍状态、章节进度、人物和伏笔状态 |
| 39 | `novel-debug` | 情节矛盾/角色冲突/伏笔遗漏排查与修复 |
| 40 | `novel-evaluator` | 7维量化小说评分系统，基于情节/人物/文笔/世界观/情感/创新/钩子进行质量审查，联动63条陷阱检测，逐条引用原文举证 |
| 41 | `novel-foreshadowing-dag` | 伏笔有向无环图管理，结构化管理和追踪所有伏笔的埋设、触发和回收 |
| 42 | `novel-generator` | 根据用户提供的内容方向自动生成提示词并创作爽文小说 |
| 43 | `novel-guardian` | 法医式事实核查 Agent，专门检查角色/时间线/世界观/情节的连续性 |
| 44 | `novel-guidelines` | 小说写作前思维基线：AI 陷阱 + 简洁原则。写章节/大纲/续写前必须加载 |
| 45 | `novel-improver` | 双平台长篇改良：10维评分 + 13项硬指标 + 结构性改写 |
| 46 | `novel-init` | 新书创作向导，帮助用户从零开始创建小说项目 |
| 47 | `novel-mechanical-scorer` | 无LLM的确定性章节质量评分器，在LLM审稿前做纯规则检查 |
| 48 | `novel-metrics` | 写作指标追踪，统计字数、速度、质量趋势 |
| 49 | `novel-orchestrator` | 小说创作总控调度器，协调 writer→planner→reviewer→humanizer→editor→memory-keeper 全链路，管理阶段门禁和返修闭环 |
| 50 | `novel-protocol` | 渐进式披露路由 + 因果链一致性（入口层，省 76% token） |
| 51 | `novel-quick-write` | 快速单章写作，无需完整编排流程，适用于写第X章类型的简单写作任务 |
| 52 | `novel-receiving-review` | 接收审稿反馈，正确处理修改建议，不是盲目接受或机械执行 |
| 53 | `novel-recovery` | 会话恢复工具，恢复中断的写作任务和上下文 |
| 54 | `novel-safe-revision` | 安全返修流程：小步返修、逐次确认、保留历史版本 |
| 55 | `novel-simplify` | 章节自查简洁度检查，识别冗余、重复、堆砌问题 |
| 56 | `novel-voice-profile` | 人物声音档案，为每个角色建立独特的语言指纹和说话风格 |
| 57 | `novel-writer-cn` | 创建小说创作框架，包括人物设定、人物关系、剧情发展和多版本结局 |
| 58 | `piqie-writing` | 番茄平台爆款写作专项：3章一爽、算法适配、新人破零 |
| 59 | `planning-with-files` | Implements Manus-style file-based planning to organize and track progress |
| 60 | `playwright` | Browser automation via Playwright MCP. Navigate websites, click elements, |
| 61 | `project-planner` | Triage ideas, problems, and feature requests into the right format: |
| 62 | `prompt-engineering-expert` | Advanced expert in prompt engineering, custom instructions design, and |
| 63 | `qidian-writing` | 起点中文网慢热品质写作专项：设定硬、人物真、信息增量 |
| 64 | `query-knowledge-graph` | 查询 codebase-memory-mcp 的知识图谱，获取结构化信息。触发：需要查询项目结构、模块关系、依赖关系。 |
| 65 | `query-symbol` | 快速定位代码符号（类/函数/变量）。触发：需要找某个符号、不知道在哪里、查询定义。 |
| 66 | `receiving-code-review` | 根据独立审查者的反馈修改代码。 |
| 67 | `refactor-safely` | Plans and executes safe refactors with small steps, tests, and rollback |
| 68 | `requesting-code-review` | Use when completing tasks, implementing major features, or before merging |
| 69 | `ripgrep-search` | 使用 ripgrep（rg）做高速文本搜索，定位引用、字符串、关键字。触发：grep、find、搜索文本、定位字符串、查找引用、查找 TODO/FIXME、查找实现、查找日志、搜索代码。 |
| 70 | `security-auditor` | Use when reviewing code for security vulnerabilities, implementing authentication |
| 71 | `self-improving` | Self-reflection + Self-criticism + Self-learning + Self-organizing memory. |
| 72 | `simplify` | Refactor code for clarity, consistency, and maintainability without changing |
| 73 | `skill-vetter` | Security-first skill vetting for AI agents. Use before installing any |
| 74 | `summarize` | Summarize URLs or files with the summarize CLI (web, PDFs, images, audio, |
| 75 | `superdesign` | Expert frontend design guidelines for creating beautiful, modern UIs. |
| 76 | `two-stage-review` | 两阶段审查：先验证 Spec 合规，再检查代码质量。code 域实现完成后使用。 |
| 77 | `ui-ux-pro-max` | UI/UX design intelligence and implementation guidance for building polished |
| 78 | `understand-project` | 理解项目结构和架构，生成知识图谱。触发：接手新项目、需要了解项目全局、询问架构设计。 |
| 79 | `web-design-guidelines` | 网页设计规范和最佳实践指南 |
| 80 | `web-novel-publishing-readiness-and-quality-check-skill` | 小说质量检查技能。触发关键词：检查正文、质量报告、违禁词、套路句、章节衔接、逻辑漏洞、自检、人写感、大纲、人设。执行最大算力深度推理五步链，每章必须跑freq_check.py词频扫描+逐行违禁词扫描双轨制，复核自检通过方可出报告。 |
| 81 | `web-tools-guide` | Web 工具使用指南：搜索、网页抓取、浏览器自动化。触发：查资料、上网、搜索、打开网站。 |
| 82 | `writing-novel` | 500+章实战提炼的长篇网文写作方法论：全流程 + AI 味消除 + 质量控制 |
| 83 | `writing-plans` | Use when you have a spec or requirements for a multi-step task, before |
| 84 | `zhi-dou-writing` | 智斗/权谋小说写作专项：真人感、信息差博弈、强情绪节奏 |

## 按功能分类

> 分类定义见 [categories.yaml](./categories.yaml)。新 skill 请在 `_meta.json` 中声明 `category` 字段。

### 架构与设计

_后端架构、API 设计、ADR、DDD_

- `architecture-patterns` - ## WHAT
- `backend-doc-generator` - 生成标准后端技术文档，包含Mermaid流程图、时序图、类图、状态图。Invoke when user needs to create backend technical documentation or draw system architecture diagrams.

### 代码审查与重构

_Code review、安全重构、simplify_

- `code-review` - Systematic code review patterns covering security, performance, maintainability,
- `document-review` - Use when reviewing any document (spec, design, plan) for completeness, clarity, and quality — especially environment preparation completeness. Triggers: review document, check document, audit spec, au
- `frontend-design` - Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications (examples inclu
- `receiving-code-review` - 根据独立审查者的反馈修改代码。
- `refactor-safely` - Plans and executes safe refactors with small steps, tests, and rollback
- `requesting-code-review` - Use when completing tasks, implementing major features, or before merging
- `simplify` - Refactor code for clarity, consistency, and maintainability without changing

### 测试与 TDD

_TDD、E2E、benchmark、验证_

- `agent-browser` - Browser automation for AI agents via inference.sh. Navigate web pages, interact with elements using @e refs, take screenshots, record video. Capabilities: web scraping, form filling, clicking, typing,
- `cursor-orchestration` - Cursor 多 subagent 并行编排，等价于 omx ultrawork。在用户已批准 plan 并说「开始实现」后，通过 harness-coder（代码）、harness-implementer（轻量）、harness-test-engineer、harness-web-investigator（research）等并行派发 WU。触发词：并行实现、多 task、开始实现、cursor

### 安全与合规

_安全审计、漏洞扫描、合规检查_

- `security-auditor` - Use when reviewing code for security vulnerabilities, implementing authentication

### 前端开发

_UI/UX 设计、动画、演示_

- `superdesign` - Expert frontend design guidelines for creating beautiful, modern UIs.
- `ui-ux-pro-max` - UI/UX design intelligence and implementation guidance for building polished

### AI / Agent 系统

_Agent 编排、LLM、Prompt、MCP、推荐_

- `prompt-engineering-expert` - Advanced expert in prompt engineering, custom instructions design, and
- `self-improving` - Self-reflection + Self-criticism + Self-learning + Self-organizing memory.

### 小说创作

_生成、编排、写作、评估_

- `inkos` - Autonomous novel writing CLI agent with web workbench (InkOS Studio)
- `junli-ai-novel` - 长篇网文核心写作引擎，支持章节续写、扩写、重写，维护人物状态和伏笔追踪
- `novel-generator` - 根据用户提供的内容方向自动生成提示词并创作爽文小说
- `novel-writer-cn` - 创建小说创作框架，包括人物设定、人物关系、剧情发展和多版本结局
- `writing-novel` - 500+章实战提炼的长篇网文写作方法论：全流程 + AI 味消除 + 质量控制
- `zhi-dou-writing` - 智斗/权谋小说写作专项：真人感、信息差博弈、强情绪节奏

### 小说结构

_大纲、节拍、伏笔、节奏_

- `novel-36-beats` - 结构化节拍写作框架，基于 36-beat 三幕式结构，为长篇网文提供完整的情节骨架与节奏控制指南

### AI 文风处理

_humanizer、文风清洗_

- `humanizer` - Remove signs of AI-generated writing from text. Use when editing or reviewing
- `humanizer-zh` - 中文 AI 文风清洗，消除 AI 生成特征，去套路化，句式重构，人物声音分化
- `novel-ai-wash` - 深度文风清洗引擎，四层清洗体系（词级→句式→叙事→人物声音），用于批量深度去AI味

### 小说发布与平台

_番茄、发布质检_

- `fanqie` - 用途与边界
- `fanqie-novel-auto-publish` - 番茄小说创作发布一条龙技能，整合 AI 创作与番茄发布，支持全自动批量上传、断点续传、错误重试、发布报告生成
- `piqie-writing` - 番茄平台爆款写作专项：3章一爽、算法适配、新人破零
- `qidian-writing` - 起点中文网慢热品质写作专项：设定硬、人物真、信息增量
- `web-novel-publishing-readiness-and-quality-check-skill` - 小说质量检查技能。触发关键词：检查正文、质量报告、违禁词、套路句、章节衔接、逻辑漏洞、自检、人写感、大纲、人设。执行最大算力深度推理五步链，每章必须跑freq_check.py词频扫描+逐行违禁词扫描双轨制，复核自检通过方可出报告。

### 新闻生成与润色

_自动生成、润色_

- `fact-check` - 事实核查 skill，对新闻内容进行多源交叉验证

### 规划与编排

_brainstorming、计划、SDD、并行_

- `brainstorming` - You MUST use this before any creative work - creating features, building
- `planning-with-files` - Implements Manus-style file-based planning to organize and track progress
- `project-planner` - Triage ideas, problems, and feature requests into the right format:
- `writing-plans` - Use when you have a spec or requirements for a multi-step task, before

### 记忆与上下文

_记忆管理、上下文预算_

- `memory-manager` - 小说项目记忆管理引擎，双轨架构+Mem0增强模式，伏笔状态机，Agent交接压缩协议

### 搜索与研究

_深度研究、Exa、查找_

- `web-tools-guide` - Web 工具使用指南：搜索、网页抓取、浏览器自动化。触发：查资料、上网、搜索、打开网站。

### 技能管理与自检

_find-skills、vetter、stocktake、verify_

- `agent-shield` - 安全审计：扫描配置漏洞、注入风险、MCP 安全问题。保护 Harness Foundry 免受提示注入、权限过度、Hook 注入等攻击。
- `ceo-orchestration` - CEO 角色主 Skill — 跨域协调入口，调用子 Skill 完成各项职责
- `find-skills` - Helps users discover and install agent skills when they ask questions
- `git-xywh` - 组织级 Git 工作流：三主干（main / test / develop）、五类临时分支、多环境隔离、Angular 提交与 MR 流程；涵盖合并、变基、冲突、恢复。任务涉及分支、提测、热修、版本标签、提交规范或 MR 时使用。
- `harness-health` - 系统健康度检查 Skill — 一键输出所有子系统的健康状态
- `playwright` - Browser automation via Playwright MCP. Navigate websites, click elements,
- `skill-vetter` - Security-first skill vetting for AI agents. Use before installing any
- `summarize` - Summarize URLs or files with the summarize CLI (web, PDFs, images, audio,
- `two-stage-review` - 两阶段审查：先验证 Spec 合规，再检查代码质量。code 域实现完成后使用。

### 代码基线

_Karpathy 准则、编码基线_

- `karpathy-guidelines` - 写代码、审查代码、重构代码时的行为准则：先想再写、保持简单、只改必要的，目标驱动。code 域默认基线，P0 优先级。

### 前端/UI 设计

_网页设计规范、设计指南_

- `web-design-guidelines` - 网页设计规范和最佳实践指南

### 代码智能

_图谱查询、LSP、ripgrep、影响分析_

- `analyze-architecture` - 深入分析项目架构，回答架构相关问题。触发：询问设计原因、技术选型、模块职责、架构决策。
- `analyze-impact` - 评估代码变更的影响范围。触发：重构前、修改核心方法、批量修改前。
- `code-insight-stack` - 编排 codebase-memory + ripgrep + LSP 三层查询栈，按场景选择最便宜的工具组合。触发：探索陌生代码库、定位修改点、调查 bug、准备 refactor、计划实现、跨文件影响分析。
- `get-callees` - 获取指定符号调用的所有代码。触发：想知道某个方法内部调用了什么、分析实现细节。
- `get-callers` - 获取调用指定符号的所有代码。触发：想知道谁在调用某个方法、分析依赖、评估影响。
- `index-project` - 为项目建立代码索引。触发：大型项目、需要精准定位符号、快速查找调用关系。
- `query-knowledge-graph` - 查询 codebase-memory-mcp 的知识图谱，获取结构化信息。触发：需要查询项目结构、模块关系、依赖关系。
- `query-symbol` - 快速定位代码符号（类/函数/变量）。触发：需要找某个符号、不知道在哪里、查询定义。
- `understand-project` - 理解项目结构和架构，生成知识图谱。触发：接手新项目、需要了解项目全局、询问架构设计。

### 语言服务器

_LSP 查询、定义引用_

- `lsp-query` - 通过 Language Server Protocol（typescript-language-server / pyright / gopls 等）做结构化代码查询：定义、引用、悬停信息、符号、代码诊断。触发：找定义、找引用、找类型、看类型签名、go to definition、find references、hover、diagnostics、rename、检查类型错误。

### 性能优化

_上下文压缩、Token 优化_

- `auto-compact` - 智能上下文压缩：在最佳时机触发压缩，保留关键状态，清理冗余上下文。

### 代码搜索

_ripgrep 搜索、定位_

- `ripgrep-search` - 使用 ripgrep（rg）做高速文本搜索，定位引用、字符串、关键字。触发：grep、find、搜索文本、定位字符串、查找引用、查找 TODO/FIXME、查找实现、查找日志、搜索代码。

### 新闻生产

_生成、润色、发布_

- `news-generator` - 新闻写作技能包：根据热点/素材生成新闻稿件
- `news-polish` - 新闻稿件润色技能：去AI味、提升可读性、专业化表达

### 小说分析

_写作指标、进度追踪_

- `novel-improver` - 双平台长篇改良：10维评分 + 13项硬指标 + 结构性改写
- `novel-metrics` - 写作指标追踪，统计字数、速度、质量趋势

### 小说基线

_写作前准则、自查、返修_

- `novel-debug` - 情节矛盾/角色冲突/伏笔遗漏排查与修复
- `novel-guidelines` - 小说写作前思维基线：AI 陷阱 + 简洁原则。写章节/大纲/续写前必须加载
- `novel-protocol` - 渐进式披露路由 + 因果链一致性（入口层，省 76% token）
- `novel-safe-revision` - 安全返修流程：小步返修、逐次确认、保留历史版本
- `novel-simplify` - 章节自查简洁度检查，识别冗余、重复、堆砌问题

### 批量写作

_批量章节写作_

- `novel-batch-write` - 批量写作模式，当用户说写到第N章时触发，自动并行/串行写作

### 小说上下文

_角色/世界观/时间线一致性_

- `novel-contexts` - 小说上下文管理，维护角色设定、世界观、时间线的全局一致性

### 小说仪表板

_进度仪表板_

- `novel-dashboard` - 小说进度仪表板，显示当前书籍状态、章节进度、人物和伏笔状态

### 一致性核查

_法医式连续性检查_

- `novel-guardian` - 法医式事实核查 Agent，专门检查角色/时间线/世界观/情节的连续性

### 小说初始化

_新书创建向导_

- `novel-init` - 新书创作向导，帮助用户从零开始创建小说项目

### 小说编排

_全链路调度、阶段门禁_

- `novel-orchestrator` - 小说创作总控调度器，协调 writer→planner→reviewer→humanizer→editor→memory-keeper 全链路，管理阶段门禁和返修闭环

### 情节结构

_伏笔 DAG、节拍_

- `novel-foreshadowing-dag` - 伏笔有向无环图管理，结构化管理和追踪所有伏笔的埋设、触发和回收

### 写作进度

_检查点、进度管理_

- `novel-checkpoint` - 创建、验证写作进度检查点，确保批量写作不丢失上下文

### 质量评分

_确定性评分、机械评分_

- `novel-mechanical-scorer` - 无LLM的确定性章节质量评分器，在LLM审稿前做纯规则检查

### 快速写作

_单章快速写作_

- `novel-quick-write` - 快速单章写作，无需完整编排流程，适用于写第X章类型的简单写作任务

### 会话恢复

_中断恢复、上下文恢复_

- `novel-recovery` - 会话恢复工具，恢复中断的写作任务和上下文

### 小说审稿

_评估、接收反馈_

- `novel-evaluator` - 7维量化小说评分系统，基于情节/人物/文笔/世界观/情感/创新/钩子进行质量审查，联动63条陷阱检测，逐条引用原文举证
- `novel-receiving-review` - 接收审稿反馈，正确处理修改建议，不是盲目接受或机械执行

### 人物声音

_角色语言指纹_

- `novel-voice-profile` - 人物声音档案，为每个角色建立独特的语言指纹和说话风格

---

_本文件由脚本自动生成，请勿手改。如需修改分类，请编辑 `skills/categories.yaml`；如需修改 skill 描述，请编辑 `SKILL.md` 的 frontmatter 或 `_meta.json` 的 `purpose` 字段。_
