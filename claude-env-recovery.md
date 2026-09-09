# Claude Code 环境恢复手册（本机快照）

> 记录**本机** Claude Code 环境（插件 / MCP / 用户级 skills），换电脑时按此恢复。
> 快照日期：2026-08-21（Windows 11，Git Bash）。全部文档已脱敏：密码 / API Key 以 `<占位符>` 表示。

## 恢复顺序

1. **装 Claude Code**（桌面版 / CLI），登录账号
2. **恢复插件** — `bash harness-foundry/restore-claude-plugins.sh`（见 [claude-code-plugins.md](claude-code-plugins.md)）
3. **恢复 MCP** — 按 [mcp-servers.md](mcp-servers.md) 手动配置（含密钥条目需手动填）
4. **恢复用户级 skills** — 整体拷贝 `~/.claude/skills/` 目录（纯文本文件，直接复制）
5. **恢复 settings** — `~/.claude/settings.json` 的 `env` 段（token / base_url / 模型映射）手动填
6. 重启 Claude Code，新会话生效

## 文件清单

| 文件 | 内容 |
|---|---|
| [claude-code-plugins.md](claude-code-plugins.md) | 插件全量清单（10 个，标注核心级）+ marketplace 源 + 恢复命令 |
| [mcp-servers.md](mcp-servers.md) | MCP 服务器清单（脱敏）+ 项目 `.mcp.json` + 用户级 skills 说明 |
| [restore-claude-plugins.sh](restore-claude-plugins.sh) | 一键恢复插件脚本（Git Bash） |

## 本机环境速览

| 项 | 值 |
|---|---|
| OS | Windows 11 |
| Shell | Git Bash |
| 插件 | 10 个（marketplace 6 个） |
| 全局 MCP | 11 个（`~/.claude.json`，含 context7 必装）+ 项目级 1 个（宿主仓库 `.mcp.json`） |
| 用户级 skills | ~140 个（`~/.claude/skills/`） |

## 与 harness-foundry 自带插件依赖的关系

本目录 README「工具栈架构」一节已声明框架必需的五件套（codebase-memory-mcp / superpowers / ecc / playwright / ponytail）。
本手册覆盖的是**本机实际安装的全部插件与 MCP**（超集），供换机全量恢复；框架必需件以 README 为准。

## 找回方式提示

harness-foundry 自身是独立 git 仓库（origin/main）。建议把这几个文件 commit 进它自己的仓库并 push，
换电脑时 clone / pull harness-foundry 即得（宿主仓库 `.gitignore` 忽略了整个 harness-foundry 目录，不随宿主仓库同步）。
