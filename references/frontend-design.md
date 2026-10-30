# 前端页面设计参考

仅在页面、视觉或交互任务时读取 skills/hf-ui/SKILL.md，再选一个主参考。内容已经固定版本随仓库保存，离线可读；完整来源、导入边界和更新方式见 coding-capabilities.md 与 upstreams.lock.json。

| 当前任务 | 主参考（相对 skills/hf-ui/） | 用法 |
|---|---|---|
| 已有页面打磨、排版或技术质量检查 | upstream/impeccable/polish.md；必要时 audit.md | 按严重度和实际操作路径修复；原文 CLI/检测器未导入，不声称运行过 |
| 新页面视觉方向与内容层级 | upstream/taste/copy.md、layout.md、type.md、colour.md 中需要的一份 | 从产品真实内容建立构图；tells.md 用于去除无意义模板装饰；遵守既有品牌和后台可用性 |
| 后台、表单、仪表盘、设计系统建议 | scripts/search.py | 用 UI UX Pro Max 原版引擎离线搜索配色、字体、图表、UX 和实际技术栈，默认最多三条 |

先看现有路由、组件库和样式变量，复用项目依赖。一个主参考不足以解决明确缺口时才补第二个，不串联三个上游完整流程。不会为了参考风格安装组件库、字体包、动画库或运行上游 Hook。

## 实施与验证

1. 明确用户、核心动作、真实内容和视觉方向；已知信息直接复用，只有实质歧义才提问。
2. 完成内容层级、布局和可用交互，再处理配色、字体和必要动效。字体和图片按项目约束使用并保留授权。
3. 验证正常、加载、空、错误与禁用状态、长文本、键盘焦点和响应式；颜色不独自表达状态，尊重减少动画偏好。
4. 按 playwright 或 hf-web-test 技能复用现有浏览器/测试，检查桌面和窄屏，操作关键路径，查看实际截图和错误。缺少工具时明确未做视觉验证。

上游地址：[Impeccable](https://github.com/pbakaus/impeccable)、[Taste](https://github.com/Leonxlnx/taste-skill)、[UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)。本地导入是明确子集；命令和能力以 hf-ui 的适配说明为准。
