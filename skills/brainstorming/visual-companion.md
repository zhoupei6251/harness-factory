---
name: visual-companion
description: "Visual Companion 使用指南：在 brainstorming 过程中提供 mockup 和图表可视化辅助"
---

# Visual Companion Guide

## 功能概述

Visual Companion 是一个轻量级的浏览器工具，在 brainstorming 过程中提供可视化辅助。

### 核心功能

1. **Mockup 创建**
   - 拖拽式 UI 组件（按钮、输入框、卡片、导航等）
   - 实时预览
   - 导出为 HTML

2. **图表生成**
   - Mermaid 语法支持
   - 流程图 (Flowchart)
   - 时序图 (Sequence Diagram)
   - 架构图 (Architecture)
   - 状态图 (State Diagram)

3. **HTML/CSS 预览**
   - 自定义 HTML/CSS 代码实时预览
   - 适合复杂布局测试

## 何时使用

在 brainstorming 过程中，当问题用图形表达比文字更清晰时使用。

### 适合可视化的场景

- UI 布局对比（"这个按钮放左边还是右边更好？"）
- 架构图（组件关系、数据流）
- 流程图（用户操作路径）
- 页面结构讨论（导航、内容区、侧边栏布局）
- 组件层级关系

### 不适合的场景

- 概念性问题（"这个功能值不值得做？"）
- 需求澄清（用文字问答更高效）
- 选项对比（表格或列表更清晰）
- 技术细节讨论（代码层面用终端更高效）

## 触发时机

**JUST-IN-TIME 原则**：不要在开始时就询问是否需要可视化工具。

等待第一个真正需要视觉辅助的问题出现，然后在独立消息中询问：

> "这个部分可能用图形展示更清楚——我可以打开可视化工具，帮你创建 mockup 和图表。需要吗？"

**这条消息必须独立发送**，不要在同一个消息中夹杂其他问题或总结。

## 使用流程

1. **判断需求**
   - 在 brainstorming 过程中评估是否需要视觉辅助
   - 如果是，发送独立的工具邀请消息

2. **用户同意后**
   ```bash
   node scripts/visual-companion/server.js --open
   ```
   这会启动服务器并自动打开浏览器

3. **分享链接**
   ```
   http://localhost:3847
   ```

4. **协作使用**
   - 在工具中创建相应的可视化
   - 用户可以同时查看和交互
   - 继续在终端中讨论其他问题

## 工具界面说明

### Mockup Builder（Mockup 构建器）

- 输入标题
- 选择布局（垂直/水平）
- 点击组件按钮添加元素
- 点击 "Generate Mockup" 生成预览
- 点击 "Export HTML" 导出

### Diagram Editor（图表编辑器）

- 选择图表类型
- 选择预设模板或手动输入 Mermaid 语法
- 点击 "Render Diagram" 渲染
- 常用预设：
  - **Basic Flow**: 基础流程图
  - **API Flow**: API 调用时序图
  - **Architecture**: 系统架构图
  - **State Machine**: 状态机图

### HTML Preview（HTML 预览）

- 输入任意 HTML/CSS 代码
- 实时预览效果
- 适合复杂自定义布局测试

## 决策原则

即使用户同意了使用 Visual Companion，每个问题仍需单独判断是否需要视觉辅助：

**使用浏览器**：视觉内容——mockup、线框图、布局对比、架构图
**使用终端**：文本内容——需求问题、概念选择、利弊对比、范围决策

示例：
- "这个向导布局选哪个更好？" → 使用浏览器
- "这个功能的核心价值是什么？" → 使用终端

## 端口说明

- 默认端口：**3847**
- 与 Superpowers 保持一致
- 如果端口被占用，会自动打开已有实例

## 命令

```bash
# 启动服务器（不自动打开浏览器）
node scripts/visual-companion/server.js

# 启动服务器并自动打开浏览器
node scripts/visual-companion/server.js --open

# 或使用简写
node scripts/visual-companion/server.js -o
```

## 故障排除

| 问题 | 解决方案 |
|------|----------|
| 浏览器未自动打开 | 手动访问 http://localhost:3847 |
| 端口被占用 | 端口已被占用时会自动打开已有实例 |
| Mermaid 语法错误 | 检查语法，使用预设模板作为起点 |
| 预览不更新 | 点击 "Generate" / "Render" 按钮 |

## 注意事项

- Visual Companion 是**工具而非模式**——接受它意味着在需要时使用浏览器，不是所有问题都要通过浏览器
- 保持工具窗口和终端对话并行进行
- 不要让工具成为分心的来源——只在真正需要时使用
- 适合临时可视化，复杂或长期需要的图表应保存到设计文档中