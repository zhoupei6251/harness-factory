---
name: ceo-skill-quality
description: "Skill 质量评分 — CEO 定期评估 skill 质量，识别僵尸 skill"
---

# Skill Quality（Skill 质量评分）

## 激活条件

- 用户说 "检查 skill 质量" / "/skill-quality"
- CEO 定期触发（月度审计）
- S-1 新增子 Skill

## 工作流程

### 1. 执行评分

调用 `bash scripts/skill-quality-check.sh`，获取所有 skill 的评分。

### 2. 分析结果

| 分数段 | 状态 | CEO 动作 |
|--------|------|---------|
| ≥ 80 | TOP | 无需操作 |
| 50-79 | OK | 无需操作 |
| 30-49 | WARN | 标记，建议改进元数据完整性 |
| < 30 | ZOMBIE | 建议归档或删除 |

### 3. 生成报告

```markdown
## Skill 质量报告

### 概览
- 总数: 331
- TOP: 8
- OK: 302
- WARN: 15
- ZOMBIE: 6

### 僵尸 Skill
- skill-a (25 分) — 建议归档
- skill-b (18 分) — 建议删除

### 改进建议
- 3 个 skill 缺少 description 字段
- 2 个 skill 缺少触发条件描述
```

## 输出

更新 `performance/worker-stats.json` 的 `skill_quality` 字段。

## 关联

- 评分脚本：`scripts/skill-quality-check.sh`
- 健康监控：CEO health-monitor Skill（skill_coverage 指标）
