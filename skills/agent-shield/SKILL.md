---
name: agent-shield
description: 安全审计：扫描配置漏洞、注入风险、MCP 安全问题。保护 Harness Foundry 免受提示注入、权限过度、Hook 注入等攻击。
version: 1.0.0
when_to_use: 调用 agent-shield 时
status: peripheral
tags:
- shared
domain: shared
category: workflow
---
# AgentShield

## 配置 fallback（2026-09 phase-2）

- 优先读 `~/.claude/agent-shield/config.json`（用户级）
- 回退到本 SKILL.md 的"扫描范围"与 rules/ 列表（项目级，替代已删除的 `hooks/guardrails/guardrail-config.json`）
- 无配置时仅 warning，不抛错——核心规则在 `core/NEVER.md`，本 skill 仅做"额外加固"层

## 功能概述

AgentShield 是 Harness Foundry 的安全审计系统，用于检测和防御 Agentic AI 环境中的安全威胁。

## 扫描范围

### 1. Secret 检测 (CRITICAL)

检测硬编码的密钥、token、密码：

| 类型 | 模式 | 严重级别 |
|------|------|---------|
| OpenAI API Key | `sk-[a-zA-Z0-9]{48}` | CRITICAL |
| GitHub Token | `ghp_[a-zA-Z0-9]{36}` | CRITICAL |
| AWS Access Key | `AKIA[0-9A-Z]{16}` | CRITICAL |
| Email+Password | `[a-z]+@[a-z.-]+:[a-zA-Z0-9]+` | CRITICAL |
| 私钥文件 | `BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY` | CRITICAL |
| Generic Secret | `secret['\"]?\s*[:=]\s*['\"][^'\"]+['\"]` | HIGH |

### 2. 注入风险检测 (HIGH)

| 类型 | 模式 | 描述 |
|------|------|------|
| Shell 注入 | `; rm -rf`, `$(curl`, `\`wget\` | 命令注入 |
| 路径遍历 | `\.\.\/`, `\.\.\\` | 目录穿越攻击 |
| Prompt 注入 | `ignore (previous|above) instructions` | 角色劫持 |
| 越权命令 | `__import__\(`, `os\.system\(` | 系统调用 |

### 3. Hook 安全审计 (HIGH)

检查 hooks 配置是否安全：

- 命令注入风险
- 路径遍历风险
- 恶意脚本检测
- 权限过度配置

### 4. MCP 安全评估 (MEDIUM)

评估 MCP 服务器风险：

| 风险类型 | 描述 |
|---------|------|
| 数据外泄 | MCP 工具是否可能外传数据 |
| 权限过度 | MCP 权限是否超出必要范围 |
| 信任边界 | 未经确认自动加载的 MCP |

### 5. 配置漏洞检测

| 检查项 | 描述 |
|-------|------|
| 绕过信任确认 | 在 `.claude/` 中配置未确认的 MCP |
| 过度权限 | 宽泛的文件系统或网络访问 |
| 环境变量注入 | 可被覆盖的 `ANTHROPIC_BASE_URL` 等 |

## 使用方式

### 命令行扫描

```bash
# 完整扫描
node scripts/security/scan.js

# 扫描指定路径
node scripts/security/scan.js --path ./hooks

# 仅扫描 secrets
node scripts/security/scan.js --type secrets

# 仅扫描 hooks
node scripts/security/scan.js --type hooks

# 输出 JSON 格式
node scripts/security/scan.js --format json
```

### Skill 调用

```
/agent-shield scan
/agent-shield scan --type secrets
/agent-shield report
```

### 集成到 CI/CD

```yaml
# .github/workflows/security.yml
- name: AgentShield Security Scan
  run: node scripts/security/scan.js
```

## 输出格式

### 人类可读格式

```markdown
## AgentShield 安全报告

### 扫描时间
2026-07-02T10:30:00Z

### 总体评分
B

### 扫描统计
- 文件数: 156
- 发现问题: 3
- 严重: 1
- 重要: 1
- 警告: 1

### 发现问题

#### 严重（必须修复）
- `[SECRET] settings.json:23` - 检测到疑似 API Key

#### 重要（建议修复）
- `[HOOK-INJECTION] hooks.json:15` - 命令注入风险

#### 警告（可选）
- `[PERMISSION] mcp.json:8` - 权限过于宽松

### 建议
1. 立即移除硬编码的 secrets
2. 限制 hooks 中的 shell 执行
3. 审查 MCP 权限配置
```

### JSON 格式

```json
{
  "timestamp": "2026-07-02T10:30:00Z",
  "files": 156,
  "issues": [
    {
      "type": "SECRET",
      "severity": "CRITICAL",
      "file": "settings.json",
      "line": 23,
      "pattern": "sk-[a-zA-Z0-9]{48}",
      "description": "检测到疑似 OpenAI API Key"
    }
  ],
  "score": "B",
  "summary": {
    "critical": 1,
    "high": 1,
    "medium": 0,
    "low": 1
  }
}
```

## 安全评分

| 评分 | 含义 | 行动 |
|------|------|------|
| A | 无问题 | 无需行动 |
| B | 轻微问题 | 建议修复 |
| C | 重要问题 | 应该修复 |
| D | 严重问题 | 必须修复 |
| F | 阻塞问题 | 立即修复 |

## 与 Guardrail 的关系

AgentShield 是**主动防御**，在问题发生前检测。
Guardrail 是**被动拦截**，在运行时阻止恶意行为。

两者结合提供完整的安全覆盖：
- **预防**: AgentShield 扫描配置
- **检测**: Guardrail 监控运行时
- **响应**: Kill Switch 中止异常会话

## 参考标准

- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-llm-applications/)
- [OWASP MCP Top 10](https://github.com/OWASP/wstg/blob/master/flipc/docs/mcp/)
- Anthropic Claude Code Security Guidelines
- Snyk ToxicSkills 研究报告

## 安全最佳实践

1. **最小权限原则**: 只授予完成任务所需的最小权限
2. **隔离执行**: 高风险任务在沙箱/容器中运行
3. **多层防御**: AgentShield + Guardrail + 人工审批
4. **持续监控**: 记录所有工具调用和审批决策
5. **定期审计**: 定期运行 AgentShield 检查配置
