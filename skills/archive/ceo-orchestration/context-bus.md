---
name: ceo-context-bus
description: "跨会话上下文总线 — CEO 在会话间传递关键上下文，保持跨域记忆"
---

# Context Bus（跨会话上下文总线）

## 激活条件

- 会话开始时：CEO 自动读取上一次的上下文
- 会话结束时：CEO 自动写入本次上下文
- S-3 新增子 Skill

## 工作流程

### 1. 会话开始 → 恢复上下文

CEO 读取 `performance/session-context.json`：

```json
{
  "last_session": "2026-06-25",
  "active_domain": "novel",
  "completed": ["第 3 章"],
  "pending": ["第 4 章", "审稿第 3 章"],
  "key_decisions": ["主角改名 → 李明"],
  "context_for_next": "下次继续写第 4 章"
}
```

### 2. CEO 传递给 Domain Leader

将上次会话的关键信息附在 `handoff/ceo-task.md` 中：

```markdown
domain: novel
task: 继续写第 4 章
constraints: 每章 3000-5000 字
priority: normal

## 上次会话上下文
- 已完成: 第 3 章
- 待办: 第 4 章、审稿第 3 章
- 关键决策: 主角改名 → 李明
- 继续: 下次继续写第 4 章
```

### 3. 会话结束 → 保存上下文

CEO 汇总本会话的关键信息，写入 `performance/session-context.json`：

```json
{
  "last_session": "2026-06-26",
  "active_domain": "novel",
  "completed": ["第 4 章"],
  "pending": ["第 5 章", "审稿第 4 章"],
  "key_decisions": ["修仙体系改为 9 级"],
  "context_for_next": "下次继续写第 5 章，注意修仙体系已改为 9 级",
  "cross_domain_notes": ["code 域暂无变更"]
}
```

### 4. 数据结构

```json
{
  "sessions": [
    {
      "date": "2026-06-26",
      "domain": "novel",
      "completed": [],
      "pending": [],
      "key_decisions": [],
      "context_for_next": ""
    }
  ],
  "_last_updated": "2026-06-26"
}
```

`sessions` 数组保留最近 10 条会话记录。

## 关联

- 数据存储：`performance/session-context.json`
- CEO 入口：`skills/ceo-orchestration/SKILL.md`
- 任务传递：`handoff/ceo-task.md`

## 超越点

OpenAI Agents SDK 有 Session 但只限单 Agent。ECC 和 gstack 无跨会话上下文传递。
Harness Foundry 是唯一一个在多域框架中实现跨会话上下文总线的项目。
