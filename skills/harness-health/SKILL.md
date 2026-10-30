---
name: harness-health
description: 显式检查 Harness 健康状态，复用 package.json 门禁，避免重复运行和无关诊断。
tags: [Skill, Observability, Meta]
version: 2.0.0
when_to_use: 用户要求健康检查，或发布 Harness 前需要整体门禁结果时
status: peripheral
domain: code
category: workflow
---

# Harness Health

1. 读取当前 `package.json`，以其中现有命令为唯一来源。
2. 完整健康检查运行一次 `npm test`；需要核对已生成的本地文件时，再运行 `npm run check-bootstrap -- --require-generated`。同一批修改已有新鲜成功结果则复用，不重跑相同检查。
3. 只有用户要求环境诊断或工具不可用时才运行 `npm run doctor`；它可能访问网络，文件存在也不能证明本会话 MCP 或插件已启用。
4. `npm run stats` 只提供计数、Git 状态和运行时大小，不作为通过判据。

普通代码修改按影响范围运行相关检查，不自动触发完整健康检查。遵守目标项目的执行限制，禁止自动 Maven 的项目只列命令和未验证项。

报告实际执行的命令、退出码和失败断言；`[skip]`、未运行和工具降级分别说明。修复失败原因后只重跑受影响检查。不得修改或跳过门禁来制造成功结果。
