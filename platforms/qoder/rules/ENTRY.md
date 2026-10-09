# Qoder platform rules

> Qoder-specific deltas. Loaded after the canonical core/ENTRY.md.

## Two config roots — do not confuse them

| Root | Holds | Repo writes to it? |
|------|-------|--------------------|
| `~/.qoder/` | `skills/` (user-installed skills), `extensions/` | via `npm run skills:install` only |
| `~/.qoder-cn/` | CLI config + runtime state: `settings.json` (user scope incl. `mcpServers`), `memory/`, `projects/<slug>/`, `plugins/` | never |

`~/.qoder/shared_client/mcp.json` also exists and is empty (`{ "mcpServers": {} }`) — it is the
desktop IDE's registry, **not** what this CLI reads. Wiring MCP there does nothing.

`config_root` here is the *first* row. The second row is the only adapter-side storage whose
project scope is path-derived (`projects/<workspace-slug>/`), so it is not a copy-pasteable
snippet target — nothing in this repo should try to pre-create it.

## Hooks

Qoder supports hooks (shell commands on tool-call events) declared in settings, and plugins can
ship a `hooks/` directory. `~/.qoder-cn/settings.json` on this machine carries `enabledPlugins`
and `mcpServers` — **no hook key, and this repo wires no Qoder hook**. Governance rides on the
auto-loaded entry file + skills. Adding a hook is a separate decision, not a bootstrap output.

## MCP

Three valid scopes, all real settings files (`mcpServers` is a **top-level** key):

| Scope | File | Committed? |
|---|---|---|
| user | `~/.qoder-cn/settings.json` | no |
| project | `<repo>/.qoder/settings.json` | yes — git |
| local | `<repo>/.qoder/settings.local.json` | no (gitignored) |

⚠️ **The repository root `.mcp.json` is NOT read by Qoder** (Claude Code convention). Verified
live: with only the root `.mcp.json` declaring `codebase_memory`, the server was absent from the
connected MCP list; it appeared only after it was written to the user-scope settings file below.

⚠️ **`command` should be `npx.cmd`, not `npx`, on Windows.** Measured: under
`child_process.spawn(..., { shell: false })` bare `npx` → `ENOENT` while `npx.cmd` → exit 0
(`PATHEXT` is not resolved without a shell). Qoder's own spawn mode was **not** verified, so this
is a safe-config choice rather than a claim about the host; `npx.cmd` works either way. Same
reason `scripts/doctor.ts:42` branches on `win32`. On this端 `mcp-config/codebase-memory.json` is
therefore *not* paste-ready — rewrite that one field.

⚠️ **Drop `--ui=true`** — the npm binary is built without the embedded UI, the flag only emits a
warning. All repo snippets are now clean; see `references/tooling.md` for the full note.

Wiring goes through the built-in `mcp-config` skill, not by hand. Verified live on this machine:
`codebase_memory` at **user** scope with `npx.cmd` connects — 14 tools surface, and
`list_projects` returns this repo (indexed, branch + head reported). The agent **cannot** reload
MCP itself; a config change only takes effect in a new session or after the user runs
`/mcp reload`. Until *that* takes effect, code-domain tasks run **degraded** — say so, per
`references/tooling.md`.

## Skills

Qoder discovers skills in `~/.qoder/skills/` (user scope) and in the current project directory.
The entries there at session start all surface in that session — but the list is collected **once,
at session start**: a skill added mid-session (e.g. the `ponytail` junction below) is on disk and
readable via `Read`, yet absent from the listing until the next session. Treat the listing as a
snapshot, not a live check.
`npm run skills:install -- --platform qoder` junctions active `skills/` into `~/.qoder/skills/`,
so edits under `skills/` stay live. Run on 2026-10-09: 49 repo skills installed, zero name
conflicts with what was already there. ⚠️ Cost — every one of those descriptions is loaded into
**every** Qoder session on this machine, across all projects, not just this repo. Drop back with
`rm ~/.qoder/skills/<name>` (they are symlinks; the repo files are untouched).
Skills bundled inside the Qoder application itself (e.g. `brainstorming`) are not on disk under
either root and are not managed by this repo.

## Tooling（本端接入）

> 代码域强制：改 TS / 脚本 / 测试 / 配置 / 规则文件前，先用 codebase-memory-mcp 取证据（R1）、生成前走 ponytail 决策阶梯（R2 / R8）。纯文案产出豁免。
> 工具缺失或未接通时改用等效手段（Read / Grep），并在回复中声明：
> `[codebase-memory-mcp 不可用，已降级] 原因：<未装 / MCP 未连通 / 索引缺失>；替代手段：<Read / Grep 手工取证>`

- **codebase-memory-mcp**：`mcp-config` skill 写入 `~/.qoder-cn/settings.json` 顶层 `mcpServers`（根 `.mcp.json` 不读，且 Windows 上 `command` 用 `npx.cmd`，见上）
- **ponytail**：Qoder 无 plugin marketplace 通道，走上游「Any other agent」路径——装为 skill。本机实际做法：
  把已安装的 `~/.codex/skills/ponytail` junction 到 `~/.qoder/skills/ponytail`（纯指令型 SKILL.md，120 行，平台无关）。
  因此 `/ponytail lite|full|ultra` 这类**命令级**开关在 Qoder 不可用，只能靠会话内指令切换强度；
  无 hook 强制，属平台能力差异，**不算降级**（同 Trae / WorkBuddy，见 `references/tooling.md`）。
  ⚠️ skill 清单只在**会话启动时**采集：junction 建好后当前会话仍看不到 `ponytail`，需新会话才生效。
  这是宿主 discover 时机，不是配置错误——别据此判断「没装上」。
- **验证**：`mcp_list` 里能看到 `codebase_memory` 工具；让 Agent 调 `list_projects` 能返回；
  `ls ~/.qoder/skills/ponytail/SKILL.md` 存在（in-session 是否可调用另见上）

## Projected to

- `.qoder/rules/ENTRY.md` (this file)
- `.qoder/rules/ROOT.md` (canonical ENTRY.md)
- `AGENTS.md` (native auto-loaded entry, **shared with Codex** — both deltas are merged into this one file)
