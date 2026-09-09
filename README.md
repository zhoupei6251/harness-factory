# Harness Factory

Clean skeleton for shipping harness rules to 4 AI platforms (Claude / Codex / Trae / WorkBuddy) across 3 routes (code / novel / news).

## Quick start
```bash
bash scripts/bootstrap.sh --platform=all --route=code
bash tests/validate-schemas.sh
```

## Structure
- `ENTRY.md` - single entry point, all platforms load this
- `core/` - 8 governance docs (R1-R8, NEVER, routing, runbooks, tags)
- `capabilities/` - 10 empty verticals (fill on demand)
- `platforms/` - 4 empty platform adapters (fill on demand)
- `routes/` - 3 empty route templates (fill on demand)
- `skills/` - canonical skills (add on demand)
- `schemas/` - 3 JSON schemas
- `scripts/bootstrap.sh` - projects canonical to platform format
- `tests/validate-schemas.sh` - schema validation

## Why this exists
harness-foundry (1290 files) was too heavy. harness-kit (skeleton only) lacked platform adapters. harness-factory = the middle ground: capability-first skeleton with 4 platform slots and 3 route slots, all empty by default.

See `core/ENTRY.md` for the governance index and `core/intent-routing.md` for how to use this.
