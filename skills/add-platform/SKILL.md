---
name: add-platform
description: "Add a new AI host adapter to harness-factory. One directory: platforms/<name>/platform.json (capability matrix) + platforms/<name>/rules/ENTRY.md (prose delta). No script keeps its own platform list."
tags: [Runbook]
triggers: ["add platform", "new platform", "add adapter"]
---

# add-platform

Add a new AI platform adapter. The whole contract is one directory —
`harness-factory/platforms/<name>/`.

## When to use
- User says "add platform" / "new platform" / "add adapter"
- A new AI tool (Cursor, Copilot, …) needs harness support

## Steps

1. Pick a name (kebab-case, e.g. `cursor`, `copilot`).
2. Create `platforms/<name>/platform.json`:

   ```json
   {
     "id": "cursor",
     "label": "Cursor",
     "configDir": ".cursor",
     "nativeEntry": "AGENTS.md",
     "renderDir": ".cursor/harness",
     "skillsDir": ".cursor/skills",
     "agentsDir": null,
     "agentFrontmatter": null
   }
   ```

   | Field | Meaning |
   |-------|---------|
   | `id` | Must equal the directory name |
   | `configDir` | Where this host reads its config from |
   | `nativeEntry` | The file the host auto-loads; two hosts naming the same file get their deltas **merged** (codex + qoder on `AGENTS.md`) |
   | `renderDir` | Where bootstrap writes `ENTRY.md` + `ROOT.md` |
   | `skillsDir` | Where `skills:install` links skills |
   | `agentsDir` | Where `agents:install` writes wrappers, or `null` when the host has no per-agent file concept |
   | `agentFrontmatter` | Keys that host accepts on an agent file, or `null` |

3. Create `platforms/<name>/rules/ENTRY.md` with the platform-specific prose (hooks, MCP, skills location, how the delta is projected).
4. Add the name to `expectedPlatforms` in `tools/scripts/structure-audit.ts` — this is the explicit claim of which hosts we support, so adding one must be a deliberate edit.
5. Add a row to the Platform mapping table in `ENTRY.md`.
6. Run `npm run bootstrap` and `npm test`. **No script edits:** every script reads `platform.json` through `tools/scripts/platforms.ts`, and bootstrap derives the platform list from the directory.

## Entry.md template

```markdown
# <Platform name> platform rules

## Tooling（本端接入）

- MCP: <where MCP servers live for this host>
- Skills: `npm run skills:install -- --platform <id> --target <project>` links into `<skillsDir>`
- Agents: <`npm run agents:install` if agentsDir is non-null, otherwise say the host has none>

Bootstrap projects this delta to `<renderDir>/ENTRY.md`.
```

## Pitfalls

- A shared `nativeEntry` means both deltas are concatenated into one file — they must not contradict each other.
- `agentsDir: null` is a real statement, not a placeholder: `agents:install` refuses `--platform <id>` rather than silently doing nothing.
- Hosts whose skills live somewhere other than `<configDir>/skills` (codex uses `.agents/skills`) just declare it in `skillsDir`; do not add a special case to any script.
