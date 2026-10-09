# 文件产物分级契约 — 设计稿

- 日期：2026-10-09
- 路径：架构级（改变「证据/产物」在仓库里的存放契约，跨 `core/` `routes/` `skills/` `tests/` 四层）
- 前置：本轮不是新功能，是**还旧账**。三段设计已逐段口头批准，本文是誊本。

## 1. 问题（实测，非推测）

仓库没有「文件产物分级契约」——即**哪一类文件必须进版本管理、哪一类必须不进**，只写在散文里，没有可执行的断言。三条旧账都是这个缺口的直接后果：

| 病灶 | 实测证据 |
|---|---|
| 证据落在被声明忽略的目录里，靠 `git add -f` 人肉抢救 | `.gitignore:24-25,37` 忽略三个 runtime 目录；`git ls-files` 却有 8 个 `.harness-news-runtime/verifications/*.md`——全靠 `git add -f` 进来。`routes/news/ARCHITECTURE.md:193-199` 自己把这称为「已知张力」 |
| 抢救机制已经在静默失败 | `routes/news/ledger.jsonl:45` 的 `fact_check_note` 指向 `.harness-news-runtime/verifications/2026-10-08-t002-fact-check.md`——文件在盘上，**没被 add -f**，于是版本管理里是一个 clone 后不存在的死指针。生产它的规则在 `skills/fact-check/SKILL.md:79` |
| 文档数字无口径、不可证伪、且互相矛盾 | `ARCHITECTURE.md:11` 写 Source files 441，实测 `git ls-files \| wc -l` = **794**（排除 `skills/` 为 96，从未有定义能得出 441）；`:15` 写 Skills 97（46+51），实测 **100**（49+51），而 `skills/INDEX.md:4` 已写 100——同仓两处矛盾；`:13` 写 Platform adapters 5，同文件 `:25` 写「4 thin adapters」 |
|  provenance 清单事实上是错的 | `skills/.skills_store_lock.json`：`version` 字段为空串、`installDir` 指向本机已不存在的路径。它想记录外部来源，但 douyin-pro 已由用户裁定收编为第一方，不再跟踪上游 |
| 「跑产物不进仓库」的口径对 `scripts/` 也在漏 | `routes/news/scripts/fix_decision_table.py`、`fix_stale_doc_claims.py` 在仓库内**零引用**，属 `ARCHITECTURE.md:196` 自称「留在忽略目录，不进仓库」的那一类，却已在版本管理里 |

## 2. 核心概念：五类文件产物

给仓库里每一个文件一个**类别**，每类一条保留规则，规则用测试锁死：

| 类别 | 定义 | 保留规则 | 例 |
|---|---|---|---|
| 工厂自身 | bootstrap 要读/要写的治理资产 | 必须版本管理 | `core/` `platforms/` `routes/*/MEMORY.md` `schemas/` |
| 自产物料 | 管线代码、skill 本体 | 必须版本管理，**跟着它的消费者放** | `skills/douyin-pro/scripts/path_b_build.py` |
| 证据 | 能证伪文档数字/契约的验证单与复算脚本 | 必须版本管理，且**不许住在可忽略目录** | `routes/news/evidence/*.md` |
| 工作态 | 草稿、日志、成片、临时脚本 | 必须**不**版本管理 | `.harness-news-runtime/videos/…` |
| 生成物 | bootstrap 投影产物 | 不手工编辑，可再生 | 根 `MEMORY.md`、`AGENTS.md`、`.qoder/rules/*.md` |

「证据」与「工作态」的分界是本次的全部难点：证据住在**声明忽略**的目录里，就必然时而进来（有人记得 `git add -f`）时而漏掉（`ledger.jsonl:45`）。解法不是要求人更细心，而是**把证据搬出可忽略目录**。

## 3. 第 1 段 · 证据归位（`routes/<route>/evidence/` 约定）

- 新建 `routes/news/evidence/`，作为**可复用的路级约定**（不只 news：任何路都用 `routes/<name>/evidence/`）。
- 迁移对象（判据：**有活指针的**才迁）：
  - `git mv` 现有 8 个已追踪验证单 `.harness-news-runtime/verifications/2026-09-29-*.md` + `2026-10-09-render-speedup-verification.md` → `routes/news/evidence/`；
  - 第 9 个 `2026-10-08-t002-fact-check.md`：盘上未被追踪，`git add` 进 `routes/news/evidence/`（这一步同时修掉死指针）。
  - 盘上另有 6 个零引用验证单（`2026-09-28-*` ×3、`2026-09-29-news-collect`、`2026-09-29-news-v2-audit`、`2026-09-29-news-v2-docs`）**不迁不提交**：按 §4 断言①的定义，没有活指针的记录属一次性跑产，留在忽略目录。若日后有文档要引它，那时它升格为证据，再迁。
- 引用点更新（实测 11 处活指针 + 1 处生产端 + 4 处描述/命令）：
  - **活指针 11**：`routes/news/ARCHITECTURE.md` ×8 — `:170`、`:171`、`:310`、`:319`、`:339`、`:352`、`:366`、`:376`；`routes/news/MEMORY.md:302`；`routes/news/RUNBOOK-first-run.md:90`；`routes/news/ledger.jsonl:45`
  - 生产端 `skills/fact-check/SKILL.md:79`（落盘路径改为 `routes/news/evidence/<date>-<topic_id>-fact-check.md`）
  - 目录图 `routes/news/ARCHITECTURE.md:188`（`verifications/` 那行从 runtime 树里拿掉）+ 口径段 `:196-199`（见 §5）——这 2 处不是指针，是**口径本身**
  - 计划文档 `docs/superpowers/plans/2026-10-09-news-render-speedup.md` ×5 — `:32`、`:628`、`:668`、`:671`、`:687`，含两处**字面 `git add -f` 命令**必须改掉（它们是错误口径的放大器）
- 契约扩展点写进 `core/routing.md`：Runtime dir 列旁增 **Evidence dir** 列（`routes/<name>/evidence/`），让「证据不在 runtime 目录」成为路由表的一部分而不是 news 路的地方传说。

## 4. 第 2 段 · 用断言替代散文（`tests/validate-schemas.ts`）

现有 `tests/validate-schemas.ts`（102 行，`validateSchemas` / `validateSkills` / `validateArchiveSkills`，`[ok] / [FAIL]` + `fail=1` 风格）是天然宿主，不新增测试文件、不新增 npm script（`npm run validate` 已在 `npm test` 链路里）。

**断言①（收窄版）**：受版本管理的文档/台账（`routes/**/*.md`、`routes/**/*.jsonl`、`skills/**/SKILL.md`）里出现的 `routes/<route>/evidence/...` 指针，其目标必须存在且被 git 追踪；**且**受版本管理文件内不得再出现字符串 `.harness-news-runtime/verifications/`（防回潮）。
> 为什么收窄：预跑「所有被引用路径必须存在」的宽版，得到 30+ 条假失败——文档叙述里提到已删除的 tmp 产物是正当写法。断言只锁**证据类的活指针**，不锁叙事。
> 预期：改前 1 红（`ledger.jsonl:45` 死指针）→ 迁完 0 红。

**断言②**：`git ls-files` 结果不得含任何 runtime 目录前缀（`.harness-news-runtime/`、`.harness-novel-runtime/`、`.ai-runtime-artifacts/`）。
> 这是「这个目录不能提交」的**可执行版本**，而不是靠人记 `--ignore`。
> 预期：改前 8 红 → 迁完 0 红。

**断言③**：文档声明的**可枚举**数量必须等于真源（见 §5）。

**跑产物清理**（同批）：`git rm routes/news/scripts/fix_decision_table.py routes/news/scripts/fix_stale_doc_claims.py`（零引用，属 §2「工作态」）；`git rm skills/.skills_store_lock.json`（provenance 事实错误 + douyin-pro 已收编为第一方，不再跟踪上游）。

> ⚠️ 落笔时新测出**第三个**同类：`routes/news/scripts/remap_pack_colors.py` 在仓库内也**零引用**（`git grep -l remap_pack_colors` 除自身目录外空命中）。用户在裁决「删」时我只报了两个名字，这个属同一判据下的漏报，**未获批准**，故不写进 §6 的既定动作，列为评审时必须一并裁定的一项（见 §8-5）。

## 5. 第 3 段 · metrics：能自动核的留，不能的删

- **删**：`ARCHITECTURE.md:11` `Source files | 441` 整行 + `:5` 里 "441 source files (vs 669…)" 的自身计数（保留 "lean replacement" 的定性表述）。理由：**无口径的数字留着就是负债**——无法判断它对错，因为不知道该跟什么比。
- **不写双份**：skills 计数只留 `skills/INDEX.md` 一处（按目录可数）。`ARCHITECTURE.md:15` 的 `Skills` 行改为指向 INDEX，不复制数字；`:27` 的「46 active」同步去掉。
- **留 + 加锁（断言③）**：
  - `Platform adapters` 声明的平台集合 == `schemas/platform.schema.json:6` 的 enum == `scripts/bootstrap.ts:12` 的 `PLATFORMS`；
  - `Routes` 声明集合 == `routes/` 下实际子目录；
  - `Core governance docs` 数字 == `core/*.md` 实测数（现 8，实测**正确**，值得一锁）。
  - 顺带手工订正 `ARCHITECTURE.md:25`「4 thin adapters」→ 5（断言③只锁指标表，这行靠改；两处矛盾正是「人工同步必然漏」的现场证据）。

**证据脚本的家（用户裁定：按被检对象分家）**：`ARCHITECTURE.md:197-199` 现在写「契约证据脚本一律落到 `skills/douyin-pro/scripts/`」——把 skill 名硬编码进 news 路的证据口径。实测那 12 个脚本**就是渲染管线本体**（`path_b_build.py` / `aigc_mode.py` / `check_publishable.py` / `verify_aigc_badge.py` / `path_b_selftest.py`…），它们成为证据是因为它们**就是被检验的东西**，不是寄放。因此不搬文件，只改分界规则：

- 验证**单** → `routes/<route>/evidence/`；
- 证据**脚本**跟着它检验的对象走：检验管线本体的留在 `skills/douyin-pro/scripts/`；检验路文档数字/路契约的进 `routes/news/scripts/`（该目录已存在，现有 10 个脚本，§4 删掉 2 个零引用后剩 8 个，均有仓库内引用）。

## 6. 变更文件清单

| # | 文件 | 动作 |
|---|---|---|
| 1 | `routes/news/evidence/` | 新建；8 个 `git mv` + 1 个 `git add` |
| 2 | `routes/news/ARCHITECTURE.md` | ×8 引用点改写；`:188` 目录图；`:196-199` 口径重写（含证据脚本分家）；删 `git add -f` 那套说法 |
| 3 | `routes/news/MEMORY.md` `:302`、`RUNBOOK-first-run.md` `:90`、`ledger.jsonl` `:45` | 指针改写 |
| 4 | `skills/fact-check/SKILL.md:79` | 生产端落盘路径改写 |
| 5 | `docs/superpowers/plans/2026-10-09-news-render-speedup.md` ×5 | 路径改写 + 删两处字面 `git add -f` 命令 |
| 6 | `core/routing.md:3-7` | Runtime dir 旁增 Evidence dir 列 |
| 7 | `tests/validate-schemas.ts` | 加断言①②③（沿用 `[ok]/[FAIL]` 风格） |
| 8 | `ARCHITECTURE.md`（根） | `:5` `:11` `:15` `:25` `:27` 按 §5 |
| 9 | `routes/news/scripts/fix_decision_table.py`、`fix_stale_doc_claims.py`、`skills/.skills_store_lock.json` | `git rm` |
| 10 | `routes/news/MEMORY.md` Key decisions + `docs/superpowers/specs/` 本文 | 记录本次契约 |

## 7. 非目标

- 不动 `skills/douyin-pro/scripts/` 下任何文件的位置（它们是管线本体，搬走是虚假的整洁）。
- 不引入生成式 INDEX/manifest 系统（`skills/INDEX.md` 维持手写，只加「别处不复制数字」的口径）。
- 不改 `.gitignore` 的 runtime 目录忽略规则（断言②锁的是「别把东西抢救回去」，不是取消忽略）。
- 不处理 `active:archive` 的 skill 1:1 断言降级问题（已单独报告，另一议题）。
- 不动本机 live 配置 `~/.codex/config.toml` / `~/.qoder-cn/settings.json`（仍在 `--ui=true`，超出批准范围，已报告）。

## 8. 风险与取舍

1. **断言①可能过窄**：只锁 evidence 前缀，叙事里的死路径仍会飘过。取舍：宽版实测 30+ 假失败，假失败会让人无视红灯——比漏报更贵。若日后需要，加「例外清单」而不是放宽判据。
2. **迁移会让 git 历史里的旧文档路径失效**：`docs/superpowers/plans/2026-10-09-*.md` 里的旧路径若不改，读者 clone 后按命令跑必失败——所以清单 #5 是硬性的，不是可选润色。
3. **6 个零引用验证单被留在忽略目录**：换机即失。这是 §2「有活指针才算证据」判据的直接代价，选它的理由是：判据可机械检查；「所有验证单都算证据」则会把 runtime 目录变成第二个影子仓库。用户如对这 6 份另有判断，可在评审时推翻。
4. **断言③依赖解析 markdown 表格**：实现比①②脆。缓解：只解析 `ARCHITECTURE.md`「Current state」一张表，不扫全仓。
5. **待裁定（本轮唯一未决项）**：`routes/news/scripts/remap_pack_colors.py` 与已批准删除的两个是同判据同类，但没在裁决时被点名。选项：一并 `git rm`（口径一致），或保留并接受 §4 断言若扩到 `routes/*/scripts/` 时它需一个引用（如给它补一行 ARCHITECTURE 记录）。默认按用户「删」的意图一并处理，**除非评审时另有指示**。

## 9. 验收判据（R4，先定后做）

- `npm run validate` 绿；三条断言各打印 `[ok]` 行。
- 人为破坏各测一次并确认变红且点名不一致两端：
  ① 把 `ledger.jsonl:45` 指回 runtime 路径；
  ② `git add -f` 任意 runtime 文件；
  ③ 把 `ARCHITECTURE.md` 的 Routes 从 3 改 4。
  破坏后全部还原，还原后重跑绿。
- `git ls-files` 不再含任何 runtime 目录路径；`git ls-files routes/news/evidence | wc -l` == 9。
- `npm run typecheck` 绿；`npm test` 全链路绿。
- 全仓 `git grep "harness-news-runtime/verifications"` 只命中历史文档（`docs/superpowers/specs/` 本文与既往 plan 的叙述性回顾），不命中任何**可执行命令**。
