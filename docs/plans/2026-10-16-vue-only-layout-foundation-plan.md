# Vue-only 版式地基 · 实施计划

**Goal:** 让一个版式可以**只有 Vue 组件、没有静态 HTML 文件**，从而让 `field`/`rank`/`versus`/`cause`
四个新结构进得了产线；同时把 Phase 3 删 217 份静态文件的前置一次性拆掉。

**Spec:** `docs/plans/2026-10-15-news-vue-phase2-redesign-spec.md` §7.10
**为什么现在做：** 四个结构的探针都答完了，**共同阻塞只剩这一条** ——
`load_style_pack` 的 `layouts` 只从 `compositions/*.html` 扫（`path_b_build.py:1930`），
槽位（`pack_slots.template_of`）与 `composition_id` 同样以静态文件为唯一真源。

**Tech Stack:** Python 3.12（stdlib `tomllib`，无新依赖）、Vue 3 SFC + Vite 6（已钉）、
仓库 harness（`path_b_selftest.py` 的 `t_*`、`tests/web/vue-build.test.ts`）。

## Global Constraints

- 新增 Python 断言函数名必须以 `t_` 开头（`path_b_selftest.py` 只收 `t_*`，写成 `test_*` 静默不执行）。
- **静态支一字节不改**：现有 7 角色的 `layouts` 条目、`slot_css` 输出、`composition_id` 全部逐字不变。
  31 包普查（`pack_render_census.py` 31/31 零 WARN）与 `t_slots_reconstruct_every_pack_byte_exact` 是回归基线。
- 契约判据**只有一份实现**：预检/发射器/自检都走同一个 `resolve_variable`，
  不许在 loader 里另立一套校验（另立 = 两边各说各话，`check_scene_contract` 的假绿就是这么来的）。
- 新角色的槽位**必须来自 `theme.toml`**（它没有静态文件可抽），且解析不出来就**停机**，
  不许悄悄退回某个默认色 —— 那是拿假常数当判据（`estimate_duration` 的前车）。
- `git push` 由用户做；每次提交前 `git diff --cached --name-only` 逐条核对。
- 基线：`path_b_selftest.py` 223/223、`npm test` exit 0、`layout_selfcheck` 227 文件 0 违规、
  `audit_pack_contrast` 24 条（刻意保留基线，不得出现新文件名）。

## 设计：契约放哪

| 候选 | 判定 |
|---|---|
| 各包 `layouts.toml` 加一段 | ✗ 一个组件服务 31 包，契约要抄 31 遍；且该文件明写「编译产物，勿手改」 |
| 发射器里硬编码一张表 | ✗ 契约与组件分离，改组件忘了改表 = 静默错槽位 |
| **组件目录带一份 `contract.toml`** | ✅ 契约与实现同处一地；per-pack 只有**槽位值**与 **composition_id 前缀**两样，都由包侧数据推出 |

```
src/web/entries/<bundle>/contract.toml
  role    = "field"            # 版式角色名
  variant = "a"                # "a" 主流簇 / "b" 变体簇
  [id] slug_from = "layouts.toml"   # composition_id = f"{pack_slug(pack)}-{role}"
  variables = [ { id=…, type=…, label=…, default=… }, … ]   # 与 HTML 的 data-composition-variables 同 schema
  [slots]   c0 = "paper"  c1 = "ink"  c2 = "ground" …        # 槽位序号 → theme token 名
```

---

### Task 1: `vue_contracts.py` —— 契约发现 + pack slug（纯新增，零风险）

**Files:** Create `skills/douyin-pro/scripts/vue_contracts.py`；Test `path_b_selftest.py`

**Interfaces:**
- `vue_contracts.load(contract_path) -> dict`
- `vue_contracts.discover(entries_dir) -> dict[(role, variant), dict]`
- `vue_contracts.pack_slug(pack) -> str` —— 从该包 `layouts.toml` 任一 `composition_id` 剥掉角色名反推
- `vue_contracts.composition_id_for(pack, role) -> str` = `f"{pack_slug(pack)}-{role}"`
- `vue_contracts.slot_values(pack, contract) -> list[str]` —— 按 `[slots]` 映射从 `theme.toml` 取值，
  **缺 token 直接抛**，不静默补默认

- [ ] Step 1: 写失败测试（4 条）
  - `t_pack_slug_is_derivable_for_every_pack`：31 包都能推出非空 slug，且用该 slug 拼出的新 id
    不与包内任何已有 `composition_id` 撞车。
  - `t_slot_values_come_from_theme_and_fail_loudly`：给一个不存在的 token 名，必须抛并点名 token。
    反向负例：把 token 名改对，必须通过。
  - `t_contract_variables_match_schema`：契约里每条 variable 必须含 `id/type/label`，
    且 `id` 在该契约内唯一。
  - `t_discover_is_keyed_by_role_and_variant`：同一 role 出现两个 `variant="a"` 必须抛
    （路由靠 (role, variant) 推导，撞了就会静默选错组件）。
- [ ] Step 2: 跑测试确认失败（`No module named 'vue_contracts'`）
- [ ] Step 3: 实现
- [ ] Step 4: 全量回归 —— 223/223 不变（本 Task 不接线，静态支不可能受影响；若受影响即说明改错了地方）
- [ ] Step 5: 提交

### Task 2: `load_style_pack` 合并 Vue-only 版式（**第一次动发射器**）

- `layouts` 末尾追加"有契约、无静态文件"的角色，条目带 `vue_only: True`；
  已有 7 角色的 dict **逐字节不变**（用 `t_static_layout_dicts_unchanged_by_vue_only` 锁：
  接线前后对同一包 dump 出的 7 个条目做深比对）。
- `vue_bundle_for(pack, role)`：命中 Vue-only 契约时返回 bundle 名，`variant` 由契约定（不再问 `pack_variants`，
  因为新角色没有静态文件可聚类）。
- 反向保护：某包既有 `field.html` 又有 `field` 契约 ⇒ **抛**，不许静默二选一。

### Task 2.5: theme 词表归一（**Task 2 当场挖出的前置，未做**）

Task 2 的合并逻辑原本在装载时就解析槽位，跑全 31 包立刻炸在
`news-policy/field: 槽位 c0 指向 theme token 'cream'，该包 theme.toml 里没有它`。
量下去才发现这不是个别缺项：

> **31 个包的 `theme.toml` 一共 68 个 token，而在全部 31 包中都存在的 token 有 0 个**
> —— 连 `ink`、`gray` 都不是全包共有。（`news-coral` 有 `cream/white/light-gray`，
> `news-policy` 一个都没有；反过来 `news-policy` 有 `paper/cobalt/rule`。）

⇒ **「新角色槽位来自 theme」这条前提当前不成立**：共享组件没法用 token 名引用色，因为没有公共名字。

- **不做的方案**：给每个槽位配候选别名列表（`c0 = ["cream","paper","white",…]`，先命中先用）。
  它会在某些包静默挑到语义不同的色（`paper` 在 A 包是冷白、在 B 包可能是暗调），
  那是把"取不到就抛"换成"取错也不说" —— 与本片自己立的规矩冲突。
- **要做的方案**：给每包 theme 加一层**规范角色别名**（`[canonical]` 段：
  `ground / surface / paper / ink / accent / accent_deep / mute / mute_light`），
  由该包自己的 token 显式映射而来，`frame.md` 色板表是它的出处；
  契约只准引用 canonical 名。映射表本身由机检覆盖：每包 8 个角色必须都能解析、
  且解析出的值必须真的是该包色板里的某一项（不许凭空造色）。
- **这一层同时是 Phase 3 的前置**：静态文件删掉之后，槽位只能从归一后的主题取。
  现在不做，Phase 3 也会撞上同一堵墙。
- 因此 Task 2 的合并阶段**不再解析槽位**（改为存 `contract` 引用，发射时解析），
  这样"某包缺 token"不会把整包变成不可加载；等 Task 2.5 落地后，
  `slot_css` 的 vue-only 分支（Task 3）才有稳定的取值来源。

#### Task 2.5 的自动化路线已被实测否证（2026-10-16）

原计划「从 `frame.md` 色板表的描述列自动推 canonical 角色，只把歧义项交人拍」。
跑完 31 包，用「token 名 + 描述关键词 + 亮度」三段规则，六个 canonical 角色的解出率是：

| 角色 | 唯一命中 | 歧义 | 缺失 |
|---|---|---|---|
| `paper` | 7/31 | 0 | 24 |
| `ground` | 3/31 | **24** | 4 |
| `ink` | 3/31 | 4 | 24 |
| `cream` | 6/31 | 1 | 24 |
| `mute` | 7/31 | 4 | 20 |
| `accent` | 4/31 | **19** | 8 |

失败原因有两条，都不是"包缺色"：

1. **描述列是散文不是受控词表** —— 「底」同时出现在「主底 / 卡片底 / 纸面底 / 地面」里，
   所以 `ground` 在 24 个包上必然歧义（这条是规则太松，可修）。
2. **`paper` 缺 24 不是解析失败，是事实** —— 复查后确认：**31 个包的色板小节全部解析正常**
   （解析到 0 行的包 = 0 个），而那 24 个包**本来就没有浅色主底**，它们是**单地面（暗底）包**；
   有浅色主底的只有 7 个。

⇒ 第二点把 canonical 层的真问题挑明了：`story` 能在 31 包都翻 light/dark 两面，
靠的是 `#ece8df` / `#0a0a0d` 这对**共享中性色**（`SHARED_TOKENS`），它们根本不在各包色板里。
**24/31 包没有第二面可绑** —— 这才是"随包变色"落空的根，不是词表没归一。

**改做法（待拍）**：canonical 层**只声明该包真正拥有的角色**，不假设两面都存在：

- 必备（各包都有）：`ground`（该包自己的暗地面）、`ink_on_light`、`accent_shared` 走共享层不动；
- 可选（有就绑、没有就**回落共享中性色**并记一条"该包单面"）：`paper`、`mute_light`；
- 判据：`ground` 的解析规则收紧成「描述含**主底**且亮度 < 0.20 且是 `#root` 实际用的那个色」，
  不许用"含底字"这种松规则（就是它造出 24 个歧义）。
- 收益上限要说清：这样新角色**只通过地面色调随包变**，与 frame.md §5
  「同一系统换地面，不做三套 token」完全一致 —— 也意味着变化幅度就是"地面色调"这一档，
  别期待更高。真要题材级差异，靠的是 §7 的**结构**，不是色。

**另一条更省的路**：完全不做 canonical 层，新角色的槽位**继续走 `SHARED_TOKENS`**
（与 `story`/`quote` 现状一致），包间差异 100% 由结构承担。
代价是新角色跨包同色 —— 但 §1.1 已量过：绑面色只有 1 包可辨、绑 accent 6/8 包过不了对比度，
**"能变的色"本来就没多少可变的**。**我倾向这条**：省掉 31 个 frame.md 的改动与一层长期维护的映射，
把力气全放在结构上。

### Task 3: 槽位来源 = 契约自带字面值 + 显式 per-pack 覆盖

**Task 2.5 取消**（不建 canonical 层）。除 §1.1/上面两条实测外，又量到一条独立理由：

> **0/31 个包有"单一地面"** —— 每个包在它的 7 个版式上用**多个**地面
> （`news-coral` 同时用 `#1a1a1a`、`#0a0a0d`、`#f5f0e8`、`#e8e0d4`）。
> 所以「该包的地面」这个可绑定对象**不存在**：包的身份体现为"每个版式各用哪个地面"，
> 是 per-layout 属性，不是 per-pack 属性。任何"自动随包变色"的方案都是虚构。

新做法：

```toml
# src/web/entries/field-a/contract.toml
[slots]                       # 契约自带默认值（字面 hex，不查 theme）
c0 = "#0a0a0d"                # 暗地面
c1 = "#f5f0e8"                # 暗面上的字
[overrides]                   # ← 顶层段。写成 [slots.overrides] 会被 tomllib 嵌进 slots，
                              #   于是 "overrides" 当成一条槽位名（不是 cNN）当场抛。
news-world = { c0 = "#0e1b36" }   # 想随包变的，显式写一条 —— 是设计决定，不是推导结果
```

- `pack_slots.slot_css(pack, role)`：先查该 `(role, variant)` 有没有 Vue-only 契约；
  有 → 用契约的 `[slots]` + 该包 override；没有 → 原路（读静态文件 hex），**一字节不变**。
- 判据 `t_slot_css_unchanged_for_static_roles`：31 包 × 7 角色，改前改后 `slot_css` 字符串全等。
- 判据 `t_vue_only_slot_css_honours_override`：给 `news-world` 写 override，
  该包必须变、其余 30 包必须不变；反向负例：override 里写一个不存在的包名 ⇒ 抛
  （拼错包名会静默不生效，那是最难发现的一类"改了没效"）。


### Task 4: 第一个 Vue-only 角色 `field-a`（none 单态）

按 `evidence/2026-10-16-field-proto.md` 的原型落组件，含两处已定改动：
眉标不写"现场无影像"这类道歉式文案；36–62cqh 的空带压掉。
契约变量：`kicker / title / onscreen / imagePath / imageCredit / imageGrade / slotSeconds`。

**落地记录（2026-10-16）**：合并方案按用户裁决走完，六类消费者假设逐条改判 + 13 处变异证明，
`path_b_selftest.py` **239/239**；第一条 `field` 镜真渲染 490/490 帧、0 WARN、`check --strict` 0 finding。
两处实测缺陷（地点行 2.43:1、12% 水印漏 `data-layout-ignore`）已修，证据与归因负例见
`evidence/2026-10-16-vue-only-merge.md`。
变量表与本计划不同：`imagePath/imageCredit/imageGrade` **本 Task 不进契约**（影像供给实测 0/9 可用，
spec §7.5 未拍），改落 `ghost`/`place` 两个作者供料位。
**遗留**：下沿 ~22% 空带 —— 必须先做 Task 5 的闸再按闸修，否则改一版没有判据。

### Task 5: 新角色的自检面（**2026-10-16 实测后改判**）

原写法：「`layout_selfcheck` 只扫 `compositions/*.html` ⇒ 对 Vue-only 版式跑同一套 17 条不变量
（复用同一实现，不重写）」。**这条按原样做不到**，三处实测（`evidence/2026-10-16-task5-precheck-findings.md`）：

1. 17 条里**没有"填幅"**——法则 17 只在 `hf_compile` 按配方几何实现（`MAX_BOTTOM_DEAD_CQH=8.0`），
   静态 227 份 HTML 同样没这条闸。所以"跑 17 条再按闸修空带"是两件事。
   `field` 实测内容下沿 **77.3cqh**（字幕区上沿 80cqh）⇒ 空 2.7cqh，**不违规**，那段黑是留给字幕的。
2. 规则 7（字幕禁入区）读 CSS 的 `bottom:`/`inset:`，成立前提是**偏移相对满幅 `#root`**；
   组件的 `.fd-place{bottom:6cqh}` 相对 `.fd-stage{inset:0 0 36cqh 0}`，实际在 42cqh ⇒
   把文本口径直接搬到组件上会**假红**。
3. 活体负例证明**引擎的 `--caption-zone` 不是侵入探测器**：把地点行渲到 **85.6cqh**（区内），
   `check --strict` 五段仍 0 finding。

⇒ 改判后的 Task 5：字幕区/填幅两条对 Vue 支按**像素几何口径**做，挂在渲染普查那一层
（每角色一镜、量最底内容行 vs 80cqh 上下界），不进 `path_b_selftest.py`；
文本口径可复用的那几条（法则 8 面淡入、动量预算、px 排版、@font-face）另做一份
**SFC 版**检查，并显式登记"17 条里哪几条在 Vue 支由谁守"，缺项不许静默跳过。

**落地记录（2026-10-16，前半做完）**：登记表 = `layout_selfcheck.VUE_GUARDS`
（`--vue-guards` 现生成，`t_vue_branch_guard_registry_is_complete` 机检，洞数钉死 2）；
SFC 版检查 = `check_component`，复用抽出来的 `check_momentum_budget` / `check_font_rules` /
`check_px_typography` + `declarations_for_classes`。今天 `reused 11 · moved 4 · 洞 2`，
`path_b_selftest.py` **242/242**，静态支 227 + 7 文件 0 违规。
接线当场抓到 `field-a` 缺中文 @font-face（已补）。
**未做**：像素几何闸（含法则 17 填幅）与 vue-build 的"注册必须存在"正向断言。
全文 `evidence/2026-10-16-vue-guard-registry.md`。

**Task 5 后半做完（2026-10-16，同日）**：两个洞都清零。
① vue-build 补正向断言 `__timelines[<非字面量>] =` 至少一条（删掉注册语句时只有新那条红，实测）；
② 像素口径闸门 = `routes/news/scripts/content_floor.py`，接成普查判据 6。
字幕区半边（>80cqh）31 包全过 ⇒ 开成硬判据；填幅半边（<71.5cqh）**0/31 过** ⇒ 只报不判，
落进 `_summary.md` 当账。登记表 `reused 11 · moved 6 · 洞 0`，`path_b_selftest` 245/245。
数据与口径全文 `evidence/2026-10-16-content-floor-pixel-gate.md`。
**新开的账（未拍）**：无图态版式下半部空 21.5–25.3cqh（227 份模板共有，从没量过）。

### Task 6: 真渲染闭环

`--target-seconds 30` 渲一条含 `field` 镜的片；要求 `check --strict` 0/0、零 WARN、
逐镜尾段动量达标，并出 before/after 联络表交用户目视（spec §2 最后一条判据）。

## 顺带挖出的一笔历史债（本计划刻意不修，但必须留名）

Task 1 原本打算"从已有 layout 的 `composition_id` 反推包前缀"，跑完全 31 包量出 **92 个少数派**：

> **30 个包的 `hook` / `quote` / `story` 三个角色，`composition_id` 全都是 `nc-night-*`**
> （`news-alert/hook`、`news-coral/hook`、`news-stat/hook` 的 id 是**同一个字符串**）。
> 来源是 v008 那次批量从 `news-coral-night` 复制骨架（MEMORY 记了"加 `night-` 前缀"，
> 但前缀加在了**所有派生包**上，等于没加）。

- **为什么今天没炸**：静态支每镜是独立 document，`window.__timelines` 不跨 document 共享，
  撞名互不可见。
- **为什么它危险**：Vue 支整个 host 只有一个 document、N 个 mount 共享一份 `__timelines`。
  Task 4 当时"必须给每条 Vue 镜唯一 composition 身份"，撞上的正是这类东西 —— 也就是说
  **这笔债已经被绕过一次，而不是不存在**。
- **本计划怎么躲开**：新角色的 id 用 `f"{role}-{pack}"`（包名本身唯一可读），
  **零血统耦合**，见 `vue_contracts.composition_id_for` 的 docstring。
  不拿 92 条"已知例外"去糊它。
- **该单独修的口子**（未拍）：把这 90 个 id 改回各自包的前缀。风险点是
  `layout_selfcheck` 规则 2 要求「子合成根 id == timeline 键」，且 31 包普查基线与
  `vue_pixel_ab` 都 keyed 在 id 上 —— 是一次需要重跑全闸的独立变更，不塞进本计划。

## 交接给后续

- Task 1–3 做完 ⇒ `rank`/`versus`/`cause` 都可直接以"契约 + 组件"落地，不必再动发射器。
- Task 5 是硬前置：**没有它，新角色等于绕过全部版式闸**。
- 本计划不动 `hf_compile.py` / `path_c` / `spec.toml`（迁移总纲 §1-4 仍有效）。
