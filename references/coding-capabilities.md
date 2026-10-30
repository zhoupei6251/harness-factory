# 精选代码能力

Harness 保留一个默认执行流程：理解代码 → 最小实现 → 相关验证。基础技能是 Ponytail full 和 codebase-memory；任务能力按 core/intent-routing.md 选择，不在会话启动时读取所有正文。

## 本地能力与范围

| 能力 | 技能入口 | 已导入内容 |
|---|---|---|
| 最小实现 | `skills/ponytail/SKILL.md` | Ponytail 原版指令；不包含插件/Hook |
| 代码理解与影响分析 | `skills/codebase-memory/SKILL.md` | Codebase Memory MCP 工具协议适配；外部服务单独配置 |
| 根因调试 | `skills/hf-debug/SKILL.md` | Superpowers systematic-debugging 及根因/等待/防御参考 |
| 完成验证 | `skills/hf-verify/SKILL.md` | Superpowers verification-before-completion |
| 安全边界 | `skills/hf-security/SKILL.md` | ECC security-review；复用已有 common/Java/TypeScript 规则 |
| 模块设计 | `skills/hf-design/SKILL.md` | Matt Pocock codebase-design、DEEPENING、可选方案比较参考 |
| 有效测试 | `skills/hf-tdd/SKILL.md` | Matt Pocock TDD、好坏测试示例、mock 边界 |
| 页面打磨 | `skills/hf-ui/SKILL.md` | Impeccable audit/polish 文档；不含 CLI、检测器、Hook、自动双 Agent 评审 |
| 页面视觉方向 | 同上 | Taste 的 copy/layout/type/colour/tells 五份参考；不含 draw/inspect、资产搜索和动画工具 |
| UI/UX 数据查询 | 同上 | UI UX Pro Max 原版 core.py、静态数据和小型本地 CLI；不含完整设计系统生成器 |
| 浏览器与 Web 测试 | `skills/playwright/SKILL.md`、`skills/hf-web-test/SKILL.md` | 已有 Playwright 指南 + Anthropic webapp-testing 原文、示例与有明确限制的辅助脚本 |

这是明确选择的上游子集。原始内容位于各技能的 upstream/，前置 SKILL.md 解释如何在本项目使用以及哪些命令不可用。仅加载当前需要的参考文件/章节。原文示例不是执行授权，不自动安装依赖、创建 worktree、提交、运行 Hook 或重复审批。当前项目的限制、用户授权与既有设计系统优先。

## 安装和使用

在 Harness 根目录：

```powershell
# 预览五端的项目级接入，不写文件
npm run skills:install -- --target D:/path/to/project --dry-run
# 安装默认 10 个核心技能：可省略 platform 以覆盖五端
npm run skills:install -- --platform codex --target D:/path/to/project
# 显式需要旧目录中的所有 active 技能时
npm run skills:install -- --platform codex --profile all --target D:/path/to/project
```

五端项目目录分别为 .claude/skills、.agents/skills（Codex）、.trae/skills、.codebuddy/skills、.qoder/skills。Codex 的发现目录见[OpenAI 官方文档](https://learn.chatgpt.com/docs/build-skills)，Trae 见[官方文档](https://docs.trae.cn/ide_skills)，WorkBuddy 的代码项目目录见[官方说明](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Project)。省略 target 时安装到用户主目录下的相同目录；旧 Codex 用户安装可能仍在 ~/.codex/skills，不自动迁移或覆盖。Trae 国际版/CN 客户端的全局目录可能不同，优先项目级安装。

安装使用目录链接（Windows junction），所以 Harness 必须保留在稳定路径。重复运行保留相同链接；用户目录、普通文件、其他目标或失效链接不会被覆盖，冲突使命令非零退出。core 不自动移除以前 all 安装的技能；若已有旧安装，先检查并显式移除不需要的链接。需要完全隔离时使用项目级安装，宿主仍可能发现用户全局技能。客户端可能需要新会话才重新发现技能。

即使未安装，原生 Harness 入口也会指示 Agent 直接读取 `harness-factory/skills/<name>/SKILL.md`。不会因未注册斜杠命令就把可读取的本地能力当成不存在。

## 外部工具

- 图谱：按 references/tooling.md 配置 Codebase Memory MCP，当前会话真实调用 list_projects 才说明连通；仅未索引才索引。
- 浏览器：优先宿主已提供的浏览器或项目已有 Playwright。需要 MCP 时使用 mcp-config/playwright.json / playwright.codex.toml 片段；它们不会被 bootstrap 或安装器自动写入全局设置。Windows JSON 片段使用 npx.cmd，其他系统改为 npx。配置后新会话实际打开一个本地页面并截图/操作，再声称可用。
- UI 搜索：Python 3、纯标准库，离线检索。命令见 hf-ui。没装 Python 就报告未执行搜索，按本地文档或 CSV 补证；浏览器未连接就报告未做视觉验证。

## 来源、许可与更新

references/upstreams.lock.json 记录八个内容来源的仓库、固定提交、源路径、目标路径和 SHA-256。Ponytail 原文为直接入口；其余上游原文不改写，所有副本仅规范化 LF 和末尾换行。许可证随每个来源保存；Impeccable 同时保留 NOTICE，Anthropic 使用 webapp-testing 自带的 LICENSE.txt。图谱和 Playwright 服务通过外部配置接入，没有复制其二进制。

`npm run check:upstreams` 和 npm test 校验本地文件、许可证记录、固定提交格式和路径安全，运行时不访问网络。哈希证明副本与清单一致，不证明代码无漏洞；引擎/数据来源和原文示例仍需按实际项目判断。

更新是显式维护操作：先审查选定上游提交与现有固定提交的差异，确认许可证、脚本权限和本地适配仍成立；只替换需要的同一子集，保留规范化方式，更新提交与文件哈希。审查新的执行代码后运行本地搜索/安装测试、npm test 和严格 bootstrap 检查。不跟随 latest 静默更新，不在会话开始、bootstrap 或普通安装时下载上游。
