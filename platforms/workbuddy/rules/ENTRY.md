# WorkBuddy platform rules

> Add WorkBuddy-specific deltas here. Loaded after the canonical core/ENTRY.md.

## Hooks

WorkBuddy has its own `hooks/` system. Trust model: **approval via `mcp-approvals.json`**.

## MCP

MCP servers in `.codebuddy/mcp.json` (i.e., `~/.codebuddy/mcp.json`).

## Agents

WorkBuddy treats agents as first-class. Export canonical agents to `~/.codebuddy/agents/`.

## Projected to

- `.codebuddy/rules/ENTRY.md` (this file)
- `.codebuddy/rules/ROOT.md` (canonical ENTRY.md)
