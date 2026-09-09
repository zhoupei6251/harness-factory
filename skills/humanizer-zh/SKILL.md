---
name: humanizer-zh
description: 中文 AI 文风清洗，消除 AI 生成特征，去套路化，句式重构，人物声音分化
metadata:
  origin: harness-ink
  priority: P0
  tags:
  - polish
  - humanize
  - chinese
version: 1.0.0
when_to_use: 调用 humanizer-zh 时
status: peripheral
tags:
- shared
domain: novel
category: novel.polish
---
# 中文 AI 文风清洗

## 激活条件

- 用户要求润色（"润色第X章"、"去AI味"）
- 审稿通过后进入润色环节
- 需要消除 AI 生成特征

## 核心能力

### AI 文风清洗
- 消除 AI 常用连接词（"首先"、"其次"、"最后"）
- 删除机械过渡句（"就在这时"、"突然之间"、"只见"）
- 去除万能结尾套话

### 去套路化
- 删除堆砌华丽辞藻
- 消除车轱辘话（同一意思反复表达）
- 避免情绪扁平化

### 句式重构
- 长短句交错
- 避免均匀分段
- 增加节奏感

### 人物声音分化
- 不同角色对话风格差异化
- 口语化调整
- 符合人物身份和性格

## 工作流程

1. **读取原文**
   - 读取待润色章节
   - 读取 `core/NEVER.md`：AI 写作禁忌清单

2. **清洗执行**
   - 识别 AI 套路表达
   - 替换为自然表达
   - 重构句式
   - 分化人物声音

3. **质量检查**
   - 朗读检查：是否有"AI味"
   - 对比检查：与人类作者作品对比
   - 剥离检查：移除套路后内容是否空洞

## 禁止事项

- ❌ 改变情节走向/删减/新增内容
- ❌ 保留 AI 套路化表达
- ❌ 润色后文本更不自然
- ❌ 审稿通过前进入润色环节

## 产物

- 润色后的章节正文
- 更新 `MEMORY.md`（章节状态：reviewed → polished）

## 依赖

- `core/NEVER.md`：AI 写作禁忌清单
- `agents/humanizer.md`：润色师角色定义
