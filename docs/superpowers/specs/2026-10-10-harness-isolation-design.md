# Harness 隔离 + 模板化设计稿

> 日期：2026-10-10 ｜ 状态：设计（待写计划 → 待实施）
> 触发：用户在 brainstorming 会话中提出「harness-factory 不提交、独立仓库、本地开发用」+「方便不同项目引入」两个约束
> 关联：[2026-10-09-required-tooling-design.md](2026-10-09-required-tooling-design.md)（双工具强制化的基线）、[2026-10-09-file-artifact-class-contract-design.md](2026-10-09-file-artifact-class-contract-design.md)（文件产物分级契约）

## 1. 背景与诉求

父仓库 `aigc_platfrom_back` 是 Java 业务仓库，与同事共用。父仓库里被 git 追踪的 harness 痕迹（CLAUDE.md/AGENTS.md/GEMINI.md 的 harness 覆盖层、`.claude/HARNESS-RULES.md`、`.mcp.json`、退役的 `harness-kit/` 74 个文件）每次 harness 演进都会被改，污染共享仓库的 git 历史、形成与同事的合并摩擦。同事也用 AI 工具与 harness（具体用哪套未确认），因此不能简单删除这些共享文件。

诉求归纳为两条：

1. **隔离**：harness 演进**永不**触碰父仓库的 git 历史（连一次性集体瘦身提交都不要——本地化即可）。
2. **模板化**：harness-factory 变成可分发的工厂。其他项目克隆 harness-factory 即可引入同一套 harness。

## 2. 目标与验收口径

- **诉求 1（隔离）**：
  1. 父仓库的 `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` / `.claude/HARNESS-RULES.md` / `harness-kit/` 在用户的本地工作树按需修改，但**不进任何共享 commit**；
  2. 父仓库的 git status 在 harness 演进后**无相关 dirty 项**；
  3. 同事 pull 父仓库后，看到的仍是原版（无 harness-factory 目录、无任何 harness 改动）。
- **诉求 2（模板化）**：
  4. `harness-factory/templates/` 含目标项目初始化所需的所有模板（CLAUDE.md / AGENTS.md / GEMINI.md / 项目鸟瞰占位 / 引入说明）；
  5. `harness-factory/scripts/install-into-project.ts --target <path>` 能在任意目标项目根生成上述文件 + 本地化配置；
  6. 对自己父仓库（`--target .`）和陌生项目（`--target /path/to/other`）的安装行为等价。
- **不变量**：
  - 父仓库的 `harness-factory/` 嵌套独立 git 仓库身份不变（其本身在父 .gitignore:86 已被忽略）；
  - harness-factory 自己的五端投影机制（`scripts/bootstrap.ts`）不变；
  - codebase-memory-mcp + ponytail 双工具强制条款（2026-10-09 决定）不变；
  - 同事视角：harness-kit 永远不被他们看到，CLAUDE.md/AGENTS.md 等仍是原版。

## 3. 范围边界

| 范围 | 处置 |
|---|---|
| harness-factory 内的 templates/ + install-into-project.ts + tests/ | **本批次**新增 |
| harness-factory 自身五端投影（bootstrap.ts） | 不动 |
| 父仓库的本地化操作 | **本批次**一次性完成，零共享 commit |
| 8 个断链引用修复 | 不在本批次（harness-factory 内部独立 issue） |
| Tier 1 分级流水线 + 证据段模板 | 不在本批次（独立 issue） |
| 多端投影到用户级 `~/.claude/` | 不在本批次（未来增强） |
| 同事视角的任何变更 | 无（设计即满足） |

## 4. 架构

三层结构，分界线是「文件存在性 + git 归属」。

```
┌─ aigc_platfrom_back/（共享仓库，本地化后）───────────────┐
│                                                           │
│  共享薄壳（git skip-worktree，零 commit）                  │
│  ├─ CLAUDE.md          项目鸟瞰 + @harness-factory/...    │
│  ├─ AGENTS.md          项目鸟瞰 + 条件读 harness-factory  │
│  ├─ GEMINI.md          同上                              │
│  ├─ .mcp.json          保留不动（低频变更）              │
│  └─ harness-kit/       git rm --cached + info/exclude    │
│                                                           │
│  未追踪：                                                 │
│  └─ harness-factory/   已在父 .gitignore:86，自动隔离     │
│                                                           │
└───────────────────────────────────────────────────────────┘

┌─ harness-factory/（嵌套独立仓库，私有）──────────────────┐
│                                                           │
│  templates/                                               │
│  ├─ target-CLAUDE.md                                    │
│  ├─ target-AGENTS.md                                    │
│  ├─ target-GEMINI.md                                    │
│  ├─ project-birds-eye.template.md                       │
│  └─ README.md                                           │
│                                                           │
│  scripts/                                                 │
│  ├─ bootstrap.ts（已存在：投影 ENTRY 到本仓库五端）       │
│  └─ install-into-project.ts（新增：注入目标项目）        │
│                                                           │
│  tests/                                                   │
│  └─ install-template.test.ts（新增）                     │
│                                                           │
│  docs/superpowers/specs/2026-10-10-harness-isolation-design.md ← 本文件
│  docs/superpowers/plans/2026-10-10-harness-isolation.md（实施计划）│
│                                                           │
└───────────────────────────────────────────────────────────┘

┌─ ~/.claude/（用户级全局，私有）──────────────────────────┐
│  CLAUDE.md（用户全局记忆）                                 │
│  rules/（用户级 skill 自动发现）                           │
└───────────────────────────────────────────────────────────┘
```

## 5. 组件设计

### 5.1 组件 ①：`harness-factory/templates/` 目录

| 模板 | 占位符 | 说明 |
|---|---|---|
| `target-CLAUDE.md` | `${PROJECT_BIRDS_EYE}` | Claude Code 在目标项目根加载的 CLAUDE.md 骨架 |
| `target-AGENTS.md` | `${PROJECT_BIRDS_EYE}` | Codex/Qoder 加载 |
| `target-GEMINI.md` | `${PROJECT_BIRDS_EYE}` | Gemini 加载 |
| `project-birds-eye.template.md` | — | 项目鸟瞰占位文本（用户在 install 时填或保留 stub） |
| `README.md` | — | 「如何把 harness-factory 引入新项目」5 步说明 |

三个目标模板的结构（统一）：

1. 顶部生成标记：`<!-- HARNESS-FACTORY GENERATED — DO NOT COMMIT -->`
2. 1 行「本机存在 `harness-factory/` 才加载 harness 规则；否则你看到的是干净的 AI」说明
3. 替换 `${PROJECT_BIRDS_EYE}` 占位
4. 1 行 harness @import 引用

### 5.2 组件 ②：`harness-factory/scripts/install-into-project.ts`

CLI 签名：

```bash
npx tsx scripts/install-into-project.ts --target <path> [--dry-run] [--force]
```

执行步骤（顺序固定，幂等）：

1. 校验 `--target` 路径存在且可写
2. 检测目标根是否已有 `CLAUDE.md` / `AGENTS.md` / `GEMINI.md`：
   - 无 → 直接从 templates/ 写入
   - 有 → 备份为 `<name>.bak-YYYYMMDD-HHMMSS.md` 后再写（除非 `--force`，则提示用户二次确认）
3. 替换 `${PROJECT_BIRDS_EYE}` 占位：若用户提供 `--birds-eye-file <path>` 则读该文件，否则用 `project-birds-eye.template.md` 的 stub
4. 检测目标是否为 git 仓库（`git rev-parse --git-dir`）：
   - 是 → 把 `harness-factory` 加进 `.git/info/exclude`；若已有 `CLAUDE.md/AGENTS.md/GEMINI.md`，运行 `git update-index --skip-worktree <each>`（仅当文件已追踪）
   - 否 → 跳过本地化步骤
5. 输出：本机就绪；模板备份路径列表；skip-worktree / info/exclude 操作摘要

退出码：`0` 成功 / `1` 参数错误 / `2` 写入失败。

### 5.3 组件 ③：`harness-factory/tests/install-template.test.ts`

三个用例，沿用 `tests/validate-schemas.ts` 的 `[ok]/[FAIL]` 风格：

| 用例 | 断言 |
|---|---|
| 干净目标 | 注入后三个文件存在，harness @import 行格式正确，`${PROJECT_BIRDS_EYE}` 已被替换 |
| 重复注入 | 第二次注入时检测到现有文件，备份创建，原内容保留在 `.bak-*` |
| 同事场景模拟 | 注入后**删除** `harness-factory/` 目录，模拟「目标项目只有薄壳没私有层」状态，断言三个模板文件的 @import 行无语法错误（运行时无引用是 Claude Code 原生行为，不在此断言覆盖） |

## 6. 迁移映射（父仓库零 commit 的本地化清单）

| 操作 | 目的 | 影响 |
|---|---|---|
| `git update-index --skip-worktree CLAUDE.md AGENTS.md GEMINI.md` | 用户本地修改不被 git status 看见 | 同事工作树不变 |
| `git update-index --skip-worktree .claude/HARNESS-RULES.md` | 同上 | 同上 |
| `git rm --cached -r harness-kit/` + `.git/info/exclude` 加 `harness-kit/` | 取消追踪（保留工作树） | 同事工作树不变 |
| `.git/info/exclude` 加 `harness-factory/` | 父 git 不再考虑这个目录 | 已有 `.gitignore:86` 兜底，本步骤是冗余加固 |
| 写覆盖后的 CLAUDE.md/AGENTS.md/GEMINI.md 内容到工作树 | 本地化生效 | 父仓库的远端无变化 |

验证：操作完成后跑 `git status` 应无 harness 相关 dirty 项；`cat CLAUDE.md` 看到的是新内容；同事 `git pull` 后仍是原版。

## 7. 数据流

```
用户打开 aigc_platfrom_back/ 下的 Claude Code 会话
   │
   ├─ Claude Code 加载顺序（按 Claude Code 原生规则）：
   │   1. ~/.claude/CLAUDE.md（用户全局）
   │   2. aigc_platfrom_back/CLAUDE.md（项目根，skip-worktree）
   │   │     → 读到 @harness-factory/CLAUDE.harness.md
   │   │     → harness-factory/ 存在？读完整规则 / 缺失则静默跳过
   │   3. ~/.claude/rules/（用户级 skill 自动发现）
   │
   └─ Agent 按 routing.md 路由任务，进入 Tier 0/1/2

Codex/Qoder 会话：
   ├─ 读 aigc_platfrom_back/AGENTS.md
   │     → 看到指令「若 harness-factory/AGENTS.harness.md 存在则读取」
   │     → 模型执行该条件读取
   └─ 同上流程

Gemini 会话：
   ├─ 读 aigc_platfrom_back/GEMINI.md
   │     → 同条件读取 harness-factory/GEMINI.harness.md
   └─ 同上流程
```

注意：`CLAUDE.harness.md` / `AGENTS.harness.md` / `GEMINI.harness.md` **目前不在设计中——本批次不创建**。原因：用户当前只需要 harness-factory 内部规则（含 ENTRY.md、core/、routes/）通过现有机制被加载。三个 `*.harness.md` 是「如果要替父仓库 CLAUDE.md 等的覆盖层」的载体，本次**仅建立模板机制**，内容留待后续批次按需填充（也可直接引用 `harness-factory/ENTRY.md`）。

## 8. 错误处理

| 失败 | 行为 |
|---|---|
| harness-factory/ 缺失 | `@import` 静默跳过（Claude Code 原生）；模型看到项目鸟瞰，按 vanilla AI 行为 |
| `install-into-project.ts` 目标路径不存在 | 退出码 1，提示 `--target` 路径无效 |
| 目标文件已存在 | 自动备份到 `.bak-YYYYMMDD-HHMMSS`，再写入新内容（除非 `--force`） |
| 目标非 git 仓库 | 跳过 skip-worktree 和 info/exclude 步骤；只写文件 |
| 父仓库 .git/info/exclude 写入失败 | 警告并继续；用户可手动追加 |
| 模板渲染失败（占位符未替换） | 退出码 2，输出未替换的占位符列表 |

## 9. 验证

- **自动化测试**：`tests/install-template.test.ts` 三个用例（§5.3）
- **冒烟脚本**（放在 `scripts/smoke-isolation.sh`）：在临时目录模拟父仓库 → 跑 install-into-project.ts → 删 harness-factory/ → grep 确认模板无错误引用
- **人工冒烟**：在 aigc_platfrom_back 跑 `install-into-project.ts --target . --dry-run` 预览，再真跑；`git status` 应无 dirty
- **同事视角验证**：在另一台机器或同事的工作区 `git pull` 父仓库，应无 harness-factory 目录、无 harness-kit 修改

## 10. 变更文件清单

### harness-factory/ 新增（私有仓库，自己的 git）

| 路径 | 性质 |
|---|---|
| `templates/target-CLAUDE.md` | 目标项目 CLAUDE.md 模板 |
| `templates/target-AGENTS.md` | 目标项目 AGENTS.md 模板 |
| `templates/target-GEMINI.md` | 目标项目 GEMINI.md 模板 |
| `templates/project-birds-eye.template.md` | 项目鸟瞰占位文本 |
| `templates/README.md` | 引入说明 |
| `scripts/install-into-project.ts` | 注入脚本 |
| `tests/install-template.test.ts` | 三个测试用例 |
| `scripts/smoke-isolation.sh` | 冒烟脚本（可选） |
| `docs/superpowers/specs/2026-10-10-harness-isolation-design.md` | **本文件** |
| `docs/superpowers/plans/2026-10-10-harness-isolation.md` | 实施计划（独立文件） |

### aigc_platfrom_back/ 本地变更（**零 commit**）

| 操作 | 文件 |
|---|---|
| 内容覆盖（工作树） | CLAUDE.md / AGENTS.md / GEMINI.md / .claude/HARNESS-RULES.md |
| skip-worktree | 上述四个文件 |
| `git rm --cached` | harness-kit/（整个目录） |
| `.git/info/exclude` 追加 | harness-kit/ + harness-factory/（加固） |
| 工作树保留 | harness-kit/（不删，下次想用还在） |

## 11. 落地步骤（顺序固定）

1. harness-factory/：创建 `templates/` 5 个文件
2. harness-factory/：写 `scripts/install-into-project.ts`
3. harness-factory/：写 `tests/install-template.test.ts`，跑通三个用例
4. harness-factory/：写 `docs/superpowers/specs/2026-10-10-harness-isolation-design.md`（本文件）+ `docs/superpowers/plans/2026-10-10-harness-isolation.md`
5. aigc_platfrom_back/：**本地操作**：
   - 跑 `npx tsx harness-factory/scripts/install-into-project.ts --target . --dry-run` 预览
   - 真跑（不带 dry-run）
   - 手动跑 skip-worktree 与 git rm --cached + info/exclude（步骤 5 的脚本可附 `print-post-install.sh` 给出确切命令）
6. harness-factory/：git add + commit（main，按 memory「直接在 main 上开发」）
7. 父仓库：仅本地状态，**不 add / 不 commit / 不 push**

## 12. 非目标（明确不做）

- 8 个断链引用修复（在 harness-factory 内部单独 issue）
- Tier 1 分级流水线（独立 issue）
- 证据段模板（独立 issue）
- 多端投影目标从仓库级改为 `~/.claude/`（未来增强，本批次不动 bootstrap.ts）
- `CLAUDE.harness.md` / `AGENTS.harness.md` / `GEMINI.harness.md` 实际内容创建（本批次只建机制，文件可后续按需填）
- 父仓库 CLAUDE.md 等远端的清理（设计上是「永远冻结」，无清理动作）

## 13. 风险与回滚

- **风险 1**：skip-worktree 在某些 git 操作下会失效（如 `git read-tree` 重建 index）。缓解：脚本在 .bak 保留原内容，失败可手动恢复。
- **风险 2**：同事若未来升级 .gitignore，`.gitignore:86` 的 `harness-factory/` 被删，本地化依赖 .git/info/exclude 兜底。缓解：.git/info/exclude 是双保险。
- **风险 3**：harness-factory/ 路径在父仓库里硬编码为相对路径 `harness-factory/...`。如果未来 harness-factory 改名/移动，所有 @import 失效。缓解：本次先在 install-into-project.ts 阶段检查 `harness-factory/` 是否存在并在 README 强调「不要改名」。
- **回滚**：父仓库所有操作都未 commit，删除本地工作树文件 + `git update-index --no-skip-worktree <files>` + `git checkout -- .` 即可恢复。
