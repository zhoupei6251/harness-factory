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
| researching | news-collect（采集线索，零成本）→ hot-topic-content-maker（选题裁决；**付费热榜查询本域禁用**）|
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

⚠️ **现在能渲染的是 `news-coral` 与 `news-policy`（2/12）**。其余 10 包 `compositions/` 里只有
`placeholder.html`（占位壳），`load_style_pack` 在加载阶段就停机（不再等第 1 镜渲染才报错）。
按本表挑了它们 = 白跑，所以**决策树先过"可渲染"这一列**：不可渲染的形态暂时政策/法规类落
`news-policy`、其余落 `news-coral`，或在 frame.md 契约下补出真 composition。

| 触发词 | pack 名 | 可渲染 |
|---|---|---|
| 单主角 / 反转 / 故事 / 召唤 / 钩子 | `news-coral` | ✅ 7 个真版式 |
| 调查 / 深度 / 卧底 / 揭露 / 长文 | `news-ink` | ⏳ 仅占位 |
| 新规 / 政策 / 法规 / 通知 / 施行 | `news-policy` | ✅ 5 个真版式（hook/story/catalog/rail/closer；`quote` 被该包法则 4 排除、`stat` 归 `news-stat`，刻意不 author）|
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
**补真版式前先看该 pack frame.md §6 的词干映射**：自动选版只认 `path_b_build.AUTO_LAYOUT_STEMS`
那 7 个文件名（hook/closer/story/stat/quote/catalog/rail），其余名字只有分镜显式点名才生效 ——
按 §7 原计划的名字直接建文件会造出一个"看着齐备、自动模式永远选不到"的惰性版式。

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
- `onscreen` 在 JSON 里要用 `｜` 分隔标记语法（如 `"门诊新规｜全国执行"`）——
  `parse_input` 会按该标记重写 `onscreen`/`onscreenAccent`，直传 `onscreenAccent` 字段会被覆盖掉。
- `--aigc-producer`（默认 `harness-news-pathb`）是隐式标识里的 ContentProducer，
  `--aigc-label`（默认 `AI 生成合成内容`）是显式角标文字。**交付件两者都不许留空**：
  空 producer 或全片时长 < 2 秒 → 停机，可交付的成片没有"关掉标识"这条路。
- **标识开关只有两处，代价都在"发不出去"这一侧**（2026-09-29 用户口径：先要开关、同日定「还是默认都打开」、
  同日再改「先帮我把两开关先关了吧」）。代码默认永远全开，**"现在关着"落在姿态文件**
  `routes/news/aigc-mode.json`（裁决顺序 **旗标 > 姿态文件 > 代码默认**，见 ARCHITECTURE D11/D12）：
  ① 渲染层 `--draft` / 姿态 `render=draft` —— 不烧角标、不写元数据，侧车只落 `draft` 一段（**不含**
  `explicit` / `metadata_key` / `implicit`，缺什么记什么缺，不写一堆 false 装作"标识在只是没开"），
  反向旗标 `--deliver`；② 发布层 `--allow-undeclared` / 姿态 `declaration=undeclared` —— 不带平台
  自主声明仍然放行，但会打警告并要求在 `videos[].declaration` 留痕，反向旗标 `--require-declaration`。
- **当前姿态（2026-09-29 起，两个开关都关着）**：`render=draft` · `declaration=undeclared`。
  直接后果：**默认渲染出来的每一份都是草稿，闸门必然 EXIT=1** —— 要交付就显式加 `--deliver`；
  姿态关了 ③ 也一并关掉发布命令里的 `--declaration`，而 ② 元数据过抖音转码即失，③ 是唯一活到
  平台侧的那一件，所以**这个阶段发出的每一条视频都要在 `videos[].declaration` 记 `undeclared`**。
  回退：把 `aigc-mode.json` 的 `render` 改回 `full`、`declaration` 改回 `required`，或删掉该文件。
- 成片旁必落 `aigc.json` 侧车（font_size_px / glyph_height_px / short_side_px / margin_v_px /
  position / shown_seconds / 七要素），发布前用它 + `contact-sheet.jpg` **第 1 镜**人工核一遍
  左下角标 —— 角标只在开场 4 秒常驻，看后面的镜头当然看不到，这不是缺陷。

当前进度 (frame.md / host.html / compositions 齐全度)：
- `news-coral`: 完整（frame + host + 7 真 compositions）
- `news-policy`: 完整（frame + host + 5 真 compositions，占位壳已删）
- 其余 10 个: frame + host + 1 placeholder（真 composition 待补，且**当前不可渲染**）
- 校验（三道闸，仓库根执行）：`path_b_selftest.py`（**项数以脚本末行输出为准，别在文档里抄数**；覆盖
  AIGC 标识、草稿轨、发布闸门与姿态文件的判据、占位包停机、色板复算、版式词表，以及三道闸各自的
  假绿负例）+ `audit_pack_contrast.py`（12 pack 色板/对比度复算）+
  `layout_selfcheck.py <pack 目录…>`（17 条结构不变量；**参数是含 `compositions/*.html` 的目录不是包名** ——
  传进去而里面没有版式文件现在当场 exit 1 并点名该目录，不再"0 个文件 0 条违规"空过，见 ARCHITECTURE D13）
- 发布前另过一道 `check_publishable.py <成片.mp4>`：它不审版式，只照 `aigc.json` 核 ①② 在不在，
  ③ 按姿态文件决定打不打 `--declaration 内容由AI生成`（关着就打警告 + 要求留痕；退出码 1 = 这份东西不许发）

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
    aigc_label: none             # ⛔ 同上 —— 已由 v004（同脚本 + AIGC 标识）取代，发布用 v004
  - id: probe-aigc
    topic_id: null               # 不是新闻成片，是 AIGC 标识端到端验证探针（2 镜）
    template: news-coral
    render_status: done
    output: .harness-news-runtime/videos/aigc-e2e/final.mp4
    spec: 1080×1920 / 11.9s / 1.01MB + aigc.json + contact-sheet.jpg
    aigc_label: verified         # ✅ 角标字芯实测 62px(≥54px 线)，元数据 ffprobe format_tags 读回一致
  - id: v004
    topic_id: t001
    template: news-coral
    render_status: done
    output: .harness-news-runtime/videos/t001-v4/final.mp4
    spec: 1080×1920 / 59.3s / 1.97MB / 字幕轨 14 条 + aigc.json + contact-sheet.jpg + build.log
    voice: zh-CN-XiaoxiaoNeural
    aigc_label: verified         # ✅ 三处独立核验：① 元数据 ffprobe format_tags 读回（自证之外再查一次）
                                 #    ② 左上角 560×90 亮像素 5s/30s/55s 恒定 12.8k → 角标贯穿全片
                                 #    ③ 裁图目视 = 「AI 生成合成内容」白字黑边
    caveat: ContentProducer 用的是默认值 harness-news-pathb；真要发布前先定**主体名**再用
            `--aigc-producer <主体名>` 重渲一次（GB 45438-2025 要求可追溯到发布主体）
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
    blocker: 一把锁 —— 抖音账号未登录（`sau douyin check` 返回 valid 前不发）。原第二把锁
             「t001 成片无 AIGC 标识」已于 09-29 12:09 解除：v004 = 同脚本重渲 + 标识三件套，独立核验通过
    note: 发布走 upload-video 时必须带 `--declaration 内容由AI生成`，成功凭据是日志出现
          `自主声明已选择「…」`（上游失败只 warning、不阻断）。发之前先跑
          `python skills/douyin-pro/scripts/check_publishable.py <成片>`，它会把这条参数连命令一起打出来。
          ⚠️ 本 note 与 2026-09-29 起的姿态冲突时以**闸门输出**为准：`aigc-mode.json` 现在写
          `declaration=undeclared`，闸门只打警告、不给必带参数 —— 要照本 note 带声明，就给闸门加
          `--require-declaration`（单次）或把姿态改回 `required`（长期）。
          发布前还有一件人定的事：
          把 `--aigc-producer` 换成真实主体名重渲（见 v004.caveat）。发布主路径已接入
          （skills/douyin-upload + 本机 .venv/Scripts/sau.exe，见其 references/local-env.md）

## Last updated
last_updated: 2026-09-29
