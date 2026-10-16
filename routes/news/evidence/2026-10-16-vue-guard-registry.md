# Vue 支的 17 条守卫登记表（地基 Task 5 前半）

**日期** 2026-10-16 · **单一真源** `skills/douyin-pro/scripts/layout_selfcheck.py::VUE_GUARDS`
**本表由命令现生成，勿手改**：`python skills/douyin-pro/scripts/layout_selfcheck.py --vue-guards`
机检：`path_b_selftest.py::t_vue_branch_guard_registry_is_complete`

## 为什么要这张表

Vue-only 版式没有 `compositions/*.html`，结构闸天然扫不到它。没有登记，就没人知道
17 条里哪几条是"换了地方守"、哪几条是"根本没人守"—— 后者会被前者的存在感盖住。
四种状态里只有 `reused` 是"同一条谓词跑在组件工件上"，`moved` 必须点名性质由谁守，
`unwired`/`none` 就是洞，必须点名收口的 Task，且**洞的条数被钉死为 2**（改了不更新表也红）。

## 接线做法（一次抽取，两分支共用）

`check_layout` 里规则 6/8/9 三段抽成 `check_momentum_budget` / `check_font_rules` /
`check_px_typography`，新增 `check_component(sfc_path)` 调**同一批函数**，只换两处口子：

- 取文本：SFC 的 `<style>` / `<script>`（不是子合成文件的 `<template>` 内联块）；
- 补间目标：`xEl.value!` → 用模板同标签的 `ref`/`class` 解析成 class 集合，再走
  静态支同一个 `declarations_for_classes`。出现 `"#id"`/`".class"` 选择器反而红
  （组件禁跨镜串目标）。

静态支回归：`layout_selfcheck` 对 path_b **227 文件 0 违规**、path_c **7 文件 0 违规**，
`path_b_selftest.py` **242/242**（抽取段的反向覆盖由既有 `t_cjk_gate_*` 等承担）。

## 登记表（快照）

| 不变量 | 状态 | 站点 | 说明 |
|---|---|---|---|
| `CANONICAL_FONT_LOCAL_OVERRIDE` | reused | `component:check_component` | 同上。 |
| `CAPTION_RESERVE_INTRUDED` | none | `none` | 文本口径对组件会**假红**（偏移相对内层 stage 不是 #root），而引擎的 --caption-zone 已用活体负例证明不是侵入探测器（地点行渲到 85.6cqh，check --strict 仍 0 finding，见 evidence/2026-10-16-task5-precheck-findings.md）。只能按像素几何口径做。收口：Task 5 的普查层像素闸。 |
| `CJK_FAMILY_USED_NOT_DECLARED` | reused | `component:check_component` | 跑 <style> 原文；Vite 只做压缩不改族名。 |
| `CJK_FONT_LOCAL_NOT_INSTALLED` | reused | `component:check_component` | 同一份在装口径（本机点测的 5 个名字）。 |
| `CONTENT_OUTSIDE_TEMPLATE` | moved | `vue-build:编译出 dist/vue/assets` | 组件样式不会「掉进 head」，但它的对应风险是样式没编译出资产或没发 <link>，由 vue-build 那条 + selftest:t_emit_host_links_vue_css_before_runtime 守。 |
| `CONTRACT_ID_MISMATCH` | moved | `vue-build:composition 身份不写死` | 子合成「根 id == timeline 键」在组件里由同一个变量保证：注册键 = 传入的 compositionId = clip 的 data-composition-id。写死字面量即红（含反向：selftest:t_two_same_role_vue_mounts_have_unique_targets 守唯一化）。 |
| `MAGIC_BUDGET_VALUE` | reused | `component:check_component` | 跑 SFC 的 <script> 块。口径两分支一样弱：只查具名常数**声明了**，不查它有没有被用（`Math.max(0.6, …)` 绕过 MIN_DRIFT 这里不红）—— 要收紧就两边一起收，别只收组件支。 |
| `MISSING_CJK_FONT_FACE` | reused | `component:check_component` | 接线时 field-a 真的缺这份 face（混挂时被 hook-a 的「全局 @font-face」遮住了）—— 这条不是假想洞。 |
| `MISSING_CONTINUOUS_MOTION` | reused | `component:check_component` | enumerate_tweens 对 ref 目标同样产出变量文本，所以 driftDur 出现与否的判据不用改。 |
| `MISSING_DRIFT_DURATION` | reused | `component:check_component` | 同上。 |
| `MISSING_SLOT_VARIABLE` | moved | `contracts:validate_contract` | 静态支从 HTML 的 data-composition-variables 里找 slotSeconds；组件支的变量表在 contract.toml，由 validate_contract 要求同一格存在（动量预算依赖它）。 |
| `MISSING_TWEEN_TARGET` | reused | `component:check_component` | 目标口径换成 ref：解析不到对应标签就红；用选择器也红（组件禁跨镜串目标）。 |
| `NO_ROOT_COMPOSITION_ID` | moved | `selftest:t_vue_only_contract_is_the_registry_for_its_role` | 组件没有 <div id="root" data-composition-id>：id 挂在发射器写的 clip 上，取值由 contract.toml 供（那条闸逐字段比契约→条目）。 |
| `NO_TEMPLATE` | reused | `component:check_component` | 同一条 code 由 check_component 发。对 SFC 它近乎恒真（没有 <template> 先编译失败），登记成 reused 而不是 moved，是为了让「谁发的这条」在表里只有一个答案。 |
| `NO_TIMELINE_REGISTER` | unwired | `vue-build:时间轴注册键不写死` | 今天那条 TS 闸只查「键不是字面量」，组件**一条都不注册**时它是绿的 —— 缺「注册必须存在」这一半。收口：Task 5 在 vue-build 里补一条正向断言。 |
| `PX_TYPOGRAPHY` | reused | `component:check_component` | 跑 <style> 原文。⚠ 口径差异要认：Vite 会把 `inset:0 0 36cqh 0`展成四条 top/right/bottom/left —— 所以 px 判定用源文更安全，而 bottom 类判定（规则 7）用源文反而更不安全。 |
| `SURFACE_OPACITY_TWEEN` | reused | `component:check_component` | ref → 同标签 class → declarations_for_classes → background 判定，与静态支共用同一个谓词函数。 |

合计 17 条：reused 11 · moved 4 · 洞 2（CAPTION_RESERVE_INTRUDED, NO_TIMELINE_REGISTER）

## 接线当场抓到的真洞

`field-a` **原来没有中文 `@font-face`**。混挂时 hook-a 的 CSS 里有一份全局 face，
所以探针片子看着正常；一版纯 `field` 的片子（全镜无 hook）会静默回落系统默认字 ——
这正是静态支 `MISSING_CJK_FONT_FACE` 逐文件核的理由。已补进组件，闸 `t_vue_only_layouts_pass_the_reusable_invariants`
从此盯住。

## 变异证明（登记表闸，6 处）

| 变异 | 结果 |
|---|---|
| R1 删掉一行登记 | 红：登记表与规则表分家 |
| R2 状态写成不认识的值 | 红：状态不认识 'fine' |
| R3 站点指向不存在的闸 | 红：站点不存在或写法不认识 |
| R4 洞没点名收口 Task | 红：洞必须点名收口的 Task |
| R5 洞被悄悄补上、数没改 | 红：洞数变了（应为 2，实为 1） |
| R6 洞行的部分守卫改名、表没跟 | 红：洞行点名的部分守卫不存在 |

R6 是**先漏后补**的一条：第一版只解析 `reused`/`moved` 的站点，洞行的 `site` 写错不红
（表在撒谎却没人管），所以把解析扩到 `unwired` 行。

`check_component` 自己的反向覆盖（临时副本上实测，5 改 4 红）：去掉 `@font-face` →
`MISSING_CJK_FONT_FACE` + `CJK_FAMILY_USED_NOT_DECLARED`；`chipEl` 改 opacity 擦入 →
`SURFACE_OPACITY_TWEEN`；补间一个模板里没有的 ref → `MISSING_TWEEN_TARGET`；
排版写 px → `PX_TYPOGRAPHY`。第五条"拆掉两条 drift 位移中的一条"**不红是对的** ——
`MISSING_CONTINUOUS_MOTION` 的口径是"至少一条"，两条全拆才红（已复测）。

## 还剩两个洞

1. `CAPTION_RESERVE_INTRUDED`（`none`）：文本口径对组件假红，引擎 `--caption-zone`
   已用活体负例证明不拦（地点行渲到 85.6cqh，`check --strict` 仍 0 finding）。
   收口 = 普查层像素几何闸（同时补上静态支一直缺的法则 17 填幅）。
2. `NO_TIMELINE_REGISTER`（`unwired`）：TS 那条只查"注册键不写死"，组件**一条都不注册**时
   它是绿的。收口 = vue-build 补一条正向断言（`window.__timelines[` 必须出现）。
