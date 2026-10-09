# 文件产物分级契约 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把「证据必须进版本管理、工作态必须不进」从散文口径升级为可执行断言，并把 9 份 news 契约证据从被 gitignore 的 runtime 目录迁到 `routes/news/evidence/`。

**Architecture:** 五类文件产物分级（工厂自身 / 自产物料 / 证据 / 工作态 / 生成物）。证据的家改为路级版本管理目录 `routes/<route>/evidence/`，脚本按「被检对象」分家（管线本体留 `skills/douyin-pro/scripts/`，路契约留 `routes/news/scripts/`）。三条断言全部落在既有 `tests/validate-schemas.ts` 的 `[ok]/[FAIL]` 脚本风格里，不新增测试文件、不新增 npm script。

**Tech Stack:** TypeScript（`tsx` 执行，ESM，`node:` 前缀导入）、Git（`git ls-files` / `git mv` / `git rm`）、Markdown 治理文档、Python 管线脚本（本计划不改动其内容）。

**Spec:** `docs/superpowers/specs/2026-10-09-file-artifact-class-contract-design.md`（本文是该 spec 的执行拆分；spec §9 是最终验收清单）

## Global Constraints

- 平台集合恒为 5：`claude` / `codex` / `trae` / `workbuddy` / `qoder`（`schemas/platform.schema.json:6` enum、`scripts/bootstrap.ts:12` `PLATFORMS`）——不做 Cursor / Gemini 兼容。
- 测试一律走既有链路：`npm run validate` → `tsx tests/validate-schemas.ts`；`npm test` → `validate && typecheck && tsx tests/bootstrap.test.ts`。**不新增 npm script**。
- 每个 Task 结束时 `npm test` 必须为绿才允许 commit；红色只允许出现在「破坏性自测」步骤内，且同步骤还原。
- runtime 目录恒为 3：`.harness-news-runtime/`、`.harness-novel-runtime/`、`.ai-runtime-artifacts/`（`.gitignore:24-25,37`），全部保持忽略。
- Windows / Git Bash 环境：`git ls-files` 输出正斜杠路径；`sed -i` 可用；**禁止**用 `git stash`（共享工作树）。
- 未获用户明确指示不得 `git push`。
- 代码域改动（TS / 脚本 / 配置 / 规则文件）前先拿图谱证据或显式声明降级：`[codebase-memory-mcp 不可用，已降级] 原因：<…>；替代手段：<Read / Grep 手工取证>`。
- 只改本计划列出的行；同文件其他内容不动（R3 surgical edits）。

## File Structure

| 文件 | 职责变化 |
|---|---|
| `routes/news/evidence/` | **新建**。news 路契约证据（验证单）唯一之家；9 个文件 |
| `tests/validate-schemas.ts` | **新增 3 个校验函数**：`validateRuntimeDirs`（断言②）、`validateEvidence`（断言①）、`validateDocCounts`（断言③） |
| `.gitignore` | 不改（断言②锁的是「别再抢救回去」） |
| `routes/news/ARCHITECTURE.md` | 8 处指针改写 + `:188` 目录图 + `:193-199` 口径重写 |
| `core/routing.md` | 路由表增 Evidence dir 列 |
| `ARCHITECTURE.md`（根） | 删无口径数字行、修 `:25` 自相矛盾、Skills 计数改指向 INDEX |
| `routes/news/MEMORY.md` `:302`、`RUNBOOK-first-run.md` `:90`、`ledger.jsonl` `:45`、`skills/fact-check/SKILL.md` `:79`、`docs/superpowers/plans/2026-10-09-news-render-speedup.md` ×5 | 指针 / 生产路径改写 |
| `routes/news/scripts/{fix_decision_table,fix_stale_doc_claims,remap_pack_colors}.py`、`skills/.skills_store_lock.json` | `git rm` |

已实测的前置事实（写计划时核过，执行时无需重测但可复核）：
- `git ls-files` 下有且只有 8 个 runtime 路径，全在 `.harness-news-runtime/verifications/`；第 9 份 `2026-10-08-t002-fact-check.md` 在盘上但未被追踪（`routes/news/ledger.jsonl:45` 是指向它的死指针）。
- 全仓对证据的引用**一律带完整前缀**：`git grep -l "verification-lite\|render-speedup-verification\|t002-fact-check"` 命中集 == `git grep -l "harness-news-runtime/verifications"` 命中集。所以一次前缀替换即全覆盖，不存在裸文件名引用。
- 证据文件内部互引 3 个文件 4 行也带该前缀，同批替换。
- `scripts/install-skills.ts` 不引用 `skills/.skills_store_lock.json`（`git grep -l skills_store_lock` 只命中 spec 自身）。
- `routes/news/scripts/` 现有 10 个 `.py`，其中 `fix_decision_table.py`、`fix_stale_doc_claims.py`、`remap_pack_colors.py` 仓库内零引用。
- 断言①的逻辑已在**当前状态**预跑过（一次性探针脚本，跑完即删）：扫描 279 个被追踪的 `.md`/`.jsonl`，命中 8 条 —— 正好是 Task 1 要改的那 8 个文件（3 份证据互引 + ARCHITECTURE + MEMORY + RUNBOOK + ledger + fact-check SKILL），且 `routes/*/evidence/` 活指针当前为 0 条。所以 Task 1 完成后 Task 2 的断言落地即为绿；`docs/superpowers/**` 被排除，plan 文档不出现在红名单里。
- 断言①的扫描范围比 spec §4 列举的（`routes/**` + `skills/**/SKILL.md`）**放宽到全部**被追踪 `.md`/`.jsonl`（仍排除 `docs/superpowers/**`）：预跑证明放宽部分不产生假阳性，而窄范围会漏掉 `skills/fact-check/SKILL.md` 之外的将来生产端。执行者不必回头改 spec。

---

### Task 1: 证据归位（断言② + 迁移 9 份 + 21 处指针改写）

本 Task 把「断言」和「让它绿」放在一个提交里：先写断言②看它红（8 条 runtime 路径），再迁移，转绿。分两个提交会让仓库在中途处于 `npm test` 红态。

**Files:**
- Create: `routes/news/evidence/`（目录，含 9 个 `.md`）
- Modify: `.harness-news-runtime/verifications/`（8 个被 `git mv` 走）+ 盘上第 9 份被 `git add`
- Modify: `tests/validate-schemas.ts`（加 `validateRuntimeDirs`）
- Modify: `routes/news/ARCHITECTURE.md`（`:170` `:171` `:310` `:319` `:339` `:352` `:366` `:376`）
- Modify: `routes/news/MEMORY.md:302`、`routes/news/RUNBOOK-first-run.md:90`、`routes/news/ledger.jsonl:45`
- Modify: `skills/fact-check/SKILL.md:79`
- Modify: `docs/superpowers/plans/2026-10-09-news-render-speedup.md`（`:32` `:628` `:668` `:671` `:687`）
- Modify: `routes/news/evidence/2026-09-29-aigc-badge-bottom-left-floor-verification-lite.md`（`:221` `:245`）、`.../2026-09-29-aigc-posture-file-verification-lite.md`（`:210`）、`.../2026-09-29-layout-selfcheck-no-empty-pass-verification-lite.md`（`:102`）

**Interfaces:**
- Consumes: 无（本计划第一个 Task）
- Produces: `routes/news/evidence/*.md` 9 个被追踪文件；`validateRuntimeDirs()`；`trackedFiles()` 辅助函数与 `RUNTIME_DIRS` 常量 —— Task 2 的 `validateEvidence()` 直接复用这两个符号。

- [ ] **Step 1: 加 import 与常量**

在 `tests/validate-schemas.ts` 顶部 import 块后追加（保持现有 `readFile/readdir/stat` 等导入不动）：

```ts
import { execFileSync } from "node:child_process";
```

在 `const SKILLS_DIR = ...` 之后追加：

```ts
// Runtime dirs are ignorable by contract (see core/routing.md). Anything tracked
// under one is an ad-hoc `git add -f` rescue that the next clone will lose.
const RUNTIME_DIRS = [".harness-news-runtime", ".harness-novel-runtime", ".ai-runtime-artifacts"];

function trackedFiles(): string[] {
  return execFileSync("git", ["ls-files"], { cwd: ROOT, encoding: "utf-8" })
    .split(/\r?\n/)
    .filter(Boolean);
}

async function validateRuntimeDirs(): Promise<void> {
  const offenders = trackedFiles().filter((p) => RUNTIME_DIRS.some((d) => p.startsWith(`${d}/`)));
  if (offenders.length === 0) {
    console.log(`[ok]   no tracked file under a runtime dir (${RUNTIME_DIRS.join(", ")})`);
  } else {
    for (const p of offenders) console.log(`[FAIL] runtime content must not be tracked: ${p}`);
    fail = 1;
  }
}
```

并在文件末尾的调用序列里追加一行（放在 `await validateArchiveSkills();` 之后）：

```ts
await validateRuntimeDirs();
```

- [ ] **Step 2: 跑测试，确认它如实报红**

Run: `npm run validate`
Expected: 末段出现 8 行 `[FAIL] runtime content must not be tracked: .harness-news-runtime/verifications/...`，进程 exit 1。**若红条数不是 8，停下**——说明盘上追踪状态与本计划前提不符，先向用户报告再继续。

- [ ] **Step 3: 建目录并迁移 8 份已追踪证据**

```bash
mkdir -p routes/news/evidence
git ls-files .harness-news-runtime/verifications | while read -r f; do
  git mv "$f" "routes/news/evidence/$(basename "$f")"
done
git ls-files routes/news/evidence | wc -l
```
Expected: `8`

（用 `git ls-files` 驱动而不是 glob：盘上 `verifications/` 里有 15 个文件，其中 7 个从未被追踪 —— glob 会让 `git mv` 对它们逐个报 fatal 噪声，而追踪集才是本 Task 的迁移对象。）

- [ ] **Step 4: 把第 9 份（ledger 死指针的证据）移入并提交**

```bash
mv .harness-news-runtime/verifications/2026-10-08-t002-fact-check.md \
   routes/news/evidence/2026-10-08-t002-fact-check.md
git add routes/news/evidence/2026-10-08-t002-fact-check.md
git ls-files routes/news/evidence | wc -l
```
Expected: `9`（这一步同时修掉 `ledger.jsonl` 指向一个 clone 后不存在文件的死指针）

（用 `mv` 而不是 `git mv`：这份从未被追踪，`git mv` 会报 fatal。目标目录不在 `.gitignore` 里，所以 `git add` 不需要 `-f`。）

- [ ] **Step 5: 一次性替换全部证据前缀（21 行，12 个文件）**

`docs/superpowers/**` 也在这批里改写路径，但**只改 `plans/2026-10-09-news-render-speedup.md` 的 5 处可执行命令与产出路径**；spec 与既往 plan 的叙述性回顾保持原样（见 spec §9 的允许项）。

```bash
sed -i 's#\.harness-news-runtime/verifications/#routes/news/evidence/#g' \
  routes/news/ARCHITECTURE.md \
  routes/news/MEMORY.md \
  routes/news/RUNBOOK-first-run.md \
  routes/news/ledger.jsonl \
  skills/fact-check/SKILL.md \
  docs/superpowers/plans/2026-10-09-news-render-speedup.md \
  routes/news/evidence/2026-09-29-aigc-badge-bottom-left-floor-verification-lite.md \
  routes/news/evidence/2026-09-29-aigc-posture-file-verification-lite.md \
  routes/news/evidence/2026-09-29-layout-selfcheck-no-empty-pass-verification-lite.md

# `git add -f` was only needed because the old home was ignored; drop the flag.
sed -i 's#git add -f routes/news/evidence/#git add routes/news/evidence/#g' \
  docs/superpowers/plans/2026-10-09-news-render-speedup.md

git grep -n "harness-news-runtime/verifications" -- . ':!docs/superpowers' | cat
```
Expected: 最后一条 `git grep` **无输出**。豁免范围是**整个** `docs/superpowers/`（spec + plan 都是执行记录，plan 正文里那些反向 sed 与自测处方**必须**保留旧路径字符串才跑得起来），与断言①的扫描口径同源。若活文档（`routes/` `skills/` `core/` `platforms/` `ARCHITECTURE.md`）里还有命中，逐行改到空为止。

- [ ] **Step 6: 跑测试转绿**

Run: `npm run validate`
Expected: `[ok]   no tracked file under a runtime dir (...)`，无 `[FAIL]`，exit 0

- [ ] **Step 7: 全链路 + 类型检查**

Run: `npm test`
Expected: `All validations passed.`，且 `typecheck` 与 `bootstrap.test.ts` 均无错误。

- [ ] **Step 8: Commit**

```bash
git add -A routes/news skills/fact-check docs/superpowers/plans/2026-10-09-news-render-speedup.md tests/validate-schemas.ts
git status --short | cat
git commit -m "refactor(news): 契约证据从可忽略 runtime 目录迁到 routes/news/evidence/

9 份验证单（8 个 git mv + 补回 ledger 指向却从未追踪的第 9 份），21 处证据
前缀改写，并加断言锁死「runtime 目录不得有追踪文件」——旧口径靠 git add -f
人肉抢救，已经静默失败过一次。"
```
Expected: 提交成功；`git status --short` 在此之前只列出本 Task 触及的文件（若列出别的，别 `git add -A` 进来，改用逐路径 add）。

---

### Task 2: 断言① —— 证据活指针必须可解析，且不许回潮

**Files:**
- Modify: `tests/validate-schemas.ts`（加 `validateEvidence()`，复用 Task 1 的 `trackedFiles()`）

**Interfaces:**
- Consumes: `trackedFiles(): string[]`、`ROOT`
- Produces: `validateEvidence()`，并注册进末尾调用序列

- [ ] **Step 1: 写断言**

在 `validateRuntimeDirs` 之后追加：

```ts
// Evidence pointers are live: a tracked doc naming an evidence file is a promise
// that file ships with the repo. Template paths (`<date>-…`) can't match this
// pattern at all, because `<` is outside the allowed charset — no special case.
const EVIDENCE_PTR = /routes\/[a-z0-9-]+\/evidence\/[A-Za-z0-9._\-/]+/g;
const OLD_EVIDENCE_HOME = ".harness-news-runtime/verifications/";

async function validateEvidence(): Promise<void> {
  const tracked = new Set(trackedFiles());
  // docs/superpowers/** is the historical record; its prose may name retired paths.
  const docs = [...tracked].filter((p) => /\.(md|jsonl)$/.test(p) && !p.startsWith("docs/superpowers/"));
  let bad = 0;
  for (const p of docs) {
    const text = await readFile(join(ROOT, p), "utf-8");
    for (const m of text.match(EVIDENCE_PTR) ?? []) {
      if (!tracked.has(m)) {
        console.log(`[FAIL] ${p}: evidence pointer is not tracked -> ${m}`);
        bad++;
      }
    }
    if (text.includes(OLD_EVIDENCE_HOME)) {
      console.log(`[FAIL] ${p}: evidence still referenced inside an ignorable runtime dir`);
      bad++;
    }
  }
  if (bad === 0) {
    console.log(`[ok]   evidence pointers resolve; no live pointer in a runtime dir (${docs.length} tracked docs scanned)`);
  } else {
    fail = 1;
  }
}
```

并在末尾调用序列追加（`await validateRuntimeDirs();` 之后）：

```ts
await validateEvidence();
```

- [ ] **Step 2: 跑测试，确认绿**

Run: `npm run validate`
Expected: 出现 `[ok]   evidence pointers resolve; ...`，exit 0
（本 Task 的断言落地时 Task 1 已把状态修好，所以是绿；**能红必须自证**，见 Step 3。）

- [ ] **Step 3: 破坏性自测（证明断言会红），然后还原**

```bash
cp routes/news/ledger.jsonl /tmp/ledger.bak
sed -i 's#routes/news/evidence/#.harness-news-runtime/verifications/#' routes/news/ledger.jsonl
npm run validate
```
Expected: 至少 2 条 `[FAIL] routes/news/ledger.jsonl: ...`（一条「not tracked」、一条「inside an ignorable runtime dir」），exit 1

```bash
cp /tmp/ledger.bak routes/news/ledger.jsonl && rm /tmp/ledger.bak
npm run validate
```
Expected: 回到全绿，exit 0

> 注意：本步骤改的是 `routes/news/ledger.jsonl` **整文件**的前缀，Step 3 只允许临时存在，还原后 `git status --short` 必须不含 `ledger.jsonl`。

- [ ] **Step 4: Commit**

```bash
git add tests/validate-schemas.ts
git status --short | cat
git commit -m "test(harness): 断言证据活指针可解析且不落在 runtime 目录

宽版（所有被引用路径必须存在）实测 30+ 假失败——文档叙述提到已删除的 tmp
产物是正当写法，所以只锁证据类活指针。"
```

---

### Task 3: 口径落地（目录图、证据脚本分家、routing 表）

**Files:**
- Modify: `routes/news/ARCHITECTURE.md:180-199`
- Modify: `core/routing.md:3-7`

**Interfaces:**
- Consumes: Task 1 产出的 `routes/news/evidence/`
- Produces: 文档层面的「五类产物 / 证据脚本按被检对象分家」口径 —— Task 4、5 的措辞依据

- [ ] **Step 1: 改 runtime 目录图 —— 换掉 `:188` 那一行**

`routes/news/ARCHITECTURE.md:188` 当前是目录树的最后一个节点（**单行替换，树的其他行不动**）：

旧（verbatim，含行首 `└──`）：
`└── verifications/<date>-*.md   ← 端到端验证记录`

新（verbatim）：
`└── tmp/                        ← 一次性草稿 / 日志 / 探针输入（跑完即弃，永不提交）`

再在 `:191` 那行（`**禁止写 \`.ai-runtime-artifacts/\`** — 那是 code 路由的运行时域 …`）**之前**插入一句：

```markdown
证据**不在**这棵树里：契约证据（验证单）的家是 `routes/news/evidence/`，受版本管理，分类口径见本节末尾的五类表。

```

- [ ] **Step 2: 重写 `:193-199` 的「已知张力」段**

把这整段（从 `` `verifications/` 默认随目录一起被忽略，这是一处**已知张力** `` 起，到 ``而不是让文档指向忽略路径。`` 止，共 7 行）替换为：

```markdown
文件产物在本仓库分**五类**，每类一条保留规则，规则由 `tests/validate-schemas.ts` 断言锁死（散文会漂，断言不会）：

| 类别 | 保留规则 | news 域落点 |
|---|---|---|
| 工厂自身 | 必须版本管理 | `core/` `platforms/` `routes/*/MEMORY.md` `schemas/` |
| 自产物料 | 必须版本管理，**跟着消费者放** | `skills/douyin-pro/scripts/path_b_build.py` 等管线本体 |
| 证据 | 必须版本管理，且**不许住在可忽略目录** | `routes/news/evidence/*.md`（验证单） |
| 工作态 | 必须**不**版本管理 | `.harness-news-runtime/`（草稿、日志、成片、临时脚本） |
| 生成物 | 不手工编辑，可再生 | bootstrap 投影出的 `AGENTS.md` / `.qoder/rules/*.md` |

口径要点：
- **验证单一律进 `routes/news/evidence/`**，不再用 `git add -f` 从忽略目录里抢救 —— 那套机制已实测静默失败过一次（ledger 台账指向一份从未被追踪的验证单，clone 后是死指针）。
- **证据脚本跟着它检验的对象走**，不按「证据」这个名义集中：检验渲染管线本体的脚本留在 `skills/douyin-pro/scripts/`（它们就是被检的东西），检验路文档数字 / 路契约的脚本进 `routes/news/scripts/`。
- **零活指针的验证记录属工作态**，留在忽略目录，不迁不提交；日后有文档要引它，那时它才升格为证据并迁入 `evidence/`。
- 一次性跑产物（草稿、日志、临时脚本）永不进仓库；跑完即弃的迁移脚本也一并弃。
```

- [ ] **Step 3: 给 core/routing.md 路由表加 Evidence dir 列**

把 `core/routing.md:3-7` 的表整体替换为：

```markdown
| Route | When | MEMORY template | Runtime dir (never tracked) | Evidence dir (tracked) |
|-------|------|----------------|---------------------------|------------------------|
| `code` | Software engineering task | `routes/code/MEMORY.md` | `.ai-runtime-artifacts/` | `routes/code/evidence/` |
| `novel` | Novel / fiction writing task | `routes/novel/MEMORY.md` | `.harness-novel-runtime/` | `routes/novel/evidence/` |
| `news` | News/article task | `routes/news/MEMORY.md` | `.harness-news-runtime/` | `routes/news/evidence/` |
| small change | < 50 lines, no spec needed | none | none | none |
```

（列名里直接写进 never tracked / tracked，是为了让「证据不在 runtime 目录」这条规则在路由表上自我说明，不依赖读者去 news 域翻。）

- [ ] **Step 4: 跑测试确认没破断言**

Run: `npm test`
Expected: 全绿。⚠️ 注意 `validateEvidence()` 会扫描改后的 `ARCHITECTURE.md`：Step 1 新写的说明句里不得出现 `.harness-news-runtime/verifications/` 字样（本步骤文本只提 `routes/news/evidence/`，符合）。

- [ ] **Step 5: Commit**

```bash
git add routes/news/ARCHITECTURE.md core/routing.md
git commit -m "docs(harness): 文件产物五类口径落地（含证据脚本按被检对象分家）

证据脚本的家此前硬编码成 skills/douyin-pro/scripts/；实测那 12 个脚本就是渲染
管线本体，搬走是虚假的整洁，所以只改分界规则：验证单进路内 evidence/，脚本跟
着被检对象走。"
```

---

### Task 4: metrics —— 断言③ + 删除无口径数字

**Files:**
- Modify: `tests/validate-schemas.ts`（加 `validateDocCounts()`）
- Modify: `ARCHITECTURE.md`（根）：`:5` `:11` `:15` `:25` `:27`

**Interfaces:**
- Consumes: `SCHEMAS_DIR`、`isDir()`（文件里已有）、`readFile`、`readdir`、`join`、`resolve`
- Produces: `validateDocCounts()`

- [ ] **Step 1: 写断言**

在 `validateEvidence` 之后追加：

```ts
const sameSet = (a: string[], b: string[]): boolean =>
  a.length === b.length && a.every((x) => b.includes(x));

async function listDirs(path: string): Promise<string[]> {
  const out: string[] = [];
  for (const e of await readdir(path)) if (await isDir(join(path, e))) out.push(e);
  return out.sort();
}

// Parse one cell of the ARCHITECTURE.md "Current state" table, e.g.
// `| Routes | 3 (code, novel, news) — ... |` -> "3 (code, novel, news) — ...".
function docRowCell(doc: string, label: string): string {
  const line = doc.split(/\r?\n/).find((l) => l.startsWith(`| ${label} |`));
  if (!line) throw new Error(`ARCHITECTURE.md: missing table row "| ${label} |"`);
  return line.split("|")[2].trim();
}

const namesInParens = (s: string): string[] =>
  (s.match(/\(([^)]*)\)/)?.[1] ?? "")
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);

// The count and the names sit in the same cell, so they can contradict each
// other without contradicting anything else ("| Routes | 4 (code, novel, news) |").
const countProblem = (label: string, cell: string, names: string[]): string | null => {
  const claimed = Number(cell.match(/^\d+/)?.[0]);
  return claimed === names.length ? null : `"${label}" claims ${claimed} but lists ${names.length} names`;
};

async function validateDocCounts(): Promise<void> {
  const problems: string[] = [];
  const doc = await readFile(join(ROOT, "ARCHITECTURE.md"), "utf-8");
  const schema = JSON.parse(
    await readFile(join(SCHEMAS_DIR, "platform.schema.json"), "utf-8"),
  ) as { properties: { name: { enum: string[] } } };
  const enumPlatforms = schema.properties.name.enum;

  const platCell = docRowCell(doc, "Platform adapters");
  const docPlatforms = namesInParens(platCell);
  if (!sameSet(docPlatforms, enumPlatforms)) {
    problems.push(`doc platforms [${docPlatforms}] != platform.schema enum [${enumPlatforms}]`);
  }
  const boot = (await readFile(join(ROOT, "scripts/bootstrap.ts"), "utf-8"))
    .match(/const PLATFORMS: Platform\[\] = \[([^\]]*)\]/);
  if (!boot) throw new Error("bootstrap.ts: PLATFORMS declaration not found");
  const bootPlatforms = boot[1].split(",").map((s) => s.trim().replace(/"/g, "")).filter(Boolean);
  if (!sameSet(bootPlatforms, enumPlatforms)) {
    problems.push(`bootstrap PLATFORMS [${bootPlatforms}] != platform.schema enum [${enumPlatforms}]`);
  }
  const pc = countProblem("Platform adapters", platCell, docPlatforms);
  if (pc) problems.push(pc);

  const routeCell = docRowCell(doc, "Routes");
  const docRoutes = namesInParens(routeCell);
  const realRoutes = await listDirs(resolve(ROOT, "routes"));
  if (!sameSet(docRoutes, realRoutes)) {
    problems.push(`doc routes [${docRoutes}] != routes/ dirs [${realRoutes}]`);
  }
  const rc = countProblem("Routes", routeCell, docRoutes);
  if (rc) problems.push(rc);

  const coreDocs = (await readdir(resolve(ROOT, "core"))).filter((e) => e.endsWith(".md"));
  if (Number(docRowCell(doc, "Core governance docs")) !== coreDocs.length) {
    problems.push(`doc claims ${docRowCell(doc, "Core governance docs")} core docs, core/ has ${coreDocs.length}`);
  }

  if (problems.length === 0) {
    console.log(`[ok]   ARCHITECTURE.md counts match reality (platforms ${enumPlatforms.length}, routes ${realRoutes.length}, core docs ${coreDocs.length})`);
  } else {
    for (const p of problems) console.log(`[FAIL] ${p}`);
    fail = 1;
  }
}
```

并在末尾调用序列追加：

```ts
await validateDocCounts();
```

- [ ] **Step 2: 跑测试，确认绿（此时表里的数字仍是真值）**

Run: `npm run validate`
Expected: `[ok]   ARCHITECTURE.md counts match reality (platforms 5, routes 3, core docs 8)`

- [ ] **Step 3: 破坏性自测，确认能红，再还原**

```bash
cp ARCHITECTURE.md /tmp/arch.bak
sed -i 's#^| Routes | 3 (code, novel, news)#| Routes | 5 (code, novel, news, ghost)#' ARCHITECTURE.md
npm run validate
```
Expected: 两条 `[FAIL]`，各锁一个分支 ——
`doc routes [code, novel, news, ghost] != routes/ dirs [code,novel,news]`（集合分支）与
`"Routes" claims 5 but lists 4 names`（同格计数分支）；exit 1

```bash
cp /tmp/arch.bak ARCHITECTURE.md && rm /tmp/arch.bak && npm run validate
```
Expected: 全绿

- [ ] **Step 4: 删无口径的体量数字（`:5` `:11` `:15` `:27`）并修 `:25` 自相矛盾**

五处逐条替换（**只改这五行**；行号是编辑前的定位坐标，实际按 verbatim 文本匹配 —— 删 `:11` 那行会使其后行号整体前移）：

1. `:5` —— 把句中的 `but on a strict diet: 441 source files (vs 669 in harness-foundry), TypeScript only, no empty placeholders.` 改为：
   `but on a strict diet: TypeScript only, no empty placeholders, and no file class without a stated rule for where it lives.`
2. `:11` —— 整行 `| Source files (excl \`.git\` + \`node_modules\`) | 441 |` **删除**（无口径的计数不可证伪，留着是负债）。
3. `:15` —— 把 `| Skills | 97 (46 active in \`skills/\` + 51 archived in \`skills/archive/\`, all restorable) |` 改为：
   `| Skills | counted in \`skills/INDEX.md\` (single source; not duplicated here on purpose) |`
4. `:25` —— 把 `**Platforms**: ... — 4 thin adapters.` 里的 `4 thin adapters` 改为 `5 thin adapters`（这一行与 `:13` 的「5」自相矛盾，是人工同步漏改的现场证据；断言③只锁指标表，散文这行靠本步骤修）。
5. `:27` —— 把 `— 46 active; 51 unused live in \`skills/archive/\`` 改为 `— counts live in \`skills/INDEX.md\``。

- [ ] **Step 5: 跑全链路**

Run: `npm test`
Expected: 全绿（删掉的行不影响 `docRowCell`，因为断言③不引用 `Source files` / `Skills` 两行）。

- [ ] **Step 6: 确认文档不再有 441 残留**

Run: `git grep -n "441 source files\|Source files" -- ARCHITECTURE.md | cat`
Expected: 无输出

- [ ] **Step 7: Commit**

```bash
git add ARCHITECTURE.md tests/validate-schemas.ts
git commit -m "refactor(harness): 删无口径体量数字，可枚举计数改由断言核对

实测 441 与任何可定义口径都对不上（git ls-files 全量 794、排除 skills 96），
Skills 97 与 skills/INDEX.md 的 100 并存矛盾，:13 说 5 个适配器而 :25 说 4。
留得住的数字只有能机械核对的那几个，于是给它们加断言③。"
```

---

### Task 5: 清掉跑产物与失效 provenance 清单

**Files:**
- Delete: `routes/news/scripts/fix_decision_table.py`、`routes/news/scripts/fix_stale_doc_claims.py`、`routes/news/scripts/remap_pack_colors.py`
- Delete: `skills/.skills_store_lock.json`

**Interfaces:**
- Consumes: 无
- Produces: `routes/news/scripts/` 剩 7 个脚本，全部有仓库内引用

- [ ] **Step 1: 复核四个删除目标确实零引用 / 无消费者**

```bash
for s in fix_decision_table fix_stale_doc_claims remap_pack_colors skills_store_lock; do
  echo "$s -> [$(git grep -l "$s" -- . ':!docs/superpowers' | tr '\n' ' ')]"
done
```
Expected: 前三个 `[]` 空；`skills_store_lock` 只可能命中 spec（已被 `:!docs/superpowers` 排除）→ `[]`。
**任一命中本计划未列的文件，停下报告**，不要顺手删。

- [ ] **Step 2: 删**

```bash
git rm routes/news/scripts/fix_decision_table.py \
       routes/news/scripts/fix_stale_doc_claims.py \
       routes/news/scripts/remap_pack_colors.py \
       skills/.skills_store_lock.json
ls routes/news/scripts/*.py | wc -l
```
Expected: `7`

- [ ] **Step 3: 跑测试**

Run: `npm test`
Expected: 全绿（`validateSkills` 只看 `skills/*/SKILL.md`，删一个 lock 文件不影响）。

- [ ] **Step 4: Commit**

```bash
git commit -am "chore(harness): 删三个零引用一次性迁移脚本与失效的 skills provenance 清单

跑完即弃的迁移脚本属工作态，此前却躺在版本管理里；.skills_store_lock.json 的
installDir 全是指向不存在路径、version 为空串，而 douyin-pro 已裁定为第一方，
不再跟踪上游升级。"
```

---

### Task 6: 记账 + spec §9 验收逐条打勾

**Files:**
- Modify: `routes/news/MEMORY.md`（Key decisions 增一条）
- Modify: `docs/superpowers/plans/2026-10-09-file-artifact-class-contract.md`（勾选）

**Interfaces:**
- Consumes: Task 1-5 全部产出
- Produces: 通过 spec §9 的验收记录

- [ ] **Step 1: 在 news 路 MEMORY 记本次契约**

在 `routes/news/MEMORY.md` 的 Key decisions 小节末尾追加一条（日期用当天）：

```markdown
- 2026-10-09: 文件产物分五类，**契约证据的家是 `routes/news/evidence/`**，不再用 `git add -f` 从
  `.harness-news-runtime/` 抢救（该机制已静默失败过一次）。证据脚本按被检对象分家：管线本体留
  `skills/douyin-pro/scripts/`，路契约留 `routes/news/scripts/`。零活指针的验证记录属工作态，不提交。
  三条断言在 `tests/validate-schemas.ts`。设计稿：
  `docs/superpowers/specs/2026-10-09-file-artifact-class-contract-design.md`
```

- [ ] **Step 2: 逐条跑 spec §9 验收判据**

```bash
npm test
git ls-files | grep -E "^\.(harness-news|harness-novel|ai-runtime)" ; echo "runtime-tracked exit=$?"
git ls-files routes/news/evidence | wc -l
git grep -n "harness-news-runtime/verifications" -- . ':!docs/superpowers' | cat
git grep -c "harness-news-runtime/verifications" -- docs/superpowers | cat
npm run typecheck
```
Expected（按 spec §9 六条）：
1. `npm test` 绿，且输出里含三条 `[ok]`（runtime dir / evidence pointers / ARCHITECTURE counts）。
2. `grep -E` 无输出，`runtime-tracked exit=1`（grep 没命中才返回 1）。
3. evidence 计数 `9`。
4. 旧路径在**活文档里零命中**（第一条 grep 无输出：`routes/` `skills/` `core/` `platforms/` `ARCHITECTURE.md` 都不再指向它）；第二条 grep 只命中 `docs/superpowers/**` —— spec 的问题陈述与本 plan 的反向-sed 自测处方，属执行记录，必须保留旧字符串才成立。
   ⚠️ 这条判据对 spec §9 第 4 条「不命中任何可执行命令」做了**口径收窄**：判据被理解为「活文档里不许有指向退役路径的指针」，而不是「任何文件都不许出现该字符串」—— 后一种写法会让自测处方无法自我表达。裁定记在 ledger，最终汇报里回呈用户。
5. `typecheck` 无错误。
6. 三条断言各做过一次破坏性自测（Step 记录在 Task 2/4 与下方 Step 3）。

- [ ] **Step 3: 断言②的破坏性自测（Task 1 里它天然从红出发，这里再补一次独立验证）**

```bash
mkdir -p .harness-news-runtime/probe && echo probe > .harness-news-runtime/probe/x.md
git add -f .harness-news-runtime/probe/x.md
npm run validate; echo "exit=$?"
git rm --cached .harness-news-runtime/probe/x.md >/dev/null && rm -rf .harness-news-runtime/probe
npm run validate; echo "restored-exit=$?"
```
Expected: `exit=1` 并打印 `[FAIL] runtime content must not be tracked: .harness-news-runtime/probe/x.md`；还原后 `restored-exit=0`

- [ ] **Step 4: 确认工作树干净**

Run: `git status --short | cat`
Expected: 只有本 Task 的 `routes/news/MEMORY.md`（和勾选后的 plan 文件），无其他残留（尤其不得残留 Step 3 的 probe 文件或 `/tmp` 备份痕迹）。

- [ ] **Step 5: Commit**

```bash
git add routes/news/MEMORY.md docs/superpowers/plans/2026-10-09-file-artifact-class-contract.md
git commit -m "docs(news): 文件产物分级契约验收回写

spec §9 六条判据逐条通过；evidence 9 份、runtime 目录零追踪、三条断言各做过
破坏性自测。"
```

- [ ] **Step 6: 汇报（不 push）**

向用户汇报六个提交与验收结果，并明确：`git push` 等用户点头；本机 live 配置（`~/.codex/config.toml`、`~/.qoder-cn/settings.json`）仍带 `--ui=true`，属 spec §7 非目标，未动。
