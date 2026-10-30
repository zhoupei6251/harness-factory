---
name: writing-plans
description: Create a concise implementation plan for complex coding work or when the user asks for a plan. Routine edits can proceed directly.
version: 1.0.0
when_to_use: 调用 writing-plans 时
status: peripheral
tags:
- plan
- writing
domain: shared
category: shared.planning
---

# Writing Plans

计划帮助完成变更，不给每次编辑增加流程。小范围且目标明确的任务直接处理；跨模块、存在重要依赖或高风险的变更，以及用户明确要求计划时，使用本技能。

先基于代码图谱和当前源码确认影响面，读取相关调用者、测试与配置。按 ponytail 阶梯优先删除、复用和最小实现；图谱不可用或覆盖不足时如实说明手工取证范围。

计划按项目目录约定保存；没有约定时使用 `docs/plans/YYYY-MM-DD-<topic>.md`。一份文档即可包含：

- **目标与通过标准**：用户可观察的结果、必要约束和范围。
- **证据与影响面**：相关符号、调用路径、文件，以及图谱覆盖或验证限制。
- **实现步骤**：按依赖顺序列出要改的文件、行为和必要测试；只列影响实现的细节，不复制整个实现。
- **验证**：优先现有相关检查，列出实际命令、预期结果和项目禁止执行的命令。
- **风险**：兼容性、数据变化与确有必要的恢复方式。

用户已授权实现时，计划后直接继续，遇到新证据再更新步骤。用户只要求计划时，交付计划即可。worktree、并行 Agent、逐步提交与额外技能均按实际需要和项目约定选择，不作为默认前置条件。不要为每个步骤重复生成设计、计划和验证文档。
