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
- 2026-10-12: `scripts/validate-schemas.ts` 的 evidence 指针校验不再误判 glob。触发点：`docs/plans/2026-10-12-sample-data-truesource-foundation-design.md:189` 写的是 `⏳ routes/news/evidence/2026-10-12-*-verification-lite.md 落盘`，`EVIDENCE_PTR` 字符类不含 `*`，匹配在星号处截断成 `…/2026-10-12-`，拿去 `git ls-files` 必然落空 ⇒ `npm test` 红在第一关。裁决：名字还没敲定的路径是 TODO 不是交付承诺，规则本就不该认它（原注释「模板路径根本匹配不上，无需特例」对 `<date>` 成立、对 glob 是错的，已更正）。判定收紧为「元字符后还接着路径字符」才算占位符——**这是为了堵住我自己引入的漏洞**：若只看后一个字符，markdown 加粗的真实指针 `**…/x.md**`（`*` 后紧跟 `*`）会被当成占位符跳过，等于把一条在检的守卫悄悄关掉。四条分支逐一实测（工作树临时追加探针、跑完按 sha256 还原）：缺失真路径 → FAIL、glob 占位 → 跳过、加粗已入库路径 → 通过、加粗缺失路径 → FAIL（证明上一条不是假绿）。校验行现在打印跳过条数（`1 glob placeholder(s) skipped`），让豁免可见、可数。**冲突记录**：那行的 `⏳` 已过期——`routes/news/evidence/2026-10-12-sample-data-truesource-foundation-verification-lite.md` 实际已落盘且 tracked；计划文档归作者维护，本轮未代改。
- 2026-10-12: 治理层三处假绿一起修掉。(1) `scripts/check-bootstrap.ts` 重写为**生成器对照法**：把契约输入复制到临时根，用真实 `scripts/bootstrap.ts` 在临时根跑一遍，再逐字节比对工作树产物（`core.autocrlf` 造成的行尾差异豁免）。旧实现是手工维护的 artifact→source 表 + mtime 比较，实测 12 条里 5 条指向 bootstrap 从不写的路径（`.claude/CLAUDE.md` / `.codex/AGENTS.md` / `.qoder/AGENTS.md` / `.codebuddy/AGENTS.md` / `GEMINI.md`——bootstrap 没有 Gemini 适配器，根 `GEMINI.md` 从来不存在），永久 `[skip]` 却打印 "No bootstrap drift detected."；mtime 又让任何 clone / checkout 之后判据自动失效。检查覆盖从 4 条真检查升到 17 个产物 + 根 `MEMORY.md`。(2) 契约（输入清单 + 产物清单 + `isBootstrapOwned`）单一来源化为 `scripts/bootstrap-contract.ts`，check-bootstrap 与两个集成测试共用——这条 bug 的根因就是同一份契约被抄了三遍。(3) `tests/downstream-render.test.ts` 的隔离漏洞：它 spawn `ROOT/scripts/bootstrap.ts` 而 cwd 设成安装副本，bootstrap 从 `import.meta.url` 推 ROOT ⇒ 投影写进本仓库，而它的 "bootstrap produced X" 断言被 :104 复制进来的旧产物满足。现在副本按 fresh-clone 过滤（`.git` / `node_modules` / 全部产物与运行时目录），spawn 副本自己的脚本，并断言本仓库产物 mtime 不变。**坑**：Windows 上 `fs.cp` 递给 filter 的是 `\\?\` 扩展长度路径，不剥前缀一条也滤不掉（旧代码那句"跳过 .git"因此从未生效）。`npm test` 现在串上 `npm run check-bootstrap`。
- 2026-10-12: ARCHITECTURE.md / STRUCTURE.md / README.md 的裸计数断言整批删除（441 / 871 / npm scripts 8 / schemas 3 / "(10 scripts.)" / "(2 files)" / "~870 source files"），只留 `npm run stats` 指针；顺带改正两处事实错误：根 `GEMINI.md` 不是 bootstrap 产物、`*.harness.md` 三个文件是**入库的**生成物（README 原先写"bootstrap 产物一个都不入库"）。判据口径：手抄的当天就过期，能机检的才留。
- 2026-10-12: tests/ → scripts/ refactor — `tests/validate-schemas.ts` and `tests/build-index.ts` moved to `scripts/`. `tests/` now holds only real tests; `scripts/` is the home for validators / builders / indexers. `package.json` `validate` and `index` entries updated. Avoided the trap: **never put non-test code in `tests/`** — the harness validator (`scripts/validate-schemas.ts`) is a 5-stage check (schemas + skills + archive + runtime-dir + evidence pointers), not an assertion test.
- 2026-10-12: `scripts/check-bootstrap.ts` added — detects drift between the gitignored bootstrap outputs and their sources. Catches the "Edit `routes/code/MEMORY.md` actually wrote to root `MEMORY.md`" bug from 2026-10-12 round 1. Run via `npm run check-bootstrap`. **⚠️ 该实现已被同日的重写取代**（见本段开头「重写为生成器对照法」那条）：它当时靠一张手工维护的 artifact→source 表 + mtime 比较，表里 5 条路径指向 bootstrap 从不写的文件。
- 2026-10-12: `scripts/skills-audit.ts` added — surfaces bit-rot risk in `skills/archive/` (51 archived skills). Reports per-skill: SKILL.md presence, _meta.json presence, size, mtime. Run via `npm run skills:audit`. Does not auto-delete; only reports.
- 2026-10-12: `scripts/stats.ts` extended — now reports tracked-file count, git working-tree state (clean / N modified), ahead/behind upstream, runtime dir sizes (flag >1 GiB), and skills/ total entries (incl. INDEX.md + archive/).
- 2026-10-12: Main-only Git workflow is now **explicit** in `ENTRY.md` § "Workflow (this repository only)" — was previously an unstated local convention. Downstream projects still follow `git-xywh`'s three-trunk / five-branch model unchanged. `git push` still requires user ask.
- 2026-10-12: ARCHITECTURE.md / README 的 "Current state" 表改为 `npm run stats` 指针，不再手抄快照——手抄的那批数字（270 / 441 / 871）每一次都当天过期。同日又复发了：手抄的 871 也过期，于是这批计数整批删除（见下条）。
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
last_updated: 2026-10-12T15:51:00
