---
name: harness-health
description: 运行仓库现有门禁并汇总健康状态 — 不另建一套检测，不维护第二份判据
tags:
- Skill
- Observability
- Meta
version: 1.2.0
when_to_use: 用户说 /health、健康检查、检查系统状态，或发版前要一份门禁汇总时
status: peripheral
domain: shared
category: workflow
---
# Harness Health Check Skill

## 激活条件

- 用户说 "/health"、"健康检查"、"检查系统状态"
- 发版前质量门禁
- 修改 `core/`、`scripts/bootstrap.ts`、`scripts/bootstrap-contract.ts`、`package.json` 之后

## 工作流

在仓库根依次运行，**保留每条的退出码**：

| # | 命令 | 检查什么 |
|---|---|---|
| 1 | `npm run validate` | schema JSON、每个 skill 的 SKILL.md、evidence 指针、运行时目录是否被 track |
| 2 | `npm run structure:audit` | 文档声明与文件系统是否一致（core / platforms / routes / verticals / INDEX 计数 / forbidden homes） |
| 3 | `npm run check-bootstrap -- --require-generated` | 生成物是否等于新 bootstrap 结果；缺失也算失败（与 pre-commit 同口径） |
| 4 | `npm run typecheck` | TS 7 类型检查 |
| 5 | `npm run typecheck:web` | Vue 模板类型检查 |
| 6 | `npm run test:render` | Python 渲染引擎自测（251 条，stdlib-only 离线） |
| 7 | `npm run doctor` | 外部工具：Node 版本、codebase-memory-mcp、其客户端接线、ponytail |
| 8 | `npm run stats` | 只作上下文：实时计数 + git 状态 + 运行时目录大小 |

`npm test` 覆盖 1–6 加集成测试与 web 构建，但不含 `doctor` / `stats`；它内部的 check-bootstrap 用默认模式（缺产物 `[skip]`），严格口径仍需单跑第 3 条。CI（`.github/workflows/verify.yml`）在 push main / PR 上跑同一份 `npm test`（Node 20.9.0 + Python 3.12）；想跑全链时本地用 `npm test`，再单跑 `doctor`，**不要**在技能里重抄一份命令清单。

## 判读规则

- 任一命令退出码非 0 ⇒ 不健康。原样贴出 `[FAIL]` / `[MISS]` 行，不要只写"失败"。
- `[skip]` 不是绿。`check-bootstrap` 默认会把缺失生成物标成 `[skip]`；健康检查按 pre-commit 口径用 `--require-generated`，缺失即红。
- `doctor` 失败 = 代码域降级（无图谱证据 / 无 ponytail 阶梯），不是业务代码失败。按 `references/tooling.md` 修复；在修好前声明降级。
- `stats` 里的 git 状态包含未提交改动，不代表不健康；它只回答"工作区现在有什么"。

## 输出格式

```markdown
## Harness Health

| 检查 | 结果 |
|---|---|
| validate | ok |
| structure:audit | ok |
| check-bootstrap (require-generated) | ok — 17 artifacts + MEMORY.md |
| typecheck | ok |
| typecheck:web | ok |
| test:render | ok — 251/251 |
| doctor | FAIL — codebase-memory-mcp 未接线 |
| stats | 参考：N tracked files，工作区 M modified |

**Status**: DEGRADED（doctor）
```

## 修复映射

| 失败项 | 动作 |
|---|---|
| validate | 按 `[FAIL]` 行修：schema JSON 格式 / 缺失 SKILL.md / evidence 指针未入库 / runtime 目录被 track |
| structure:audit | 文档声明与文件系统对齐；不要只改数字不改文件（或反之） |
| check-bootstrap | `npm run bootstrap` 重新生成；**不要直接编辑生成物**（`AGENTS.md` / `CLAUDE.md` / `.qoder/rules/*` 等） |
| typecheck / typecheck:web | 修类型错误；`<script setup>` 当前不被 vue-tsc 检查是已知依赖限制，不是本闸的信号 |
| test:render | 读第一个 `FAIL` / `ERROR` 行；找不到 Python 解释器时先装 3.11+（自测导入 `tomllib`） |
| doctor | 按输出里的 fix 行；完整安装路径见 `references/tooling.md` |
| 集成测试 | 读失败断言；先判断是生成器回归还是测试假设过期 |

## 不做什么

- 不发明仓库里不存在的检查项（旧版提到的 instinct 质量、guardrail 配置、agent frontmatter 覆盖率都不属于本仓库）。
- 不为了"全绿"跳过 `doctor`、重跑 bootstrap 掩盖漂移，或把 `[skip]` 说成通过。
- 不维护第二套命令实现；门禁逻辑只活在 `scripts/` 与 `package.json`。
