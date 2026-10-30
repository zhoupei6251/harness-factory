# Trae platform rules

## Tooling（本端接入）

- MCP: configure through Trae settings using `mcp-config/codebase-memory.json`; platform setup details are in `references/tooling.md`.
- Ponytail runs as a skill/instruction. Do not assume plugin commands or lifecycle hooks.
- Verify MCP once with `list_projects`; apply canonical evidence/降级 rules.

Bootstrap projects this delta to `.trae/rules/ENTRY.md` and the native `.trae/rules/project_rules.md`.
