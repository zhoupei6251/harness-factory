# Skill Index

Auto-generated. Total: 87 skills.

| Skill | Description |
|-------|-------------|
| add-platform | Add a new platform adapter to harness-factory. Walks through platforms/<plat>/rules/ENTRY.md creatio |
| add-route | Add a new route (vertical domain) to harness-factory. Walks through routes/<route>/MEMORY.md creatio |
| add-skill | Add a new skill to harness-factory. Walks through SKILL.md + _meta.json creation, schema validation, |
| agent-browser | Browser automation for AI agents via inference.sh. Navigate web pages, |
| agent-shield | 安全审计：扫描配置漏洞、注入风险、MCP 安全问题。保护 Harness Foundry 免受提示注入、权限过度、Hook 注入等攻击。 |
| analyze-architecture | 深入分析项目架构，回答架构相关问题。触发：询问设计原因、技术选型、模块职责、架构决策。 |
| analyze-impact | 评估代码变更的影响范围。触发：重构前、修改核心方法、批量修改前。 |
| architecture-patterns | ## WHAT |
| auto-compact | 智能上下文压缩：在最佳时机触发压缩，保留关键状态，清理冗余上下文。 |
| backend-doc-generator | 生成标准后端技术文档，包含Mermaid流程图、时序图、类图、状态图。Invoke when user needs to create backend |
| brainstorming | You MUST use this before any creative work - creating features, building |
| ceo-orchestration | CEO 角色主 Skill — 跨域协调入口，调用子 Skill 完成各项职责 |
| code-insight-stack | 编排 codebase-memory + ripgrep + LSP 三层查询栈，按场景选择最便宜的工具组合。触发：探索陌生代码库、定位修改点、调查 bug、准备 refactor、计划实现、跨文件影 |
| code-review | Systematic code review patterns covering security, performance, maintainability, |
| cursor-orchestration | Cursor 多 subagent 并行编排，等价于 omx ultrawork。在用户已批准 plan 并说「开始实现」后，通过 harness-coder（代码）、harness-implemen |
| document-review | Systematic document review with type-specific rules. **Environment preparation** |
| fact-check | 事实核查 skill，对新闻内容进行多源交叉验证 |
| fanqie | 用途与边界 |
| fanqie-novel-auto-publish | 番茄小说创作发布一条龙技能，整合 AI 创作与番茄发布，支持全自动批量上传、断点续传、错误重试、发布报告生成 |
| find-skills | Helps users discover and install agent skills when they ask questions |
| frontend-design | Create distinctive, production-grade frontend interfaces with high design |
| get-callees | 获取指定符号调用的所有代码。触发：想知道某个方法内部调用了什么、分析实现细节。 |
| get-callers | 获取调用指定符号的所有代码。触发：想知道谁在调用某个方法、分析依赖、评估影响。 |
| git-xywh | 组织级 Git 工作流：三主干（main / test / develop）、五类临时分支、多环境隔离、Angular 提交与 MR 流程；涵盖合并、变基、冲突、恢复。任务涉及分支、提测、热修、版本标 |
| harness-health | 系统健康度检查 Skill — 一键输出所有子系统的健康状态 |
| humanizer | Remove signs of AI-generated writing from text. Use when editing or reviewing |
| humanizer-zh | 中文 AI 文风清洗，消除 AI 生成特征，去套路化，句式重构，人物声音分化 |
| index-project | 为项目建立代码索引。触发：大型项目、需要精准定位符号、快速查找调用关系。 |
| inkos | Autonomous novel writing CLI agent with web workbench (InkOS Studio) |
| junli-ai-novel | 长篇网文核心写作引擎，支持章节续写、扩写、重写，维护人物状态和伏笔追踪 |
| karpathy-guidelines | 写代码、审查代码、重构代码时的行为准则：先想再写、保持简单、只改必要的，目标驱动。code 域默认基线，P0 优先级。 |
| lsp-query | 通过 Language Server Protocol（typescript-language-server / pyright / gopls 等）做结构化代码查询：定义、引用、悬停信息、符号、代码 |
| memory-manager | 通用项目记忆管理引擎，三域（code/novel/news）共用架构，域隔离，状态机追踪，Agent 交接压缩协议 |
| news-generator | 新闻写作技能包：根据热点/素材生成新闻稿件 |
| news-polish | 新闻稿件润色技能：去AI味、提升可读性、专业化表达 |
| novel-36-beats | 结构化节拍写作框架，基于 The Crucible Writing System 的 36-beat 三幕式结构，为长篇网文提供完整的情节骨架与节奏控制指南 |
| novel-ai-wash | 深度文风清洗引擎，四层清洗体系（词级→句式→叙事→人物声音），用于批量深度去AI味，与humanizer-zh互补 |
| novel-batch-write | 批量写作模式，当用户说"写到第N章"时触发，自动并行/串行写作 |
| novel-checkpoint | 创建、验证写作进度检查点，确保批量写作不丢失上下文 |
| novel-contexts | 小说上下文管理，维护角色设定、世界观、时间线的全局一致性 |
| novel-dashboard | 小说进度仪表板，显示当前书籍状态、章节进度、人物和伏笔状态 |
| novel-debug | 情节排查：角色矛盾/伏笔遗漏/节奏失控。发现问题后加载。 |
| novel-evaluator | 7维量化小说评分系统，基于情节/人物/文笔/世界观/情感/创新/钩子进行质量审查，联动63条陷阱检测，逐条引用原文举证 |
| novel-foreshadowing-dag | 伏笔有向无环图管理 — 借鉴 Openwrite 伏笔DAG系统，结构化管理和追踪所有伏笔的埋设、触发和回收 |
| novel-generator | 根据用户提供的内容方向自动生成提示词并创作爽文小说。适用场景：(1) 用户提供小说方向/题材/关键词，(2) 需要生成章节连贯的长篇爽文，(3) 需要维护角色、地点、情节的连续性 |
| novel-guardian | 法医式事实核查 Agent — 借鉴 Novel-OS Guardian，专门检查角色/时间线/世界观/情节的连续性 |
| novel-guidelines | 小说写作前思维基线：AI 陷阱 + 简洁原则。写章节/大纲/续写前必须加载。 |
| novel-improver | 双平台长篇改进skill。将长篇小说系统性地改良至番茄9.0+或起点精品标准。适用于：用户要求"改良小说"、"提升评分"、"去AI味"、"平台优化"、"让小说达到9.0+"等情况。覆盖多维度评审、结构 |
| novel-init | 新书创作向导，帮助用户从零开始创建小说项目 |
| novel-mechanical-scorer | 无LLM的确定性章节质量评分器 — 借鉴 autonovel (NousResearch) 机械评分器，在LLM审稿前做纯规则检查 |
| novel-metrics | 写作指标追踪，统计字数、速度、质量趋势 |
| novel-orchestrator | 小说创作总控调度器，协调 writer→planner→reviewer→humanizer→editor→memory-keeper 全链路，管理阶段门禁和返修闭环 |
| novel-protocol | 长篇网文写作协议——渐进式披露入口 + 因果链一致性强制。解决长篇小说两大痛点：(1) 全量加载 416KB novel 规则导致 token 浪费与注意力稀释；(2) 跨章世界观漂移、能力凭空出现、 |
| novel-quick-write | 快速单章写作，无需完整编排流程。适用于"写第X章"类型的简单写作任务 |
| novel-receiving-review | 接收审稿反馈，正确处理修改建议，不是盲目接受或机械执行 |
| novel-recovery | 会话恢复，当用户重新打开会话时恢复小说写作进度 |
| novel-safe-revision | 安全返修：审稿后小步修改，验证不破坏其他章节。 |
| novel-simplify | 章节自查：AI 痕迹/冗余/套路化。写后审稿前必须自查。 |
| novel-voice-profile | 为小说角色建立可复用的声音档案（Voice Profile），借鉴 ECC brand-voice 的 Source-First 方法论 |
| novel-writer-cn | 创建小说创作框架，包括人物设定、人物关系、剧情发展和多版本结局。Use when users ask to write novels, create story plots, design chara |
| piqie-writing | 番茄爆款写作技能（融合版）— 500章+350章两次长篇实战教训。快节奏爆款专项：3章一爽、平台算法适配、新人破零路径。触发场景：写番茄小说、写网文爆款、快节奏章节。 |
| planning-with-files | Implements Manus-style file-based planning to organize and track progress |
| playwright | Browser automation via Playwright MCP. Navigate websites, click elements, |
| project-planner | Triage ideas, problems, and feature requests into the right format: |
| prompt-engineering-expert | Advanced expert in prompt engineering, custom instructions design, and |
| qidian-writing | 起点中文网写作技能 — 慢热品质专项：设定硬、人物真、每章信息增量。基于《黑龙醒》前100章实战 + 起点读者行为分析。触发场景：写起点小说、慢热品质文、群像展开。 |
| query-knowledge-graph | 查询 codebase-memory-mcp 的知识图谱，获取结构化信息。触发：需要查询项目结构、模块关系、依赖关系。 |
| query-symbol | 快速定位代码符号（类/函数/变量）。触发：需要找某个符号、不知道在哪里、查询定义。 |
| receiving-code-review | 根据独立审查者的反馈修改代码。 |
| refactor-safely | Plans and executes safe refactors with small steps, tests, and rollback |
| requesting-code-review | Use when completing tasks, implementing major features, or before merging |
| ripgrep-search | 使用 ripgrep（rg）做高速文本搜索，定位引用、字符串、关键字。触发：grep、find、搜索文本、定位字符串、查找引用、查找 TODO/FIXME、查找实现、查找日志、搜索代码。 |
| security-auditor | Use when reviewing code for security vulnerabilities, implementing authentication |
| self-improving | Self-reflection + Self-criticism + Self-learning + Self-organizing memory. |
| simplify | Refactor code for clarity, consistency, and maintainability without changing |
| skill-vetter | Security-first skill vetting for AI agents. Use before installing any |
| summarize | Summarize URLs or files with the summarize CLI (web, PDFs, images, audio, |
| superdesign | Expert frontend design guidelines for creating beautiful, modern UIs. |
| two-stage-review | 两阶段审查：先验证 Spec 合规，再检查代码质量。code 域实现完成后使用。 |
| ui-ux-pro-max | UI/UX design intelligence and implementation guidance for building polished |
| understand-project | 理解项目结构和架构，生成知识图谱。触发：接手新项目、需要了解项目全局、询问架构设计。 |
| web-design-guidelines | 网页设计规范和最佳实践指南 |
| web-novel-publishing-readiness-and-quality-check-skill | 小说质量检查技能。触发关键词：检查正文、质量报告、违禁词、套路句、章节衔接、逻辑漏洞、自检、人写感、大纲、人设。执行最大算力深度推理五步链，每章必须跑freq_check.py词频扫描+逐行违禁词扫描 |
| web-tools-guide | Web 工具使用指南：搜索、网页抓取、浏览器自动化。触发：查资料、上网、搜索、打开网站。 |
| writing-novel | 长篇小说写作skill。从500+章实战中提炼的全流程方法论。覆盖大纲设计、逐章写作、质量控制、平台优化、AI味消除。适用于番茄小说等网文平台。触发场景：写小说、写网文、写章节、设计大纲、做人物设定。 |
| writing-plans | Use when you have a spec or requirements for a multi-step task, before |
| zhi-dou-writing | 智斗小说专属写作技能。融合《第九特区》《犯上者》《诡秘之主》《赘婿》等顶级智斗作品的创作精华，专注于写出有真人感、高智商博弈、强情绪节奏的智斗/权谋小说。触发场景：写智斗小说、写权谋文、写高智商对抗、 |
