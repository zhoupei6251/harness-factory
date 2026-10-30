---
name: brainstorming
description: Clarify ambiguous coding requirements and compare meaningful design choices before a substantial change. Use on demand, not for every edit.
version: 1.2.0
when_to_use: 调用 brainstorming 时
status: peripheral
tags:
- 头脑风暴
- 设计
domain: shared
category: shared.planning
---

# Brainstorming

把影响实现的未知条件变成明确决定。适用于需求不清、架构取舍明显或变更风险较高的编码任务；目标已明确的小修复、配置调整和页面修改直接执行。

1. 先读相关代码、项目状态与现有约定，使用代码图谱定位调用和影响；图谱不可用或覆盖不足时按 Harness 规则声明并读取源码取证。
2. 明确用户、触发条件、期望行为、约束与通过标准。能从仓库或会话推断的内容自行确认；只问会实质影响结果的问题，不预设客户类型或业务场景。
3. 有真实取舍时提出两三个可行方案，说明成本与风险并给出建议。没有取舍就采用复用现有代码的最小正确方案。
4. 普通任务用几句话说明决定；跨模块或高风险变更才按项目约定保存一份简短设计，可与计划和验证合并，避免复制代码和已有文档。
5. 用户已要求实现或已批准方案时，继续实施，不重复请求开始许可。用户只要求讨论、设计或计划时，交付对应产物后等待下一步。

保留输入校验、错误处理、安全和必要验证。仅在缺失信息阻止正确实现、出现超出授权的操作或用户明确要求审批时暂停；不强制 worktree、额外技能或完整产品流程。
