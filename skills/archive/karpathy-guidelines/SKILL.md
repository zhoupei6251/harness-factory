---
name: karpathy-guidelines
description: "写代码、审查代码、重构代码时的行为准则：先想再写、保持简单、只改必要的，目标驱动。code 域默认基线，P0 优先级。"
tags: [Rules, Code, Baseline]
domain: code
category: code.baseline
priority: P0
version: 1.0.0
when_to_use: "写代码、审查代码、重构代码时的行为准则基线"
status: stable
---

# Karpathy Guidelines Skill

> code 域强制性前置检查。任何代码编写/修改任务启动前必须加载。

## 速查

Read `core/karpathy-guidelines.md` 获取完整 9 条规则。四句话记住：

**先想后写 → 保持简单 → 精准修改 → 目标驱动**

## 9 条规则摘要

| # | 规则 | 核心 |
|---|------|------|
| 1 | 先想后写 | 不确定就问，该反驳就反驳 |
| 2 | 保持简单 | 过度设计检测 + 三个问题验证 |
| 3 | 精准修改 | 只碰要改的，不碰无关代码 |
| 4 | 目标驱动 | 先定怎么算通过，再写代码 |
| 5 | 先读后写 | 没读过的代码不要改 |
| 6 | 工具优先 | Write/Edit 不 shell 重定向 |
| 7 | 不静默失败 | 报错不吞异常 |
| 8 | 冲突显式化 | 矛盾立刻说出来 |
| 9 | 写完自查 | 够简洁吗？能删 20% 吗？ |

## 完整流水线

```
karpathy-guidelines (写前思维模式)
    → 写代码
    → simplify (自查简洁度)
    → code-review (五轴审查)
```

**这些准则是行为基线，不是建议。违反任何一条都应被标记。**
