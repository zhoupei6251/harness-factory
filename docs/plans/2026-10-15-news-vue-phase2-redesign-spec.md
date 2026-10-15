# 新闻域 Phase 2 = redesign · 规格说明书

> 日期：2026-10-15 · 路线：`news` · 状态：**待用户复核**
> 承接：`docs/plans/2026-10-13-news-static-pack-retire-vue-migration-spec.md`（迁移总纲）
> 与 `docs/plans/2026-10-14-news-vue-phase1-plan.md`（Phase 1，hook 已闭环）
> 用户裁决（2026-10-15）：**「Phase 2 即 redesign」** —— 其余 6 个角色不再按原计划做像素保真搬迁，
> 而是直接在 Vue 支重写到"好看"，并重定判据。

---

## 0. 为什么要改判

Phase 1 的 Global Constraints 有一条用户 2026-10-14 拍的「**1:1 保真：本 Phase 不改变任何包的视觉**」，
Phase 2 原样继承它，判据是 `routes/news/scripts/vue_pixel_ab.py`（静态支 vs Vue 支同 seek 比 PSNR）。

redesign 与这条判据**逻辑互斥**：`vue_pixel_ab` 测的就是"和旧版一样"，改版式必然判红。
不先换判据就开工，结果会是同一份代码同时"通过"和"不通过"。⇒ 本 spec 的第一件事是换判据（§2）。

## 1. 范围：先把工作量说准

`t_slots_reconstruct_every_pack_byte_exact`（Phase 1 Task 1）机检证明：
**同一角色的 31 份静态文件，跨包差异只有「有序 hex 列表 + composition_id」，其余逐字节相同。**

⇒ 今天系统里真实存在的设计不是 217 个，而是 **7 个版式 ×（主流簇 + news-policy 变体簇）= 14 个组件**，
外加 31 套配色（配色成立性已由 `audit_pack_contrast.py` 复算，24 条 OFF_PALETTE_HEX 是刻意保留基线）。

- **在范围内**：14 个 Vue 组件的设计质量；图板下沉到组件；3 条契约增补；判据替换。
- **不在范围内**：给不同题材做不同**结构**（榜单片/数据片骨架不同）——那是另一个量级，需另立 spec。
  本 spec 完成后，31 个 pack 的差异**仍然只有配色**，这一点不假装。
- **不碰**：`hf_compile.py` / `path_c` / `spec.toml`（迁移总纲 §1-4 仍然有效）。

## 2. 判据改判（正式记录）

| 判据 | 处置 | 口径 |
|---|---|---|
| `vue_pixel_ab.py` 像素零漂移 | **对 Phase 2 的 6 个新角色退役**；hook 保留（它已按此判据闭环，留着防后续回归） | 新角色没有"旧版"要复刻，基线无从谈起 |
| 结构一致（槽位 + 路由） | 保留并加强 | `t_hook_vue_route_registered_for_every_pack` 的形状逐角色复制：31 包 × 该角色全部有 bundle |
| 对比度 AA | 保留 | `audit_pack_contrast.py` 复算，违规数不得超过 24 条基线，且**不得出现新文件名** |
| **断点/孤字闸（新）** | 新增机检 | 见 §3-C |
| **装饰层纯度闸（新）** | 新增机检 | 见 §3-A |
| **目视 compare 表** | 新增，且**明确不假装能机检** | 每角色一张 `hyperframes compare`（旧 pack × 新设计 或 before/after），用户点头才算过 |

## 3. 设计契约增补三条（全部来自 2026-10-15 实测帧）

### A. 装饰层不许吃通用文字阴影 —— 这是实现违反自己的契约

`frame.md` §2 字阶明写壁纸序号 = **`22–52cqw`，12% ink + `data-layout-ignore`**。
而 v007 为兜 WCAG AA 加的通用规则把它打回实黑：

```css
#root > *:not([class$="-photo"]):not([class$="-photo-credit"]) {
  text-shadow: 0 1px 3px rgba(0,0,0,.7), 0 0 1px rgba(0,0,0,.5);
}
```

实测：story 的「02」CSS 写 `rgba(26,26,26,0.12)`，渲染帧该区域**最暗像素 (27,25,24)**（≈实黑），
两层阴影叠加所致。命中面量过：含该通用规则的 composition **212 份** + `hook-a` 组件 1 份，
其中真正带装饰件（`data-layout-ignore`）的文件 **126 份**。

- **修法**：该选择器加 `:not([data-layout-ignore])`，212 + 1 全改（不只改那 126 份 ——
  规则本身是"给所有 root 子元素兜底"，留着不改，将来新加的装饰件会再次中招）。
  文字元素（真正需要阴影兜 AA 的）一个不动。
- **机检两条，一条静态一条真判**：
  - 静态 `t_decorative_layers_excluded_from_text_shadow`：任何含 `data-layout-ignore` 的文件，
    其通用 `text-shadow` 选择器必须出现 `:not([data-layout-ignore])`；缺即点名文件。反向负例：
    临时去掉一个文件的该 `:not()`，断言必须变红。
  - 像素 `t_watermark_renders_at_declared_alpha`（真判据）：固定 fixture 渲 story 一镜，
    `hyperframes snapshot` 取帧，量序号区域最暗像素。声明 `rgba(26,26,26,.12)` 叠在
    cream(233) 上应得 ≈208 ⇒ 断言**最暗 ≥ 190**（容差 18）。修前实测 27，必红 —— 这条
    比静态检查强，因为它测的是"最终合成出来的像素"，而不是"我假设 CSS 会怎么生效"。

### B. 图板归组件，且无图不许留任何许可指向

已落地一半：212 份静态版式补 `display:none` + `hasPhoto` 点亮；`hook-a` 补 `v-if="hasPhoto"`
（**我第一轮只扫了 `templates/`，漏了 Vue 支**，被用户「不是都用 vue 了吗」问出来）。
断言 `t_imageless_shots_never_show_photo_credit` 现覆盖两支，并验证过 HEAD 版 hook-a 会被判红。

Phase 2 要求：**6 个新组件每个自带图板**（用户 10-14 已拍「图板由 Vue 支承接」），
且接 P3 grade 机制 —— 非现场真图必须走 `schematic` 三轨免责标注，不许以"真实照片"身份上屏。
Commons 里不存在"宁波这套房"，通用图一律是**示意**。

### C. 屏上文字必须有断点，不许出现孤字

根因实测：`fitCqw()` 只按行数缩字号，`perLine = floor(BOX_CQW / base) = floor(88/8.6) = 10`；
11 字领句 → 2 行 ≤ 3 行上限 → **字号不动** → 浏览器贪婪折行切出「六月报平安，九月成废 / 墟」。
CJK 可任意位置断行，而 `HEAD_BREAK_CHARS`（`，、｜`）这套作者标记早就存在，只是 fit 逻辑不看它。

- **修法**：fit 与换行都按**断点分段**算——每段必须 ≤ 一行容量，放不下就缩字号或换版式，
  绝不让浏览器决定在哪断。
- **机检**（`t_no_orphan_line_break`）：对每个角色用边界稿（每段恰好 1 字、总长恰好容量+1）
  渲染 snapshot，逐行扫描墨迹，**任一行可见字符数 < 2 即判红**；同时断言断点字符不残留在屏上。
- 顺带更正我自己的误判：我曾把「story 中间大片留白」列为契约缺口。实测该版式内容**居中**、
  上下各余 12.2cqh 是文件头写明的设计。**留白不是缺陷**，真正的破坏者只有 A 和 C。

## 4. 架构

```
组件（14 个，Vue SFC，src/web/entries/<role>-<a|b>/）
  ├─ 只读 var(--cNN) 有序色位槽（发射器按包注入，Phase 1 已闭环）
  ├─ 自带图板 + grade 通道（B）
  ├─ 断点感知的 fit 逻辑（C）
  └─ 装饰层与文字层分离，阴影只归文字（A）
        ↑
  vue_bundle_for(pack, role) → f"{role}-{variant_of(pack, role)}"（Phase 1 Task 4）
        ↑
  CUTOVER_ROLES: {"hook"} → 逐角色扩到 7 个（每过一个角色的 §2 全套判据就登记一个）
```

静态支在 Phase 2 期间**继续服务未 cutover 的角色**（今天的 story/closer 就是它渲的），
A、C 两条修复**两支都要**——静态支还要活到 Phase 3，不能把丑留在将死分支里。

## 5. 切片与验收

| 片 | 内容 | 通过判据（Expected 先写死后执行） |
|---|---|---|
| **P2-0** | 契约三修：A 阴影选择器一行 × (212 静态 + 1 Vue)、C fit 断点、三条新机检（A 静态 + A 像素 + C 孤字） | 每条新闸各带反向负例（证明它会红，不是只会绿）；`path_b_selftest` 全绿；`layout_selfcheck` 0 违规；`audit_pack_contrast` 仍 24 条且无新文件名；story 序号区域最暗像素从 27 升到 ≥190 |
| **P2-1** | 基座：图板 + grade 通道抽成可复用件（含 schematic 三轨标注） | 用一条带图 fixture 渲真帧，标注出现在非真图镜、不出现在无图镜 |
| **P2-2…P2-7** | 6 个角色 × 2 簇 = 12 个组件，按 `story → stat → rail → quote → catalog → closer` 顺序（story 最难先看设计天花板） | 每角色：31 包路由全绿 + 对比度复算 + 孤字闸 + **一张 compare 表交用户目视**；目视未过不算完 |
| **P2-8** | BGM bed（产线目前**完全没有**：`path_b_build` grep 不到 music/sfx） | 音量与人声的 ducking 有实测数；关掉 BGM 的开关默认态明确 |
| **P2-9** | 收尾：`CUTOVER_ROLES` 满 7 → 交 Phase 3（删 217 静态文件） | 普查脚本改跑 Vue 支且零 WARN |

每片结束回填 `routes/news/MEMORY.md`，证据落 `routes/news/evidence/`。

## 6. 风险与未决

1. **「好看」的天花板不在代码里**：14 个组件重写完，如果只用 31 套配色，题材间的视觉差异仍然有限。
   要不要给不同题材不同结构（§1 明确排除项），需要一次单独的 brainstorm。
2. **目视判据不可约**：§2 最后一行是人工的。我不提议给它编分数——那会造出一个
   "真片与假片分布重叠"的指标，按既有规矩那种指标该删不该设阈值。
3. **BGM 的授权与成本**：`media-use` 的 resolve 路径要落盘冻结文件，零云费口径是否覆盖音乐许可未证。
4. **发布仍卡两把锁**（既有）：抖音账号未登录；`--aigc-producer` 仍是默认值 `harness-news-pathb`，
   真要发得先定主体名重渲。redesign 不解决这两条。
5. **本轮未提交**：212 静态文件 + hook-a + 两条断言（全闸绿）与 P2-0 会落在同一批模板文件上，
   建议先 commit 再开 P2-0，否则 diff 混在一起没法审。
