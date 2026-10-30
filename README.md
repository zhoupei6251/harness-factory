# Harness Factory

Code-only rules and tools for Claude Code, Codex, Trae, WorkBuddy and Qoder. The default workflow is: understand the relevant code, make the smallest complete change, run the checks that matter.

## Quick start

```bash
npm ci
npm run bootstrap
npm run hooks:install
npm test
```

Bootstrap is local and does not probe external tools or the network. Run `npm run doctor` explicitly for environment diagnosis. Required coding tools and per-platform setup are in [references/tooling.md](references/tooling.md).

## Curated coding capabilities

The default profile links 10 skills: Ponytail, Codebase Memory, debugging, verification, security, module design, effective tests, UI design, Web testing and Playwright. Local adapters use selected content from Superpowers, ECC, Matt Pocock Skills, Impeccable, Taste, UI UX Pro Max and Anthropic Skills. Original reference files, data, licenses and fixed revisions ship with the repository; ordinary tasks load only the matching skill. Full frameworks, hook runtimes and automatic updates are not part of this profile.

```powershell
# Preview project-local installation for all five hosts
npm run skills:install -- --target D:/path/to/project --dry-run
# Install for the host you use; omit --platform for all five
npm run skills:install -- --platform codex --target D:/path/to/project
```

Omit `--target` for user-level installation. The explicit `--profile all` option retains access to all active legacy skills. Existing user directories/foreign links are preserved and reported as conflicts. Native rule entries also point directly to bundled skill files when host discovery is unavailable. [Capability scope, tool setup and updates](references/coding-capabilities.md).

To use this harness in another project, clone/link it at `<project>/harness-factory/` and run:

```bash
npx tsx harness-factory/scripts/install-into-project.ts --target <project>
```

See [templates/README.md](templates/README.md) for installation and [STRUCTURE.md](STRUCTURE.md) for file ownership.

## Fast coding with evidence

- Implementation/fix/optimization requests proceed through relevant verification without repeated spec/plan approval.
- Ordinary tasks need targeted graph/source evidence, direct implementation and useful checks. Plans, worktrees, subagents and verification documents are not mandatory.
- Risky/shared-contract changes use one concise plan/evidence record, stronger checks and independent review.
- Read rules and skills once, on demand. Reuse current evidence; avoid full-repository audits for local edits and repeated whole-project checks after every file.
- Keep validation, error handling, accessibility and honest reporting. Speed comes from removing unrelated work.
- Root `MEMORY.md` stores the project's current facts; bootstrap initializes it only when missing.

For frontend pages, [references/frontend-design.md](references/frontend-design.md) selects local Impeccable/Taste references or the UI UX Pro Max offline search engine. Choose one primary source for the task.

## Repository commands

| Command | Purpose |
|---------|---------|
| `npm run bootstrap -- --platform all --route code` | Generate platform rules and distributable harness entries |
| `npm run doctor` | Explicit environment/tooling diagnosis |
| `npm run validate` | Schema, skill and tracked-artifact checks |
| `npm run structure:audit` | Verify directory and skill contracts |
| `npm run typecheck` | Check the TypeScript meta toolchain |
| `npm run check-bootstrap` | Compare generated entries with fresh output in isolation |
| `npm run index` | Regenerate `skills/INDEX.md` |
| `npm run stats` | Live repository counts and Git state |
| `npm run skills:install -- --platform codex` | Link 10 core skills; optional --target, --profile all and --dry-run; five hosts supported |
| `npm run check:upstreams` | Verify bundled source hashes and license records offline |
| `npm run hooks:install` | Install the pre-commit bootstrap drift gate once per clone |
| `npm test` | Full repository governance/bootstrap/install checks |

Use Node.js 20.9+ with the locked npm dependencies. Scripts run through tsx; no application build step is needed.

## Sources and generated files

Edit `ENTRY.md`, `core/`, `capabilities/rules/`, `platforms/`, `templates/` and code skills. `npm run bootstrap` generates native entries and per-platform rule directories. Codex and Qoder share `AGENTS.md`, so their deltas are merged.

The three `*.harness.md` files are tracked distribution artifacts; regenerate and commit them with their sources. Native entries, platform projections, dependencies and runtime scratch are gitignored. Existing project `MEMORY.md` is preserved.

This repository supports only the `code` route. Source statistics read Git-tracked paths rather than recursively scanning local outputs.

Repository maintenance commits directly to `main`; push requires an explicit request. Downstream projects retain their own Git workflow.
