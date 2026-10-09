# 新闻域出片提速设计（吞吐摊薄 ≤ 3 分钟/条 · 零云费不变）

> 日期：2026-10-09 ｜ 状态：设计已批准，待实施计划
> 路线：方案 A（保 hyperframes，消固定开销 + N 路并行）；方案 B（渲染引擎旁路）留作后备
> 上游背景：`routes/news/RUNBOOK-first-run.md`（2026-10-08 实跑暴露的缺口清单 P0 #1/#2/#3）

## 1. 目标与验收口径

- **成功标准**：批量渲染 ≥4 条约 60 秒的稿件，从"发射"到全部 mp4 出炉的墙钟时间 ÷ 条数 **≤ 3 分钟/条**（吞吐量摊薄口径，非单条延迟）。
- **不变量**：
  - 零云费：不引入任何付费 API / 云服务 / 按次扣费工具；
  - 成片规格不变：1080×1920、h264+aac、字幕烧录、AIGC 侧车（`aigc.json`）与 `check_publishable.py` 发布闸门照旧；
  - 32 pack 模板资产（frame / host / compositions）一行不动；
  - 三道闸（`path_b_selftest.py` / `layout_selfcheck.py` / `audit_pack_contrast.py`）继续全绿。

## 2. 非目标（本轮不做，后续迭代）

- 抖音发布闭环（账号登录、自动上传、发布回写）；
- 选题端强化（更多免费热榜源、真热度信号）；
- 中文配图能力（图源与 31 pack 图板扩展）；
- 渲染引擎替换（puppeteer/ffmpeg 直渲）——仅当阶段 0 决策门触发时重新评估。

## 3. 阶段 0 · 实测拆时（先拿数据，再动刀）

给渲染链路加分段计时，覆盖：npx/hyperframes 定位 → check → TTS 配音 → 渲染 → 字幕+AIGC 烧录。**冷跑、热跑各计一次**，报告落 `.harness-news-runtime/tmp/timing/`。

目的：把 RUNBOOK P0 #1 里"第二次应快很多"的悬念变成数字，确认时间大头究竟在 npx 拉包、Google Fonts 拉字体，还是渲染本身。

**决策门**：热跑单条 > 12 分钟（按 3-4 路并行也无法把摊薄值拉进 3 分钟/条）→ 停止实施、回报用户，转方案 B（渲染引擎旁路）评估。不硬做。

## 4. 组件设计

### 4.1 组件 ①：hyperframes 可执行定位（消 npx 重装）

- `skills/douyin-pro/scripts/path_b_build.py` 新增 `--hyperframes-bin` 旗标；
- 自动探测顺序（每步结果打日志，带真出处）：
  1. 显式旗标 `--hyperframes-bin`；
  2. 项目 `node_modules/.bin/hyperframes`；
  3. npm 的 `_npx` 缓存（`%LOCALAPPDATA%\npm-cache\_npx\`）内已有的 hyperframes 0.8.141（已确认存在于 `_npx\702923228c2ce1e6\`）；
  4. 回落现状 `npx -y hyperframes`（仅当以上全缺）。
- `skills/douyin-pro/scripts/install_path_b_deps.py --check` 把 **edge-tts** 纳入依赖校验（RUNBOOK P0 #3）。

### 4.2 组件 ②：字体离线化（消 Google Fonts 拉取）

- 阶段 0 先确认字体拉取的真实机制（模板 `@import` 还是 hyperframes 渲染器内建请求）；
- 改为本地 `@font-face`，字体文件指向 `~/.cache/hyperframes` 已有缓存（276M）或随仓库分发的字体子集；
- 改动落在 host 共享层一处，不逐 pack 改版式；离线失效时降级为渲染器自带回退字体并打警告（取"慢但能出片"，不停机）。

### 4.3 组件 ③：`batch_render.py` 并行发射器

- 位置：`routes/news/scripts/batch_render.py`（新闻域编排层，薄封装 `path_b_build.py`）；
- 输入：批量任务清单（每条 = scenes.json 路径 + pack + 输出名），文件或 CLI 多参数；
- 并发：`--jobs N`（默认 3，16 核机器的保守值），每路独立工作目录（沿用 `DEFAULT_WORK_ROOT = .harness-news-runtime/work/`，互不冲突）；
- 输出：每条成片照旧落 `.harness-news-runtime/videos/<id>/`，含 `aigc.json` + `contact-sheet.jpg`；
- 汇总：批次报告（逐条状态、耗时、摊薄值）打屏 + 落盘。

## 5. 错误处理

- **失败隔离**：单条红不拖垮批次，逐条状态 + 批次汇总退出码非零（R6 不静默）；
- **报真话**：并行子进程的 stderr 原文并进汇总报告，禁止只给路径（"报不出原因的拒绝等于没有拒绝"）；
- **闸门不放松**：每条成片独立过 `check_publishable.py`，批量化不豁免任何一条；
- 并发资源不足（内存/CPU 打满）的表现是变慢而非失败，`--jobs` 可下调，不做自动调参。

## 6. 测试与验收

- `path_b_selftest.py` 增补断言：
  - 可执行探测顺序正确、探测结果带真出处（含"假绿"负例：探测落空必须回落而不是假装成功）；
  - 批量清单解析（坏清单当场点名停机）；
  - 失败隔离语义（一条失败 → 批次退出码非零 + 其余条目仍出片）。
- 真验收（落 `routes/news/` 侧验证单，`git add -f` 进版本管理）：
  - 批量渲 4 条真实稿件（复用 t001/t002 稿件或 `fixtures/`）；
  - 冷跑 / 热跑计时数据 + 摊薄值 ≤ 3 分钟/条；
  - 4 条成片全部过 `check_publishable.py`，三道闸保持全绿。

## 7. 风险与已知张力

| 风险 | 处置 |
|------|------|
| 热跑单条仍 > 12 分钟（渲染本身慢，固定开销不是大头） | 阶段 0 决策门拦住，转方案 B 评估，不硬上并行 |
| hyperframes 版本升级导致 `_npx` 缓存路径漂移 | 探测落空即回落 `npx -y` 并告警，不因定位失败停机 |
| 字体离线化后字面率变化影响 AIGC 角标字芯判据（D8 擦边字号无余量） | 改字体后必须重跑 `verify_aigc_badge.py` 重量一次字面率 |
| 并行 3-4 路 × headless 浏览器吃内存 | 默认 jobs=3 保守起步，验收时按实测内存调整 |
