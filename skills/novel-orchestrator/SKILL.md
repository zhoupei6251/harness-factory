---
name: novel-orchestrator
description: 小说创作总控调度器，协调 writer→planner→reviewer→humanizer→editor→memory-keeper 全链路，管理阶段门禁和返修闭环
metadata:
  domain: novel
  priority: P0
  tags:
  - orchestration
  - novel
  - pipeline
  - multi-agent
version: 1.0.0
when_to_use: 调用 novel-orchestrator 时
status: peripheral
tags:
- novel
domain: novel
category: novel.orchestration
---

# Novel Orchestrator — 小说创作总控调度器

> Novel 域的编排核心。协调 8 个 Agent 角色完成从大纲到交付的全流程。
> **禁止** 用 `harness-orchestration` 处理小说 — 必须使用本 skill。

## 激活条件

- 用户进入 novel 域写作模式（`/novel` 命令）
- 用户要求批量创作多章（"写到第N章为止"）
- 需要协调 planner→writer→reviewer→humanizer 全链路
- 大纲确认后开始逐章产出

## 阶段链（6 阶段门禁）

```
0. 开书 → brainstorming（产出 spec）
   [门禁：用户确认设定/题材/风格]

1. 规划 → planner 产出大纲 + 人物设定 + 分卷规划
   [门禁：用户确认大纲]

2. 正文 → writer 逐章写作
   │    ├─ 读 MEMORY.md（人物状态/伏笔/上章摘要）
   │    ├─ 写本章正文（≥2000 字）
   │    └─ 更新 MEMORY.md
   [门禁：每章自检（字数 + AI套路检查）]

3. 审稿 → reviewer 7 维评分 + 逐条原文举证
   │    ├─ ≥70 分 → 进入 Guardian 核查
   │    └─ <70 分 → 返修（最多 2 次）→ 仍不通过则通知用户
   [门禁：审稿通过]

3.5 守护 → guardian 法医式事实核查 (★ v2.0 新增)
   │    ├─ 角色连续性（名字/外貌/性格/关系/位置）
   │    ├─ 时间线连续性（事件顺序/间隔/年龄）
   │    ├─ 世界观连续性（地理/设定/能力体系）
   │    ├─ 情节连续性（伏笔回收/因果/信息传递）
   │    ├─ 记忆健康度检查（逾期伏笔/沉默角色/遗忘设定）
   │    ├─ 通过 → 进入润色
   │    └─ 不通过 → 阻塞，必须修复连续性矛盾
   [门禁：Guardian 通过]

4. 润色 → humanizer 文风清洗
   │    ├─ 单章轻量 → humanizer-zh
   │    └─ 批量深度 → novel-ai-wash
   [门禁：润色完成 + 质量检查]

5. 统稿 → editor 跨章一致性检查 + 角色长期记忆更新
   │    ├─ 人物称呼 / 地名 / 专有名词统一
   │    ├─ 时间线校对
   │    ├─ 伏笔状态核实
   │    └─ 更新 characters.json（长期角色档案）
   [门禁：统稿通过]

6. 记忆同步 → memory-keeper 更新双轨记忆 + 章节自动摘要
```

## 角色调度

| 阶段 | Agent | Skill | 产物 |
|------|-------|-------|------|
| 开书/规划 | `novel-planner` | `brainstorming`, `junli-ai-novel` | 大纲.md, 人物设定/, 章节目录.md |
| 正文写作 | `novel-writer` | `junli-ai-novel`, `humanizer-zh` | 章节正文/第XXX章_标题.md |
| 审稿评分 | `novel-reviewer` | `novel-evaluator` | 审稿报告（评分+问题清单+结论） |
| 守护核查 | `guardian` | `novel-guardian` | 连续性报告 + 记忆健康度 |
| 润色清洗 | `humanizer` | `humanizer-zh` (轻量) / `novel-ai-wash` (深度) | 润色后章节 |
| 统稿检查 | `editor` | `memory-manager`, `junli-ai-novel` | 一致性报告 + characters.json |
| 记忆同步 | `memory-keeper` | `memory-manager` | 更新 MEMORY.md + GLOBAL-MEMORY.md + 章节摘要 |

## 并行策略

满足以下条件时并行派发 writer（≤5）：

- 连续写 ≥2 章
- 各章独立（无续写依赖关系）
- 用户明确说"写到第N章为止"

**有依赖关系的章节必须串行**（第 3 章依赖第 2 章结局 → 先写第 2 章，完成后写第 3 章）。

## 返修闭环

```
writer 写初稿
  → reviewer 审稿
    → ≥70 分 → 通过，进入润色
    → <70 分 → reviewer 出修改建议 → writer 返修（第 1 次）
      → reviewer 再审
        → ≥70 分 → 通过
        → <70 分 → reviewer 出修改建议 → writer 返修（第 2 次）
          → reviewer 三审
            → ≥70 分 → 通过
            → <70 分 → 输出最终审查报告 → 通知用户介入决策
```

## 门禁规则（硬性）

- ❌ 大纲未确认 → 不得写正文
- ❌ 审稿未通过 → 不得进入润色
- ❌ 润色未完成 → 不得交付
- ❌ Leader 主线程不得直接写正文（小改动 <200 字除外）
- ❌ 禁止使用 `harness-orchestration` 处理小说

## 产物

- `.novel-runtime-artifacts/plans/` — 大纲/规划产物
- `章节正文/` — 各章正文
- `.novel-runtime-artifacts/reviews/` — 审稿报告
- `.novel-runtime-artifacts/execution-logs/` — 执行日志
- `MEMORY.md` — 单书记忆（人物/伏笔/章节索引）

## 依赖

- `core/intent-routing.md` — 意图路由（Route: novel）
- `core/orchestration/dispatcher-workflow.md` — 通用调度器
- `core/NEVER.md` — 禁止项（novel 域 63 条陷阱）
- `agents/leader-novel.md` — 主编角色定义
- `agents/*.md` — 各 Worker 角色定义
- `traps-archive/novel/00-all.md` — 小说域陷阱清单
