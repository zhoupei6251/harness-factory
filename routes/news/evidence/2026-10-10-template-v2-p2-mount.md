# 模板 v2 · P2-3/P2-4 字幕挂载进 HyperFrames（2026-10-10）

裁决 2「字幕收进 HyperFrames 成为一级公民；AIGC 角标留 ASS」的落地轮。spec §6.4 记四条锁定
口径，本文件记**实测证据**：机判全绿 + 旗舰离线出帧（发射+自检+确定性）+ Node 22 下真渲染四闸全过。

## K11 机判：`path_b_selftest` 141/141 全绿

P2-2 尾是 132/132，本轮 +9 项全部围绕字幕挂载、ASS 退役与字幕翻色：

| 测项 | 断言的接缝 |
|---|---|
| `t_subtitle_pieces_never_changes_the_on_screen_text` | 标点附着到前词，上屏文本 == 归一化正文（不改一个字） |
| `t_subtitle_scene_cues_marks_accent_without_touching_text` | 三源优先序：`10月`（数字+单位）压过 `全国执行`（屏句强调段） |
| `t_subtitle_composition_is_a_valid_subcomposition_and_selfchecks_clean` | 字幕子合成过 `layout_selfcheck` 全条 |
| `t_subtitle_composition_is_deterministic` | 同参两次调用逐字节相同，无 `Date.now`/`Math.random` |
| `t_subtitle_mount_uses_track_two_and_points_at_generated_file` | 挂 `data-track-index="2"`、指向 `subtitle-<i>.html`、不传 `data-variable-values` |
| `t_selfcheck_exempts_subtitle_only_for_the_two_invariants` | 只豁免 #6/#7 两条；改坏根 id 仍报 `CONTRACT_ID_MISMATCH`（反证，防"整文件跳过"假绿） |
| `t_flagship_compiled_pack_mounts_subtitle_through_the_real_emitter` | 走真 `emit_composition`：`subtitle-1.html` 落盘 + 宿主 `data-track-index="2"`×1 + `compositions/` 引用×2；存量包 `compiled is False` |
| `t_mux_retires_ass_subtitles_for_compiled_pack_only` | 编译包 ASS 仅剩 `,AIGC,,` 一条 Dialogue、无 `,Default,,`；存量包仍带字幕条 |
| `t_subtitle_fill_flips_with_ground_tone_to_pass_contrast` | 浅地面出墨字+白描边、深地面出白字+黑描边、强调两 tone 都琥珀、caption-zone 豁免项在位（钉住 K16 翻色不回退） |

## K12 旗舰离线出帧（发射 + 版式自检 + 确定性）

`--skip-render` 支不打网络、不渲 Chrome，但**走完整发射链路**：`fallback_scene_cues` 造词级
时间轴 → `emit_composition(scene_cues=…)` → `gate_layout_selfcheck`。输入单镜（title+屏句+正文）：

```
分镜1 → story  时长 6.8s  start 0.0s  地面 light
✅ 版式自检通过 (0 违规)
```

产出目录核对（`compositions/`）：七个版式 HTML + **`subtitle-1.html`** 都在。宿主 `index.html`：

- `data-track-index` 出现 `1` 与 `2` 各一次 —— 版式在 1 轨、字幕在 2 轨压在版式之上（裁决 2 的层序）
- `data-composition-src="compositions/…"` 引用 `story` 与 `subtitle-1` 两条 —— 挂载计数与 `mounts` 自洽

**发射级确定性**（判据 4a 的发射器半边，两次独立 `--skip-render` 跑）：

| 文件 | run1 == run2 | `Date.now`/`Math.random` 计数 |
|---|---|---|
| `compositions/subtitle-1.html` | `c4e6d8d1…` 逐字节相同 | 0 |
| `index.html` | `919cd592…` 逐字节相同 | — |

## K13 字幕子合成的时间轴形状（对齐裁决 17）

`subtitle-1.html` 脚本体（全绝对时间、`timeline({paused:true})`，可 seek）：

- 每个可见字一个 `fromTo(… {opacity:0,y:10},{opacity:1,y:0}, t=词start)` —— **只管入场、累积不消失**；start 落在词时间轴上逐词推进（0.0 → 6.595）。
- 整条 cue 一个退场 `tl.to("#sc-c0", {opacity:0, duration:0.3}, 6.822)` —— **按 cue 末一次做**，落在镜尾。
- 强调 `10月` 带 `.sc-acc`（`#B45309`），其余白字黑 `text-shadow` 八向描边，几何取 ASS 口径（`3.125cqh` 字高 / `9cqh` 底 / `6cqw` 侧 / `88cqw` 幅）。

一处**自我更正**（v1 试跑）：fixture 初版只给 `body`+`onscreen`+`onscreenAccent`，旗舰 `story`
契约要 `title`（领句位），`choose_layout` 报"填不满任何版式"。这是测试数据缺项、不是字幕实现缺陷 ——
补 `title` 后走真 `emit_composition` 全绿。

## K14 渲染闸：Node 22 下四条全过（本机 nvm 切换）

> **自我更正（覆盖上一版 K14）**：上一版记"渲染闸被 Node 阻塞、未跑"，把 Node 当成硬阻塞。
> 错。本机 `nvm` 装有 `22.20.0`（还有 `23.11.1` / `26.8.2`），`nvm use 22.20.0` 即可解锁真渲染。
> 唯一坑：nvm-windows 的符号链接**不跨调用持久** —— 每个新 Bash 会话起壳时活动 Node 会回落到
> `20.9.0`，所以 `nvm use 22.20.0` 必须和渲染命令**写在同一次调用**里，子进程 `hyperframes.cmd`
> 才继承到 22。分两次调用 = 第二次仍是 20，闸会拒启。

旗舰（story · 地面 light · `news-editorial-warm`）四条闸，Node 22.20.0 全过：

| 闸 | 结果 |
|---|---|
| `gate_hyperframes_check`（`check --strict --caption-zone=…;severity=error`） | `✅ check --strict 通过 (ok=True)`（修复前见 K16：20 条 contrast + 29 条 caption-zone 违规） |
| 判据 4a **视频流哈希**两次相同 | 两次 `--no-browser-gpu` 软栅渲染：H.264 流（`-c copy` 解包）逐字节相同 `cd5a45ce…`；解码后原始 yuv 逐帧相同 `a36506cb…`（各 979,776,000 B） |
| track-1 / track-2 叠放 | 宿主 `index.html`：story 挂 `data-track-index="1"`、`subtitle-1.html` 挂 `data-track-index="2"`，字幕轨压在版式之上（裁决 2 层序） |
| 寻址稳定（`fromTo` only，无 seek 漂移） | `check --strict` 无时序类 finding，`ok=True` 兜住 |

**注意区分**：整只 `silent.mp4` 的 md5 两次**不同**（`924ded2d` vs `109601ff`），差在容器头
（`mvhd` 里的 creation_time 等），文件长度差 72 字节使后续字节整体错位、`cmp` 报 140 万"不同"。
判据 4a 口径是**画面可复现**，不是**容器逐字节** —— 解包出 H.264 流、解码出像素两路都逐字节相同，
所以通过。副作用：`ProduceID = sha256(整只 silent.mp4)[:32]` 因此不随"同稿同片"稳定
（两次渲染 ProduceID `4c0dad50` ≠ `90aea5ca`），这是**先于字幕挂载就存在**的 AIGC 台账口径问题，
记在案不在本轮修。

**没有静默装 Node**：`nvm use` 只切符号链接、不改系统运行时，属可逆操作。

## K16 字幕翻色 + caption-zone 豁免（`check --strict` 修复轮）

修复前 `check --strict` 报 `ok=False`，两类 finding：

1. **20 条 `contrast_aa_failure`**：旧 `SUBTITLE_TEXT_COLOR = "#ffffff"` 是写死的白字，
   落到浅地面 story（`background: #f5efe3`）上 WCAG 对比只有 **1.15:1**（AA 大字要 3:1）。
2. **29 条 `caption_zone_collision`**：原生字幕的词级 DOM 落在引擎保留的字幕带
   （`--caption-zone=…y0=0.80…`）里，门禁按"给外部字幕预留、不许自绘内容侵占"判红。

**翻色裁决（owner 选「随地面翻色」）**：字幕填充色跟着地面 tone 走，不再写死 ——
`_subtitle_palette(tone)`：

| tone | 主字色 | 描边色 | 实测对比 |
|---|---|---|---|
| light（纸面 `#f5efe3`） | 墨 `#1f1b16` | 白 `#ffffff` 八向 | 墨/纸 **14.95:1**、墨/深纸 `#ddd3bf` 11.53:1 |
| dark | 白 `#ffffff` | 黑 `#000000` 八向 | 白/深底够用（旗舰是 light，dark 路走自测断言覆盖） |

强调色 `#B45309`（琥珀）两 tone 都用，light 地面实测 **4.39:1**（过 3:1 大字线）。
**未验证 / 推迟**：琥珀强调若压在深底（如钴蓝 `#3b5bd6`）实测 1.14:1 会破线 ——
旗舰 light 地面不触发，深底强调翻色留 P5 补。

**caption-zone 豁免**：`#sc-wrap` 加 `data-layout-allow-caption-zone` —— 原生字幕**本就是**这片带的
内容主体（裁决 2 把它收进 HyperFrames），保留带正是给它用的，引擎"预留给外部字幕"的假设在此不成立，
故显式声明占用。豁免只放行 caption-zone 一条；根 id / 其它版式契约违规照报（`t_selfcheck_exempts_…`
反证兜住）。自测 `t_subtitle_fill_flips_with_ground_tone_to_pass_contrast` 钉住翻色映射不回退。

## K15 存量包字节不变（裁决：只有编译包走原生字幕）

`pack["compiled"] = os.path.isfile(spec.toml)` 是唯一判据。`emit_composition` 仅当
`pack["compiled"] and scene_cues is not None` 才挂字幕轨；`mux_and_burn` 仅当 `pack["compiled"]`
才把 ASS cue 清空为"只角标"。31 套 path_b 存量手发包 `compiled is False` ⇒ 不传 `scene_cues`、
ASS 仍烧字幕，片字节形状不变。自测 `t_flagship_…_real_emitter` 里对 `DEFAULT_STYLE` 断言
`compiled is False` 兜住这条不回退。
