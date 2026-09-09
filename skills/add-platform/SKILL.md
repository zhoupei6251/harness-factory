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
3. (Optional) Edit `scripts/bootstrap.ts` to add the new platform:
   - Add to `PLATFORMS` array
   - Add to `PLATFORM_DIR` map
4. (Optional) Update `schemas/platform.schema.json` enum
5. Run `npm run bootstrap -- --platform <name> --route code` to test

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
