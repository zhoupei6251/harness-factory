# Heron 工作区指令

本目录是前后端工作区，不是 Git 仓库。以下路径均相对本文件所在目录；命令在目标仓库内执行。

## 任务入口

| 任务范围 | 先读入口 | 技术栈 |
| --- | --- | --- |
| 后端、数据库、业务接口 | [heron/AGENTS.md](heron/AGENTS.md) | RuoYi-Vue-Plus、Java、MySQL、Redis |
| 前端页面、API、types | [heron-ui/AGENTS.md](heron-ui/AGENTS.md) | plus-ui、Vue 3、TypeScript、Element Plus |
| 前后端联动 | 上述两个入口 | 先核对接口契约，再分别验证 |
| 整体架构、模块职责、配置与部署 | [heron/CODE_WIKI.md](heron/CODE_WIKI.md) | 代码地图（只讲组织，业务规则外链） |

业务需求以 [业务规格](heron/docs/plans/2026-10-29-heron-business-spec.md) 为准。只读取当前任务相关规范，不在每次任务中展开所有角色和 reference。

## 编码规范与角色（已挂到工作区根）

两个子仓库的 `.codex/skills` 与 `.claude/agents` 已链接到本目录 `.claude/`，会话可直接用，不必进子仓库找：

- 后端写码：`Skill: ruoyi-plus-ai-coding` → 按需读 `references/backend.md`；配套前端页读 `references/frontend.md`
- 前端写码：`Skill: frontend-crud-coding` → 按需读 `references/frontend.md`；标准用例读 `references/examples.md`
- 角色（10 个）：`backend-crud` / `backend-query-permission` / `backend-module-enhancement` / `backend-common-infrastructure` / `backend-javadoc` / `backend-engineering`（后端总入口）、`frontend-crud-page` / `frontend-crud-coding`（前端总入口）/ `frontend-api-types` / `frontend-page-enhancement`
- 后端任务优先从 `backend-engineering` 起步，前端从 `frontend-crud-coding` 起步，再按其指引读具体角色
- 角色文档里的相对路径按**子仓库**理解：后端 `heron/`，前端 `heron-ui/`
- 这些是链接，改子仓库原文件即生效；两侧内容冲突时以子仓库真实代码和 `CLAUDE.md` 为准

## Qoder 适配方式

- 各仓库的 `CLAUDE.md` 是现有项目规范，按下级入口显式读取；文件名不要求安装或启动 Claude。
- `.codex/skills` 的编码指导可以用 Read 读取。只有当前会话确实列出的技能名才通过 Skill 调用，不把 `$技能名` 当成 Qoder 命令。
- `.claude/agents` 是角色指导材料，不代表 Qoder 已注册同名子代理。需要委派时选用当前可用代理，提供适用角色文件与任务范围；没有合适代理就由主代理执行，不声称完成了独立审查。
- 不复制 `agents/openai.yaml` 为 Qoder 配置，不迁移权限、Hooks、MCP、模型或凭据。指令文件存在不等于已验证新会话自动加载；未加载时显式附加或读取本文件。

## WorkBuddy 适配方式

- WorkBuddy 读项目根 `AGENTS.md`（官方兼容 `CODEBUDDY.md`、`.codebuddy/CODEBUDDY.md`、`AGENTS.md`），与 Codex / Qoder 共用同一份入口，本文件即会话上下文，不需要另建 `.codebuddy/rules/` 副本。
- 代码开发的项目级配置在 `.codebuddy/`：`skills/` 放技能链接、`agents/` 放角色包装、`commands/` 放斜杠命令；`.workbuddy/` 只存 Agent 工作态（记忆/会话数据），不往里写规则。
- Skill 只有在当前会话的技能清单里出现时才算可调用；未出现就 Read `harness-factory/skills/<name>/SKILL.md` 作为降级，不假装已加载。
- `.claude/agents` 是角色指导材料，不自动等于 WorkBuddy 已注册同名子代理；委派时向当前可用代理提供角色文件路径与任务范围。

## 工作边界

- 产品名称为 Heron，保留若依基座和 `ruoyi-*` 命名；业务落在 `heron/ruoyi-modules/ruoyi-heron`，公共模块只读参考，修改需用户另行明确授权。
- 遵守现有单租户自部署边界；不增加第二套账号、权限、租户或计费体系，发布与业务交付保留人工确认。
- 改动前分别检查目标仓库状态，保留已有未提交工作；提交、推送、服务重启和数据库操作不能由“初始化”或“写代码”推定授权。
- 按下级规范运行与改动相关的验证；前端交互还需实际浏览器验收。仅改指令时检查路径、内容和 diff，不运行应用构建。
