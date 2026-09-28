---
name: novel-debug
description: "情节排查：角色矛盾/伏笔遗漏/节奏失控。发现问题后加载。"
tags: [Debug, Novel]
domain: novel
category: novel.baseline
priority: P0
version: 1.0.0
when_to_use: "情节矛盾、角色冲突、伏笔遗漏、节奏失控时排查"
status: stable
---

# Novel Debug — 情节系统排查

复现→定位→修复。对应 Code 域 systematic-debugging。

## 排查流程

复现矛盾 → 缩小范围 → 假设原因 → 验证对照 → 小步修复 → 回归检查

## 角色矛盾

- 说话风格是否独特
- 行为是否符合性格
- 能力/知识是否矛盾

## 伏笔遗漏

- 对照 MEMORY.md 伏笔表
- 检查未回收伏笔
- 追加新伏笔到 MEMORY.md
