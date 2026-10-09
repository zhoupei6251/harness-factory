---
name: harness-factory
description: "Harness Factory unified entry: behavior rules for all 5 platforms."
tags: [Rules, Runbook]
---

# ENTRY.md - Harness Factory unified entry

> One file, all platforms. Claude / Codex / Trae / WorkBuddy / Qoder share this as the single source of truth.

## Load priority

1. **This file** - behavior rules (all platforms mandatory)
2. `core/ENTRY.md` - 7 governance doc index
3. `core/intent-routing.md` - intent routing
4. `core/NEVER.md` - forbidden list (mandatory)

## Behavior rules (R1-R8)

| # | Rule | One-liner |
|---|------|-----------|
| R1 | Read before write | Never modify code you have not read |
| R2 | Keep it simple | If 200 lines can be 50, rewrite |
| R3 | Surgical edits | Touch only what needs touching |
| R4 | Goal-driven | Define pass criteria before coding |
| R5 | Tool first | Use tools, do not shell-around |
| R6 | No silent failures | Raise errors, do not swallow |
| R7 | Surface conflicts | State contradictions immediately |
| R8 | No over-engineering | Abstract only on the second occurrence |

## Routes

| Route | Load | Project to |
|-------|------|-----------|
| `code` | `routes/code/MEMORY.md` + `capabilities/rules/` | `./MEMORY.md` |
| `novel` | `routes/novel/MEMORY.md` | `./MEMORY.md` |
| `news` | `routes/news/MEMORY.md` + `capabilities/rules/` | `./MEMORY.md` |

## Platform mapping

| Platform | Config root | Source |
|----------|------------|--------|
| Claude Code | `~/.claude/` | `platforms/claude/` |
| Codex | `./AGENTS.md` + `~/.codex/` | `platforms/codex/` |
| Trae | `~/.trae/` | `platforms/trae/` |
| WorkBuddy | `~/.codebuddy/` | `platforms/workbuddy/` |
| Qoder | `./AGENTS.md` + `~/.qoder/` + `~/.qoder-cn/` | `platforms/qoder/` |

## Tooling (required — 代码域强制)

> 两工具是代码域开发的**执行方式**，不是可选附件。
> 适用范围：改 TS / 脚本 / 测试 / 配置 / 规则文件。豁免：纯文案产出（novel / news 稿件）。
> 降级语义：工具未装或未接通时，改用等效手段（Read / Grep），并**在回复中声明降级原因**；禁止默默跳过或假装已用。

| Tool | 绑定规则 | 必须这样做 | Install |
|------|---------|-----------|---------|
| codebase-memory-mcp | R1 | 改代码前用 `analyze-impact` / `get-callers` / `query-symbol` 拿图谱证据 | 根 `.mcp.json` 或 `references/tooling.md` |
| ponytail | R2 / R8 | 生成前走七级决策阶梯（不写→复用→库→原生→依赖→一行→最小实现） | `references/tooling.md` |
