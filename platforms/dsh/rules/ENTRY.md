# DeepSeek Harness (DSH) platform rules

## 入口与加载（本端读哪个文件）

- DSH 从项目根（`.git` 标记）到会话工作目录逐级加载 `AGENTS.md`，同目录的 `CLAUDE.md` 也会作为候选加载；两者内容相同时只注入一次。
- 本项目统一走项目根 `AGENTS.md`，与 Codex / Qoder / WorkBuddy 共用同一入口，四端 delta 合并进同一个文件；不要再把同一份项目规则抄进第二个入口文件。
- 用户全局先读 `~/.dsh/AGENTS.md`，再读 `~/.agents/AGENTS.md`；项目链从项目根到当前工作目录。
- 已注入的规则不重复读取；子目录规则由 `read` / `write` / `edit` 触达更深目录后自动加载，`bash` 切换目录不会触发。

## 审批策略（本端必须遵守）

- 审批策略是用户对会话的设置，不是模型可改的开关；不要试图修改审批策略、沙箱或权限配置。
- `ask`：受限操作可能弹审批。只对当前具体的受限操作发起审批请求，不要预先为未来步骤打包申请。
- `never`：每个审批请求都会直接得到 `rejected`，不会询问任何人。此时受限操作就是不可用：
  - 不索取审批，不请求权限升级；
  - 不换工具、不换路径、不重试同一受限操作来绕过拒绝；
  - 停下并报告被阻断的动作、已完成部分和剩余步骤。
- `ask_user_question` 是面向用户的提问，不等于宿主审批；不能拿它替代受限操作的批准。
- 工具结果里的 `[sandbox: ...]` 等拒绝是执行策略结果，不是故障，按上面的规则处理；不要绕过沙箱读写。

## Tooling（本端接入）

- Skills: `npm run skills:install -- --platform dsh --target <project>` links the curated core into `.dsh/skills/` (DSH's highest-priority project root); omit target for user scope (`~/.dsh/skills`), use `--profile all` for the legacy catalog. DSH also discovers `.agents/skills/` (shared with Codex) at lower priority, so a duplicate name in `.dsh/skills/` wins. Skills are kebab-case bundles with `SKILL.md`; a newly added skill appears before the next model step.
- Agents: DSH has no per-agent project file; subagents come from presets and bundles. `agents:install -- --platform dsh` must refuse instead of silently doing nothing.
- MCP: DSH connects MCP servers through profile bundles or presets, not a project `.mcp.json`; configure one only when the user asks for it.
- Ponytail and local skills run as skills/instructions; there is no plugin or hook lifecycle to enable.
- Subagents and workflows are tools, not permission grants: delegation does not widen the user's authorization, and child agents inherit the same approval policy.

Bootstrap projects this delta to `.dsh/harness/ENTRY.md` and merges it into the shared `AGENTS.md`; `.dsh/skills/` is the only DSH directory the host discovers by itself.
