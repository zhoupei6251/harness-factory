# Skill Index

Auto-generated. Re-run with: npm run index
Total: 36 active + 17 archived = 53 skills

## Active (36)

| Skill | Description |
|-------|-------------|
| add-platform | Add a new platform adapter to harness-factory. Walks through platforms/<plat>/rules/ENTRY.md creatio |
| add-route | Add a new route (vertical domain) to harness-factory. Walks through routes/<route>/MEMORY.md creatio |
| add-skill | Add a new skill to harness-factory. Walks through SKILL.md + _meta.json creation, schema validation, |
| agent-browser | Browser automation for AI agents via inference.sh. Navigate web pages, |
| analyze-architecture | 深入分析项目架构，回答架构相关问题。触发：询问设计原因、技术选型、模块职责、架构决策。 |
| analyze-impact | 评估代码变更的影响范围。触发：重构前、修改核心方法、批量修改前。 |
| architecture-patterns | ## WHAT |
| brainstorming | You MUST use this before any creative work - creating features, building |
| code-review | Systematic code review patterns covering security, performance, maintainability, |
| fact-check | 事实核查 skill，对新闻内容进行多源交叉验证 |
| find-skills | Helps users discover and install agent skills when they ask questions |
| get-callees | 获取指定符号调用的所有代码。触发：想知道某个方法内部调用了什么、分析实现细节。 |
| get-callers | 获取调用指定符号的所有代码。触发：想知道谁在调用某个方法、分析依赖、评估影响。 |
| git-xywh | 组织级 Git 工作流：三主干（main / test / develop）、五类临时分支、多环境隔离、Angular 提交与 MR 流程；涵盖合并、变基、冲突、恢复。任务涉及分支、提测、热修、版本标 |
| harness-health | 系统健康度检查 Skill — 一键输出所有子系统的健康状态 |
| humanizer | Remove signs of AI-generated writing from text. Use when editing or reviewing |
| humanizer-zh | 中文 AI 文风清洗，消除 AI 生成特征，去套路化，句式重构，人物声音分化 |
| index-project | 为项目建立代码索引。触发：大型项目、需要精准定位符号、快速查找调用关系。 |
| lsp-query | 通过 Language Server Protocol（typescript-language-server / pyright / gopls 等）做结构化代码查询：定义、引用、悬停信息、符号、代码 |
| news-generator | 新闻写作技能包：根据热点/素材生成新闻稿件 |
| news-polish | 新闻稿件润色技能：去AI味、提升可读性、专业化表达 |
| planning-with-files | Implements Manus-style file-based planning to organize and track progress |
| playwright | Browser automation via Playwright MCP. Navigate websites, click elements, |
| project-planner | Triage ideas, problems, and feature requests into the right format |
| query-knowledge-graph | 查询 codebase-memory-mcp 的知识图谱，获取结构化信息。触发：需要查询项目结构、模块关系、依赖关系。 |
| query-symbol | 快速定位代码符号（类/函数/变量）。触发：需要找某个符号、不知道在哪里、查询定义。 |
| receiving-code-review | 根据独立审查者的反馈修改代码。 |
| refactor-safely | Plans and executes safe refactors with small steps, tests, and rollback |
| requesting-code-review | Use when completing tasks, implementing major features, or before merging |
| ripgrep-search | 使用 ripgrep（rg）做高速文本搜索，定位引用、字符串、关键字。触发：grep、find、搜索文本、定位字符串、查找引用、查找 TODO/FIXME、查找实现、查找日志、搜索代码。 |
| self-improving | Self-reflection + Self-criticism + Self-learning + Self-organizing memory. |
| simplify | Refactor code for clarity, consistency, and maintainability without changing |
| skill-vetter | Security-first skill vetting for AI agents. Use before installing any |
| two-stage-review | 两阶段审查：先验证 Spec 合规，再检查代码质量。code 域实现完成后使用。 |
| understand-project | 理解项目结构和架构，生成知识图谱。触发：接手新项目、需要了解项目全局、询问架构设计。 |
| writing-plans | Use when you have a spec or requirements for a multi-step task, before |

## Archived (17)

> Not in active use. Restore via: `git mv skills/archive/<name> skills/<name>`

| Skill | Description |
|-------|-------------|
| archive/agent-shield | 安全审计：扫描配置漏洞、注入风险、MCP 安全问题。保护 Harness Foundry 免受提示注入、权限过度、Hook 注入等攻击。 |
| archive/auto-compact | 智能上下文压缩：在最佳时机触发压缩，保留关键状态，清理冗余上下文。 |
| archive/backend-doc-generator | 生成标准后端技术文档，包含Mermaid流程图、时序图、类图、状态图。Invoke when user needs to create backend |
| archive/ceo-orchestration | CEO 角色主 Skill — 跨域协调入口，调用子 Skill 完成各项职责 |
| archive/code-insight-stack | 编排 codebase-memory + ripgrep + LSP 三层查询栈，按场景选择最便宜的工具组合。触发：探索陌生代码库、定位修改点、调查 bug、准备 refactor、计划实现、跨文件影 |
| archive/cursor-orchestration | Cursor 多 subagent 并行编排，等价于 omx ultrawork。在用户已批准 plan 并说「开始实现」后，通过 harness-coder（代码）、harness-implemen |
| archive/document-review | Systematic document review with type-specific rules. **Environment preparation** |
| archive/frontend-design | Create distinctive, production-grade frontend interfaces with high design |
| archive/karpathy-guidelines | 写代码、审查代码、重构代码时的行为准则：先想再写、保持简单、只改必要的，目标驱动。code 域默认基线，P0 优先级。 |
| archive/memory-manager | 通用项目记忆管理引擎，双域（code/news）共用架构，域隔离，状态机追踪，Agent 交接压缩协议 |
| archive/prompt-engineering-expert | Advanced expert in prompt engineering, custom instructions design, and |
| archive/security-auditor | Use when reviewing code for security vulnerabilities, implementing authentication |
| archive/summarize | Summarize URLs or files with the summarize CLI (web, PDFs, images, audio, |
| archive/superdesign | Expert frontend design guidelines for creating beautiful, modern UIs. |
| archive/ui-ux-pro-max | UI/UX design intelligence and implementation guidance for building polished |
| archive/web-design-guidelines | 网页设计规范和最佳实践指南 |
| archive/web-tools-guide | Web 工具使用指南：搜索、网页抓取、浏览器自动化。触发：查资料、上网、搜索、打开网站。 |
