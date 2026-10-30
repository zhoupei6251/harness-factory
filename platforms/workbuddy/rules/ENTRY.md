# WorkBuddy platform rules

## Tooling（本端接入）

- MCP: WorkBuddy uses `.codebuddy/mcp.json`; setup details are in `references/tooling.md`.
- Skills: `npm run skills:install -- --platform workbuddy --target <project>` links the curated core into `.codebuddy/skills/`; omit target for user scope, use `--profile all` for the legacy catalog. Host skill trust/discovery is separate from file installation.
- Ponytail runs as a skill/instruction. Do not assume plugin commands or lifecycle hooks.
- Verify MCP once with `list_projects`; apply canonical evidence/降级 rules.
- WorkBuddy hook approvals are host configuration, not bootstrap output.

Bootstrap projects this delta to `.codebuddy/rules/ENTRY.md` and the native `.codebuddy/rules/project_rules.md`.
