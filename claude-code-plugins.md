# Claude Code 插件清单

来源：`~/.claude/plugins/installed_plugins.json` + `known_marketplaces.json`（2026-08-21 快照）。

## 已装插件（10 个）

`★` = 核心（本项目日常工作流依赖，务必装）；`○` = 可选（按需）。

| 插件 | Marketplace | 版本 | 级别 | 用途 |
|---|---|---|---|---|
| ponytail | ponytail | 4.9.0 | ★ | 懒惰阶梯：写代码默认极简（YAGNI / 复用 / 一行优先），全程生效 |
| superpowers | claude-plugins-official | 6.3.0 | ★ | harness 流程核心 skill 集：brainstorming / writing-plans / verification-before-completion / requesting-code-review 等 |
| context7 | claude-plugins-official | — | ★ | 新库 / 新 API 文档查询（工具纪律：新库 API 用它） |
| playwright | claude-plugins-official | — | ★ | 接口 / 浏览器自动化测试（测试接口时用它） |
| github | claude-plugins-official | — | ★ | GitHub 仓库 / PR / Issue 操作 |
| mattpocock-skills | claude-plugins-official | 1.2.3 | ★ | tdd / prototype / research / domain-modeling / grilling 等 TypeScript 向技能集 |
| firecrawl | claude-plugins-official | 1.0.9 | ○ | 网页抓取 / 搜索（MCP 同名服务也在用） |
| minimax-skills | minimax-skills | 1.0.0 | ○ | MiniMax 官方技能包 |
| ecc | ecc | 2.0.0 | ○ | 增强命令集（user + project 双 scope 装过）— **2026-09 降级为可选；本地 `agents/ecc-*.md` 兜底** |
| andrej-karpathy-skills | karpathy-skills | 1.0.0 | ○ | Karpathy 编码行为准则（先想后写、简单优先、精准修改、目标驱动） |

## Marketplace 源（6 个）

| Marketplace 名 | 源 | 注册命令 |
|---|---|---|
| claude-plugins-official | anthropics/claude-plugins-official | 内置，无需注册 |
| ponytail | DietrichGebert/ponytail | `claude plugin marketplace add DietrichGebert/ponytail` |
| minimax-skills | MiniMax-AI/skills | `claude plugin marketplace add https://github.com/MiniMax-AI/skills.git` |
| ecc | affaan-m/ECC | `claude plugin marketplace add https://github.com/affaan-m/ECC.git` |
| anthropic-agent-skills | anthropics/skills | `claude plugin marketplace add anthropics/skills`（marketplace 级技能如 `claude-api` 随注册生效） |
| karpathy-skills | multica-ai/andrej-karpathy-skills | `claude plugin marketplace add multica-ai/andrej-karpathy-skills` |

## 手动恢复命令

完整恢复命令见 [`restore-claude-plugins.sh`](restore-claude-plugins.sh)（一键脚本，单一来源）；下面仅展示市场/插件摘要：

| 类别 | 数量 | 说明 |
|------|------|------|
| 核心插件（★） | 7 | 必装，缺则流程降级 |
| 可选插件（○） | 3 | ecc 已降级，缺失走 `agents/ecc-*.md` 兜底 |

## 备注

- **ecc** 此前同时装了 user 和 project scope（projectPath 为 `C:\Users\zhoupei`），换机时 user scope 即可。
- **anthropic-skills:*** 命名空间的技能来自 anthropic-agent-skills marketplace 注册，无需单独 install 即可用（如 `claude-api` 参考）。
- 插件安装到用户级（`~/.claude/plugins/`），所有项目生效。
- 安装后需重启会话，技能列表才会刷新。
