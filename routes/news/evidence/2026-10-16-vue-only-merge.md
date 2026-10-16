# 地基 Task 4（合并方案落地）· 六类消费者假设改判 + 第一条 `field` 镜真渲染

**日期** 2026-10-16 · **裁决** 用户：「合并方案继续走，工作量更大但 Phase 3 少一步」
（否掉了我提的"Vue-only 角色另立一个 dict"窄方案 —— 保留 `pack["layouts"]` 单一视图，
把消费侧改成 Vue-only-aware。）

## 判据与结果

| 判据 | 结果 |
|---|---|
| `path_b_selftest.py` 全绿 | **239/239**（Task 4 起点是 12 红：6 FAIL + 6 ERROR） |
| `npm test`（vue-build） | exit 0，`field-a` 三条断言在内 |
| `layout_selfcheck` 31 包 | **227 文件 0 违规**（静态支一个字节没动） |
| `audit_pack_contrast` | **24 条 OFF_PALETTE_HEX**，与基线同数、无新文件名 |
| `check_scene_contract --demo` | 5 反例全报 + 1 干净稿不误报 |
| 含 `field` 镜的真渲染 | `check --strict` **0 findings** · 490/490 帧 · **0 WARN/ERROR** · 1.66 MB / 19.6 s |

## 六类消费者假设怎么改的（每条都配了变异证明）

| # | 消费者 | 原假设 | 改判 |
|---|---|---|---|
| 1 | `t_layouts_equivalence_gate_covers_all_217_layouts` | `layouts` 全部来自 HTML，登记表必须逐字段等值 | 等价闸按 `pkl.static_layouts()` 收口，217 这个数字**只属于静态支**；契约支另立一条 `t_vue_only_contract_is_the_registry_for_its_role`（契约 → 合并条目逐字段比），并锁合并数 = 契约条数 × 包数 |
| 2 | `t_auto_layout_stems_are_the_only_vocabulary` | 包交出的版式名 ⊆ 自动词表，否则是"选不到也不报错"的孤儿 | 词表外的名分两种：静态孤儿仍然当场红（原判据没松）；契约角色"只能点名"是设计状态，其"不进自动候选"由同闸的 `named == vocab` 两条断言证完 |
| 3 | `t_every_layout_variable_id_has_a_source` | 变量 id 只有三条来源（DERIVERS / 条目类语法 / 取图） | **发射器本来就有第四条**（`resolve_variable` 的 scene 同名键分支），闸的词表漏了它。补第四桶「作者供料位」= 契约的 `author_slots`，并锁三条拒绝侧：id 必须在契约里、**不许有 default**、机器本来切得出来的不许声明。五桶数 1271/372/424/**62**/0（口径写在断言上方） |
| 4 | 5 条 `t_p3_*` + `t_flagship_compiled_pack_mounts_subtitle_*` | 发射器把每个版式 `copyfile` 进 `compositions/` | Vue-only 的 `path` 是 `None` ⇒ TypeError。拷贝循环跳过契约支（它的产物由 `stage_vue_assets` 落 `work_dir/vue/`） |
| 5 | `t_hf_compile_pack_loads_through_the_real_emitter` | 编译包的家族 == `CANONICAL_LAYOUTS` | `CANONICAL_LAYOUTS` 是**编译产物**的家族定义，按静态口径收口后比；契约角色不是编译出来的 |
| 6 | 我自己写的两条（Task 2 遗留） | — | `t_new_composition_ids_collide_with_nothing` 拿合并视图当对手表 ⇒ 自撞，改成只比静态 id；`t_static_layout_entries_untouched_by_vue_only` 的 before 快照带上了真契约 ⇒ "临时契约的 field ≠ 真契约的 field"被误判成"已有条目被改了"，before 改 `vue_only={}`，并补一条 `t_real_contracts_leave_static_entries_untouched` 用盘上真契约走生产路径 |

顺带把 `pack_layouts.write_layouts` 加了拒绝侧：Vue-only 角色**不许**进 `layouts.toml`
（一张表两个真源 = 把等价闸变成比抄写）。拒绝分支由 `t_layouts_toml_roundtrip_keeps_loader_fields`
里的 try/except 当场证明。

**变异证明**（一次性脚本：把源码改坏 → 只跑点名那条闸 → 断言它必须红 → 从备份还原；
可复现的做法，不留 gitignored 路径当引用）：
M1 verify_pack 不收口 → 两条红 · M2 拷贝不跳过 → 两条 ERROR · M3 write 不拒绝 → 红 ·
M4/M5/M6 author_slots 三条规则各自失效 → 红 · M7 契约键白名单失效 → 红 ·
M8 不投影 author_slots → 红 · M9 静态版式偷声明供料位 → 红 · M10/M11/M12 合并条目
不照契约（变量表 / id / 地面）→ 红。还原后全部复跑 GREEN。

## 第一条 `field` 镜：真渲染出来的两处缺陷

稿件 `.harness-news-runtime/articles/field-probe-scenes.json`（3 镜：hook / **field** / closer）。
发射出的 clip：`data-composition-id="field-news-coral__2"`、`data-vue-bundle="field-a"`、
槽位块 `--c0..--c7` 全来自契约。

首帧（`field-frame-before-contrast-fix.png`）过不了 `check --strict`，两条 contrast finding：

```
warning  '21年'                    1.31:1   （要求 3:1）
warning  '湖南常德 · 救助站门口'    2.43:1
```

- **地点行**是真内容，没有豁免资格：组件里写死了 `rgba(245,240,232,.30)`（实测落在 #0a0a0d 上
  = rgb(81,79,79)）。改成契约槽位 `c6 = #8a8a8a`。
- **12% 水印**是装饰层，按 `frame.md` §壁纸序号**必须带 `data-layout-ignore="true"`**
  （静态支 126 个文件都带，`rail.html` 的 `.rl-wall` 就是同一条规矩）。组件漏了。
  归因做了负例：把 staged bundle 里那一个属性删掉重跑 check ⇒ 恢复报
  `'21年' 1.31`，整片被拒。所以"少了它就红"是实测，不是推测。
- 两条都改完后 `check --strict` 五段（lint/runtime/layout/motion/contrast）全 ok、0 finding，
  渲染 490/490 帧、0 WARN。

组件里两处写死的 rgba 一并收进契约（`c6`/`c7`），`.fd-*` 现在只认 `var(--cNN)`。

## 遗留（进 Task 5，不在本 Task 偷偷修）

`field-frame-after.png` 下沿约 22% 是空黑，条纹地面在 ~62% 高度硬截断。
`check --strict` 的 layout 段看不见它（0 finding），`layout_selfcheck` 的 17 条结构不变量
**根本没扫到它** —— 因为它只吃 `compositions/*.html`。这正是计划里 Task 5
（`t_vue_only_layouts_pass_layout_selfcheck`）要堵的洞：**没有它，新角色等于绕过全部版式闸**。
所以顺序上先落闸、再按闸修填幅，避免"目测改一版"没有判据。
