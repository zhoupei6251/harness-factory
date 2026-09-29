# Codex platform rules

> Add Codex-specific deltas here. Loaded after the canonical core/ENTRY.md.

## Hooks

Codex uses `[hooks.state]` in `config.toml` with trusted hashes. Trust model: **explicit per hook** — run `/hooks` to approve.

## MCP

MCP servers live in `[mcp_servers.*]` of `~/.codex/config.toml` (Codex does not read project `.mcp.json`). See `mcp-config/codebase-memory.codex.toml` for a ready-made snippet.

## Skills

Codex discovers skills in `~/.codex/skills/`. Install repo skills with `npm run skills:install` (junctions to `skills/`, edits are live).

## Projected to

- `.codex/rules/ENTRY.md` (this file)
- `.codex/rules/ROOT.md` (canonical ENTRY.md)
- `AGENTS.md` (native auto-loaded entry, generated from canonical + this delta)
