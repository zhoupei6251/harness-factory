---
name: ceo-orchestration
description: CEO 角色主 Skill — 跨域协调入口，调用子 Skill 完成各项职责
version: 1.0.0
when_to_use: 调用 ceo-orchestration 时
status: peripheral
tags:
- shared
domain: shared
category: workflow
---
# CEO Orchestration

## 激活条件

以下任一情况激活本 Skill：
- 用户首次输入需求（CEO 路由决策）
- 用户说 "检查系统健康" / "/health"
- 用户说 "新开了一个 xxx 领域"
- Domain Leader 汇报失败，需 CEO 介入

## 子 Skill

| 子 Skill | 作用 |
|---------|------|
| intent-router | 意图理解 + 路由到域 |
| health-monitor | 系统健康监控 |
| domain-init | 新域初始化 |
| performance-analyst | 绩效分析 + PUA 策略 |
| skill-quality | Skill 质量评分 (S-1) |
| worker-matcher | Worker 经验学习匹配 (S-2) |
| context-bus | 跨会话上下文总线 (S-3) |

## 核心流程

### 流程一：接收需求

```
用户输入
  │
  ▼
加载 ceo-orchestration
  │
  ▼
调用 intent-router → 判断域
  │
  ▼
生成 handoff/ceo-task.md
  │
  ▼
通知 Domain Leader（通过 state.json）
  │
  ▼
等待结果
```

### 流程二：接收汇报

```
Domain Leader 写 handoff/<domain>-result.md
  │
  ▼
CEO 读取结果文件
  │
  ├── status: success → 整合全局摘要，通知用户
  ├── status: failed → 分析 blocked_wu + recommendation
  │                     → 需要用户介入？→ 汇报用户
  │                     → 可自行解决？→ 调用仲裁子 Skill
  │
  ▼
更新 performance/worker-stats.json
```

## 阶段门禁

CEO 的阶段门禁与 Domain Leader 不同：
- 无需 spec/plan 确认（那是 Domain Leader 的职责）
- 唯一门禁：handoff 文件写入成功

## 成功标准

- 用户需求被正确路由到对应域
- handoff 文件格式正确
- Domain Leader 汇报被正确处理
- 绩效数据被正确更新

## 失败处理

| 失败场景 | 处理 |
|---------|------|
| intent-router 无法判断域 | 反问用户确认域 |
| handoff 写入失败 | 重试 1 次，仍失败通知用户 |
| Domain Leader 无响应 | 超时 5 分钟，主动查询 state.json |
