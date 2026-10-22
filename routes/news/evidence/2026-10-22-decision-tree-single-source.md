# 2026-10-22 · 计划二：模板决策树收口成一份（D27）

> 一句话：入口文件 `skills/news-workflow/SKILL.md` 里藏着第二张「形态 → pack」表，只覆盖 12 个
> master；`routes/news/MEMORY.md` 那份被 D20 强制列全 31 行。选包时人第一眼看的是入口，
> 于是另外 19 个派生变体/主题包在文档层面就是"选不到"。本次删表、留指针、上闸。

## 1. 病灶实测（改动前）

对 HEAD 版 SKILL.md 跑新写的扫描器（不碰工作树，用 `git show` 取旧文本）：

```
HEAD 版表行命中: 12 ['news-alert', 'news-blast', 'news-bulletin', 'news-coral', 'news-explainer',
                    'news-ink', 'news-onsite', 'news-policy', 'news-stat', 'news-takes',
                    'news-thread', 'news-world']
HEAD 版缺指针: ['decide_pack.py']
现版表行命中: []
现版缺指针: []
```

缺口由真实模板集合现算，不抄：

```
$ python routes/news/scripts/decide_pack.py --list | head -3
============================================================
31 pack 分类表 (按主气质)
============================================================

$ python -c "len(cu.ALL_TEMPLATE_NAMES) - 12"
真实 pack 数 = 31 | 旧入口表覆盖 12 | 缺口 = 19
```

两张表的分工是**假对称**：入口那张列的是 12 个 master（视觉正交轴），MEMORY 那张列的是
全部可选 pack（master + 派生变体 + 主题包，含 主/备 与触发词）。人只看入口时，
`news-dusk` / `news-noir` / `news-polarity` / `news-dawn` / `news-coral-mono` 这一类
根本不会进入候选 —— 而 D23 恰恰是拿"零独有色的变体"当可牺牲位来删包的，
说明变体包是设计里有位置的角色，不是边角料。

顺带证实"第二张表必然过期"：D23 删 `news-coral-night` 时只重写了 MEMORY 的树，
入口表当时没人动 —— 因为它没有断言，红不了，也就没人被提醒。

## 2. 改动

| 文件 | 改了什么 |
|---|---|
| `skills/news-workflow/SKILL.md` | 步骤 1 的 12 行表**整段删除**，换成指针（MEMORY 树 + `decide_pack.py "<关键词>"` / `--list` + `pack-decision.md`）；保留 `news-coral` 作为默认包那一条（散文点名，非表行）；表头 `（12 节目包）`→`（选 pack）`；`X/12` → `X/Y` 并写明分母也现算；第 9 步 `读 12 pack 之一`→`读步骤 1 选中的 pack`；硬规则 6 `12 pack 自检先行`→`新 pack 自检先行`；v1/v2 对照表 `12 pack 决策树`→`pack 决策树（唯一一份在 MEMORY）`；顶部 `12 个节目包覆盖视觉形态`→`视觉形态由决策树选出的 pack 决定`；`31/31 全部有真版式：12 master + 19 派生变体`→现算口径 |
| `skills/news-curate/scripts/curate_selftest.py` | 新增 `_WORKFLOW_SKILL` / `_TREE_POINTERS` / `_pack_names_in_table_rows()` + `t_workflow_skill_does_not_own_a_template_tree`（负向拦表、正向锁指针，另含两条扫描器自检探针） |
| `skills/douyin-pro/scripts/path_b_build.py` | `:134` 注释与 `:3844` 的 `--help` 不再把读者指向 SKILL.md 的树，改指 `routes/news/MEMORY.md` + `decide_pack.py` |
| `routes/news/ARCHITECTURE.md` | §4 加"本表是 master 轴，不是选包全集（D27）"标注；§5 加 D27 决策行 |
| `routes/news/MEMORY.md` | `# 32 个 pack 之一` / `<12 选 1, 见上方决策树` 两处陈旧注释改为"决策树选出的 pack"（都在 ``` 围栏内，D26 的闸按设计不追围栏内文本，只能手改） |

## 3. 闸的判据与双向锁

`t_workflow_skill_does_not_own_a_template_tree()` 四条：

1. **负向**：SKILL.md 里凡以 `|` 开头的行（markdown 表格行）命中 `cu.ALL_TEMPLATE_NAMES`
   中任何一个真实 pack 名即红。名单从 `path_b_build.ALL_TEMPLATES` 现算，**没有豁免名单**。
   副作用（好的那种）：`news-collect` / `news-curate` / 已退役的 `news-polish` 这些**技能名**
   不是 pack，不会被误伤 —— 这正是"按 `news-` 前缀扫"会翻车的地方，所以按名单匹配而不是按前缀。
2. **正向**：`routes/news/MEMORY.md` 与 `decide_pack.py` 两个指针必须在文件里。
   只删表不留路 = 把决策树删了，闸门同样红。
3. **扫描器自检（必抓）**：合成一行 `| 故事 | \`<真实 pack>\` |` 必须被 `_pack_names_in_table_rows` 抓到。
4. **扫描器自检（必不抓）**：`- 都不命中用 \`news-coral\`（DEFAULT）` 这行散文不许命中 ——
   否则默认包那条也得进豁免名单，而一开名单这条闸就又变成装饰（D20 的翻车记录）。

红→绿凭据即 §1 那段 `git show HEAD:` 对照：同一把尺子在旧文本上报 12 命中 + 缺 `decide_pack.py`，
在新文本上报 0 命中 + 指针齐。

## 4. 全量闸门（本次真跑输出）

```
$ python skills/news-curate/scripts/curate_selftest.py
  ok    t_workflow_skill_does_not_own_a_template_tree
[selftest] 全绿 41/41

$ python skills/douyin-pro/scripts/path_b_selftest.py
[selftest] 全绿 253/253
$ npm run validate
All validations passed.

$ npm run structure:audit
Structure audit passed.
```

项数以脚本末行为准，**不要抄进别的文档**（D26）。

## 5. 边界：这条闸不管什么

- **不管 MEMORY 的树** —— 它是唯一事实源，由 `t_memory_decision_table_lists_every_template` 锁"列全"。
- **不管 `pack-decision.md` 的分类表** —— 它回答"关键词怎么归类 + 长度→镜数"，是 `decide_pack.py`
  的文档镜像，集合一致性已由 `t_decide_pack_covers_every_real_template` 锁。
- **不管 ARCHITECTURE §4 的 master 表** —— 它讲派生轴（谁是父、什么气质），本次只加标注、不删内容。
  三份表硬合成一份，只会做出一个没人敢改的巨型文件；收口的是"**选包**这件事只有一处入口"，不是"全库只剩一张表"。
- **不拦散文点名 pack**：`news-coral` 作为 `DEFAULT_TEMPLATE` 必须出现在步骤 1 与步骤 4，探针 ④ 专门保护它。
- **不做的事**：没有给 SKILL.md 生成一张 31 行的新表（那只是把重复换成更大的重复），
  也没有新增脚本/依赖/文件，只删了一张表和一段注释。

## 6. 遗留（不属本计划）

- `audit_pack_contrast.py` 的 `exit 1` 与 `t_no_pack_has_off_palette_after_repair` 全绿**口径不一致**，
  硬规则 6「三道闸必绿」字面上今天不可满足 —— 已在 §4/步骤 1 写明"以断言为准"，
  但要不要把脚本改成按"第四类未解释越界"退出，仍是待拍的决定。
- 根 `npm run typecheck` 因昨日未提交的 web 文件（`src/web/lib/hyperframes-bridge.ts`、
  `tests/web/vue-build.test.ts` 用了 DOM 全局，而 `tsconfig.json` 的 `lib` 只有 `ES2023`）为红，
  `typecheck:web` 单独跑是绿的。整条 `npm test` 因此仍不可信，属另一件事。
