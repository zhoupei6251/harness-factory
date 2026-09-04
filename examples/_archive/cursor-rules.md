# Cursor 项目规则模板

> 复制此文件到项目根目录 `.cursor/rules/harness.mdc`

## 元数据

```yaml
description: Harness Foundry 项目规则
globs: **/*
alwaysApply: true
```

## 规则

### 核心原则
- 三域统一：代码 / 小说 / 新闻共用 harness-foundry 框架
- 按需加载：只加载当前场景需要的规则
- 持续学习：会话结束自动提取经验

### 代码开发
- 加载 `harness-foundry/rules/code/<tech>/` 规则
- 加载 `harness-foundry/rules/common/` 通用规则
- 使用 `/code` 进入开发模式
- 使用 `/review` 进行代码审查
- 使用 `/test` 进行 TDD 开发

### 小说创作
- 加载 `harness-foundry/rules/novel/` 规则
- 使用 `/novel` 进入创作模式
- 使用 `/write` 写章节
- 使用 `/evaluate` 审稿评分

### 新闻采编
- 加载 `harness-foundry/rules/news/` 规则
- 使用 `/news` 进入采编模式
- 使用 `/hot` 追踪热点
- 使用 `/fact` 事实核查

### 禁止事项
- 禁止使用 `harness-orchestration` 处理小说（用 `novel-orchestrator`）
- 禁止在代码中硬编码密钥
- 禁止忽略错误
- 禁止提交敏感信息到 Git
