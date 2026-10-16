# rank 落成第二个 Vue-only 角色 · 顺带挖出 dist 层的同款样式事故

**日期** 2026-10-16 · 承接 `2026-10-16-task6-field-render.md`（地基 Task 1–6 之后的第一个新结构）

## 落地物

```
src/web/entries/rank-a/{contract.toml, RankA.vue, main.ts, main.html}
```
设计出处 `2026-10-16-rank-proto.md`：**带 bar**，容量上限由"带不带 bar"决定（≤5），
两条诚实负担一起进代码，不是只写文档。

成片数据（`news-coral`，虚构排版数据）：

| 镜 | 版式 | 最底墨线 | 法则 17 |
|---|---|---|---|
| 1 | story | 58.91cqh | ✗（已记录的 story 行为） |
| 2 | **rank** | **76.88cqh** | ✅ |
| 3 | field | 77.4cqh | ✅ |

普查夹具 `census-probe-scenes.json`（7 镜，2 镜走 Vue-only 契约）单包复验：
`clips 7 · vue 3 · 1617/1617 帧 · 0 WARN · intrude 0 · pass true`。

## 三条新闸（都可反证）

1. **尾部可选行**（`contract.optional`）：rank 的容量是 5，但真实稿件常只有 3 条 ——
   固定 5 行会把绝大多数榜单稿拒掉。规则：只准长在 `itemN*` 的**尾部**，
   标在中间（item3 可选而 item4 必填）或非条目 id 一律 `ContractError`。
   填不出来时落空串由组件收行，`row_capacity` 仍是 5（超行照旧警告）。
   变异 N6b：把"必须是尾部"那条判据关掉 → `t_optional_rows_must_be_a_tail` 红。
2. **量级条单位必须一致**（`_check_bar_units`）：条长 = `value / max(values)`，
   `3亿` 与 `1188万` 并排时字面比是 3:1188，条会差 400 倍而屏上没有任何提示 ——
   那是拿图替我们说一句我们没说过的话。**拒发射**，不是"组件里小心点"。
   变异 N2/N3：不调闸 / 只查有没有数字 → `t_rank_bar_refuses_mixed_units` 红。
3. **口径标注是版式常量，不是契约变量**：我第一版把 `basis` 写进 variables，
   自检 `t_every_layout_variable_id_has_a_source` 当场报"四条来源都不沾"——
   这一红反而指出设计错了：**能改标签就等于允许「条按相对第一名画、字写占总量比例」**。
   现在标注是组件里的字面文本，`t_rank_bar_honesty_is_wired` 要求
   ① 存在带字面文本的 `rk-basis` 节点（插值即红）② bar 的补间用 `ratio(...)` 表达式
   （常量 1 即红，就是旧 probe"bar 永远满格"那个形态）。变异 N4/N5 各红一次。

## 挖出的真事故：`dist/vue/assets/` 会攒旧代 CSS

现象：屏句 `{{ vars.onscreen }}` 数据在 clip 里、DOM 里有、CSS 也对，**画面上就是没有**。

根因：`vite.config.ts` 是 `outDir:"dist" + emptyOutDir:false`，每次 `npm run build:templates`
只**加**新 hash 资产、不清旧的。`dist/vue/assets/` 一度同时躺着 rank-a 的**三代** CSS，
`stage_vue_assets` 整目录拷走、`emit_host` 又按 `<bundle>*.css` 全发 ⇒
**三份一起挂进 host，哪份生效取决于文件名字母序**。最早那版 `.rk-sub{position:absolute;bottom:24cqh}`
赢了，屏句被排到画面底部、被行区盖住。

上一轮我在 **work_dir** 那层修掉的是同一类事故（暂存目录不清），但**源头 dist 还漏着** ——
`t_stage_vue_assets_leaves_no_stale_generation` 当时还绿，因为它断言的"暂存集 == dist 集"
在 dist 本身就脏的时候是成立的。两处一起修：

- `package.json` 加 `prebuild:templates`：build 前清 `dist`（和 vue-build 测试自己清 dist 的
  做法对齐 —— 那个测试早就知道陈旧产物会让断言假绿，但只有它清，裸跑 build 的人不清）；
- `stage_vue_assets` 见到同一 bundle 有多条 CSS 直接 **`EmitterError`**，
  不"挑最新的一份"（mtime 在拷贝后不可靠，猜错是静默的）。
  闸 `t_stage_vue_assets_refuses_two_generations`。

## 我自己在这条上连错两次，都记下来

1. **手算行高**：按 CSS 估 5cqh/行，实测 9.6cqh/行 ⇒ 5 行溢出容器。第一版压进字幕区
   （85.4cqh 判红），第二版把屏句挪到标题带却因编辑失误让它和第五行**叠在一起**。
   最终改成**容器固定 + 每行 `flex:1 1 0` 等分**：N 行永远吃满且不越界，
   法则 10 的"任何 N 下不得留 >15% 整块空白"由同一条机制满足。行高不该由人估。
2. **测试里的 stem 正则贪错**：`-[A-Za-z0-9_-]{6,}` 会把 `a-CVY5PZqH` 整段吃掉，
   `field-a` 被剥成 `field`，种下去的假资产 glob 不到 ⇒ 新闸"绿着通过"。
   改成从**路由函数**取 bundle 名，不猜文件名。

## 闸况

`path_b_selftest` **250/250** · `npm test` all ok · 静态支 **227 文件 0 违规** ·
`check_scene_contract --demo` 通过 · 单包普查 `pass:true`。

## 遗留

- `rank` 只有 a 簇组件。路由**不会**去找 `rank-b`：`vue_bundle_for` 先查契约（契约给 `rank-a`），
  只有没有契约的角色才走 `CUTOVER_ROLES` + `variant_of` 那条路 —— 这是代码事实，
  不是"跑过没报错"。新角色因此天然是"一角色一组件、31 包共用"，与 closer/story 那种
  按簇分变体的旧角色不同。将来真要 a/b 两版（比如 rank-plain），得靠 `(role, variant)`
  双键发现，`discover` 已经按这个键查重。
- 单包复验只跑了 `news-coral`；全量 31 包普查留到下一次统一跑（含 rank 镜）。
- 探针数据是虚构的，成片不进发布链路；`field` 的影像供给那条仍未拍。
