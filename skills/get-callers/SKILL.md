---
name: get-callers
description: "获取调用指定符号的所有代码。触发：想知道谁在调用某个方法、分析依赖、评估影响。"
version: 1.0.0
when_to_use: 分析调用方时
status: peripheral
tags:
- intelligence
- code
- tactical
domain: code
category: code.intelligence
---

# /get-callers

使用 codebase-memory 查找调用指定符号的所有代码。

## 使用场景

| 场景 | 示例问题 |
|------|---------|
| 评估影响 | "修改这个方法会影响哪些地方？" |
| 理解依赖 | "哪些地方在调用 UserService？" |
| 回归测试 | "我改了这段代码需要测哪些？" |
| 重构分析 | "这个方法被用的多吗？" |

## 调用方式

```markdown
使用 codebase-memory 的 trace_path(direction="inbound") 工具：
- symbol: {符号名称}
- depth: 1 (调用深度，默认1层)
```

## 与 /analyze-impact 的区别

| Skill | 回答什么 |
|-------|---------|
| `/get-callers` | 直接调用方（一层） |
| `/get-callees` | 直接被调用方（一层） |
| `/analyze-impact` | 完整影响范围（多层） |
