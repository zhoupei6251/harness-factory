# Architecture

## Why this exists

`harness-factory` is the lean replacement for `harness-foundry` (1290 files) and `harness-kit` (skeleton only). It keeps the bones of harness-kit and the multi-platform intent of harness-foundry, but on a strict diet: 346 source files (vs 669 in harness-foundry), TypeScript only, empty placeholders for everything that isn't governance or bootstrap.

## Current state (as of phase-4)

| Metric | Count |
|---|---|
| Source files (excl `.git` + `node_modules`) | 346 |
| Core governance docs | 8 |
| Platform adapters | 4 (claude, codex, trae, workbuddy) — all with placeholder rules |
| Routes | 3 (code, novel, news) — all with MEMORY templates |
| Skills | 91 (88 migrated from harness-foundry + 3 meta: add-skill, add-platform, add-route) |
| MCP servers | 1 (codebase-memory only; harness-foundry's 15+ bloat config removed) |
| Capability verticals (in `capabilities/rules/`) | 3 (java, typescript, common) |
| Schemas | 3 |
| npm scripts | 4 (bootstrap, validate, typecheck, test) |

## The 5 layers

1. **Foundation**: `core/` — 8 governance docs. Mandatory, no variation.
2. **Capabilities**: `capabilities/rules/{java,typescript,common}/` — per-language rules. Other capability verticals (eval, intelligence, memory, etc.) were removed in phase-5 as empty placeholders.
3. **Platforms**: `platforms/<name>/rules/ENTRY.md` — 4 thin adapters. Per-platform deltas.
4. **Routes**: `routes/<name>/MEMORY.md` — 3 vertical templates. Per-domain state.
5. **Skills**: `skills/<name>/SKILL.md` + `_meta.json` — 88 from harness-foundry + 3 meta.

## How a session works

```
session start
    |
    +-- read ENTRY.md (mandatory)
    +-- read core/NEVER.md (mandatory)
    +-- read platform-specific rules (if platform set)
    +-- read route MEMORY.md (if route set)
    +-- read skills/<x>/SKILL.md (on trigger)
    |
    v
work
    |
    +-- on add-skill trigger: skills/add-skill/SKILL.md
    +-- on add-platform trigger: skills/add-platform/SKILL.md
    +-- on add-route trigger: skills/add-route/SKILL.md
    |
    v
session end
```

## What was cut (and why)

| Cut | Was in | Ceiling | Upgrade path |
|---|---|---|---|
| 315-file Claude adapter mirror | harness-foundry | format drift | `npm run bootstrap` regenerates |
| 9 novel scripts | harness-foundry | none initially | write 1 when starting a novel |
| 7 skill-meta scripts | harness-foundry | manual frontmatter | 1 script when 3+ skill editors needed |
| 4 test layers (L1/L2/L3-eval/L3-intelligence) | harness-foundry | platform drift | 1 layer per platform when added |
| 694 md files | harness-foundry | doc bloat | write on demand |
| bash + python | harness-foundry | dual toolchain | TS only |
| 23 top-level dirs | harness-foundry | navigation cost | 10 top-level items |
| 15+ unused MCP servers | harness-foundry's mcp-servers.json | none (placeholders never filled) | add when actually used |
| 5 harness-foundry leftover files in skills/ | `_layer.yaml`, `categories.yaml`, `INDEX.md`, `README.md` | none (auto-gen script gone) | replace with new `skills/INDEX.md` (phase-5) |
| 9 empty capability placeholders | design intent | none (YAGNI) | recreate when first content lands |

## How to add things

- **Skill**: see `skills/add-skill/SKILL.md`
- **Platform**: see `skills/add-platform/SKILL.md`
- **Route**: see `skills/add-route/SKILL.md`
- **Language rule**: add file under `capabilities/rules/<lang>/` (e.g., `python/hooks.md`)

## Bootstrap contract

`scripts/bootstrap.ts` projects canonical content to per-platform format:

| Canonical | Per-platform |
|-----------|--------------|
| `core/ENTRY.md` (or `platforms/<plat>/rules/ENTRY.md` if exists) | `<platform>/rules/ENTRY.md` |
| `ENTRY.md` | `<platform>/rules/ROOT.md` |
| `routes/<route>/MEMORY.md` | `./MEMORY.md` (project root) |
| `<route>` runtime dirs | `<route-specific>/` (e.g., `.ai-runtime-artifacts/`) |

If `platforms/<plat>/rules/ENTRY.md` exists, it wins over canonical. This is how platform-specific deltas work.

## Migration from harness-foundry (done in phase-3)

- mcp-config (codebase-memory only, others were bloat)
- references/traps.md
- capabilities/rules/{java,typescript,common}/*.md (12 files)
- skills/ — full 88-skill set migrated (some may be unused; trim as needed)

Target: harness-foundry is empty / deletable.
