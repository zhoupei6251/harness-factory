# skills/archive phase-6 cull 设计（不再"留个口子")

> 日期：2026-10-19 ｜ 状态：方案已选定，待实施
> 上游：`scripts/skills-audit.ts`（现状可见但仅报告不决策）、`scripts/skills-archive-review.ts`（本次新增，量化"可删性"）
> 不变量：`skills/INDEX.md` 的"Total: 49 active + 51 archived = 100"行必须由真机机检守住（已由 `scripts/structure-audit.ts` 守护）

## 1. 背景

- ARCHITECTURE.md 自承 phase-5 砍掉 9 个空 capability 占位、694 md 文件、15+ MCP 占位 —— 但 `skills/archive/` 一直按"留个口子，万一要用呢"留着。
- 截至 2026-10-19 共 **51 个 archived skill**，49 个 active skill。新增的 `scripts/skills-archive-review.ts` 对所有 archive 条目按"被仓内非 archive 文件 word-boundary 引用次数"做量化扫描：

| 桶 | 数量 |
|---|---|
| 总 archived | 51 |
| 0 引用（候选删除） | 48 |
| 1-9 引用 | 3（web-tools-guide / archive-karpathy-guidelines / summarize） |
| 名称冲突（active 或 core 同名） | 1（archive/karpathy-guidelines ↔ core/karpathy-guidelines.md） |
| 缺 SKILL.md 或 _meta.json | 0 |

## 2. 目标

把"51 个 archive skill"这个数字降到诚实反映当前 use case 的值，**而不是降到 0**：

- archive 的合法用途 = "我承认它现在没人用，但保留一份以防恢复"。**真正不可删的是仓库内有引用、或仍在被 tools 链路间接依赖的那一两个**。
- phase-6 不"全删"，也不"不删"——按 reachability 把 51 个分成三档，每档独立处置。

## 3. 方案 A（已选）：三档分类处置

| 档位 | 标准 | 数量 | 处置 |
|---|---|---|---|
| 真死代码 | 0 引用、SKILL.md 与 _meta.json 都齐、且不在任何工具链路里 | 1（`archive/novel-debug` —— 唯一例外） | 删除 |
| 死代码（保留观察） | 0 引用、SKILL.md 与 _meta.json 都齐 | 47 | **保留**，本期不删 |
| 仍有引用 | refs ≥ 1 | 3 | 保留 |
| 名称冲突 | 同一名字同时存在于 archive 与 core/ 或 active/ | 1（archive/karpathy-guidelines） | 删 archive 侧 |

> 实施计划：本期只动两个文件——删除 `archive/karpathy-guidelines/` 与 `archive/novel-debug/`。其余 49 个 archive skill 一概不动。
> 为什么不全删 47 个 0-ref：reachability 在仓内可机检，但**仓外**（用户机器上装到 `~/.qoder/skills/` 等目录）是否有引用无从知道。`scripts/install-skills.ts:67` 会 junction 整个 `skills/` 目录——archive 里的 skill 是"过去或将来某一台机器还在用"的合理假设。在没有用户明确信号前一律保留。

### 3.1 删除项 #1：`archive/karpathy-guidelines/`

- 与 `core/karpathy-guidelines.md` **同名**且内容重复；core 侧是当前 ENTRY.md 表格里列出的官方 doc，archive 侧是 v0 时期放在 skills 里的版本。
- 仓内引用数：4（全部来自 core 引用 core 自身）。
- 删除后 reachability 不动，paths 不动。

### 3.2 删除项 #2：`archive/novel-debug/`

- 仓内 0 引用。
- `SKILL.md` 体积 0 KiB（空文件）—— 唯一一个 0 KiB 的 archive skill，连可恢复的内容都没有，留它没有任何价值。
- 删除后到达 `49 + 50 archived = 99 skills` 的真正计数。
- 注：**其余 22 个 `archive/novel-*` 都保留**（仍按"留个口子"原则）。它们是 v2.5 之前 novel 路由的引擎残留，novel 域当前确实无 engine code，但 R8 "如无必要勿增实体"同样适用于"删"——在用户没明确说"novel 路线彻底砍掉"之前不批量删。

### 3.3 不删除项的理由记录

为了让下次 phase-7 cull（如果有）能基于决策日志推进而不是重做：

| Skill | 不删理由 |
|---|---|
| `archive/novel-*`（除 novel-debug） | novel 路由的 v1 引擎残留；routes/novel/MEMORY.md 还在，路由占位还在，引擎只是没人调用 |
| `archive/fanqie-novel-auto-publish / fanqie / piqie-writing / qidian-writing / zhi-dou-writing / writing-novel` | 平台/网站特定的发布工具，code route 不引用是正常的；删了即丢失这些平台的可恢复性 |
| `archive/web-novel-publishing-readiness-and-quality-check-skill` | 同上 |
| `archive/inkos / junli-ai-novel` | 独立 novel CLI；同上 |
| `archive/agent-shield / security-auditor / auto-compact / document-review / prompt-engineering-expert / superdesign` | v0→v1 重构的"已被取代但仍有保留学术价值"的工具；任何一台机器的 `~/.qoder/skills/` junction 装上也许还在用 |
| `archive/ceo-orchestration / cursor-orchestration / code-insight-stack` | 编排器；与 active 的 `harness-orchestration` / `analyze-impact` 等是同族不同代——删 archive 意味着"彻底不再有 v0 编排的可恢复路径"，目前没人要求 |
| `archive/frontend-design / ui-ux-pro-max / web-design-guidelines / web-tools-guide / backend-doc-generator` | UI/文档类工具；active 的 `frontend-design / ui-ux-pro-max / web-design-guidelines / web-tools-guide / backend-doc-generator` 名字一致（注意 `web-tools-guide` 是 archive 引用 active skill `playwright` 的唯一连接点） |
| `archive/memory-manager` | 与 active `memory-bank` 同族不同代 |
| `archive/summarize` | 仓内 9 引用（含 `routes/news/scripts/batch_render.py`）—— **真活**，绝对不删 |
| `archive/web-tools-guide` | 1 引用（`skills/playwright/SKILL.md`）—— 也算"还有用" |

## 4. 不变量与验收

### 4.1 不变量

- 删除后 `scripts/skills-audit.ts` / `scripts/structure-audit.ts` / `scripts/skills-archive-review.ts` 都跑得通——它们读 `readdir` 不读 `git ls-files`，删了 archive 子目录后列表自动更新。
- `skills/INDEX.md` 的 "Total:" 行必须重生成：本仓 `INDEX.md` 由 `scripts/build-index.ts` 产出，所以删完跑 `npm run index` 即可。
- 新 `INDEX.md` 行：`49 active + 49 archived = 98 skills`。
- `npm test` 全过（包含 `structure:audit`，它会重新核对新数字）。

### 4.2 验收口径

- [ ] `archive/karpathy-guidelines/` 目录已删（保留目录下的两个文件消失，`git status` 干净）
- [ ] `archive/novel-debug/` 目录已删
- [ ] `npm run index` 已跑，新 `skills/INDEX.md` 行 = `49 + 49 = 98`
- [ ] `npm test` 全过（7 个 step + 4 个 test 文件）
- [ ] `npm run skills:archive-review` 输出里 "Total archived" 由 51 变为 49，"Cull candidates" 由 48 减到 46（少 2 个）
- [ ] `routes/code/MEMORY.md` 的 Key decisions 加一条本次决策记录

## 5. 暂不实施

- 不实现自动删除脚本。reachability 是仓内信号 + 仓外假设的合成，单凭脚本永远不够定。phase-6 完成后给用户人工 review 一次，再决定 phase-7 是否要做 "reachability + 上次使用 mtime 启发式"的自动 cull。
- 不改 `scripts/skills-audit.ts` / `scripts/skills-archive-review.ts` 的 output format——它们的报告已经够用；改 format 会引发"为啥改了"的追溯成本。
- 不改 `.gitignore`。archive 删除是单次动作，不需要 ignore 模式。