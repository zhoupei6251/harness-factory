# Claude Code platform rules

## Tooling（本端接入）

- MCP: Claude Code reads the committed project `.mcp.json`.
- Declaration: a project may carry `harness.json` (`platforms` / `skills` / `agents`). When present it is the truth — the installers render exactly those and prune factory-owned leftovers they did not name. Without it the installers fall back to `--profile`.
- One command: `npm run init:project -- --target <project> [--platform claude|all] [--force]` runs the three steps below.
- Skills: `npm run skills:install -- --platform claude --target <project>` links the curated core into `.claude/skills/`; omit target for user scope, use `--profile all` for the legacy catalog.
- Agents: `npm run agents:install -- --platform claude --target <project>` generates thin wrappers in `.claude/agents/` from `agents/<role>.md`; `agents/index.json` decides what installs and under which name. Hand-written wrappers are never overwritten without `--force`.
- Ponytail: enable the plugin or read the installed skill; skill installation alone does not enable lifecycle hooks.
- Hooks use `.claude/settings.json` and explicit trust. Configure them only when requested; do not add per-edit full builds.
- Verify MCP once with `list_projects`; apply the canonical evidence/降级 rules in `ENTRY.md`.
- Setup and command details belong in `references/tooling.md`, loaded on demand.

Bootstrap projects this delta to `.claude/harness/ENTRY.md` and merges it into the native `CLAUDE.md`.
