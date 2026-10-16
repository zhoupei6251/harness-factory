# Task 5 开工前的三条实测（推翻两处我上一轮的判断）

**日期** 2026-10-16 · 承接 `2026-10-16-vue-only-merge.md`（Task 4）

## 1. 我上一条推荐里"先落 `t_vue_only_layouts_pass_layout_selfcheck` 再按闸修填幅"是错的

`layout_selfcheck` 的 17 条不变量**没有"填幅"这一条**。17 个 code 全列在这里：
`NO_TEMPLATE` / `CONTENT_OUTSIDE_TEMPLATE` / `NO_ROOT_COMPOSITION_ID` / `NO_TIMELINE_REGISTER` /
`CONTRACT_ID_MISMATCH` / `MISSING_SLOT_VARIABLE` / `MISSING_TWEEN_TARGET` / `SURFACE_OPACITY_TWEEN` /
`MAGIC_BUDGET_VALUE` / `MISSING_DRIFT_DURATION` / `MISSING_CONTINUOUS_MOTION` /
`CAPTION_RESERVE_INTRUDED` / `MISSING_CJK_FONT_FACE` / `CJK_FAMILY_USED_NOT_DECLARED` /
`CJK_FONT_LOCAL_NOT_INSTALLED` / `CANONICAL_FONT_LOCAL_OVERRIDE` / `PX_TYPOGRAPHY`。

法则 17（填幅）只在 **`hf_compile`** 里实现（`MAX_BOTTOM_DEAD_CQH = 8.0`，path_c 编译配方按
`Step.height_cqh` 算几何），静态 path_b 的 227 份 HTML 和 Vue 支都**没有**这条闸。

而且那帧 `field` 的"下沿 22% 空带"我目测错了 —— 量出来：

```
最亮(>120)行 y=1485 → 77.3cqh        字幕禁入区上沿 = 80cqh (1536px)
80–100cqh 各段行最大亮度 = 10（= 地面本色，无内容）
```

77.3cqh 距 80cqh 只空 **2.7cqh < 8.0** ⇒ 按法则 17 的口径**这块不违规**，下面那段黑是
**留给烧录字幕的家**（探针用 `--skip-render`，没配音也就没字幕，所以看着空）。
`field` 现在不需要修填幅。帧图见 `2026-10-16-vue-only-merge/field-frame-after.png`。

## 2. 但字幕禁入区对 Vue 支确实**没有任何闸**（负例已渲出来证明）

`layout_selfcheck` 规则 7 只吃 CSS 文本里的 `bottom:` / `inset:`，其**成立前提是偏移相对
`#root`**（静态 composition 都是满幅根）。组件不是：`.fd-place{bottom:6cqh}` 相对的是
`.fd-stage{inset:0 0 36cqh 0}`，实际落在 42cqh。所以把规则 7 直接搬到组件 CSS 上会**假红**。

那引擎管不管？`check --strict` 带 `--caption-zone=…;severity=error`。做了活体负例：
把 `.fd-stage` 下沿 36cqh 改成 8cqh ⇒ 地点行落到 14cqh（区内）。

```
渲染后实测：最亮行 y=1643 → 85.6cqh（> 80cqh，确实侵入）
check --strict: ok=True   lint/runtime/layout/motion/contrast findings 全 0
```

⇒ **`--caption-zone` 不是侵入探测器**（它是"字幕住这儿"的声明，供引擎自己排字幕用）。
现场帧见 `2026-10-16-task5-precheck/caption-intrusion-negative.png`（地点行已在 80cqh 之下）。
结论：Vue-only 角色的字幕区判据今天**没人守**，而且它必须是**几何/像素口径**，不能是 CSS 文本口径。
便宜且忠实的做法是把它挂到渲染普查那一层（每角色渲一镜、量最底内容行），
不是塞进 `path_b_selftest.py`。

## 3. 撞出一个发射器 bug：复用 work_dir 会同时挂两代 CSS（已修）

`field-probe2/index.html` 链了两份 field-a 样式：

```
<link href="vue/assets/field-a-C-nBYAjC.css">   ← 改色前那一代
<link href="vue/assets/field-a-Ni89-8RF.css">   ← 改色后这一代
```

根因：`stage_vue_assets` 只拷不清，而 Vite 的 CSS 资产名带内容 hash，
`emit_host` 又按 `<bundle>*.css` 全发 ⇒ **哪代生效取决于 hash 的字母序**（这次 C < N，
新的恰好赢；反过来就是"改了没效"，且没有任何现象提示）。普查目录
`.harness-news-runtime/tmp/render-census/<pack>/` 正是跨轮复用的，所以不是理论风险。
我那个"改了没动"的无效负例就是被它骗出来的 —— 打在没赢的那份上。

修法：`stage_vue_assets` 先 `rmtree(work_dir/vue)` 再拷（清空放在 `bundles` 判空之前，
包从"有 Vue 镜"退回纯静态时残留也要消失）。
闸：`t_stage_vue_assets_leaves_no_stale_generation` —— 种一个 `field-a-ZZ9stale.css` +
`vue/stale-chunk.js`，重发后必须都不在；并锁"同一 bundle 至多一条 `<link>`"、
"暂存集 == 当前 dist 集"、两次暂存交出同一路径表。
变异证明：把 `rmtree` 改成 `if False` ⇒ 该闸当场红（"复用时上一代 CSS 资产还留着"）。

`path_b_selftest.py` **240/240**。
