---
name: novel-protocol
description: 长篇网文写作协议——渐进式披露入口 + 因果链一致性强制。解决长篇小说两大痛点：(1) 全量加载 416KB novel 规则导致 token 浪费与注意力稀释；(2) 跨章世界观漂移、能力凭空出现、因果断裂。触发：写小说、写网文、写章节、续写、长篇小说创作。
domain: novel
category: novel.baseline
priority: P0
version: 1.0.0
when_to_use: 任何 novel 域写作指令的入口——先路由，再按需装配协议
status: stable
tags:
  - novel
  - protocol
  - progressive-disclosure
  - causality
---

# Novel Protocol — 渐进式披露 + 因果链一致性

## 核心原则

**入口轻、协议重、事实外置**：

- **入口轻**：本文件是唯一入口，只做指令路由，不加载全量规则（novel 域全部 skill 合计 416KB——全量加载既浪费 token 又稀释注意力）
- **协议重**：具体写作规则在对应 skill 中，按指令只装配需要的
- **事实外置**：世界观事实来自项目知识库文件，不内联在 skill 中

## 指令路由表（novel 域唯一权威路由）

> 所有 novel 指令先在本表路由，再按需装配协议。本表是唯一权威源——
> `core/intent-routing.md`、`commands/novel.md`、`rules/novel/README.md` 均引用本表，不另设路由。

| 用户意图 | 装配的协议 | 禁止加载 |
|------|-----------|---------|
| 写章节/续写 | `writing-novel` + `novel-guidelines` | 审稿/润色类 |
| 快速写单章 | `novel-quick-write` | 批量类 |
| 批量写到第 N 章 | `novel-batch-write` | 单章工具类 |
| 新书创建 | `novel-init` | 正文类 |
| 会话恢复 | `novel-recovery` | 正文类 |
| 设计大纲/世界观/设定 | `brainstorming` + `writing-novel` + `novel-36-beats` | 正文类 |
| 查看进度/统计 | `novel-dashboard` + `novel-metrics` | 写作类 |
| 上下文一致性检查 | `novel-contexts` | 写作类 |
| 检查点管理 | `novel-checkpoint` | 写作类 |
| 复杂任务/完整编排 | `novel-orchestrator` | 单章工具类 |
| 审稿评分 | `novel-evaluator` + `novel-guardian` | 写作类 |
| 改良已有作品 | `novel-improver` | 写作类 |
| 润色去 AI 味 | `humanizer-zh` | 正文类 |
| 平台专项（番茄）| `piqie-writing` | 起点类 |
| 平台专项（起点）| `qidian-writing` | 番茄类 |
| 智斗/权谋类型 | `zhi-dou-writing` | 非类型类 |
| 发布前质检 | `web-novel-publishing-readiness-and-quality-check-skill` | 写作类 |
| 番茄发布 | `fanqie-novel-auto-publish` | 写作类 |
| 返修/排查情节 | `novel-debug` + `novel-safe-revision` | 正文类 |
| 章节自查 | `novel-simplify` | 审稿类 |
| 跨章记忆/统稿 | `memory-manager` | 单章类 |
| 写前查设定 | 读 MEMORY.md + `novel-contexts` | — |

## 执行闭环（每条指令固定五步）

1. **指令识别**：识别指令类型（写/审/改/润）与范围（卷/章）
2. **协议装配**：按路由表加载对应 skill，只加载需要的
3. **知识库绑定**：定位并读取项目知识库（见下）
4. **前置校验**：因果链检查（见下）+ 连续性检查
5. **交付收束**：输出正文 + 一句话状态报告；写后自检走 `traps-archive/novel/novel-checklist.md`（5 维 + AI 痕迹红线）

## 因果链一致性（法典级约束）

### 因果律闭环

任何**重大事件**（核心角色死亡、世界规则改变、Tier-1/2 伏笔回收）必须在前文找到**逻辑先导事件**作为其因：

```
检查流程（有 kb/graph.yaml 时，用脚本自动校验）：
1. 列本章重大事件，更新 kb/graph.yaml（节点 + 边 + chapter_events）
2. 跑：python scripts/novel/novel_graph.py kb/graph.yaml validate
   → 熔断：FATAL_ERROR: Causality_Chain_Broken（列出缺失先导的事件/物品）
   → 补写先导或修正图，重跑直到通过
3. 用 path 命令回溯关键道具因果链：
   python scripts/novel/novel_graph.py kb/graph.yaml path <物品id>
无 kb/graph.yaml 时降级为人工追溯：每个事件向前查前文逻辑先导
```

**禁止**：
- 关键能力/物品凭空出现（必须完整叙述获取过程或有可靠线索支撑）
- 因果链断裂的峰值章节（必须逆向追溯扫描后确认闭环才可交付）

### 保真度层级

```
战略宏图 → 全书蓝图 → 章节目录 → 正文
```

下级是上级的**高保真显化**，而非创造性修正：
- 正文必须忠于目录的核心情节与悬念
- 目录必须忠于蓝图的宏观节奏与时代边界
- 蓝图必须忠于战略宏图的最终事件

### 禁止捏造

项目知识库是**唯一真实世界**。缺失知识库文件时：
- 报告绑定失败（列出缺失文件）
- **禁止捏造设定**——等用户补充或明确授权

## 项目知识库（6 件，用户自行填充）

| 文件 | 内容 | 缺失降级 |
|------|------|---------|
| `kb/world-rules.md` | 世界观规则（力量体系/地理/时代）| 禁止正文，可大纲 |
| `kb/characters.md` | 角色档案（目标/信念/秘密/关系）| 禁止正文，可大纲 |
| `kb/events.md` | 档案事件（已发生的重大事件）| 因果链检查降级为提示 |
| `kb/style-sample.md` | 文风样本（写作风格基准）| 禁止正文，可大纲 |
| `kb/world-stone.md` | 世界基石（动态核心，系统自动维护）| 禁止正文 |
| `kb/graph.yaml` | 剧情知识图谱（角色/地点/物品/事件节点 + 关系边）| 因果链检查降级为人工追溯 |

## 与现有 skill 的关系

- 本 skill 是 **novel 域的轻量入口**，不替代任何现有 skill
- `writing-novel` 是基础方法论（内容层），本 skill 是协议层（路由 + 一致性）
- `novel-orchestrator` 处理复杂任务的流水线编排（批量多章），本 skill 负责入口路由——复杂任务由本 skill 装配 `novel-orchestrator`
- `novel-guardian` 做审稿时的连续性核查，本 skill 在**写作前**做因果链预检——互补不冲突
