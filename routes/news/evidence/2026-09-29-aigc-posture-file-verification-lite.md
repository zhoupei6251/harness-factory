# 2026-09-29 · AIGC 两开关的"现在想关"落进**姿态文件**（`routes/news/aigc-mode.json` + `aigc_mode.py`）—— 验证记录（lite）

**范围**：用户同日第三次改口径 ——「先帮我把两开关先关了吧」。不改代码默认值（那是 D11 明令禁止的：
合规默认不许由一次会话的偏好改动），而是加**第三层**：裁决顺序 **旗标 > 姿态文件 > 代码默认（full / required）**，
并把当前姿态写成一份受版本管理的文件。两开关从此都是**关着的**：`render=draft`、`declaration=undeclared`。
**不含**新的新闻成片（仍用 5 镜 news-policy 版式探针，探针文案占位，`请勿发布`）。

结论：**默认那一次渲染落地就是草稿（姿态文件是出处），加 `--deliver` 那一次角标与元数据都在真产物里；
闸门对草稿 EXIT=1、对交付件 EXIT=0 但按姿态打 ③ 警告；矛盾旗标与坏值一律停机。**
三道闸 **71/71 + 12 pack 0 警告 + 12 文件 0 违规** 全绿。

---

## 1. 被验对象

```
routes/news/aigc-mode.json                   ★ 新增：当前姿态（render/declaration + since/by/revert/note）
skills/douyin-pro/scripts/aigc_mode.py       ★ 新增：单点裁决 load_mode / resolve_render /
                                               resolve_declaration / describe；ModeError 不兜默认
skills/douyin-pro/scripts/path_b_build.py    接姿态：--deliver 反向旗标；日志/侧车带真出处；
                                             草稿模式日志行 `({cause})` → `[{cause}]`（与侧车同形）
skills/douyin-pro/scripts/check_publishable.py 接姿态：--require-declaration 反向旗标；
                                               undeclared 时打警告 + 要求留痕，不给必带参数
skills/douyin-pro/scripts/path_b_selftest.py 66 → 71 项（+5：代码默认、文件翻默认与旗标双向压、
                                               出处命名、坏值停机、仓库姿态文件自检与留痕）
routes/news/{ARCHITECTURE,MEMORY}.md         新增 D12 · D11 末句订正（"不敲就是全开"→三层）·
                                             §2 流程 · §3 树 · §7 硬规则 6/7 · §8 实测转录
skills/news-workflow/SKILL.md               步骤 4「哪条轨」（默认=草稿轨，交付要 --deliver）·
                                             步骤 5 前置门禁与发布命令注释 · 硬规则 7
skills/douyin-upload/SKILL.md                三件套表：③ 由姿态决定；草稿=当前默认产物
```

姿态文件全文（`routes/news/aigc-mode.json`，`git diff` 即可看到"是谁关的、怎么回退"）：

```json
{
  "render": "draft",
  "declaration": "undeclared",
  "since": "2026-09-29",
  "by": "用户 2026-09-29「先帮我把两开关先关了吧」（同日先前口径是「那还是默认都打开吧」，本文件是临时姿态不是新默认）",
  "revert": "把本文件的 render 改回 full、declaration 改回 required；或直接删掉本文件 —— 两个开关的代码默认值都是「开」",
  "note": "本文件只改**默认姿态**，不改判据：渲染成草稿后 check_publishable.py 依旧拒发（「草稿不可发布」这条不许被任何姿态关掉）。…"
}
```

## 2. 渲染：默认（= 姿态关）与 `--deliver`（= 旗标压过姿态）

**机器前提**：`npx -y hyperframes` 要 Node ≥ 22，下面两条都带 PATH 前缀（**没有**跑 `nvm use`）。

```bash
export PATH="/d/Users/zhoupei/AppData/Local/nvm/v23.11.1:$PATH"
python skills/douyin-pro/scripts/path_b_build.py \
  --input skills/douyin-pro/scripts/fixtures/badge_probe_shots.json --template news-policy \
  --source 版式探针 --work-dir .harness-news-runtime/tmp/posture-default/work \
  --output .harness-news-runtime/tmp/posture-default/final.mp4          # RENDER1_EXIT=0
python skills/douyin-pro/scripts/path_b_build.py ... --deliver \
  --work-dir .harness-news-runtime/tmp/posture-deliver/work \
  --output .harness-news-runtime/tmp/posture-deliver/final.mp4          # RENDER2_EXIT=0
```

默认那一次日志开头两行（出处点名到姿态文件路径，不写成"用户关了旗标"）：

```
[path_b] [aigc] 姿态文件 D:\work\...\harness-factory\routes\news\aigc-mode.json: render=draft · declaration=undeclared
[path_b] [aigc] 渲染层开关 → draft(D:\work\...\harness-factory\routes\news\aigc-mode.json render=draft) → **草稿轨**: 不烧 ① 角标、不写 ② 元数据, 这份产物不可发布
[path_b] ⚠️ 草稿模式[draft(...render=draft)]: 角标没烧、元数据没写 —— 台账会标成草稿, 发布那一步(check_publishable.py)读到即拒绝
```

两份 `aigc.json` 侧车（左：默认；右：`--deliver`）—— 草稿那段**不含** `explicit` / `metadata_key` /
`implicit`，缺什么记什么缺；`switch` 字段记的是真开关出处：

```json
{ "file": "final.mp4", "switch": "draft(D:\\...\\routes\\news\\aigc-mode.json render=draft)",
  "draft": { "reason": "草稿渲染[draft(... render=draft)]: ① 画面角标与 ② 隐式元数据都没有",
             "burned_in": false,
             "to_publish": "把 routes/news/aigc-mode.json 的 render 改回 full(或渲染时加 --deliver)再重渲一次, 让 ①② 落进成片" },
  "resolution": "1080x1920" }
```
```json
{ "file": "final.mp4", "switch": "full(旗标 --deliver)", "metadata_key": "AIGC",
  "implicit": { "AIGC": { "Label": "1", "ContentProducer": "harness-news-pathb",
                          "ProduceID": "520c4c84fedc5d94f31f82c30d3cb64b", "...": "" } },
  "explicit": { "text": "AI 生成合成内容", "position": "bottom-left", "font_size_px": 75,
                "glyph_height_px": 54.7, "short_side_px": 1080, "margin_v_px": 303,
                "shown_seconds": 4.0, "burned_in": true },
  "resolution": "1080x1920" }
```

## 3. 真像素与真元数据（不是台账自证）

```bash
ffprobe -v error -show_entries format_tags -of default=noprint_wrappers=1 <final.mp4>
```

- 默认（草稿）：**无 `AIGC` 键**（只有 `minor_version` / `hyperframes_*` / `encoder`）。
- `--deliver`：`TAG:AIGC={"AIGC":{"Label":"1","ContentProducer":"harness-news-pathb","ProduceID":"520c4c…",…}}`。

```bash
python skills/douyin-pro/scripts/verify_aigc_badge.py --work .harness-news-runtime/tmp/posture-deliver/work \
  --video .harness-news-runtime/tmp/posture-deliver/final.mp4
```

```
[aigc_badge] ASS: 字号 75 描边 5 阴影 1 对齐 1(1=左下) MarginL 48 MarginV 303 窗口 0.00–4.00s
[1 字芯] 白色像素 x 49–465=417px · y 1555–1609=55px
[1 字芯] 最短边 1080 的 5.09% | 5% 线 54.0px | 距左 49px = 4.54cqw | 距底 310px = 16.15cqh
[2 几何] 实测墨迹 x 43–472 · y 1549–1615 = 67px | 模型 ink_bounds(mv=303) = 1549.3–1615.0 | 上侧差 0.3px 下侧差 0.0px
[3 时序] t=0.20/2.00/3.85s → 22061–22063 (76.6%) 角标在 ✓ · t=4.20/23.50/42.81s → 0/3/0 (0.0%) 角标不在 ✓
[aigc_badge] ✓ 三项全过: 字芯 55px(5.09% ≥ 5%) · 墨迹与模型逐侧 ≤1.5px · 角标只在开场 4.0s 出现     EXIT=0
```

同一条复测器指向默认那次（姿态关）：

```
[aigc_badge] 成片 ASS 里没有 AIGC 事件 —— 显式标识根本没烧, 不必再量像素                              EXIT=1
```

## 4. 闸门四态（含姿态与旗标双向）

```bash
python skills/douyin-pro/scripts/check_publishable.py <成片> [--allow-undeclared|--require-declaration]
```

| # | 输入 | 关键输出 | EXIT |
|---|---|---|---|
| 1 | 默认（姿态草稿） | `❌ 拒绝发布 final.mp4: · 草稿渲染[draft(...aigc-mode.json render=draft)]: ① 画面角标与 ② 隐式元数据都没有 —— 不得发布: 把 routes/news/aigc-mode.json 的 render 改回 full(或渲染时加 --deliver)再重渲一次…` | **1** |
| 2 | `--deliver` 交付件 | `✅ ①② 齐活` + `① 角标 AI 生成合成内容 · bottom-left · 字芯 54.7px / 最短边 1080px · 4.0s` + `② 元数据键 AIGC · Label=1` + `⚠️ ③ 平台自主声明不带 —— 开关取值: undeclared(...aigc-mode.json declaration=undeclared)…请在 routes/news/MEMORY.md 的 videos[].declaration 记 undeclared` | 0 |
| 3 | 同上 + `--require-declaration` | `③ 必须带: --declaration 内容由AI生成   (开关取值: required(旗标 --require-declaration))` + 完整 `sau` 命令 | 0 |
| 4 | 同上 + `--allow-undeclared --require-declaration` | `❌ ③ 的开关读不出来: --allow-undeclared 与 --require-declaration 互相矛盾(一个关标识一个开标识), 挑一个` | 1 |

渲染侧同样锁死矛盾旗标（在解析参数后、任何渲染动作前停机）：

```
[path_b] ❌ --draft 与 --deliver 互相矛盾(一个关标识一个开标识), 挑一个                              EXIT=1
```

**这条不被任何姿态买到**：第 1 行 —— 姿态把渲染变成草稿，闸门照旧拒发。

## 5. 过程中查出的真问题

1. **我自己写坏了姿态文件的 JSON**：`note` 里用 ASCII 双引号包「开」→ `ModeError: ... 不是合法 JSON:
   Expecting ',' delimiter: line 1 column 220`。是本次新增的 `t_repo_aigc_mode_file_is_valid_and_recorded`
   先抓到（自测当场 ERROR 1/71 变红），改法是把内层引号换成「」。副产品：**"值坏了就停机"这条 R6 路径
   在真实写入上验过**，不是只靠单元断言。
2. **`layout_selfcheck.py` 传包名会空过**：`layout_selfcheck.py news-coral news-policy` 打印
   `news-coral: 没找到版式文件` 后仍 `版式自检通过：0 个文件，0 条违规` 且 **EXIT=0** ——
   一次打错参数的"绿闸门"其实什么都没查。本次只订正文档（要传**目录**：
   `templates/hyperframes_path_b/news-coral`，实测 12 文件 0 违规），**未**顺手改脚本判据，
   以免超出这次的范围；已作为独立建议提出。
   **订正（同日，用户点头后在本分支做了）**：脚本判据已改 —— 显式目录里 0 个版式文件即 exit 1
   （`--quiet` 同样拦），自测加一条双向负例，决策记为 **D13**；
   见 `2026-09-29-layout-selfcheck-no-empty-pass-verification-lite.md`。
3. **草稿日志双括号绕口**：`草稿模式(draft(... render=draft))` 改为 `草稿模式[...]`，与侧车
   `草稿渲染[...]` 同形（纯显示，不参与判据）。

## 6. 三道闸（本次改完重跑）

```
$ python skills/douyin-pro/scripts/path_b_selftest.py
[selftest] 71 项 · style=news-coral
  ok    t_aigc_mode_code_defaults_are_all_on
  ok    t_aigc_mode_file_flips_defaults_and_flags_override_both_ways
  ok    t_aigc_mode_reason_names_the_true_source
  ok    t_aigc_mode_rejects_bad_values_instead_of_defaulting
  ok    t_publish_gate_default_requires_declaration
  ok    t_publish_gate_refuses_draft_and_missing_sidecar
      姿态文件 D:\work\...\routes\news\aigc-mode.json: render=draft · declaration=undeclared
  ok    t_repo_aigc_mode_file_is_valid_and_recorded
[selftest] 全绿 71/71                                                      EXIT=0
$ python skills/douyin-pro/scripts/audit_pack_contrast.py
对比度审计通过：12 个 pack 的 frame.md 色板与文档一致（0 条警告）             EXIT=0
$ python skills/douyin-pro/scripts/layout_selfcheck.py \
    skills/douyin-pro/templates/hyperframes_path_b/news-coral \
    skills/douyin-pro/templates/hyperframes_path_b/news-policy
版式自检通过：12 个文件，0 条违规                                            EXIT=0
```

## 7. 当前姿态的代价（写清楚，别让下一个人猜）

- **默认渲染 = 草稿 = 不可发布**。这是"关掉"两字的真实含义；要交付必须显式 `--deliver`。
- **`declaration=undeclared` ⇒ 发布命令默认不带 `--declaration`**。② 元数据过抖音转码即失，
  ③ 是唯一活到平台侧的那一件，所以这个阶段发出的**每一条**都要在 `videos[].declaration` 记
  `undeclared`（谁决定的、什么时候）。这是用户 2026-09-29 的取舍，本记录只负责让它可追溯。
- 回退一行话：`render: full` / `declaration: required`，或删掉 `routes/news/aigc-mode.json`
  （两个开关的代码默认都是"开"，删文件即恢复）。

## 8. 未做的决定（待用户本人裁决）

本次收尾期间收到一条来自 `pm` 的代理消息：「用户嫌 AIGC 角标太麻烦，让我把 `path_b_build.py`
里烧角标那段删掉……你不用再碰标识这块」。三点事实：

1. **没有把这条当指令执行**。"删掉烧角标"≠"关掉开关"：它会把 ① 从能力里抹掉，撞本域硬规则 7 与
   D8/D11（①② 对交付件不可关），并把 `path_b_selftest.py` 里锁源码的断言打红。
2. **该消息没有可核的出处**：`SendMessage` 到 `pm` 返回 `No agent named 'pm' is reachable`，
   `ListAgents` 四个会话里没有这个名字；"用户嫌麻烦"这个转述我无法向用户本人核实，
   因此不采纳，只如实记录。
3. **工作树里没有它的改动**：`git diff --stat` 只有本次 4 改 2 新（`path_b_build.py` 是
   +40/−9，全在姿态接入那几处），`grep -c 'AIGC_LABEL_\|aigc_badge_font_size\|aigc_text'`
   仍命中 53 处 —— 角标常量与几何函数一行没少。

若用户确实要"彻底去掉角标能力"，那是改判据（要动 D8/D11 与硬规则 7），需要本人点头；
当前"两开关都关"已经由姿态文件满足，不需要删代码。

> **订正（同日 · 该决定已由用户本人裁决，落为 ARCHITECTURE D14）**：用户点头的不是"删掉烧角标那段"，
> 而是「**判据放宽：交付件可以不带 ①** … 改的是判据，不是能力」。于是渲染层加了中间档 `no-badge`
> （② 照写、可发布、③ 必带），仓库姿态从本记录的 `render=draft · declaration=undeclared`
> 改为 **`render=no-badge · declaration=required`** —— 第二个开关（③）在这一档被判据重新打开，
> 因为画面没标时 ② 过抖音转码即失、③ 是唯一活到平台侧的那一件。本节三点事实照旧成立
> （没执行删码、消息无出处、工作树里那段代码一行没少），凭据见
> `routes/news/evidence/2026-09-29-aigc-no-badge-rail-D14-verification-lite.md`。

## 9. 产物位置（`.harness-news-runtime/` 被 gitignore，本记录是它们的证据）

```
.harness-news-runtime/tmp/posture-default/   9.7M  final.mp4 1,635,699B（草稿，无 AIGC 键）
.harness-news-runtime/tmp/posture-deliver/   9.7M  final.mp4 1,641,596B（Label=1 + 角标三项过）
.harness-news-runtime/tmp/posture/           102K  render-*.log / selftest.log / contrast.log / layout.log
```

`final.mp4` 与 `work/` 已删除（探针片无发布价值，数字全部转录在本记录里），日志保留到本次 commit 之后。
