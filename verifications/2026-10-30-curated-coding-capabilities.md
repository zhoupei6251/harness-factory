# 精选上游代码能力交付证据

范围与取舍见 docs/plans/2026-10-30-curated-coding-capabilities.md。基线为 0336507，工作于 main，没有改用户全局配置或 push。

## 图谱与实现

- 精确项目 D-work-xinyue-aigc_platfrom_back-harness-factory；最终取证代际 2026-10-30T03:21:43Z，记录刷新至 03:22:54Z。
- search_graph 定位 installSkill、skillNames、verifyUpstreams；trace_path 验证安装模块调用 installSkill。覆盖检查针对修改的脚本、测试和 UI CLI 无记录缺口；仍以当前源文件为准，没有把图谱空边解释为完整性证明。
- 复用现有 skills、安装器、Node 标准库、bootstrap、断言测试与已有 Playwright 指南。新增默认 core10/显式 all、五端路径、项目安装与 dry-run、冲突保护和离线源文件校验，无新增 npm 依赖。

## 上游审查记录

清单中的 75 个文件约 2.4 MB（主要为静态 UI 数据），记录八个仓库的精确提交和每文件 SHA-256；导入只规范化换行。移除了检索引擎不使用的图标原始清单、目录统计和设计系统推理表，保留查询数据与字体许可。完整路径、版本、许可见 references/upstreams.lock.json 与各 upstream 目录。

| 来源 | 文件数 | 选取内容与权限判断 |
|---|---:|---|
| Superpowers | 9 | 调试/验证指令与例子；调查 Bash 脚本需要项目命令与 Bash，仅明确需要时使用，不是默认执行链 |
| ECC | 2 | 安全检查文档和 MIT 许可；代码为示例，适配层禁止自动更新依赖或执行生产操作 |
| Matt Pocock | 8 | 模块/TDD 文档和 MIT 许可；本地适配去除重复确认与默认多 Agent 流程，尊重现有领域词汇 |
| Impeccable | 4 | audit/polish、Apache-2.0 许可和 NOTICE；未接入 CLI/检测器，适配层明确不能执行模板命令 |
| Taste | 6 | 五份设计参考及 MIT 许可；无脚本、浏览器、图片下载、动画运行时 |
| UI UX Pro Max | 38 | 原版 core.py、检索数据及许可来源记录；引擎仅用标准库读取本地数据，无网络/包安装/进程启动；小型本地 CLI 复用它 |
| Anthropic | 6 | webapp-testing 文档、三个例子、辅助脚本和自带 Apache-2.0 许可；例子需改实际地址/路径。辅助脚本 shell/子进程/管道限制已明确，不默认执行 |
| Ponytail | 2 | 原版技能和 MIT 许可；无插件/Hook 运行时 |

执行路径的源代码已静态读取；资源按静态数据处理并逐文件核对哈希。没有把代码示例中的凭证占位符当成真实凭证，没有向外发送项目数据或安装上游 Hook。风险分类：文档/数据低；可执行浏览器示例和 Bash/服务辅助脚本中，保留为受限、非默认能力。哈希一致不等于无漏洞或完整的上游行为审计。

## 测试与独立审查

- 安装 CLI 测试先在旧实现上失败（旧脚本忽略 target/dry-run），再在新实现上通过；所有写入在临时 home/project 中，退出清理。
- 上游校验/UI 测试先因模块尚未实现失败，后验证原始哈希、改动、丢失文件、路径穿越、固定 revision、UX/Vue 实际命中、空查询、无匹配和无效参数。
- requesting-code-review / two-stage-review 要求的一名独立只读审查者复核需求和代码。发现 Codex 项目目录及 Windows 跨盘 junction 两个可复现问题，均增加先红后绿回归并修复；审查者独立重跑两组测试，退出 0，没有剩余阻塞问题。
- Codex 当前技能目录通过 OpenAI 官方文档核实为 .agents/skills；修正安装、说明与测试，不迁移旧全局副本。
- 完整 npm test 已通过一轮，严格 check-bootstrap 与 diff 检查通过；审查修复后的最终完整命令结果在下方记录。

## 验证边界

当前会话 Codebase Memory MCP 已连通并实际取证。安装器验证的是五端文件/目录及保护契约，没有启动五端客户端检查 native discovery；没有启动浏览器 MCP、执行 UI 页面交互或调用上游完整插件。新技能可能需要新会话；未装 Python 时 UI 查询测试明确跳过，本机使用 Python 3.12.3 实际运行并通过。没有自动执行 Maven、部署或改其他项目。

最终验证：审查修复和静态删减后 npm test 完整退出 0（含 Python 3 实际查询）；npm run check:upstreams、npm run check-bootstrap -- --require-generated 及 git diff --cached --check 均退出 0。git checkout-index 生成的全新暂存快照在 core.autocrlf=true 下也通过哈希检查，证明 LF 属性保证 Windows 检出字节一致。上游 webapp-testing 原文的一处末尾空格按精确文件属性保留，未改动原文哈希；自己的代码/文档仍接受正常 whitespace 检查。
