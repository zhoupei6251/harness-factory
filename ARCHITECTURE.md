# Architecture

## Why this exists

`harness-factory` is the single replacement for `harness-foundry` (retired: 1290 files, too heavy) and `harness-kit` (retired: workflow machinery merged here). Core idea: **one shared canonical set + thin platform shims** — all 4 platforms consume the same `core/` `routes/` `skills/` `artifact-templates/` content; per-platform output is a stub referencing this factory, so there is zero content duplication and zero drift.

## Current state (as of phase-6: kit machinery merged)

| Metric | Count |
|---|---|
| Core governance docs | 10 (`core/*.md`) + `core/orchestration/` dispatch subsystem |
| Artifact templates | 16 (`artifact-templates/`) |
| Platform adapters | 4 (claude, codex, trae, workbuddy) — thin delta rules |
| Routes | 3 (code, novel, news) — MEMORY templates; news wired to skill chain |
| Skills | 87 (37 active in `skills/` + 50 archived in `skills/archive/`, restorable) |
| Project instance files | 3 (`project.profile.md`, `project.git.md`, `project.verification.md`) |
| Entrypoints | `entrypoints/` (HARNESS-PLATFORM-ENTRY.md, AGENTS.omx.md) |
| MCP servers | 1 (codebase-memory only) |
| Capability verticals | 3 (java, typescript, common) |
| Schemas | 3 |
| npm scripts | 5 (bootstrap, validate, typecheck, index, test) |

## The layers

1. **Foundation**: `core/` — governance + routing（业务路线表、任务路由表、阶段门禁、Git 协作）+ runbooks（新功能/缺陷/决策/news 写作/尾盘）+ artifacts/verification 契约。
2. **Orchestration**: `core/orchestration/` — multi-task dispatch（WU 拆分、DISPATCH-TRACK、leader/coder/reviewer 角色、worktree 隔离、尾盘）。Platform-neutral: Codex 用 omx，Claude 用 claude-orchestration，Trae/WorkBuddy 用平台原生 subagent。
3. **Capabilities**: `capabilities/rules/{java,typescript,common}/` — per-language rules.
4. **Platforms**: `platforms/<name>/rules/ENTRY.md` — 4 thin adapters. Per-platform deltas.
5. **Routes**: `routes/<name>/MEMORY.md` — 3 vertical templates. Per-domain state.
6. **Skills**: `skills/<name>/SKILL.md` + `_meta.json` — 37 active; 50 unused live in `skills/archive/`.
7. **Instance files**: `project.{profile,git,verification}.md` — per-project facts, editable per repo.

## How a session works

```
session start
    |
    +-- read ENTRY.md (mandatory)
    +-- read core/NEVER.md (mandatory)
    +-- read core/routing.md (route 判定 + 阶段门禁, by intent)
    +-- read platform-specific rules (if platform set)
    +-- read route MEMORY.md (if route set)
    +-- read skills/<x>/SKILL.md (on trigger)
    |
    v
work  (spec -> plan -> implement -> verify, stage gates pause between)
    |
    +-- multi-task: core/orchestration/dispatcher-workflow.md (WU + 尾盘)
    +-- news route: news-generator -> fact-check -> news-polish -> humanizer-zh -> document-review
    |
    v
session end
```

## What was cut from foundry (and why)

| Cut | Was in | Ceiling | Upgrade path |
|---|---|---|---|
| 315-file Claude adapter mirror | harness-foundry | format drift | shim stubs regenerate via `npm run bootstrap` |
| 694 md files | harness-foundry | doc bloat | write on demand |
| bash + python build toolchain | harness-foundry | dual toolchain | TS only (small operational `.sh` helpers kept in `scripts/`) |
| 23 top-level dirs | harness-foundry | navigation cost | ~14 top-level items |
| 15+ unused MCP servers | harness-foundry's mcp-servers.json | none | add when actually used |

## What was merged from kit (phase-6)

- `core/routing.md`（阶段门禁/组合指令/小改动判定，平台列泛化为 4 平台）
- `core/artifacts.md`、`core/verification.md`、`core/harness.md`
- `core/runbooks.md`（新功能/缺陷/决策/Git/迁移 + factory 维护流程合并）
- `core/orchestration/`（dispatcher-workflow、agents 角色、tracking、skill-preferences）
- `artifact-templates/`（16 个产物契约模板）
- `entrypoints/`、`init/`（onboarding 话术、实例模板）、`docs/superpowers/specs/`（尾盘/worktree 权威 spec）
- `project.profile.md` / `project.git.md` / `project.verification.md` 实例位
- skills: `verification-before-completion`、`systematic-debugging`（自 `~/.agents/skills` 收编）；`document-review` 解档

Target: `harness-kit/` and `harness-foundry/` are empty / deletable.

## How to add things

- **Skill**: see `skills/add-skill/SKILL.md`
- **Platform**: see `skills/add-platform/SKILL.md`
- **Route**: see `skills/add-route/SKILL.md`
- **Language rule**: add file under `capabilities/rules/<lang>/` (e.g., `python/hooks.md`)

## Bootstrap contract

`scripts/bootstrap.ts` projects the canonical set to per-platform format:

| Canonical | Per-platform (shim mode, default) | Per-platform (copy mode) |
|-----------|-----------------------------------|--------------------------|
| `core/ENTRY.md` (or `platforms/<plat>/rules/ENTRY.md` if exists) | stub referencing the source of truth | full copy |
| `ENTRY.md` | stub referencing factory root entry | full copy |
| `routes/<route>/MEMORY.md` | seed only if absent (never clobbers) | overwrite |
| `<route>` runtime dirs | created under `--target` | same |

If `platforms/<plat>/rules/ENTRY.md` exists, it wins over canonical. This is how platform-specific deltas work.
