# Trae platform rules

> Add Trae-specific deltas here. Loaded after the canonical core/ENTRY.md.

## Hooks

Trae hook support is limited (as of 2026). Document what works here.

## MCP

Trae MCP format: `.trae/mcp.json`.

## Tooling（本端接入）

> 代码域强制：改 TS / 脚本 / 测试 / 配置 / 规则文件前，先用 codebase-memory-mcp 取证据（R1）、生成前走 ponytail 决策阶梯（R2 / R8）。纯文案产出豁免。
> 工具缺失或未接通时改用等效手段（Read / Grep），并在回复中声明：
> `[codebase-memory-mcp 不可用，已降级] 原因：<未装 / MCP 未连通 / 索引缺失>；替代手段：<Read / Grep 手工取证>`

- **ponytail**：Trae 无插件系统 → 装为 skill（上游 `skills/ponytail/SKILL.md`）或复制上游 `AGENTS.md` 精简版进项目规则；纯指令约束、无 hook 强制，属能力差异不算降级
- **codebase-memory-mcp**：设置 → MCP → 添加服务器，粘贴 `mcp-config/codebase-memory.json` 内容
- **验证**：规则版新会话问「阶梯当前档位」有回答；skill 版 `/ponytail-help` 有输出；`list_projects` 能返回

## Projected to

- `.trae/rules/ENTRY.md` (this file)
- `.trae/rules/ROOT.md` (canonical ENTRY.md)
- `.trae/rules/project_rules.md` (native auto-loaded entry, generated from canonical + this delta)
