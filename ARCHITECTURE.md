# Architecture

## Why this exists

`harness-factory` is the lean replacement for `harness-foundry` and `harness-kit` (skeleton only). It keeps the bones of harness-kit and the multi-platform intent of harness-foundry, but on a strict diet: the meta toolchain (`scripts/` + `tests/`) is TypeScript only, and there are no empty placeholders.

## Current state

No counts live in this file. `npm run stats` prints them (source files by extension, tracked files, skills active/archived, schemas, npm scripts, git state, runtime dir sizes) — every number written down by hand here has gone stale within a day, three times over.

What the counts are *of*:

- **Platform adapters**: claude, codex, trae, workbuddy, qoder. Codex + Qoder share the `AGENTS.md` native entry, merged by bootstrap.
- **Routes**: code, novel, news — each with a `MEMORY.md` template.
- **Capability verticals**: java, typescript, common.
- **MCP servers**: codebase-memory only, wired via the committed root `.mcp.json` plus the `mcp-config/` snippet (see `references/tooling.md`).
- **Web templates**: `src/web/` — Vue compositions for the news route, built by `vite build` into `dist/`, consumed by `skills/douyin-pro/scripts/path_b_build.py`. Which compositions go through Vue is declared by each entry's `contract.toml` (`role` + `variant`); `path_b_build.py` derives the bundle name as `{role}-{variant}`, uses `VUE_ROUTES` only for explicit overrides (currently empty), and `CUTOVER_ROLES` to decide which roles are switched over. No count is recorded here.

## The 6 layers

1. **Foundation**: `core/` — governance docs. Mandatory, no variation.
2. **Capabilities**: `capabilities/rules/{java,typescript,common}/` — per-language rules. Other capability verticals (eval, intelligence, memory, etc.) were removed in phase-5 as empty placeholders.
3. **Platforms**: `platforms/<name>/rules/ENTRY.md` — thin adapters. Per-platform deltas.
4. **Routes**: `routes/<name>/MEMORY.md` — vertical templates (code, novel, news). Per-domain state.
5. **Skills**: `skills/<name>/SKILL.md` + `_meta.json` — active skills live in `skills/`, unused ones in `skills/archive/` (same structure, restore via `git mv`).
6. **Web templates**: `src/web/` — the only layer with a build step and a second toolchain (Vue 3 + Vite + GSAP). It is *not* a governance layer: `bootstrap` never reads it, `BOOTSTRAP_INPUTS` deliberately excludes it, and nothing in `dist/` is tracked.

### Why the Vue layer sits at the repo root, not under `skills/douyin-pro/`

Ruled on 2026-10-13, against the intuitive "put it next to the renderer":

- `scripts/install-skills.ts:67` junctions the **whole** skill directory into `~/.qoder/skills/` (and `~/.codex/`, `~/.claude/`). A Vite project inside `skills/douyin-pro/` would be published to every platform session on the machine, `dist/` and all.
- `src/web/lib/` (`gsap-runtime`, `hyperframes-bridge`, `data.contract`, `tokens/`) is shared across packs, while the skill boundary is one self-contained directory per skill.
- Vite wants a single `root`, one `node_modules`, and one `dist/`; multi-entry is expressed by `rollupOptions.input`, not by N projects.
- The Python side only *consumes* `dist/` — it has no reason to own the source.

`skills/douyin-pro/` therefore keeps the scripts and the `host.html` templates; the Vue source lives in `src/web/entries/<name>/`.

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
| 9 novel scripts | harness-foundry | none | novel route restored in v2.5 (archive skills, no scripts) |
| 7 skill-meta scripts | harness-foundry | manual frontmatter | 1 script when 3+ skill editors needed |
| 4 test layers (L1/L2/L3-eval/L3-intelligence) | harness-foundry | platform drift | 1 layer per platform when added |
| 694 md files | harness-foundry | doc bloat | write on demand |
| bash + python | harness-foundry | dual toolchain | meta toolchain (`scripts/` + `tests/`) is TS only; Python lives in skill/route payload code; the one second toolchain (Vue + Vite + GSAP) is confined to `src/web/` |
| 23 top-level dirs | harness-foundry | navigation cost | 10 top-level items |
| 15+ unused MCP servers | harness-foundry's mcp-servers.json | none (placeholders never filled) | add when actually used |
| 5 harness-foundry leftover files in skills/ | `_layer.yaml`, `categories.yaml`, `INDEX.md`, `README.md` | none (auto-gen script gone) | replace with new `skills/INDEX.md` (phase-5) |
| 9 empty capability placeholders | design intent | none (YAGNI) | recreate when first content lands |

## How to add things

- **Skill**: see `skills/add-skill/SKILL.md`
- **Platform**: see `skills/add-platform/SKILL.md`
- **Route**: see `skills/add-route/SKILL.md`
- **Language rule**: add file under `capabilities/rules/<lang>/` (e.g., `python/hooks.md`)
- **Vue composition**: add `src/web/entries/<name>/` (`main.ts` + `<Name>.vue` + `contract.toml` declaring `role` and `variant`; `main.html` optional). `vite.config.ts` needs no edit — it enumerates `src/web/entries/*/main.ts` and generates the rollup input and HTML-flatten plugin per directory. `path_b_build.py` derives the bundle as `{role}-{variant}`; add a `VUE_ROUTES` override only when derivation cannot express the mapping, and add the role to `CUTOVER_ROLES` to switch a shot over. A built-but-uncutover bundle renders nothing.

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
