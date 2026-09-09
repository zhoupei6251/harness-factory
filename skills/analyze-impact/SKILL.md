---
name: analyze-impact
description: "评估代码变更的影响范围。触发：重构前、修改核心方法、批量修改前。"
version: 1.0.0
when_to_use: 评估代码影响时
status: peripheral
tags:
- intelligence
- code
- tactical
domain: code
category: code.intelligence
---

# /analyze-impact

使用 codebase-memory 评估代码变更的完整影响范围。

## 使用场景

| 场景 | 使用价值 |
|------|---------|
| 重构前 | 知道改哪里会影响到哪些模块 |
| 修改核心方法 | 评估风险，制定测试计划 |
| 批量修改 | 避免遗漏关键的依赖方 |
| Code Review | 快速了解变更的影响范围 |

## 调用方式

```markdown
使用 codebase-memory 的 detect_changes 工具：
- file: {文件路径}
- symbol: {符号名称} (可选)
```

## 风险等级说明

| 等级 | 说明 |
|------|------|
| `low` | 无调用方或被广泛测试覆盖 |
| `medium` | 有少量调用方，需要回归测试 |
| `high` | 被多个模块调用，影响范围广 |
| `critical` | 核心基础设施，影响整个系统 |

## 与其他 Skill 的配合

```
1. /query-symbol     → 定位要修改的代码
2. /get-callers      → 快速查看直接调用方
3. /get-callees      → 快速查看被调用方
4. /analyze-impact   → 综合评估完整影响
```
