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

## Phase → skill map

| Phase | Track | 推荐技能 |
|-------|-------|----------|
| researching | text | hot-topic-content-maker（轻选题）/ news-generator（成稿前素材整理） |
| researching | video | hot-topic-content-maker（当天轻发）/ douyin-pro 采集（要成片时）— 裁决规则见 skills/news-workflow |
| drafting | text | news-generator |
| drafting | video | media-short-video-copy（文案+标题 skillset）/ viral-script-writer（口播稿） |
| fact_check | both | fact-check（必须触发，不可跳过） |
| polishing | text | news-polish + humanizer-zh（去 AI 味） |
| rendering | video | douyin-pro（Path B 免费快出片 / Path A 付费高质量） |
| publishing | both | （暂无专用技能，agent-browser 兜底；发布后回填 published_at） |

## Topics
topics: []
  # - id: t001
  #   title: (topic)
  #   track: (text | video)
  #   status: (researching | drafting | fact_check | polishing | rendering | published)
  #   published_at: YYYY-MM-DD

## Drafts
drafts: []
  # - id: d001
  #   topic_id: t001
  #   word_count: (count)
  #   fact_check: (passed | flagged)

## Videos
videos: []
  # - id: v001
  #   topic_id: t001
  #   path: (A | B)            # douyin-pro 双路径：A=付费高质量 B=免费动画风
  #   render_status: (scripting | dubbing | rendering | done | failed)
  #   output: (成片文件路径，产出后回填)

## In progress
in_progress:
  - current_phase: (researching | drafting | fact_check | polishing | rendering | publishing)
    track: (text | video)

## Last updated
last_updated: YYYY-MM-DDTHH:MM:SS
