---
name: memory-manager
description: 通用项目记忆管理引擎，三域（code/novel/news）共用架构，域隔离，状态机追踪，Agent 交接压缩协议
metadata:
  domains: [code, novel, news]
  priority: P0
  tags: [memory, state, persistence, cross-domain]
version: 2.0.0
status: stable
tags: [memory, state, persistence, cross-domain]
when_to_use: 调用 memory-manager 时
domain: all
category: shared.memory
---

# Memory Manager — 通用项目记忆管理引擎

> 三域共用架构。核心逻辑共享，域字段由 `domain-config/<domain>.yaml` 注入。
> Novel 域保留 Mem0 增强模式。Code/News 域从空白实现生产级记忆。

## 激活条件（三域通用）

- 会话开始 → 读 MEMORY.md + state.json，3 句话概括进度
- 工作单元完成后 → 更新 index、状态追踪
- Agent 交接时 → 输出 Handoff 压缩包
- 会话结束 → 压缩记忆、更新状态、写回全局索引
- 用户说"接着上次继续" → 触发跨会话恢复

---

## 架构总览

```
┌──────────────────────────────────────────────────────────────┐
│                       Memory Manager                          │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────┐    ┌────────────────────────────┐  │
│  │   File Mode (default) │    │   Mem0 Mode (novel only)   │  │
│  │   MEMORY.md + state   │    │   SQLite + Vector Store    │  │
│  │   三域统一模板         │    │   长篇(>50章) 自动提取      │  │
│  └──────────┬───────────┘    └──────────┬─────────────────┘  │
│             │                           │                     │
│             └───────────┬───────────────┘                     │
│                         │                                     │
│               ┌─────────▼──────────┐                         │
│               │ Unified Interface  │                         │
│               │ search / remember  │                         │
│               │ forget / recall    │                         │
│               └────────────────────┘                         │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│  Domain Configs:                                              │
│  core/memory/domain-config/code.yaml   ← Code 域注入          │
│  core/memory/domain-config/novel.yaml  ← Novel 域注入 (legacy)│
│  core/memory/domain-config/news.yaml   ← News 域注入          │
└──────────────────────────────────────────────────────────────┘
```

---

## 三层隔离

| 层级 | 存储位置 | 内容 | 隔离方式 |
|------|---------|------|---------|
| L1 域 | `{project}/MEMORY.md` | 本项目本域的具体记忆 | 域标签 |
| L2 项目 | 每项目根目录 | 独立 MEMORY.md | 路径隔离 |
| L3 全局 | `~/.claude/GLOBAL-MEMORY.md` | 项目索引（无具体内容） | 只索引 |

---

## File Mode：统一模板

所有域使用 `core/memory/state-schema.yaml` 定义模板，域字段从 domain-config 注入。

### Code 域 MEMORY.md 示例

```yaml
state:
  meta:
    domain: code
    project: my-app
    phase: implement
    last_updated: 2026-07-03
    active_wu: [wu-01, wu-02]
  memory:
    modules:
      - path: src/auth/
        status: modified
        summary: "重构认证模块"
    tech_debt:
      - "test coverage 不足"
  index:
    - id: src/auth/login.ts
      type: source
      status: in_progress
      summary: "迁移登录到 JWT"
  blockers:
    - id: BLK-01
      desc: "CI 流水线失败"
      severity: blocker
  learning:
    patterns_extracted: 5
    traps_recorded: 2
```

### News 域 MEMORY.md 示例

```yaml
state:
  meta:
    domain: news
    project: tech-weekly
    phase: implement
  memory:
    articles:
      - id: article-5
        title: "AI 监管新政策"
        word_count: 1200
        status: draft
    sources:
      - name: "路透社"
        reliability: high
    fact_check:
      - claim: "新政策将于8月生效"
        verified: true
    threads:
      - name: "AI 监管"
        status: active
```

---

## Novel 域：伏笔状态机

```
planted → referenced → foreshadowed → resolved
                                    ↘ abandoned
```

### Mem0 增强模式（Novel 可选）

> 保留原有全部能力：Entity Linking + 多信号检索 + 时间感知 + Memory Decay。

| 能力 | 说明 |
|------|------|
| Entity Linking | 自动从正文提取实体并跨章链接 |
| 多信号检索 | 语义 + BM25 + 实体匹配三路融合 |
| 时间感知 | 人物状态变更时间线，自动检测矛盾 |
| Memory Decay | >30 章未更新伏笔自动标记 ⚠️ |

---

## Agent 交接压缩协议（三域通用）

```markdown
## HANDOFF: <from> → <to>
### 产物
### 关键变动 (≤ 3 条)
### 状态变更
### 给下游的上下文 (≤ 100 token)
```

| 域 | 交接 | 配额 |
|----|------|------|
| code | coder → reviewer | ≤ 100 token |
| novel | writer → reviewer | ≤ 150 token |
| novel | reviewer → humanizer | ≤ 80 token |
| news | writer → fact-checker | ≤ 80 token |

---

## 跨会话恢复（三域通用）

1. 读 `~/.claude/GLOBAL-MEMORY.md` → 找当前项目
2. 读 `{project}/MEMORY.md` → 加载域配置
3. 读 state.json → 获取精确状态
4. 压缩 ≤500 token → 喂 worker

---

## 压缩策略

| 域 | 触发 | 保留规则 |
|----|------|---------|
| code | 每 10 WU | 最近 5 WU 完整 + 旧 WU 200 字摘要 |
| novel | 每 5 章 | 最近 3 章全文 + 旧章摘要 |
| news | 每 20 篇 | 最近 5 篇完整 + 旧篇 200 字摘要 |

## 禁止

- ❌ 跳过记忆读取直接工作
- ❌ 压缩时删除原文
- ❌ 跨域混用记忆（域标签隔离）
- ❌ Agent 交接超过配额
- ❌ 会话结束不写回 MEMORY.md

## 依赖

- `core/memory/state-schema.yaml` — 统一状态结构
- `core/memory/domain-config/<domain>.yaml` — 域配置
- `agents/memory-keeper.md` — 记忆管理员角色
- `core/memory/continuous-learning/protocol.md` — 连续学习协议
- **Mem0 Mode** (novel 可选): `pip install mem0`
