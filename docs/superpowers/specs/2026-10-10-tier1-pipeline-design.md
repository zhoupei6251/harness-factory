# Tier 1 分级流水线 + 证据段模板 — 设计稿

> 日期：2026-10-10 ｜ 状态：设计已批准，落地在 `CLAUDE.harness.md` §2/§3
> 关联：[2026-10-10-harness-isolation-design.md](2026-10-10-harness-isolation-design.md)（隔离 + 模板化）、[2026-10-09-required-tooling-design.md](2026-10-09-required-tooling-design.md)（双工具强制化）

## 1. 问题

Harness 流程只有两档：「小改动」（< 50 行、单文件）与「全套仪式」（spec → 暂停 → plan → 暂停 → 多 Agent 编排 → 集体测试 → 集体审查）。中间 80% 的中等改动被迫走全套，浪费回合数与墙钟时间；返工也多发于「按全套写完才发现本可一句话搞定」的反差。

工具层面（[2026-10-09 双工具强制化](2026-10-09-required-tooling-design.md)）已把 R1（改前查图谱证据）写进 NEVER.md，但**没有可检验的落点**——会话里查不查图谱，事后无法判断。

## 2. 目标

- **诉求 1（速度）**：中等改动（≤ 200 行 / ≤ 3 文件 / 不碰公共 API）→ 1 份合并文档 + 1 次暂停 + 主 Agent 直做。
- **诉求 2（准确）**：R1 证据环有**可检验产物**——合并文档的「证据」段是机器可读的结构化记录。
- **不变量**：
  - Tier 2+ 全套流程保留（真的大改动仍走集体测试+审查）；
  - 五端投影机制不变；
  - 双工具强制条款不变（ponytail + codebase-memory-mcp）；
  - 「完成」判据仍按层级区分（Tier 0/1/2+）。

## 3. Tier 判定标准

任一不满足走 Tier 2+：

- 改动 ≤ 200 行
- 改动 ≤ 3 个文件
- 不碰公共 API、不改数据库 schema、不改构建脚本
- 不涉及多模块联动、不引入新依赖

写合并文档时如发现触发条件失效，**立即停止并告知用户升 Tier 2**；已写文档作为 Tier 2 的 spec 输入。

## 4. Tier 1 流程（与 Tier 2+ 对照）

| 阶段 | Tier 2+ | Tier 1 |
|---|---|---|
| 文档 | spec + plan + 验证分散 3 份 | **1 份合并文档** |
| 暂停 | spec 后 + plan 后两次 | **合并文档后 1 次** |
| 实现 | Leader 派 WU 给子 Agent（worktree） | **主 Agent 直做**（不开 worktree） |
| 验证 | collective-test + code-review | 内联断言 + verification-lite |
| 集成 | 集体审查落盘 `*-code-review.md` | 写 `verifications/*-verification-lite.md` |

合并文档的章节顺序固定：

1. 任务背景（1-2 段）
2. 方案概述（关键决策、边界）
3. 实施步骤（按文件列出改动）
4. **证据（Evidence）**（见 §5 模板）
5. 验证断言（内联 checklist）
6. 风险与回滚

## 5. 证据段模板

落地在 `CLAUDE.harness.md` §3。要点：

- **改动触及的代码**（from `search_graph`）：至少 1 行；行数 ≥ 50 的函数同时列测试覆盖
- **影响面**（from `trace_path`）：inbound callers / outbound callees / 跨服务链路
- **验证断言**：可机器核的 checklist（行号、新分支测试、callers 兼容、构建命令——仅列不跑）
- **不可验证的盲点**：主动声明（比假装全绿更值得信任）

工具降级语义：MCP 未装/未接通 → 改用 `Read` / `Grep` 手工取证，**回复中声明降级原因**（继承 [2026-10-09-required-tooling-design.md](2026-10-09-required-tooling-design.md) 的口径）。

## 6. 验证：怎么知道 Tier 1 没退化成 Tier 0 的粗糙

- `verifications/*-verification-lite.md` 必含**合并文档链接 + 证据段截图**（图谱节点名 / 行号）
- 若 evidence 段为空 / 仅「N/A」→ 退回到 Tier 2+（判定 Agent 没走证据环）
- 内联断言至少 3 条，缺一条则不通过

## 7. 升级与降级

- **升档（Tier 1 → Tier 2+）**：写合并文档时发现触发条件失效；已写文档作为 spec 输入
- **降档（Tier 2+ → Tier 1）**：写完 spec 后判定触发条件全部满足；合并 spec + plan 为单文档
- **Tier 0 ↔ Tier 1**：≤ 50 行且单文件 → Tier 0；其它 ≤ 200 行 → Tier 1

## 8. 范围边界

| 范围 | 处置 |
|---|---|
| `CLAUDE.harness.md` §2/§3 | **本批次**新增 |
| `docs/superpowers/specs/2026-10-10-tier1-pipeline-design.md` | **本批次**新增（本文） |
| Tier 0/2+ 流程 | 不变（保留在 §5/§6） |
| 五端投影 | 不变 |
| 双工具强制 | 不变 |
| NEVER.md 禁止项 | 不变（Tier 1 仍受「change code without evidence」约束） |

## 9. 非目标

- 「写完合并文档即自动执行实现」——仍需用户一次「确认开始实现」授权（不能去掉最后的护栏）
- 合并文档的 web 渲染器 / 模板引擎
- 证据段的 lint 工具（先靠 Agent 自觉 + 人工 review）

## 10. 风险与回滚

- **风险 1**：Agent 把 Tier 1 当 Tier 0 偷懒，证据段空。缓解：verification-lite 强制含证据段链接。
- **风险 2**：用户授权「开始实现」后 Agent 跑偏到 Tier 2 范围。缓解：合并文档写时已锁定边界；偏离即提示升档。
- **回滚**：CLAUDE.harness.md §2/§3 删掉即恢复 Tier 2 唯一档位。
