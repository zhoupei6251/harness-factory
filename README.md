# Harness Factory

Clean skeleton for shipping harness rules to 5 AI platforms (Claude / Codex / Trae / WorkBuddy / Qoder) across 3 routes (code / novel / news).

## Why

`harness-foundry` (1290 files) was too heavy. `harness-kit` (skeleton only) lacked platform adapters. `harness-factory` is the middle ground: ~270 source files, TypeScript only, no placeholders for things that aren't governance, bootstrap, or skills.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the design rationale.

## Quick start (5 minutes)

```bash
npm install
npm run typecheck   # TypeScript 7 native compiler
npm run validate    # check schemas + skills
npm run doctor      # verify required external tools (codebase-memory-mcp, ponytail) — bootstrap runs this automatically
npm run bootstrap -- --platform all --route code
npm run skills:install  # link skills into ~/.codex/skills + ~/.claude/skills + ~/.qoder/skills
```

This projects `core/ENTRY.md` and `platforms/<plat>/rules/ENTRY.md` to `.claude/`, `.codex/`, `.trae/`, `.codebuddy/`, `.qoder/`, creates runtime dirs, and writes `./MEMORY.md` from the route template. Codex and Qoder share one native entry (`AGENTS.md`); bootstrap merges both deltas instead of letting one overwrite the other.

## Toolchain

- **Node 20.9+ ~ 26+** — tested green on 20.9.0 and 26.8.2 (`engines: >=20.9.0`)
- **TypeScript 7** (Go-native compiler, ~10× faster typecheck). `npm run typecheck` calls `lib/tsc.js` directly: TS 7's `bin/tsc` launcher is an extensionless ESM file that Node <22 cannot load — calling the lib keeps the Node 20 floor
- **tsx** runs all TS scripts (bootstrap / validate / index / tests) — no build step, no Babel
- `tsconfig.json`: `erasableSyntaxOnly` (native-strip compatible) + `types: ["node"]` (TS 7 no longer auto-includes `@types/*`)

## Layout

```
harness-factory/
├── ENTRY.md                  # single entry point
├── LICENSE
├── README.md
├── ARCHITECTURE.md           # design rationale
├── .mcp.json                 # project-scoped MCP (codebase-memory), auto-offered by Claude Code
├── package.json
├── tsconfig.json
├── core/                     # 8 governance docs (always loaded)
├── capabilities/rules/       # per-language rules (java / typescript / common)
├── mcp-config/               # canonical MCP server snippets
├── platforms/                # 4 adapters with per-platform rules
├── references/               # traps.md + tooling.md (external tool setup)
├── routes/                   # 3 route templates (code / novel / news)
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
- `npm run skills:install` — symlink active skills into `~/.codex/skills/` and `~/.claude/skills/` so each platform can discover them
- `npm run doctor` — hard gate for required external tooling (Node >=20.9, `codebase-memory-mcp`, its Codex/Claude wiring, `ponytail`); `bootstrap` refuses to run when it fails
- `npm run typecheck` — TypeScript 7 native type check (via `lib/tsc.js` for Node 20 compat)
- `npm test` — runs validate + typecheck + bootstrap smoke test

## Tooling

Two **required** external tools for code-domain work (prose-only output is exempt) — both local, free, no API keys. Full per-platform install guide: [`references/tooling.md`](references/tooling.md).

- **codebase-memory-mcp** — code knowledge-graph MCP (tree-sitter + Hybrid LSP). Root `.mcp.json` is committed, so Claude Code offers it automatically on first open; the `query-symbol` / `get-callers` / `analyze-impact` skills (10 total) depend on it.
- **[ponytail](https://github.com/DietrichGebert/ponytail)** — "laziest senior dev" decision ladder enforced before code generation; complements `core/NEVER.md` and rules R2 / R8. Claude Code: `/plugin marketplace add DietrichGebert/ponytail` + `/plugin install ponytail@ponytail`.

Neither tool enters `package.json` or is rendered by bootstrap — they are per-machine environment config; the repo ships only the config snippets and the guide.
