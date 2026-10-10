# CLAUDE.harness.md — harness-factory 可分发 harness 规则

> 本文件由 `harness-factory/scripts/install-into-project.ts` 在 other 模式下被目标项目 `@harness-factory/CLAUDE.harness.md` 引用。  
> 自包含：包含阶段门禁、Tier 1 分级流水线、证据段模板、加载规则。  
> 设计稿：[2026-10-10-tier1-pipeline-design.md](docs/superpowers/specs/2026-10-10-tier1-pipeline-design.md)

## §1 阶段门禁（强制基线）

| 阶段 | 必做 | 暂停时机 |
|---|---|---|
| 设计 / spec | Load `brainstorming` skill → 写 spec 产物 | 写完暂停，等用户「开始计划 / 开始实现」 |
| 计划 | Load `writing-plans` skill → 写 plan 产物 | 写完暂停，等用户「开始实现」 |
| 实现 | 已批准 plan 后才动业务代码；**Tier 1 走主 Agent 直做**（见 §2）；Tier 2+ 走 `claude-orchestration` + worktree 派发 | 末次实现完成 ≠ 批次完成 |
| 验证 / 尾盘 | Load `verification-before-completion` → 写 `verifications/*-verification-lite.md`（Tier 1）或 `*-collective-test.md`（Tier 2+） | 证据未落盘禁止声称「完成」 |
| Git | Load `git-xywh` skill；子 Agent 默认不 commit / push | 由 Leader 统一处理 |

**自主性约束**：
- 「自主性」仅适用于**实现阶段**，且须满足 plan/spec 已批准 + 用户原话授权
- 写完 spec / plan / decision 后**必须暂停**；「写方案」「写计划」不属于实现阶段
- Tier 1 走主 Agent 直做时仍须写**证据段**（见 §3）+ verification-lite

## §2 Tier 1 分级流水线（标准改动）

**触发条件**（任一不满足则走 Tier 2+）：
- 改动 ≤ 200 行
- 改动 ≤ 3 个文件
- 不碰公共 API、不改数据库 schema、不改构建脚本
- 不涉及多模块联动、不引入新依赖

**流程**（与 Tier 2+ 的区别）：

| 阶段 | Tier 2+ 流程 | Tier 1 流程 |
|---|---|---|
| 文档 | spec + plan + 验证分散 3 份 | **1 份合并文档**（spec + plan + 验证断言合一，见 §3 证据段模板） |
| 暂停 | spec 后 + plan 后**两次** | **合并文档后 1 次**：「确认开始实现？」 |
| 实现 | Leader 派发 WU 到子 Agent（worktree） | **主 Agent 直做**（不开 worktree，不派子 Agent） |
| 验证 | collective-test + code-review | 内联断言 + verification-lite |

**完成判据**：
1. 合并文档已写（含证据段）
2. 用户确认「开始实现」
3. 主 Agent 改完 + 跑通内联断言
4. 写 `verifications/*-verification-lite.md`，证据闭环
5. **可以 commit**（不自动 push，push 由用户决定）

**升档判据**（Tier 1 干到一半发现需要升档）：写到合并文档阶段如发现触发条件不再满足（> 200 行、跨模块、碰 schema），立刻停止并告知用户升 Tier 2。已写文档可作为 Tier 2 的 spec 输入。

## §3 证据段模板（合并文档必填）

合并文档的「证据」段**不能为空**。Agent 改代码前必须从知识图谱拿证据。

**模板**：

```markdown
## 证据（Evidence）

### 改动触及的代码（from search_graph）

| 符号 | qualified_name | 现有行数 | 角色 |
|---|---|---|---|
| <Name> | `com.example.X` | 123 | 直接改 |
| <Name2> | `com.example.Y` | 45 | 调用者 |

> 至少 1 行；行数 ≥ 50 的函数应同时列出其测试覆盖情况。

### 影响面（from trace_path）

- **inbound callers**（谁调我）：
  - `com.example.A.method1`（line 30，调用 `X.process()`）
  - `com.example.B.method2`（line 88，调用 `X.validate()`）
- **outbound callees**（我调谁）：
  - `com.example.Z.fetch()`（line 67）
- **跨服务 / 异步链路**（如有）：—

### 验证断言（改完逐条核）

- [ ] `<行号>` 处的旧实现替换为新实现，类型签名不变
- [ ] 新增分支有对应单元测试（或解释为何不需）
- [ ] 受影响的 callers 行为不变（或解释兼容方案）
- [ ] `mvn compile` / 等价构建命令成功（**仅列出命令，不自动跑**）
- [ ] 影响面内的关键路径走查通过

### 不可验证的盲点（如有）

- 列出本次改动未触及但理论上可能受影响的路径，**主动声明盲点比假装全绿更值得信任**。
```

**取证据的硬性要求**（R1 / R2 / R8 对应）：
- 改动前**必须**调 `search_graph` / `trace_path` 拿图谱证据；不许凭印象
- 工具未装/未接通 → 声明降级：`[codebase-memory-mcp 不可用，已降级] 原因：<...>；替代手段：<Read / Grep 手工取证>`
- **不可**在没有证据的情况下声称完成（违反 NEVER.md 禁止项）

## §4 加载规则（其他项目用本文件时按此加载）

| 路径 | 用途 |
|---|---|
| [`ENTRY.md`](../ENTRY.md) | harness 唯一入口（治理文档、阶段门禁总纲） |
| [`core/routing.md`](../core/routing.md) | 路由表（task → route → skill 加载） |
| [`core/intent-routing.md`](../core/intent-routing.md) | 意图路由（任务判定 + 加载规则） |
| [`core/NEVER.md`](../core/NEVER.md) | 禁止项（每条必读） |
| [`core/runbooks.md`](../core/runbooks.md) | 触发词 → 动作映射（Git、路由、工具） |
| [`core/principles.md`](../core/principles.md) | 设计原则（minimal change 等） |
| [`templates/README.md`](../templates/README.md) | 跨项目注入 harness 的方法（install-into-project.ts） |

**加载顺序**（Claude Code 会话开始时）：
1. `~/.claude/CLAUDE.md`（用户全局记忆）
2. `<cwd>/CLAUDE.md`（项目根，**含本文件的 @import**）
3. `~/.claude/rules/`（用户级 skill 自动发现）

**5 端对应入口**（多端协作时各自加载）：
- Claude Code: 项目根 `CLAUDE.md` 的 `@harness-factory/CLAUDE.harness.md`
- Codex / Qoder: 项目根 `AGENTS.md` 的条件读 `harness-factory/AGENTS.harness.md`（若存在）
- Trae / WorkBuddy: 同 Codex，由模型读 prompt 内指令
- Gemini: 项目根 `GEMINI.md` 的条件读 `harness-factory/GEMINI.harness.md`（若存在）

## §5 Tier 0（小改动）速通

≤ 50 行、单文件、不引入依赖、不改公共 API、不改 schema：直接处理，**无需合并文档**。首句声明 `「Harness：小改动，直接处理」` 即可，验证内联在回复里。

## §6 完成判据

| 任务 Tier | 完成判据 |
|---|---|
| **Tier 0**（小改动） | 改动符合判定 + 口头说明改动范围 |
| **Tier 1**（标准改动） | 合并文档 + 用户确认 + 主 Agent 改完 + 验证断言逐条核 + `verifications/*-verification-lite.md` 落盘 |
| **Tier 2+**（多 task / GROUP） | collective-test + code-review 落盘 |

**写完 ≠ 完成**。必须按上表落盘后再向用户声称完成。
