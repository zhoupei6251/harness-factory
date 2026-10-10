# P1-3 前置摸底：编译器必须对齐的契约面（2026-10-09 实测）

这份清单只干一件事：把"新版式能不能被现有产线驱动"这个问题**在写代码之前**问完。
每条都是读源码得到的，行号是 2026-10-09 的 HEAD。契约面共 10 处，其中 3 处是硬停机（不改就装不上包）。

## A. 装包期（`path_b_build.load_pack`，:1240-1303）

| # | 契约 | 位置 | 违反后果 |
|---|---|---|---|
| A1 | 包目录必须有 `host.html` + `compositions/` | `:1247-1252` | `EmitterError` 硬停机 |
| A2 | `compositions/placeholder.html` 不算版式；剩 0 个版式即"不可渲染" | `:1257`、`:1293-1301` | 硬停机，并列出当前可渲染包 |
| A3 | `<html>` 上必须有 `data-composition-variables='[…]'`，`html.unescape` 后是合法 JSON | `VARIABLE_ATTR_RE :260`、`:1260-1269` | 硬停机 |
| A4 | 根节点必须 `<div id="root" data-composition-id="…">` | `ROOT_COMPOSITION_ID_RE :263`、`:1264` | 硬停机 |
| A5 | **`#root { … background:#rrggbb }` 本体**（带属性选择器的 `#root[data-tone=…]` 不算地面） | `ROOT_GROUND_RE :269`、`:1270-1275` | 缺声明硬停机 |
| A6 | 该地面 hex 必须已在 `GROUND_TONE_BY_HEX` 登记归明/归暗 | `:274-298`、`:1277-1283` | 硬停机，报"未登记的地面会让逐镜换色失效" |

A6 的现状实测：`GROUND_TONE_BY_HEX` 现在 **56 条 hex**（`len()` 现算），其中 **50 行注释写着 `auto-extended`**
—— 即这张表是**跟着包手涨的**，只有最初 6 条是设计时定的。
旗舰包的两个地面 `#f5efe3`(paper) / `#e8dfcb`(paper-dark) **已在表内**（`:279-280`，来自 news-paper/news-policy），
所以 P1 不用改它。但 P5 铺到 31 套新包时这条必然失效：地面明暗应当从 spec 的 `color.surfaces` +
相对亮度现算，而不是维护一张手写 hex 表。**这是 §6.6 该收的一项，本轮只记录不动手。**

## B. 发射期（变量能不能填出来）

- **发射器不认包名、只认变量 id**：`DERIVERS`（`:1573-1595`）按 id 查推导器，`INDEXED_VAR_RE`
  （`:1598`，`^(item|step)([1-9])(Label|Value|Body)$`）按需挂表（`register_indexed_derivers` `:1601`）。
  ⇒ 编译器只要**复用现有 id 词表**（`kicker/headTop/headBottomLead/headAccent/support/onscreen/value/unit/label/
  compareValue/compareUnit/compareLabel/quoteBody/attribution/channel/cta/ctaAccent/tone` + `itemN*/stepN*`），
  新版式零改发射器代码。用了表外 id ⇒ `missing_variables()`（`:1610`）判它填不出来，`choose_layout` 直接落选该版式。
- `slotSeconds` 是保留变量（`layout_selfcheck.SLOT_VARIABLE :46`），宿主逐实例传入，版式内部据此算动量预算。
- `TITLE_LANDING_VARS = {title, headTop, headBottomLead, headAccent}`（`:230`）：标题行必须有落点，
  选中的版式没标题位就发⚠（README 排障表最后一行）。
- 挂载几何：`MOUNT_TPL`（`:396`，画面固定 `data-track-index="1"`）、`AUDIO_TPL`（`:416`，配音 0 轨）、
  `AUDIO_MOUNT_HEADROOM_SECONDS = 0.05`（`:415`，浮点进位实测 2e-15 → `duplicate_audio_track` → `--strict` 拒渲染）。
- 宿主占位符只有 `{{COMPOSITION_ID}} {{W}} {{H}} {{TOTAL}} {{SCENES}} {{AUDIOS}}`；
  **注释里不得出现带花括号的原文**（`emit_host` 的自检 `:1748` 就是数这个串出现次数）。

## C. 结构闸（`layout_selfcheck.py`，逐文件）

`NO_TEMPLATE` / `NO_ROOT_COMPOSITION_ID` / `NO_TIMELINE_REGISTER` / `MISSING_SLOT_VARIABLE` /
`MISSING_TWEEN_TARGET`（`#id`、`.class` 两类目标都要在**同文件**存在）/
`MAGIC_BUDGET_VALUE`（`BUDGET_CONSTANTS = ("INTRO_END","MIN_DRIFT")`，`:49`，必须 `const X =` 具名声明）/
`MISSING_DRIFT_DURATION` + `MISSING_CONTINUOUS_MOTION`（必须算出 `driftDur` 且**至少一条补间用它**，否则尾段冻住）/
`CAPTION_RESERVE_INTRUDED`（`bottom:` 与 `inset` 下边界都不许进 20cqh）/
`PX_TYPOGRAPHY`（`font-size/line-height/letter-spacing/padding/margin/inset`… 禁 px；`PX_ALLOWED_PROPS :71` 只放行 background 系与 mask-image）/
opacity×background（`:335-352`，法则 8）/
四条 CJK 闸（P1-1 落地的 `MISSING_CJK_FONT_FACE`、`CJK_FAMILY_USED_NOT_DECLARED`、`CJK_FONT_LOCAL_NOT_INSTALLED`、拉丁族禁 `local()`）。
CJK 族名集合只有两个：`("HF CJK", "HF Serif CJK")`（`:59`）；`local()` 候选必须**至少命中一个**
`CJK_INSTALLED_LOCALS`（`:65`，实测在装 5 个：Noto Sans SC / Microsoft YaHei / Noto Serif SC / SimSun / DengXian）。

## D. 色板闸（`audit_pack_contrast.py`）

- 认 frame.md 的两张表：`| token | 值 |` 色板（`parse_palette :212`）与 `| 组合 | 比值 | 判定 |` 对比度表
  （`parse_ratio_claims :225`）；表头指纹在 `:56`。只认列名不认小节号。
- `DOC_RATIO_DRIFT`：文档里写的比值必须能被 `contrast_ratio()`（`:162`）复算出来 —— **编译产物天然占优**，
  frame.md 由 spec 生成时这一条是按构造成立，不是靠人抄对。
- `OFF_PALETTE_HEX`（`:290-311`）：版式与宿主里每个 hex 都要在本包色板找到出处。
  **但它有 `SHARED_TOKENS` 后门**（`:110-132`，17 个跨包共享 hex）。实测 news-coral 的
  `#0a0a0d / #c0392b / #dcdcdc` 都不在自家 frame.md §1，靠这个后门才 0 findings。
  ⇒ 与裁决 12（清空 `SHARED_TOKENS`，族间共享角色不共享色值）直接冲突。
  **本轮结论**：path_c 的包必须"自家色板自足"，编译器不许依赖后门；后门的关闭时机排在 P4（审计上移），
  现在先把这条写清，避免 P5 铺 31 套时把共享 hex 当成合法解。
- 现状基线：31 包 24 条违规（`news-thread`/`news-explainer` 各 4 条最多），P1 期间**不许变动**，
  它是老包的历史债，不是新包的验收线。

## E. 老包 frame.md 已经在漂移（真源上移的实证）

`news-coral/frame.md` §1 声明 8 个 token，§2 字阶写"主标题 10–10.5cqw / 正文 3.4–4.2cqw"，
而 `compositions/hook.html` 实际用 `#root{background:#0a0a0d}`、`.h-band/.h-ac/.h-hair{background:#c0392b}`、
`.h-sup{color:#dcdcdc}` —— **这三个色值没有一个在 §1 表里**（§1 的 ink 是 `#1A1A1A`、coral 是 `#E85D5D`、
light-gray 是 `#B0B0B0`）。其余 `#f5f0e8`(cream)、`#ffffff`(white) 确实对得上，所以漂移是局部的、
更容易被当成"没问题"。文件头还写着"本文件是唯一 token 源…改风格先改这里"。
这不是抓取失败，是**手抄契约的必然结局**：`frame.md` 与 HTML 由不同时期不同人改，两道闸都拦不住"文档没跟上"
（色板闸放行了共享后门，结构闸不看色值）。§6.3 把真源上移到 spec、`frame.md` 降级为编译产物，理由在此落地为实测。

## F. 由此定的编译器边界（P1-3c 的验收口径）

1. 产物目录：`templates/hyperframes_path_c/<pack>/{spec.toml, host.html, compositions/*.html, frame.md}`（裁决 14 双轨）。
2. 版式名严格等于 `hf_style_spec.CANONICAL_LAYOUTS`（7 个），与发射器 `AUTO_LAYOUT_STEMS`（`:223`）已由测试锁相等。
3. 变量 id 只从 B 的词表取；新 id 必须先加推导器再上版式。
4. 所有色值取自 spec 的 `color.surfaces` / `color.text[].hex`，写进自家 frame.md §1，不借 `SHARED_TOKENS`。
5. 动效一律 `fromTo`、原语自带 `INTRO_END/MIN_DRIFT` 具名常数与 `driftDur` 持续位移；随机在编译期烘焙（法则 10）。
6. 三道闸 + `hyperframes check --strict`（产线口径：`--strict --json --caption-zone=…`，**不带** `--at-transitions`）全绿才算出包。

## G. 一处必须改措辞的地方：`char-rise` 的"构建期切 span"在版式里做不到

§6.2 写"逐字 = 构建期按码点切 span"。P0-1 探针（本文档 `…p0-probes.md:36-47`）确实是构建期切好的 ——
但那是**探针**：文本写死在探针页里（18 个码点）。版式文件不是：`path_b_build.py` 把 `compositions/*.html`
**逐字节复制**进 `work_dir/compositions/`，同一份版式挂 N 次、每次文字不同，文字只在运行时经
`data-variable-values` → `window.__hyperframes.getVariables()` 进来（`:1240-1303` 的装包路径 + `MOUNT_TPL :400`）。
⇒ 编译器生成时**拿不到那一镜的字**，只能生成"切分代码"，不能生成"切好的 span"。

可行的落点仍是脚本体内**同步** split（不是 `onStart`）：`getVariables()` → 按码点建 span →
一条 `fromTo("#x .cr-ch", {…}, {…, stagger})`。seek 安全性与探针等价 —— 探针之所以稳，
关键是"补间在时间轴创建时就已存在、且不用 `from()`"，而不是"span 由谁建"。
这条要在 P1-3e 用真版式实测（同镜两次抽帧哈希一致）才算立住，现在是推断。

顺带两个闸的细节，编译器要照着写才不踩：
- `MISSING_TWEEN_TARGET` 的 class 收集是 `collect_elements`（`layout_selfcheck.py:232-239`）用
  `<[a-zA-Z][^>]*>` 扫**整个 template HTML（含 script 文本）**，所以 JS 字符串字面量里的
  `class="cr-ch"` 会被认作存在的类 —— 别把它当特性依赖，但要知道它不会拦。
- `CONTRACT_ID_MISMATCH`（`:315`）：根 `data-composition-id` 集合必须与 `window.__timelines["…"]`
  键集合**完全相等**，多一个少一个都不行。


**P1-3b 落地（2026-10-09）**：`hf_primitives.char_rise` 就按上面这条实现 —— 脚本体内
`Array.from(String(vars[id] || "").trim())` 同步切码点、建 span、发**一条** `fromTo(".{ident}-ch", …, stagger)`，
容器里另留一个静态 `<span class="{ident}-ch">` 占位（空镜兜底，且让结构闸在真标记上看见这个类，
而不是靠 JS 字符串的形状 —— 上面那条"字符串里的 class 会被认作存在"因此不是可依赖的特性，是已知噪声）。
副作用一条：法则 10 的 `.from(` 禁令不能用子串判，`Array.from(` 会误伤招牌原语本身（第一版实踩），
现走 `GAP_FROM_RE = (?<!Array)\.from\(`。**同镜两次抽帧哈希一致仍未测**，那是 P1-3e 的验收项。

## H. P1-3c 落地：旗舰包出包 + `hyperframes check` 的四条实测信号（2026-10-09）

`hf_compile.py`（spec.toml → `host.html` + 7 版式 + `frame.md`，9 个文件）已按 §F 的六条边界落地，
四道闸全绿。下面只记**只有真跑引擎才知道**的部分 —— 每条都在同一台机、同一份探针脚本上复测过，
探针口径 = `--strict --json --caption-zone=…`（不带 `--at-transitions`），fixture 值取契约的 `default`。

| 包 / 输入 | lint | runtime | layout(err/warn/info) | motion | contrast(查/过) | `ok` |
|---|---|---|---|---|---|---|
| `news-editorial-warm`（编译包，在约文字） | 0/0/0（8 文件） | 0/0/0 | 0/0/0 | `enabled:false` | 20/20 | true |
| `news-coral`（存量包，同一探针） | 0/0/0（8 文件） | 0/0/0 | 0/0/0 | `enabled:false` | 24/24 | true |
| `news-editorial-warm` + 30 字塞进每个文本位 | 0/0/0 | 0/0/0 | **80/0/0**（全 `content_overlap`） | `enabled:false` | 18/18 | false |
| `news-coral` + 同样越约 | 0/0/0 | 0/0/0 | **7/1/15**（`content_overlap`×6、`caption_zone_collision`×1、`escaped_container`⚠、`canvas_overflow`×9/`text_box_overflow`×4/`container_overflow`×2 ℹ） | `enabled:false` | 24/24 | false |

四次跑的都是 `duration: 28`（7 镜 × 4s）、`layout.samples: 10`、`transitionSamples: []`。
**`motion` 段 `enabled: false` ⇒ 它那三列零是空转，不是证据**；转场采样同理为空（口径里没带
`--at-transitions`）。这条必须写死在读表方式上：本口径只证明 lint / runtime / layout / contrast 四段。


### H1 `invalid_inline_script_syntax`（error，一处坏 → 全版式死）

原语的 DOM id 是 kebab（`ew-hk-top`），早期版本直接把它拼进 JS 局部名：
`const ew-hk-topChars = …` ⇒ 整段 `<script>` 语法不合法，**七个文件每套都报 error**，
而结构闸和色板闸全都没意见（它不看 JS 词法）。修法：`hf_primitives.js_name()` 做 kebab→camel
（`ew-hk-top` → `ewHkTop`），`char_rise`/`photo-duotone`/`photo-local-crop` 三处派生名改走它；
同时把这条禁令上移成 Python 断言 —— `fragment_violations` 现在用 `JS_DECL_NAME_RE` 扫每条
`const|let|var` 的左值，非 `JS_IDENT_RE` 直接拒编。代价是命名口径必须统一：`ew-hk-top` 与
`ew_hk_top` 会撞成同一个局部名，所以 ident 只许 kebab（`pack_prefix` + 配方表保证）。
`photo-local-crop` 是第一轮漏掉的那个，被自家 kebab 全量扫描测试（遍历 `P0_NAMES` 拿 kebab id 渲染）逮住。

### H2 `container_overflow`（info，不影响退出码 ⇒ 必须自己变成断言）

`#root > * { position:absolute; inset:0 }` + `drift-y` 的 `yPercent` 相对自身高度 ⇒ 满幅内容层上移
时**自己的顶边**离开带 `overflow:hidden` 的 `#root`。同稿对照实测：内容层收成真实区间
（`_content_span()`，七套收到 8.5–12cqh 顶边 / 56–68cqh 层高）后 **6 条 info 归零**；
把七条规则改回 `inset: 0` 立刻复现 `6×(info, container_overflow)` 且 `rc` 仍是 0。
⇒ 结论不是"引擎会提醒我们"，而是**它不会**：info 级不改变 `--strict` 退出码，31 套一起刷同一条
噪音时真越界就没有信号。因此收进 `geometry_violations`：`span_top ≥ |DRIFT_Y_PERCENT|/100 × 层高`，
以及"存在无 `top` 的步骤（P3 全幅图层）⇒ 拒编"，两条各有反例测试（`⑥⑦` 分支）。
位移量随之从 `-2.2` 改 `-3`（`DRIFT_Y_PERCENT`）：存量包的 `#*-field` 漂移都是 `-3`、注释自陈
吃掉 1.7cqh，编译层高 ≈60cqh × 3 % = 1.8cqh，P1-3e 并排比帧时深浅才同级。

### H3 越约文字：包不是防线，发射器才是 —— 但发射器有两个缺口

`hf_compile` 按 `Step.height_cqh`（最坏行数）核几何，所以**版式在契约内**永远不重叠；越约输入
（30 字塞 `headTop`）炸出 80 条 error，而 `HOOK_LINE_CHARS=7`（`path_b_build.py:184`）这类截断
发生在发射器侧 —— 真产线不会把 30 字送进 `headTop`。**没有上界的只有两个**：
`QUOTE_MIN_CHARS=8`（`:195`，只有下限）和 `statLabel` 只有 `STAT_LABEL_MIN_CHARS=3`（`:1010`）。
⇒ `quoteBody`/`statLabel` 是本表里唯一能合法穿过发射器截断、把版式顶进 `content_overlap` 的路径。
另一条差距：`news-coral` 越约时报 7 条而不是 80 条，靠的是 `story.html:218` 的运行时 `fitCqw()`
自动缩字号；编译包**没有**复刻它（也与法则 10 的口径需要一次裁决）。两项都记为待办，本轮不动手。

### H4 一处推翻：`contrast_aa_failure` 没复现

上一轮在 `news-coral` 的 `stat.html` 见过 `contrast_aa_failure`（warning）。本轮同一探针、同一口径
在约（24 查 24 过）与越约（24/24）两次跑，`contrast` 段都是 `enabled: true`、0 warning，
**未复现**。按"数不到的就不写"处理：不进本表、不作为已知缺陷。要追它得先还原当时那份 fixture 文本，
优先级低于 P1-3e。

### H5 顺带三条编译期才看得见的发射器事实

- `emit_host`（`:1728-1735`）要求 `HOST_PLACEHOLDERS`（`:256`）**六个** `{{…}}` 一个不缺，
  所以编译产物里的宿主骨架必须**留着占位符**（画布宽高、合成 id 由装包时给，包不携带全片尺寸）。
- 占位符填充是 `str.replace`（`:1736-1742`，**全局**替换）⇒ **注释里也不许出现双花括号原文**，
  否则那处也会被换成挂载片段。本编译器的宿主模板占位符普查为
  `{{COMPOSITION_ID}}`×2 + 其余五个各 ×1，与存量包 `news-coral/host.html` 的普查**逐位相同**
  （2026-10-09 `grep -o | uniq -c` 现算）。多写一处占位符不会被 `emit_host` 拦住（它只查缺、
  不查多），所以这条计数由 `t_hf_compile_pack_loads_through_the_real_emitter` 盯住；
  编译产物只填包名，六个占位符一个都不动。
- `audit_pack_contrast` 认的是**表形状**，不是内容：色板表头必须是 `| token | 值 | … |`、
  比率表必须是 `| 组合 | 比值 | 判定 | … |`（比值第 2 列、判定第 3 列），否则整表被判
  `NO_PALETTE_TABLE` 而**静默放行**。`frame_md` 已按这两个指纹产出，并有测试断言
  `audit_pack` 对旗舰包返回 `[]`；文字色也进了 token 表，免得 `OFF_PALETTE_HEX` 把字色当越板。

## I. P1-3d 落地：pack 根接缝（裁决 14 双轨）+ 禁忌断言注册表（2026-10-09）

### I1 先量到的是：**旗舰包犯了自家禁忌，而三条禁忌一条都没实现**

`spec.toml` 声明 `entrance-not-faster-than-0p5s`，实测产物里有 **11 条入场低于 0.5s**：
`7 × duration: 0.4`（`#{p}-{tag}-kicker`，`block_chip` 默认值 `hf_primitives.py:312`）
+ `4 × duration: 0.45`（`#{p}-{hk,qt,sy,cl}-bar`，`rule_pull` 默认值 `:262`）。
`no-overshoot`、`no-border-radius` 两条则**连读取者都没有** —— 全仓 `grep taboo` 只有
`hf_style_spec` 的结构校验（名字是不是 kebab、有没有 `why`）和 `frame_md` 的**打印**。
这正是法则 13 要防的形态：写进 spec 的禁忌如果只被"列出来"，31 套就等于 0 套约束。
同一条假话还写在 `hf_primitives` 模块注释里（"forbidden 里的缓动另有一道断言"）—— 注释说的
那道断言此前不存在。

### I2 下限修在原语里，不修在配方里

修法选了 `dur = max(tok.entrance_min, duration)`（`hf_primitives.py:270`、`:323`），
**没有**在 `hf_compile._steps` 里写 `duration=0.5`。理由：`_steps` 是 31 套共用的七套版式，
把杂志族的下限写进共用配方就等于宣布号外族（招牌 ≤0.9s、`back.out(2.8)` 过冲）拿不到 0.4s 的
快入场。族差别因此只经由 `motion.entrance-min-seconds` 这一个 spec 字段流动，与
`char_rise`（`:229`）、`cue_fade`（`:382`）已有的 `max(下限, …)` 口径一致 —— 入场下限
**按构造成立**，注册表那条断言则负责在有人把 spec 下限调到低于自家禁忌时说真话。
修后实测时长普查：`25 × 0.5 / 9 × 0.6 / 13 × 0.7 / 7 × 1.4`，最小 0.5s。

### I3 注册表的三条闸（`hf_compile.py:687-816`，接在 `compile_violations:860-861`）

- `scan_entrances()`（`:709`）只认 `tl.fromTo("<sel>", {起}, {…, duration: D, …}, <数字秒>)`。
  位置参数必须是数字字面量：命名位置是呼吸位移/衔接，不该吃入场下限（实测 7 条
  `tl.to(…, driftStart)` 因此被正确排除）。**计数拿 `text.count("tl.fromTo(")` 对** ——
  形状一改正则就会静默少认，而"少认"在禁忌闸里等于通过；实测 54/54 认全、0 漏网。
  认出来却没有 `duration` 字面量的也算漏网（GSAP 默认 0.5s，闸数不到）。
- `easing_violations()`（`:735`）**无条件**跑（`motion.easing` 是 spec 必填层，不进注册表）：
  全文扫 `ease:` 取值，`_ease_head()`（`:699`）取点号前那段与 `forbidden` 比；
  `allowed` 只约束**入场**。`ease:"none"` 是位移层的法则级词汇（7 条漂移补间都在用），
  塞进杂志族的 `allowed` 反而会让"招牌缓动"这条判据失真。
- `taboo_violations()`（`:793`）按 `taboos[].check` 取名：精确名查 `TABOO_CHECKS`（`:787`），
  `entrance-not-faster-than-<N>p<M>s` 由 `ENTRANCE_FASTER_RE`（`:696`）解析参数
  （`p` 代替 `.` 是因为 `hf_style_spec.KEBAB_RE:85` 不许点号进名字）。
  **取不到实现就拒编**，报错带上 spec 的 `why` 原话 —— 这条是 P5 的强制函数（见 I5）。

踩过的坑：`forbidden` 里写的是 `back.out`，第一版按全文子串比 ⇒ `grep -ic 'back'` 在七个文件里
各命中 4-5 次，全是 `background:`。所以"先取 `ease:` 的值、再切点号前段"两步都不许省。

### I4 每条闸都被真的坏写法触发（负控，2026-10-09 现跑）

`t_hf_compile_taboo_registry_executes_every_declared_check`（`path_b_selftest.py:2432`）走
spec 真变异 + 产物文本注入，共 5 个分支。逐个把闸拆掉后重跑，**六个变异全部转红**：
`taboo_violations` 恒空 / `TABOO_CHECKS` 清空（→ ① 散文那条报出）/ `_taboo_no_overshoot` 恒过
（→ ② 红）/ `_taboo_no_border_radius` 恒过（→ ④ 红）/ `_taboo_entrance_floor` 恒过（→ ③ 红）/
`scan_entrances` 吞掉漏网（→ ⑤ 红）；`easing_violations` 恒过同样转红，证明它与注册表是
**两个独立证人**（② 里 `no-overshoot` 被拆掉时，forbidden 那一半仍自己报案）。
全量：`path_b_selftest.py` **117/117**；结构闸 7 文件 0 违规；色板闸 1 pack 0 警告；
引擎 `check . --strict --json --caption-zone=…`（不带 `--at-transitions`）`rc=0`、`ok=true`，
lint/runtime/layout/contrast 四段 0/0/0（`motion.enabled=false` ⇒ 那段零仍是空转，口径同 §H）。

### I5 pack 根接缝：两代包在一个进程里同时可点名

`path_b_build.py:114-162` 新增 `PATH_C_ROOT` / `PACK_ROOTS`（顺序 = 查找优先级）/
`set_packs_root()`（测试与工具换根）/ `pack_dir()`（取第一个**存在**的 `<root>/<style>`）/
`available_templates()`（手写名单在前、按目录自动补在后，认 `host.html` 才算数）。
`--template` 的 `choices` 从 argparse 挪到解析后校验（`:2479`）—— 可寻址范围取决于磁盘现状，
写死 choices 的包每次加一套都要改发射器。新增 `--list-templates`，实测打印 **32** 个名字，
末位是 `news-editorial-warm`（编译包），前 31 个是手写名单。
P5 因此不需要为每个新包动 `path_b_build.py`：**加包 = 写 spec + 编译**。

### I6 P5 的账：其余各族的禁忌还没有实现

§5 表里除杂志族外的禁忌 —— `fade`（号外/霓虹）、匀速 `none`（街采）、对称与完美对齐（街采）、
阴影与 chip（胶片）、暖色（霓虹/胶片）、serif（竞技）、>1s 与 >0.8s 的**上限**（号外/竞技）、
同窗并动元素数（数据/图解）、无出处比例（数据/图解）、装饰动效（瑞士/数据）——
注册表里都还没有对应名字。它们写进 spec 的当下就会被 I3 那条"没有实现 ⇒ 拒编"顶回来，
这是有意的：铺 31 套时每族的禁忌必须**先写断言再上版式**，不许出现"spec 写了、闸没写"的第二轮散文。
上限型（`>1s`、`>0.8s`）与 `entrance-not-faster-than` 同族，加一个 `entrance-not-slower-than-<N>p<M>s`
即可复用 `scan_entrances`；计数/比例/颜色型要新的取数面（P5 起手项）。

---

## J. P1-3e/f 落地：法则 18 + 决定性重测 + 审美门素材（2026-10-09）

这一节量三件事：一处**真的上了片**的缺陷怎么变成一道能跑的闸；判据 4a 与 P0-4 的结论
互相打脸时谁是真的；以及最终几何上六项机判的重测数字。

### J1 缺陷：眉标色带横穿标题（并排帧实测，不是推演）

编译产物首帧里，`#ew-hk-kicker`（带 `#B45309` 底色的 `block-chip`）与它下面那行标题的
**行盒**重叠。两处交叠量出来（重建值 —— `hf_compile.py` 当时还没进版本库，"改前"取不到
第二份文件，只能按改前那组 `top/left/max-width` 入参复算同一套盒式）：

| 对 | 横向交 | 纵向交 | 后果 |
|---|---|---|---|
| `hk-kicker` × `hk-title1` | 6.72cqw | 0.59cqh | 琥珀色带从标题字中部横穿 |
| `rl-title` × `rl-ordinal` | 4.00cqw | 6.58cqh | 标题与巨号序数叠成一团 |

四道门禁当时**全绿**。这不是闸写坏了，是闸的**范围**没覆盖：结构闸量 px / 留白 / 禁入区，
色板闸量对比度，引擎 lint 量 seek 安全，没有任何一道量"两个文字位是否压在彼此头上"。
带底色的位子尤其危险 —— 它画出来的不是字，是**面**。

### J2 修法：法则 18 —— 文字位必须声明栏宽，且两两不得交

关键不是"把 top 调大两格"，而是**让右沿可判**。绝对定位只写 `left` 时盒宽是收缩量
（上限 `100 − left`），"这一位会不会伸到下一位头上"在编译期根本算不出来 ⇒ 任何重叠判定
都是纸面数字。写了 CSS `max-width` 之后盒宽由**浏览器**钉死：字太长就折行（变高，那是
占位行数的事），不会悄悄变宽。原语侧三个载体各加一个可选参数（`hf_primitives.py` 的
`block_chip` / `giant_numeral` / `keyword_tint`），不写就落不进 CSS。

`hf_compile.py:751-811` 新增 `text_box()` + `overlap_violations()`，接在
`compile_violations` 几何段之后（`:1007`）。三条分支各对应一种实测失效：缺声明（拒编 ——
只看写了栏宽的那些位就是假绿）、越出安全幅、两盒相交。右沿口径有个坑：`max-width` 管
**内容盒**，片的底色画到边框盒为止，所以 `block-chip` 右沿 = `left + max_width + 2×pad_h`
—— 那道横穿的色带正是差在这 3.8cqw 上。

41 个文字位全部声明了栏宽，来源两种，不许混：

- **字形推出来的**（数字位、眉标片）：`kicker_width()` / `numeral_width()`
  （`hf_compile.py:178-190`）。系数是量的：`LATIN_DIGIT_EM = 0.569` 从成片帧上 16cqw 两位
  序数的墨盒宽 18.20cqw 反推（`pair/probe-ord.png`），`CJK_CHAR_EM = 1.0` 取保守上界
  （汉字实际 ≈1em，拉丁/数字更窄 ⇒ 按 1em 估只会偏宽，不会漏判相交）。
- **设计选的**（整句位）：写栏宽字面量。`hk-accent` 与它上面两行标题同栏 88.0（强调行不许
  比正文先折），`st-cmp` 30.0（9.5 起算右沿 39.5，正好让在 42 起的对比说明左边）。

序数位因此从"写死 left"改成**由栏宽反推位置**：`left = 94 − numeral_width(16)` ⇒ 产物
`left: 75.79cqw; max-width: 18.21cqw`，右沿正落在 94 的安全边上。两处标题 top 相应抬格
（rail 16.5→19.0、catalog 16.0→18.5）让出色带下沿。

### J3 三条分支都被真的坏写法触发

`t_hf_compile_text_positions_have_columns_and_never_touch`（`path_b_selftest.py:2430`）先正向
断言 41 位全有栏宽、七套版式 `overlap_violations == []`，并断言 `max-width: 22.4cqw` /
`left: 75.79cqw` / `max-width: 18.21cqw` **真的出现在产物 HTML**（参数落不进 CSS 的话，
前两条断言会一起假绿）。然后三个变异各打一条分支：标题 top 压回 13.0 ⇒ 恰好 1 条同时含
"相交"与"法则 18"、其余版式不受影响；`pop("max_width")` ⇒ "没声明 max_width"；
story 标题 `max_width=90.0` ⇒ "越出安全幅"。

### J4 判据 4a 与 P0-4 冲突：软件光栅才是确定的，硬件不是

P0-4（`2026-10-09-template-v2-p0-probes.md`）记的是"两次渲染逐字节一致 ⇒ 同稿同片成立"。
本轮在最终几何上重跑，**硬件路径（引擎默认，ANGLE / 本机 Intel Arc）不再复现**：

| 轮 | 光栅 | 对象 | 帧数 | 不同帧 | 视频流 sha256（前 20） |
|---|---|---|---|---|---|
| warm-g / warm-h | 硬件 | 编译包两次 | 1290 / 1290 | **464** | `75f41ebc10e0b0ce4b10` vs `c010472f461ae4e9ebfa` 不同 |
| coral-c / coral-d | 硬件 | 存量包两次 | 1290 / 1290 | **710** | `220f17ea72c427d6da4c` vs `93f2f5f79353764b7a26` 不同 |
| warm-i / warm-j | 软件 | 编译包两次 | 1290 / 1290 | **0** | `354ecc6f2c46b0135436` 两次同 |
| coral-e / coral-f | 软件 | 存量包两次 | 1290 / 1290 | **0** | `4e336c269709b599d10d` 两次同 |

存量包同样复现 ⇒ 不是编译包引入的。渲染器**上游**全同（同一份 `index.html`、同一批
`cues.json` 落盘的时序），差异只能来自光栅化。为什么硬件不确定**没有归因**：spec §11 已把
"软件=确定"标为实测相关而非机制解释，不许当成已解释现象往下铺。

处置：发射器默认走 `--no-browser-gpu`（`path_b_build.py:2609`，`--gpu` 降为显式开关），
由 `t_render_argv_defaults_to_software_raster`（`:2262`）钉住那行字面量。
**这是行为变更，需 owner 点头才算裁决**（见 J7）。

### J5 一次差点交出去的假绿：framehash 解析器

上一轮"两次渲染 0 帧不同"用的是 `frame-hash (\d+) (\S+)` —— 这份 ffmpeg 输出的是 CSV 行
`0, dts, pts, duration, size, hash`，那个模式**一行都不匹配**，返回空表，空表比对当然
"0 帧不同"。所以 J4 表里硬件那两行不是"重测变了"，而是**上一轮根本没测**（旧数字
398/1291、641/1291 作废）。本轮取末列、校验 32 位十六进制、空表直接抛。教训与 §G 同源：
**判据取不到数时必须炸，不许返回空表**。

### J6 最终几何上的机判复测与留白

- 判据 2 引擎：`check . --strict --json --caption-zone=…`（不带 `--at-transitions`）`ok=true`，
  lint / runtime / layout / contrast 四段 0/0/0（`motion.enabled=false` ⇒ 那段零仍是空转，口径同 §H）。
- 结构闸 `layout_selfcheck.py`：**7 个文件 0 违规**。色板闸 `audit_pack_contrast.py`：**1 pack 0 警告**。
  `path_b_selftest.py`：**122/122**。
- 判据 3（编译前 WCAG）：`contrast_floor_violations` 在编译期把关，本轮未新增未配对色。
- 判据 4b（分镜音频）：五镜 mp3 **时长**两遍逐毫秒一致 —— `8.976 / 8.400 / 8.880 / 8.712 / 8.064`，
  合计 43.03s。注意 mp3 的**字节**每次不同（md5 全不一样，edge-tts 返回的容器元数据会变），
  所以 4b 的口径只能是时长，写成"字节一致"会永远红；时间轴由时长决定，这个口径是对的。
- 判据 6（时长）：编译包 **94.89s / 94.05s**，红线 102.9s（基线 68.57s × 1.5）⇒ **通过**。
  同机软件光栅下基线是 100.91s / 98.77s —— 离红线只剩 2%。分段：
  `dub 12.1-12.9 | gate 14.1-15.1 | render 59.9-66.0 | mux 4.9-5.5 | finalize 1.2-1.4`。
  **产能风险**：软件光栅更慢（编译包 render 61.4/59.9 vs 硬件 57.2/48.9；存量包
  66.0/63.2 vs 硬件 40.9/36.2），但硬件那两条自身就有 17% 抖动，且确定性是门禁、时长只是预算。
- 法则 17 底部空转复测（`limit = 100 − 20.0 − 0.5 = 79.50`）：
  `hook 4.71 / stat 6.50 / rail 3.50 / quote 6.82 / catalog 6.20 / story 7.58 / closer 4.98`，
  全部 ≤ 8.0，两处 top 抬格没把任何一套推出线外。

同稿并排的口径：`p13e_fixture.json` 五镜占位稿（hook / catalog / story / rail / closer，
每镜都带 ≤8 字眉标、≤18 字标题、42 字正文，刻意压各版式的字符上限），两支 `final.mp4`
由同一份稿、同一批时序发射，只差 pack。五个中点帧（t = 4.49 / 13.18 / 21.82 / 30.61 / 39.00）
并排成 `pair/s-1…s-5.png`，左 = 编译包、右 = 存量包。

### J7 留给后面的账

- **发射器侧还没有眉标截断**：`KICKER_MAX_CHARS = 8` 只是编译器算栏宽的单边声明，
  `path_b_build.py:238-270` 那批字符上限里没有眉标位。真稿给一个 10 字眉标就会折行、
  把片撑高 ⇒ 法则 18 的纵向口径失效。P4 补 `kicker` 截断，或让它走 `overlap_violations` 报错。
- `GROUND_TONE_BY_HEX` → spec 推导（P4）、`SHARED_TOKENS` 后门（P4，裁决 12）、
  字幕 reserve 3 行/2 行口径（P2）、31 套齐平（P5）—— 与 §I6 同批。
- 软件光栅默认 = 行为变更，待 owner 确认（J4）。
- **判据 1（人工审美）已过（2026-10-10）**：五张并排帧 + 两支 `final.mp4` 交出，owner 以"你继续铺吧"认可当前水位并放行 P2。
  同时量出的三条差距**不阻塞、记账到 P5**：D2 字号档（编译包标题与正文整体偏小一档）、
  D3 中段密度（story / closer 中部约 30% 空转）、D4 序数存在感（Playfair 16cqw 细衬线 vs
  存量包同位近满宽的重量级数字）。三条都是 `hf_compile._steps` 的配方数值，不是闸或缺陷。
  软件光栅默认同批升为裁决 16。

