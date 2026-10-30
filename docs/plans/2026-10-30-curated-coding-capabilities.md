# 精选上游代码能力接入

目标：沿用 Claude Code、Codex、Trae、WorkBuddy、Qoder 五端，在现有 Harness 上接入能离线读取的精选上游内容，保持默认上下文和安装范围小。

用户已选择方案 A（精选上游技能加少量适配），并授权实施。直接在 main 工作，不创建 worktree，不修改用户全局配置，不 push。

## 设计与取舍

- 复用 skills/、现有安装器、bootstrap 和测试框架，不新增依赖或插件运行时。
- 默认安装少量核心技能；旧技能保留为显式 all 配置。技能正文按任务加载，同一任务只有一个主流程。
- Ponytail 与代码图谱为基础；Superpowers 提供调试和验证，ECC 提供安全与语言实践，Matt Pocock 提供模块设计与测试，Anthropic 提供 Web 测试方法。
- UI 采用 Impeccable 的打磨准则、Taste 的视觉参考、UI UX Pro Max 的本地搜索引擎和数据。只接入明确列出的子集；不冒充完整插件，不运行上游 Hook、双 Agent 评审或浏览器探测器。
- 上游文件保留原文、许可证和固定提交；清单记录每个文件的 SHA-256。离线检查检测缺失和改动，升级需显式重新取证。
- 各端通过原生技能目录接入。浏览器/图谱服务是外部工具，提供配置和真实可用性检查，不把技能安装等同于服务连通。

## 当前证据

- 图谱项目：D-work-xinyue-aigc_platfrom_back-harness-factory；已定位 activeSkillNames / installSkill，trace_path 确认模块为调用者。
- 现有安装器扫描所有 active skills，仅支持 claude/codex/qoder；缺少选择配置、预览和安装行为测试。
- references/frontend-design.md 目前只有三个上游链接。安装/生成规则可复用；工作区起始干净，基线提交 0336507。

## 实施与通过标准

1. 先为安装器写 CLI 集成测试，验证五端项目级安装、核心/all 选择、幂等、保留用户目录与外部链接、错误参数及 dry-run 不落盘；先见红再实现。
2. 加入精选技能入口、上游原文/数据/许可和哈希清单；逐项静态审查，只保留所需能力。UI 本地搜索验证实际命中与错误输入。
3. 更新入口、任务选择、平台说明和下游模板；bootstrap 仍只做本地生成。
4. 运行相关测试、npm test、严格生成一致性检查和 git diff --check；对安装边界及供应链变更安排独立审查并修复发现。

验证边界：CLI 安装与文件内容可以在临时项目中验证；没有启动的五端客户端、浏览器 MCP 和外部工具不声称已做端到端验证。
