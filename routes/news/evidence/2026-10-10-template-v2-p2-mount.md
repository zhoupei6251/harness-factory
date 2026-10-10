# 模板 v2 · P2-3/P2-4 字幕挂载进 HyperFrames（2026-10-10）

裁决 2「字幕收进 HyperFrames 成为一级公民；AIGC 角标留 ASS」的落地轮。spec §6.4 记四条锁定
口径，本文件记**实测证据**：机判全绿 + 旗舰离线出帧（发射+自检+确定性）+ 渲染闸的环境阻塞。

## K11 机判：`path_b_selftest` 140/140 全绿

P2-2 尾是 132/132，本轮 +8 项全部围绕字幕挂载与 ASS 退役：

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

## K14 渲染闸：本机阻塞，未跑

三条只能在**真渲染**下证的闸，本轮**没有**过，如实记：

| 闸 | 卡在哪 |
|---|---|
| `gate_hyperframes_check`（`check --strict`）认字幕 DOM + `text-shadow` 描边 | HyperFrames 要求 Node **>=22**；本机 `nvm` 只有一个 `nodejs`= **20.9.0**，`node_modules/hyperframes` 的 `engines.node` 拒启 |
| 判据 4a **视频流哈希**两次相同（字幕进流后） | 需两次真渲染（Chrome 软栅），同上被 Node 版本挡住 |
| track-1 / track-2 **渲染期**叠放正确性 | 同上 |

**没有静默装 Node 22**（改系统运行时不在本轮授权范围，且 `doctor` 已明确报 ❌）。发射级确定性（K12）
与自检全绿（K11）是"字幕进流不破同稿同片"的必要条件，不是充分条件 —— 充分性要一台 Node>=22 的机器
跑一次旗舰双渲染补 K14。**这不是假绿**：结论明写"渲染闸未过"，代码里也没有把 `--check-only`/渲染
伪装成已通过。

## K15 存量包字节不变（裁决：只有编译包走原生字幕）

`pack["compiled"] = os.path.isfile(spec.toml)` 是唯一判据。`emit_composition` 仅当
`pack["compiled"] and scene_cues is not None` 才挂字幕轨；`mux_and_burn` 仅当 `pack["compiled"]`
才把 ASS cue 清空为"只角标"。31 套 path_b 存量手发包 `compiled is False` ⇒ 不传 `scene_cues`、
ASS 仍烧字幕，片字节形状不变。自测 `t_flagship_…_real_emitter` 里对 `DEFAULT_STYLE` 断言
`compiled is False` 兜住这条不回退。
