---
name: news-workflow
description: 新闻域总工作流入口：选题 → 文字/视频分轨生产 → 事实核查 → 润色/成片 → 发布，串联 news 域全部技能并给出选题双技能裁决规则。route=news 的多阶段任务从这里开始。
version: 1.0.0
when_to_use: route=news 且任务跨多个阶段（选题+成稿/成片）时；单阶段任务直接用对应技能
status: peripheral
tags:
- news
- workflow
domain: news
category: news.workflow
skills:
  - "hot-topic-content-maker"
  - "douyin-pro"
  - "news-generator"
  - "media-short-video-copy"
  - "viral-script-writer"
  - "fact-check"
  - "news-polish"
  - "humanizer-zh"
---

# 新闻域总工作流

route=news 的多阶段任务按本工作流走。状态记在 `routes/news/MEMORY.md`（Phase → skill map / topics / drafts / videos 槽位），每完成一个阶段回填状态。

## 步骤 0：选题裁决（先做这个决定）

两个选题技能触发词重叠，按产出去向裁决：

| 场景 | 用哪个 |
|------|--------|
| 当天要发的图文/轻内容（封面+正文+标签，最多加口播成片） | **hot-topic-content-maker** |
| 目标是高质量成片视频（混剪/AI生图/配音渲染/数字人） | **douyin-pro**（采集→策略大脑，走 Path A 或 B） |
| 用户自己带来了热点/素材 | 跳过采集，直接进步骤 1 |

裁决后在 MEMORY `topics` 记录 `track: text | video`。

## 步骤 1：分轨生产

### 文字轨（track: text）
1. **news-generator**：根据选题/素材生成新闻稿件 → 记入 `drafts`
2. **fact-check**：草稿进入 fact_check 阶段**必须触发**，多源交叉验证；flagged 的稿件回到上一步修正，不可带病进入润色

### 视频轨（track: video）
1. **media-short-video-copy**（skillset，内含 6 技能）：竞品文案提取 → 多平台脚本 → 爆款标题；或单用 **viral-script-writer** 出黄金3秒口播稿
2. 已有文字稿要转视频：把稿件作为素材喂给 media-short-video-copy 的脚本创作步骤（文字轨 → 视频轨的桥）
3. **douyin-pro**：成片渲染，记入 `videos`（path A/B、render_status）
   - Path B（免费）：edge-tts + HyperFrames → MP4，零云费，默认首选
   - Path A（付费）：策略大脑→混剪/高光→AI生图→配音渲染→数字人，用户明确要高质量时启用
4. 视频轨的口播文案若引用外部数据/事实，同样过 **fact-check**

## 步骤 2：润色（文字轨）

- **news-polish**：去 AI 味、专业化表达
- 需要更彻底的去 AI 味时叠加 **humanizer-zh**

## 步骤 3：发布（两轨共用）

暂无专用发布技能：
1. 用 agent-browser / playwright 兜底操作发布页，或把成品交给用户手动发布
2. 发布后回填 MEMORY：`topics.published_at`、`videos.output`、`in_progress` 清空

## 硬性规则

1. **fact-check 不可跳过**：任何进入 publishing 的稿件/口播文案，`fact_check` 字段必须是 passed
2. **状态随做随记**：每阶段结束更新 MEMORY，跨会话不丢进度
3. **选题裁决先于生产**：没定 track 之前不要同时启动两条轨
4. **产物写 route 运行时目录**：稿件/成片落 `.harness-news-runtime/`（`articles/`、`videos/`），**不要**写 `.ai-runtime-artifacts/`——那是 code 路由的运行时目录（specs/plans/decisions/verifications），news 产物放错域会脱离本产线的状态跟踪
