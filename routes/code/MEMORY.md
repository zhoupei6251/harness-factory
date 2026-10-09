# Code domain MEMORY

> Auto-loaded when route=code. Persists across sessions.

## Project info
- name: (fill in)
- stack: (fill in)
- language: (fill in)

## Key decisions
- 2026-10-09: Qoder 升为第 5 个正式适配器（此前它的规则「寄生」在 Codex 的 `AGENTS.md` 上）。关键约束：只用 Claude / Codex / Trae / WorkBuddy / Qoder 五端，不为 Cursor、Gemini 等做兼容。顺带修掉一个真 bug——Codex 与 Qoder 共用 `AGENTS.md` 原生入口，原先一对一写文件会互相覆盖，现按 native entry 分组合并 delta。
- 2026-10-09: doctor 的 MCP 门禁由硬「且」（codex ∧ claude）改为跨端「或」，并把「客户端已配」与「仓库片段存在」分开打印——纯 Qoder 机器不再被 `npm run bootstrap` 挡。推翻了同日设计稿里「不改 doctor 代码」那条，更正已回写 spec §6。
- 2026-10-09: `--ui=true` 全量移除（`.mcp.json` / `mcp-config/*` / `references/tooling.md`）——npm 版二进制不含内嵌 UI，该 flag 只产出一行警告。本机 `~/.codex/config.toml` 与 `~/.qoder-cn/settings.json` **未动**（超出批准范围）。
- 2026-10-09: ponytail + codebase-memory-mcp 升级为代码域强制工具——绑定 R1/R2/R8，NEVER.md 加两条禁止项，四端 delta 补接入/验证/降级声明；缺失时声明降级（不默跳），纯文案产出豁免。设计稿：`docs/superpowers/specs/2026-10-09-required-tooling-design.md`
- YYYY-MM-DD: (decision summary)

## In progress
in_progress:
  - current_phase: (planning | implementing | verifying)

## Blockers
blockers: []

## Test status
testing:
  framework: (junit | pytest | ...)
  last_run: YYYY-MM-DD

## Code review
review:
  status: approved
  last_reviewer: requesting-code-review（2026-10-09 工具强制化改动）

## Last updated
last_updated: 2026-10-09T11:14:27
