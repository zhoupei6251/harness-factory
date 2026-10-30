# Claude Code platform rules

## Tooling（本端接入）

- MCP: Claude Code reads the committed project `.mcp.json`.
- Skills: `npm run skills:install -- --platform claude --target <project>` links the curated core into `.claude/skills/`; omit target for user scope, use `--profile all` for the legacy catalog.
- Ponytail: enable the plugin or read the installed skill; skill installation alone does not enable lifecycle hooks.
- Hooks use `.claude/settings.json` and explicit trust. Configure them only when requested; do not add per-edit full builds.
- Verify MCP once with `list_projects`; apply the canonical evidence/降级 rules in `ENTRY.md`.
- Setup and command details belong in `references/tooling.md`, loaded on demand.

Bootstrap projects this delta to `.claude/rules/ENTRY.md` and merges it into the native `CLAUDE.md`.
