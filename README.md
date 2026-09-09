# Harness Factory

Clean skeleton for shipping harness rules to 4 AI platforms (Claude / Codex / Trae / WorkBuddy) across 3 routes (code / novel / news).

## Why

`harness-foundry` (1290 files) was too heavy. `harness-kit` (skeleton only) lacked platform adapters. `harness-factory` is the middle ground: ~30 source files, TypeScript only, empty placeholders for everything that isn't governance or bootstrap.

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
├── capabilities/             # 10 empty verticals (fill on demand)
├── platforms/                # 4 adapters with per-platform rules
├── routes/                   # 3 route templates
├── skills/                   # add-skill, add-platform, add-route
├── schemas/                  # 3 JSON schemas
├── scripts/bootstrap.ts      # projects canonical to platform format
└── tests/
    ├── validate-schemas.ts
    └── bootstrap.test.ts
```

## How to add things

| Want to add | Read |
|---|---|
| A skill | `skills/add-skill/SKILL.md` |
| A platform (Cursor, Copilot, etc.) | `skills/add-platform/SKILL.md` |
| A route (podcast, video, etc.) | `skills/add-route/SKILL.md` |
| A capability doc | Just write `capabilities/<name>/SKILL.md` |

## npm scripts

- `npm run bootstrap -- --platform X --route Y` — project canonical to platform format
- `npm run validate` — schema + skill check
- `npm run typecheck` — TypeScript type check
- `npm test` — runs both validate and bootstrap smoke test
