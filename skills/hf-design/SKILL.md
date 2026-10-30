---
name: hf-design
description: "设计或重构模块接口时，使用 Matt Pocock 的深模块方法减少调用者负担并改善可测试性。"
---

# 模块设计

读取 upstream/SKILL.md；准备合并或调整模块时按需读 upstream/DEEPENING.md。以真实调用者需要、接口承诺、错误行为和维护局部性比较方案。

保持项目现有业务词汇，不为统一上游术语批量重命名。Ponytail 优先：不为单一实现新增端口、适配器或抽象。upstream/DESIGN-IT-TWICE.md 是可选的多方案研究，只有用户明确要求或项目规则要求独立方案时才启用，普通设计不自动派发多个 Agent。
