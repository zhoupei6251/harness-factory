# runbooks.md - procedure guides

## Bootstrap (new project)

1. Run `npm run bootstrap -- --platform all --route code`
2. Verify with `npm run validate`
3. Edit `ENTRY.md` to reflect project-specific behavior

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
