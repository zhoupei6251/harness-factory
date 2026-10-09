# 2026-09-29 · D14 判据放宽：渲染层加中间档 `no-badge`（② 照写、可发布、③ 必带）—— 验证记录（lite）

**范围**：用户 2026-09-29 对上一轮记录 §8 那条「删掉 `path_b_build.py` 里烧角标那段」的无出处请求，
本人选的是另一条路，原话（逐字）：

> **判据放宽：交付件可以不带 ①** … D8/硬规则 7 从「交付件三件齐活」改成「② 元数据 + ③ 发布声明齐活
> 即可发布，① 由开关决定」。交付轨能出无角标但可发布的片子，烧角标的代码留着（--deliver + 姿态 full
> 随时回来）。改的是判据，不是能力。

于是**烧角标的代码一行没删**，改的是判据 + 加一档。落点四处：`aigc_mode.py` 渲染层从两档变三档、
`path_b_build.py` 按档分派并写三种形态的台账、`check_publishable.py` 的判据表与「① 没烧 ⇒ ③ 必带」
代价结算、`routes/news/aigc-mode.json` 的姿态取值。**不含**新的新闻成片（仍用 5 镜 news-policy
版式探针，探针文案占位，`请勿发布`）。

结论：**三档都在真产物上验过 —— 默认落 `no-badge`（可发布、② 在、① 点名关掉），`--deliver` 角标三项
几何全过，`--draft` 依旧被闸门拒；闸门对 `no-badge` 台账遇 `undeclared` / `--allow-undeclared`
EXIT=1 并打三条出路；`--deliver` + `--no-badge` 这类两两互斥与坏姿态值一律停机不猜。**
三道闸 **73/73 + 12 pack 0 警告 + 12 文件 0 违规** 全绿。

---

## 1. 被验对象

```
skills/douyin-pro/scripts/aigc_mode.py        RENDER_MODES = ("full","no-badge","draft")；
                                              resolve_render 三旗标只能挑一个（两个同时给 = ModeError）；
                                              RENDER_WHAT 一档一句话，日志与台账都从这里取话
skills/douyin-pro/scripts/path_b_build.py     +`--no-badge`；mux_and_burn 接 render/render_cause，
                                              burn_badge = (render=="full")、write_meta = (render!="draft")，
                                              未知档即停机；侧车三种形态（full 记几何 / no-badge 记
                                              disabled_by+to_enable / draft 只记 draft 段）
skills/douyin-pro/scripts/check_publishable.py 判据表按 D14 改：② 永远不许缺、① 要么 burned_in:true
                                              要么 false+disabled_by；+badge_burned() / requires_declaration()；
                                              ① 没烧而 decl 关了 → EXIT=1 + 三条出路（不静默改用户姿态）
skills/douyin-pro/scripts/path_b_selftest.py 72 → 73 项（+1：t_no_badge_is_publishable_but_demands_declaration；
                                              另改 t_publish_gate_refuses_draft_and_missing_sidecar 的 ① 段断言、
                                              t_aigc_mode_* 三处随三档更新）
routes/news/aigc-mode.json                    draft·undeclared → **no-badge·required**（含 since/by/revert/note）
routes/news/ARCHITECTURE.md                   新增 D14 行；D8/D11/D12 各加末句订正；§2 流程两行、
                                              §3 树四行、§7 硬规则 7 重写、§8 真转录（三档渲染 + 四种闸门调用）、
                                              集成状态加 D14 条目并对 D12 那条警告下订正
routes/news/MEMORY.md                         渲染层状态行、标识开关两条、发布前一条、in_progress.note
skills/news-workflow/SKILL.md                 步骤 4 合成行与「哪条轨」重写、步骤 5 门禁与命令注释、硬规则 7 重写
skills/douyin-upload/SKILL.md                 三件套表头与 ① 列、姿态取值、草稿/无侧车两条
```

姿态文件全文（`git diff routes/news/aigc-mode.json` 即可看到"是谁关的、关的是哪一件、怎么回退"）：

```json
{
  "render": "no-badge",
  "declaration": "required",
  "since": "2026-09-29",
  "by": "用户 2026-09-29 点头放宽判据（ARCHITECTURE D14：「判据放宽：交付件可以不带 ①」）。先前姿态是 render=draft · declaration=undeclared",
  "revert": "要 ① 回到画面上：把 render 改回 full（或渲染时加 --deliver）；要整个恢复代码默认：删掉本文件（代码默认是 full · required）",
  "note": "这是 D14 新增的中间档：① 画面角标不烧，② 隐式元数据照写并读回，于是产物**可发布**（旧行为下「不要角标」只能得到不可发布的草稿）。代价由发布闸门结算：① 没烧 ⇒ ③ 平台自主声明必带 —— check_publishable.py 对这类台账拒绝 declaration=undeclared 也拒绝 --allow-undeclared（EXIT=1），所以本文件的 declaration 不再是 undeclared。判据没被姿态改掉：draft 依旧不可发布，② 依旧不许缺，台账里 ① 必须写明是谁关的（disabled_by）。"
}
```

**为什么这一档必须存在**：旧的两档里"不要角标"只能选 `draft`，而 draft 连 ② 一起砍 → 产物发不出去。
用户要的那个中间态（无角标但仍可交付）在代码里根本不存在，所以加档而不是删码。
**为什么 `declaration` 跟着从 `undeclared` 回到 `required`**：① 没烧时画面上一件标识都没有，
② 过抖音转码即失，③ 是平台侧唯一活下来的那一件 —— 关 ① 买不到"什么都不用说"。
这条不是顺手替用户多开一个开关，而是他所选方案的既有条件，且闸门用的是**停机 + 三条出路**，
不是静默把 `undeclared` 当 `required` 用（R6）。

---

## 2. 三档真渲染（同一条 5 镜探针、同一台机器、Node v23.11.1）

命令（`--check-only` 之后那三步各跑一次；日志全文留 `.harness-news-runtime/tmp/d14/`）：

```bash
export PATH="/d/Users/zhoupei/AppData/Local/nvm/v23.11.1:$PATH"   # hyperframes 要 Node ≥ 22
# A 不加旗标 → 落姿态文件 no-badge
python skills/douyin-pro/scripts/path_b_build.py --input skills/douyin-pro/scripts/fixtures/badge_probe_shots.json \
  --template news-policy --voice XiaoxiaoNeural --output-dir .harness-news-runtime/tmp/d14-nobadge --y
# B  --deliver      C  --draft   （同上，换旗标与输出目录）
```

三档的裁决行（逐字取自日志）：

```
A [path_b] [aigc] 姿态文件 …\routes\news\aigc-mode.json: render=no-badge · declaration=required
  [path_b] [aigc] 渲染层开关 → no-badge(…\aigc-mode.json render=no-badge) → 交付轨(按 D14 不烧 ①): ② 元数据照写 —— 可发布, 但发布必须带 ③
  [path_b] ⚠️ 未烧 ① 角标[no-badge(…)]: ② 元数据照写并读回 —— 这份**可发布**, 代价是发布必须带 ③ 自主声明(check_publishable.py 会拒绝 undeclared)
  [path_b]   AIGC 隐式标识已核验: ProduceID=97c20ceba5b61b72ae7ed5a4d7fd415a Label=1 ContentProducer=harness-news-pathb
B [path_b] [aigc] 渲染层开关 → full(旗标 --deliver) → 交付轨: 烧 ① 角标 + 写 ② 元数据
  [path_b]   AIGC 隐式标识已核验: ProduceID=ad6783cfe5023f80be40df2351698bfa Label=1 ContentProducer=harness-news-pathb
C [path_b] [aigc] 渲染层开关 → draft(旗标 --draft) → 草稿轨: ①② 都不做, 这份产物不可发布
  [path_b] ⚠️ 草稿模式[draft(旗标 --draft)]: 角标没烧、元数据没写 —— 台账会标成草稿, 发布那一步(check_publishable.py)读到即拒绝
```

三次 EXIT 都是 0（渲染本身成功；差别只在标识），产物大小 1,633,313 / 1,639,723 / 1,634,044 B。

## 3. 台账三种形态（「缺什么记什么缺」vs「关了什么记什么关」）

```jsonc
// A no-badge —— explicit 段**必须存在**并点名是谁关的、怎么开回来
{"file":"final.mp4","switch":"no-badge(…\\aigc-mode.json render=no-badge)","metadata_key":"AIGC",
 "implicit":{"AIGC":{"Label":"1","ContentProducer":"harness-news-pathb",
   "ProduceID":"97c20ceba5b61b72ae7ed5a4d7fd415a","ReservedCode1":"cdd349fc47be485fb645352c0e05b5f726d729b0", …}},
 "explicit":{"burned_in":false,
   "disabled_by":"no-badge(…\\aigc-mode.json render=no-badge)",
   "to_enable":"把 routes/news/aigc-mode.json 的 render 改回 full(或渲染时加 --deliver)再重渲一次, 让 ① 落进成片"},
 "resolution":"1080x1920"}
// B full —— 记几何（与旧交付轨逐字同形，能力没被这次改动削过）
//   "explicit":{"font_size_px":75,"glyph_height_px":54.7,"short_side_px":1080,
//               "margin_v_px":303,"shown_seconds":4.0,"burned_in":true, …}
// C draft —— 只留 draft 段，不写一堆 false 装作"标识在只是没开"
```

## 4. 发布闸门的四种调用（判据与代价都在这里结算）

| 调用 | 期望并实得 |
|---|---|
| `check_publishable.py <no-badge>/final.mp4` | **EXIT=0** `✅ 可发布(按 D14: ② 在、① 点名关掉)` + `① 未烧 —— 出处 no-badge(…)` + `② 元数据键 AIGC · Label=1` + `③ 必须带: --declaration 内容由AI生成` |
| 同上 `--allow-undeclared` | **EXIT=1** `❌ 这份 final.mp4 不许不带 ③ —— ① 没烧…开关取值 undeclared(旗标 --allow-undeclared) 在这一档不适用。` + 三条出路 |
| 同上 `--require-declaration` | **EXIT=0**，`开关取值: required(旗标 --require-declaration)` |
| `check_publishable.py <deliver>/final.mp4` | **EXIT=0** `✅ ①② 齐活` + `① 角标 AI 生成合成内容 · bottom-left · 字芯 54.7px / 最短边 1080px · 4.0s` |
| `check_publishable.py <draft>/final.mp4` | **EXIT=1** `· 草稿渲染[draft(旗标 --draft)]: ① 画面角标与 ② 隐式元数据都没有 —— 不得发布: 去掉 --draft 重渲一次, 让 ①② 落进成片` |

被闸门拒绝的两种"① 没交代"（负例由自测锁，不是这里的手写台账）：`explicit` 段整个缺失 →
`① 段缺失(sidecar 没有 explicit) —— 台账不完整(旧产物或手改), 重渲`；只有 `burned_in: false`
而没有 `disabled_by` → `① 显式角标没烧且没交代 … 按 D14 要么烧, 要么点名关掉, 重渲`。

## 5. 元数据与像素的交叉核验

```bash
ffprobe -v error -show_entries format_tags -of default=noprint_wrappers=1 .harness-news-runtime/tmp/d14-nobadge/final.mp4 | grep -i aigc
# TAG:AIGC={"AIGC":{"Label":"1","ContentProducer":"harness-news-pathb","ProduceID":"97c20ceba5b61b72ae7ed5a4d7fd415a",…}}
ffprobe … .harness-news-runtime/tmp/d14-draft/final.mp4 | grep -ci aigc
# 0     ← 草稿连 ② 都没有，与 no-badge「② 在、① 没烧」从此在文件层可分辨
```

`verify_aigc_badge.py` 是 **full 档**的复测器，它对 no-badge 的红是**正确行为**（不是回归）：

```
$ … --work .harness-news-runtime/tmp/d14-deliver/work --video …/d14-deliver/final.mp4      # EXIT=0
[aigc_badge] ASS: 字号 75 描边 5 阴影 1 对齐 1(1=左下) MarginL 48 MarginV 303 窗口 0.00–4.00s
[1 字芯] 白色像素 x 49–465=417px · y 1555–1609=55px → 最短边 1080 的 5.09% | 5% 线 54.0px
[2 几何] 实测墨迹 y 1549–1615 vs 模型 ink_bounds(mv=303) 1549.3–1615.0（上 0.3px / 下 0.0px）
[3 时序] 窗口内 76.6% · t=4.20s 起 0.0% · t=42.81s 0.0%
[aigc_badge] ✓ 三项全过: 字芯 55px(5.09% ≥ 5%) · 墨迹与模型逐侧 ≤1.5px · 角标只在开场 4.0s 出现
$ … --work .harness-news-runtime/tmp/d14-nobadge/work --video …/d14-nobadge/final.mp4     # EXIT=1
[aigc_badge] 成片 ASS 里没有 AIGC 事件 —— 显式标识根本没烧, 不必再量像素
```

几何数字与 D8 那条（左下角 / 擦边字号 / 开场 4 秒）逐字一致 → **本次改动没动 full 档的任何像素判据**。

## 6. 三道闸

```
$ python skills/douyin-pro/scripts/path_b_selftest.py
[selftest] 73 项 · style=news-coral … [selftest] 全绿 73/73          # 末行含新断言
      姿态文件 D:\work\…\routes\news\aigc-mode.json: render=no-badge · declaration=required
$ python skills/douyin-pro/scripts/audit_pack_contrast.py
对比度审计通过：12 个 pack 的 frame.md 色板与文档一致（0 条警告）
$ python skills/douyin-pro/scripts/layout_selfcheck.py \
    skills/douyin-pro/templates/hyperframes_path_b/news-coral \
    skills/douyin-pro/templates/hyperframes_path_b/news-policy
版式自检通过：12 个文件，0 条违规
```

新断言 `t_no_badge_is_publishable_but_demands_declaration` 锁的是：判据表（no-badge `check()==[]`、
没交代的 `false` 非空、缺 `explicit` 非空）、`badge_burned()` / `requires_declaration()` 两端、
`RENDER_MODES` / `RENDER_WHAT` 键集一致、旗标→档与反向覆盖（姿态 no-badge 遇 `--deliver` 回 full）、
三旗标两两互斥的报错串、以及源码里 `--no-badge` / `render=render_mode` / `disabled_by`+`to_enable` /
`main()` 里 `requires_declaration` 四处字面。`t_publish_gate_refuses_draft_and_missing_sidecar`
同步改了 ① 段断言（旧断言把 `{"burned_in": false}` 当违规，现在违规的是"false 又没 disabled_by"）。
**项数只在本记录与 §8 真转录里出现，别处不抄**（加断言必然让抄进文档的数过期）。

## 7. 与相邻文档的一致性检查

`grep -rln "render=draft\|--allow-undeclared\|declaration=undeclared\|草稿轨\|--deliver"` 命中的
五个活文档（`aigc-mode.json` / ARCHITECTURE / MEMORY / news-workflow / douyin-upload）全部改到位；
`skills/douyin-pro/SKILL.md` 不含这些字样，无需改。旧口径三处已订正而非另起一套：
ARCHITECTURE §7 硬规则 7 标题、集成状态里 D12 那条「默认渲染不可发布」的 ⚠️、
MEMORY `in_progress.note` 里「本 note 与姿态冲突」那句（现在二者一致，note 重新有效）。

## 8. 未做的事（明确留着，不是遗漏）

1. **没删烧角标的代码，也没把它抽成独立模块**。用户点头的是判据不是能力，`--deliver` + `render=full`
   随时能回到带角标成片（本次 §5 就是证据）。
2. **没让闸门在 ① 没烧时静默把 `undeclared` 当 `required` 用**。选的是 EXIT=1 + 三条出路：
   替用户改姿态是最难查的那种"闸门自己拿主意"。
3. **没给 `no-badge` 加"这次想烧 ①"的第三条旗标**。已有 `--deliver` 覆盖这个方向，再加一个入口 = 两个入口打架。
4. **没重渲历史成片**（v001–v004 的台账不动）。旧交付件带 ①②，按新判据照样可发布；
   `videos[].aigc_label` 那几行的 `none` 说的是"当时没这能力"，不是违规。
5. **没有 push**（本仓库规矩：push 要先问）。本轮两个 commit 与本次改动都只在本地 `main`。

## 9. 产物位置（`.harness-news-runtime/` 被 gitignore，本记录是它们的证据）

```
.harness-news-runtime/tmp/d14-nobadge/   final.mp4 1,633,313B（② 在、无 ①）+ aigc.json + contact-sheet.jpg + work/
.harness-news-runtime/tmp/d14-deliver/   final.mp4 1,639,723B（①② 齐活）+ aigc.json + contact-sheet.jpg + work/
.harness-news-runtime/tmp/d14-draft/     final.mp4 1,634,044B（无 AIGC 键）+ aigc.json + contact-sheet.jpg + work/
.harness-news-runtime/tmp/d14/           render-{nobadge,deliver,draft}.log / selftest.log / verify-{deliver,nobadge}.log
```

探针片无发布价值（文案占位、`请勿发布`），`final.mp4` 与 `work/` 可在 commit 后删除，日志与本记录留档。
