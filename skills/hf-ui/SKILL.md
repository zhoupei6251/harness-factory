---
name: hf-ui
description: "页面视觉、排版、设计系统与交互改进：按任务选择 Impeccable 打磨、Taste 视觉参考或 UI UX Pro Max 本地数据搜索。"
---

# UI 能力选择

先读目标页面、相邻组件、样式变量和既有品牌规范。下面选一个主参考，只有具体缺口才补另一个；不全量读取目录。

| 任务 | 本技能目录内的入口 |
|---|---|
| 已有界面打磨 | upstream/impeccable/polish.md；技术问题按需 upstream/impeccable/audit.md |
| 新页面的内容与视觉方向 | upstream/taste/copy.md、layout.md、type.md、colour.md 中所需的一份；去模板感时补 tells.md |
| 配色、字体、UX、图表或技术栈建议 | scripts/search.py，本地调用 UI UX Pro Max 的原版引擎和数据 |

本地搜索需要 Python 3，纯标准库，无网络、无第三方依赖。用所选技能的实际绝对路径替换 <skill>，搜索关键词使用英文：

    python <skill>/scripts/search.py "keyboard focus" --domain ux
    python <skill>/scripts/search.py "dashboard" --domain color
    python <skill>/scripts/search.py "forms accessibility" --stack vue

默认输出最多三条 JSON 记录；无匹配就调整查询或明确报告，无数据/读取错误以非零退出。先服从项目实际框架版本，再采用数据库建议。

适配边界：Impeccable 仅导入 audit/polish 文档，Taste 仅导入五份设计参考；不包含两者 CLI、Hook、检测器、draw/inspect、图片搜索或自动双 Agent 评审。原文中的这些命令不可执行；其中检查项由当前 Agent 和已有浏览器工具按任务完成。Taste 的 house style 是风格参考，不覆盖已有产品系统，后台表格、边框和业务标签按可用性保留。UI UX Pro Max 接入本地检索，不包含完整设计系统生成器或全平台安装器。

实现后检查加载、空、错误、禁用状态、键盘焦点、长文本和窄屏；按 playwright 技能使用已有浏览器/测试检查实际关键流程。没有浏览器就明确未做视觉验证，不能声称原版检测器通过。
