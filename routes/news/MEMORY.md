# News domain MEMORY（v2 单轨 · 零云费）

> Auto-loaded when route=news. Persists across writing sessions. 架构见 `routes/news/ARCHITECTURE.md`。

## Column info
- title: (column name)
- beat: (column beat)
- cadence: (daily | weekly | monthly)
- sources: []
  # - name: (source name)
  #   url: (url)
  # - trust: (high | medium | low)

## Phase → skill map

| Phase | 技能 |
|-------|------|
| researching | hot-topic-content-maker |
| drafting | media-short-video-copy / viral-script-writer |
| fact_check | fact-check（必须，不可跳过）|
| rendering | douyin-pro（Path B only：`--template <pack>`）|
| publishing | douyin-upload `sau douyin upload-video`（前置：fact_check=passed + cookie valid）|

## Topics
topics:
  - id: t001
    title: 拾荒老人不知自己每月有3700元养老金（湖南常德，71岁）
    status: rendering                   # researching → drafting → fact_check → rendering → published
    source: 微博热搜榜 #5（tophub 采集于 2026-09-28）
    official_response: 常德市社会救助事务中心（澎湃/工人日报·三工晨报 报道内引用）
  # - id: t001
  #   title: (topic)
  #   status: (researching | drafting | fact_check | rendering | published)
  #   published_at: YYYY-MM-DD

## Drafts
drafts:
  - id: d001
    topic_id: t001
    kind: 口播稿（5 分镜）
    path: .harness-news-runtime/articles/t001-script.md
    word_count: 230
    fact_check: passed         # 多源交叉：澎湃/工人日报·三工晨报 + 新浪财经 + 中华网 + 搜狐 + 官方回应
  # - id: d001
  #   topic_id: t001
  #   word_count: (count)
  #   fact_check: (passed | flagged)

## 模板决策树 (12 pack)

按稿件特征词选视觉气质。t001（拾荒老人）= 人物故事型 → `news-coral`。

| 触发词 | pack 名 |
|---|---|
| 单主角 / 反转 / 故事 / 召唤 / 钩子 | `news-coral` |
| 调查 / 深度 / 卧底 / 揭露 / 长文 | `news-ink` |
| 新规 / 政策 / 法规 / 通知 / 施行 | `news-policy` |
| 排行 / 数据 / 第一 / 同比 / 数字 | `news-stat` |
| 突发 / 现场 / 直击 / 抢险 / 灾害 | `news-onsite` |
| 今日要闻 / 整点新闻 / 速报 / 合辑 | `news-bulletin` |
| 为什么 / 原理 / 科普 / 图解 / 解读 | `news-explainer` |
| 紧急 / 提醒 / 务必 / 不要 / 预警 | `news-alert` |
| 纪念 / 节日 / 致敬 / 回顾 / 专题 | `news-thread` |
| 观点 / 评论 / 专栏 / 我觉得 | `news-takes` |
| 比赛 / 比分 / 进球 / 实时赛事 | `news-blast` |
| 国际 / 战况 / 边境 / 地理 / 联合国 | `news-world` |

完整设计契约：`skills/douyin-pro/templates/hyperframes_path_b/<pack>/frame.md`（每个 pack 一份）。

跑命令：

```bash
python skills/douyin-pro/scripts/path_b_build.py \
  --input .harness-news-runtime/articles/<id>-script.md \
  --template <pack_name> \
  --source <署名> \
  --output .harness-news-runtime/videos/<id>/final.mp4
```

当前进度 (frame.md / host.html / compositions 齐全度)：
- `news-coral`: 完整（frame + host + 7 真 compositions）
- 其余 11 个: frame + host + 1 placeholder（真 composition 待补）
- 校验：`python skills/douyin-pro/scripts/path_b_selftest.py` 跑 `t_full_loadability_progress` 看 X/12

## Videos
videos:
  - id: v001
    topic_id: t001
    template: news-coral         # 12 模板之一 (见上方决策树)
    render_status: done
    output: .harness-news-runtime/videos/t001/final.mp4
    spec: 1080×1920 / h264+aac / 60.9s / 2.32MB / 字幕轨 10 条（ASS 内嵌烧录）
    voice: zh-CN-XiaoxiaoNeural
    kicker: 新闻速读
  # - id: v001
  #   topic_id: t001
  #   template: <12 选 1, 见上方决策树>
  #   render_status: (scripting | dubbing | rendering | done | failed)
  #   output: (成片文件路径, 产出后回填)

## In progress
in_progress:
  - current_phase: publishing
    topic_id: t001
    blocker: 抖音账号未登录（用户自行准备账号中）——`sau douyin check` 前不发
    note: 发布主路径已接入（skills/douyin-upload + 本机 .venv/Scripts/sau.exe，见其 references/local-env.md）；成片 .harness-news-runtime/videos/t001/final.mp4，待 cookie valid 后执行 upload-video

## Last updated
last_updated: 2026-09-29
