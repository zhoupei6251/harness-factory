# WorkBuddy platform rules

> Add WorkBuddy-specific deltas here. Loaded after the canonical core/ENTRY.md.

## Hooks

WorkBuddy has its own `hooks/` system. Trust model: **approval via `mcp-approvals.json`**.

## MCP

MCP servers in `.codebuddy/mcp.json` (i.e., `~/.codebuddy/mcp.json`).

## Agents

WorkBuddy treats agents as first-class. Export canonical agents to `~/.codebuddy/agents/`.

## Tooling（本端接入）

> 代码域强制：改 TS / 脚本 / 测试 / 配置 / 规则文件前，先用 codebase-memory-mcp 取证据（R1）、生成前走 ponytail 决策阶梯（R2 / R8）。纯文案产出豁免。
> 工具缺失或未接通时改用等效手段（Read / Grep），并在回复中声明：
> `[codebase-memory-mcp 不可用，已降级] 原因：<未装 / MCP 未连通 / 索引缺失>；替代手段：<Read / Grep 手工取证>`

- **ponytail**：WorkBuddy 无插件系统 → 装为 skill（上游 `skills/ponytail/SKILL.md`）或复制上游 `AGENTS.md` 精简版进项目规则；纯指令约束、无 hook 强制，属能力差异不算降级
- **codebase-memory-mcp**：MCP server 写进 `.codebuddy/mcp.json`（即 `~/.codebuddy/mcp.json`）
- **验证**：规则版新会话问「阶梯当前档位」有回答；skill 版 `/ponytail-help` 有输出；`list_projects` 能返回

## Projected to

- `.codebuddy/rules/ENTRY.md` (this file)
- `.codebuddy/rules/ROOT.md` (canonical ENTRY.md)
- `.codebuddy/rules/project_rules.md` (native entry, generated from canonical + this delta)
