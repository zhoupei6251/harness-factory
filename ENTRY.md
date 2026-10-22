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
| `novel` **(archived)** | `routes/novel/MEMORY.md` — 归档件，不再自动装载 | `./MEMORY.md` 仅显式 `--route novel` |
| `news` **(archived)** | `routes/news/MEMORY.md` + `capabilities/rules/` — 归档件，不再自动装载 | `./MEMORY.md` 仅显式 `--route news` |

> **2026-10-22 退役中**：news 与 novel 两域整体迁往独立仓库 `D:\zhoupei\heron`（规格见其
> `docs/plans/2026-10-22-heron-news-webapp-design.md`，本仓库的域内件另有快照 `heron/reference/from-harness-factory/`）。
> 归档期内的口径：目录与脚本**此刻仍可运行**（它们还是 heron 的 oracle 与视觉尺子），但意图路由不再指向它们。
> 分两步退：先摘路由（本次），摘目录与 schema/投影/package 脚本另起一次提交，等新闻域在 heron 侧
> 用 `fixtures/` 对完账再做。详见 `core/intent-routing.md`。

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

## Workflow (this repository only)

> **This section describes how `harness-factory` itself is developed. It is NOT a rule for downstream projects** — they should follow `git-xywh` and the per-platform branching guidelines they receive via bootstrap.

- **Main-only Git workflow.** Since 2026-09-29 the harness-factory repo commits directly to `main`; no `task/*` / `feature/*` branches, no worktrees held open between sessions. Rationale: this repo is a *rule distribution* artifact, not a product codebase — every commit is a self-contained, easily-revertable ruleset change; merge conflicts are rare because most edits are in different subtrees. `git-xywh`'s three-trunk / five-branch model is **not relaxed for downstream projects**.
- **`push` requires explicit ask.** Even on `main`, `git push` is the user's call — don't push after commit unless the user said so.
- **Backups never committed.** `*.bak-*.md` is git-ignored; `npx tsx scripts/install-into-project.ts --target <path>` is the supported way to roll back a target project's harness install.
- **Hygiene gates before commit.** `git status` should show only files you intentionally touched; stray `*.bak-*` / `timing.json` / runtime dumps must be cleaned up. See `.gitignore` for the runtime pattern list.
