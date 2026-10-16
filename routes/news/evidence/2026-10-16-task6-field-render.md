# Task 6 真渲染闭环 · 第一条含 `field` 镜的成片 + before/after 同稿对比

**日期** 2026-10-16 · 计划 `docs/plans/2026-10-16-vue-only-layout-foundation-plan.md` Task 6

## 判据与结果

| Task 6 判据 | 结果 |
|---|---|
| `--target-seconds 30` 落带内 | **29.568s**（27–33 带内）；逐镜 8.23 / 11.04 / 10.30s |
| `check --strict` 0/0 | ✅ ok=True（五段全 0 finding） |
| 零 WARN/ERROR | ✅ render.log 0 条，888/888 帧 |
| 逐镜尾段动量达标 | ✅ hook 0.0370 · **field 0.0029** · closer 0.0166（阈 0.002） |
| before/after 联络表交目视 | ✅ 见文末两张表（同稿、同正文、唯一变量＝第 2 镜版式） |

命令（生产形态，不 `--skip-render`，真取图真配音）：

```
python skills/douyin-pro/scripts/path_b_build.py \
  --input .harness-news-runtime/articles/t004-field-after-scenes.json \
  --template news-coral --work-dir .harness-news-runtime/tmp/t004-after \
  --output .../final.mp4 --source 央视新闻 --kicker 要闻速读 --target-seconds 30
```

## before/after：同一镜、同一份正文，只换版式

两份稿件的三条 `body` **逐字相同**（Σ 都是 29.568s），差异只有第 2 镜：
`story`（静态支）vs `field`（Vue-only 新角色）。

| 镜 | 版式 | 最底墨线 | 法则 17（≥71.5cqh） |
|---|---|---|---|
| 1 | hook（静态） | 66.56cqh | ✗ 空 12.9 |
| 2 before | **story**（静态） | **58.70cqh** | ✗ 空 20.8 |
| 2 after | **field**（Vue-only） | **77.40cqh** | ✅ |
| 3 | closer（静态） | 58.07cqh | ✗ 空 21.4 |

⇒ 换结构买到 **+18.7cqh 的填幅**，且 `field` 是今天整批量过的版式里**唯一过法则 17 的一条**。
上一轮"31 包 0/31 达标"因此不是测量偏差 —— 是版式事实，而新结构确实能把它拉过线。

## 有图态那问：今天无法用测量回答

我上一轮推荐"拿一条有图成片再量一遍，看空带是不是照片吃掉的"。跑完的事实是：
**三镜全部降级无图**，日志逐镜报
`「要闻速读」没有授权/尺寸/相关性都合规的图 ⇒ 本镜降级为绘制地面`。
⇒ 供货仍是 0（与 `project-news-supply-gaps` 记的 0/9 一致），**"有图态"这个前提今天不成立**，
那条问题只能等影像供给解决后才能量。`content_floor` 已经按"只量无图镜"设计，
所以它报的就是产线当前的真实形态。

## 顺带修的一个发射器 bug（生产路径才触发）

全链路最后一步炸：

```
❌ '.harness-news-runtime/tmp/t004-after\shots.json' and
   'D:\...\t004-after\shots.json' are the same file
```

`--work-dir` 给**相对路径**时（普查与本地跑法都这样），`work` 与 `final` 所在目录是同一条路径的
两种写法，`shutil.copyfile` 抛 `SameFileError`。危险性在于它发生的位置：片已渲完、字幕已烧完、
AIGC 元数据已核验，**整轮却以 exit 1 收场**。修法是先比绝对路径、同址即跳过。
普查没撞上是因为它带 `--skip-render`，走不到 finalize。

## 交付物（可点）

- after 成片 `.harness-news-runtime/tmp/t004-after/final.mp4`（1.28 MB / 29.568s / 含 ② 元数据）
- after 联络表 `routes/news/evidence/2026-10-16-task6-render/contact-after-field.jpg`
- before 联络表 `routes/news/evidence/2026-10-16-task6-render/contact-before-story.jpg`

运行时目录 gitignored，成片只在本机；两份联络表已入库当账。

## 待拍（没变，只是多了数据）

1. **填幅这笔账**：`field` 证明"往下推"做得到，但 30 个包的 hook/closer/story 仍是 58–67cqh。
   动的是 227 份模板的骨架，不是开关。
2. **影像供给**：0/9 → 今天 0/3。不解决，`field` 的 none 单态就是唯一能上的现场版式。
