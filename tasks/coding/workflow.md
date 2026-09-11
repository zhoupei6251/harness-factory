# tasks/coding/workflow.md — Coding 总流程

> 本文件是 code 路线的唯一 workflow。
> 平台/档位/技能怎么用 → 看 `core/` `skills/coding/` `agents/`。
> 任务阶段 → 看 `core/task-lifecycle.md`。

## 默认档

**M · 一页方案。**

理由：code 路线几乎不只改一个文件——单点改动也常常牵动 import、test、文档。

强制升 L：
- 跨模块改动
- 多 task 派发
- 对外发布
- 重构核心架构

强制保持 M（不降 S）：
- 即便只改一行，code 路线也有「改前读、改后验」的成本 → S 档不划算

## 路线管线（不随档升降）

```
EXPLORE   读现有代码（constitution R1）
   ↓
READ-AGAIN 读相关 skill（`skills/coding/<skill>/SKILL.md`）
   ↓
DESIGN    一段话方案（M）或 plan.md 落盘（L）
   ↓
IMPLEMENT 最小改动（constitution R2）
   ↓
VERIFY    跑 `state/profile.md` 声明的 verification_command
   ↓
REVIEW    spawn `agents/code-reviewer.md`（物理禁写）
   ↓
CLOSE     MEMORY.md 一段日志（M）/ closeout.md（L）
```

**必跑的步骤**：EXPLORE、VERIFY、REVIEW——不随档位升降。S 档也跑 EXPLORE+VERIFY。

**例外**：纯打字改动（错别字、formatting）不跑 REVIEW。

## 工具链约束

| 工具 | 用途 | 不许做 |
|---|---|---|
| Read / Grep / Glob | 读 | 写（写在哪个文件里） |
| Bash | 跑命令 | 改文件（除非是临时脚本） |
| Edit / Write | 改文件 | 改 `.harness/`（AI 自己管） |
| ApplyPatch（Codex） | 改文件 | 同 Edit/Write |

**核心禁令**：
- **不读就改 = 错误**（constitution R1）—— Edit/Write 前必须先读
- **不改 `.harness/`**——那是 AI 自己的状态空间
- **不删 `state/.bak/`**——除非用户明确要求

## 改前清单（必跑）

| 步骤 | 命令 | 不做的后果 |
|---|---|---|
| 读目标文件 | `Read <file>` | 改错位置 / 破坏现有逻辑 |
| 读相邻文件 | `Grep < <file> related>` | 漏掉 caller |
| 看最近修改 | `git log -5 -- <file>` | 跟现有方向反着改 |
| 看 diff 范围 | `git diff` | 漏掉冲突 |

## 改后清单（必跑）

| 步骤 | 命令 |
|---|---|
| 跑验证命令 | `<state/profile.md>: verification_command` |
| 看 diff | `git diff` |
| 看 lint | `npm run check`（如果项目有 lint） |
| 看测试 | 项目自带测试命令 |

## 多 task 派发（L 档批次）

走 `engine/runbooks/multi-task.md`。要点：

- WU（work unit）拆分：文件不重叠 / 依赖显显 / 都有 done criteria
- 并行派发到 `agents/implementer.md`（不同进程、不同上下文）
- 派发 prompt 必带：目标 / 文件清单 / skill 路径 / 必须回什么
- 摘要回来**自己读代码验证**——子 agent 的摘要不是证据（constitution R3）

## 跨平台

| 平台 | 入口文件 | 接什么 |
|---|---|---|
| Claude | `platform/claude/CLAUDE.md` | `.claude/rules/HARNESS.md` 一行 @import |
| Codex | `platform/codex/AGENTS.md` | 项目根 `AGENTS.md` |
| WorkBuddy | `platform/workbuddy/CODEBUDDY.md` | 项目根 `CODEBUDDY.md` |
| Trae | `platform/trae/project-rules/*.md` | `.trae/rules/project_rules.md` |

## 常见错误

| 错 | 对 |
|---|---|
| 顺手格式化 | 不格式化（PR 噪音） |
| 顺手加注释 | 不加注释（代码说话） |
| 改一个函数连带改其测试到「能跑」 | 改业务代码本身，测试独立 |
| 「应该可以」 | 跑测试 + 贴输出 |
| 先 Edit 后 Read | 改前必读 |
| 跳过 REVIEW | 物理禁写 agent 5 分钟的事 |