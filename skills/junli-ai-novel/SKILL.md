---
name: junli-ai-novel
description: 长篇网文核心写作引擎，支持章节续写、扩写、重写，维护人物状态和伏笔追踪
metadata:
  origin: harness-ink
  priority: P0
  tags:
  - writing
  - novel
  - long-form
version: 1.0.0
when_to_use: 调用 junli-ai-novel 时
status: peripheral
tags:
- shared
domain: novel
category: novel.creation
---
# 君黎 AI 小说写作引擎

## 激活条件

- 用户要求写小说章节（"写第X章"、"续写"、"扩写"）
- 需要生产 2000 字以上的正文内容
- 涉及人物对话、情节推进、场景描写

## 核心能力

### 章节写作
- 单章正文生产（2000-5000 字）
- 续写：承接上一章结尾，保持情节连贯
- 扩写：基于大纲扩展为完整章节
- 重写：根据审稿意见返修

### 人物与伏笔管理
- 写章前读取 `MEMORY.md` 了解人物状态
- 写章后更新人物状态、伏笔状态
- 对话符合人物身份和性格

### 字数控制
- 字数自检：必须 ≥2000 字（包含符号）
- 使用 Python 脚本统计字数

## 工作流程

1. **读取上下文**
   - 读取 `MEMORY.md`：上一章摘要、人物状态、伏笔
   - 读取 `大纲.md`：本章目标
   - 读取 `章节目录.md`：已完成章节索引

2. **写作执行**
   - 承接上一章结尾
   - 推进本章目标
   - 埋设/回收伏笔
   - 保持人物声音一致

3. **自检交付**
   - 字数统计 ≥2000 字
   - 检查是否有 AI 套路表达（见 `core/NEVER.md`）
   - 更新 `MEMORY.md`

## 禁止事项

- ❌ 未经润色直接交付（必须经过 humanizer）
- ❌ 跳过记忆读取直接写
- ❌ 自行审稿/润色
- ❌ 使用 AI 套路化表达
- ❌ 字数不足 2000 字

## 产物

- `章节正文/第XXX章_标题.md`
- 更新 `MEMORY.md`（人物状态、伏笔状态）

## 依赖

- `core/NEVER.md`：AI 写作禁忌清单
- `agents/novel-writer.md`：写手角色定义
- `agents/humanizer.md`：润色师角色定义
