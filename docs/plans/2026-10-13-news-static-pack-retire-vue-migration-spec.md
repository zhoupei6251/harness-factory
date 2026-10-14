# 静态 composition 退役 · Vue 迁移 spec（news 域 31 pack）

日期：2026-10-13　状态：**待用户复核**（未开工）
决策人：用户（唯一维护者）。本 spec 的四条口径来自本次对齐，逐条记于 §1。

---

## §0 一句话

`hyperframes_path_b` 的 31 套手抄静态版式（217 份 `compositions/*.html` / 55,071 行）退役，改为
**14 个版式组件 × 31 份主题 token**；迁移期两条路并存，全量验完才一次性删；
`path_c` 的编译器（`spec.toml` → `hf_compile` → 静态 html）**不动**。

---

## §1 四条已定口径（用户逐条选定，非本 Agent 推断）

| # | 口径 | 选定 |
|---|---|---|
| 1 | 迁移单元 | **分层**：版式组件 + 主题 token（不是 1:1 逐 pack 移植） |
| 2 | 退役时序 | **并存到全迁完，最后一次删**；历史 ProduceID 的可复现承诺 = **结构一致**，不承诺逐字节（2026-10-13 用户就风险 6 选②，见 §7） |
| 3 | 验收判据 | **结构闸门全量 + 像素对拍抽样（每 pack 1 镜，共 31 次）** |
| 4 | 退役范围 | **只退役手抄静态**（`path_b`）；`path_c` 编译产物保留，它不是历史包而是真源编译结果 |

---

## §2 盘上事实（全部实测，非估算）

| 量 | 值 | 取法 |
|---|---|---|
| pack 数 | 31 | `ls templates/hyperframes_path_b/`；`path_b_build.ALL_TEMPLATES`（:82）+ `decide_pack.PACK_BUCKETS` 全覆盖，有 `t_decide_pack_covers_every_real_template` 守 |
| 版式角色 | 7：`hook stat rail quote catalog story closer` | `hf_style_spec.CANONICAL_LAYOUTS`（:48），与盘上文件名一致 |
| layout 文件 | 217 = 7 × 31 | `find … -path "*compositions/*.html"` 去掉 placeholder |
| 加占位壳 | 227（10 份 `placeholder.html`） | 同上；占位壳不是版式（`load_style_pack` docstring 引 D7） |
| 总行数 | 55,071 | `cat */compositions/*.html \| wc -l` |
| **跨 pack 重复度** | `hook.html` 有 **30/31 份字节相同**，只有 `news-policy` 不同 | 逐 pack md5 分组 |
| **结构变体数** | 判据 0a **逐行实测**（不再是 md5 抽样）：7 个角色**各自 2 簇**，簇规模一律 `[30, 1]`，孤簇一律 `news-policy` | 归一化口径 = 去硬编码色值 / `rgba()` / `data-composition-id` 字面量 / `__timelines` 键名 / 逐行首尾空白后聚 md5；产出 `routes/news/evidence/2026-10-13-pack-variant-clusters.md`（由 `pack_variants.report()` 生成，与现跑输出逐字符相等），闸 `t_variant_clusters_hook_has_the_measured_two_shapes` + `t_normalization_actually_collapses_stat` |
| 主题的真实形态 | 约 3 行硬编码 hex（`#f5f0e8` vs `#fff7ed`、`#e85d5d` vs `#f2c94c`） | `diff news-coral/stat.html news-alert/stat.html` |
| token 源 | 31/31 的 `frame.md` 色板表**可机器解析**，合计 **398 条**（每包 6–16 条，无空包、无同名不同值）；该总数已被串色闸的快照断言钉住（`t_section_scoping_loses_no_palette_rows`，`== 398`，增删 pack 或作用域错收行都会让它变红并要求人工重校准） | 正则 `^\| \`[a-z0-9-]+\` \| \`#[0-9A-Fa-f]{3,8}\`` 命中 31/31；逐包计数实测 |
| token 词汇表 | **不统一**：全并集 68 个名（`coral` / `alert` / `cobalt` / `navy` / `accent`…），最高频 `accent` 只 21 次 | 31 份 frame.md 汇总 |
| `host.html` | 每 pack 59 行、31 份互不相同、只含 **1 个色值**、**31/31** 带 CDN `<script>` 引 `gsap@3.14.2` | 实测；版本冲突见 §7 风险 6 |
| 现有 Vue 覆盖 | **1 / 217**（`nc-night-hook` → `news-coral-hook`） | `VUE_COMPOSITIONS`（:471） |
| 单镜移植体量 | 静态 `hook.html` 256 行 → `NewsCoralHook.vue` 250 行 | `wc -l` |

**结论**：「227 份要移植」是假工作量。真实交付物 = 14 个组件 + 31 份 theme + 一张版式登记表。
其中 **14 是「一簇一组件」这条设计政策下的取值**（= 7 角色 × 各自 2 簇），不是数学下界：
`stat` / `quote` 的第二簇只差个位数行动画参数，若作参数化处理可以只要 12 个组件（见 §7 风险 5）。

---

## §3 硬约束：发射器的版式元数据现在长在静态文件里

这是整件事最容易踩空的地方，必须先解决再谈删文件。

`load_style_pack()`（`path_b_build.py:1810-1880`）逐份读 `compositions/*.html`，从中**正则抠出**：

| 字段 | 现在的来源 | 抠不出就 |
|---|---|---|
| `composition_id` | `ROOT_COMPOSITION_ID_RE`（`<div id="root" data-composition-id="…">`） | `EmitterError` 装包即停 |
| `variables` 契约 | `VARIABLE_ATTR_RE` → `data-composition-variables` 的 JSON | 同上（"没有 data-composition-variables 契约"） |
| `ground_hex` / `ground_tone` | `ROOT_GROUND_RE`：`#root{ … background:#rrggbb }`（:338） | 报"没有 background 声明" |
| 地面明暗归类 | `GROUND_TONE_BY_HEX`（:343，未登记色停机） | 报"地面色不在设计系统色板里" |
| `primitives` | `_layout_primitives`（:329，读 `data-hf-primitives`；手抄包恒空） | — |

⇒ **删掉 `compositions/*.html`，即使该 pack 全部走 Vue，发射器也拿不到版式表。**
所以退役的前提是先有一张不依赖 HTML 的登记表（§4 L0）。

---

## §4 目标形态（四层）

```
L0 版式登记表  packs/<pack>/layouts.toml     217 条：(role) → {composition_id, variables, ground_hex, variant}
L1 版式组件    src/web/layouts/<role>[-b].vue  14 个：7 角色 × 2 变体，不认 pack 名
L2 主题 token  packs/<pack>/theme.toml        31 份：面/文字对/强调色，沿用 hf_style_spec 的 color 层词汇
L3 路由登记    path_b_build 的 Vue 路由表      (pack, role) → (组件 bundle, theme)
```

**L2 复用现成 schema，不新造 token 语言。** `hf_style_spec._validate_color`（:225-）已经定义
`color.surfaces{面名=hex}` / `color.text[{role,hex,on,size}]` / `color.accents[{role,hex}]` /
`saturation-budget` / `value-ladder`，且有校验。§2 已证 31 个 pack 的 token **名不统一**，
所以组件不能写 `var(--coral)`；组件只认**语义位**（地面/正文/强调），由 `theme.toml` 提供该 pack 的映射。

**L1 的 GSAP 颜色口径（本方案唯一的技术选择，需在实现前固定）**：
> **注意：「GSAP color 补间不支持 `var(--x)`」是本 Agent 的先验判断，仓内无实测证据。**
> P1 步骤 0 之后加一道**探针（判据 0）**：一个最小 .vue，`fromTo(el, {color:'var(--x)'}, {color:'var(--y)'})`
> 与 `{color:'#hex'}` 各 seek 一次截图对比。探针若证伪（变量能补间），B 方案可省掉「GSAP 取字面量」这条，
> 只留 CSS 变量；若证实，按 B 执行。**这条不得当成既定事实写进组件**。
> **2026-10-13 实测（判据 0b 闭，gsap 3.15.0，真 Chrome）：t0=`rgb(255,0,0)` / t0.5=`rgba(0, 0, 191, 0.75)` /
> t1=`rgb(0,0,255)`——中间帧红通道丢失、端点仅靠浏览器解析原样回写的 `var()` ⇒ 先验判断**证实**，
> B 方案内部「GSAP 从 theme JSON 取 hex 字面量」这条**必须保留**（证据：
> `routes/news/evidence/2026-10-13-gsap-var-interpolation.md`）。**

取 **B 方案**（探针结果不影响 A/B 的选择，只影响 B 内部要不要那层解析）：

| | 做法 | 产物数 | 确定性 |
|---|---|---|---|
| A 编译期烤死 | 31×14 份 CSS 全 bake 字面量（同 `hf_compile` 口径） | ~434 | 最强，但把 217 的重复搬进构建 |
| **B 采用** | theme 随 bundle stage；静态样式走 `var()`，**GSAP 补间从 theme JSON 取 hex 字面量** | **14 + 31** | theme 文件是固定输入，可入哈希；**「逐字节可复现」是有范围的**（已钉 / 未钉的输入见下方注与 §7 风险 7） |

> **P0 已执行（2026-10-13）**：`gsap` 与 `vue` 从 caret 钉成精确版本（`package.json` devDependencies
> `gsap = 3.15.0`、`vue = 3.5.43`），`tests/web/vue-build.test.ts` 有两条断言：
> ①「声明 == lock 解析」，②「**bundle 内** GSAP 版本 == 声明版本」（按产物里的 `version="x.y.z"` 标记取，防陈旧 dist）。
>
> **仍未钉的输入（所以「逐字节」不是无条件承诺）**：`vite = ^6.4.4`、`@vitejs/plugin-vue = ^5.2.4`
> 还是 caret 范围。打包器的版本同样决定 bundle 字节（plugin-vue 内含 `@vue/compiler-sfc`，
> 模板编译产物的形态、CSS 作用域处理、helper 命名都会随它漂）。⇒ 本行「逐字节可复现」的准确口径是
> **「同一 vite / plugin-vue 版本下，GSAP 与 theme 已固定 ⇒ 字节可复现」**；跨 vite 小版本重构建，
> 新片字节仍可能变。Phase 1 把哈希入档之前必须二选一：钉死这两个（或 lockfile-only 安装 +
> 记录哈希基线时的工具链版本），或把哈希口径显式写成「同工具链版本内可比」。
> 本轮（Phase 0 修复波次）**没有**动这两个范围——它是决策而不是补断言，交给用户拍。
> （§7 风险 7 同口径。）

---

## §5 阶段（每阶段末尾有可机检的门，不过不进阶）

### P0 契约落盘（不碰渲染，可独立提交）

1. `scripts/extract_pack_theme.py`：`frame.md` 色板表 → `theme.toml` × 31。
2. `scripts/extract_pack_layouts.py`：`compositions/*.html` → `layouts.toml`（217 条），
   并按 §2 的归一化口径给每 (pack, role) 标 `variant`（1/2）。
3. 把 `gsap` / `vue` 从 caret 范围钉成精确版本（写这条时 `package.json:27` 是 `^3.15.0`），并在
   `tests/web/vue-build.test.ts` 加「bundle 内 GSAP 版本 == 声明版本」断言——否则 §4 那格
   「逐字节可复现」不成立（§7 风险 7）。
   **P0 交付状态（2026-10-13 实测）**：devDependencies 现为精确 `gsap = "3.15.0"` / `vue = "3.5.43"`；
   断言两条并存 —— ①声明 == lock 解析，②读 `dist/vue/news-coral-hook.js` 里的 GSAP
   `version="x.y.z"` 标记（实测全文恰好 1 处）并要求其值 == 声明版本，陈旧 dist 会让②变红。
4. **门 G0（三条全量闸）**：
   - `theme.toml` 与它所属 pack 的 `frame.md` 色板表**逐条相等**（串色闸，31/31 全跑）。
   - `layouts.toml` 与 `load_style_pack()` 当次读出的 `composition_id / variables / ground_hex / ground_tone` **逐字段相等**（等价闸，217/217 全跑）。
   - 变量 id 都有取值来源 —— 词表是**三条并集**：`DERIVERS`（:2160）、`INDEXED_VAR_RE`（:2188，`itemN*/stepN*`）、
     `imagePath`/`imageCredit` 硬分支（`resolve_variable` :1905）。今天实测 1943 条变量 = 1147 条 DERIVERS 命中 + 372 条 INDEXED 语法 + 424 条取图硬分支，无来源 0 条。
     ⚠ 判据原文「⊆ `DERIVERS`」是错的（今天会红 796 条）；且**不许**用 `register_indexed_derivers` 先把 id 灌进 `DERIVERS` 再判——
     那函数是运行时改全局字典，会让断言取决于跑测顺序。

> 这三条是整件事的保险丝：**抽取必须证明与现状等价**，否则后面所有对拍都失去基线。

### P1 角色纵切（7 轮，每轮一个角色）

**P1 前置（只做一次，两道探针，出结果才谈组件数）**：

- **判据 0a 量化分歧**：对 7 个角色各做一次「去掉硬编码色值 + `data-composition-id` 字面量 + 行首尾空白后」的全 31 pack 互 diff，输出**每个角色的真实变体簇数**。§2 的「2 变体」是 md5 抽样结论，此步把它变成逐行证据；簇数 > 2 时按簇补组件，不改分层方案。产出写进 `verifications/`。
- **判据 0b GSAP 变量补间探针**：证伪或证实 §4 那条先验（见 §4 注）。

先做 `hook`（唯一已有真渲染证据的角色），其余 6 个角色同法：

1. 建该角色的 2 个变体组件（`<role>.vue` / `<role>-b.vue`），theme 走 L2 注入。
2. 31 个 pack 全部在 L3 登记该角色 → 组件 + theme。
3. **门 G1-结构（全量 217 镜）**：元素 ID 齐 + `window.__timelines` 注册 + 变量真值渲染 + **产物无 CDN 引用**。
4. **门 G1-像素（每 pack 1 镜 = 31 次，预算在此一次花清）**：
   31 次**按 pack 轮转角色**（`pack[i] → ROLES[i % 7]`），不是 31 次全抽 hook。
   理由：口径是「每 pack 1 镜」，但串色风险落在**每一个角色的地面/强调位**上；全抽 hook 会让
   `stat / rail / closer / catalog` 的主题映射一次像素都没被验过。轮转后每个角色约 4-5 镜，
   31 个 pack 与 7 个角色两个轴都覆盖到，总次数不变。
   - 基线侧与被测侧都只跑**画面轨**（`--skip-render`），配音不受 §7 阻塞影响。
   - 静态基线本身要渲 31 次 ⇒ 总渲染 62 次画面轨，写在这里是为了成本不意外。

### P2 切默认路由

`pack["compiled"]` 那类分叉已有先例（:1879）。Vue 路由从「`composition_id` 命中白名单」升级为
「(pack, role) 查 L3」，命中即 Vue，未命中 ⇒ **报错而不是回落静态**（并存期靠 §5-P1 把 217 条登记填满，不留未覆盖镜）。

**门 G2**：`path_b_selftest.py` 全绿 + 31 个 pack 各出一次画面轨且结构闸过。

> 为什么这步不可省（Phase 0 实测）：217 条镜只有 130 个不同 `composition_id`，30 个 pack 的 hook 同名 `nc-night-hook`；
> 更要紧的是 `choose_layout`（`path_b_build.py:2253-2280`）**逐镜独立选版式、无跨镜去重** —— 实测一条 20 镜的片子
> 会把 hook 选 7 次、story 6 次、closer 7 次。挂载点 id（`vue-target-{composition_id}`）与时间轴键都以
> composition_id 为唯一键 ⇒ 同版式第二镜起就撞车。**路由键必须是 `(pack, role)`，挂载身份必须是每次唯一的 `mount_id`。**

### P3 删静态（唯一不可逆动作，单独一次提交）

1. `load_style_pack()` 改读 `layouts.toml`（§3 的五个字段全部换源，`ROOT_GROUND_RE` 那条正则随之作废）。
2. 删 `path_b/*/compositions/`（217 + 10 份占位壳）。
3. `host.html` 里的 `<script src="https://cdn.jsdelivr.net/…gsap@3.14.2">` 删除——Vue bundle 自带 GSAP，
   **离线必挂**这条性质就此关闭。§7 风险 6 已由用户拍**方案②**（台账只承诺结构一致），此步**解锁执行**。
4. **门 G3**：`--doctor` + 31 pack 画面轨重跑全绿 + 历史 ProduceID 重渲过「结构一致」闸（定义见下）。

**「结构一致」的可机检定义（方案②落地，不接受叙述）**——同一 ProduceID 用新路重渲，断言：

1. 帧数一致：`total_frames` 与旧记录相同（同 fps、同时间轴总长）；
2. `window.__timelines` 注册齐（每镜一条，键名 = `composition_id`）；
3. 每镜元素 ID 齐 + 变量真值渲染（判据 4 的同一套断言）；
4. 产物无 CDN 引用。

**明确不承诺**：mp4 字节哈希一致。GSAP 从 `3.14.2`（CDN）换成 `3.15.0`（bundle），补间曲线在同一 seek 点可能落到不同像素——所以旧成片的哈希对不上是**预期行为**，不是回归。台账侧若正在拿哈希做判重，这处要同步改口径（见 §7 风险 6 处置）。

### P4 明确不做

- **不碰** `hf_compile.py` / `hf_primitives.py` / `spec.toml`（§1-4）。
- **不收敛** 31 份 `host.html` 为一份共用模板。收益真实但可后置，且不挡退役。
- **不复活** `.vue` 模板类型检查（TS 7 不导出 `./lib/tsc`，vue-tsc 启动即崩，见 `STRUCTURE.md:93` 与 `verification-lite` §6 第 1 条）。
- **不改** `ALL_TEMPLATES` / `decide_pack.PACK_BUCKETS` / 那条覆盖性测试（并存期 pack 数不变）。

---

## §6 判据汇总（可机检，不接受叙述）

| # | 判据 | 覆盖 | 命令形态 |
|---|---|---|---|
| 0a | 每角色真实变体簇数（去色/去 id/去空白后全 pack 互 diff） | 7 角色 × 31 pack | 一次性脚本，产出记 `verifications/` |
| 0b | GSAP 能否补间 `var(--x)`（§4 先验的证实/证伪） | 1 探针镜 | 最小 .vue + 同 seek 截图对比 |
| 1 | theme ↔ frame.md 色板逐条相等 | 31/31 | `path_b_selftest.py` 新增断言 |
| 2 | layouts.toml ↔ 现读版式表逐字段相等 | 217/217 | 同上 |
| 3 | 变量 id ∈ `DERIVERS` ∪ `INDEXED_VAR_RE` ∪ 图片硬分支 | 1943 条变量 | 同上 |
| 4 | 每镜结构闸（ID/timeline/真值/无 CDN） | 217/217 | `tests/web/*` + `layout_selfcheck` |
| 5 | 像素抽样 diff ≤1%（31 镜，按 pack 轮转角色，7 角色各约 4-5 镜） | 31 镜 / 两轴都覆盖 | `npx hyperframes` 画面轨 + 截图比对 |
| 6 | 每 pack 的画面轨真渲染成功 | 31/31 | 手动跑，结果记 `verifications/` |
| 7 | 删静态后历史 ProduceID **结构一致**（帧数 + timeline 注册 + 元素/真值 + 无 CDN），**不比字节** | 抽样 | P3 门 G3 |

---

## §7 风险与未闭项（摆明，不藏）

| # | 风险 | 性质 | 处置 |
|---|---|---|---|
| 1 | 配音仍被服务端拒（`edge-tts` 403，四条证据见 `verifications/2026-10-13-hyperframes-vue-poc-verification-lite.md` §10.b） | 外部，与本迁移无关 | 所有门只要求**画面轨**；整片 `final.mp4` 不在本次判据内 |
| 2 | 串色：token 名不统一导致某 pack 的地面/强调错位 | 分层方案新引入的**质量**风险（可全量机检） | 判据 1 全量 + 判据 5 抽样兜底 |
| 3 | `news-world` / `news-world-globe` 这类变体对说明 31 套的真实分歧度不止于颜色 | 度量口径边界 | 判据 0a 已把它变成逐行证据；**14 是「一簇一组件」政策下的取值，不是下界**（见风险 5） |
| 4 | `layout_selfcheck` / 三道闸 / `image_gate` 现在吃 HTML 文本 | 删静态后失去输入 | P3 第 1 步同批改源到 `layouts.toml`，改不动的那条闸随静态留到最后 |
| 5 | ~~14 个组件是下界，不是上界~~ **已由判据 0a 逐行实证**（Phase 0）：7 角色全部 2 簇 `[30, 1]`，孤簇一律 `news-policy` ⇒ 「一簇一组件」政策下的组件数 = **14**。⚠ 14 **不是数学下界**，它和处置栏「`stat`/`quote` 可参数化处理」是同一个政策的两个取值：按政策 14 个，把这两条近同构簇参数化合并则 **12** 个。实证把风险从「数量」挪到**分量**：孤簇与主流簇的归一化 diff 行数分两档——`stat` 4 行、`quote` 7 行（只差动画参数，近同构）vs `hook` 283 / `rail` 250 / `catalog` 259 / `story` 242 / `closer` 276 行（真不同构） | 数量风险的真实形态是**政策选择**（14 或 12），不是盘上事实；**工作量口径**按角色分档，14 不等于 14 份等力工 | Phase 1 排期按角色分档估，`stat`/`quote` 的第二变体可作参数化处理（那样总组件数 12）；其余 5 个按独立组件算 |
| 6 | **两条路的 GSAP 不是同一份字节**（实测）：31/31 份 `host.html:5` 引 `cdn.jsdelivr.net/npm/gsap@**3.14.2**/dist/gsap.min.js`；Vue bundle 打的是 npm `gsap@**3.15.0**`（P0 已把声明从 `^3.15.0` 钉成精确 `3.15.0`，lock 同值，产物侧另有断言） | ~~需用户拍~~ **已拍②**（2026-10-13）：台账只承诺**结构一致**，不承诺逐字节 ⇒ P3 步骤 3 解锁 | 定义见 §5-P3「结构一致」四条断言；判据 7 按此改写 |
| 6b | **删 CDN 不违反法则 10**（我先前把这条写成「法则 10 断掉」，是误用）：仓内 `法则 10` 只在 `hf_compile.py:21` / `:1135` 出现，指的是**编译期确定性**（同 pack 编译两次字节相同 + 无运行时随机），讲的是 path_c 编译产物，与「旧成片重渲字节一致」不是同一件事 | 表述纠正 | 台账的字节可复现**从来没有被机检过**（实测：`routes/news/*.md` 里 `逐字节\|字节一致\|deterministic` 零命中）——所以选②没有拆掉任何现存闸门，只是把这条未成文的历史假设正式关掉 |
| 7 | Vue 侧依赖面自己也在漂：产物字节取决于 lock 而非声明，凡是 caret 范围的依赖都可能带漂 | 可复现性隐患（这条威胁的是**新片**，与 6 同源但方向相反） | **P0 已封口一半**（2026-10-13 实测）：已钉精确版本的是 `gsap = 3.15.0`、`vue = 3.5.43`，`vue-build.test.ts` 断言 ①声明 == lock 解析 ②bundle 内 GSAP 版本标记 == 声明版本。**仍未封口**：`vite = ^6.4.4`、`@vitejs/plugin-vue = ^5.2.4` 留在 caret，而 plugin-vue 内含的 `@vue/compiler-sfc` 同样决定 bundle 字节 ⇒ 「逐字节可复现」按 §4 注的范围读，不是无条件结论。Phase 1 哈希入档前补一条封口任务（钉这两个，或把哈希口径限定为「同工具链版本内」） |
| 8 | **`composition_id` 不区分包**（Phase 0 实跑测出）：217 条镜只有 **130 个不同 id**；31 个 pack 的 `hook` 有 **30 个共用 `nc-night-hook`**（唯一例外 `news-policy` 的 `np-hook`），`stat` 才是一包一号 | 路由唯一性风险；**原先写的「路由级串色」是错的，见下行更正** | 现行 `VUE_COMPOSITIONS` 按 `composition_id` 命中，登记 hook 一条就一次覆盖 30 个包。~~⇒ 29 包整块错色~~ **该推论被实测推翻**（2026-10-13 复查）：那 30 个包的 `compositions/hook.html` **字节完全相同**（`diff` 输出 0 行；六色集合也一致：`#0a0a0d #e85d5d #f5f0e8 #ffffff #b0b0b0 #c0392b #dcdcdc`）——即 hook 版式今天根本不随包换色，30 镜走 Vue 与走静态视觉等价，**不存在错色**。真正的必要性见风险 9 |
| 9 | **同一次渲染里同一版式会重复出现**（Phase 0 复查实测，可复现）：`choose_layout`（`path_b_build.py:2253-2280`）逐镜独立选版式、**无跨镜去重**（只有 `is_first`/`is_last` 固定 hook/closer 的优先级）。用真样本 `t002-scenes.json` 的中段分镜复制成 20 镜跑一遍，得到的版式序列里 **hook 出现 7 次、story 6 次、closer 7 次**。而 `VUE_MOUNT_TPL` 的挂载点 id 是 `vue-target-{composition_id}`、组件注册的时间轴键是 `window.__timelines[composition_id]`，两处都以 composition_id 为唯一键。实发两条 hook mount 验证：两个 `id` **字符串相同** ⇒ loader 的 `getElementById` 只命中第一个，第二镜起挂空 target / 读到别人的 `data-variable-values` | **Phase 1 的开工前置**（不是优化项）。今天潜伏只因为唯一登记的 hook 在实际片子里恰好多为 1 镜；登记 story/stat/closer 后必发 | 挂载身份换成每次唯一的 `mount_id`（loader 与 `__timelines` 键同步改），与 `(pack, role)` 路由一起构成 L3 的唯一性面。静态路靠 `data-composition-src` 逐 clip 独立加载，所以这个键重复问题在静态路上不曾暴露 |

---

## §8 已闭的前置（本次不再问）

Tier 3 挂载能否被引擎真渲染，已证实：`nc-night-hook` 出 1570 帧、3.0 MB、零正确性告警，
失败形态是响的（`sub_timeline_script_failure`）而非静默黑屏。证据与两个已修断裂见
`verifications/2026-10-13-hyperframes-vue-poc-verification-lite.md` §10 / §10.a / §10.c。
31 个 pack 的迁移压在这个已验证形态上，不再是「未验证押注」。
