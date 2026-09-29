# runbooks.md - procedure guides

## Bootstrap (new project)

1. Run `npm run bootstrap -- --platform all --route code`
2. Verify with `npm run validate`
3. Edit `ENTRY.md` to reflect project-specific behavior

## Install recommended tooling (per machine, one-time)

Full guide: `references/tooling.md`. Both tools are local and free — no API keys.

1. **codebase-memory-mcp** — Claude Code: root `.mcp.json` is already committed, accept the enable prompt on first open. Other platforms / static-binary install: see `references/tooling.md`
2. **ponytail** — Claude Code: `/plugin marketplace add DietrichGebert/ponytail` then `/plugin install ponytail@ponytail`. Codex / Cursor / Gemini / instruction-only adapters: see `references/tooling.md`
3. Verify: ask the agent to call `list_projects` (MCP connected) and run `/ponytail-help` (plugin loaded)

## Add a skill

1. Create `skills/<name>/SKILL.md` + `_meta.json`
2. Validate via `npm run validate`
3. Regenerate the skill index via `npm run index`
4. Sync to platforms via `npm run bootstrap -- --platform all`

## Add a platform adapter

1. Create `platforms/<name>/` with `rules/ENTRY.md` and any platform-specific config
2. Update `schemas/platform.schema.json` enum
3. Update `scripts/bootstrap.ts` (`Platform` type + `PLATFORM_DIR` map)

## Bug fix

1. Reproduce first (write a failing test if possible)
2. Trace to root cause, not symptom
3. Fix in the shared path, not the symptom path
4. Run the full validate suite

## News pipeline

Route: `news`. Runtime: `.harness-news-runtime/` (plans / articles / videos). State: root `MEMORY.md` (projected from `routes/news/MEMORY.md`).

**This runbook does not describe the pipeline — it points at its single source.** The news track is v2 single-track (topic → template decision → script → fact-check → Path B render → publish) and it lives in `skills/news-workflow/SKILL.md`; the visual/technical detail lives in `routes/news/ARCHITECTURE.md`. Governance docs only route intent here (see `intent-routing.md`); restating the stages creates drift, and v1's text track (`news-generator` / `news-polish` / `humanizer`) was already written back twice.

Load `skills/news-workflow/SKILL.md` and follow it. The two rules that must survive anywhere in this repo:

1. **fact-check is a hard gate** — no script enters rendering unless `drafts[].fact_check == passed`.
2. **artifacts go to `.harness-news-runtime/`** — never `.ai-runtime-artifacts/` (that dir belongs to the `code` route).

Phase is always mirrored in `MEMORY.md` → `in_progress.current_phase` so any session can resume.
