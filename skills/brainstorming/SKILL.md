---
name: brainstorming
description: You MUST use this before any creative work - creating features, building
  components, adding functionality, or modifying behavior. Explores user intent, requirements
  and design before implementation.
version: 1.2.0
when_to_use: 调用 brainstorming 时
status: peripheral
tags:
- 头脑风暴
- 设计
domain: shared
category: shared.planning
---

# Brainstorming Ideas Into Designs

## Overview

Help turn ideas into fully formed designs and specs through natural collaborative dialogue.

Start by understanding the current project context, then ask questions one at a time to refine the idea. Once you understand what you're building, present the design in small sections (200-300 words), checking after each section whether it looks right so far.

## 场景检测（首轮执行）

### 自动识别场景

如果用户提到以下任一关键词，自动识别场景并注入对应配置：

| 场景 | 关键词 |
|------|--------|
| product (前端) | 前端、页面、HTML、Vue、React、卖给大学生 |
| product (后端) | 后端、接口、API、Spring |
| product (全栈) | 全栈、前后端都要、完整 |

**识别到 product 场景时：**
1. 在对话开头输出：`「Route: product」`
2. 告知用户识别到的场景类型
3. 询问确认或让用户选择
4. 加载对应场景的 skills 和 deliverables 配置

### 无法自动识别

无法识别时，问用户选择题：

```
请问您要服务的客户是哪种类型？
1. 只想要前端页面的大学生（HTML/Vue/React）
2. 只想要后端接口的大学生（Spring/Express 等）
3. 前后端都要的大学生（全栈）
4. 其他（请描述）
```

<HARD-GATE>
在设计被用户批准前，禁止：
- 写任何代码
- 创建任何文件（设计文档除外）
- 执行构建命令
- 调用实现类 skill

违反将导致立即停止并输出门禁消息。详见 `core/rules/design-gate.md`
</HARD-GATE>

## Anti-Pattern: "This Is Too Simple To Need A Design"

Every project goes through this process. A todo list, a single-function utility, a config change — all of them. "Simple" projects are where unexamined assumptions cause the most wasted work. The design can be short (a few sentences for truly simple projects), but you MUST present it and get approval.

## The Process

**Understanding the idea:**
- Check out the current project state first (files, docs, recent commits)
- Ask questions one at a time to refine the idea
- Prefer multiple choice questions when possible, but open-ended is fine too
- Only one question per message - if a topic needs more exploration, break it into multiple questions
- Focus on understanding: purpose, constraints, success criteria

**Exploring approaches:**
- Propose 2-3 different approaches with trade-offs
- Present options conversationally with your recommendation and reasoning
- Lead with your recommended option and explain why

**Presenting the design:**
- Once you believe you understand what you're building, present the design
- Break it into sections of 200-300 words
- Ask after each section whether it looks right so far
- Cover: architecture, components, data flow, error handling, testing
- Be ready to go back and clarifying if something doesn't make sense

## After the Design

**Documentation:**
- Write the validated design to `docs/plans/YYYY-MM-DD-<topic>-design.md`
- Use elements-of-style:writing-clearly-and-concisely skill if available
- Commit the design document to git

**Implementation (if continuing):**
- Ask: "Ready to set up for implementation?"
- Use superpowers:using-git-worktrees to create isolated workspace
- Use superpowers:writing-plans to create detailed implementation plan

## Key Principles

- **One question at a time** - Don't overwhelm with multiple questions
- **Multiple choice preferred** - Easier to answer than open-ended when possible
- **YAGNI ruthlessly** - Remove unnecessary features from all designs
- **Explore alternatives** - Always propose 2-3 approaches before settling
- **Incremental validation** - Present design in sections, validate each
- **Be flexible** - Go back and clarify when something doesn't make sense
