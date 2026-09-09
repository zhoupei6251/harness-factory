# Architecture

## Why this exists

`harness-factory` is the lean replacement for `harness-foundry` (1290 files) and `harness-kit` (skeleton only). It keeps the bones of harness-kit and the multi-platform intent of harness-foundry, but on a strict diet: ~30 source files, TypeScript only, empty placeholders for everything that isn't governance or bootstrap.

## The 5 layers

1. **Foundation**: `core/` — 8 governance docs. Mandatory, no variation.
2. **Capabilities**: `capabilities/<name>/` — 10 empty verticals. Fill on demand.
3. **Platforms**: `platforms/<name>/rules/ENTRY.md` — 4 thin adapters. Per-platform deltas.
4. **Routes**: `routes/<name>/MEMORY.md` — 3 vertical templates. Per-domain state.
5. **Skills**: `skills/<name>/SKILL.md` + `_meta.json` — on-demand, validated by schema.

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

## How to add things

- **Skill**: see `skills/add-skill/SKILL.md`
- **Platform**: see `skills/add-platform/SKILL.md`
- **Route**: see `skills/add-route/SKILL.md`
- **Capability doc**: just write `capabilities/<name>/SKILL.md` (no registration needed; load by intent)

## Bootstrap contract

`scripts/bootstrap.ts` projects canonical content to per-platform format:

| Canonical | Per-platform |
|-----------|--------------|
| `core/ENTRY.md` (or `platforms/<plat>/rules/ENTRY.md` if exists) | `<platform>/rules/ENTRY.md` |
| `ENTRY.md` | `<platform>/rules/ROOT.md` |
| `routes/<route>/MEMORY.md` | `./MEMORY.md` (project root) |
| `<route>` runtime dirs | `<route-specific>/` (e.g., `.ai-runtime-artifacts/`) |

If `platforms/<plat>/rules/ENTRY.md` exists, it wins over canonical. This is how platform-specific deltas work.

## Migration from harness-foundry

1. Pick 1 skill per day from `harness-foundry/skills/`
2. Add it to `harness-factory/skills/` via `skills/add-skill/SKILL.md`
3. Run `npm run validate` to confirm
4. When a category is migrated, delete from harness-foundry
5. Target: harness-foundry is empty by end of 2026
