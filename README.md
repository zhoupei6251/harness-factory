# Harness Factory

Clean skeleton for shipping harness rules to 4 AI platforms (Claude / Codex / Trae / WorkBuddy) across 2 routes (code / news).

## Why

`harness-foundry` (1290 files) was too heavy. `harness-kit` (skeleton only) lacked platform adapters. `harness-factory` is the middle ground: ~270 source files, TypeScript only, no placeholders for things that aren't governance, bootstrap, or skills.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the design rationale.

## Quick start (5 minutes)

```bash
npm install
npm run typecheck   # tsc --noEmit
npm run validate    # check schemas + skills
npm run bootstrap -- --platform all --route code
```

This projects `core/ENTRY.md` and `platforms/<plat>/rules/ENTRY.md` to `.claude/`, `.codex/`, `.trae/`, `.codebuddy/`, creates runtime dirs, and writes `./MEMORY.md` from the route template.

## Layout

```
harness-factory/
├── ENTRY.md                  # single entry point
├── LICENSE
├── README.md
├── ARCHITECTURE.md           # design rationale
├── package.json
├── tsconfig.json
├── core/                     # 8 governance docs (always loaded)
├── capabilities/rules/       # per-language rules (java / typescript / common)
├── platforms/                # 4 adapters with per-platform rules
├── routes/                   # 2 route templates (code / news)
├── skills/                   # active skills (in use) + skills/archive/ (restorable on demand)
├── schemas/                  # 3 JSON schemas
├── scripts/bootstrap.ts      # projects canonical to platform format
└── tests/
    ├── validate-schemas.ts
    ├── build-index.ts
    └── bootstrap.test.ts
```

## How to add things

| Want to add | Read |
|---|---|
| A skill | `skills/add-skill/SKILL.md` |
| A platform (Cursor, Copilot, etc.) | `skills/add-platform/SKILL.md` |
| A route (podcast, video, etc.) | `skills/add-route/SKILL.md` |
| A language rule | Just add a file under `capabilities/rules/<lang>/` |

Skills are split into two tiers:

- **`skills/`** — active, in use (code workflow, codebase tools, news, meta).
- **`skills/archive/`** — not in use, kept restorable. Enable one: `git mv skills/archive/<name> skills/<name> && npm run index`.

## npm scripts

- `npm run bootstrap -- --platform X --route Y` — project canonical to platform format
- `npm run validate` — schema + skill check
- `npm run index` — regenerate `skills/INDEX.md`
- `npm run typecheck` — TypeScript type check
- `npm test` — runs validate + typecheck + bootstrap smoke test
