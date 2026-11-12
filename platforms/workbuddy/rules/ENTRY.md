# WorkBuddy platform rules

## 入口（本端读哪个文件）

- WorkBuddy 兼容 `CODEBUDDY.md`、`.codebuddy/CODEBUDDY.md`、`AGENTS.md` 与用户级 `~/.codebuddy/`；本项目统一走项目根 `AGENTS.md`，与 Codex / Qoder 共用同一入口，三端 delta 合并进同一个文件。
- 因此不要再把同一份项目鸟瞰写进 `.codebuddy/rules/`：`AGENTS.md` 与项目规则目录都会自动注入，双写等于同一份上下文注入两遍。
- `.codebuddy/` 是代码开发的项目级配置根（`rules/`、`agents/`、`skills/`、`commands/`、`CODEBUDDY.md`），可随仓库提交；`.workbuddy/` 是 Agent 工作态（记忆/会话数据），不入库，两者不要混用。

## Tooling（本端接入）

- Skills: `npm run skills:install -- --platform workbuddy --target <project>` links the curated core into `.codebuddy/skills/`; omit target for the user scope, use `--profile all` for the legacy catalog. Host skill trust/discovery is separate from file installation.
- Agents: `npm run agents:install -- --platform workbuddy --target <project>` writes thin wrappers into `.codebuddy/agents/`; the contract stays in `agents/`.
- MCP: the user-level entry is `~/.workbuddy/mcp.json`; project-level MCP belongs to the `.codebuddy/` config root. The repository `.mcp.json` is not WorkBuddy's configuration target. Setup details are in `references/tooling.md`.
- Ponytail runs as a skill/instruction. Do not assume plugin commands or lifecycle hooks.
- Verify MCP once with `list_projects`; apply canonical evidence/降级 rules.
- WorkBuddy hook approvals are host configuration, not bootstrap output.

Bootstrap projects this delta to `.codebuddy/harness/ENTRY.md` and merges it into the shared `AGENTS.md`; there is no separate `.codebuddy` native entry file.
