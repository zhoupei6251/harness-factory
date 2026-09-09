# MCP 服务器与用户级 skills 清单

来源：`~/.claude.json`（全局 MCP）、仓库根 `.mcp.json`（项目级 MCP）、`~/.claude/skills/`（2026-08-21 快照）。
**密钥一律不落盘**：`<占位符>` 处换机时手动填写（原值在旧机 `~/.claude.json` 里可查到）。

## 全局 MCP（`~/.claude.json` → `mcpServers`）

### ★ 核心（本项目工作流依赖）

| 名 | 命令 | 配置要点 |
|---|---|---|
| redis | `uvx --from redis-mcp-server@latest redis-mcp-server --url redis://:<REDIS_PASSWORD>@192.168.8.67:6379/0` | 涉及 Redis 一律用它（记忆纪律） |
| context7 | `npx -y @upstash/context7-mcp` | **必装必用**：外部库/依赖/模型 API 的当前版本用法（resolve-library-id → query-docs），写新依赖、版本敏感行为、凭记忆写库 API 时先查；纯搬迁重构不查 |
| mysql | `npx -y @benborla29/mcp-server-mysql` | env：`MYSQL_HOST=192.168.8.67`、`MYSQL_PORT=3306`、`MYSQL_USER=root`、`MYSQL_PASS=<DB_PASSWORD>`、`MYSQL_DB=xywh_dev`；只读，涉及库查询用它 |
| codebase-memory-mcp | `C:/Users/zhoupei/.local/bin/codebase-memory-mcp.exe` | 图谱探索默认入口；需先装 `codebase-memory-mcp` 二进制（.local/bin），换机重装该工具后建索引 |
| github | `npx -y @modelcontextprotocol/server-github` | env：`GITHUB_PERSONAL_ACCESS_TOKEN=<GITHUB_PAT>` |
| firecrawl | `npx -y firecrawl-mcp` | env：`FIRECRAWL_API_KEY=<FIRECRAWL_API_KEY>` |
| longhand | `longhand mcp-server` | 会话历史记忆（需先安装 longhand CLI） |
| memory | `npx -y @modelcontextprotocol/server-memory` | 知识图谱记忆 |
| filesystem | `npx -y @modelcontextprotocol/server-filesystem D:/work/xinyue` | 限定访问 D:/work/xinyue |

### 其他

| 名 | 命令 | 备注 |
|---|---|---|
| parallel-search | type http：`https://search.parallel.ai/mcp` | 联网搜索（免密） |
| node_repl | Codex 内置路径 | Codex 专属，Claude Code 环境可忽略 |

> 注：`ccd_*`、`Claude_Browser`、`scheduled-tasks` 等为桌面应用自带 MCP，随应用安装自动恢复，无需配置。

## 项目级 MCP（仓库根 `.mcp.json`）

```json
{
  "mcpServers": {
    "codebase_memory": {
      "command": "C:/Users/zhoupei/.local/bin/codebase-memory-mcp.exe"
    }
  }
}
```

随仓库走 git，克隆即恢复；注意换机后需把命令路径改成本机实际路径。

## 用户级 skills（`~/.claude/skills/`，约 140 个）

**恢复方式：整体拷贝目录即可**（纯 Markdown 文件，无安装逻辑）。

核心名单（本项目 harness / 日常流程相关，拷贝时优先确认存在）：

| Skill | 用途 |
|---|---|
| harness / harness-orchestration | Harness 编排入口、路由协调 |
| claude-orchestration / cursor-orchestration | 多 task 并行编排（Claude Code / Cursor） |
| git-xywh | 组织级 Git 工作流（提交前必 Load） |
| verification-before-completion | 完成声明前验证 |
| requesting-code-review / code-review | 尾盘审查 |
| systematic-debugging | 缺陷调查 |
| brainstorming / writing-plans | 设计 / 计划阶段 |
| ruoyi-aigc-backend-developer | 本项目后端开发规范 |
| codebase-memory | 图谱工具说明 |
| ponytail 相关（inline 配置） | 懒惰阶梯配置 |

其余多为 omx（oh-my-codex）、mattpocock、写作类技能，拷贝目录时一并带走即可。

### 注意事项

- `karpathy-guidelines`（旧 stub）引用不存在的 `harness-kit/core/karpathy-guidelines.md`，可删；完整版已由 `andrej-karpathy-skills` 插件提供。
- `harness-kit/scripts/install-ai-skills.sh` 可检查 / 补齐 harness 相关 skills（见 routing.md）。
- omx 相关 skills 换机需重装 oh-my-codex；mattpocock 系列有 `setup-matt-pocock-skills` 引导脚本。

## settings.json 恢复要点

`~/.claude/settings.json` 的 `env` 段含敏感项，换机手动填：

- `ANTHROPIC_AUTH_TOKEN`、`ANTHROPIC_BASE_URL`（<占位>）
- `ANTHROPIC_DEFAULT_{FABLE,HAIKU,OPUS,SONNET}_MODEL(_NAME)`（模型映射）
- `extraKnownMarketplaces` / `enabledPlugins` 由插件恢复命令自动写入，无需手填
