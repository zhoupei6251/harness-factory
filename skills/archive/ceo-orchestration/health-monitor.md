---
name: ceo-health-monitor
description: "系统健康监控 — CEO 定期或按需检查 harness-foundry 的各项健康指标"
---

# Health Monitor（健康监控）

## 激活条件

- 用户说 "检查系统健康" / "/health"
- 每周定时自动触发
- CEO 主动判断需要检查时

## 工作流程

### 1. 执行健康检查

调用 `node scripts/harness-health.js --json`，获取 7 项检查结果：

```json
{
  "config_validity": "pass",
  "reference_integrity": "pass",
  "execution_context": "pass",
  "guardrail_config": "pass",
  "instinct_quality": "warn",
  "skill_coverage": "pass",
  "agent_format_consistency": "pass"
}
```

### 2. 异常分析

| 状态 | CEO 动作 |
|------|---------|
| healthy | 静默通过，无需汇报 |
| degraded | 汇报用户，列出 warn 项 + 修复建议 |
| unhealthy | 立即汇报用户，标记 critical 项 |

### 3. 生成报告

汇报格式：

```
## System Health Report

Status: DEGRADED

### Checks
- ✅ config_validity
- ⚠️ instinct_quality: 12 instincts, avg 0.52 (偏低)

### Recommendations
1. 运行 /prune --threshold=0.3 清理低置信度 instinct
2. 考虑 /evolve 触发进化
```

## 关注指标

- instinct_quality：是否有新 instinct 积累
- execution_context：Provider 是否正常工作
- guardrail_config：规则是否完整

## 主动触发阈值

| 指标 | 触发阈值 |
|------|---------|
| instinct_quality | avg_confidence < 0.5 |
| guardrail_config | input_enabled < 3 或 output_enabled < 3 |
| execution_context | provider count < 2 |

低于阈值时，CEO 主动提醒用户。

## 关联

- CLI: `scripts/harness-health.js`
- Protocol: `core/observability/health-protocol.md`
