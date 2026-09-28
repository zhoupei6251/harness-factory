---
name: ceo-performance-analyst
description: "绩效分析 + PUA 策略 — CEO 基于 Worker 绩效数据决定激励/降级策略"
---

# Performance Analyst（绩效分析）

## 激活条件

- Domain Leader 汇报完成时自动调用
- 用户说 "检查 Worker 表现" 时触发

## 工作流程

### 1. 读取绩效数据

从 `handoff/<domain>-result.md` 中提取 Worker 绩效：

```markdown
## Worker 绩效
- Writer: WU=10, success=9, rework=1, 返工率=10%
- Reviewer: WU=10, success=10, rework=0, 返工率=0%
```

### 2. 更新全局索引

更新 `performance/worker-stats.json`：

```json
{
  "Writer": {
    "total_wu": 10,
    "success_count": 9,
    "rework_count": 1,
    "success_rate": 0.9,
    "rework_rate": 0.1
  }
}
```

### 3. 计算趋势

- 相比上次统计，成功率上升/下降多少？
- 返工率是否持续偏高？

### 4. 生成 PUA 策略

#### 表扬（success_rate ≥ 0.9）

```markdown
### 表扬
- Writer 表现优秀（成功率 90%），继续维持当前节奏
- Reviewer 表现稳定，可委以更复杂任务
```

#### 降级（success_rate < 0.7 或 rework_rate > 0.3）

```markdown
### 降级建议
- Coder 返工率偏高（35%），建议降级为轻量任务
- 或安排 Code Reviewer 加强审查
```

### 5. 记录裁决

将 PUA 策略写入 `performance/worker-stats.json` 的 `last_action` 字段。

### 6. 更新 Worker 标签 (S-2)

从 handoff 结果中提取 Worker 的领域标签（tags），更新 `performance/worker-stats.json`：

```json
{
  "Writer": {
    "tags": {"修仙": 0.95, "都市": 0.80},
    "last_used": "2026-06-26"
  }
}
```

标签成功率 = 该标签下成功 WU / 该标签下总 WU

## 阈值定义

| 指标 | 表扬线 | 警告线 | 降级线 |
|------|--------|--------|--------|
| success_rate | ≥ 0.9 | 0.7-0.9 | < 0.7 |
| rework_rate | ≤ 0.1 | 0.1-0.3 | > 0.3 |

## 数据来源

- `handoff/<domain>-result.md` — 各域 Worker 绩效
- `performance/worker-stats.json` — 全局绩效索引

## 输出

更新 `performance/worker-stats.json`，可选生成 PUA 建议供 CEO 决策。
