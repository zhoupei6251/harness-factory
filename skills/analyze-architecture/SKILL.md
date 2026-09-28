---
name: analyze-architecture
description: "深入分析项目架构，回答架构相关问题。触发：询问设计原因、技术选型、模块职责、架构决策。"
version: 2.0.0
when_to_use: 需要深入分析架构时
status: peripheral
tags:
- intelligence
- code
- strategic
domain: code
category: code.intelligence
---

# /analyze-architecture

使用 codebase-memory-mcp 的 `get_architecture` 进行架构问答，深入分析设计决策。

## 使用场景

| 场景 | 示例问题 | 分析方式 |
|------|---------|---------|
| 设计评审 | "为什么要用微服务架构？" | 架构模式分析 |
| 技术选型 | "为什么选择 Spring Boot？" | 技术栈分析 |
| 模块分析 | "订单模块的职责是什么？" | 模块职责分析 |
| 依赖分析 | "缓存层是如何设计的？" | 依赖关系分析 |
| 模式识别 | "用了哪些设计模式？" | 模式识别 |
| 流程追踪 | "下单流程是怎样的？" | 数据流分析 |

## MCP 调用协议

### Request

```json
{
  "tool": "get_architecture",
  "params": {
    "project": "<project>",
    "aspects": ["overview", "structure", "dependencies", "clusters"]
  }
}
```

### Response

```json
{
  "overview": {
    "name": "项目名称",
    "description": "一句话描述",
    "language": "主要语言",
    "packages": ["核心包列表"]
  },
  "structure": {
    "layers": ["表现层", "业务层", "持久层"],
    "modules": [{"name": "user", "path": "src/user", "dependencies": ["common"]}]
  },
  "clusters": [
    {"label": "认证模块", "member_count": 12, "top_nodes": ["AuthService", "..."]}
  ]
}
```

## 问题类型与回答模板

### 1. 设计原因类

```
问: 为什么要 [设计点]？

## 回答

[直接回答，1-2 句话]

## 理由

1. [原因 1]
   - 证据: [相关代码/配置]
   - 位置: [文件:行号]

## 相关文件

• [文件1]
• [文件2]
```

### 2. 技术选型类

```
问: 为什么选择 [技术A] 而不是 [技术B]？

## 技术 [技术A] 的优势

• [优势 1]
• [优势 2]

## 当前项目的选择依据

• [依据 1]: 在 [文件] 中发现 [证据]

## 与 [技术B] 的对比

| 维度 | [技术A] | [技术B] |
|------|---------|---------|
| [维度1] | [优势] | [劣势] |
```

### 3. 模块职责类

```
问: [模块名] 的职责是什么？

## 模块职责

[核心职责描述]

## 核心功能

| 功能 | 方法 | 说明 |
|------|------|------|
| [功能1] | [方法名] | [说明] |

## 依赖关系

[模块名]
├─ 依赖 ─→ [模块A]: [依赖原因]
└─ 被依赖 ←─ [模块C]: [使用方式]
```

### 4. 流程追踪类

```
问: [业务流程] 是怎样的？

## 流程: [流程名称]

用户请求 → [Controller] → [Service] → [Repository] → 数据库

## 详细步骤

1. [步骤 1]
   - 位置: [文件:行号]
```

## 深入分析工作流

```
1. get_architecture(aspects=["overview", "clusters"]) → 模块边界与真实聚类
2. search_graph(query=...) → 定位具体类/函数
3. trace_path(direction="both") → 调用链/依赖链
4. get_code_snippet(qualified_name=...) → 读关键实现
```

## 与 /understand-project 的区别

| Skill | 回答什么 | 使用时机 | 分析深度 |
|-------|---------|---------|---------|
| `/understand-project` | 项目整体是什么 | 第一次接触项目 | 广度优先 |
| `/analyze-architecture` | 为什么这样设计 | 有具体问题时 | 深度优先 |

## 使用建议

1. **先了解全局**: 首次使用建议先调用 `/understand-project`
2. **具体问题**: 越具体的问题回答越准确
3. **结合证据**: 回答会包含代码证据，位置精确到文件和行号
4. **多角度分析**: 可以追问"有没有更好的方案"获取更深入分析
