# Architecture

Harness Factory distributes software-engineering instructions across five platform adapters using one canonical source. It has no application runtime or media build toolchain.

## Layers

| Layer | Responsibility |
|-------|----------------|
| `core/` + root `ENTRY.md` | Short shared behavior rules and on-demand governance index |
| `capabilities/rules/{common,java,typescript}/` | Task/language-specific practices |
| `platforms/<name>/rules/ENTRY.md` | Host configuration differences only |
| `routes/code/MEMORY.md` | Neutral project-memory initialization template |
| `skills/` | Curated core and optional legacy procedures; upstream subsets live beside their adapters, loaded on demand |
| `references/` | Tool setup, lessons and frontend design source guidance |

Claude, Codex, Trae, WorkBuddy and Qoder are the adapters. Codex and Qoder share the native `AGENTS.md`; generation merges their deltas. Gemini's distributable harness remains for the existing downstream installer contract, without adding a sixth bootstrap adapter.

## Execution design

The common path is targeted evidence → smallest implementation → relevant verification. User authorization persists across the task. Routine edits do not create mandatory spec, plan, review and verification documents or pause at artificial stage gates.

Complex changes record the necessary scope, evidence and pass criteria once. Shared APIs, migrations and security boundaries get broader validation and independent review. Evidence, validation and accessibility remain requirements at every size.

Context is loaded progressively. Setup guides, hook instructions, historical decisions and unrelated skills stay out of ordinary coding context. Frontend tasks use `references/frontend-design.md` to select an upstream reference as needed.

`core/intent-routing.md` selects a bundled skill without requiring native discovery. `skills:install` optionally links 10 core skills into one or all five native host directories; all active legacy skills require explicit `--profile all`. Project scope uses `--target`, default scope is the user's home. The installer preserves user files/foreign links and never changes MCP or hook settings. `references/upstreams.lock.json` pins reviewed content files and licenses; `check:upstreams` verifies their bytes offline. Source upgrades are explicit, separate maintenance work. Graph/browser services and optional Python remain external capabilities, not npm runtime dependencies.

## Bootstrap contract

`scripts/bootstrap-contract.ts` lists inputs and generated files; drift checks and integration tests consume the same contract.

| Canonical source | Output |
|------------------|--------|
| Root `ENTRY.md` + core index + platform delta | Native entry |
| Platform delta | `<platform>/rules/ENTRY.md` |
| Root `ENTRY.md` | `<platform>/rules/ROOT.md` |
| `templates/harness.template.md` + platform tokens | Three tracked `*.harness.md` artifacts |
| `routes/code/MEMORY.md` | Root `MEMORY.md` only if missing |

Bootstrap is deterministic local generation. External-tool diagnostics are an explicit `npm run doctor` operation, avoiding a network/package probe on each generation.

`check-bootstrap` uses a throwaway source copy and the real generator to compare outputs. Project `MEMORY.md` is mutable state and is not byte-equal to its template after initialization.

## Verification

`npm test` runs the current governance, type and installation/generator checks. The installer tests exercise exact rendering, idempotence, backup/dry-run behavior and source-repository isolation. The pre-commit hook checks generated-file drift.

Live counts belong to `npm run stats`; do not hand-maintain snapshots here. Source enumeration uses Git-tracked paths and does not walk local outputs.
