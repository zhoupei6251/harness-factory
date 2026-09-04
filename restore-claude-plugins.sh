#!/usr/bin/env bash
# 一键恢复 Claude Code 插件（Git Bash / macOS / Linux 通用）
# 用法: bash harness-foundry/restore-claude-plugins.sh
# 不含任何密钥；MCP 与 settings 恢复见 mcp-servers.md / README.md
#
# 2026-09 单一来源：本脚本为 claude-code-plugins.md 配套执行入口
#（markdown 仅作摘要，不再独立维护命令块）
set -e

echo "==> 1/2 注册 marketplace（claude-plugins-official 为内置，跳过）"
claude plugin marketplace add DietrichGebert/ponytail
claude plugin marketplace add https://github.com/MiniMax-AI/skills.git
claude plugin marketplace add https://github.com/affaan-m/ECC.git
claude plugin marketplace add anthropics/skills
claude plugin marketplace add multica-ai/andrej-karpathy-skills

echo "==> 2/2 安装插件"
# ★ 核心
claude plugin install ponytail@ponytail
claude plugin install superpowers@claude-plugins-official
claude plugin install context7@claude-plugins-official
claude plugin install playwright@claude-plugins-official
claude plugin install github@claude-plugins-official
claude plugin install mattpocock-skills@claude-plugins-official
# ○ 可选（不需要可注释掉）
claude plugin install firecrawl@claude-plugins-official
claude plugin install minimax-skills@minimax-skills
claude plugin install ecc@ecc
claude plugin install andrej-karpathy-skills@karpathy-skills

echo ""
echo "插件恢复完成。请重启 Claude Code 会话使技能生效。"
echo "下一步：按 mcp-servers.md 恢复 MCP（密钥需手动填）、拷贝 ~/.claude/skills/ 目录。"
