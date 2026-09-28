---
name: understand-project
description: "理解项目结构和架构，生成知识图谱。触发：接手新项目、需要了解项目全局、询问架构设计。"
version: 2.0.0
when_to_use: 需要理解项目结构时
status: peripheral
tags:
- intelligence
- code
- strategic
domain: code
category: code.intelligence
---

# /understand-project

使用 codebase-memory-mcp 分析项目结构，建立/查询知识图谱。

## 使用场景

| 场景 | 调用时机 | 价值 |
|------|---------|------|
| 新项目接手 | plan 阶段开始时 | 5 分钟了解项目全貌 |
| 架构评审 | design 阶段 | 提供架构上下文 |
| 大型重构 | implement 前 | 识别影响范围 |
| Bug 定位 | verify 阶段 | 快速定位相关模块 |

## MCP 调用协议

### Request

```json
{
  "tool": "index_repository",
  "params": {
    "repo_path": "/path/to/project",
    "mode": "moderate"
  }
}
```

### Response

```json
{
  "project": "harness-foundry",
  "nodes_indexed": 1234,
  "edges_indexed": 5678
}
```

## 工作流程

```
1. index_status  → 检查项目是否已索引
2. 未索引       → index_repository(repo_path=...) 建立索引
3. get_architecture(aspects=["overview"]) → 项目全貌
4. 需要细节     → search_graph / get_code_snippet 深入
```

## 索引生命周期

索引由 codebase-memory-mcp 管理。不要手动删除或操作其内部索引目录。项目代码变更后，`detect_changes` 可增量更新。

## 与其他 Skill 的配合

```
/understand-project  →  get_architecture 获取全局理解
        ↓
/analyze-architecture  →  get_architecture 深入分析架构
        ↓
/index-project  →  建立索引（首次）
        ↓
/query-symbol  →  快速定位代码
```

## 限制与注意事项

1. **首次索引较慢**: 完整索引可能需要 1-5 分钟
2. **需要增量更新**: 代码变更后用 `detect_changes` 更新
3. **图谱存储**: 由 codebase-memory-mcp 管理，位置透明
4. **隐私**: 所有分析在本地进行，代码不外传
