---
name: get-callees
description: "获取指定符号调用的所有代码。触发：想知道某个方法内部调用了什么、分析实现细节。"
version: 1.0.0
when_to_use: 分析被调用方时
status: peripheral
tags:
- intelligence
- code
- tactical
domain: code
category: code.intelligence
---

# /get-callees

使用 codebase-memory 查找指定符号调用的所有代码。

## 使用场景

| 场景 | 示例问题 |
|------|---------|
| 理解实现 | "这个方法里面调用了什么？" |
| 追踪逻辑 | "订单创建的完整流程是什么？" |
| 分析依赖 | "这个服务依赖了哪些组件？" |
| Bug 定位 | "哪个调用抛出了这个异常？" |

## 调用方式

```markdown
使用 codebase-memory 的 trace_path(direction="outbound") 工具：
- symbol: {符号名称}
- depth: 1 (调用深度，默认1层)
```

## 使用建议

- 配合 `/get-callers` 一起使用可获得完整调用图
- 使用 `/analyze-impact` 可一次性获取完整影响范围
