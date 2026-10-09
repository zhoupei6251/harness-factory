# 新闻域出片提速 — 吞吐验收验证单

> 日期: 2026-10-09 · 计划: `docs/superpowers/plans/2026-10-09-news-render-speedup.md` Task 3/4/6
> 输入: `skills/douyin-pro/scripts/fixtures/badge_probe_shots.json`（5 镜探针稿，成片约 43s）
> 计时证据: `.harness-news-runtime/tmp/timing/cold.json` / `hot.json` / `batch4.json` / `batch/job0*.json`

## 0. 环境前置（Node ≥ 22，批渲与冷/热跑共同前提）

- 本机默认 `node` 是 **20.9.0**，过不了 hyperframes 门禁（`HyperFrames requires Node.js >= 22`）。
- 处置：取 nvm 已装的 **Node v23.11.1**（`D:\Users\zhoupei\AppData\Local\nvm\v23.11.1`，
  `nvm list` 现存 22.20.0 / 23.11.1 / 26.8.2），以 **PATH 前缀注入** 方式生效：
  `$env:Path = "D:\Users\zhoupei\AppData\Local\nvm\v23.11.1;" + $env:Path`，注入后 `node --version` = `v23.11.1`。
- **不执行 `nvm use`、不改全局默认、不动系统配置**；每次跑渲染命令都需在同一 PowerShell 会话内先注入
  （会话间环境不保留）。PowerShell 串联用 `;`（本机不支持 `&&`）。

## 1. 冷/热跑逐段秒数（Task 3 实测，见 tmp/timing/summary.md）

| 阶段 | 冷跑(s) | 热跑(s) | 差值(s) | 说明 |
|------|--------:|--------:|--------:|------|
| parse | 0.01 | 0.00 | -0.01 | 5 镜 JSON 解析 |
| dub | 12.36 | 12.57 | +0.21 | edge-tts 网络合成，无本地缓存，冷热持平 |
| images | 0.00 | 0.00 | 0.00 | 本 fixture 无逐镜取图 |
| emit | 0.01 | 0.01 | 0.00 | 合成 HTML 生成 |
| gate | 16.17 | 15.73 | -0.44 | 版式自检 + hyperframes check |
| render | 33.68 | 30.24 | -3.44 | hyperframes 渲染 silent.mp4 |
| motion | 0.55 | 0.58 | +0.03 | 运动审计 |
| mux | 4.72 | 5.13 | +0.41 | ffmpeg 拼音频 + 烧字幕 |
| finalize | 1.08 | 1.66 | +0.58 | 联络表 / shots.json / 元数据 |
| **total** | **68.57** | **65.92** | **-2.65** | |

- 对比历史基线（单条 15-25 分钟 = 900-1500s）：**约快 14-23 倍**。主因 Task 2 的 hyperframes 可执行定位
  命中项目 `node_modules/.bin/hyperframes.cmd`（日志打 `[hf] hyperframes 出处: 项目 node_modules (hyperframes.cmd)`），
  每次 `npx -y` 现场拉包的 5-15 分钟消失。

## 2. Task 3 决策门结论

- 判据：热跑 `total_seconds` ≤ 720s → 继续；> 720s → 停、转方案 B。
- **实测热跑 total = 65.92s ≤ 720s → ✅ 通过，继续 Task 4/5/6。**

## 3. Task 4 字体处置分支判定

- 判据：热跑 `render` 段 ≤ 180s → 分支 A（字体缓存已命中，组件②免做）。
- **实测热跑 render = 30.24s ≤ 180s → 分支 A。** 字体缓存 `~/.cache/hyperframes/fonts`
  （inter / jetbrains-mono / league-gothic）已命中，**组件②（字体离线化）免做，无代码改动**。

## 4. Task 6 真批渲 4 条（batch_render.py · --jobs 3）

清单 `.harness-news-runtime/tmp/timing/batch4.json`：4 条同输入、4 个 master 模板
（news-policy / news-coral / news-onsite / news-stat），均带 `source` + `aigc-producer`。

汇总行（原文）：

```
批次完成: 2/4 成功 | 墙钟 114.8s | 摊薄 28.7s/条
  ✅ #1 .harness-news-runtime/tmp/timing/batch/b1/final.mp4 113.2s
  ✅ #2 .harness-news-runtime/tmp/timing/batch/b2/final.mp4 114.8s
  ❌ #3 .harness-news-runtime/tmp/timing/batch/b3/final.mp4 38.2s | rc=1 | …\batch\b3\build.log
  ❌ #4 .harness-news-runtime/tmp/timing/batch/b4/final.mp4 55.5s | rc=1 | …\batch\b4\build.log
```

- **摊薄实测 28.7s/条（墙钟 114.8s ÷ 4 条）≤ 180s/条 → 吞吐判据 ✅ 达标。**
  保守口径（只按成功条目摊薄 114.8 ÷ 2 = 57.4s/条）同样 ≤ 180s/条，达标结论不依赖口径。
- 成功条目单条墙钟 113-115s，与热跑 65.9s 的差额是 3 路并行争用 CPU/GPU 的合理上浮。
- **批次完整性 2/4 未达计划预期（4/4），如实记录，见 §6 异常。**

## 5. 闸门复核输出摘要（原文末行 / 退出码）

| 闸门 | 结果 |
|------|------|
| `check_publishable.py b1/final.mp4` | `✅ 可发布(按 D14: ② 在、① 点名关掉)` · **EXIT=0**（输出带 `③ 必须带: --declaration 内容由AI生成` 属正常，姿态 `declaration=required`）|
| `check_publishable.py b2/final.mp4` | `✅ 可发布(按 D14: ② 在、① 点名关掉)` · **EXIT=0**（同上）|
| `check_publishable.py b3 / b4` | **不适用**：无成片（gate 在渲染前拒收，`final.mp4` 未产出）|
| `path_b_selftest.py` | `[selftest] 全绿 86/86` |
| `batch_render_selftest.py` | `[batch-selftest] 全绿 5/5` |

## 6. 异常与处置（照实记录，不粉饰）

1. **b3（news-onsite）/ b4（news-stat）被 hyperframes `check --strict` 拒渲**，rc=1，发生在 gate 段
   （dub 已过、render 未开始），非吞吐问题。真实原因（复跑留存的 `check.json` 原文）：
   - b3 `news-onsite/compositions/catalog.html`：条目序号 `01/02/03` 白字压琥珀底 `rgb(242,201,76)`，
     对比度 **1.59:1**（WCAG AA 需 3:1），3 条 `contrast_aa_failure` warning；
   - b4 `news-stat/compositions/catalog.html`：同位置序号，对比度 **1.81:1**，3 条同类 warning；
   - `--strict` 下 warning 即整体 `ok: false` → `path_b_build` 拒渲（闸门不放松，行为正确）。
   - 判定：**模板资产既有缺陷**（catalog 序号位没做 v007 那套「对比度临界 selector 加 padding 黑底」处置），
     与本次提速改动无关；此前只有 news-policy/news-coral 真渲过 catalog 镜，未暴露。
     按计划红线「不改 32 pack 模板资产；不放松任何闸门」**本次不处置**，列为遗留项：
     应补 `news-onsite` / `news-stat`（及其他未真渲过 catalog 镜的 pack）序号位对比度修复，
     参考 v007 的 `cl-ch` padding 黑底做法，属 D19「设计补全」性质。
2. **batch_render.py 路径上溯缺陷（本次修复）**：`BUILD` / `DEFAULT_TIMING_DIR` 原从
   `routes/news/scripts` 只上溯 2 级，落到 `routes/skills/…`（不存在），首跑 4 条全部 rc=2 秒败。
   修复为上溯 3 级到仓库根（`routes/news/scripts/batch_render.py` 一处），复跑即发射成功；
   `batch_render_selftest.py` 5/5 不受影响（其断言不覆盖路径解析）。
3. 批渲期 `build.log` 各条独立追加写 `batch/b*/build.log`，失败条目按设计保留日志落点，批次未被拖垮
   （b1/b2 在 b3/b4 失败后照常完成）—— 失败隔离符合设计。

## 7. 结论

- **吞吐达标**：摊薄 28.7s/条 ≤ 180s/条（宽松与保守口径均达标）；决策门、字体分支 A、
  两个 selftest、2 条成片发布闸门全部通过。
- **遗留 1 项**：news-onsite / news-stat 的 catalog 序号位对比度（模板既有缺陷），修完后同清单可望 4/4。
- **前置记忆**：凡渲染/批渲，先 Node v23.11.1 PATH 注入（见 §0）。
