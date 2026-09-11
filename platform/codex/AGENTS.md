<!--
platform/codex/AGENTS.md — Codex 入口文件的母版
渲染器将此文件原样复制到 `.harness/rendered/AGENTS.md`，再在项目根写 shim `AGENTS.md` 一行 import。
总预算 ≤240 行（design §6）。
-->

# Harness — Codex Entry

## Identity

- 项目：**{{project}}**
- 路线：**{{route}}**（code | novel | news）
- 默认档：**{{gate}}**（S | M | L）
- 引擎位置：`{{engine_path}}` @ `{{engine_commit}}`
- workspace：`.harness/`（AI 全部产出，gitignored）

开工第一句必须声明：`Harness: {{gate}}`。若需要升降档——看 `core/quality-gates.md`。

## R-1-8 行为规则（不删的版本）

| | 规则 |
|---|---|
| R1 | 改任何文件前先读它。不读就改视为错误。 |
| R2 | 只改完成任务所需的行。顺手重构、改格式、改命名一律禁止。 |
| R3 | 没有证据不得声称完成。说「跑过了」必须同时贴命令与输出。 |
| R4 | 报错先复现再猜。同一处连修两次失败即停手写诊断，禁止第三次盲改。 |
| R5 | 缺信息就问，但先把不依赖答案的部分做完；禁止用提问代替干活。 |
| R6 | 秘密（密码 / API Key / 私钥）不写进任何仓库；用 profile、占位符或部署环境变量。 |
| R7 | 记忆边界：**状态进 `MEMORY`，事实进 `profile.md`，**教训进平台记忆——三不许越界**。 |
| R8 | 一页纸之外的正文（技能、`contracts/`）只在触发时读，读完即用，不向用户复述。 |

R1-R8 在 `core/constitution.md` 有完整背景——本表只是 cheat sheet。

## 本档要求

按 `{{gate}}` 走 `core/quality-gates.md` 的对应档位行为。

```
{{gate.requirements}}
```

## 路线管线（不随档升降）

按 `{{route}}` 走 `routes/<route>/workflow.md` 的 pipeline 段。

```
{{route.pipeline}}
```

**禁止「降档时一起降管线」**」——档位决定文书重量，管线决定流程完整性。

## 项目事实

取自 `.harness/state/profile.md`（人类 seed + AI 增量）：

```
{{project.facts}}
```

## 技能索引（按需加载）

按 `{{route}}` 走 `routes/<route>/workflow.md` 的 skills 段。**正文按需加载**（R8）：

```
{{route.skills}}
```

每个 skill 一行：触发条件 → 路径。

## 可用 agent

- `agents/leader.md`（主线程角色，L 档）—— 不亲自改业务文件
- `agents/explorer.md`（只读摸底）
- `agents/implementer.md`（可写 + 必跑验证）
- `agents/code-reviewer.md`（物理禁写）
- `agents/debugger.md`
- `agents/test-engineer.md`
- `agents/researcher.md`
- `agents/editor.md`
- `agents/fact-checker.md`

详细权限形状与组织分层 → `agents/README.md` + `agents/*.md`。

## 收尾自检（L 档必跑 / M/S 可选）

1. 本档要求的证据落了吗？未落 → 不得称完成。
2. 改过的文件对应的验证命令跑了吗？命令与输出一并写出。
3. 有顺手改的东西吗？有 → 回退，或说明为什么必须留。
4. 状态类事实写回 `.harness/state/MEMORY.md` 了吗？

---

> 渲染产物由 `compiler/render.ts` 生成。改本文件不会传播——改 `core/` `tasks/` `routes/` `agents/` `skills/` 才会。
>
> 多跳加载只在 L 档允许；那时读 `engine/contracts/<spec,plan,closeout>.md`。
>
> Codex 接 hooks：session-start / post-tool-use / stop。详见 `platform/codex/hooks.json`（待填）。