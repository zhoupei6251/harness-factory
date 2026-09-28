# tooling.md — 推荐外部工具：ponytail + codebase-memory-mcp

> 本仓库推荐所有使用者安装以下两个工具。两者均为**本地运行、免费开源**，无需任何 API Key，
> 符合仓库安全条款（禁止真实密码 / Key / 私钥入库）。
> 安装状态属于**每台机器一次性配置**，不随 `npm run bootstrap` 渲染。

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
      "args": ["-y", "codebase-memory-mcp", "--ui=true"],
      "env": { "NODE_ENV": "production" }
    }
  }
}
```

- **Claude Code**：在本仓库目录打开会话时自动提示启用（项目级 MCP），确认即可。
- 需要本机有 Node（`engines: >=20.9.0` 与本仓库一致）。
- npm 包已验证存在：`codebase-memory-mcp`（安装时取 latest）。

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
| Codex | `~/.codex/config.toml` 增加 `[mcp_servers.codebase_memory]`，`command = "npx"`、`args = ["-y", "codebase-memory-mcp", "--ui=true"]`；或方式 B 指向二进制 |
| Trae | 设置 → MCP → 添加服务器，粘贴 `mcp-config/codebase-memory.json` 内容 |
| WorkBuddy | 同 Trae，手动添加 MCP server（npx 或二进制路径均可） |

### 验证与首次使用

1. 让 Agent 调用 `list_projects` —— 能返回即 MCP 已连通。
2. 对目标仓库执行一次 `index_repository`（大仓库首次索引需要几分钟）。
3. 之后即可使用 `search_graph` / `trace_path` / `query_graph` / `get_architecture` / `detect_changes` 等 17 个工具，
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
| **Trae / WorkBuddy**（无插件系统） | 指令文件方式：clone 上游仓库，把其中的规则文件（如 `AGENTS.md` / `.cursor/rules/` 下的 ponytail 规则）复制到平台的项目规则目录，作为纯指令生效（无 hook 强制，靠规则文本约束） |

> Claude Code / Codex 的 hook 强制检查需要本机 PATH 上有 Node。

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
- **R2 / R8 / NEVER.md**：ponytail 把「先问能不能不写」从文档约定变成生成前的强制检查，二者同向。
- **最小改动原则**：两工具都不进 `package.json` 依赖、不被 bootstrap 渲染——它们是每台机器的环境配置，仓库只提供配置片段（`.mcp.json`、`mcp-config/`）与本文档。
