# Qoder platform rules

## Tooling（本端接入）

- `~/.qoder/` holds user skills/extensions; `~/.qoder-cn/` holds CLI config/runtime. Do not mix these roots.
- MCP: top-level `mcpServers` in `~/.qoder-cn/settings.json` (user), `.qoder/settings.json` (project), or `.qoder/settings.local.json` (local). The root `.mcp.json` and `~/.qoder/shared_client/mcp.json` are not CLI configuration targets.
- On Windows use `npx.cmd` in the MCP command; omit `--ui=true`. Config changes require a new session or user `/mcp reload`.
- Skills: `npm run skills:install -- --platform qoder` links into `~/.qoder/skills/`. Discovery is a session-start snapshot; a newly installed skill may need a new session.
- Ponytail runs as a skill/instruction, without plugin commands or lifecycle hooks. Read its ladder; this platform difference is not a failure.
- Verify MCP once with `list_projects`; apply canonical evidence/降级 rules. Setup details belong in `references/tooling.md`.

Bootstrap projects this delta to `.qoder/rules/ENTRY.md` and merges it with Codex in the shared `AGENTS.md`.
