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
- 2026-10-19: 三道结构主张 → 机检 + pre-commit 硬门禁 + install roundtrip 烟测，同批落地。(1) `scripts/structure-audit.ts` 新增，把 README/ARCHITECTURE/STRUCTURE 里的散文主张（"8 governance docs"、"5 platforms"、"3 routes"、"3 verticals"、"templates 必备 4 文件"、"INDEX 数字 vs fs"、"禁放位置"）从 prose 升到机检断言。`npm test` 串在 `validate` 之后做硬门禁；实测首跑 12 项全过，发现并修掉 `core/ENTRY.md` 索引表漏列它自己这一处真 drift（核心结论：原先说"7 governance docs"，但 ENTRY.md 自己就是第 8 个；现在改成"8 governance docs"并加注「此文件本身是第 8 个」）。(2) `git-hooks/pre-commit` 源文件 + `scripts/install-hooks.ts`（`npm run hooks:install`）配套：`pre-commit` 跑 `npm run check-bootstrap` 做硬 gate；检测到 sandbox 边界（spawn EPERM / 缺 tsx / npm 不可用）时 warn 但 exit 0——sandbox 不该把"我没法验证"悄悄变成"这次 commit 没事"。装到 `.git/hooks/pre-commit` 后保留可执行权限，且 refuse 覆盖用户自装 hook（除非传 `--force`）。(3) `tests/install-roundtrip.test.ts` 新增——给 install-into-project 装上 byte-equality 烟测：独立 render 一遍 `templates/target-*.md` + fixture，比对 install 写入下游的 `CLAUDE.md`/`AGENTS.md`/`GEMINI.md` 三文件 bytes（CRLF 排除）；二次 install 同 fixture 字节不变；不同 fixture 字节变化（防 fixture 静默被忽略）；`--dry-run` 字节 + mtime 都不动。17 个断言全过。(4) `scripts/skills-archive-review.ts` 新增——按 word-boundary 引用次数对 archive 量化排序：51 archived → 48 候选删除 / 3 仍有引用 / 0 文件缺失 / 1 名称冲突（`archive/karpathy-guidelines` ↔ `core/karpathy-guidelines.md`）；输出"按可达性排序"全表 + 干净 cull 候选清单 + 冲突清单。本期不删任何 skill（reachability 在仓内可机检，仓外假设无信号），决策写进 `docs/superpowers/specs/2026-10-19-skills-archive-phase6-cull-design.md`：下期只删 2 个（`archive/karpathy-guidelines` 冲突 + `archive/novel-debug` 0 KiB 唯一空文件），其余 49 个 archive 按"留个口子"原则保留。降级声明：`[codebase-memory-mcp 不可用] + [ponytail 不可用]`——按 NEVER.md「change code without evidence」走 fs walk + 读源文件手工取证；按 R8 不做"用一次就抽象"的事。**坑**：Windows sandbox ACL 把 `grantWrite` 拒了，`SetNamedSecurityInfoW (Win32 5)`；用 `diagnose-windows-sandbox-acl` skill 补上 `WRITE_OWNER` 后再 verify；同时 sandbox 把 esbuild 的 `spawn EPERM` 视为 grandchild 边界（**预期内**，无需 ACL 修复），对应 unconfined 跑 npm test。**实证**：`npm test` 最终 234 个 `[ok]` / `ok` 断言全过、0 fail，串行 9 个 npm script：validate → structure:audit → typecheck → typecheck:web → check-bootstrap → bootstrap.test → install-template.test → install-roundtrip.test → downstream-render.test → test:web。Hygiene：`.acl-reports/` 加入 `.gitignore`（跟 runtime dump 同性质）。
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
