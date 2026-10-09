# 代码域工具强制化（ponytail + codebase-memory-mcp）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 ponytail 与 codebase-memory-mcp 从「推荐工具」升级为代码域开发的强制执行方式，绑定到既有 R1/R2/R8，四个平台（Claude Code / Codex / Trae / WorkBuddy）一次 bootstrap 全部生效。

**Architecture:** 治理文档单源改造——根 `ENTRY.md` 是单一事实源，`scripts/bootstrap.ts` 把它 + `core/ENTRY.md` + `platforms/<端>/rules/ENTRY.md` 拼成四个平台的原生入口（`CLAUDE.md` / `AGENTS.md` / `.trae/rules/project_rules.md` / `.codebuddy/rules/project_rules.md`）。因此改一处即四端生效；各端只补「本端安装 + 验证 + 降级声明」短节。`core/NEVER.md` 不进原生入口，靠 load priority 的 mandatory 加载生效，禁止项写在那里。

**Tech Stack:** Markdown（治理文档）+ TypeScript（`tests/bootstrap.test.ts` 冒烟断言）+ `npm run bootstrap` / `npm run test`（tsx + tsc）。

**Spec:** `docs/superpowers/specs/2026-10-09-required-tooling-design.md`（本计划逐条对应其 §1–§7）

> **提交约定**：每个 Task 末尾的 commit 步骤按仓库既有 Angular 风格（`docs(tooling): ...`）执行；若用户要求不提交，则跳过 commit 步骤并保留工作区改动。

---

## File Structure

| 文件 | 职责 | 动作 |
|------|------|------|
| `tests/bootstrap.test.ts` | bootstrap 冒烟 + 原生入口内容断言（回归护栏） | 修改 |
| `ENTRY.md` | 四端共享的行为规则与工具强制条款（单一事实源） | 修改 |
| `core/NEVER.md` | 禁止项清单（mandatory 加载） | 修改 |
| `platforms/{claude,codex,trae,workbuddy}/rules/ENTRY.md` | 各端接入/验证/降级声明 delta | 修改 ×4 |
| `core/runbooks.md` | 操作手册措辞同步 | 修改 |
| `references/tooling.md` | 安装全集 + 降级语义（详细步骤唯一出处） | 修改 |
| `README.md` | 仓库门面措辞同步 | 修改 |
| `routes/code/MEMORY.md` | code 域记忆源（决策记录） | 修改 |

**不在本计划内**：`scripts/doctor.ts` 校验、`package.json` 依赖、`skills/` 库、根 `MEMORY.md`（bootstrap 投影产物，Task 9 自动更新）。

---

### Task 1: 先写失败断言（原生入口必须带强制条款）

**Files:**
- Modify: `tests/bootstrap.test.ts:2`（import 行）与 `tests/bootstrap.test.ts:159-167`（EXPECTED 断言块之后）

- [ ] **Step 1: 给 `readFile` 加进 import**

把 `tests/bootstrap.test.ts` 第 2 行：

```ts
import { cp, mkdtemp, readdir, realpath, rm, stat } from "node:fs/promises";
```

改为：

```ts
import { cp, mkdtemp, readFile, readdir, realpath, rm, stat } from "node:fs/promises";
```

- [ ] **Step 2: 写内容断言（此时必须失败）**

在 `tests/bootstrap.test.ts` 的 `for (const e of EXPECTED) { ... }` 循环结束之后、`// The repository root must be byte-for-byte unchanged by the smoke test.` 注释之前，插入：

```ts
  // Required-tooling clause must survive into every native entry, and NEVER.md
  // must carry the two forbidden rows (spec: docs/superpowers/specs/
  // 2026-10-09-required-tooling-design.md §1).
  const NATIVE_ENTRIES = [
    "CLAUDE.md",
    "AGENTS.md",
    ".trae/rules/project_rules.md",
    ".codebuddy/rules/project_rules.md",
  ];
  const ENTRY_MARKERS = ["Tooling (required", "降级", "Tooling（本端接入）"];
  for (const entry of NATIVE_ENTRIES) {
    const body = await readFile(resolve(tempRoot, entry), "utf-8");
    const missing = ENTRY_MARKERS.filter((m) => !body.includes(m));
    if (missing.length === 0) {
      console.log(`[ok]   ${entry} carries required-tooling clause`);
    } else {
      console.log(`[FAIL] ${entry} missing markers: ${missing.join(", ")}`);
      fail = 1;
    }
  }

  // core/NEVER.md is loaded by priority, not concatenated into native entries.
  const neverBody = await readFile(resolve(tempRoot, "core", "NEVER.md"), "utf-8");
  for (const marker of ["change code without evidence", "skip the lazy ladder"]) {
    if (neverBody.includes(marker)) {
      console.log(`[ok]   core/NEVER.md forbids "${marker}"`);
    } else {
      console.log(`[FAIL] core/NEVER.md missing forbidden row "${marker}"`);
      fail = 1;
    }
  }
```

- [ ] **Step 3: 跑测试确认失败**

Run: `npm run test`
Expected: **FAIL**，输出里出现 `missing markers: Tooling (required, 降级, Tooling（本端接入）` ×4 与 `core/NEVER.md missing forbidden row` ×2，末尾 `Bootstrap smoke test FAILED.`

（若 typecheck 先挡下，看是否有 `readFile` 未使用之类的报错——断言代码已用到 `readFile`，不应报。）

---

### Task 2: 根 `ENTRY.md` Tooling 小节替换为强制条款

**Files:**
- Modify: `ENTRY.md:48-53`

- [ ] **Step 1: 整节替换**

把 `ENTRY.md` 末尾这一节（含标题行与两行表格）：

```markdown
## Tooling (recommended, per-machine install)

| Tool | Why | Install |
|------|-----|---------|
| codebase-memory-mcp | code knowledge graph — evidence for R1 (read before write); powers `query-symbol` / `get-callers` / `analyze-impact` skills | root `.mcp.json` (Claude Code) or `references/tooling.md` |
| ponytail | lazy-senior-dev decision ladder before any generation — complements R2 / R8 / `core/NEVER.md` | `references/tooling.md` |
```

替换为：

```markdown
## Tooling (required — 代码域强制)

> 两工具是代码域开发的**执行方式**，不是可选附件。
> 适用范围：改 TS / 脚本 / 测试 / 配置 / 规则文件。豁免：纯文案产出（novel / news 稿件）。
> 降级语义：工具未装或未接通时，改用等效手段（Read / Grep），并**在回复中声明降级原因**；禁止默默跳过或假装已用。

| Tool | 绑定规则 | 必须这样做 | Install |
|------|---------|-----------|---------|
| codebase-memory-mcp | R1 | 改代码前用 `analyze-impact` / `get-callers` / `query-symbol` 拿图谱证据 | 根 `.mcp.json` 或 `references/tooling.md` |
| ponytail | R2 / R8 | 生成前走七级决策阶梯（不写→复用→库→原生→依赖→一行→最小实现） | `references/tooling.md` |
```

- [ ] **Step 2: 肉眼确认 R1-R8 表未被动过**

Run: `npm run typecheck`
Expected: 通过（本 Task 无 TS 改动，只是确认没误伤）。

- [ ] **Step 3: Commit**

```bash
git add ENTRY.md tests/bootstrap.test.ts
git commit -m "docs(tooling): 两工具升级为代码域强制，绑定 R1/R2/R8 并加原生入口断言"
```

---

### Task 3: `core/NEVER.md` 加两行禁止项

**Files:**
- Modify: `core/NEVER.md:12-13`（表格末尾追加）

- [ ] **Step 1: 追加两行**

在 `core/NEVER.md` 表格 `| "大概"/"差不多" in code | slop | exact match or fail |` 这一行**之后**追加：

```markdown
| change code without evidence | guessing | query graph first; if MCP down, degrade and say so |
| skip the lazy ladder | over-build | ponytail ladder first; if unavailable, say so |
```

- [ ] **Step 2: Commit**

```bash
git add core/NEVER.md
git commit -m "docs(tooling): NEVER.md 加「无证据不改代码 / 不跳生成阶梯」禁止项"
```

---

### Task 4: 四端 `platforms/<端>/rules/ENTRY.md` 各加接入小节

四段结构完全一致，只有装法与验证三行不同。**标题必须是 `## Tooling（本端接入）`**（Task 1 的断言靠这个标记）。

**Files:**
- Modify: `platforms/claude/rules/ENTRY.md`、`platforms/codex/rules/ENTRY.md`、`platforms/trae/rules/ENTRY.md`、`platforms/workbuddy/rules/ENTRY.md`

- [ ] **Step 1: Claude Code delta**

在 `platforms/claude/rules/ENTRY.md` 的 `## Projected to` 小节**之前**插入：

```markdown
## Tooling（本端接入）

> 代码域强制：改 TS / 脚本 / 测试 / 配置 / 规则文件前，先用 codebase-memory-mcp 取证据（R1）、生成前走 ponytail 决策阶梯（R2 / R8）。纯文案产出豁免。
> 工具缺失或未接通时改用等效手段（Read / Grep），并在回复中声明：
> `[codebase-memory-mcp 不可用，已降级] 原因：<未装 / MCP 未连通 / 索引缺失>；替代手段：<Read / Grep 手工取证>`

- **ponytail**：会话内 `/plugin marketplace add DietrichGebert/ponytail` → `/plugin install ponytail@ponytail`（两次独立确认）
- **codebase-memory-mcp**：根 `.mcp.json` 已提交，首次打开接受启用提示即可
- **验证**：`/ponytail-help` 有输出；让 Agent 调 `list_projects` 能返回

```

- [ ] **Step 2: Codex delta**

在 `platforms/codex/rules/ENTRY.md` 的 `## Projected to` 小节**之前**插入（引言三行与 Step 1 **逐字相同**）：

```markdown
## Tooling（本端接入）

> 代码域强制：改 TS / 脚本 / 测试 / 配置 / 规则文件前，先用 codebase-memory-mcp 取证据（R1）、生成前走 ponytail 决策阶梯（R2 / R8）。纯文案产出豁免。
> 工具缺失或未接通时改用等效手段（Read / Grep），并在回复中声明：
> `[codebase-memory-mcp 不可用，已降级] 原因：<未装 / MCP 未连通 / 索引缺失>；替代手段：<Read / Grep 手工取证>`

- **ponytail**：`codex plugin marketplace add DietrichGebert/ponytail` → `codex plugin add ponytail@ponytail`，再开 `/hooks` 信任它的两个 lifecycle hook，然后新起线程
- **codebase-memory-mcp**：把 `mcp-config/codebase-memory.codex.toml` 并入 `~/.codex/config.toml`
- **验证**：`/ponytail-help` 有输出；让 Agent 调 `list_projects` 能返回

```

- [ ] **Step 3: Trae delta**

在 `platforms/trae/rules/ENTRY.md` 的 `## Projected to` 小节**之前**插入（引言三行同上）：

```markdown
## Tooling（本端接入）

> 代码域强制：改 TS / 脚本 / 测试 / 配置 / 规则文件前，先用 codebase-memory-mcp 取证据（R1）、生成前走 ponytail 决策阶梯（R2 / R8）。纯文案产出豁免。
> 工具缺失或未接通时改用等效手段（Read / Grep），并在回复中声明：
> `[codebase-memory-mcp 不可用，已降级] 原因：<未装 / MCP 未连通 / 索引缺失>；替代手段：<Read / Grep 手工取证>`

- **ponytail**：Trae 无插件系统 → 装为 skill（上游 `skills/ponytail/SKILL.md`）或复制上游 `AGENTS.md` 精简版进项目规则；纯指令约束、无 hook 强制，属能力差异不算降级
- **codebase-memory-mcp**：设置 → MCP → 添加服务器，粘贴 `mcp-config/codebase-memory.json` 内容
- **验证**：规则版新会话问「阶梯当前档位」有回答；skill 版 `/ponytail-help` 有输出；`list_projects` 能返回

```

- [ ] **Step 4: WorkBuddy delta**

在 `platforms/workbuddy/rules/ENTRY.md` 的 `## Projected to` 小节**之前**插入（引言三行同上）：

```markdown
## Tooling（本端接入）

> 代码域强制：改 TS / 脚本 / 测试 / 配置 / 规则文件前，先用 codebase-memory-mcp 取证据（R1）、生成前走 ponytail 决策阶梯（R2 / R8）。纯文案产出豁免。
> 工具缺失或未接通时改用等效手段（Read / Grep），并在回复中声明：
> `[codebase-memory-mcp 不可用，已降级] 原因：<未装 / MCP 未连通 / 索引缺失>；替代手段：<Read / Grep 手工取证>`

- **ponytail**：WorkBuddy 无插件系统 → 装为 skill（上游 `skills/ponytail/SKILL.md`）或复制上游 `AGENTS.md` 精简版进项目规则；纯指令约束、无 hook 强制，属能力差异不算降级
- **codebase-memory-mcp**：MCP server 写进 `.codebuddy/mcp.json`（即 `~/.codebuddy/mcp.json`）
- **验证**：规则版新会话问「阶梯当前档位」有回答；skill 版 `/ponytail-help` 有输出；`list_projects` 能返回

```

- [ ] **Step 5: Commit**

```bash
git add platforms/claude/rules/ENTRY.md platforms/codex/rules/ENTRY.md platforms/trae/rules/ENTRY.md platforms/workbuddy/rules/ENTRY.md
git commit -m "docs(tooling): 四端 delta 补工具接入/验证/降级声明"
```

---

### Task 5: `core/runbooks.md` 措辞同步

**Files:**
- Modify: `core/runbooks.md:9-15`

- [ ] **Step 1: 标题与正文升级为 required**

把：

```markdown
## Install recommended tooling (per machine, one-time)

Full guide: `references/tooling.md`. Both tools are local and free — no API keys.
```

改为：

```markdown
## Install required tooling (code domain, per machine, one-time)

Full guide: `references/tooling.md`. Both tools are local and free — no API keys.
**Required for code-domain work** (TS / scripts / tests / config / rules files); prose-only output (novel / news drafts) is exempt.
```

- [ ] **Step 2: 第 3 步补降级声明格式**

把：

```markdown
3. Verify: ask the agent to call `list_projects` (MCP connected) and run `/ponytail-help` (plugin loaded)
```

改为：

```markdown
3. Verify: ask the agent to call `list_projects` (MCP connected) and run `/ponytail-help` (plugin loaded)
4. If a tool is missing or disconnected, the agent must degrade to Read / Grep and state it in the reply:
   `[codebase-memory-mcp 不可用，已降级] 原因：<...>；替代手段：<...>` — never skip silently
```

- [ ] **Step 3: Commit**

```bash
git add core/runbooks.md
git commit -m "docs(tooling): runbooks 工具小节升级为 required 并补降级声明格式"
```

---

### Task 6: `references/tooling.md` 措辞 + Trae/WorkBuddy 装法修正 + 降级语义

**Files:**
- Modify: `references/tooling.md:1-5`、`references/tooling.md:96`、`references/tooling.md:118-122`

- [ ] **Step 1: 首段推荐 → 强制**

把：

```markdown
# tooling.md — 推荐外部工具：ponytail + codebase-memory-mcp

> 本仓库推荐所有使用者安装以下两个工具。两者均为**本地运行、免费开源**，无需任何 API Key，
> 符合仓库安全条款（禁止真实密码 / Key / 私钥入库）。
> 安装状态属于**每台机器一次性配置**，不随 `npm run bootstrap` 渲染。
```

改为：

```markdown
# tooling.md — 代码域强制工具：ponytail + codebase-memory-mcp

> 代码域开发（改 TS / 脚本 / 测试 / 配置 / 规则文件）**强制**使用以下两个工具；纯文案产出（novel / news 稿件）豁免。
> 两者均为**本地运行、免费开源**，无需任何 API Key，符合仓库安全条款（禁止真实密码 / Key / 私钥入库）。
> 安装状态属于**每台机器一次性配置**，不随 `npm run bootstrap` 渲染。
> 缺失或未接通时**声明降级**：改用等效手段（Read / Grep）并在回复中说明原因，禁止默默跳过。详见文末「降级语义」。
```

- [ ] **Step 2: ponytail 表格里 Trae / WorkBuddy 行按上游官方装法修正**

把：

```markdown
| **Trae / WorkBuddy**（无插件系统） | 指令文件方式：clone 上游仓库，把其中的规则文件（如 `AGENTS.md` / `.cursor/rules/` 下的 ponytail 规则）复制到平台的项目规则目录，作为纯指令生效（无 hook 强制，靠规则文本约束） |
```

改为：

```markdown
| **Trae / WorkBuddy**（无插件系统） | 按上游官方「Any other agent」路径二选一：① 装为 skill（上游 `skills/ponytail/SKILL.md`）；② 复制上游 `AGENTS.md` 精简版进项目规则。纯指令生效、无 hook 强制——这是平台能力差异，不算「降级」 |
```

- [ ] **Step 3: 「与本仓库治理的关系」小节升级措辞并补「降级语义」小节**

把：

```markdown
## 与本仓库治理的关系

- **R1（Read before write）**：改动前用 `analyze-impact` / `get-callers` 拿图谱证据，而不是凭感觉。
- **R2 / R8 / NEVER.md**：ponytail 把「先问能不能不写」从文档约定变成生成前的强制检查，二者同向。
- **最小改动原则**：两工具都不进 `package.json` 依赖、不被 bootstrap 渲染——它们是每台机器的环境配置，仓库只提供配置片段（`.mcp.json`、`mcp-config/`）与本文档。
```

改为：

```markdown
## 与本仓库治理的关系

- **R1（Read before write）**：改动前用 `analyze-impact` / `get-callers` 拿图谱证据，而不是凭感觉。
- **R2 / R8 / NEVER.md**：ponytail 把「先问能不能不写」从文档约定变成生成前的强制检查，二者同向；`core/NEVER.md` 另有两条禁止项（无证据不改代码 / 不跳生成阶梯）。
- **强制范围**：改 TS / 脚本 / 测试 / 配置 / 规则文件必用两工具；纯文案产出（novel / news 稿件）豁免，交由 route 自身规则治理。
- **最小改动原则**：两工具都不进 `package.json` 依赖、不被 bootstrap 渲染——它们是每台机器的环境配置，仓库只提供配置片段（`.mcp.json`、`mcp-config/`）与本文档。

## 降级语义

工具未装或未接通时，**声明降级**，不要默默跳过、不要假装已用：

```
[codebase-memory-mcp 不可用，已降级] 原因：<未装 / MCP 未连通 / 索引缺失>；替代手段：<Read / Grep 手工取证>。
[ponytail 不可用，已降级] 原因：<未装 / 插件未启用>；替代手段：<按 R2/R8 手工走决策阶梯>。
```

降级只覆盖**工具缺失 / 未接通**。Trae / WorkBuddy 上 ponytail 无 hook 强制（纯指令生效）属于平台能力差异，照常用，不算降级。
```

- [ ] **Step 4: Commit**

```bash
git add references/tooling.md
git commit -m "docs(tooling): tooling.md 升级为强制口径，修正 Trae/WorkBuddy 装法，补降级语义"
```

---

### Task 7: `README.md` 措辞同步

**Files:**
- Modify: `README.md:83`

- [ ] **Step 1: 推荐 → 强制**

把：

```markdown
Two recommended external tools — both local, free, no API keys. Full per-platform install guide: [`references/tooling.md`](references/tooling.md).
```

改为：

```markdown
Two **required** external tools for code-domain work (prose-only output is exempt) — both local, free, no API keys. Full per-platform install guide: [`references/tooling.md`](references/tooling.md).
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs(tooling): README 工具小节改为 required 口径"
```

---

### Task 8: 决策记录落 `routes/code/MEMORY.md`

**Files:**
- Modify: `routes/code/MEMORY.md:10-11`、`routes/code/MEMORY.md:31`

> **注意**：根 `MEMORY.md` 是 `npm run bootstrap` 的投影产物（`routes/code/MEMORY.md` → `./MEMORY.md`），**不要改根 `MEMORY.md`**，Task 9 会自动覆盖。

- [ ] **Step 1: 写决策条目**

把：

```markdown
## Key decisions
- YYYY-MM-DD: (decision summary)
```

改为：

```markdown
## Key decisions
- 2026-10-09: ponytail + codebase-memory-mcp 升级为代码域强制工具——绑定 R1/R2/R8，NEVER.md 加两条禁止项，四端 delta 补接入/验证/降级声明；缺失时声明降级（不默跳），纯文案产出豁免。设计稿：`docs/superpowers/specs/2026-10-09-required-tooling-design.md`
- YYYY-MM-DD: (decision summary)
```

- [ ] **Step 2: 更新 last_updated**

把：

```markdown
last_updated: YYYY-MM-DDTHH:MM:SS
```

改为（用执行时的本地时间替换，格式不变）：

```markdown
last_updated: 2026-10-09T00:00:00
```

- [ ] **Step 3: Commit**

```bash
git add routes/code/MEMORY.md
git commit -m "docs(tooling): code 域记忆写入工具强制化决策"
```

---

### Task 9: bootstrap 渲染四端 + 全量验收

**Files:**
- 生成（不手改）：`CLAUDE.md`、`AGENTS.md`、`.trae/rules/project_rules.md`、`.codebuddy/rules/project_rules.md`、`.*/rules/ENTRY.md`、`.*/rules/ROOT.md`、根 `MEMORY.md`

- [ ] **Step 1: 渲染**

Run: `npm run bootstrap -- --platform all --route code`
Expected: 输出 8 行 `[ok]`（四端 rules/ + 四端 native entry）+ route 投影 + runtime 目录，末尾 `Harness Factory bootstrap complete (platform=all, route=code).`

- [ ] **Step 2: 跑全量测试（Task 1 的断言此时转绿）**

Run: `npm run test`
Expected: `validate` 通过、`typecheck` 通过、`Bootstrap smoke test passed.`，且看到 4 行 `carries required-tooling clause` + 2 行 `core/NEVER.md forbids "..."`。

- [ ] **Step 3: 人工验收 grep（验收标准 1 与 3）**

Run（PowerShell）：

```powershell
Select-String -Path CLAUDE.md,AGENTS.md,.trae/rules/project_rules.md,.codebuddy/rules/project_rules.md -SimpleMatch -Pattern "Tooling (required","Tooling（本端接入）","降级"
```

Expected: 四个文件各自都命中三个标记（合计 ≥ 12 行命中；`-SimpleMatch` 必须带，否则括号会被当正则分组）。

再确认没有遗留推荐口径：

```powershell
Select-String -Path ENTRY.md,README.md,references/tooling.md,core/runbooks.md -SimpleMatch -Pattern "recommended tooling","推荐所有使用者安装","Two recommended external tools"
```

Expected: **无输出**（0 命中）。

- [ ] **Step 4: Commit（只提交源文件；投影产物不入库）**

`CLAUDE.md` / `AGENTS.md` / `.claude` / `.codex` / `.trae` / `.codebuddy` / 根 `MEMORY.md` 全是 bootstrap 投影产物，已在 `.gitignore:16-22` 忽略且未被 git 跟踪——**不要 `git add` 它们**（会报 ignored 错误）。本轮入库的只有源文件：

```bash
git add ENTRY.md README.md core/NEVER.md core/runbooks.md references/tooling.md routes/code/MEMORY.md platforms/claude/rules/ENTRY.md platforms/codex/rules/ENTRY.md platforms/trae/rules/ENTRY.md platforms/workbuddy/rules/ENTRY.md tests/bootstrap.test.ts
git commit -m "docs(tooling): 两工具升级为代码域强制（R1/R2/R8 绑定 + NEVER 禁止项 + 四端接入）"
```

---

### Task 10: 代码审查（按仓库规范走 requesting-code-review）

**Files:** 无新改动，只审查。

- [ ] **Step 1: 调用 `requesting-code-review` skill**

对 Task 1–9 的全部改动做统一审查，重点核对：
- 设计稿 §1 验收四条是否逐条达成；
- 四端 delta 引言三行是否逐字一致（Task 1 的断言只查标记，不查引言一致性）；
- 是否误改了 bootstrap 投影产物（根 `MEMORY.md`、`.*/rules/ROOT.md` 只能由 bootstrap 生成）。

- [ ] **Step 2: 处置审查结论**

有问题就修（改完重跑 `npm run test`）；无问题则在 `routes/code/MEMORY.md` 的 `review:` 块写 `status: approved`、`last_reviewer: <审查实例>`，并按用户要求决定是否提交。

---

## Self-Review 记录

1. **Spec 覆盖**：§1 四条验收 → Task 9 Step 2/3 + Task 1 断言；§2 范围边界 → Task 2 条款文本；§3.1 → Task 2；§3.2 → Task 3；§3.3 → Task 4；§3.4 → Task 5/6/7；§4 降级格式 → Task 4 引言 + Task 6 降级语义小节；§5 清单 8 项 → Task 2–9；§6 非目标 → 未在计划中出现（正确）；§7 风险「delta 过长」→ Task 4 每端 ≤10 行。无缺口。
2. **占位符扫描**：Task 8 Step 2 的 `2026-10-09T00:00:00` 是待执行时替换的真实时间格式示例，已在步骤里写明替换规则，不算 TBD；其余步骤均给出可直接粘贴的完整文本与命令。无其它占位符。
3. **类型/命名一致性**：Task 1 的 `NATIVE_ENTRIES` / `ENTRY_MARKERS` / `neverBody` 均在插入块内自洽；标记串 `Tooling (required`、`Tooling（本端接入）`、`change code without evidence`、`skip the lazy ladder` 与 Task 2/3/4 的产出文本逐字一致（含全角括号 `（本端接入）`）。
