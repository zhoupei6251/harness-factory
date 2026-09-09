---
name: index-project
description: "为项目建立代码索引。触发：大型项目、需要精准定位符号、快速查找调用关系。"
version: 1.0.0
when_to_use: 建立代码索引时
status: peripheral
tags:
- intelligence
- code
- tactical
domain: code
category: code.intelligence
---

# /index-project

使用 codebase-memory 为项目建立代码索引。

## 使用场景

| 场景 | 说明 |
|------|------|
| 大型项目 (>100 文件) | 索引后查询效率提升 57%+ |
| 需要快速定位符号 | 代替逐文件 grep |
| 分析影响范围 | 变更前的必要准备 |

## 索引后可用工具

| 工具 | 用途 |
|------|------|
| `/query-symbol` | 搜索符号定义 |
| `/get-callers` | 查找调用方 |
| `/get-callees` | 查找被调用方 |
| `/analyze-impact` | 评估变更影响 |

## 性能指标

| 指标 | 目标 |
|------|------|
| 10万行代码 | < 5 分钟 |
| 查询响应时间 | < 100ms |
| Token 节省 | >= 30% |

## 增量索引

```bash
# 仅索引变更的文件
detect_changes

# 监视文件变更，自动索引
index_status
```
