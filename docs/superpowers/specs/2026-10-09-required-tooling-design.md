# 代码域工具强制化设计（ponytail + codebase-memory-mcp · 四端一致）

> 日期：2026-10-09 ｜ 状态：设计已批准，待实施计划
> 方案：B（强制条款 + 绑定 R1/R2/R8 + NEVER.md 禁止项 + 四端接入），方案 A（只改措辞）已被否
> 上游：[DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail)（MIT）、[DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp)

## 1. 目标与验收口径

- **诉求**：在本仓库开发时**每次**都用 ponytail 与 codebase-memory-mcp，且 Trae / Claude Code / Codex / WorkBuddy 四端一致生效。
- **成功标准**：
  1. 四个原生入口（`CLAUDE.md` / `AGENTS.md` / `.trae/rules/project_rules.md` / `.codebuddy/rules/project_rules.md`）都含：required 条款、文案豁免、降级语义、本端安装与验证命令；
  2. `npm run test`（validate + typecheck + bootstrap.test）全绿；
  3. 治理文本（ENTRY / README / tooling / runbooks）不再把两工具描述为 "recommended"；
  4. `routes/code/MEMORY.md` 的 Key decisions 有本次决策记录。
- **不变量**：
  - 不新增行为规则条目——只给既有 R1 / R2 / R8 装上执行工具（符合 R8「如无必要勿增实体」）；
  - 两工具不进 `package.json` 依赖、不被 bootstrap 渲染——它们是每台机器的环境配置，仓库只提供配置片段与文档；
  - 不改 skills 库、不做 doctor 自动校验（用户明确排除）。

## 2. 范围边界

| 范围 | 处置 |
|------|------|
| 改 TS / 脚本 / 测试 / 配置 / 规则文件 | **两工具强制** |
| 纯文案产出（novel / news 稿件等） | **豁免**，交由 route 自身规则（humanizer / fact-check 等）治理 |
| 工具未装 / 未接通 | **声明降级**：改用等效手段（Read / Grep），并在回复中说明降级原因；禁止默默跳过或假装已用 |

豁免理由：ponytail 的检查项与 benchmark 全部围绕代码（"读改动触及的代码"、"有分支/循环/解析/资金/安全逻辑才留测试"），对纯文案会退化成"少写点"，甚至把该写长的稿件压短；codebase-memory-mcp 是代码图谱，对文案无对象。

## 3. 组件设计

### 3.1 组件 ①：根 `ENTRY.md` Tooling 小节整节替换

现状为 `## Tooling (recommended, per-machine install)`，替换为：

```markdown
## Tooling (required — 代码域强制)

> 两工具是代码域开发的**执行方式**，不是可选附件。
> 适用范围：改 TS / 脚本 / 测试 / 配置 / 规则文件。豁免：纯文案产出（novel / news 稿件）。
> 降级语义：工具未装或未接通时，改用等效手段（Read / Grep），并**在回复中声明降级原因**；禁止默默跳过或假装已用。

| Tool | 绑定规则 | 必须这样做 | Install |
|------|---------|-----------|---------|
| codebase-memory-mcp | R1 | 改代码前用 `analyze-impact` / `get-callers` / `query-symbol` 拿图谱证据 | 根 `.mcp.json` 或 `references/tooling.md` |
| ponytail | R2 / R8 | 生成前走七级决策阶梯（不写→复用→库→原生→依赖→一行→最小实现） | `references/tooling.md` |
```

关键：绑定列把两工具挂到既有 R1（Read before write）/ R2（Keep it simple）/ R8（No over-engineering）上，而不是新立规则。

### 3.2 组件 ②：`core/NEVER.md` 加两行禁止项

沿用现有「Forbidden | Why | Alternative」三列短表风格：

| Forbidden | Why | Alternative |
|-----------|-----|-------------|
| change code without evidence | guessing | query graph first; if MCP down, degrade and say so |
| skip the lazy ladder | over-build | ponytail ladder first; if unavailable, say so |

NEVER.md 是 mandatory 加载，这两行是「每次都用」的真正抓手。

### 3.3 组件 ③：四端接入（`platforms/<端>/rules/ENTRY.md` 各加 ≤10 行）

| 端 | ponytail | codebase-memory-mcp | 验证 |
|---|---|---|---|
| Claude Code | `/plugin marketplace add DietrichGebert/ponytail` → `/plugin install ponytail@ponytail` | 根 `.mcp.json` 打开即提示启用 | `/ponytail-help` + `list_projects` |
| Codex | `codex plugin marketplace add` / `codex plugin add` → `/hooks` 信任两个 lifecycle hook | `mcp-config/codebase-memory.codex.toml` 并入 `~/.codex/config.toml` | 同上 |
| Trae | 无插件系统 → 装为 skill（上游 `skills/ponytail/SKILL.md`）或复制上游 `AGENTS.md` 精简版进项目规则 | 设置 → MCP 粘贴 `mcp-config/codebase-memory.json` | 规则版：新会话询问阶梯当前档位有回答；skill 版：`/ponytail-help` 有输出 |
| WorkBuddy | 同 Trae | 同 Trae | 同 Trae |

**篇幅控制**：安装完整步骤留在 `references/tooling.md`，各端 delta 只放「本端 3 条命令 + 验证 + 降级声明格式」。这些 delta 会被 bootstrap 拼进每次会话加载的原生入口，写长了是常驻上下文负担。

**如实声明**：Trae / WorkBuddy 上 ponytail 只有规则文本约束、无 hook 强制。这属于能力差异，**不算「降级」**，降级只指工具缺失或未接通。

### 3.4 组件 ④：`core/runbooks.md` 与 `references/tooling.md` 措辞同步

- `core/runbooks.md`：小节标题 `Install recommended tooling` → `Install required tooling (code domain)`；第 3 步验证补降级声明格式；
- `references/tooling.md`：首段 `本仓库推荐所有使用者安装` → required 措辞；Trae / WorkBuddy 的 ponytail 装法按上游官方修正为「装 skill 或复制 `AGENTS.md`」；新增「降级语义」小节；
- `README.md` L83：`Two recommended external tools` → required 措辞。

## 4. 降级声明格式

工具缺失 / 未接通时，在当次回复中显式声明，格式：

```
[codebase-memory-mcp 不可用，已降级] 原因：<未装 / MCP 未连通 / 索引缺失>；替代手段：<Read / Grep 手工取证>。
[ponytail 不可用，已降级] 原因：<未装 / 插件未启用>；替代手段：<按 R2/R8 手工走决策阶梯>。
```

## 5. 改动清单

| # | 文件 | 改什么 |
|---|------|--------|
| 1 | `ENTRY.md` | Tooling 小节整节替换为 §3.1 |
| 2 | `core/NEVER.md` | 加 §3.2 两行 |
| 3 | `core/runbooks.md` | 标题与验证步骤措辞同步（§3.4） |
| 4 | `platforms/{claude,codex,trae,workbuddy}/rules/ENTRY.md` | 各加 §3.3 一节 |
| 5 | `references/tooling.md` | 措辞 + Trae/WorkBuddy 装法修正 + 降级语义小节 |
| 6 | `README.md` | L83 措辞 |
| 7 | `routes/code/MEMORY.md` | Key decisions 记一条本次约定 |
| 8 | 执行 `npm run bootstrap -- --platform all --route code` | 重新渲染四个原生入口 |

**冲突提示（R7）**：根目录 `MEMORY.md` 是 bootstrap 的投影产物（`projectRoute` 把 `routes/code/MEMORY.md` 复制为 `./MEMORY.md`），写进根 `MEMORY.md` 会在下次 bootstrap 被冲掉。记忆落在 **`routes/code/MEMORY.md`**（源），根 `MEMORY.md` 由 bootstrap 自动更新。

## 6. 非目标

- `scripts/doctor.ts` 的校验逻辑**保持不变**（执行时更正：它早已存在，且是 `npm run bootstrap` 的硬门禁 `doctor && bootstrap`，并非「留作后续」）。本轮只按它打印的开方把本机 `~/.codex/config.toml` 补上 `mcp_servers.codebase_memory`（追加 `mcp-config/codebase-memory.codex.toml`），使门禁通过；不改 doctor 代码。
  - **后续更正（同日，Qoder 适配）**：上面这条「不改 doctor 代码」已被推翻，原因是门禁形态本身有缺陷——`codexWired && claudeWired` 是硬「且」，纯 Qoder / 纯 Claude 机器会被 `npm run bootstrap` 挡在门外。现改为**跨端「或」**（codex config.toml / qoder settings.json / 项目 `.mcp.json` 任一命中即通过），并把「客户端已配」与「仓库片段存在」分开打印，避免项目 `.mcp.json` 恒真导致的假通过。ponytail 检查同步加入 `~/.qoder/skills/` 路径。改动经正/反两分支实测（qoder-only → 通过；无任何接线且隐藏 `.mcp.json` → `[MISS]` + exit 1）。
- 两工具进 `package.json` 依赖或被 bootstrap 渲染；
- 改动 skills 库（`skills/query-symbol` 等 10 个依赖 codebase-memory-mcp 的 skill 保持原样）；
- 给 Trae / WorkBuddy 做 hook 级强制（无插件系统，做不到）。

## 7. 风险

| 风险 | 处置 |
|------|------|
| 强制条款被当成附录跳过 | 条款写进 Tooling 小节 + NEVER.md 禁止项双写；NEVER.md 是 mandatory 加载 |
| 各端 delta 过长撑大常驻上下文 | 每端 ≤10 行，完整步骤只留 `references/tooling.md` |
| 上游工具更名 / 装法变更 | `references/tooling.md` 记录上游链接与验证命令，装法失效时按 §4 声明降级 |
