# runbooks.md - procedure guides

## Bootstrap (new project)

1. Install npm dependencies with `npm ci`.
2. Run `npm run bootstrap -- --platform all --route code` (local generation, no network/tool probe).
3. Run `npm run validate` and `npm run check-bootstrap`.
4. Run `npm run doctor` explicitly when diagnosing environment/tooling. Do not repeat it before every coding task.

## Install required tooling

Full per-platform guide: `references/tooling.md`.

- Discover MCP tools and call `list_projects` to verify codebase-memory connectivity. Use the exact project returned; index only if not indexed.
- Read the installed ponytail skill and use `full` by default. Installation as a skill does not enable plugin hooks.
- If tools fail, continue with source reads and targeted searches; report the actual failure and fallback. Do not kill other sessions to unlock an index.
- `npm run skills:install -- --platform codex|claude|trae|workbuddy|qoder --target <project>` links 10 core skills into the selected host's native project directory. Omit the platform for all five, omit target for user scope, add `--profile all` for all active legacy skills. Preview with `--dry-run`; conflicts preserve existing directories/foreign links and return nonzero. This is setup, not a per-task step.
- `npm run check:upstreams` verifies fixed revisions, local file hashes and license records offline. Imported subsets and explicit update procedure: `references/coding-capabilities.md`.

## Add a skill

Create `skills/<name>/SKILL.md` and `_meta.json`, run `npm run index` and `npm run validate`. Keep it about software engineering. Do not load every installed skill for each task.

## Add a platform adapter

Add `platforms/<name>/rules/ENTRY.md`; update the platform schema, bootstrap platform maps, structure assertions and relevant tests together. A native entry shared by two adapters must merge both deltas.

## Bug fix

Reproduce the failure, trace the changed shared path and relevant callers, fix the cause and run affected checks. Use a regression test for non-trivial behavior. Expand to the full suite when shared contracts, bootstrap or install behavior change.

## Verification and Git

Ordinary changes need relevant checks and an accurate result in the response. Complex changes may use one plan/evidence record plus independent review. For this repository, `npm test` checks the governance/generator/install contract; `npm run check-bootstrap -- --require-generated` is the pre-commit drift gate.

Commit only the intended diff. Repository maintenance commits directly to `main`; push requires explicit user instruction.
