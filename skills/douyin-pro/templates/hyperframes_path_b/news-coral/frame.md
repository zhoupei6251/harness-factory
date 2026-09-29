# news-coral — 设计系统与硬约束

本文件是 **唯一 token 源**。版式文件 (`compositions/*.html`) 与宿主 (`host.html`) 里出现的每一个
色值、字号、时长常数都必须能在这里找到出处；改风格先改这里。

画布基准: `1080 × 1920`（竖屏 9:16）。`1cqw = 10.8px`，`1cqh = 19.2px`。
本版式一律使用容器相对单位（`cqw/cqh`），禁止 `px` 排版（继承旧发射器的 `px` 是它换分辨率即崩版的原因）。

---

## 1. 色板

| token | 值 | 用途 |
|---|---|---|
| `coral` | `#E85D5D` | 主强调：火带、标尺、脊线、序号片底 |
| `coral-dark` | `#D44A4A` | 次级形状（分隔线），**只作形状，不作文字** |
| `cream` | `#F5F0E8` | 墨底正文色；纸面底 |
| `cream-dark` | `#E8E0D4` | 纸面页底（quote 的衬底） |
| `ink` | `#1A1A1A` | 墨底；纸面底正文 |
| `gray` | `#6B6B6B` | 纸面底次级文字（眉标、标签） |
| `light-gray` | `#B0B0B0` | 墨底次级文字（辅助行、步骤说明） |
| `white` | `#FFFFFF` | 片(chip)底、卡底；珊瑚面上的唯一合法文字色 |

### 1.1 对比度实测表（WCAG 2.x 相对亮度）

相对亮度 `L`：ink `0.0554` · gray `0.1471` · light-gray `0.4341` · coral-dark `0.1937` ·
coral `0.2577` · cream-dark `0.7521` · cream `0.8757` · white `1.0`。
对比度 `(L1+0.05)/(L2+0.05)`：

| 组合 | 比值 | 判定 |
|---|---|---|
| cream / ink | 8.78 | ✓ 任意字号 |
| light-gray / ink | 4.59 | ✓ 任意字号 |
| gray / ink | 1.87 | ✗ 禁止 |
| **coral / ink** | **2.92** | ✗ **连大字号(3.0)都不过 —— 墨底上不写珊瑚字** |
| **ink / coral** | **2.92** | ✗ **珊瑚面上不写墨字（"ink-on-fire" 被实测否证）** |
| white / coral | 3.41 | ✓ 大字号（片上文字都 ≥28px） |
| white / coral-dark | 4.31 | ✓ 大字号 |
| coral / white | 3.41 | ✓ 大字号 |
| ink / white | 9.96 | ✓ |
| gray / white | 5.33 | ✓ |
| ink / cream | 8.78 | ✓ |
| gray / cream | 4.70 | ✓ |
| coral / cream | 3.01 | △ 仅大字号，勉强过 3.0；本版式**不用**（见下） |
| ink / cream-dark | 7.61 | ✓ |

> 这一表是本次实现里最重要的一页。旧稿把"珊瑚字在墨上""墨字在珊瑚上"当作好看的常规做法，
> 实测两者都是 **2.92**，在 `hyperframes check` 的对比度审计里属于不通过项。
> 结论写死为两条法则：
> **L1 珊瑚面只当形状；需要文字压在珊瑚上时，用"珊瑚片 + 白字"。**
> **L2 墨底文字只用 cream / light-gray；强调词不染珊瑚，改用珊瑚片衬白字或珊瑚底线（形状）。**
> `coral/cream = 3.01` 离 3.0 只差 0.01，审计器取整方式一变就翻车，因此成片版式一律避开该组合。

### 1.2 纹理与形状

- 45° 网纹：`repeating-linear-gradient(45deg, transparent 0 20px, rgba(0,0,0,.06) 20px 40px)`
  —— 只在珊瑚面上用（`::before`，`inset:0`，`pointer-events:none`，不参与几何与时间轴）。
  墨底页脚纹理改用 `rgba(245,240,232,.05)`（closer）。
- **0 阴影 / 0 圆角**。只有圆形装饰才 `border-radius:50%`，本版式没有。
- 壁纸序号：`rgba(26,26,26,.12)`（12% ink），必须带 `data-layout-ignore="true"`。

## 2. 字阶

| 位 | 字体 | 字号 | 字重 | 其他 |
|---|---|---|---|---|
| 眉标 eyebrow | `"JetBrains Mono", monospace` | `2.9cqw` | 700 | `letter-spacing:.16em`，走白片+珊瑚字 |
| 主标题 display | `"HF CJK", sans-serif` | `10–10.5cqw` | 900 | `line-height 1.22–1.24`，`letter-spacing:-.01em` |
| 小标题 | `"HF CJK"` | `8.4–8.6cqw` | 900 | |
| 巨号数字 | `"League Gothic", sans-serif` | `30cqw` | — | **`line-height:1.12` 是校准值**，更小会与单位基线重叠 |
| 次级数字 | `"League Gothic"` | `7.4–12cqw` | — | |
| 壁纸序号 | `"League Gothic"` | `22–52cqw` | — | `line-height:.78–.8`，12% ink + `data-layout-ignore` |
| 正文/说明 | `"HF CJK"` | `3.4–4.2cqw` | 400 | 墨底用 light-gray，纸面用 gray |
| 屏句(整句) | `"HF CJK"` | `4.4cqw` | 400 | story 专属；88cqw 盒一行 20 字 → 两行封顶（法则 6） |
| 引文 | `"HF CJK"` | `6.4cqw` | 900 | `line-height:1.5` |

- 拉丁显示族（`League Gothic` / `JetBrains Mono` / `Inter`）**只写裸族名**，让 HyperFrames 自动供给并缓存。
  给它们加 `local()` 会让自动下载失效（probe 验证）。
- 中文族固定为 `"HF CJK"`，由每个版式文件自己声明 `@font-face`（`local()` 六连：
  Noto Sans SC / NotoSansSC-VF / Source Han Sans SC / Noto Sans CJK SC / Microsoft YaHei / PingFang SC）。
  原因：`font_family_without_font_face` 审计**按文件**走，且引擎的字体缓存里没有 `noto-sans-sc`。

## 3. 版面法则

1. **内容只占顶部 80%**：底部 `20cqh`（1920→384px）是烧录字幕禁入区，所有 `inset` 下边界一律 `20cqh`。
   这个数是量出来的：`subs.ass` 用 `Alignment 2 / MarginV = h*0.09 = 172 / FontSize = h/32 = 60`，
   块底固定 1748、行距 = 字号 = 60 ⇒ 两行字幕顶边 1628、**三行顶边 1568**
   （`final.mp4` 在 t=7/30/50 逐行像素扫描实测）。旧值 `16cqh`=1613 落在三行字幕里，
   所以发射器同时把每条字幕**封顶两行**（`CAPTION_MAX_LINES`，超长条按时长切成多条）：
   禁入区与字幕行数是同一个约束的两半，只改一半必然还撞。
2. **入场不许越界**：色块入场用 `scaleY(0→1)` + `transform-origin:50% 0%`（或 `scaleX` + `0% 50%`），
   禁止 `y:"-100%"`（旧 probe 因此产生 6 条 `container_overflow`/`panel_out_of_canvas`）。
3. **入场色块面上无文字**：文字是独立层、独立补间（几何与对比度都更好控）。
4. **壁纸位只放序号**，不放统计值：壁纸大字会与主数字抢读，且容易被当成第二个事实。
5. **禁止编造比例与对比**：源数据没有诚实分母时不画比例条（旧 probe 的 bar 永远满格就是假数据）；
   同一个镜头凑不出两个有出处的数字时也不画对比块——第二个数没有来源，画出来就是在替当事人造事实。
6. **屏上的字分两级，两级都不许是口播句**（判据 5 的结构保证；配音只念 `body`，见发射器
   `synthesize_audio`）：
   - **整句型屏上位**（story 的屏句位 / hook 的辅助行 / closer 的行动句）**唯一取材处是作者写的屏句**
     （markdown 的 `屏:` 行，或 JSON 的 `"onscreen"`）。长度 5–16 字（`ONSCREEN_MIN/MAX_CHARS`，
     上限来自 story 屏句位 4.4cqw 在 88cqw 盒里两行的容量）。正文里被念出来的任何分句
     **一律不许**作为整句上屏——旧 `lead/detail` 直接从正文取句，等于把字幕二次上屏。
   - **行式说明位**（catalog 的 `stepNBody`、rail 的 `itemNValue`）只能放**不构成整句**的名词短语：
     说明 ≤`ROW_BODY_MAX_CHARS`=42 字（3.4cqw 在 74cqw 盒里一行 21 字 × 两行），超一点就整条拒收，
     因为三行说明会把清单顶进法则 1 的禁入区。
   - **强调段（珊瑚片）只有两个合法断点**：作者点的 `｜`，或原文里的"数字+单位"。两者都没有就当
     这一镜没有可强调的一段（该版式落选）。旧实现兜底 `text[-4:]` 硬切尾巴，实测产出
     墨字"困" + 珊瑚片"住半辈子"——切在词中间的珊瑚片就是 t001 最难看的一处。
     标题行里的 `｜` 只当**换行点**（`HEAD_BREAK_CHARS`），标记本身一律不上屏。
7. `gsap_css_transform_conflict`：被 GSAP 补间 transform 的元素**禁止**在 CSS 里写 `transform`
   （`transform-origin` 安全）。
8. **面用 transform 入场，墨才用 opacity**：自带 `background` 且承载文字的元素（片块/卡片）**禁止**
   opacity 补间。实测证据（probe6a，`check --strict --json`）：`#h-eb` 白片在 α≈0.72 时
   有效底色被合成为 `rgb(246,213,213)`，珊瑚字掉到 **2.5:1**（要求 3:1）→ `contrast_aa_failure`。
   审计器的模型是**前景色取原值不乘 alpha、元素自身背景按 alpha 与地面混色**——所以纯文字淡入不会被判
   （同一次运行里 `#rl-ttl` α≈0.65 未被记录），而"有底色的片块淡入"必被拖下水。
   片块一律 `scaleX: 0→1` + `transform-origin: 0% 50%` 擦入，与火带/标尺/脊线共用同一套形状语言。
   审计取样落在 host `t=0.5s` 起、每 2s 一次（9s 片 → `[0.5,2.5,4.5,6.5,8.5]`），整数秒挂载的镜头
   必然暴露**局部 ≈0.5s** 那一帧，因此该帧上所有带底色的文字必须已经 α=1。
9. **被 GSAP 引用的元素必须有 `id`**：选择器解析成空数组时 GSAP 只打 console 警告
   （文案 `GSAP target  not found.`，**两个空格**即空目标），`--strict` 会因此不过。
   `rail.html` 的 `.rl-head` 漏 `id` 就是靠这条抓出来的（表头从此不呼吸）。
   发射器自检：扫每个版式的 `fromTo("…")/to("…")` 目标，逐个比对同文件的 `id="…"`。

## 4. 动量预算（每个版式必须满足）

```
INTRO_END = 1.5   // 入场节拍上限（hero 在 t≤0.5s 可见，禁止把内容堆在最后）
MIN_DRIFT = 0.6   // 呼吸位移下限
driftStart = max(0, min(INTRO_END, slot - MIN_DRIFT))
driftDur   = max(MIN_DRIFT, slot - driftStart)
```

- 补间一律 `fromTo`（`from()` 在 seek 回退时失步）。
- 漂移作用在**内容容器**（`.h-field` / `.st-plate` / `.rl-rows` / `.qt-card` / `.cb-rows` / `.sy-field` / `.cl-field`），
  绝不作用在带 `.clip` 的挂载元素上（lint `gsap_animates_clip_element`）。
- 非末帧禁止写退场。末帧（closer）也只保留漂移，不做淡出——判据 3 对每一镜都成立，包括最后一镜。
- `slotSeconds` 由宿主逐实例传入；版式内部据此算预算，因此同一 layout 文件挂 N 次、每次时长不同都合法。

## 5. 版式清单与地面

| layout | 地面 | 文字色 | 珊瑚的出场方式 |
|---|---|---|---|
| `hook` | ink | cream / light-gray / 白片珊瑚字 | 顶部火带(形状) + 强调词珊瑚片 + 标尺 |
| `stat` | cream | ink / gray | 标尺 + 对比区分隔线（纯形状） |
| `rail` | cream | ink / gray | 左侧脊线（`scaleY` 擦入） |
| `quote` | cream-dark + 白卡 | ink / gray | 卡顶边 + 破折号 + 巨引号(装饰) |
| `catalog` | ink | cream / light-gray / 珊瑚片白字 | 序号片 + coral-dark 分隔形状 |
| `story` | **light↔dark 逐镜翻转**（唯一声明 `tone` 的版式） | light 面: ink / gray；dark 面: cream / light-gray | 白片珊瑚字眉标 + 珊瑚标尺(形状) + 序号水印(装饰层) |
| `closer` | ink | cream / light-gray / 白片珊瑚字 | 顶部火带(形状, 与 hook 同几何 22cqh + 贴片 17cqh = 书挡) + 强调词珊瑚片 |

三段混调（用户选定）= 同一系统换地面，不做三套 token：
`hook/stat` 墨↔纸大色块对撞（钩子），`rail/quote` 纸面（叙述），`catalog/closer` 回墨（行动收口）。
`story` 是中间那个可翻面的铰链：它跟上一镜取反（发射器 `_tone()`），所以首末两个墨底书挡之间
一定有明暗交替，而不是靠镜号奇偶赌运气。
