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
