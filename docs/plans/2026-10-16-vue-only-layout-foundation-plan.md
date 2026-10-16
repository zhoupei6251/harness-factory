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

### Task 3: 槽位来源分叉

`pack_slots.slot_css(pack, role)` 现在一律读静态文件。改为：
`vue_only` 角色走 `vue_contracts.slot_values`，其余走原路。
判据：`t_slot_css_unchanged_for_static_roles`（31 包 × 7 角色逐个比对改前改后字符串全等）。

### Task 4: 第一个 Vue-only 角色 `field-a`（none 单态）

按 `evidence/2026-10-16-field-proto.md` 的原型落组件，含两处已定改动：
眉标不写"现场无影像"这类道歉式文案；36–62cqh 的空带压掉。
契约变量：`kicker / title / onscreen / imagePath / imageCredit / imageGrade / slotSeconds`。

### Task 5: 新角色的自检面

`layout_selfcheck` 只扫 `compositions/*.html` ⇒ Vue-only 角色**不在 17 条结构不变量覆盖内**。
必须补一条 `t_vue_only_layouts_pass_layout_selfcheck`：对 Vue-only 版式跑同一套不变量
（复用同一实现，不重写），否则新角色是个"没有闸的洞"。

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
