# Codex platform rules

## Tooling（本端接入）

- MCP: Codex reads `[mcp_servers.*]` in `~/.codex/config.toml`, not the repository `.mcp.json`. Snippet: `mcp-config/codebase-memory.codex.toml`.
- Skills: `~/.codex/skills/`; `npm run skills:install -- --platform codex` links active repository skills.
- Ponytail: read the installed skill; plugin/hook activation is separate. Hooks require explicit trust via `/hooks`.
- Verify MCP once with `list_projects`; apply the canonical evidence/降级 rules in `ENTRY.md`.
- Setup details: `references/tooling.md` on demand.

Bootstrap projects this delta to `.codex/rules/ENTRY.md`. Codex and Qoder share `AGENTS.md`; both deltas must survive generation.
