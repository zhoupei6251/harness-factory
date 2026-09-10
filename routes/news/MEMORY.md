# News domain MEMORY

> Auto-loaded when route=news. Persists across writing sessions.

## Column info
- title: (column name)
- beat: (column beat)
- cadence: (daily | weekly | monthly)
- sources: []
  # - name: (source name)
  #   url: (url)
  #   trust: (high | medium | low)

## Topics
topics: []
  # - id: t001
  #   title: (topic)
  #   status: (researching | drafting | published)
  #   published_at: YYYY-MM-DD

## Drafts
drafts: []
  # - id: d001
  #   topic_id: t001
  #   word_count: (count)
  #   fact_check: (passed | flagged)

## In progress
in_progress:
  - current_phase: (researching | drafting | fact_check | publishing)

## Last updated
last_updated: YYYY-MM-DDTHH:MM:SS

## Workflow & skill chain (auto)

| 阶段 | Skill | 说明 |
| --- | --- | --- |
| 选题/初稿 | `news-generator` | 结构化产出初稿：导语、事实要素、背景 |
| 事实核查 | `fact-check` | 引语、数据、时间线逐条核对；flagged 项禁止发布 |
| 润色 | `news-polish` | 语言、节奏、结构优化 |
| 去 AI 味 | `humanizer-zh` | 中文人味化改写 |
| 审查 | `document-review` | 发布前文档审查 |

技能位置：`skills/<name>/SKILL.md`。流程权威：`core/runbooks.md` § news 路线。
