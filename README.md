# Harness Factory

Single source of truth for harness rules across 4 AI platforms (Claude / Codex / Trae / WorkBuddy) and 3 routes (code / novel / news). Replaces `harness-foundry` (retired: too heavy) and `harness-kit` (retired: machinery merged here).

## Core idea: one shared set + thin platform shims

All platforms consume the **same canonical content** (`core/`, `routes/`, `skills/`, `artifact-templates/`). Per-platform output is a thin stub that references the shared files — no content duplication, no drift. Platform-specific deltas live in `platforms/<plat>/rules/ENTRY.md` and override the canonical entry.

## Quick start (5 minutes)

```bash
npm install
npm run typecheck   # tsc --noEmit
npm run validate    # check schemas + skills
npm run bootstrap -- --platform all --route code --target <your project root>
```

Shim mode (default) writes thin stubs into `<target>/.claude/`, `.codex/`, `.trae/`, `.codebuddy/` referencing this factory, creates runtime dirs, and seeds `MEMORY.md` from the route template (never clobbers an existing one). Use `--mode copy` for the legacy full-copy behavior.

## Layout

```
harness-factory/
├── ENTRY.md                  # single entry point
├── ARCHITECTURE.md           # design rationale
├── project.profile.md        # project instance: identity, stack, module map
├── project.git.md            # project instance: git deltas vs org baseline
├── project.verification.md   # project instance: verification commands
├── core/                     # governance: routing (阶段门禁/路由表), runbooks,
│   ├── ...                   # artifacts/verification contracts, orchestration/
│   └── orchestration/        # multi-task dispatch: WU, DISPATCH-TRACK, roles
├── artifact-templates/       # spec/plan/decision/collective-test/code-review overlays
├── capabilities/rules/       # per-language rules (java, typescript, common)
├── platforms/                # 4 thin adapters with per-platform rules
├── routes/                   # 3 route templates (code / novel / news)
├── skills/                   # active skills + skills/archive/ (restorable)
├── entrypoints/              # HARNESS-PLATFORM-ENTRY.md, AGENTS.omx.md
├── init/                     # onboarding prompts + instance templates
├── docs/superpowers/specs/   # authoritative workflow specs (尾盘, worktree isolation…)
├── schemas/                  # 3 JSON schemas
├── scripts/                  # bootstrap.ts + operational shell helpers
└── tests/                    # validate-schemas, build-index, bootstrap smoke
```

## How to add things

| Want to add | Read |
|---|---|
| A skill | `skills/add-skill/SKILL.md` |
| A platform (Cursor, Copilot, etc.) | `skills/add-platform/SKILL.md` |
| A route (podcast, video, etc.) | `skills/add-route/SKILL.md` |
| A capability doc | Just write `capabilities/<name>/SKILL.md` |

Skills are split into two tiers:

- **`skills/`** — active, in use (code workflow, codebase tools, news/writing, meta).
- **`skills/archive/`** — not in use, kept restorable. Enable one: `git mv skills/archive/<name> skills/<name> && npm run index`.

## npm scripts

- `npm run bootstrap -- --platform X --route Y [--mode shim|copy] [--target dir]` — project canonical to platform format
- `npm run validate` — schema + skill check (active + archive)
- `npm run typecheck` — TypeScript type check
- `npm run index` — regenerate `skills/INDEX.md` (Active + Archived sections)
- `npm test` — runs both validate and bootstrap smoke test
