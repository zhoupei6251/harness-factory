# news-coral — 版式包使用说明

配套代码: `skills/douyin-pro/scripts/path_b_build.py` (发射器) +
`skills/douyin-pro/scripts/layout_selfcheck.py` (结构自检)。

**分工**: 本文件讲"怎么用 / 怎么加"。每一个色值、字号、时长常数的出处都在
**`frame.md`**（唯一 token 源 + 版面法则），两边不重复内容，只互相引用。

---

## 1. 包内文件

```
news-coral/
├── frame.md            # 色板 / 字阶 / 版面法则 / 动量预算 / 地面清单
├── host.html           # 宿主骨架: 只有 #root、.clip、audio 零尺寸规则 + 6 个占位符
└── compositions/       # 7 个子合成, 每个都是自含的 <template> 文件
    ├── hook.html       nc-hook      墨底 开场钩子(首镜)
    ├── stat.html       nc-stat      纸底 单个巨号数字 + 对比块
    ├── rail.html       nc-rail      纸底 三行"标签→事实"脊线
    ├── quote.html      nc-quote     深纸底 引文卡
    ├── catalog.html    nc-catalog   墨底 三步清单
    ├── story.html      nc-story     双地面 叙事节拍(领句+屏句)
    └── closer.html     nc-closer    墨底 行动收口(末镜)
```

跑一条成片:

```bash
python skills/douyin-pro/scripts/path_b_build.py --input .harness-news-runtime/articles/t001-scenes.json --style news-coral --source 新闻拆解 --gpu --quality=delivery --fps=30 --output .harness-news-runtime/videos/t001-v3/final.mp4
```

输入吃两种形态，同一个选题必须两边一致：`.json`（**权威稿**：逐镜点名 `layout`，`屏句` 写
在 `"onscreen"` 键里）与 `.md`（标题行 / 正文 / `屏:` 行，版式由 `choose_layout` 竞选）。
t001 的两份稿子在 `.harness-news-runtime/articles/`。

只想验证发射与门禁（不渲染，约 1 分钟）:

```bash
python skills/douyin-pro/scripts/path_b_build.py --input <脚本> --style news-coral --source <署名> --check-only --work-dir <目录>
```

## 2. 变量契约（发射器 ↔ 版式的接口）

契约写在版式 `<html data-composition-variables="[...]">` 上，**发射器不读注释、只读这份 JSON**。
每个变量必须由下面四类来源之一填出来，填不出来就停机或换版式，绝不拿 `default` 冒充事实：

| 来源 | 变量 | 规则 |
|---|---|---|
| **时间** | `slotSeconds` | = 该镜配音实测时长（`emit_mount` 强制注入，契约 `min:1` 与 `MIN_SLOT_SECONDS` 两头一致） |
| **镜号** | `ordinal` | = `f"{shot_no:02d}"`，只出现在壁纸位（法则 4） |
| **事实** | `value/unit/label`、`compareValue/compareUnit/compareLabel`、`itemNLabel/itemNValue`、`stepNLabel/stepNBody` | 由 `DERIVERS` 从分镜原文里**摘**（数字必须带单位、小标题含自身数字即拒收）；摘不出 → `None` → 该版式判为"填不满" |
| **作者原话** | `onscreen`（屏句）、`title`（story 领句）、`quoteBody` | 只认作者写的 `屏:` 行 / 标题行 / `quote` 键。**绝不从被配音念的正文里取整句上屏**（frame.md 法则 6，判据 5 的结构保证）；没写 → story/hook 辅助行/closer 行动句整类落选，由条目或数字版式接手 |
| **署名** | `attribution`、`channel` | 只认 JSON 里的 `attribution`/`source`、CLI `--source`、或正文破折号后的落款。**发射器不会自己编频道名** |
| **设计词** | `kicker`、`title`（仅 `rail`/`catalog` 的小节标签位，见 `TITLE_LABEL_LAYOUTS`）、`tone` | 允许回落到版式自带 `default`（它们是栏目眉标/小节标签这类版式词汇），回落时值来自 `layout_default()`。story 的 `title` **不在这类**——它是领句，回落预览词就是替新闻下结论 |

数字类为什么需要单位：`NUMBER_UNIT_RE` 把"42万 / 21年 / 3700元"这类"数字+中文单位"当成一个事实；
`stat` 的两个数字若有一个在原句里找不到独立小标题，就不选 `stat`（法则 5）。

各版式实际声明的变量清单由代码生成，不手抄：

```bash
python .harness-news-runtime/tmp/probe_contracts.py
```

## 3. 挂载格式（发射器写进 `index.html` 的东西）

画面（`MOUNT_TPL`，每镜一条，**1 轨**）：

```html
<div id="shot-3" class="clip" data-composition-id="nc-catalog"
     data-composition-src="compositions/catalog.html"
     data-variable-values="{&quot;kicker&quot;:&quot;…&quot;,…}"
     data-start="25.3" data-duration="13.1" data-track-index="1"
     data-width="1080" data-height="1920"></div>
```

配音（`AUDIO_TPL`，每镜一条，**0 轨**，与画面**同一起点**、终点早 0.05s）：

```html
<audio id="voice-3" src="scene_3.mp3" data-start="23.688" data-duration="13.078"
       data-track-index="0" data-volume="1"></audio>
```

- 配音窗比画面窗（同一镜 `data-duration="13.128"`）短 `AUDIO_MOUNT_HEADROOM_SECONDS`：
  引擎自己把 `data-start + data-duration` 做浮点加法算终点，严丝合缝的相邻窗会因
  `1e-15` 的进位被判成叠放（`duplicate_audio_track`）——见 §7 偏离 k。

- `data-variable-values` 是 `json.dumps(..., ensure_ascii=False)` 再 `html.escape(quote=True)`；
  逐实例传值 ⇒ 同一个 layout 挂 N 次、每次内容不同（子合成契约要求）。
- 挂 `<audio>` 不是渲染需要，是**工程一致性**需要：`hyperframes check` 的
  `audio_file_without_element` 判据认为"目录里躺着 mp3 而合成里一个 `<audio>` 都没有"= 链路外补声音。
  成片的声音仍然只来自拼接后的 `narration.mp3`（`mux_and_burn` 用 `-map 0:v:0 -map 1:a:0` 明说）。
- 宿主占位符共 6 个（`HOST_PLACEHOLDERS`）：`COMPOSITION_ID / W / H / TOTAL / SCENES / AUDIOS`。
  `emit_host()` 填完后会**数标记**：`data-composition-src="compositions/` 的出现次数必须等于挂载条数，
  `<audio id="voice-` 同理。曾因在 host 的 CSS 注释里写占位符原文而被复制进样式表，这条检查就是它的守卫。
  ⇒ **host 注释里永远不要写双花括号形式的占位符。**

## 4. 地面轮换（"三段混调"落地成机械规则）

`frame.md` §5 定了同一套系统换地面、不做三套 token。发射器里可判定的部分只有一条：

- 装包时从每个版式的 `#root { background: #rrggbb }` 解析地面色（`ROOT_GROUND_RE`），
  再用 `GROUND_TONE_BY_HEX` 归成 `light/dark`；**没登记过的色值直接停机**（不给静默退化留口子）。
- `emit_composition()` 逐镜记录"这一镜**实际**呈现的地面"：声明了 `tone` 契约的版式（现只有 `story`）
  用它填出来的值，其余用包自带的默认地面。
- `_tone()`：与上一镜相反；第一镜没有上一镜 ⇒ `light`。

**已知边界**：版式选择（`choose_layout`）不看地面，所以两个固定纸底版式相邻时会出现同面
（例如 `rail` 直接接 `stat` —— 两张纸贴在一起，第 4 镜的巨号数字失去"换了个场景"的提示）。
目前唯一能翻面的版式是 `story`（它声明 `tone` 契约），所以它在序列里就是**铰链**：稿子把
story 放在两张纸底版式中间，同面问题自动消失。t001-v3 实测序列
hook→rail→story→stat→closer = dark/light/**dark**/light/dark，正是第 3 镜翻墨底把
`rail` 与 `stat` 隔开。要让所有版式都能翻面，需要给每个版式补 `data-tone` 双地面并重新
验一对比度表，属于新增设计工作，未做。

## 5. 加一个版式（或换一套风格包）

新文件放 `compositions/<name>.html`，必须同时满足下面 5 条，缺一条就过不了自检或渲染：

1. 结构：`<html data-composition-variables="[…]">` + `<body><template>`，`template` 内根元素
   `id="root"` 且带 `data-composition-id="<cid>"`，脚本末尾 `window.__timelines["<cid>"] = tl;`
   —— 三处 id 必须一致（`CONTRACT_ID_MISMATCH` / `NO_ROOT_COMPOSITION_ID` / `NO_TIMELINE_REGISTER`）。
2. 地面：`#root` 写一条**不带属性选择器**的 `background: #rrggbb`，色值必须已在
   `GROUND_TONE_BY_HEX` 登记；新风格包则整张色板一起登记（`load_style_pack` 装包即校验）。
3. 变量：新变量名要么进 `DERIVERS`（精确 id → 推导器），要么符合 `INDEXED_VAR_RE`
   （`itemNLabel/itemNValue/stepNLabel/stepNBody`，自动注册）。名字取不到事实就别声明——
   声明了填不出来会在 `check-only` 阶段就暴露。
   作者写的话去哪，由发射器里三张名单管着，加版式时要在脑子里过一遍：
   `TITLE_LABEL_LAYOUTS`（只有 `rail`/`catalog` 允许把 `title` 当小节标签回落版式 `default`）、
   `TITLE_LANDING_VARS`（版式里真正吃标题的变量集合，含 hook 的 `headTop/headBottomLead/headAccent`；
   一个都不沾 ⇒ 发射器打「标题行没有落点」⚠，因为标题行不进配音，那句作者话会静默消失）、
   `HEAD_BREAK_CHARS`（标题断点只认 `｜`/标点与"数字+单位"，切不出合法断点就不进 `hook`）。
4. 动量：脚本里显式写 `INTRO_END = 1.5` / `MIN_DRIFT = 0.6`（`MAGIC_BUDGET_VALUE` 只认这两个名字），
   算出 `driftStart/driftDur`，并对内容容器留一段 `ease:"none"` 漂移（`MISSING_CONTINUOUS_MOTION` /
   `MISSING_DRIFT_DURATION`）。漂移禁止作用在带 `.clip` 的挂载元素上。
5. 排版：字号用 `cqw/cqh`（`PX_TYPOGRAPHY`，只有 `background/mask` 类属性允许 `px`）；
   底部 `20cqh` 留给字幕（`CAPTION_RESERVE_INTRUDED`；这个数是量出来的，见 `frame.md` 法则 1）；
   中文族（允许名单 `HF CJK` / `HF Serif CJK`）自己声明 `@font-face`，用到的中文族必须本文件有声明、
   声明里的 `local()` 候选必须至少一个在本机已装（`MISSING_CJK_FONT_FACE` /
   `CJK_FAMILY_USED_NOT_DECLARED` / `CJK_FONT_LOCAL_NOT_INSTALLED`）；拉丁显示族写裸名（`CANONICAL_FONT_LOCAL_OVERRIDE`）。

写完后每个 GSAP 目标都要有 `id`（法则 9），带 `background` 且压字的片块禁止 `opacity` 补间（法则 8）。
验收两条命令：`--check-only`（自检 + `check --strict`）与一次 `draft` 渲染看联络表。

## 6. 门禁（失败即停机，不降级）

| 阶段 | 命令/函数 | 判据 |
|---|---|---|
| 结构自检 | `gate_layout_selfcheck` → `layout_selfcheck.check_layout` | 17 条不变量，含 `SURFACE_OPACITY_TWEEN`、`MISSING_TWEEN_TARGET`、`PX_TYPOGRAPHY`、`CAPTION_RESERVE_INTRUDED`、`CONTRACT_ID_MISMATCH`、`MAGIC_BUDGET_VALUE` 等 |
| 引擎门禁 | `gate_hyperframes_check` → `npx -y hyperframes check . --strict --json --caption-zone=…` | lint / runtime / layout / motion / contrast 全部 0 error 0 warning（`--strict` 把 warning 升级为失败） |
| 动量审计 | `audit_motion` | 逐镜取后 1/4 帧间变化均值 ≥ `MIN_TAIL_MOTION = 0.002`（判据 3） |
| 人工比对 | `build_contact_sheet` → `contact-sheet.jpg` | 每镜尾段一帧拼贴（判据 6 的验收对象） |

自检的负样本留在 `.harness-news-runtime/tmp/selfcheck_bad/`（`replay_hook_chip.html` 复刻面上淡入、
`replay_rail_head.html` 复刻缺 `id`），用来证明规则码真能抓到这两类历史缺陷。

## 7. 与引擎文档/通用做法的偏离（都有实测理由）

| # | 偏离 | 原因 |
|---|---|---|
| a | 子合成写成**整份 HTML 文档 + `<template>`**（不是引擎示例里的裸片段） | 独立打开可预览；运行时只克隆 `<template>`，实测挂载/渲染一致 |
| b | 中文用自声明 `@font-face` 的 `"HF CJK"` + `local()` 六连 | 引擎自动供给只覆盖 18 个拉丁族，字体缓存里没有 `noto-sans-sc`；`font_family_without_font_face` 审计按文件走 ⇒ 每个版式自带一份 |
| c | 地面写在子合成的 `#root` 上（宿主 `#root` 只 `overflow:hidden`） | 宿主不画东西，逐镜换地面才不用换宿主 |
| d | `fitCqw()`、漂移预算计算在多个版式文件里各存一份 | 子合成必须自含（运行时不共享模块），这是引擎约束下的重复，非懒政 |
| e | `rail` / `catalog` 固定 3 行 | 变量契约是静态 JSON，无法声明可变行数；多于 3 条时发射器打 ⚠ 并说明几条没上屏 |
| f | 宿主写死 `.clip{position:absolute;inset:0}`、gsap 走 CDN `<script>`、`audio` 给零尺寸盒 | 挂载盒约定 + 子合成不自带 gsap + 配音行盒会撑高 `#root` 把画面顶偏 |
| g | 片块入场一律 `scaleX/scaleY`，不用 `opacity` | 法则 8 的实测：审计器按"前景不乘 alpha、自身背景乘 alpha 与地面混色"取样，淡入到 α≈0.72 时白片被合成成 `rgb(246,213,213)`，珊瑚字掉到 2.5:1 |
| h | 单位、小标题、频道名不许发射器代拟 | 编出来的就是假事实（法则 5 + `MIN_STAT_FACTS` + `_attribution` 只认出处） |
| i | 相邻镜地面取反，用**实际**地面而非镜号奇偶 | 固定地面版式会占掉某个奇偶位，实测出现"暗底 catalog 后接暗底 story" |
| j | host 注释里不写占位符原文 + `emit_host` 数标记 | `str.replace` 不分 CSS 注释，写过一次就把 5 条 clip 复制进样式表 |
| k | 配音窗终点比画面窗早 0.05s（不是同一条窗） | 引擎 `lintDuplicateAudioTracks` 自己做 `data-start + data-duration` 浮点加法求终点再判 `b.start < a.end`；实测 `11.88 + 11.808 = 23.688000000000002 > 23.688` ⇒ **严丝合缝**的相邻两窗被判成叠放，`duplicate_audio_track` 以 warning 触发，`--strict` 下就是渲染失败。留 50ms 余量（约一个 mp3 帧，24kHz/1152 样本 = 48ms）后不等式再也翻不过来；成片声音来自 `narration.mp3`，这一层只是工程一致性挂载 |

## 8. 排障速查（全部踩过）

| 症状 | 真实原因 | 处理 |
|---|---|---|
| `Invalid quality … Got "=delivery"` | `-q` 是短选项，引擎不给短选项剥 `=` | 写长形式 `--quality=delivery`（发射器已改） |
| 成片报 `narration.mp3 … No such file`，但拼接那步没报错 | `list.txt` 里写相对路径 ⇒ concat 按 list 自己的目录二次解析；且老代码把 stderr 丢 devnull 又不查返回码 | 条目只写文件名；拼接失败当场 `_ffmpeg_failure` 停机 |
| `audio_file_without_element` | 目录里有 mp3 而合成里没有 `<audio>` | 逐镜挂 0 轨 `<audio>`（已实现），别去关 lint |
| `GSAP target  not found.`（两个空格） | 被补间的元素漏 `id` | 法则 9；自检 `MISSING_TWEEN_TARGET` |
| `contrast_aa_failure` 只在某一帧出现 | 带底色的片块用 `opacity` 入场 | 法则 8，改 `scaleX` 擦入 |
| `index.html` 里挂载重复两份 | host 注释写了占位符原文 | 注释里只写不带 `{{}}` 的名字（`emit_host` 会拦住） |
| `stat` 永远选不上 | 数字没配单位，或同句两个数字共用整句标签 | `NUMBER_UNIT_RE` 收时间单位；`number_phrase()` 按小句给每个数字配独立标签 |
| 中文显示成宋体/方框 | 版式文件自己没声明 `@font-face` | 偏离 b；自检 `MISSING_CJK_FONT_FACE` |
| 中文**悄悄**降档（字体不像设计稿，但渲染不报错） | 正文用了没声明的中文族，或 `local()` 候选名本机一个都没装 | 2026-10-09 前的旧判定是子串（`"HF CJK" in block`），这两条**全绿放过**；现自检报 `CJK_FAMILY_USED_NOT_DECLARED` / `CJK_FONT_LOCAL_NOT_INSTALLED` |
| 拉丁显示族没下载 | 给 `League Gothic` 等加了 `local()` | 写裸族名（偏离 b 的另一面） |
| `duplicate_audio_track`：相邻两镜配音窗"重叠"（打印出来的却是 23.7 vs 23.688） | 引擎浮点相加算终点，`+2e-15` 让严格不等式成立（偏离 k） | 配音窗留 `AUDIO_MOUNT_HEADROOM_SECONDS`（已实现）。别去关 lint，也别给画面窗加缝——画面加了就是黑帧 |
| `check --strict` 说 1 warning 就拒渲染 | `--strict` 把 warning 升级为失败，本包按 0 error 0 warning 验收 | 读 `check.json` 的 `lint.findings[].code` 定位，别猜 |
| 发射打「分镜N 的标题行没有落点」⚠ | 作者写了标题行，但选中的版式（`stat`/`closer`/`quote`）没有标题位，而标题行不进配音 ⇒ 那句话既不上屏也不出声 | 并进正文，或点名带 `title` 的版式（`rail`/`catalog`/`story`，`hook` 由 `split_headline` 用它切主视觉） |
| story/hook/closer 报 `onscreen` 填不出来 | 该镜没写 `屏:` 行（JSON 里没有 `"onscreen"` 键） | 屏句只能作者给；发射器不许从被念的正文里挑整句上屏（判据 5 的结构保证） |
| `hook` 选不上，缺的是 `headAccent` | 标题里既没有"数字+单位"也没有 `｜` ⇒ 没有合法断点 | 旧实现兜底切 `text[-4:]`，会把珊瑚片切进词中间（"困住半辈子"→墨"困"+片"住半辈子"）；现在改为不进 hook。给标题补一个可断的落点，或让 `｜` 落在你要强调的词前 |
| 某一镜的珊瑚片颜色不对/字被吃掉 | `title` 的两种身份被混用：story 的领句 vs `rail`/`catalog` 的小节标签 | 回落只允许发生在 `TITLE_LABEL_LAYOUTS` 里那两个版式；领句必须作者写 |
