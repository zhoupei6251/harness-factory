# WorkBuddy platform rules

## Tooling（本端接入）

- MCP: WorkBuddy uses `.codebuddy/mcp.json`; setup details are in `references/tooling.md`.
- Ponytail runs as a skill/instruction. Do not assume plugin commands or lifecycle hooks.
- Verify MCP once with `list_projects`; apply canonical evidence/降级 rules.
- WorkBuddy hook approvals are host configuration, not bootstrap output.

Bootstrap projects this delta to `.codebuddy/rules/ENTRY.md` and the native `.codebuddy/rules/project_rules.md`.
