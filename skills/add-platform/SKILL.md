---
name: add-platform
description: "Add a new platform adapter to harness-factory. Walks through platforms/<plat>/rules/ENTRY.md creation and bootstrap.ts registration."
tags: [Runbook]
triggers: ["add platform", "new platform", "add adapter"]
---

# add-platform

Add a new AI platform adapter to `harness-factory/platforms/<name>/`.

## When to use
- User says "add platform" / "new platform" / "add adapter"
- A new AI tool (Cursor, Copilot, etc.) needs harness support

## Steps

1. Pick a name (kebab-case, e.g., `cursor`, `copilot`)
2. Create `platforms/<name>/rules/ENTRY.md` with platform-specific notes
3. Edit `scripts/bootstrap.ts` to add the new platform:
   - Add to `Platform` type and `PLATFORMS` array
   - Add to `PLATFORM_DIR` map
   - Add to `PLATFORM_NATIVE_ENTRY` map — the file path this platform natively auto-loads (e.g. `AGENTS.md` for Codex, `CLAUDE.md` for Claude). Projecting only to platform dirs is not enough.
   - If the native entry path **collides with an existing platform**, their deltas are merged into one file (as with codex + qoder on `AGENTS.md`); no extra code is needed, but the delta files must not contradict each other.
   - If the platform's own config lives outside the repo (e.g. `~/.<plat>/skills`), add it to `TARGETS` in `scripts/install-skills.ts`.
4. Add the new output paths to `EXPECTED` and `ROOT_MUST_SURVIVE` in `tests/bootstrap.test.ts`
5. (Optional) Update `schemas/platform.schema.json` enum
6. Add a row to the Platform mapping table in `ENTRY.md`
7. Run `npm run bootstrap -- --platform <name> --route code` to test

## Entry.md template

```markdown
# <Platform name> platform rules

> Add <Platform>-specific deltas here. Loaded after the canonical core/ENTRY.md.

## Hooks
<how this platform handles hooks>

## MCP
<where MCP servers live in this platform>

## Projected to
- <output path>/rules/ENTRY.md (this file)
- <output path>/rules/ROOT.md (canonical ENTRY.md)
```
