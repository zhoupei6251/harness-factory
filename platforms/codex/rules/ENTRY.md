# Codex platform rules

> Add Codex-specific deltas here. Loaded after the canonical core/ENTRY.md.

## Hooks

Codex uses `[hooks.state]` in `config.toml` with trusted hashes. Trust model: **explicit per hook** — run `/hooks` to approve.

## MCP

MCP servers live in `[mcp_servers.*]` of `~/.codex/config.toml` (Codex does not read project `.mcp.json`). See `mcp-config/codebase-memory.codex.toml` for a ready-made snippet.

## Skills

Codex discovers skills in `~/.codex/skills/`. Install repo skills with `npm run skills:install` (junctions to `skills/`, edits are live).

## Tooling（本端接入）

> 代码域强制：改 TS / 脚本 / 测试 / 配置 / 规则文件前，先用 codebase-memory-mcp 取证据（R1）、生成前走 ponytail 决策阶梯（R2 / R8）。纯文案产出豁免。
> 工具缺失或未接通时改用等效手段（Read / Grep），并在回复中声明：
> `[codebase-memory-mcp 不可用，已降级] 原因：<未装 / MCP 未连通 / 索引缺失>；替代手段：<Read / Grep 手工取证>`

- **ponytail**：`codex plugin marketplace add DietrichGebert/ponytail` → `codex plugin add ponytail@ponytail`，再开 `/hooks` 信任它的两个 lifecycle hook，然后新起线程
- **codebase-memory-mcp**：把 `mcp-config/codebase-memory.codex.toml` 并入 `~/.codex/config.toml`
- **验证**：`/ponytail-help` 有输出；让 Agent 调 `list_projects` 能返回

## Projected to

- `.codex/rules/ENTRY.md` (this file)
- `.codex/rules/ROOT.md` (canonical ENTRY.md)
- `AGENTS.md` (native auto-loaded entry, generated from canonical + this delta)
