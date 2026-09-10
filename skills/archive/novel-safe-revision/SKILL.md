---
name: novel-safe-revision
description: "安全返修：审稿后小步修改，验证不破坏其他章节。"
tags: [Refactor, Novel]
domain: novel
category: novel.baseline
priority: P0
version: 1.0.0
when_to_use: "审稿后返修、小改、章节修改时"
status: stable
---

# Novel Safe Revision — 安全返修

审稿后返修章节时加载。对应 Code 域 refactor-safely。

## 返修原则

- 单次小改，不大幅重写
- 先读 MEMORY.md 再改
- 改一点审一点
- 保留原版本记录

## 返修流程

明确范围 → 识别风险 → 小步修改 → simplify 自查 → 验证 → 更新 MEMORY.md

## 常见类型

| 类型 | 操作 |
|------|------|
| 角色矛盾 | 对照 voice-profile 修改 |
| 伏笔遗漏 | 追加或调整伏笔状态 |
| 节奏问题 | 调整章节密度 |
