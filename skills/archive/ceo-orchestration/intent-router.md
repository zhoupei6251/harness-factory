---
name: ceo-intent-router
description: "意图理解 + 路由到域 — CEO 将用户需求翻译成结构化任务"
---

# Intent Router（意图路由）

## 激活条件

CEO 接收用户输入时自动调用。

## 工作流程

### 1. 意图提取

分析用户输入，提取：
- **域**：code / novel / news
- **任务**：要做什么
- **约束**：字数/质量/截止时间等
- **优先级**：normal / high / low

### 2. 路由决策

按 `core/intent-routing.md` 的三层路由判断：

```
第一层：显式路由
  用户说 "写代码" → code
  用户说 "写小说" → novel
  用户说 "写新闻" → news

第二层：上下文路由
  当前文件类型 / 最近对话 / 工作目录

第三层：兜底
  无法判断 → 反问用户
```

### 3. 格式转换

将用户需求转换为标准格式，写入 `handoff/ceo-task.md`：

```markdown
domain: novel
task: <从用户输入提取的核心任务>
constraints: <约束条件>
priority: normal | high | low
```

### 4. 质量检查

- domain 是否有效
- task 是否非空
- constraints 是否合理

## 输出

`handoff/ceo-task.md`

## 错误处理

| 场景 | 处理 |
|------|------|
| 无法判断域 | 反问用户："你想写代码、写小说还是写新闻？" |
| 用户说 "随便" | 询问当前工作目录对应的域 |
| 域间歧义 | 展示多个可能，征求用户确认 |
