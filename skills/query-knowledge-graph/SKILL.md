---
name: query-knowledge-graph
description: "查询 codebase-memory-mcp 的知识图谱，获取结构化信息。触发：需要查询项目结构、模块关系、依赖关系。"
version: 2.0.0
when_to_use: 查询项目图谱时
status: peripheral
tags:
- intelligence
- code
- strategic
domain: code
category: code.intelligence
---

# /query-knowledge-graph

查询 codebase-memory-mcp 建立的知识图谱。

## 使用场景

| 场景 | 示例查询 |
|------|---------|
| 模块导航 | "用户模块在哪里？" |
| 依赖追踪 | "哪些模块依赖了订单服务？" |
| 关系查询 | "Controller 和 Service 的关系是什么？" |

## 调用方式

```markdown
使用 codebase-memory 的 search_graph 工具：
- query: {查询语句}
- node_types: ["class", "function", "method"] (可选)
```

## 预期输出

```json
{
  "results": [
    {
      "node": {
        "id": "user-module",
        "type": "module",
        "name": "用户模块"
      },
      "relationships": [
        "被订单模块依赖",
        "依赖基础模块"
      ]
    }
  ]
}
```

## 进阶查询

| 需求 | 工具 |
|------|------|
| 模块/类/函数定义 | `search_graph(query=...)` |
| 调用链/依赖链 | `trace_path(direction="inbound"/"outbound")` |
| 复杂多跳关系 | `query_graph(cypher=...)` |
| 跨文件调用关系 | `trace_path(mode="cross_service")` |
