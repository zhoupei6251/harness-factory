# Code domain MEMORY

> Auto-loaded when route=code. Persists across sessions.
>
> **This file is the canonical code-route MEMORY.** Downstream projects that install harness-factory get a copy in their project root as `MEMORY.md`, and they fill in the `Project info` block with their own values. The `Key decisions` / `In progress` / `Blockers` sections are also per-project — what you see below is harness-factory's own state, included as a worked example.

## Project info (example — harness-factory itself)
- name: harness-factory
- stack: TypeScript 7 (Node ≥20.9), tsx runner, JSON Schema, no runtime deps
- language: TypeScript (Markdown governance docs, Python helper scripts under `skills/douyin-pro/`)
- downstream example: `aigc_platfrom_back` (Java 21 / Spring Boot 3.5.6 / RuoYi-Vue-Plus 5.5.x — uses this harness's code route)

## Key decisions
- 2026-10-12: Main-only Git workflow is now **explicit** in `ENTRY.md` § "Workflow (this repository only)" — was previously an unstated local convention. Downstream projects still follow `git-xywh`'s three-trunk / five-branch model unchanged. `git push` still requires user ask.
- 2026-10-12: ARCHITECTURE.md / README "Current state" tables now derived from `npm run stats` (`scripts/stats.ts`) — both 270 and 441 hardcoded numbers were stale; live count today is 871 source files (21 .ts / 335 .md / 127 .json / 53 .py / 267 .html / 68 other).
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
  framework: tsx (script tests) + node `lib/tsc.js` (typecheck)
  last_run: 2026-10-12

## Code review
review:
  status: approved
  last_reviewer: requesting-code-review（2026-10-12 卫生债 + 文档同步 + 工作流显式化改动）

## Last updated
last_updated: 2026-10-12T11:30:00
