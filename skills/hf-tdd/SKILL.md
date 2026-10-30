---
name: hf-tdd
description: "用户要求 TDD，或非平凡逻辑需要回归测试时，按 Matt Pocock 方法测试公开行为并逐步红绿验证。"
---

# 有效测试

读取 upstream/SKILL.md；测试质量和隔离方式分别按需读 upstream/tests.md、upstream/mocking.md。先确定公开接口和可观察结果，一条失败用例 → 最小实现 → 验证，再处理下一种行为。

本地适配：当前实现/修复授权已涵盖受影响公开接口的常规验证时，说明测试范围并继续，不为 upstream 的 seam 确认再次暂停。只有接口行为存在实质歧义才提问。沿用测试框架，不强制覆盖率、专门测试提交或全库 TDD；文案等可直接检查的简单改动按项目规则处理。不要把 Superpowers/ECC 的另一套 TDD 流程串联执行。
