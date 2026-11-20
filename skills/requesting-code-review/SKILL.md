---
name: requesting-code-review
description: Request an independent review of substantial or high-risk code changes, or when the user asks for review.
version: 1.0.0
when_to_use: 调用 requesting-code-review 时
status: peripheral
tags:
- review
- workflow
domain: code
category: code.review
---

# Requesting Code Review

跨模块、大范围或高风险变更完成后，请独立审查者检查整体改动；用户明确要求审查时也使用。普通小改动检查 diff 并运行相关验证，无需为每个任务派发审查 Agent。

## 提供给审查者

- 用户需求、通过标准和必要的设计决定。
- 明确的基准提交与当前提交，或尚未提交的 diff 和文件范围；不要默认 `HEAD~1` 就是本次基准。
- 代码图谱证据、真实调用路径与覆盖限制；当前源码和实际 diff 是最终依据。
- 已执行检查、结果和未验证项。

使用宿主已有的独立 Agent 或项目审查渠道，不依赖特定插件或外部技能名，不要求额外 worktree。审查者只读，不提交、不推送。无法取得独立审查时如实报告限制，不能把实现者自查称为独立审查。

## 审查与返修

先核对需求是否完整，再查正确性、兼容性、边界校验、错误处理、安全和必要测试。按 [two-stage-review](../two-stage-review/SKILL.md) 的两个维度一次完成即可。

报告可复现的问题及具体文件位置、影响和优先级；没有发现问题就明确说明，同时保留验证限制。修复重大问题后复查相关改动，只有新修改或未解决疑点才扩大验证。意见有误时用源码或测试说明，不为风格偏好扩大范围。

简单任务将结论写入交付说明；大范围或高风险变更按项目约定保存一份审查记录，避免重复报告。
