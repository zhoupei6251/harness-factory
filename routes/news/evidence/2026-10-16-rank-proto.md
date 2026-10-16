# rank 结构原型 · 量级条值不值得它的诚实负担（2026-10-16）

> 触发：spec §7 结构队列的第二个（`rank` 不依赖影像，是「不同题材用合适结构」里当下能兑现的那条）。
> 探针问题只有一个：**TOP-N 排行榜该不该画量级条** —— 因为 [frame.md §3 法则 5](../../../skills/douyin-pro/templates/hyperframes_path_b/news-coral/frame.md)
> 明写「源数据没有诚实分母时不画比例条（旧 probe 的 bar 永远满格就是假数据）」。
> 两版同一份数据、同一套字阶与留白，只差 bar。可复看：`bar-frame.png` / `plain-frame.png`，
> 源文件 `rank-bar.html` / `rank-plain.html`（丢进任意 HyperFrames 项目目录
> `npx hyperframes render -o out.mp4 -f 25 --quality=draft --no-browser-gpu`，Node ≥22）。
> ⚠️ 数据是虚构的排版探针，屏上右上角常驻「探针·数据为虚构·请勿发布」。

---

## 1. 结论：**带 bar**，但它的诚实负担必须一起设计进去

`plain` 版干净、层级清楚，但 **1188 万 vs 742 万差 60% 这件事读不出来** —— 观众得自己心算除法。
而排行榜的核心信息就是**梯度**，不是名次本身（名次已经由 01–05 表达了）。
`bar` 版一眼看出上海与成都差一截、01–02 咬得很近 —— 这是 `plain` 给不了的。

⇒ bar 的信息增益明确，值得它带来的两条负担：① 必须标口径；② 必须限制容量。

## 2. 三处实测缺陷（都是看帧看出来的，不是推演出来的）

| # | 缺陷 | 证据 | 修法 |
|---|---|---|---|
| 1 | **口径标注与第 5 行相撞** —— 「条长 = 相对第一名，非占总量比例」压在 05 的 bar 和 `742万` 上 | `bar-frame.png` 底部 | 标注挪到 bar 区上方（跟着标题带走），或行区 `bottom` 抬到 26cqh |
| 2 | **bar 版容量比 plain 低** —— 5 行已顶到字幕禁入区边缘；plain 同字号能放 6–7 行 | 两版对比 | 容量必须**写进契约**（像 `rail` 的 `row_capacity`），不能靠写稿人自觉 |
| 3 | **plain 版底部空一大片** —— 行区用 `space-between`，行数不足时全堆在上半 | `plain-frame.png` 下半 | 行距按 N 自适应（`N≤4` 时收紧），或固定行高 + 顶对齐 |

第 2 条是这次最有用的产出：**`rank` 的容量上限是"带不带 bar"决定的，不是"几行好看"决定的。**
所以 `rank` 至少要有两个变体（`rank-bar` ≤5 行 / `rank-plain` ≤7 行），由发射器按行数选，
而不是一个版式硬塞。

## 3. 法则 5 在 `rank` 里的具体形态

- bar 一律 `scaleX = value / max(values)`：**第一名满格是事实，不是设计**；其余按真实比值。
  旧 probe 的病根是"永远满格"，即所有 bar 都 1.0 —— 那才是造假。
- **没有第二组数时不画对比条**（`versus` 那条结构另说）。
- 口径标注必须在脸上：观众默认会把 bar 读成"占总量百分比"，不写就等于让画面替我们说一句我们没说过的话。

⇒ 这两条都可机检，且必须是机检（不能只写在文档里）：
1. `t_rank_bar_matches_value_ratio`：解析版式里每根 bar 的 `scaleX` 终值，逐项比对
   `value/max`，误差 > 0.02 即判红；反向负例：把某根 bar 手改成 1.0，断言必须变红。
2. `t_rank_requires_basis_label`：`rank-bar` 变体里必须存在口径文案节点，缺即判红。
3. `t_rank_row_capacity`：`rank-bar` >5 行 / `rank-plain` >7 行时发射器必须拒收（同 `rail` 的条目超行闸）。

## 4. lint 归因（别把它当设计问题）

两版各 2 条 warning：`studio_missing_editable_id`（inline clip 无 id）与
`nested_structure_needs_subcomposition`（没用 sub-composition 挂载）。
**都是原型脚手架造成的** —— 产线的 clip 由发射器生成，自带 `id="shot-N"` 与
`data-composition-src`，接线后自然消掉。生产判据仍是 `check --strict` 0/0。

## 5. 与 `field` 那次的一致教训

`field` 的探针否证了"角标够用"；`rank` 的探针**没有否证 bar**，但暴露了容量与相撞两个真问题。
两次的共同点：**只看代码/CSS 是看不出来的**（`bottom: 22cqh` 与 `bottom: 22.6cqh` 差 0.6cqh
在代码里毫无异常，渲出来才知道压字了）。⇒ spec §5 的每片"目视 compare 表"不是形式，
是这批缺陷唯一的发现渠道。
