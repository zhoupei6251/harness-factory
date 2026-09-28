---
name: add-route
description: "Add a new route (vertical domain) to harness-factory. Walks through routes/<route>/MEMORY.md creation and bootstrap.ts registration."
tags: [Runbook]
triggers: ["add route", "new route", "new vertical"]
---

# add-route

Add a new route (vertical domain) to `harness-factory/routes/<name>/`.

## When to use
- User says "add route" / "new route" / "new vertical"
- A new domain needs persistent state (e.g., `podcast`, `video`)

## Steps

1. Pick a name (kebab-case, e.g., `podcast`)
2. Create `routes/<name>/MEMORY.md` with the domain-specific state template
3. Edit `scripts/bootstrap.ts`:
   - Add to `Route` type union
   - Add to `ROUTE_RUNTIME` map
   - Add to `ROUTE_BASE` map
   - Add parsing branch in `parseArgs`
4. (Optional) Update `schemas/route.schema.json` enum
5. Run `npm run bootstrap -- --platform all --route <name>` to test

## MEMORY.md template

```markdown
# <Domain> domain MEMORY

> Auto-loaded when route=<name>.

## <Domain info>
- key1: (fill in)
- key2: (fill in)

## State
state_field: []

## In progress
in_progress:
  - current_phase: (phase1 | phase2)

## Last updated
last_updated: YYYY-MM-DDTHH:MM:SS
```
