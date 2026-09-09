---
name: query-symbol
description: "快速定位代码符号（类/函数/变量）。触发：需要找某个符号、不知道在哪里、查询定义。"
version: 1.0.0
when_to_use: 定位代码符号时
status: peripheral
tags:
- intelligence
- code
- tactical
domain: code
category: code.intelligence
---

# /query-symbol

使用 codebase-memory 快速定位代码符号（类、函数、方法、变量等）。

## 使用场景

| 场景 | 示例 |
|------|------|
| 找类定义 | "UserService 在哪里？" |
| 找函数实现 | "login 方法在哪里？" |
| 找变量声明 | "MAX_RETRY 是什么？" |
| 找接口实现 | "实现了哪些接口？" |

## 调用方式

```markdown
使用 codebase-memory 的 search_graph 工具：
- query: {符号名称}
- node_types: ["class", "function", "method", "variable"] (可选)
```

## 支持的符号类型

| 类型 | 说明 |
|------|------|
| `class` | 类 |
| `interface` | 接口 |
| `function` | 函数 |
| `method` | 方法 |
| `property` | 属性 |
| `variable` | 变量 |
| `constant` | 常量 |
| `enum` | 枚举 |

## 搜索优化

- 支持模糊搜索
- 自动过滤测试文件（除非指定）
- 结果按相关性排序
