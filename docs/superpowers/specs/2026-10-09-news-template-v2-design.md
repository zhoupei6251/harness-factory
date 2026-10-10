# 新闻域模板 v2 设计（31 套同等质量 · 原语库 + 配方编译 · 字幕进体系）

> 日期：2026-10-09 ｜ 状态：设计已批准，待用户复审 → 转实施计划
> 路线：方案 B（视觉原语库 + 风格 spec 编译）；方案 A（token 注入）与方案 C（31 套全手工）已否决
> 上游背景：`skills/douyin-pro/templates/hyperframes_path_b/`（现存 31 包；原 32 包，2026-10-09 删 `news-coral-night`，理由见裁决 15 与 `routes/news/ARCHITECTURE.md` D23）、`routes/news/pack-decision.md`（12 体裁路由）
> 关联：提速设计 `2026-10-09-news-render-speedup-design.md`（本设计不得使单条摊薄时长退化超过其阈值）

---

## 1. 目标与验收口径

**目标**：把新闻域出片的视觉水位从"模板感/PPT 感"提升到"信息流原生、能打完播率"的水平，产出 **31 套同等质量、每套都能独立上片**的模板包。

**验收口径（全部可机判，除第 1 项）**：

| # | 判据 | 口径 |
|---|---|---|
| 1 | 审美水位 | **人工判断**：P1 旗舰包出帧，与老包**同稿并排**比对，用户认可后放行 |
| 2 | `hyperframes check --strict` | 全绿，零违规 |
| 3 | 编译前色对预校验 | spec 声明的每个文字/底色对 WCAG 达标（正文 4.5 / 大字 3.0），不过即拒编 |
| 4a | 画面确定性 | 同稿渲染两次，**视频流哈希**一致（P0-4 实测：改造前即成立） |
| 4b | 音频确定性 | 同稿渲染两次，逐镜 mp3 **时长**（ffprobe）一致；P2 起再加一项：落盘的 `cues.json` 一致 |
| 5 | 区分度门禁 | 任意两套之间，`grid.grammar` / `type.display` / `motion.signature` / `color.value-ladder` 四项**至少两项不同** |
| 6 | 渲染时长 | 以提速项目所立 `timing.json` 基线为准；旗舰包单条摊薄 > 基线 ×1.5 → 停止并回报 |
| 7 | 合规门禁 | 含可辨认人脸的图不得进入首镜 / closer / 人物镜 / 含专名镜 |

**判据 5 是这份设计里最重要的一条新增**。它把"别做成模板感"从主观愿望变成一个编译期可拒的断言——31 套塌回一套，历史上发生过（见 §3），必须有闸。与裁决 6 咬合后有一条算术后果：**4 变体族的三轴选参只能取偶校验排布**，详见 §6.1「P1 实施记录」第四条——P5 铺 31 套时这是硬约束，不是审美建议。

**判据 4 在 P0-4 后被拆成 4a/4b**（原口径"整支 `final.mp4` 哈希一致"**永红**）。P0-4 三层归因：两次渲染的 `index.html` 与全部合成文件逐字节相同、逐镜 mp3 **时长**相同，但 mp3 **字节**不同（edge-tts 每次重新编码，非确定性；当前发射器无字节缓存，`synthesize_audio()` 每次都现问服务），于是容器哈希必然不同；把 `silent.mp4` 拆流后**视频流哈希两次一致**、音频流不一致。结论是确定性只能对画面立约，音频侧改立"时长一致"这种弱一档但仍可机判的口径，P2 再用 `cues.json` 落盘把外部时序不确定性固化成可复现输入。证据：`routes/news/evidence/2026-10-09-template-v2-p0-probes.md`。

## 2. 非目标（本轮不做）

- **不做真实素材源接入**（正版图库 API / AI 生图 / 人工传图）。本轮只在 Commons 现状下把图降级为纹理 + 加合规门禁。
- **不动 AIGC 角标**。它的 5% 最短边字高有实测字面率 0.729 校准（`aigc_badge_font_size`），迁进 HTML 等于重做一遍已通过的国标验证，纯亏。
- **不改 `hyperframes` 引擎本身**。`check --strict` 是外部黑盒，我们只适配它。
- **不做老包升级**。现存 31 包整体归档（原 32，删除见裁决 15），新体系另落 `hyperframes_path_c/`。
- **不引入 GSAP 插件**（见裁决 10）。

## 3. 现状诊断（实测证据，非印象）

> **测量时点**：下表全部数字取自 32 包状态（2026-10-08/09）。2026-10-09 删掉 `news-coral-night` 后现存 31 包（裁决 15 / D23）。**删除后复跑 `audit_pack_contrast.py`：仍是 24 条 OFF_PALETTE_HEX、仍是同样 10 个包**（与 D19 记的 32 包基线同数，且被删的包不在其中），所以下表 D1/D2 的结论不因删除而失效 —— 被删的那个包恰好是"零独有色"的，删除只会让同质化判断更成立，不会更弱。

| # | 缺陷 | 证据 |
|---|---|---|
| D1 | **32 包共用同一个红**，连色都没换，只是换布局名 | `audit_pack_contrast.py:104` 实测：`#e85d5d` 在 32 包色板声明中出现 **32** 次、`#c0392b` **41** 次、`#d44a4a` **34** 次。同脚本 `:84` 给了更硬、不可辩驳的口径：**`#e85d5d` 命中 12/12 个 master 包色板**（作主强调）。注意前者数的是"声明次数"（一包多 token 可指向同色，故 >32 正常），只能看量级；后者才是"每包都有"的证据 |
| D2 | **同质被工具链制度化** | `SHARED_TOKEN_MIN_PACKS = 6`（D18, 2026-10-08）把 18 个色值提升为跨包共享层，`OFF_PALETTE_HEX` 从此放行。止血决策正确，副作用是审计器改为保护同质 |
| D3 | **动效词汇只有一个动作** | 7 版式全用 `scaleX/scaleY` 擦入 + `yPercent:-3` 漂移；`hook.html:224` 的逐字入场注释记录的是 `onStart` 里 split + `tl.from` —— **`onStart` 在 seek 时不触发、`from` 违反"一律 fromTo"**，该方案在 seek 模型下必然失步，撤掉是对的 |
| D4 | **首镜用真人照片构成错误指认** | `t001-v10/media-credits.json`：湖南常德拾荒者新闻的首镜满屏图 = 巴西累西腓拾荒者（`Wilfredor`/CC0，`relevance: 2`），**面部清晰可辨**；另三镜为废弃水泥厂齿轮（`relevance: 2`）、意大利造纸回收（`relevance: 1`）、智能手机（`relevance: 1`） |
| D5 | **字幕不在设计体系内**，且设计体系在为它让位 | `path_b_build.py:366-369` 静态 ASS（`h/32`=60px、描边 3px、两行封顶），ffmpeg 在 HyperFrames 之后烧；`frame.md` 法则 1 的底部 20cqh 禁入区 = 给未设计图层让位 |
| D6 | **色相打架** | `t001-v10` 抽帧第 1 格：蓝色火带与珊瑚红眉标片同框，两个高饱和无关色对撞。WCAG 审计管明度不管色相关系 |
| D7 | **中文只有一把 sans**，"杂志感"无从落地 | `frame.md §2` CJK 固定 `HF CJK`（Noto Sans SC）。而 `typography.csv` 中 `Chinese Traditional` / `Japanese Elegant` / `News Editorial` / `Magazine Style` / `Editorial Classic` **五条独立记录一致推荐衬线标题** |

## 4. 已锁裁决

| # | 裁决 | 依据 |
|---|---|---|
| 1 | 业务基准 = **信息流原生 + 完播率优先** | 用户选定 |
| 2 | **字幕收进 HyperFrames** 成为一级公民；AIGC 角标留 ASS | 用户选定 |
| 3 | **排版/图形为王，图只做纹理**（不追求电影感纪实） | 用户选定；且 D4 使满屏纪实路线不可信 |
| 4 | 架构 = **原语库 + 配方编译**（方案 B） | 31 套同等质量只有生成式系统能满足 |
| 5 | 规模 = **31 套 = 9 族 × 变体**，同等质量全可上片 | 用户硬性要求 |
| 6 | **族 = 版面语法差异；变体 = 语法内参数差异** | 反"模板感"的结构性保证 |
| 7 | **思源宋体进 CJK 族集合** | `NotoSerifSC-VF.ttf` 已装于 `C:\Windows\Fonts`，OFL 免费商用；D7 |
| 8 | **街采族保留，排在 P5 末位** | 手绘感参数化过头会退化为"卡通"，须待原语库被前八族磨稳 |
| 9 | **瑞士族 `drift: none` 例外**；`MIN_DRIFT` 由全局铁律降为族级默认值 | 该族性格即"不动的权威感" |
| 10 | **零 GSAP 插件依赖** | 见 §6.2；`RoughEase` 不在 CDN（404）且其内部随机本就摧毁确定性 |
| 11 | **审计上移到编译前**；事后审计降级为编译器回归测试 | `contrast_ratio()` 数学已在 Python（`audit_pack_contrast.py:155-177`），非重写。这是"审计只抓人、不抓编译器"的时序问题的解 |
| 12 | **`SHARED_TOKENS` 清空**：族间共享**角色**，不共享**色值** | D1/D2 |
| 13 | **强调色的明度是族级参数**（号外 `#DC2626` / 杂志 `#B45309` / 竞技 `#EF4444` / 警示 `#7F1D1D`） | `colors.csv` News/Media 推荐 `#DC2626`；现用 `#E85D5D` 是抬明度后的 breaking red，抬明度＝降冲击 |
| 14 | **双轨目录** `templates/hyperframes_path_c/`，老包原地归档 | `path_b_build.py` 2637 行同时服务产线；且新旧并存才能同稿并排判水位 |
| 15 | **老体系先减到 31：物理删除 `news-coral-night`**（2026-10-09 已执行，记录见 `ARCHITECTURE.md` D23） | 判据是"删掉后能力不减"，三条可复算：① 按 frame.md 色板 token 表算**独有色 = 0**（全库仅 4 个包为 0，另 3 个是 master，其中 `news-coral` 还是 `DEFAULT_STYLE`）；② 它的 13 色是其余 19 个包色板的**真子集**，即它没给系统带来任何一个色；③ 暗底能力由同派生的 `news-dusk`(`#7c3aed`) / `news-noir`(`#080808`) 承接，且 `news-dusk` 本来就在人物/故事的 `secondary` 里。反证也已记：`t001-v8` 用它真出过片，但删模板不动历史成片 |
| 16 | **渲染默认走软件光栅**（`--no-browser-gpu`），`--gpu` 降为显式排查开关 | 判据 4a 只在软件路径成立：硬件光栅两遍 1290 帧里编译包差 464 帧、存量包差 710 帧，流哈希也不同；软件两遍逐帧 md5 全同（`354ecc6f…` / `4e336c26…`）。代价实测有：render 段变慢（存量包 66.0/63.2s vs 硬件 40.9/36.2s），基线总时长离 102.9s 红线只剩 2% —— 确定性是门禁、时长只是预算，所以取前者。**"软件=确定"是实测相关不是机制解释**，未归因项留在 §11。数字见 `routes/news/evidence/2026-10-09-template-v2-p1-contract.md` §J4/§J6；批准形式是 owner 在 P1 决策门上说的"你继续铺吧"（2026-10-10），不是逐条点头，若日后判定代价不可接受即从此条改回，须连带重开判据 4a |
| 17 | **字幕层：词级只管入场，退场按整条 cue 一次做**（改 §6.4 原文的"每词两个 fromTo"） | 实测词 lifetime min 0.075s / 均 0.267–0.327s，词间空隙 max +0.575s ⇒ 逐词退场 = 屏上平均 0.3s 一跳 + 标点处必出半秒空窗，与裁决 1（完播率优先）正面冲突。词级数据仍照用：入场节奏、强调定位都吃它。数字与探针见 `routes/news/evidence/2026-10-10-template-v2-p2-captions.md` §K3；owner 选定"词级入场+整条退场"（2026-10-10） |

## 5. 9 族 / 31 套

切法：**族 = 网格语法 + 字体角色 + 动效词汇表**；变体 = 同语法内的色相关系、字重档、纹理密度。

| 族 | 网格语法 | CJK 标题 / 正文（本地已装） | 拉丁位（引擎自动供给） | 动效签名 | 禁忌（≥3，编译期断言） | 变体 |
|---|---|---|---|---|---|---|
| 号外 Neubrutalism | 粗黑描边包幅 + 45° 硬阴影 + 字压线 | 汉仪中黑 900 / 等线 | `Space Mono`·`League Gothic` | `expo.out`+`none`，`back.out(2.8)` 过冲，≤0.9s | 禁 fade；禁 `sine/power2`；禁 >1s 入场 | 4 |
| 杂志 Editorial | 非对称栏 + 首字下沉 + 大负空间 | **思源宋体 900** / Noto Sans SC 400 | `Playfair Display`·`EB Garamond` | `clip-path` 遮罩上涌 + 逐字 `y:14→0`，1.4s | 禁一切过冲；禁 <0.5s 入场；禁圆角 | 4 |
| 数据 Data-Dense | 数字主角 + 网格底纹 | Noto Sans SC 900 / 400 | `IBM Plex Mono`·`League Gothic` | 条形 `scaleX`、折线 `strokeDashoffset`、数字滚动 | 禁装饰动效抢数字；禁 >2 元素同动；禁假比例 | 4 |
| 街采 Anti-Polish | 手绘圈注 + 故意不对齐 | 等线 700 / 等线 | `Space Mono`（仅批注）⚠️ 见下注 | `strokeDashoffset` 圈注生长、马克笔带 ±1.5°、烘焙手抖 | 禁完美对齐；禁 `ease:"none"` 匀速；禁对称 | 3 |
| 胶片 Vintage Analog | 颗粒 + 漏光 + 暗角 + 白边 | **思源宋体 700** / Noto Sans SC | `Playfair Display`（仅 hero） | 遮罩 + 颗粒 opacity 抖 + zoom 1.02→1.06 | 禁现代 UI（圆角·阴影·chip）；禁 >1 高饱和色 | 3 |
| 霓虹 Cyberpunk | 扫描线 + RGB 三层分离 | 奇黑 900 / Noto Sans SC | `JetBrains Mono`·`Oswald` | `steps(n)` 主导 + 打字机 | 禁平滑长曲线；禁暖色；禁 fade | 3 |
| 瑞士 Swiss | 严格 12 栏 + 大留白 | Noto Sans SC 900 / 400 | `Inter` + `Inter` | 仅 `opacity` + `y:8`，8px 节拍 | 禁装饰动效；禁过冲；**禁漂移**（裁决 9） | 3 |
| 竞技 Vibrant Block | 撞色块 + 记分牌 | 奇黑 900 / Noto Sans SC | `Archivo Black` | 对角擦入 + 数字翻滚 + 烘焙纸屑，≤0.6s | 禁任何 >0.8s 动作；禁慢入场；禁 serif | 4 |
| 图解 Bento/Schematic | 模块卡 + 分步流程 | Noto Sans SC 700 / Noto Sans SC | `Montserrat`·`Inter` | 卡片 `back.out(1.7)` + `clip-path` 插值 + 箭头 | 禁步骤同时出现；禁无出处比例 | 3 |

合计 **4+4+4+3+3+3+3+4+3 = 31**（按上表「变体」列自上而下求和；任一族变体数改动须重算此式，且不得改总数 31）。

**字体策略的结构性不对称**（决定上表分工）：`frame.md §2` 已 probe 验证 **CJK 只能 `local()`**（引擎字体缓存无 `noto-sans-sc`，加 `local()` 反而使自动下载失效），而**拉丁族写裸名即由引擎自动供给**。故 CJK 选择锁死在已装集合、承担语义；拉丁侧只做数字/眉标/点缀。

> ⚠️ **订正（P1 实施实测，推翻本节原"拉丁侧无上限"说法）**：拉丁侧同样是**闭集** ——
> 引擎捆绑 18 个 canonical 族（`node_modules/hyperframes/dist/chunk-HBBJFK6I.js:33-135`
> 的 `FONT_ALIAS_MAP` + `CANONICAL_FONT_DISPLAY_NAMES`，代码侧真源
> `hf_style_spec.LATIN_CANONICAL_FAMILIES`）。集合外写任何族名都会命中
> `dist/chunk-WY5OODN5.js:6064` 的 `font_family_without_font_face`（severity=**error**，
> `check --strict` 直接失败），而且字先静默回落到通用族 —— 排版走形却不报原因。
> **别名同样禁用**：`Bebas Neue`→league-gothic、`Georgia`→eb-garamond 之类能过闸，
> 但渲染成**别人的脸**，31 套的区分度不能建立在一次静默替换上。
> 上表因此按集合内族名重写：原 `Libre Bodoni`/`Newsreader`/`Fira Code`/`Caveat`/
> `Abril Fatface`/`Chakra Petch`/`Russo One`/`Space Grotesk`/`DM Sans` 全部在集合外。
> 唯一补不平的是**手写味**：18 族里没有 script 族，街采族的批注因此退为
> `Space Mono` 打字机味，手写感改由烘焙手抖的 `strokeDashoffset` 圈注承担 ——
> 这条是本节的一处降格，**待裁决**（若要真手写，得走 CJK `local()` 之外的自托管字体，
> 与法则 10 的确定性口径无冲突，但要新增资产链路）。

两条库内警告带走：`Bebas Neue` 是 all-caps 显示族，中文无大小写 → 只能待在拉丁位（且它只是 League Gothic 的别名，上表已直接写本名）；`Caveat` 库内自注 "use sparingly for accents"。

## 6. 组件设计

### 6.1 组件 ①：风格 spec 语言（`schema: hf-style/1`）

每套 = 一份 YAML（**P1 实装订正为 TOML，理由见本节末「P1 实施记录」**），七层：`grid` / `type` / `color` / `motion` / `subtitle` / `layouts` / `taboos`。

**立场：spec 声明结构，不只声明值。** 只装 token 的 YAML 就是被否决的方案 A。

关键项：
- `grid.grammar` —— **有限集**，编译器按名取骨架，不允许自由发挥
- `color.saturation-budget` —— `{max-hues-per-frame: 1, accent-min-S: .45, support-max-S: .15}`，直接治 D6。**`-S` 的口径实装为 chroma `(max-min)/255`，不是 HSL 的 S**（P1 实测，见本节末记录）
- `color.value-ladder` —— 明度阶梯，"看起来像什么"由它决定，不是色值表
- `color.accents[].role` —— `shape-only` / `shape-or-large-text`，是现有法则 L1/L2 的泛化
- `motion.easing.forbidden` + `taboos[]` —— 禁忌必须是**可执行断言**（裁决见法则 13）
- `grid.safe.bottom: auto` —— 由 `subtitle.position` 反算，D5 的根治

**P1 实施记录（2026-10-09 · `scripts/hf_style_spec.py` + `templates/hyperframes_path_c/news-editorial-warm/spec.toml`）**

- **格式偏离 YAML → TOML**。理由：仓库七级决策阶梯把「原生」排在「新增依赖」之前（`AGENTS.md:55`），而本 skill 零 pip 依赖，PyYAML 会是新依赖。**代价（要认的）**：Python 下限从 3.10 抬到 **3.11**（`tomllib` 自 3.11 进 stdlib）。
- **文件位置对账**：本节原写 `styles/<id>.yaml`，实装落 **`templates/hyperframes_path_c/<pack>/spec.toml`**。与裁决 14 的双轨目录一致 —— spec 与它的编译产物（`frame.md`、7 版式 HTML）同包共存，`styles/` 不再单设目录。真源仍是 spec，`frame.md` 降级为编译产物（§6.3）不变。
- **彩度口径订正（推翻本节原口径）**：`saturation-budget` 按 HSL 的 S 算会**永久报红** —— 暖纸地 `#f5efe3` 的 HSL S = **0.4737**，已越过 `accent-min-S: .45`，而它按定义是个 support 色，须 ≤`.15`。HSL 的 S 在近中性色上被低明度放大，与"刺不刺眼"无关。实装改用 **chroma `(max-min)/255`**：暖纸 = `0.0706`、panel `#e8dfcb` = `0.1137`、ink `#1f1b16` = `0.0353`（三者都在 support 档 .15 以下），强调橙 `#B45309` = `0.6706`（过 .45 下限），与 `.45/.15` 两个阈值量纲相合。字段名里的 `-S` 沿用本节，含义以 `hf_style_spec.chroma()` 为准。
- **判据 5 与裁决 6 咬合的算术后果（新增约束，P5 铺 31 套时是硬约束）**：四轴 = `grid.grammar` / `type.display` / `motion.signature` / `color.value-ladder`（`AXIS_NAMES`），两两相同项 ≤2。同族变体 grammar 必同 ⇒ 余下三轴两两汉明距离 ≥2 ⇒ **4 变体族在 3 维立方里只能取偶校验子集** `{000,011,101,110}`（或其补 `{100,010,001,111}`）。不是"尽量不一样"，是必须按这个排布选参数；已在 `t_hf_style_spec_distinctness_gate_counts_axes_not_vibes` 里正反各验一次（破坏排布当场报红）。
- **反算复现两个手测像素边**（D5 的根治拿到验收）：`caption_reserve_cqh` 的算法是先算字幕块顶边 `top_px = h − margin − n × line`，再取 `(h − top_px) / h × 100 + 1` **向上取整**（那 1 cqh 是 `CAPTION_HEADROOM_CQH`，作用是让点值不越过实测边，不是第二个估出来的数）。用产线口径参数（`line-height-frac = 1/32` 即字号 60px，对齐 `ASS_FONT_H_FRAC`；`margin-bottom-frac = 0.09`，对齐 `ASS_MARGIN_BOTTOM_H_FRAC`）：`n=2` → `top_px = 1627.2`、reserve **17.0**；`n=3` → `top_px = 1567.2`、reserve **20.0**。两个顶边分别对上 `path_b_build.py:370-373` 那次逐行像素实测的"两行顶边 ≈ 1628px / 三行顶边 ≈ 1568px"（0.8px 差是那条注释自身的取整）。**口径对账**：本节与 §11 说的"由 `subtitle.position` 反算"，实装里 `position` 是给人读、也给 P2 字幕轨挂载用的**描述串**，反算真正取的是同层三个数值键 `margin-bottom-frac` / `line-height-frac` / `worst-case-lines` —— 数值不进 `position` 就无法被闸检查，所以它是标签不是输入。
- **顺带查清一件事：现值 20.0 是"三行"口径，比产线自己的上限保守一整行。** `layout_selfcheck.py:43` 写死的 `CAPTION_RESERVE_CQH = 20.0`（`path_b_build.py:812` 消费）反推恰好等于 `worst-case-lines: 3` 的 18.375 + 余量后向上取整；而 ASS 路径 `CAPTION_MAX_LINES = 2`（`path_b_build.py:375`，超长按时长切多条而非折三行）。旗舰 spec 暂以 `worst-case-lines = 3` 复现 20.0 —— **这是为了 P1 的"反算 ≡ 现状"验收，不是新决策**；P2 字幕轨接进 HyperFrames 后要不要收到 2 行（禁入区缩到 17cqh，还给排版 3 行 × 60px 的空间），届时按 §9 P2 的口径单独裁。
  - **P2 已裁（2026-10-10）：维持 20cqh，不塌到 17cqh**。字幕进 HyperFrames 后禁入区本可随字幕层重算，但量了 AIGC 角标的竖向几何：塌到 17cqh 会吃掉角标唯一落点（角标带缩到 34px < 实测角标 65.7px），与裁决 2"角标留 ASS"冲突。收口推迟到 P4/P5，与"字幕与角标同层重排"合并裁。详见 §6.4 P2-3/P2-4 落地第 2 条。
- **`saturation-budget` 三阈值只有一侧在 spec 层可执行**：`accent-min-S`（自称强调色的够不够艳）编译前就能数；`support-max-S` 与 `max-hues-per-frame` 要**逐元素逐帧**数 —— 一份色板同时有 2 个高彩度色并不矛盾，只要它们不同帧出现。后两条排在编译器（法则 11/12 配额处），不是 spec 层的活。本节的"直接治 D6"由此收窄为这个口径。

### 6.2 组件 ②：视觉原语库（44 个，三档）

原语是 **Python 函数**（不是 HTML 串），因为法则 10 要求随机在编译期烘焙。每个原语声明**前置条件**而非只有参数：

```
requires: [solid-ground|asset|image-gate-ready|accent-allows-large-text|paired-text-role|container-not-clip]
contrast: inherits|self-proofs|requires-chip|none · seek_safe: by-construction · budget: {paint, frames, dom, motion}
```

（形状已按实装修正两处：原写的 `ground: ink|paper|any` 一行删掉，理由见下方 P1-3b 记录第一条；`budget` 里原先重复表达"要图"的裸 `asset` 词条也删了 —— 同一件事由 `requires: [asset]` 单点表达。）

- **P0 · 12**：`clip-wipe-up` `char-rise` `rule-pull` `block-chip` `hairline` `giant-numeral` `photo-duotone` `photo-local-crop` `ken-burns-in` `drift-y` `cue-fade` `keyword-tint`
- **P1 · 18**：破格斜切、半调网点、扫描线、胶片颗粒、暗角呼吸、竖排大字、编号水印、首字下沉、条形生长、折线绘制、数字滚动、对比标尺、RGB 分离、glitch 烘焙、霓虹描边、视差分层、纸屑、示意标注
- **P2 · 14**：手绘圈注、马克笔高亮、胶带条、贴纸倾斜、手绘箭头、涂改线、遮罩局部显影、色键混合、进度脊、环形弧、迷你趋势、括号框、打字机、过曝闪

**零插件替代方案**（裁决 10）：逐字 = 构建期按码点切 span；圈注 = SVG `pathLength="1"` + core `attr:{strokeDashoffset:1→0}`；打字机 = 构建期切 span 逐个 `opacity`；纸屑 = 构建期烘焙抛物线关键帧；形状变形 = `clip-path` 顶点插值（唯一有画质让渡项）。理由：`19be62b` 刚为"每次 npx 重装"踩过坑，多一个 CDN 就多一个离线故障面；插件重建 DOM 与 `data-var-text`/`getVariables()` 注入顺序耦合；构建期烘焙天然满足法则 10。代价：多约 200 行 Python。

**P1-3b 实施记录（2026-10-09 · `scripts/hf_primitives.py` · P0 十二个已落地，P1/P2 档共 32 个待铺）**

- **`ground` 字段删掉，`requires` 是唯一的前置条件入口**（订正本节上方的声明形状）。12 个原语的 `ground` 实测全是 `any`，那条 `prim.ground not in ("any", ground)` 永远不可能成立 —— 两条机制里有一条是死的，就删它。"要实色地面"改由 `requires: [solid-ground]` 表达，口径 = `SOLID_GROUNDS = (ink, paper)`：形状（chip／标尺／发丝线）坐在照片或纹理上时边缘对比不可算，判据 3 数不到它。
- **`contrast` 值集加 `none`**：`inherits|self-proofs|requires-chip` 三档覆盖不到"根本不承载文字的纯形状/纹理"，而 clip 揭示、双色化图层正属于这一类。硬塞 `inherits` 会让审计去核一个不存在的色对。
- **`requires` 值集闭合（新增闸）**：每个名字必须落到 `CHECKED_REQUIRES`（检查器能判）或 `CALLSITE_REQUIRES`（点名谁强制它 —— `paired-text-role` 由 `Tok.pair()/face()` 抛 KeyError 强制，`container-not-clip` 由结构闸的 `gsap_animates_clip_element` 强制），两边都不在就**拒编**。没有这条兜底，"声明前置条件"就会长成第二份没人核的 frame.md 色值表。
- **措辞订正：逐字切分不在构建期，在脚本体内同步做**。发射器对 `compositions/*.html` 是逐字节复制（§6.3 契约面），文字只在运行时经 `data-variable-values` 注入 —— 构建期拿不到最终标题串，"构建期切 span"在版式文件里做不到。实装：`Array.from` 按码点切 + 每条 `fromTo`，切分**不进 onStart**（seek 模型里它不触发）。P0-1 的结论本身不变，成立的是"运行时同步、关键帧已存在"这一半。已在版式里留静态占位 `<span class="…-ch">`，让结构闸在真标记上看见这个类，而不是靠 JS 字符串的形状。
- **法则 10 检测器的口径实测修正：GSAP 回调是补间参数表的键**（`{ onUpdate: tick }`），不是方法调用。带点的 `.onStart(` 形状在真实死法（老 `hook.html:224`）上一条也抓不到；`FORBIDDEN_JS` 因此用裸词 `onStart/onUpdate/onComplete`。误伤方向是拒编，比放行安全。
- **`.from(` 走正则且豁免 `Array.from(`**：前者是 D3 死因，后者是招牌原语的切字手法。子串判会把 `char-rise` 自己打死 —— 第一版实踩，测试 `t_hf_primitives_detector_rejects_every_death_mode` 的正反例把这个豁免钉住。
- **`.to(` 的时长必须挂 `driftDur`**（只给 `driftStart` 不算）。原语库与结构闸的契约面是**名字**（`layout_selfcheck.BUDGET_CONSTANTS`，实测 `("INTRO_END", "MIN_DRIFT")`），改数字可以改名不行；`BUDGET_JS` 模板 + 连续位移使用者集合由 `t_hf_primitives_budget_block_satisfies_the_structure_gate` 双向核。
- **`value-ladder` 拿到可执行口径，判据 5 第四轴不再是装饰数字**：新增 `value_ladder_violations()`，用 **HSL 明度**（`hsl_lightness()`，量纲 0..100）双向核色板 —— 每个非强调面色要落在某档 ±`LADDER_TOLERANCE = 2.0` 内，且每档至少被一个面色命中；强调色不参与（`#B45309` 明度 37.06，离任何一档都超容差，跳过它这一支是真在起作用）。旗舰包实测四档 **92.55 / 85.29 / 80.78 / 10.39** ⇒ `value-ladder = [93, 85, 81, 10]`，并为此在色板里补了承载第三档的 **`rule` 分隔线面 `#ddd3bf`**（原 spec 只有纸/面板/墨，阶梯却写了四档 —— 那条"凭空档"分支正是抓这个的）。
- **`motion.entrance-seconds` 进 spec 必填**：原语的入场时长从这里取默认，写在版式里就是又一个手抄常数（`1.4` 在旧口径里只存在于注释）。校验强制 `entrance-seconds ≥ entrance-min-seconds`，`char_rise` 的单字时长按 `max(下限, 招牌/2)` 算 ⇒ 法则 13 的入场下限**按构造成立**，不靠事后拦。
- **图片类三原语在 P3 前一律拒编**：`photo-duotone` / `photo-local-crop` / `ken-burns-in` 挂 `requires: [image-gate-ready]`（`GATED_REQUIRES`），`asset` 与 `image-gate-ready` 是两条独立事实 —— 门禁接好但本镜无图照样拒。
- **`budget` 是与渲染行为对账的数据，不是标签堆**（本节点新增的两条闸）：词条形状钉死为 `维度:值`，维度词表 = `BUDGET_DIMENSIONS = (paint, frames, dom, motion)`，且必须与实际用量相等；每条标签再与渲染出来的片段对账 —— `motion:continuous ⟺ 补间里出现 driftDur`、`dom:chars ⟺ 出现 Array.from(`、`frames:1 ⟺ 一条补间且不膨胀 DOM`。对账当场抓出两处真错：`photo-duotone/photo-local-crop` 该有 `frames:1` 却没有（它们各只发一条补间），以及裸 `asset` 词条与 `requires: [asset]` 重复。
- **验收面**：`path_b_selftest.py` 108/108 全绿（本节点新增 9 项）。另跑 21 条变异，逐条被抓、逐条回滚（跑法：每次只改一个文件、跑完立刻从原文重写，避免变异互相泄漏）：
  - **包体侧 4 条**（`spec.toml`）：阶梯退回装饰数字 `[96,91,85,12]`、删 `rule` 面、删 `entrance-seconds`、加一个 HSL 明度 51.6 的超容差面色 —— 四条全打红 `t_hf_style_spec_value_ladder_must_be_the_actual_surfaces` 或编译前门。
  - **源码侧 17 条**：`char-rise` 退回 `.from(`、有色面加 `opacity`、`.to(` 时长写死 2.0、摘掉 `photo-duotone` 的 `image-gate-ready`、`value_ladder_violations` 改成永远通过、`LADDER_TOLERANCE` 放大到 30、去掉 `Array.from(` 豁免、删掉未登记 `requires` 的兜底分支、回调禁令退回带点写法、阶梯只核单向（删"凭空档"分支）、`budget` 塞回裸 `asset`、维度改名 `doms:`、`contrast` 造新值 `auto`、`seek_safe` 改成口号 `assume-safe`、`ken-burns-in` 预算换成 `paint:low`、`char-rise` 去掉 `dom:chars`、`photo-duotone` 去掉 `frames:1`。
  - 四道既有闸同步复跑：结构闸 227 文件 0 违规、色板闸 31 pack / 24 条基线不变、curate 33/33、`npm test` 通过。

### 6.3 组件 ③：编译器

`spec.yaml` → 7 版式 HTML + 字幕轨 composition + **frame.md（降级为编译产物）**。

顶部标注 `# 本文件由 styles/<id>.yaml 编译生成，勿手改`。**真源上移到 YAML**，`frame.md` 的"唯一 token 源"地位让位。

**版式名不变**（`hook/stat/rail/quote/catalog/story/closer`）—— 这是发射器与版式之间唯一的契约面，`MOUNT_TPL`、`data-composition-variables`、`choose_layout()` 全部原样可用。**本设计最大的降风险项。**

### 6.4 组件 ④：字幕轨（cue 驱动）

**更正记录**：本设计早期判断"真逐词数据已在管线里"**错误**。CLI 默认走 `SentenceBoundary`，逐镜字幕文件里只有句子级 cue。
（原引的"整镜仅一条 cue `00:00:00,100 --> 00:00:06,187`"也不准：实测那份文件是**两条**，且相邻 cue 交叠 50ms。文件名 `scene_1.vtt` 本身在骗人 —— 7.2.8 的 `SubMaker` 只有 `get_srt`，CLI `--write-subtitles` 落盘的是 **SRT 体**（逗号毫秒、无 `WEBVTT` 头），`collect_cues` 的 `CUE_RE` 一直解析的就是 SRT。P2-1 落地后这条文件路径整个取消：字幕由取数面自己派生，`scene_i.vtt` 与 `CUE_RE` 已删。）

修法：`edge_tts` 7.2.8 给 `Communicate(text, voice, boundary="WordBoundary")` 传参即可（`communicate.py:335`；`TTSConfig` 在 `:342` 内部构造且**不在顶层导出** —— 原文"TTSConfig 支持 boundary"措辞不准）。`synthesize_audio`（`path_b_build.py:2145`）从 shell 调 CLI 改为调 Python API，一次 `stream()` 同时收音频字节与词事件；`doctor` 门禁项由"可执行定位"换成"可 import"（`:2131` 已是 import，要拆的是 `:2147` 的 `which`）。

**P2-0 探针实测**（2026-10-10，五镜真稿，全文见 `routes/news/evidence/2026-10-10-template-v2-p2-captions.md`）：词级数据真拿得到，粒度是**词**不是字（`门诊/新规/10月/起`），单位 100ns tick；同一句两次请求的 `start`/`duration` 差 **max 0.000s**（服务给的词级时序确定，五镜复算见 §K9）。三条形状必须由取数面处理，不能假设干净：① **词序列不含标点**（丢字数 = 正文标点数）⇒ 匹配前一律先去标点空白归一化；② 词间**相切**（106 个间隙里 33 处 `gap=0.000000`，**负空隙实测 0 处** —— 原文"偶发 -0.000s 重叠 3 处"是把端点先四舍五入再相减的假象，§K2 已更正）⇒ 仍夹 `s = max(s, prev_e)`，但它是**防御性**一支，自测里由合成的重叠事件证明会执行；③ 末词右沿比音频早 **0.56–0.68s** ⇒ 尾段要有口径。

**P2-1 已落地**（2026-10-10，同一轮内跑真链路）：`synthesize_audio` 改调 `Communicate(boundary="WordBoundary")` + `cues.json`（`schema: hf-cues/1`）落盘并按 (归一化正文, voice) 哈希复用 —— 五镜首次 13.5s、复用 **0.00s** 且逐镜时长/词表/cue 逐字相同，`--check-only` 的 timing 里 `dub=0.0s` 就是在产线里证了一次复用；精确消费字符数归组在真服务数据上**五镜零失配**。实测数字、四道闸复测与三处自我更正见同一份证据文档 §K7/§K8/§K9。

- **挂载**：每镜一个字幕 composition，挂最高 track（与 `MOUNT_TPL` 同构、失败隔离）。不用全片常驻层。
- **时基**：发射器负责 `+data-start` 平移；composition 内部只见 `0..slotSeconds`。
- **入退场（裁决 17，2026-10-10 改口径）**：**词级只管入场，退场按整条 cue 一次做** —— 每词一个 `fromTo`（`opacity 0→1` 落在词 start，累积不消失），每条 cue 一个退场 `fromTo`（`1→0` 落在该 cue 末词 end 与镜尾之间）。均 seek 可回退。字幕轨是**唯一允许退场的层**（法则 14），且纯墨无底色面，不触法则 8。
  ~~原文"每词两个 `fromTo`（`1→0` 落在词 end）"~~ 按字面实现已被实测否掉：词 lifetime **min 0.075s / 均 0.267–0.327s / max 0.700s**，词间空隙 max **+0.575s**，标点处必出半秒空窗 ⇒ 那是频闪不是字幕，与裁决 1（完播率优先）正面冲突。
- **强调匹配**：`onscreenAccent` / `｜` / "数字+单位" 三源改为与 words 数组**精确子串匹配**；匹配不上即不高亮，**禁止按比例猜**（与法则 5 同立场）。P2-2 落地的三条细则（实测见 `routes/news/evidence/2026-10-10-template-v2-p2-captions.md` §K10）：① 三源按 `｜` → 数字+单位 → 屏句强调段 取**第一个匹配得上的**，优先序抄 `pick_accent`，字幕轨不自定第二套；② 匹配只在**这条 cue 自己的词**里做，不在整镜词表里做（否则同一短语出现两次会两句一起亮）；③ `｜` 是标记不是字 —— 实测服务既不念也不回事件（`门诊新规｜全国执行。` 只回 4 词），所以它必须进 `caption_norm` 的剥离集，否则每一条点了强调的稿子都归组失配、整片掉进退化支；上屏文本同样去它，但 cue 原文保留它供 ① 读。两条支上比的都是**亮起来的这串字**而不是词的切法（字符支按字切、词级支按服务词切）。
- **降级**：WordBoundary 依赖微软服务，失败时**只降级时序**（按字符数比例分配每个词的 start/end），**不降级"哪个词被强调"**——强调仍走精确子串匹配，匹配不上就不高亮。两处"比例"的口径不同：前者是无外部时序数据时的兜底切分，后者是被明令禁止的猜测（法则 5）。解析结果**必须落盘 `cues.json` 进 work_dir 当可复现输入**，重跑读文件不重问服务。
  ~~原文理由"否则两条路径时序不同会破坏同稿同片"~~ 被 P2-0 实测否掉：同一句连跑两次 `WordBoundary`，词数与逐词文本全同，`start`/`duration` 差 max **0.000s** —— 服务给词级时序是确定的。落盘的真理由换两条：① **降级路径与真路径时序确实不同**，不落盘就无法证明一支片子走的是哪条、也无法复现；② 配音段实测 **12.1–12.9s** 是网络往返，重跑门禁/重渲染不该再花一次网络，更不该在微软服务抖动时把已合格的稿子变成失败。复用键 = (归一化正文, voice) 的哈希，哈希不匹配必须重配 —— 不许拿旧 cues 配新稿。
- **禁入区协商**：`grid.safe.bottom` 由 `subtitle.position` 反算；但抖音右侧点赞栏要求左右各留 6%，此宽度约束硬，与字幕归谁渲染无关。

**P2-3 / P2-4 已落地**（2026-10-10，`path_b_selftest` 141/141；Node≥22 机器过真渲染闸）：字幕真正收进 HyperFrames，成为每镜一个 2 轨子合成（`compositions/subtitle-<i>.html`，透明 `#root`、`@font-face "HF CJK"` 走本机 CJK 族、词级入场 `fromTo opacity 0→1` 累积 + 每 cue 一次退场）。**填充/描边随本镜地面 tone 翻面**（浅面墨字 `#1f1b16`＋白描边、深面白字 `#ffffff`＋黑描边），强调 `#B45309` 两 tone 通用。四条锁定口径与实现：

1. **裁决 17 落地**：词级只管入场（累积不消失），退场按整条 cue 一次做；数字常量单一真源在发射器（`SUBTITLE_*`）。
2. **禁入区维持 20cqh、AIGC 角标不动**：`CAPTION_RESERVE_CQH` **不改**（20.0）。原"收到 2 行 / 17cqh"的收口**推迟到 P4/P5** —— 量过角标几何后确认：烧录字幕块底固定在 `h−MarginV`、三行字幕顶边实测 1568px（81.7cqh），把禁入区塌到 17cqh 会物理吃掉 AIGC 角标唯一的竖向落点（角标带从 92px 缩到 34px < 角标实测 65.7px）。裁决 2 的"角标留 ASS"与这条几何耦合，不能提前解。
   - **字幕填充色改"随地面翻色"（2026-10-10，推翻原"统一白字+黑描边"）**：`check --strict` 实测白字在旗舰暖纸浅地面 `rgb(234,229,217)` 上对比 **1.26:1**、不过 WCAG AA 3:1（深地面则过）。原口径能成立的前提是字幕由 ASS 在 HyperFrames **之后**烧、引擎看不见它；收进体系后地面 tone 就成了变量。owner 选定"随地面翻色"：`_subtitle_palette(tone)` 浅→墨字白边、深→白字黑边；强调 `#B45309` 在旗舰所有地面上实测 ≥3（浅纸 3.8–4.4、墨面 3.4），不随 tone 变。cobalt 深地面（号外/竞技族，非本旗舰包）上强调仅 2.24:1，列为 **P5 铺该族时的待办**，非本轮阻塞。
   - **字幕 `#sc-wrap` 打 `data-layout-allow-caption-zone`**：引擎的 `--caption-zone=y0=0.80` 是给"烧录字幕预留、体系内容别怼进去"的，现在字幕本身就是体系里故意落在 lower-third 的那一层，不打此标记 `check` 会把每条字幕判成 `caption_zone_collision`（实测 29 条）。这是引擎 fixHint 明写的正规出口，不是绕过。
3. **只有编译包（path_c，有 `spec.toml`）走原生字幕**：`load_style_pack` 现返回 `pack["compiled"]`；`emit_composition` 仅在 `pack["compiled"] and scene_cues is not None` 时挂字幕轨。31 套 path_b 存量手发包不传 `scene_cues` ⇒ 字幕子合成一个不生成、片字节形状不变。
4. **ASS 烧录对编译包降为"仅角标"**：`mux_and_burn` 收 `ass_cues = [] if pack["compiled"] else cues`（`subs.vtt` 仍写全量供审计）；守卫改成 `if not cues and not burn_badge`，空字幕 cue 但 full 档要角标时仍走滤镜，合规标识不被静默丢掉。
5. **自检豁免两条、其余照查**：`layout_selfcheck` 认 `subtitle-` 前缀为字幕文件，只对 #6（动量预算）/#7（底部禁入区）两条不变量豁免（字幕层本就常驻底部、无 driftDur 预算），其余 15 条（含 `CONTRACT_ID_MISMATCH`、空目标补间、CJK `@font-face`、px 排版）全数生效 —— 反证测试改坏根 id 必须仍报红。

### 6.5 组件 ⑤：图片门禁与纹理化

**门禁实现（本地零网络，已实测）**：`{frontalface_alt2, profileface} × {原图, 水平镜像}` 四通道并集，`minNeighbors≥3`、`minSize≥24px`。

实测分离度：s1（累西腓拾荒者，侧脸朝左）`profileface` 命中 `(118,188,52×52)`；镜像后 `frontalface_alt2` 命中 ×2；s2（齿轮）**四通道全零**。
**禁用 `frontalface_default`（齿轮图误报 4 个）与 `upperbody`（误报 7 个）** —— 锈螺栓圈被当正脸。

**asset_grade 三档**：
- **G0 可指认** —— 任一通道命中人脸（s1 在此）
- **G1 场景可推断** —— 无人但场景具指认性
- **G2 纯材质** —— 纹理/特写（s2 在此）

**硬规则**：
1. **G0 禁入首镜、closer、人物镜、含专名镜**；首镜是"暗示这是谁"的最强位置
2. G0 要用只能裁掉人脸连通域后**复检**，仍命中则弃用
3. 检测器不可用/超时 → **一律降级为 G0**（宁可少用图，不可错指认人）
4. **首镜改为排版主导**，图库照片不进首帧（推翻现有 `.hk-photo` 满屏设计）

**纹理化强度按 grade**：G2 可满屏 + duotone 压向族色 + S<0.15；G1 强制裁到 25–35% 局部以失去场景指认；G0 默认不用。

**「示意画面」强制标注**：左下、安全区内、z 高于所有原语（禁止被任何入场元素遮挡）、等宽 2.0cqw、字距 .08em、大字档 ≥3:1。第一行 `示意画面 · 与报道对象无直接关联`，第二行降为附属的版权署名（现有 credit 视觉上像权威背书，其实是免责信息）。**凡 `grade != real` 一律强制，无例外无开关。**

一个机制解决三个问题：大裁切 + 强压色 → 图失去指认性（合规）、不再抢文字戏（审美）、同图反复用于同选题也不被察觉（观感）。

### 6.6 组件 ⑥：审计与门禁改造

| 位置 | 现状 | 改为 |
|---|---|---|
| `audit_pack_contrast.py:110` `SHARED_TOKENS` | 18 个色值跨包共享白名单 | **清空**（裁决 12）；改为共享角色不共享色值 |
| `audit_pack_contrast.py:56` 表头指纹 + `parse_palette():212` | 从 frame.md 解析 markdown 表取色板 | 改读 spec；表仍生成供人读。**新增编译前入口**调 `contrast_ratio()` 预校验，不过即拒编 |
| `layout_selfcheck.py:43` `CAPTION_RESERVE_CQH=20.0` | 写死 | 从 spec `subtitle.position` 反算 |
| `layout_selfcheck.py:49` `BUDGET_CONSTANTS` | `MIN_DRIFT` 全局 | 族级默认值；瑞士族 `drift:none` 走例外表 |
| `layout_selfcheck.py:55` `CJK_FAMILY` | **单数字符串** `"HF CJK"`，`:336` 判定用 `CJK_FAMILY in block`（**子串**） | 改成族名集合 + **精确提取** `font-family` 值；再补两条：版式用到的中文族必须本文件声明、声明的中文 face 必须至少命中一个本机已装 `local()` 名。**P0 实测订正：旧闸的后果不是"误挂审计"，而是漏掉三条静默路径**（用到未声明 / `local()` 全假 / 前缀式自造族名）；详见 §11 结论与证据附录 |
| `layout_selfcheck.py:52` `CANONICAL_LATIN_FAMILIES` | 3 个拉丁族 | 扩充；拉丁侧仍走裸名自动供给 |

**新增检查**：
- 法则 10 静态检查：生成 HTML 里出现 `Math.random(` 即失败
- 法则 11 配额：`filter: blur(` 元素数 × 覆盖帧数 超 `≤2 / ≤40%` 拒编
- 饱和预算：从 hex 算 HSL 的 S，数每版式高饱和 accent 数，超 `max-hues-per-frame` 拒编
- **区分度门禁**（验收判据 5）：任意两套四项至少两项不同
- **确定性哈希门**：同稿两渲比对**视频流哈希**（判据 4a；P0-4 已证整支 `final.mp4` 容器哈希因 mp3 字节不可比）—— 唯一能证明法则 10 真守住的手段

烧录后的 `check --strict` 与事后审计**保留**，语义降级为**编译器回归测试**（抓编译器自己写跑偏，不再抓人）。

### 6.7 组件 ⑦：路由改造

`routes/news/pack-decision.md` + `routes/news/scripts/decide_pack.py`：12 体裁 → 9 族 × 变体的决策表。体裁映射见 §5 表；同族多变体按情绪/昼夜/强弱选。

## 7. 新增版面法则（10–18）

- **法则 10 · 构建期随机一律禁用。** 同一 page load 内 seek 稳定，但**跨渲染会变**，两次跑同稿出两支片子即作废"确定性 MP4"。所有随机值由 `seed = hash(norm_key)` 的 PRNG 在**编译期**烘焙成常量关键帧。
- **法则 11 · `clip-path` 是 `opacity` 的合法替身，`blur` 要配额。** 法则 8 禁的是"带底色面块用 opacity"（α≈0.72 混色 → 2.5:1 不过审）；`clip-path: inset()` 不混色，**P0-2 实测：带 `background` 的面块做 `clip-path` 擦入，`check --strict` 零违规**。**但 P0-2 同时推翻了原表述里的"不改几何、完全合规"**：`clip-path` 只裁视觉，检测器量的是 layout box，所以**它藏不住一个越界的盒子** —— 文字溢出（`text_box_overflow`）或容器越界（`container_overflow`）照报，`overflow:hidden` 同样不豁免。遮罩解决"怎么出现"，不解决"能超出边界"。`filter: blur()` 每帧重算，配额 `≤2 元素 / ≤40% 帧`。
- **法则 12 · `onUpdate` 写 DOM 允许，禁累积状态。** 数字滚动走 `fromTo` 到代理对象 + `onUpdate` 回写 `innerHTML`，seek 会重放故安全；但累加计数器会失步。
- **法则 13 · 每族必须声明 ≥3 项禁忌，且为编译期断言。** 31 套会不会长成一套，取决于禁忌有没有写死。差异靠"这族不许干什么"守，不靠"我想不一样"。
- **法则 14 · 字幕轨是唯一允许退场的层。** 它承载瞬时信息，cue 结束必须消失；纯墨无底色面故不触法则 8。
- **法则 15 · 入场不从画布外起跳（P0-2 后新增）。** 原语库的 `slide-in` 类手法**不得**把起点写在界外（`x:-110cqw` 之类）再擦入 —— 那是靠"产线不传 `--at-transitions`"混过 `check --strict` 的（P0-2(c) 实测：传了该开关即 `canvas_overflow`，不传则全绿）。招牌入场改用**界内满幅盒 + `clip-path` 同帧揭示**（P0-2(a) 已证合法）。旋转（`rotate(-3deg)` 静态/`fromTo`）不受此限，号外族与街采族的斜切招牌照常。
- **法则 16 · `data-var-text` 容器不得有元素子节点（P1-3e 出帧后新增）。** 引擎的变量写入函数（`hyperframe-runtime.js:350` 的 `_1(e,t)`）只在 `childElementCount===0` 时走 `textContent=t` **替换**；容器里有元素子节点时改为往第一个 TEXT_NODE 写、没有就 `insertBefore(createTextNode…)`，**不动已有的元素子节点**。`char-rise` 为"空镜兜底 + 让结构闸在真标记上看见 class"留的占位 span 正好落进后一条支路 ⇒ 每个逐字标题渲染两遍，而四道闸当时全绿 —— 缺陷只在摊开的帧上看得见。原语要留占位节点，就必须在 `pre_js` 里 `removeAttribute("data-var-text")` 让脚本成为唯一写入者（对"引擎先写/后写"两种顺序都成立）。这条由 `hf_primitives.var_text_shape_violations` 逐片段断言，违反即拒编。
- **法则 17 · 竖屏必须填幅：最重内容下沿距内容区下沿 ≤ `MAX_BOTTOM_DEAD_CQH`（P1-3e 出帧后新增）。** 法则 1 只拦"怼进字幕禁入区"，不拦"下半部空转"；未约束时旗舰包七套版式空出 3.5–14.6cqh，而下半部空是"模板感"的第一来源。口径是配方的**最坏占位**（`Step.height_cqh` 按最大行数算），与法则 1 同处 `hf_compile.geometry_violations` 核。已知残留（P4）：占位行数由配方手写，没跟发射器的字符上限（`TITLE_LINE_MAX_CHARS=18`、`HOOK_LINE_CHARS=7`）对账，长文案下真实行数可以大于声明行数。

- **法则 18 · 每个文字位必须声明栏宽，且任意两位的盒不得相交（P1-3e 出帧后新增）。** 绝对定位只写 `left` 时盒宽是**收缩量**（上限 `100−left`），右沿取决于那一镜的字有多长 ⇒ "这一位会不会伸到邻位头上"在编译期根本不可判。实测缺陷：报头 `block-chip` 的强调色底与标题行盒交 0.59cqh，出帧上是一道色带横穿标题，而四道闸当时全绿（片是带底色的，leading 吸收不掉）。修法是把横向口径交给浏览器钉死：`hf_compile` 要求每个文字位写 `max_width`，原语把它落成 CSS 的 `max-width` ⇒ 超长的字宁可折行（变高，归占位行数那条账）也不许变宽，于是 `overlap_violations()` 算出的盒在渲染里仍然成立。字宽系数实测：`LATIN_DIGIT_EM = 0.569`（从成片帧量镜序大数字的墨盒 18.20cqw ÷ 16cqw ÷ 2 位）、`CJK_CHAR_EM = 1.0`（偏保守的一侧）。三条分支缺一不可：没声明栏宽 ⇒ 拒编（否则只看写了栏宽的那些位就是假绿）、越出 `spec.grid.safe` 的幅 ⇒ 拒编、两盒相交 ⇒ 拒编。**已知残留（P4）**：`KICKER_MAX_CHARS=8` 只是编译器侧的声明，发射器不截眉标，超长眉标会在盒内折行而配方占位仍按一行算 —— 与法则 17 那条残留同源。

## 8. 阶段 0 · 四个探针（先拿结论，不保留代码）

| # | 探针 | 若失败的后果 | 实测结论（2026-10-09） |
|---|---|---|---|
| P0-1 | 构建期切 span + `fromTo` 逐字，seek 抽帧比对稳定性 | 逐字入场不可用，杂志族招牌手法要换 | **通过**：两次独立渲染同帧快照哈希逐字节相同；思源宋体确实以衬线形态出帧 |
| P0-2 | `clip-path` 在 `check --strict` 下是否报 `container_overflow` | 杂志族与胶片族招牌手法要换替身 | **有条件通过**：界内遮罩揭示合法；但裁切藏不住越界盒（法则 11 订正），并新立法则 15 |
| P0-3 | **edge-tts 中文 `WordBoundary` 返回词还是字** | 若是字级，逐词高亮需在发射器侧做词组聚合；**§6.4 全部成立与否取决于此** | **通过（返词）**：§6.4 原样成立，无需聚合层 |
| P0-4 | 同稿两渲哈希基线（**改造前测**） | 若现在就不一致，"确定性 MP4"本身是坏的，与本设计无关但更该先修 | **渲染器确定**：视频流哈希一致，容器哈希因 mp3 字节不同而不一致 → 判据 4 拆 4a/4b。**P1-3e 订正（同日实测）**：4a 在**硬件光栅**那条路上不再成立（编译包与未改动的 `news-coral` 都复现，两遍 1291 帧里 398/641 帧像素不同、PSNR 58–63dB），而同一次发射改 `--no-browser-gpu` 两遍逐字节一致 —— 与本行 P0 结论冲突，未归因（见 §11）；发射器默认已改软件光栅，4a 由 argv 的默认支保证（`t_render_argv_defaults_to_software_raster`） |

**决策门**：P0-3 与 P0-2 任一失败 → 停止实施、回报用户、回 §5 调整对应族签名。不硬做。
**决策门结论：四个探针无一触发停止，P1 放行。** 全部证据、命令与输出见
`routes/news/evidence/2026-10-09-template-v2-p0-probes.md`（探针代码在 gitignore 的
`.harness-news-runtime/probe/` 下，按本节口径不保留）。

## 9. 排期

1. **P0** 四探针（§8）
2. **P1 旗舰包 = 决策门**：12 个 P0 原语 + 编译器最小版 + **杂志族·暖纸**一套 → 出片 → **与老包同稿并排，用户看帧判定**。不认可即停在此处，损失只有 P1
   - **已过（2026-10-10）**：六项机判全绿 + 判据 1 人工门认可（批准语"你继续铺吧"）。三条实测审美差距**不阻塞但记账**，P5 铺同族变体时一并解决：D2 字号档比基线小一档、D3 story/closer 中段约 30% 空转、D4 序数存在感弱（Playfair 16cqw 细衬线 vs 基线近满宽重量级数字）。并排帧与两支成片在 `.harness-news-runtime/tmp/p13e/`，数字在证据 §J6
3. **P2** 字幕轨（WordBoundary + `cues.json` 落盘 + 禁入区反算）
   - **P2-3/P2-4 已过（2026-10-10，`path_b_selftest` 141/141 + Node≥22 真渲染闸）**：字幕每镜编译为 2 轨子合成、ASS 对编译包降为仅角标、自检两条豁免其余照查；`check --strict` 通过（字幕填充随地面翻色 + `data-layout-allow-caption-zone` 消掉对比与禁入区两闸）；判据 4a 双渲染视频流逐字节相同（含字幕进流）。禁入区**维持 20cqh**、AIGC 角标不动，17cqh 收口推迟到 P4/P5（几何证据见 §6.4 第 2 条）。
4. **P3** 图片门禁（四通道 + grade + 纹理化 + 示意标注）
5. **P4** 审计上移（编译前预校验 + 5 道新检查 + 确定性哈希门）
6. **P5** 铺 31 套，族顺序：**杂志 → 号外 → 数据 → 瑞士 → 竞技 → 图解 → 霓虹 → 胶片 → 街采**。每族先出 1 个变体验收，再铺同族其余变体

## 10. 待决项

| # | 事项 | 说明 |
|---|---|---|
| Q1 | ~~老 32 包是否物理删一个~~ **已决（2026-10-09 执行完毕）** | 删 `news-coral-night`，老体系 32 → **31**，与新体系套数对齐。判据与影响面见裁决 15 和 `ARCHITECTURE.md` D23；`path_b_selftest` 86/86、`curate_selftest` 33/33、`layout_selfcheck` 227 文件 0 违规、`audit_pack_contrast` 24 条与删除前同数（D19 的刻意保留项，未受影响） |
| Q2 | `grid.grammar` 有限集的具体成员 | 9 族各一个骨架？还是族内变体共用？P1 编译器最小版必须先定，否则区分度门禁（判据 5）无从计算 |
| Q3 | 变体的区分轴是否够 | 同族 4 变体若只靠色温/字重，是否仍会显同质感？P1 验收时一并判定 |
| Q4 | ~~渲染默认改软件光栅，待裁决~~ **已决（2026-10-10）= 采纳，升为裁决 16** | P1-3e 实测：硬件光栅（引擎默认）两次渲染 1290 帧里编译包差 464 帧、存量包差 710 帧，流哈希也不同；`--no-browser-gpu` 两遍逐帧全同。判据 4a 因此只在软件路径成立，发射器默认已按实测改为软件（`path_b_build.py:2609`）。代价是渲染段变慢（存量包 66.0/63.2s vs 硬件 40.9/36.2s），基线总时长离 102.9s 红线只剩 2% —— 这条代价随 31 套铺开会被重新量一次，见 §11 产能项 |

## 11. 风险与已知张力

- **本设计的成败不在编译器，在原语库的审美水位。** 编译器只忠实展开写进去的东西；原语平庸则 31 套平庸 31 次。所以 P1 是决策门而非进度点。
- **渲染时长与审美直接对撞。** 提速项目刚把单条压进 3 分钟，而 `blur`、大面积 `clip-path`、逐字 span 带来的 DOM 节点膨胀都是每帧成本。`budget` 字段与验收判据 6 是为此而设，不是装饰。
- **`SHARED_TOKENS` 清空会让 `OFF_PALETTE_HEX` 违规量反弹。** D18 那次是 561 条。这次必须**逐包按族重新声明色板**，不能靠机械重映射——`audit_pack_contrast.py:88-91` 那段教训（"审计的判据要跟设计意图一致，不为了让工具变绿而毁掉产物"）照搬有效。
- **人脸检测不是充分条件。** 指认性还有地标、品牌 logo、门牌招牌文字，以及"同图反复出现在同选题"。本轮只解人脸这一维，其余靠 §6.5 的纹理化间接消解（大裁切 + 强压色使图不可识别）。地标/logo 检测列为后续迭代。
- **`WordBoundary` 依赖外部服务**，与"本地零网络"的门禁设计（§6.5）方向相反。`cues.json` 落盘是唯一把外部不确定性变成可复现输入的手段，必须做。
- **`CJK_FAMILY` 子串判定是本设计唯一的静默阻断点，P0 实测把它的故障方向反过来了。** 旧判定是 `"HF CJK" in block`（**子串**），实测有三条静默路径：正文用到未声明的中文族、`local()` 名全写错、自造前缀式族名（`"HF CJK" in "HF CJK Serif"` 为 True）。但**不是**"思源宋体进来不挂审计"那么笼统 —— 产线现用名是中缀式 `HF Serif CJK`，不含该子串，单用它旧闸当场就红（news-policy 能过是因为它黑体宋体**都**声明）。所以两条方向都不许照抄：既不该"怕它挂审计"去放宽，也不该只放宽一条而漏掉三条静默路径。修法（**精确族名集合** + 用到即须声明 + 声明须命中本机已装 `local()` 名）见 P1 第一个提交；六组用例实测见 `routes/news/evidence/2026-10-09-template-v2-p0-probes.md` 附录（含本条的自我订正）。
- **判据 4a 的成立与否取决于光栅路径，而两轮实测互相冲突（未归因）。** P0-4 测的是硬件光栅（`--gpu`）：两遍视频流哈希一致。P1-3e 在同一台机重测，硬件/引擎默认路径**不再一致**（编译包 398/1291 帧像素不同、未改动的 `news-coral` 641/1291，PSNR 58–63dB），同一次发射改 `--no-browser-gpu` 则逐字节一致。两轮的差异变量没有锁定（驱动状态？负载？Chrome 版本？），**所以"软件光栅=确定"目前只是实测相关性，不是被解释的机制** —— 已核到的事实是渲染之前的全部输入（`index.html`、`shots.json`、`subs.ass`、`compositionHash`）逐字节相同，差异只可能出在光栅/编码段。处置：发射器渲染 argv 的**默认支改成软件光栅**（实测耗时 58.2s vs 硬件 ~57s，代价为零），4a 由 argv 保证；真因列入 P4 的确定性哈希门，那时它必须每次出片都数，而不是靠人记得跑一遍。
- **人工审美验收不可自动化。** 判据 1 明确标为人工判断；其余六项全部机判。别把"好看"写进断言里自欺。
