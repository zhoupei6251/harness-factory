# Claude Code platform rules

> Add Claude-specific deltas here. Loaded after the canonical core/ENTRY.md.

## Hooks

Claude uses `.claude/settings.json` for hooks. Trust model: **explicit** (you approve once).

## MCP

Add Claude-specific MCP servers in `.mcp.json` (or use a shared `core/intelligence/mcp/`).

## Tooling（本端接入）

> 代码域强制：改 TS / 脚本 / 测试 / 配置 / 规则文件前，先用 codebase-memory-mcp 取证据（R1）、生成前走 ponytail 决策阶梯（R2 / R8）。纯文案产出豁免。
> 工具缺失或未接通时改用等效手段（Read / Grep），并在回复中声明：
> `[codebase-memory-mcp 不可用，已降级] 原因：<未装 / MCP 未连通 / 索引缺失>；替代手段：<Read / Grep 手工取证>`

- **ponytail**：会话内 `/plugin marketplace add DietrichGebert/ponytail` → `/plugin install ponytail@ponytail`（两次独立确认）
- **codebase-memory-mcp**：根 `.mcp.json` 已提交，首次打开接受启用提示即可
- **验证**：`/ponytail-help` 有输出；让 Agent 调 `list_projects` 能返回

## Projected to

- `.claude/rules/ENTRY.md` (this file)
- `.claude/rules/ROOT.md` (canonical ENTRY.md)
- `CLAUDE.md` (native auto-loaded entry, generated from canonical + this delta)
