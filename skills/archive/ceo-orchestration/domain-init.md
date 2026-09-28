---
name: ceo-domain-init
description: "新域初始化 — 当用户新开一个领域时，CEO 生成对应的 Leader、Worker、配置和目录结构"
---

# Domain Init（新域初始化）

## 激活条件

用户说 "新开了一个 xxx 领域" / "我想要一个 yy 域" 时触发。

## 工作流程

### 1. 确认域信息

与用户确认：
- 领域名称（如 "podcast" / "game" / "education"）
- 主要 Worker 角色（默认 3 个：writer / reviewer / specialist）

### 2. 生成文件

按模板生成以下文件：

```
agents/
  ├── leader-<domain>.md    # 新域 Leader

agents/<domain>/
  ├── writer.md
  ├── reviewer.md
  └── specialist.md

rules/<domain>/
  ├── patterns.md
  ├── security.md
  └── traps.md

contexts/<domain>.md

.artifacts/<domain>-runtime/
  ├── plans/
  ├── execution-logs/
  └── tracking/
```

### 3. 注册域

在以下文件中注册新域：

```yaml
# domain-config.yaml
domains:
  <domain>:
    primary_agents: [leader-<domain>]
    secondary_agents: [writer, reviewer, specialist]
```

```markdown
# intent-routing.md
| 用户说的话包含... | 意图 | 动作 |
|------------------|------|------|
| <domain 关键词> | <domain>:init | 调用 domain-init |
```

### 4. 初始化 handoff 目录

```bash
handoff/<domain>/
  └── .gitkeep
```

## 模板引用

- Leader 模板：`agents/leader-novel.md`（复用结构）
- Worker 模板：按域类型参照 code/novel/news 的对应 Worker
- rules 模板：`rules/novel/`（参照）

## 验证

生成后自动检查：
- 所有文件存在
- domain-config.yaml 格式正确
- intent-routing.md 路由条目已添加

## 错误处理

| 场景 | 处理 |
|------|------|
| 域名已存在 | 告知用户，建议改名 |
| 文件写入失败 | 重试，仍失败汇报用户 |
| 模板缺失 | 降级为手工创建，告知用户哪些需要手动补 |
