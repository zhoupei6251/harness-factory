---
name: harness-factory
description: "Code-only Harness rules for Claude / Codex / Trae / WorkBuddy / Qoder."
tags: [Rules, Runbook]
---

# ENTRY.md - Harness Factory unified entry

Code is the only route. Keep the default path short: understand, implement, verify.

## Load once, then work

- Native entries already contain this file, the core index and platform deltas; do not re-read their source copies.
- Read `core/NEVER.md`, then use `core/intent-routing.md` for task-specific loading. Read each document/skill once per session unless it changes.
- Root `MEMORY.md` is project state. `routes/code/MEMORY.md` is an initialization template, not another state source.
- Load common rules and only the current language/task rules; hook/setup guides are for configuring hooks, not every edit.
- For frontend layout and styling, consult [references/frontend-design.md](references/frontend-design.md) on demand.

## Behavior rules (R1-R8)

| # | Rule | One-liner |
|---|------|-----------|
| R1 | Read before write | Read the code and relevant callers before editing |
| R2 | Keep it simple | Use the smallest complete solution |
| R3 | Surgical edits | Touch only the requested scope |
| R4 | Goal-driven | Define observable pass criteria |
| R5 | Tool first | Use purpose-built tools when available |
| R6 | No silent failures | Preserve validation and useful errors |
| R7 | Surface conflicts | Resolve material contradictions explicitly |
| R8 | No over-engineering | Reuse before adding abstraction |

## Execution

- A request to implement, fix or optimize authorizes work through relevant verification. Do not require a separate spec/plan approval for the same scope.
- Routine changes: brief intent, targeted evidence, direct implementation and relevant checks. No mandatory plan file, worktree, subagent or verification document.
- Complex or risky changes: keep one concise plan/evidence record, split independent work when useful, and request independent review for material risks.
- Ask only when a missing decision changes scope/behavior or the next action needs authorization. A request for a plan alone does not authorize implementation.
- Batch independent reads/checks. Run relevant tests after a coherent edit, not whole-project checks after every file. Repeat only after changes or failures that justify it.

## Tooling (required — 代码域强制)

Read installed `codebase-memory` and `ponytail` skills once on first coding work; ponytail defaults to `full`.

| Tool | Required use |
|------|--------------|
| codebase-memory-mcp | `list_projects` once; choose the exact project, locate relevant symbols with `search_graph`, trace changed contracts/callers as needed and read source. Check cited-path coverage; re-index only when needed, not at every task. |
| ponytail | Before generation: 不写 → 复用 → 标准库 → 平台原生 → 已有依赖 → 一行 → 最小实现. Keep boundary validation, error handling and accessibility. |

When graph tools are unavailable, use source reads and targeted searches and state:
`[codebase-memory-mcp 不可用，已降级] 原因：<实际错误>；替代手段：<源码读取与调用追踪>`。
Stale/missing graph coverage requires checking current source, not pretending the graph is complete. Setup details: [references/tooling.md](references/tooling.md).

## Platform mapping

| Platform | Config root | Source |
|----------|------------|--------|
| Claude Code | `~/.claude/` | `platforms/claude/` |
| Codex | `AGENTS.md` + `~/.codex/` | `platforms/codex/` |
| Trae | `~/.trae/` | `platforms/trae/` |
| WorkBuddy | `~/.codebuddy/` | `platforms/workbuddy/` |
| Qoder | `AGENTS.md` + `~/.qoder/` + `~/.qoder-cn/` | `platforms/qoder/` |

## Workflow (this repository only)

- Commit directly to `main`; do not create a worktree or feature branch for routine repository maintenance. Downstream projects retain their own Git policy.
- Push only when explicitly requested. Never force-push shared branches.
- Edit canonical files, then run `npm run bootstrap` to regenerate distributed entries. Bootstrap is local; run `npm run doctor` explicitly for environment diagnosis.
- Before commit, review the diff, run relevant checks and check `git status`; do not commit backups or runtime dumps.
