# Code-only fast Harness implementation plan

**Goal:** Keep harness-factory focused on writing code, reduce default agent overhead, retain evidence and relevant verification, and publish to main as explicitly requested.

**Architecture:** Reuse the current bootstrap and installation contract. Remove non-code routes and their private assets/dependencies instead of building another configuration layer. Keep frontend design sources as on-demand references, with no automatic installation.

**Tech stack:** Node.js, TypeScript, tsx, Markdown, existing platform adapters.

## Authorization and boundaries

The user explicitly requested implementation, removal of the news/writing domains, commit to main and push. No additional spec/plan approval is needed for this authorized task. Do not edit global host configuration or other repositories. Historical design records may retain retired paths and are not active instructions.

## Evidence

- Project: `D-work-xinyue-aigc_platfrom_back-harness-factory`; graph generation `2026-10-14T08:56:03Z`.
- `search_graph` found bootstrap `parseArgs`, `projectRoute`, `projectHarnessFiles`, schema validators and skill installation functions.
- `trace_path(projectRoute, both, depth=2)` identifies the bootstrap module as caller and `exists` as callee. `get_code_snippet(projectHarnessFiles)` confirms that the shared harness template generates all three harness artifacts.
- Coverage reports metadata changes for bootstrap/entry/routing, and excludes route MEMORY files. Current source has been read directly; new structural audit is also read directly because the old graph does not track it. Graph results are leads, not proof of complete current coverage.
- Current costs observed in source: mandatory repeated approval/doc stages, duplicate entry loading, archived domain assets still included in bootstrap/test copies, Vue/video build checks in npm test, per-edit typecheck/lint hook recommendations, and project-state examples in the route template.

## Tasks

1. Simplify canonical workflow and loading rules. Default to direct execution for authorized coding tasks; scale evidence, tests and documents to risk. Keep codebase-memory and ponytail, safety checks, honest verification and explicit push authorization. Keep required platform differences and regenerate outputs.
2. Remove news/novel routes, publishing/writing/video skills and domain assets. Restrict bootstrap/schema to code. Remove rendering commands and Vue/video-only dependencies; update guards and integration assertions together.
3. Add `references/frontend-design.md` describing when to consult impeccable, taste-skill and ui-ux-pro-max-skill. Load only the relevant source for a frontend task and retain repository component/style conventions and accessibility.
4. Run the existing remaining repository checks, bootstrap drift checks and install roundtrip tests. Obtain independent review, fix findings, record verification, inspect the final diff, commit on main and push normally.

## Pass criteria

- Only the code route is accepted and distributed; removed domains are absent from active sources, dependencies and test commands.
- Authorized routine coding no longer requires redundant approval, mandatory worktrees/subagents or multiple evidence documents.
- Relevant tests and evidence remain required; no per-edit whole-project build or unrelated workflow is mandated.
- Frontend references have all three verified upstream links and task-specific guidance.
- Bootstrap outputs match canonical sources; installation remains idempotent and isolated from the source repository.
- Tests pass, independent review has no unresolved material findings, and origin/main points at the published commit.

## Minimal implementation choice

Delete retired components, reuse the existing generator/tests, and edit canonical Markdown. Add no runtime dependency or new orchestration/configuration subsystem.
