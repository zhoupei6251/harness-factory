---
name: novel-checkpoint
description: 创建、验证写作进度检查点，确保批量写作不丢失上下文
metadata:
  domain: novel
  priority: P1
  tags:
  - checkpoint
  - progress
  - recovery
version: 1.0.0
when_to_use: 调用 novel-checkpoint 时
status: peripheral
tags:
- novel
domain: novel
category: novel.progress
---

# Novel Checkpoint — 写作检查点

> 创建、验证写作进度检查点，确保批量写作不丢失上下文。
> 借鉴 ECC checkpoint 机制。

## 命令

```
/novel checkpoint [create|verify|list] [name]
```

---

## 创建检查点

### 自动创建场景

| 场景 | 检查点名称 | 说明 |
|------|-----------|------|
| 开书 | `book-start` | 新书创建完成 |
| 完成大纲 | `outline-done` | 大纲确认 |
| 完成章节 | `chapter-{N}-done` | 单章完成 |
| 完成审稿 | `chapter-{N}-reviewed` | 审稿通过 |
| 完成润色 | `chapter-{N}-polished` | 润色完成 |
| 完成卷 | `volume-{N}-done` | 单卷完成 |
| 完成书籍 | `book-complete` | 全部完成 |

### 创建流程

```markdown
/novel checkpoint create chapter-5-done

1. 检查 MEMORY.md 状态
2. 创建 git stash 或 commit
3. 记录检查点到状态文件

┌─────────────────────────────────────────┐
│  ✓ 检查点已创建                          │
│                                         │
│  名称：chapter-5-done                   │
│  章节：第5章                            │
│  状态：审稿通过                         │
│  时间：{时间戳}                         │
│  提交：{commit-hash}                   │
└─────────────────────────────────────────┘
```

---

## 验证检查点

### 验证流程

```markdown
/novel checkpoint verify chapter-5-done

1. 读取检查点状态
2. 对比当前状态

┌─────────────────────────────────────────┐
│  检查点对比                              │
│                                         │
│  名称：chapter-5-done                 │
│  章节：第5章                            │
│                                         │
│  变化：                                │
│  ✓ 章节文件存在                       │
│  ✓ 字数达标（3200字）                 │
│  ✓ 审稿通过                           │
│  ✓ MEMORY.md 已更新                   │
│                                         │
│  状态：同步                            │
└─────────────────────────────────────────┘
```

### 检查清单

| 检查项 | 说明 |
|--------|------|
| 章节文件存在 | `章节正文/{书名}/第{N}章_*.md` |
| 字数达标 | ≥2000 字 |
| 审稿状态 | 已通过/待审稿 |
| MEMORY 更新 | 章节摘要已记录 |
| 伏笔状态 | 已更新 |
| 人物状态 | 如有变更已记录 |

---

## 列出检查点

```markdown
/novel checkpoint list

┌─────────────────────────────────────────┐
│  📍 检查点列表                            │
├─────────────────────────────────────────┤
│                                         │
│  book-start         2026-06-28 10:30   │
│  outline-done       2026-06-28 11:45   │
│  chapter-1-done    2026-06-28 14:20   │
│  chapter-1-reviewed 2026-06-28 15:00   │
│  chapter-2-done    2026-06-29 09:15   │
│  chapter-3-done    2026-06-29 10:30   │
│  ...                                    │
│                                         │
│  当前：chapter-3-done                  │
│  进度：3/10 章                         │
└─────────────────────────────────────────┘
```

---

## 状态文件格式

检查点状态存储在 `章节正文/{书名}/.checkpoints/`

```markdown
# 检查点状态

## 检查点
| 名称 | 时间戳 | 章节 | 状态 | 提交 |
|------|--------|------|------|------|
| book-start | 2026-06-28 10:30 | - | 完成 | abc1234 |
| outline-done | 2026-06-28 11:45 | - | 完成 | def5678 |
| chapter-1-done | 2026-06-28 14:20 | 第1章 | 完成 | ghi9012 |

## 当前进度
- 已完成章节：3/10
- 最近检查点：chapter-3-done
- 上次写作：2026-06-29 10:30
```

---

## Git 集成

### 自动提交

```bash
# 创建检查点时自动提交
git add 章节正文/{书名}/
git commit -m "checkpoint: {检查点名称}"

# 记录到检查点日志
echo "{时间戳} | {检查点名称} | $(git rev-parse --short HEAD)" >> .checkpoints.log
```

### 恢复检查点

```markdown
# 从检查点恢复
git stash
git checkout {commit-hash}
```

---

## 批量写作中的检查点

```markdown
批量写作流程中的自动检查点：

WU-1 完成 → checkpoint create chapter-1-done
WU-2 完成 → checkpoint create chapter-2-done
WU-3 完成 → checkpoint create chapter-3-done
...

所有 WU 完成后 → checkpoint create batch-done
```

---

## 禁止事项

- ❌ 不更新 MEMORY.md 就创建检查点
- ❌ 创建检查点时不提交 git
- ❌ 跳过字数检查
- ❌ 跳过审稿状态检查

---

## 依赖

- `skills/novel-quick-write/` — 写作
- `skills/novel-dashboard/` — 状态显示
- `rules/novel/templates/memory-template.md` — 记忆模板
