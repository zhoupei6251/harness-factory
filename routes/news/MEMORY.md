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
| researching | news-collect（采集线索，零成本）→ **news-curate（台账去重 + 免费热度排序，产出带理由的候选清单；⚠STALE 陈旧不当日新闻、⚠REVIEW 疑似已发需人工确认）** → hot-topic-content-maker（选题裁决；**付费热榜查询本域禁用**）|
| drafting | media-short-video-copy / viral-script-writer |
| fact_check | fact-check（必须，不可跳过）|
| rendering | douyin-pro（Path B only：`--template <pack>`；交付轨自带元数据隐式标识，画面显式角标由渲染档决定 —— full 烧、no-badge 不烧，见 D14）|
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

## 模板决策树（32 个 pack，数量现算见 D20）

按稿件特征词选视觉气质。t001（拾荒老人）= 人物故事型 → `news-coral`。

**32/32 全部可渲染**（2026-10-08 实测，本节原写的「2/12 可渲染 + 其余 10 包仅占位」
以及「18 个派生变体骨架未独立填实」**均已作废**）：每个包 `compositions/` 7 个真 composition、
`placeholder.html` 全删、`load_style_pack` 32/32 成功、
`layout_selfcheck.py` 32 包 234 文件 0 违规。20 个派生变体已补 `frame.md`（含 `derived_from` 派生声明）。

> ⚠️ 改色板用色时：`audit_pack_contrast.py` 口径是「本包色板 ∪ 共享 token 层」，
> `SHARED_TOKENS` 不许手抄（用 `shared_tokens_need_review()` 核对）；`#root` 地面色另受
> `GROUND_TONE_BY_HEX` 约束，改它等于改整片的底（D18/D19）。

| 触发词 | pack | 视觉气质 |
|---|---|---|
| 故事 / 人物 / 感人 / 心酸 / 老人 / 孩子 | `news-coral` （主） | （master · 主气质） |
|  | `news-coral-night` （主） | coral 基调 · 夜店感深红（深蓝黑底 + 暗红强调） |
|  | `news-coral-mono` （主） | coral 基调 · 单色灰（去饱和） |
|  | `news-mosaic` （备） | coral 基调 · 马赛克拼贴（多色块） |
|  | `news-dusk` （备） | coral 基调 · 黄昏紫 |
| 调查 / 揭露 / 卧底 / 追踪 / 暗访 / 曝光 | `news-ink` （主） | （master · 主气质） |
|  | `news-ink-graphite` （主） | ink 基调 · 墨石墨（更冷的黑） |
|  | `news-noir` （备） | coral 基调 · 黑色（纯黑） |
| 新规 / 政策 / 办法 / 通知 / 施行 / 印发 | `news-policy` （主） | （master · 主气质） |
|  | `news-policy-bold` （主） | policy 基调 · 政策加粗（高对比蓝） |
|  | `news-paper` （备） | ink 基调 · 报纸白底 |
| 排行 / TOP / 同比 / 指数 / 榜单 / 数据 | `news-stat` （主） | （master · 主气质） |
|  | `news-stat-grid` （主） | stat 基调 · 数据网格 |
| 突发 / 现场 / 直击 / 抢险 / 灾害 / 地震 | `news-onsite` （主） | （master · 主气质） |
|  | `news-onsite-urgent` （主） | onsite 基调 · 现场紧急（琥珀警示） |
| 速报 / 整点 / 合辑 / 盘点 / 一句话 / 多条新闻 | `news-bulletin` （主） | （master · 主气质） |
|  | `news-bulletin-strip` （主） | bulletin 基调 · 速报条状 |
| 为什么 / 原理 / 科普 / 图解 / 什么是 / 冷知识 | `news-explainer` （主） | （master · 主气质） |
|  | `news-explainer-blueprint` （主） | explainer 基调 · 科普蓝图（亮蓝） |
| 紧急 / 务必 / 预警 / 小心 / 骗局 / 诈骗 | `news-alert` （主） | （master · 主气质） |
|  | `news-alert-warning` （主） | alert 基调 · 警示警告（黄三角） |
| 纪念 / 致敬 / 清明 / 国庆 / 追忆 / 缅怀 | `news-thread` （主） | （master · 主气质） |
|  | `news-thread-tribute` （主） | thread 基调 · 致敬专题（金） |
| 观点 / 专栏 / 我观察 / 评论 / 思考 / 认为 | `news-takes` （主） | （master · 主气质） |
|  | `news-takes-column` （主） | takes 基调 · 观点专栏（深靛） |
|  | `news-podcast` （备） | coral 基调 · 播客紫 |
| 比赛 / 比分 / 进球 / 加时 / 绝杀 / 世界杯 | `news-blast` （主） | （master · 主气质） |
|  | `news-blast-score` （主） | blast 基调 · 比分（绿） |
| 战况 / 外交 / 国际 / 边境 / 联合国 / 乌克兰 | `news-world` （主） | （master · 主气质） |
|  | `news-world-globe` （主） | world 基调 · 国际地球（亮蓝） |
| 反差 / 极简 / 黑白 / 强烈对比 / 反差感 / 对比 | `news-polarity` （主） | alert 基调 · 极端对比（纯黑白橙） |
| 拂晓 / 晨光 / 温暖 / 希望 / 新生 / 清晨 | `news-dawn` （主） | coral 基调 · 拂晓暖橙 |

> **自动决策工具**（推荐，省得自己查表）：`python routes/news/scripts/decide_pack.py "<热点关键词>"`
> 输出推荐 pack + 备选 + 理由，并按 `--length` 给镜数。详见 `routes/news/pack-decision.md`
> （全表 + 关键词分类 + 长度 → 镜数）。它的 pack 集合与真实模板的一致性由
> `skills/news-curate/scripts/curate_selftest.py` 的 `t_decide_pack_covers_every_real_template` 锁。

**派生变体填实流程**（已全部完成，这里留作新增变体时的做法）：
1. 选气质，参考同 master 的 7 个真版式
2. 写 host.html + frame.md（可跑 `routes/news/scripts/gen_variant_frames.py` 按真实用色生成色板表
   + `derived_from` 派生声明；**不要手抄对比度表**，那是 D10 的事故源）
3. 7 个 comp 各写一个 .html，先落 `AUTO_LAYOUT_STEMS` 那 7 个词干（hook/closer/story/stat/quote/catalog/rail）
4. `python skills/douyin-pro/scripts/path_b_selftest.py` + `audit_pack_contrast.py` 必绿
5. 真渲一镜测试，`check --strict` 必须 0 errors / 0 warnings

**填实流程**(1 个真 pack 成本 ≈ 半天-1 轮:7 comp × ~200 行 + host + 契约 + 调色板 + 渲染验证):
1. 选气质,参考 news-coral 的 7 comp 真版式作参考
2. 写 host.html + frame.md(同 news-coral 骨架,换 ground/accent)
3. 7 个 comp 各写一个 .html,内含契约 + 真 ground(已在 GROUND_TONE_BY_HEX 调色板内)
4. 加 `--template <新名>` 跑 check-only 验证
5. 真渲一镜测试,check --strict 必须 0/0
6. MEMORY.md 在本表里把 ⏳ 改为 ✅ 并加 spec 链接

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
  `--aigc-label`（默认 `AI 生成合成内容`）是显式角标文字。**② 元数据两档交付轨都不许留空**：
  空 producer → 停机；全片时长 < 2 秒且真要烧角标 → 停机。① 角标自 D14 起可以按开关不烧（见下条），
  但"什么标识都没有又可发布"这份东西不存在。
- **标识开关有两处，代价一侧是"发不出去"、另一侧是"③ 必带"**（2026-09-29 用户口径：先要开关、同日定
  「还是默认都打开」、同日再改「先帮我把两开关先关了吧」、最后对无法核实的删码请求改选
  「判据放宽：交付件可以不带 ①」）。代码默认永远全开，**"现在关着"落在姿态文件**
  `routes/news/aigc-mode.json`（裁决顺序 **旗标 > 姿态文件 > 代码默认**，见 ARCHITECTURE D11/D12/D14）：
  ① 渲染层三档 `--deliver` / `--no-badge` / `--draft`（只能挑一个，两个同时给 = 报错）——
  `full` 烧 ① + 写 ②；`no-badge`（D14 新增）只写 ②、产物**可发布**，代价是 ③ 从此必带；
  `draft` ①② 都不做、侧车只落 `draft` 一段（**不含** `explicit` / `metadata_key` / `implicit`，
  缺什么记什么缺，不写一堆 false 装作"标识在只是没开"），读到即 EXIT=1。
  no-badge 的台账反过来是"关了什么记什么关"：`explicit` 段必须存在，写 `burned_in: false` +
  `disabled_by` 真出处 + `to_enable` 回退写法。② 发布层 `--allow-undeclared` / 姿态
  `declaration=undeclared` —— 不带平台自主声明仍然放行，但会打警告并要求在 `videos[].declaration`
  留痕，反向旗标 `--require-declaration`；**① 没烧的产物不认这个关法**，闸门照样 EXIT=1。
- **当前姿态（2026-09-29 起，D14 落地后）**：`render=no-badge` · `declaration=required`。
  直接后果：**默认渲出来的每一份都是可发布交付件**（无 ① 角标、② 元数据在读回），发布命令必须带
  `--declaration 内容由AI生成`；要把 ① 烧回画面上就加 `--deliver`（或把 `render` 改回 `full`）。
  这一档**买不到**"什么都不用说"：画面没标、② 过抖音转码即失，③ 是唯一活到平台侧的那一件，
  所以 `declaration` 不能是 `undeclared` —— 用户先前关掉的第二个开关在这一档被判据重新打开，
  这是所选方案的既有条件。回退：`aigc-mode.json` 的 `render` 改 `full`、或删掉该文件（代码默认全开）。
- 成片旁必落 `aigc.json` 侧车（font_size_px / glyph_height_px / short_side_px / margin_v_px /
  position / shown_seconds / 七要素），发布前用它 + `contact-sheet.jpg` **第 1 镜**人工核一遍
  左下角标 —— 角标只在开场 4 秒常驻，看后面的镜头当然看不到，这不是缺陷。

当前进度 (frame.md / host.html / compositions 齐全度)：
- **32/32 全部完整**（2026-10-08 实测推翻原「2/12」记录，D15）：12 master + 20 派生变体，
  每个包 `frame + host + 7 个真 compositions`，`placeholder.html` 全删
- 20 个派生变体已补 `frame.md`（含 `derived_from` 派生声明，`gen_variant_frames.py` 生成）
- 校验（三道闸，仓库根执行）：`path_b_selftest.py`（**项数以脚本末行输出为准，别在文档里抄数**；覆盖
  AIGC 标识、三档渲染（full / no-badge / draft）、发布闸门判据与姿态文件、共享 token 层校准、色板复算、版式词表，以及三道闸各自的
  假绿负例）+ `audit_pack_contrast.py`（32 pack 色板/对比度复算；**仍有 24 条 OFF_PALETTE_HEX 是刻意保留的**，
  自动换色会让对比度从 ~16:1 掉到 ~1.1:1，该补进 frame.md 算设计补全而非改色，见 D19）+
  `layout_selfcheck.py <pack 目录…>`（17 条结构不变量；**参数是含 `compositions/*.html` 的目录不是包名** ——
  传进去而里面没有版式文件现在当场 exit 1 并点名该目录，不再"0 个文件 0 条违规"空过，见 ARCHITECTURE D13）
- 发布前另过一道 `check_publishable.py <成片.mp4>`：它不审版式，只照 `aigc.json` 核「② 在 + ① 有交代」（D14 判据），
  ③ 按姿态文件决定打不打 `--declaration 内容由AI生成`（① 烧着时关着 = 警告 + 要求留痕；**① 没烧时不给关**，
  `undeclared` 与 `--allow-undeclared` 都 EXIT=1；退出码 1 = 这份东西不许发）

## Videos
videos:
  - id: v001
    topic_id: t001
    template: news-coral         # 32 个 pack 之一 (见上方决策树)
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
  - id: photo-probe
    topic_id: null               # 不是新闻成片, 是 Phase 1(commons_media 接线)端到端探针, 4 镜
    template: news-coral
    render_status: done
    output: .harness-news-runtime/videos/photo-probe/final.mp4
    spec: 1080x1920 / 33.0s / 2.6MB / aigc.json + contact-sheet.jpg + media-credits.json
    aigc_label: verified         # ② 元数据读回一致; ① 按姿态 no-badge 不烧, 发布须带 ③
    note: Phase 1 已接线完成 (2026-09-29) —— 每镜可选一张 Wikimedia Commons 真实图:
          scene 写 "image": "查询词" 取图, "image": false 显式弃图, 不写则回落 kicker。
          授权闸沿用 commons_media(拒 SA/NC/ND/GFDL); 取图失败一律降级为无图, 绝不停机。
          成片旁 media-credits.json 是授权/署名台账 —— CC BY 图发布时简介必须带它。
          已接图板的版式: news-coral 全部 7 个(hook/story/stat/quote/catalog/rail/closer);
          其余 31 pack 图板未接(2026-10-08 实测: 32/32 都有真版式, 但只有 news-coral 接了 .xx-photo 图板), 补图板时按同一套模式接。
  - id: v005
    topic_id: t001
    template: news-coral
    render_status: done
    output: .harness-news-runtime/videos/t001-v5/final.mp4
    spec: 1080×1920 / 60.3s / 2.76MB / 字幕轨 14 条 + aigc.json + contact-sheet.jpg + build.log + media-credits.json
    voice: zh-CN-XiaoxiaoNeural
    aigc_label: verified         # ② 元数据读回一致; ① 按姿态 no-badge 不烧, 发布须带 ③
    note: 首条**真实图**成片 (2026-09-30) —— 4/5 镜 Wikimedia Commons 真实图(CC0×2 / CC BY×1 / PD×1),
          镜3 banknote 无合规结果正常降级为无图。输入 t001-scenes.json 显式编排(kicker×5 + rail items×3
          + stat 六元组)复刻 v004 版式序列 hook→rail→story→stat→closer。**教训**: md 被重写成两个长句后
          自动切分只出 2 条目, rail 按闸拒绝 —— 不是回归, 是输入丢了编排; 显式 items/layout 才是正路。
          授权台账 media-credits.json 跟片归档 —— CC BY 3.0(镜2 废弃工厂)发布时简介必须署名。
  - id: v006
    topic_id: t001
    template: news-coral
    render_status: done
    output: .harness-news-runtime/videos/t001-v6/final.mp4
    spec: 1080×1920 / 60.3s / 5.13MB / 字幕轨 14 条 + aigc.json + contact-sheet.jpg + build.log + media-credits.json
    voice: zh-CN-XiaoxiaoNeural
    aigc_label: verified         # ② 元数据读回一致; ① 按姿态 no-badge 不烧, 发布须带 ③
    note: 首条**单镜像cinematic化**样板 (2026-09-30) —— hook.html 改满屏背景图(白框→z=0 全屏)+Ken Burns push in(scale 1.0→1.06)+
          黑色渐变 mask(图作底)+credit 移出 figure 破除 stacking context+screen 上署名(7 字符作者·许可证)。
          其它 4 镜仍 v005 白框贴图。教训: CSS 注释里含 `<script>` 会让 HTML parser 关 <style>, 导致 check 报
          `A <style> block is never closed` —— 注释里用纯文字或 `&lt;script&gt;`。
  - id: v007
    topic_id: t001
    template: news-coral
    render_status: done
    output: .harness-news-runtime/videos/t001-v7/final.mp4
    spec: 1080×1920 / 60.3s / 视频 + aigc.json + contact-sheet.jpg + build.log + media-credits.json
    voice: zh-CN-XiaoxiaoNeural
    aigc_label: verified         # ② 元数据读回一致; ① 按姿态 no-badge 不烧, 发布须带 ③
    note: **全 5 镜 cinematic 化** (2026-09-30) —— v006 的 hook 样板推广到 rail/catalog/closer/quote/story/stat 全部 7 个 composition。
          共性改造: 满屏背景图 + ::before 黑色渐变 mask + Ken Burns push in + credit 移出 figure。
          通用 rule (`#root > *:not([class$="-photo"]):not([class$="-photo-credit"])`) 提升 z-index 到 1 + text-shadow。
          `.has-photo` 下各 wrapper 改浅色 + 对比度临界 selector(rl-no/st-eb/st-lab/st-unit/cl-ch/rl-lb) 加 padding 黑底+改 opacity 入场为 scaleX(SURFACE_OPACITY_TWEEN)。
          4/5 镜带真实图(镜3 banknote 仍无合规降级)。path_b check --strict 0 errors/0 warnings。
          教训: **mask 是 stacking 上层不算 contrast 下层**——亮底图上浅文字必须自带 padding 黑底才能过 3:1 WCAG AA;
  - id: v008
    topic_id: t001
    template: news-coral-night         # 【历史记录, 当时 30 pack】第 2 个真 cinematic 包
    render_status: done
    output: .harness-news-runtime/videos/t001-v8/final.mp4
    spec: 1080×1920 / 60.3s / 视频 + aigc.json + contact-sheet.jpg + build.log + media-credits.json
    voice: zh-CN-XiaoxiaoNeural
    aigc_label: verified         # ② 元数据读回一致; ① 按姿态 no-badge 不烧, 发布须带 ③
    note: 【历史记录】**当时的 30 pack 系统接入 + 1 个真变体** (2026-09-30) —— ALL_TEMPLATES 12→30 (12 master + 12 派生变体 + 6 主题包); 2026-10-08 起为 32 个, 见 D15/D20;
          GROUND_TONE_BY_HEX 自动扩展 +49 个 ground 色; 28 个新 pack 骨架 (host + 7 placeholder comp) 批量生成。
          news-coral-night = 从 news-coral 完整复制 7 comp + host, 替换 ground (#1a1a1a→#0a0a0d / #f5f0e8→#ece8df) +
          accent (#e85d5d→#c0392b 暗红), data-composition-id 加 `night-` 前缀。check --strict 0/0, 4/5 镜真实图。
          视觉差异: 整体偏冷、夜店感更强(深蓝黑底 + 暗红强调)。**剩余变体已于 2026-10-08 全部填实**
          （实测 32/32 全部有 7 个真版式、load 32/32 成功，见"模板决策树"段的 D15 说明）。
          填实流程见「模板决策树」段尾(每 pack ≈ 半天)。
          **文字 inline opacity 入场 + 自带 background 会触发 SURFACE_OPACITY_TWEEN** —— 改 scaleX。
          同样教训见 v005 note 的「code-side vs data-side」, cinematic 化是「设计层数据」(版式细节),不是「内容层数据」——
          12 模版独立 7 composition × 12 = 84 静态文件 + 30 模版计划意味着 ~210 文件手工设计,后续单独 brainstorm 模版扩展策略。
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
          2026-09-29 D14 后本 note 与姿态**一致**：`aigc-mode.json` 写 `render=no-badge ·
          declaration=required`，默认渲出的即无 ① 角标的可发布交付件，③ 必带。两条要记住的边界：
          ① 姿态若被改成 `declaration=undeclared`，闸门对这类台账**不静默放行**而是 EXIT=1 并打三条出路
          （画面没标时 ③ 是唯一活到平台侧的那一件）；② 想要 ① 回到画面上就加 `--deliver` 重渲，
          旧 v004 那份带角标的成片仍是 ①② 齐活，闸门对它照常打 ③ 必带参数。
          发布前还有一件人定的事：
          把 `--aigc-producer` 换成真实主体名重渲（见 v004.caveat）。发布主路径已接入
          （skills/douyin-upload + 本机 .venv/Scripts/sau.exe，见其 references/local-env.md）

## Last updated
last_updated: 2026-09-29
