---
name: harness-factory
description: "Harness Factory unified entry: behavior rules for all 4 platforms."
tags: [Rules, Runbook]
---

# ENTRY.md - Harness Factory unified entry

> One file, all platforms. Claude / Codex / Trae / WorkBuddy share this as the single source of truth.

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
| `novel` | `routes/novel/MEMORY.md` + `capabilities/rules/` | `./MEMORY.md` |
| `news` | `routes/news/MEMORY.md` + `capabilities/rules/` | `./MEMORY.md` |

## Platform mapping

| Platform | Config root | Source |
|----------|------------|--------|
| Claude Code | `~/.claude/` | `platforms/claude/` |
| Codex | `./AGENTS.md` + `~/.codex/` | `platforms/codex/` |
| Trae | `~/.trae/` | `platforms/trae/` |
| WorkBuddy | `~/.codebuddy/` | `platforms/workbuddy/` |
