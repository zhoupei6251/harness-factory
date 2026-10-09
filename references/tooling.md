# tooling.md — 代码域强制工具：ponytail + codebase-memory-mcp

> 代码域开发（改 TS / 脚本 / 测试 / 配置 / 规则文件）**强制**使用以下两个工具；纯文案产出（novel / news 稿件）豁免。
> 两者均为**本地运行、免费开源**，无需任何 API Key，符合仓库安全条款（禁止真实密码 / Key / 私钥入库）。
> 安装状态属于**每台机器一次性配置**，不随 `npm run bootstrap` 渲染。
> 缺失或未接通时**声明降级**：改用等效手段（Read / Grep）并在回复中说明原因，禁止默默跳过。详见文末「降级语义」。

## 一览

| 工具 | 是什么 | 与本仓库的关系 | 上游 |
|------|--------|----------------|------|
| **codebase-memory-mcp** | 代码知识图谱 MCP 服务：tree-sitter（162 语言）+ Hybrid LSP，持久化 SQLite 图谱 | 10 个 active skills 依赖它（`query-symbol`、`get-callers`、`get-callees`、`analyze-impact`、`query-knowledge-graph`、`index-project`、`understand-project`、`analyze-architecture`、`lsp-query`、`ripgrep-search`）；为 R1「Read before write」提供改动前证据 | [DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) |
| **ponytail** | 「最懒资深工程师」生成前检查插件：7 级决策阶梯（不写 → 复用 → 配置 → 一行 → 最小实现 → 完整实现），官方数据约省 54% 代码量 | 与 `core/NEVER.md`、R2「Keep it simple」、R8「No over-engineering」互补：NEVER.md 是文档约束，ponytail 是生成前强制检查 | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail)（MIT） |

---

## codebase-memory-mcp

### 安装方式 A：零安装（npx，本仓库已配置）

仓库根 **`.mcp.json`** 已提交以下配置（与 `mcp-config/codebase-memory.json` 同源）：

```json
{
  "mcpServers": {
    "codebase_memory": {
      "command": "npx",
      "args": ["-y", "codebase-memory-mcp"],
      "env": { "NODE_ENV": "production" }
    }
  }
}
```

- **Claude Code**：在本仓库目录打开会话时自动提示启用（项目级 MCP），确认即可。
- 需要本机有 Node（`engines: >=20.9.0` 与本仓库一致）。
- npm 包已验证存在：`codebase-memory-mcp`（安装时取 latest）。
- ⚠️ **不要加 `--ui=true`**。npm 分发的二进制是「built without the embedded UI」，带着它只会多打一行
  `the HTTP server will not start` 警告，UI 并不存在（实测）。要内嵌 UI 得用
  `codebase-memory-mcp-ui` release 资产或自行 `make -f Makefile.cbm cbm-with-ui`。
  本仓库的 `.mcp.json` / `mcp-config/*` 早期都带过这个 flag，已全部去掉。

### 安装方式 B：静态二进制（官方推荐，零依赖、无需 Node）

单文件二进制，图谱缓存在 `~/.cache/codebase-memory-mcp/`。

**Windows（PowerShell）**：

```powershell
Invoke-WebRequest -Uri https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.ps1 -OutFile install.ps1
Unblock-File .\install.ps1
.\install.ps1
```

**macOS / Linux**：

```bash
curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash
```

安装器会自动探测并配置本机已装的 AI 客户端（官方称支持 45 种）。手动配置 MCP 时指向二进制即可：

```json
{ "mcpServers": { "codebase-memory-mcp": { "command": "/path/to/codebase-memory-mcp", "args": [] } } }
```

### 各平台接入

| 平台 | 接入方式 |
|------|----------|
| Claude Code | 仓库根 `.mcp.json`（已提交，首次打开提示启用）；或 `claude mcp add` 全局注册 |
| Codex | `~/.codex/config.toml` 增加 `[mcp_servers.codebase_memory]`，`command = "npx"`、`args = ["-y", "codebase-memory-mcp"]`；或方式 B 指向二进制 |
| Trae | 设置 → MCP → 添加服务器，粘贴 `mcp-config/codebase-memory.json` 内容 |
| WorkBuddy | 同 Trae，手动添加 MCP server（npx 或二进制路径均可） |
| Qoder | ⚠️ 仓库根 `.mcp.json` **不读**（实测：声明了 `codebase_memory`，会话内 MCP 列表无此服务）。改写 `~/.qoder-cn/settings.json` 的顶层 `mcpServers`（user 作用域；另有 project `.qoder/settings.json` / local `.qoder/settings.local.json`）。⚠️ Windows 上 `command` 必须是 `npx.cmd`——片段里的 `npx` 在 `spawn(shell:false)` 下直接 ENOENT，与 `scripts/doctor.ts:42` 同因。用内置 `mcp-config` skill 写，改完 `/mcp reload` |

### 验证与首次使用

1. 让 Agent 调用 `list_projects` —— 能返回即 MCP 已连通。
   ⚠️ 返回的 `name` 是**路径 slug**（如 `D-work-xinyue-aigc_platfrom_back-harness-factory`），
   不是目录名。凡需要 `project` 参数的工具（`index_status` / `search_graph` / `detect_changes` …）
   都传这个 slug；传目录名 `harness-factory` 会得到 `project not found or not indexed`（实测）。
2. 对目标仓库执行一次 `index_repository`（大仓库首次索引需要几分钟）。
3. 之后即可使用 `search_graph` / `trace_path` / `query_graph` / `get_architecture` / `detect_changes` 等工具
   （本机 0.9.0 实测暴露 14 个，上游文档写 17 —— 以 `mcp_list` 当次结果为准），
   入口见本仓库 skills（如 `skills/query-symbol/SKILL.md`）。

### 团队共享图谱（可选）

- 索引产物可导出为 `.codebase-memory/graph.db.zst` 快照并**提交进目标项目仓库**，队友克隆后免于全量重建索引。
- ⚠️ **不要**让每次自动刷新都提交该快照——上游 README 记载有团队因此把 git 历史撑到 ~6GB。只在里程碑处手动提交。
- 相关环境变量：`CBM_CACHE_DIR`（图谱缓存目录）、`CBM_ALLOWED_ROOT`（限制可索引的根目录）。

---

## ponytail

### 各平台安装

| 平台 | 安装方式 |
|------|----------|
| **Claude Code** | 会话内依次执行（两次独立确认）：<br>`/plugin marketplace add DietrichGebert/ponytail`<br>`/plugin install ponytail@ponytail` |
| **Codex** | `codex plugin marketplace add DietrichGebert/ponytail`<br>`codex plugin add ponytail@ponytail` |
| **Cursor** | `git clone https://github.com/DietrichGebert/ponytail` 后 `node ponytail/scripts/cursor-hooks.js install` |
| **Gemini CLI** | `gemini extensions install https://github.com/DietrichGebert/ponytail` |
| **Trae / WorkBuddy**（无插件系统） | 按上游官方「Any other agent」路径二选一：① 装为 skill（上游 `skills/ponytail/SKILL.md`）；② 复制上游 `AGENTS.md` 精简版进项目规则。纯指令生效、无 hook 强制——这是平台能力差异，不算「降级」 |
| **Qoder**（无插件市场） | 同「装为 skill」，本机复用 Codex 那份：`~/.codex/skills/ponytail` junction 到 `~/.qoder/skills/ponytail`（纯指令型 SKILL.md，平台无关）。代价：`/ponytail lite\|full\|ultra`、`/ponytail-help` 等**命令级**能力不可用，只能会话内用指令切强度；新会话才会被 discover。`npm run doctor` 已把该路径计入检查 |

> Claude Code / Codex 的 hook 强制检查需要本机 PATH 上有 Node。

### MCP 注册位置（各端不同，别抄错）

| 端 | 用户级 | 项目级 | 备注 |
|----|--------|--------|------|
| Claude Code | `~/.claude.json` | 仓库根 `.mcp.json` | 本项目走项目级，已提交 |
| Codex | `~/.codex/config.toml` 的 `[mcp_servers.*]` | 不读项目 `.mcp.json` | 片段见 `mcp-config/codebase-memory.codex.toml` |
| Qoder | `~/.qoder-cn/settings.json` 顶层 `mcpServers` | `.qoder/settings.json`（入库）/ `.qoder/settings.local.json`（gitignored） | ⚠️ Windows 上 `command` 用 `npx.cmd`；改完需 `/mcp reload`（CLI 侧命令，Agent 无法自行触发） |

> 本机实测：`codebase_memory` 已注册在 Qoder **user 作用域**，`command = "npx.cmd"`，**已连通**
> （会话内 `mcp_list` 可见 14 个工具，`list_projects` 返回本仓库及其索引状态）。
> 裸 `npx` 在 `spawn(shell:false)` 下 `ENOENT`，故仓库片段虽写着 `npx`，抄到 Windows 端要改这一个字段。
> ⚠️ Agent 无法自行触发 `/mcp reload`，配置改动要等新会话或由用户手动 reload。

### 配置

| 项 | 说明 |
|----|------|
| `PONYTAIL_DEFAULT_MODE` | 环境变量：`lite` / `full` / `ultra` / `off`，默认 `full` |
| `~/.config/ponytail/config.json` | `{ "defaultMode": "full" }`，与环境变量二选一 |
| `PONYTAIL_SUBAGENT_MATCHER` | 正则，控制哪些 subagent 也走 ponytail 检查 |

### 命令

`/ponytail`（开关）、`/ponytail-review`（审查本次生成）、`/ponytail-audit`、`/ponytail-debt`、`/ponytail-gain`（节省统计）、`/ponytail-help`。

### 验证

安装后新开会话，执行 `/ponytail-help` 有输出即成功；生成代码时观察是否先走决策阶梯。

---

## 与本仓库治理的关系

- **R1（Read before write）**：改动前用 `analyze-impact` / `get-callers` 拿图谱证据，而不是凭感觉。
- **R2 / R8 / NEVER.md**：ponytail 把「先问能不能不写」从文档约定变成生成前的强制检查，二者同向；`core/NEVER.md` 另有两条禁止项（无证据不改代码 / 不跳生成阶梯）。
- **强制范围**：改 TS / 脚本 / 测试 / 配置 / 规则文件必用两工具；纯文案产出（novel / news 稿件）豁免，交由 route 自身规则治理。
- **最小改动原则**：两工具都不进 `package.json` 依赖、不被 bootstrap 渲染——它们是每台机器的环境配置，仓库只提供配置片段（`.mcp.json`、`mcp-config/`）与本文档。

## 降级语义

工具未装或未接通时，**声明降级**，不要默默跳过、不要假装已用：

```
[codebase-memory-mcp 不可用，已降级] 原因：<未装 / MCP 未连通 / 索引缺失>；替代手段：<Read / Grep 手工取证>。
[ponytail 不可用，已降级] 原因：<未装 / 插件未启用>；替代手段：<按 R2/R8 手工走决策阶梯>。
```

降级只覆盖**工具缺失 / 未接通**。Trae / WorkBuddy / Qoder 上 ponytail 无 hook 强制（纯指令生效）属于平台能力差异，照常用，不算降级。
