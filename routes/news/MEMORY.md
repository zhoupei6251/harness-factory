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
| rendering | douyin-pro（Path B only：`--template <pack>`；产出自带 AIGC 显式角标 + 元数据隐式标识）|
| publishing | douyin-upload `sau douyin upload-video`（前置：fact_check=passed + cookie valid + 成片 `aigc.json` 存在）|

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

⚠️ **只有 `news-coral` 现在能渲染**。其余 11 包 `compositions/` 里只有 `placeholder.html`（占位壳），
`load_style_pack` 在加载阶段就停机（不再等第 1 镜渲染才报错）。按本表挑了它们 = 白跑，
所以**决策树先过"可渲染"这一列**：不可渲染的形态暂时一律落 `news-coral`，或在 frame.md
契约下补出真 composition。

| 触发词 | pack 名 | 可渲染 |
|---|---|---|
| 单主角 / 反转 / 故事 / 召唤 / 钩子 | `news-coral` | ✅ 7 个真版式 |
| 调查 / 深度 / 卧底 / 揭露 / 长文 | `news-ink` | ⏳ 仅占位 |
| 新规 / 政策 / 法规 / 通知 / 施行 | `news-policy` | ⏳ 仅占位 |
| 排行 / 数据 / 第一 / 同比 / 数字 | `news-stat` | ⏳ 仅占位 |
| 突发 / 现场 / 直击 / 抢险 / 灾害 | `news-onsite` | ⏳ 仅占位 |
| 今日要闻 / 整点新闻 / 速报 / 合辑 | `news-bulletin` | ⏳ 仅占位 |
| 为什么 / 原理 / 科普 / 图解 / 解读 | `news-explainer` | ⏳ 仅占位 |
| 紧急 / 提醒 / 务必 / 不要 / 预警 | `news-alert` | ⏳ 仅占位 |
| 纪念 / 节日 / 致敬 / 回顾 / 专题 | `news-thread` | ⏳ 仅占位 |
| 观点 / 评论 / 专栏 / 我觉得 | `news-takes` | ⏳ 仅占位 |
| 比赛 / 比分 / 进球 / 实时赛事 | `news-blast` | ⏳ 仅占位 |
| 国际 / 战况 / 边境 / 地理 / 联合国 | `news-world` | ⏳ 仅占位 |

完整设计契约：`skills/douyin-pro/templates/hyperframes_path_b/<pack>/frame.md`（每个 pack 一份）。

跑命令：

```bash
python skills/douyin-pro/scripts/path_b_build.py \
  --input .harness-news-runtime/articles/<id>-scenes.json \
  --template news-coral \
  --source <署名/频道> \
  --aigc-producer <你的频道/主体名> \
  --output .harness-news-runtime/videos/<id>/final.mp4
```

- `--input` 两种写法：**场景 JSON**（数组，每镜 `layout/kicker/title/body/onscreen`）最稳；
  走 `.md` 脚本则**每镜必须自带 `屏:` 行**，否则 `check_onscreen` 闸门挡住（不是渲染失败，是拒收）。
- `onscreen` 在 JSON 里要用 `｜` 分隔标记语法（如 `"左上角必须有标识｜贯穿全片"`）——
  `parse_input` 会按该标记重写 `onscreen`/`onscreenAccent`，直传 `onscreenAccent` 字段会被覆盖掉。
- `--aigc-producer`（默认 `harness-news-pathb`）是隐式标识里的 ContentProducer，
  `--aigc-label`（默认 `AI 生成合成内容`）是显式角标文字。**两者都不许留空**：
  空 producer 或全片时长 < 2 秒 → 停机，合规项没有逃生门。
- 成片旁必落 `aigc.json` 侧车（font_size_px / short_side_px / shown_seconds / 七要素），
  发布前用它 + `contact-sheet.jpg` 人工核一遍左上角标。

当前进度 (frame.md / host.html / compositions 齐全度)：
- `news-coral`: 完整（frame + host + 7 真 compositions）
- 其余 11 个: frame + host + 1 placeholder（真 composition 待补，且**当前不可渲染**）
- 校验：`python skills/douyin-pro/scripts/path_b_selftest.py`（58 项，含 AIGC 标识与占位包停机测）

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
    aigc_label: none             # ⛔ 不可发布：无显式角标、无隐式元数据（标识能力是 09-29 才补的）
  - id: v002
    topic_id: t001
    template: news-coral
    render_status: done
    output: .harness-news-runtime/videos/t001-v2/final.mp4
    spec: 1080×1920 / 60.9s / 2.17MB（镜头重排版）
    aigc_label: none             # ⛔ 同上
  - id: v003
    topic_id: t001
    template: news-coral
    render_status: done
    output: .harness-news-runtime/videos/t001-v3/final.mp4
    spec: 1080×1920 / 59.3s / 1.87MB（当前最优一版）
    aigc_label: none             # ⛔ 同上 —— t001 要发布必须**重渲**
  - id: probe-aigc
    topic_id: null               # 不是新闻成片，是 AIGC 标识端到端验证探针（2 镜）
    template: news-coral
    render_status: done
    output: .harness-news-runtime/videos/aigc-e2e/final.mp4
    spec: 1080×1920 / 11.9s / 1.01MB + aigc.json + contact-sheet.jpg
    aigc_label: verified         # ✅ 角标字芯实测 62px(≥54px 线)，元数据 ffprobe format_tags 读回一致
  # - id: v001
  #   topic_id: t001
  #   template: <12 选 1, 见上方决策树>
  #   render_status: (scripting | dubbing | rendering | done | failed)
  #   output: (成片文件路径, 产出后回填)
  #   aigc_label: (none | verified)   # none = 发布门禁不放行

## In progress
in_progress:
  - current_phase: publishing
    topic_id: t001
    blocker: 两把锁 —— ① 抖音账号未登录（`sau douyin check` 前不发）；② **现有 t001 三版成片都没有 AIGC 标识**（09-29 才把标识能力做进构建），发布前必须用 v003 那版脚本重渲
    note: 重渲命令见上方「跑命令」；重渲后核对 `videos/<id>/aigc.json` + contact-sheet 左上角标，再走 upload-video。发布主路径已接入（skills/douyin-upload + 本机 .venv/Scripts/sau.exe，见其 references/local-env.md）

## Last updated
last_updated: 2026-09-29
