# harness-factory templates

## Install into a project

1. Clone or link this repository at `<project>/harness-factory/`; keep that directory name.
2. Run `npx tsx harness-factory/scripts/install-into-project.ts --target .` from the project root.
3. The installer backs up existing entries and renders the project overview. Review the resulting local files and start a new agent session.

| Template | Output |
|----------|--------|
| `target-CLAUDE.md` | Project `CLAUDE.md` |
| `target-AGENTS.md` | Project `AGENTS.md` for Codex/Qoder |
| `target-GEMINI.md` | Project `GEMINI.md` |
| `project-birds-eye.template.md` | Default overview; replace with `--birds-eye-file <path>` |
| `harness.template.md` | Repository `CLAUDE.harness.md`, `AGENTS.harness.md`, `GEMINI.harness.md` through bootstrap |

The target templates contain `${PROJECT_BIRDS_EYE}` and `${HARNESS_FACTORY_IMPORT}`. Other-project mode points at `harness-factory/*.harness.md`; self mode uses this repository's `ENTRY.md`. Codex/Gemini use conditional text instructions and Claude uses an `@import`.

## Maintain the shared harness

Edit `harness.template.md`, then run `npm run bootstrap`. Bootstrap replaces the platform title, intro, loading convention/order and cross-platform tail from `HARNESS_DELTAS` in `scripts/bootstrap.ts`.

Keep the common execution rules here. Platform deltas contain only platform differences. Routine coding proceeds directly; complex work uses a concise plan and relevant verification. Frontend design guidance is referenced on demand through `references/frontend-design.md`.

`tests/install-roundtrip.test.ts` verifies exact rendering, idempotence and dry-run behavior. `npm run check-bootstrap` verifies distributed harness files against the canonical template.
