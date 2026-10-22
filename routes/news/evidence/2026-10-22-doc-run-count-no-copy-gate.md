# 文档不许抄"跑出来的数"（D26）· 2026-10-22 实测与双向验证

> 触发：用户问「这个仓库的新闻域如何」，我实跑三道闸后发现有三个位置的计数在文档里互相矛盾、
> 且全部与真跑不符。D20/D23 早已定下「没人断言的数字就是死数字」，但那条闸只管 **pack 总数**，
> 闸门自己的计数漏在外面。本轮把口径补齐。

---

## 1. 本轮实测（这些数字**故意**只出现在这份凭据里）

| 命令 | 真跑结果 | 退出码 |
|---|---|---|
| `python skills/douyin-pro/scripts/path_b_selftest.py` | `[selftest] 全绿 253/253` | 0 |
| `python skills/news-curate/scripts/curate_selftest.py`（改前） | `全绿 39/39` | 0 |
| `python skills/news-curate/scripts/curate_selftest.py`（加闸后） | `[selftest] 40 项 · news-curate` → `全绿 40/40` | 0 |
| `python skills/douyin-pro/scripts/layout_selfcheck.py <31 个版式目录>` | `版式自检通过：227 个文件，0 条违规` | 0 |
| `python skills/douyin-pro/scripts/audit_pack_contrast.py` | `对比度审计不过：31 个 pack 里 24 条违规（另有 0 条警告）` | **1** |
| `ls skills/douyin-pro/templates/hyperframes_path_b/`（去掉 3 个非包文件） | 31 个 pack | — |
| `npm run test:render` | `[selftest] 全绿 253/253` | 0 |
| `npm run structure:audit` | `Structure audit passed.` | 0 |

## 2. 改之前文档里的"当前状态"长什么样（同五版，全错）

| 位置 | 文档写的 | 真值 |
|---|---|---|
| `ARCHITECTURE.md` §4 三道闸现状 | `全绿 78/78` · `234 文件` | 253/253 · 227 文件 |
| `RUNBOOK-first-run.md:4` 前提行 | `自检 78/78、版式 234 文件 0 违规` | 同上 |
| `ARCHITECTURE.md` §8 转录（围栏内） | `[selftest] 73 项` + `全绿 73/73` | 2026-09-29 那天的快照，早已漂 |
| `ARCHITECTURE.md` §4 / `MEMORY.md` 决策树段 / `news-workflow/SKILL.md` 步骤 1 | `load_style_pack 31/31 成功`（4 处，其中 `MEMORY.md` v008 那条还是 `32/32`） | 31 个包，逐个成功 —— 数会随删包漂（D23 就漂过一次） |
| `MEMORY.md` 普查段 | `首跑 31/31 通过` | 同上，且它是历史首跑，不该当现值引用 |
| `MEMORY.md` Vue 守卫段 | `静态支回归 227 + 7 文件 0 违规` | 227 是当日数，加一个文件就漂 |
| `DESIGN-lsh.md` §6 完成判据 | `末行输出 全绿 39/39` | 加一条断言即变 40 —— **本轮就变了** |
| `scripts/test-render.ts` 注释 | `its 251 assertions` | 253 |

旁证（**不引路径**：那份会话任务报告落在被 gitignore 的 sdd 工作目录里，不是仓库凭据）：
2026-10-14 一次 Vue 支改动的会话记录里，同一条 `[selftest] 全绿` 末行在**一天之内**是
`202/202 → 205/205 → 206/206` —— **计数五天就能漂 4 个**，抄进文档等于当场埋雷。

## 3. 落地

**改文档（删数不补数）**：`ARCHITECTURE.md` §4 两处 + §8 头注、`RUNBOOK-first-run.md:4`、
`DESIGN-lsh.md` §6、`news-workflow/SKILL.md` 步骤 1 两处、`MEMORY.md` 四处、`scripts/test-render.ts` 注释。
文档只写命令与 `N` 占位。

**加闸**：`skills/news-curate/scripts/curate_selftest.py`
→ `t_no_doc_copies_a_gate_run_count`（+ 模块级 `_RUN_COUNT_TARGETS` / `_RUN_COUNT_PATTERNS` /
`_run_count_hits`，并把 D20 那条闸的 `NEGATION` 提到 `_DOC_NEGATION` 共用，**不新增豁免词**）。
拦八种散文形状：`全绿 N/N`、`自检 N/N`、`版式自检通过：N`、`版式 N 文件`、`对比度审计通过：N`、
`N/N 成功|通过`、`[selftest] N 项`、`N assertions`。目标 = 8 个文档/脚本，缺文件即红（防静默少扫）。

**决策入档**：`ARCHITECTURE.md` §5 新增 D26。

## 4. 双向锁（真输出）

植入探针（往 `ARCHITECTURE.md` 末尾追加一行含三种形状的假数）：

```
- 假探针：本轮自检 全绿 1/1、版式 999 文件、load 5/5 成功
```

```
  FAIL  t_no_doc_copies_a_gate_run_count: 文档抄了闸门跑出来的计数（改法：只写命令，数由现跑给。见 ARCHITECTURE D26）:
  routes/news/ARCHITECTURE.md:415 「全绿 1/1」
  routes/news/ARCHITECTURE.md:415 「版式 999 文件」
  routes/news/ARCHITECTURE.md:415 「5/5 成功」
[selftest] 失败 1/40
```

还原后（`sha256sum` 前后一致：`1c108fe5…55422`）：

```
[selftest] 40 项 · news-curate
[selftest] 全绿 40/40
```

扫描器自身也双向锁（写在断言内的合成样本，不碰真文档）：围栏外的 `全绿 7/7`、`8/8 成功` 必须抓到；
围栏内的 `[selftest] 全绿 9/9` 必须**不**抓 —— 否则 §8 那份 D14 凭据会被逼着改数（伪造凭据）。

## 5. 边界与**没覆盖到的**（别把这条闸当全能）

- ``` 围栏内不检：§8 是字面转录，属凭据。风险：有人把假主张包进围栏就能躲——靠 review，不靠这条闸。
- 沿用 D20 的 `_DOC_NEGATION`（`推翻`/`已作废`/`原写`/`曾经`…）：引用被推翻的旧数字不算声明。
  副作用：一行散文只要含这些词就整体豁免。**已知弱点，与 D20 同型**，不为它单开名单。
- `对比度审计不过：N` / `版式自检通过：0 个文件` 里的 **0 一律放过**：那是 D13 的 bug 症状，不是抄来的规模。
- 不覆盖的形状：`基线 42`、`42 处`、`84 静态文件`、`~210 文件`（规划期估算，不是闸门末行）、
  以及会话任务报告与被 gitignore 的产物域里的日期转录（按定义是历史凭据，`ARCHITECTURE.md` §6 已定这个口径）。
- 本闸只保证"文档不再抄数"，**不保证文档说的状态为真** —— 见下面第 6 条既存矛盾。

## 6. 本轮顺带查出的两件既存问题（未修，归属昨日那批未提交工作）

1. **`audit_pack_contrast.py` exit 1 与 `t_no_pack_has_off_palette_after_repair` 全绿口径不一致**：
   前者按"0 条越界"判，后者按"不许有第四类未解释越界"判（D19 的保留项本就是非零）。
   于是硬性规则 6 那句「三道闸全绿才算过」按字面读**当前不成立**。已在 §4 与 SKILL.md 步骤 1 写明
   "以断言为准"，但**退出码要不要改成 0（或加 `--allow-kept`）是新的设计决定**，本轮不动。
2. **`npm run typecheck` 红**（非本轮引入，mtime 早于本会话）：
   `src/web/lib/hyperframes-bridge.ts:33/91` 与 `tests/web/vue-build.test.ts:65/179/180` 报
   `Cannot find name 'document'/'Element'` —— `tsconfig.json`（10-13 起未改）`lib` 只有 `ES2023`
   且 `include` 带 `tests/**/*`，而 `typecheck:web`（`tsconfig.web.json`）单独跑是过的。
   ⇒ 昨日的 Vue 支把 DOM 代码放进了根工程的编译范围。**影响**：`npm test` 现在整条红，
   所以本轮的验收只敢报「curate 40/40 · test:render 253/253 · structure:audit pass」。
