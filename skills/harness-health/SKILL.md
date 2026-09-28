---
name: harness-health
description: 系统健康度检查 Skill — 一键输出所有子系统的健康状态
tags:
- Skill
- Observability
- Meta
version: 1.0.0
when_to_use: 调用 harness-health 时
status: peripheral
domain: shared
category: workflow
---
# Harness Health Check Skill

## 激活条件

- 用户说 "/health"、"健康检查"、"检查系统状态"
- Session 启动时（可选：配置了 auto-health-check）
- 发版前质量门禁

## 工作流

1. 调用 `node scripts/harness-health.js`
2. 解析 JSON 输出
3. 对 `warn` 和 `fail` 项生成修复建议
4. 输出可读的健康报告

## 输出示例

```markdown
「Route: 小改动，直接处理」

## Harness Foundry Health Report

**Status**: 🟡 DEGRADED

### Checks
- ✅ Config Validity — All config files valid
- ✅ Reference Integrity — All core files present
- ✅ Execution Context — Model + Protocol present, 3 providers
- ✅ Guardrail Config — 5 input / 5 output rules enabled
- ⚠️ Instinct Quality — 12 instincts, avg confidence 0.52
- ✅ Skill Coverage — 328/328 skills with SKILL.md
- ⚠️ Agent Format Consistency — 5/97 agents with YAML frontmatter

### Recommendations
1. **Instinct Quality** — 平均置信度偏低 (0.52)，建议运行 `/prune --threshold=0.3` 清理低质量 instinct
2. **Agent Format Consistency** — Frontmatter 覆盖率仅 5%，建议渐进式迁移（参考 `adapters/TEMPLATE/`）
```

## 修复建议映射

| Check | fail/warn 建议 |
|-------|---------------|
| config_validity fail | 检查对应 JSON/YAML 文件格式 |
| reference_integrity warn | 创建缺失文件 |
| execution_context fail | 检查 `core/orchestration/execution-context/` 目录 |
| guardrail_config warn | 启用至少 1 条 input + 1 条 output 规则 |
| instinct_quality warn | 运行 `/prune --threshold=0.3` |
| skill_coverage warn | 为缺失 SKILL.md 的目录创建文件 |
| agent_format_consistency warn | 渐进式迁移：参考 `adapters/TEMPLATE/` |
