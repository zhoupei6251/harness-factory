# Codex platform rules

> Add Codex-specific deltas here. Loaded after the canonical core/ENTRY.md.

## Hooks

Codex uses `[hooks.state]` in `config.toml` with trusted hashes. Trust model: **explicit per hook** — run `/hooks` to approve.

## MCP

MCP servers live in `[mcp_servers.*]` of `config.toml`. Add via `codex plugin marketplace add` or edit directly.

## Projected to

- `.codex/rules/ENTRY.md` (this file)
- `.codex/rules/ROOT.md` (canonical ENTRY.md)
