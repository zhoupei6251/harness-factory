# 2026-09-29 · AIGC 角标退到法定线上（左下角 · 擦边字号 · 开场 4 秒）—— 验证记录（lite）

**范围**：把显式角标从「左上角 · 贯穿全片 · 字号 85」改成「**左下角 · 开场 4 秒 · 字芯擦到最短边 5% 线**」，
并把一次性量测脚本升级为受版本管理的 `skills/douyin-pro/scripts/verify_aigc_badge.py`。
**不含**新的新闻成片（用 5 镜 news-policy 版式探针量几何，探针不是可发布内容）。

结论：**三项判据全部在真实渲染像素上复现；三道闸全绿；量测器对植入的假字号确实停机（EXIT=1）。**
过程中查出一处会让文档自吹真画压字的几何错误：底边距没扣 ASS 行盒的 8px 下伸部空白，
模型报「上侧留 13px」而按 8px 反算实画只有 5px（旧 mv=311 时角标几乎贴上内容下界 1536）
—— 已改正（`MarginV` 311 → 303）。

---

## 1. 被验对象

```
skills/douyin-pro/scripts/path_b_build.py        AIGC_LABEL_LINE_SLACK_PX / AIGC_LABEL_SHADOW_PX /
                                                 AIGC_LABEL_OUTLINE_EM_DIV 新增；
                                                 aigc_badge_outline / ink_bounds / band_bounds 提出为函数；
                                                 aigc_badge_margin_v 改为「解带上下界取中」；
                                                 角标 Alignment 1（左下）+ 事件窗口 0–4.00s
skills/douyin-pro/scripts/path_b_selftest.py     63 项（墨迹两侧留高 + 横屏退让新断言）
skills/douyin-pro/scripts/verify_aigc_badge.py   ★ 新增：真像素复测器（字芯 / 墨迹 / 时序）
skills/douyin-pro/scripts/fixtures/badge_probe_shots.json
                                                ★ 新增：量像素用的 5 镜探针输入（受版本管理，见 §2.2）
routes/news/{ARCHITECTURE,MEMORY}.md             D8 重写（底线 vs 加码）· §8 实测数字 · 决策树旁注
skills/news-workflow/SKILL.md                    第 ⑧ 步描述 + 三道闸项数
skills/douyin-upload/SKILL.md                    ① 显式标识那一格
```

`AIGC_LABEL_SUB_GAP_FRAC`（旧的「字幕块顶往上让固定比例」）已删除 —— 它反推出来的底边距
不扣行盒空白，是这次 8px 偏差的来源。

## 2. 命令与实测输出（仓库根执行）

### 2.1 三道闸

```bash
python skills/douyin-pro/scripts/path_b_selftest.py
python skills/douyin-pro/scripts/audit_pack_contrast.py
python skills/douyin-pro/scripts/layout_selfcheck.py \
    skills/douyin-pro/templates/hyperframes_path_b/news-coral \
    skills/douyin-pro/templates/hyperframes_path_b/news-policy
```

```
[selftest] 63 项 · style=news-coral
  ok    t_aigc_badge_sits_in_the_gap_between_content_and_subtitles
  ok    t_aigc_badge_landscape_band_yields_to_subtitles
[selftest] 全绿 63/63
对比度审计通过：12 个 pack 的 frame.md 色板与文档一致（0 条警告）
版式自检通过：12 个文件，0 条违规
```

### 2.2 渲一份用来量像素的探针（news-policy 5 镜，1080×1920）

探针输入是**受版本管理的 fixture** `skills/douyin-pro/scripts/fixtures/badge_probe_shots.json`
（5 镜 news-policy 占位文案，`请勿发布`）—— 按 §6 的口径，复现命令不许指向 gitignore 里的残留路径。
`--work-dir` 必须显式给：`verify_aigc_badge.py` 要读工作目录里留下的 `subs.ass` 与 `silent.mp4`。
这一步要联网（edge-tts 配音 + HyperFrames 渲染）；镜头时长随 TTS 微变，而本记录判据里的字芯、
墨迹上下界、左边距都只由分辨率与 ASS 样式决定，与时长无关。

```bash
python skills/douyin-pro/scripts/path_b_build.py \
    --input skills/douyin-pro/scripts/fixtures/badge_probe_shots.json \
    --template news-policy --source 版式探针 \
    --work-dir .harness-news-runtime/tmp/badge-probe/work \
    --output .harness-news-runtime/tmp/badge-probe/probe.mp4
```

侧车（`.harness-news-runtime/tmp/badge-probe/aigc.json`，隐式段略）：

```json
{"file": "probe.mp4", "metadata_key": "AIGC",
 "explicit": {"text": "AI 生成合成内容", "position": "bottom-left",
              "font_size_px": 75, "glyph_height_px": 54.7, "short_side_px": 1080,
              "margin_v_px": 303, "shown_seconds": 4.0, "burned_in": true},
 "resolution": "1080x1920"}
```

### 2.3 真像素复测（本记录的判据来源，同一命令跑三次输出逐字相同）

```bash
python skills/douyin-pro/scripts/verify_aigc_badge.py \
    --work .harness-news-runtime/tmp/badge-probe/work \
    --video .harness-news-runtime/tmp/badge-probe/probe.mp4
```

```
[aigc_badge] 成片 probe.mp4 1080×1920 · 50.0s (silent 50.0s)
[aigc_badge] ASS: 字号 75 描边 5 阴影 1 对齐 1(1=左下) MarginL 48 MarginV 303 窗口 0.00–4.00s

[1 字芯] 白色像素 x 49–465=417px · y 1555–1609=55px
[1 字芯] 最短边 1080 的 5.09% | 5% 线 54.0px
[1 字芯] 距左 49px = 4.54cqw(ASS MarginL 48 → 模型 48px) | 距底 310px = 16.15cqh

[2 几何] 实测墨迹(含描边阴影) x 43–472 · y 1549–1615 = 67px
[2 几何] 模型 ink_bounds(mv=303) = 1549.3–1615.0 | 上侧差 0.3px 下侧差 0.0px

[3 时序] 基准 silent.mp4 vs 成片 · bbox (43, 1549, 473, 1616) = 28810px
       时刻 |    bbox 差异 |      占比 | 判定
t=   0.20s |      22061 |   76.6% | 角标在  ✓
t=   2.00s |      22061 |   76.6% | 角标在  ✓
t=   3.85s |      22066 |   76.6% | 角标在  ✓
t=   4.20s |          0 |    0.0% | 角标不在  ✓
t=   27.00s |          0 |    0.0% | 角标不在  ✓
t=   49.79s |          0 |    0.0% | 角标不在  ✓

[aigc_badge] ✓ 三项全过: 字芯 55px(5.09% ≥ 5%) · 墨迹与模型逐侧 ≤1.5px · 角标只在开场 4.0s 出现
EXIT=0
```

读法（三件事各自证明什么）：
- **字芯 55px ≥ 54.0px 线** 是国标真正量的那个数（ASS `FontSize` 75 是 em 高，字面率 0.729）。
  距底 16.15cqh < 20cqh → 位置在画面底边带内，配合 4.54cqw 的左边距，视觉上就是左下角。
- **模型与实测逐侧 ≤0.3px** 证明几何式子（行盒底 → 减 8px 下伸部空白 → 字芯 → 加描边/阴影）
  对得上渲染。旧式子在这里差整整 8px。
- **窗口内 76.6% / 窗口外 0.0%** 证明「只在开场 4 秒常驻」是按像素成立的事实，不是注释里的愿望。
  基准取 `silent.mp4`（烧 ASS 之前），所以差异只可能来自角标。

凭据来源如实写清：下面引用的输出产生于清理前的 `.harness-news-runtime/tmp/badge-probe2/`（输入就是
上面那份 fixture 的原件），删除 scratch 之前已按 2.2 → 2.3 的路径命名复跑一次，输出与引用逐字相同。

### 2.4 负例：量测器确实停机

植入假字号（把 `subs.ass` 的 AIGC 样式 `FontSize` 75 改成 60，其余一字不动）：

```bash
mkdir -p .harness-news-runtime/tmp/badge-neg
cp .harness-news-runtime/tmp/badge-probe/work/silent.mp4 .harness-news-runtime/tmp/badge-neg/
sed 's/^Style: AIGC,Microsoft YaHei,75,/Style: AIGC,Microsoft YaHei,60,/' \
    .harness-news-runtime/tmp/badge-probe/work/subs.ass > .harness-news-runtime/tmp/badge-neg/subs.ass
python skills/douyin-pro/scripts/verify_aigc_badge.py \
    --work .harness-news-runtime/tmp/badge-neg \
    --video .harness-news-runtime/tmp/badge-probe/probe.mp4
```

```
[aigc_badge] 成片 probe.mp4 1080×1920 · 50.0s (silent 50.0s)
[aigc_badge] ASS: 字号 60 描边 5 阴影 1 对齐 1(1=左下) MarginL 48 MarginV 303 窗口 0.00–4.00s

[1 字芯] 白色像素 x 49–382=334px · y 1567–1610=44px
[1 字芯] 最短边 1080 的 4.07% | 5% 线 54.0px
[1 字芯] 距左 49px = 4.54cqw(ASS MarginL 48 → 模型 48px) | 距底 309px = 16.09cqh

[2 几何] 实测墨迹(含描边阴影) x 43–388 · y 1562–1617 = 56px
[2 几何] 模型 ink_bounds(mv=303) = 1549.3–1615.0 | 上侧差 12.7px 下侧差 2.0px

[3 时序] 基准 silent.mp4 vs 成片 · bbox (43, 1562, 389, 1618) = 19376px
       时刻 |    bbox 差异 |      占比 | 判定
t=   0.20s |      15437 |   79.7% | 角标在  ✓
t=   2.00s |      15435 |   79.7% | 角标在  ✓
t=   3.85s |      15440 |   79.7% | 角标在  ✓
t=   4.20s |          0 |    0.0% | 角标不在  ✓
t=  27.00s |          0 |    0.0% | 角标不在  ✓
t=  49.79s |          0 |    0.0% | 角标不在  ✓

[aigc_badge] ✗ 字芯 44px 低于最短边 5% 线 54.0px → 不合规
[aigc_badge] ✗ 墨迹上侧实测 1562 与模型 1549.3 差 12.7px > 容差 1.5px
[aigc_badge] ✗ 墨迹下侧实测 1617 与模型 1615.0 差 2.0px > 容差 1.5px
EXIT=1
```

顺带量到一件事：**行盒下空白随字号缩放**（75 号→8px，60 号→7px，约 0.10 em）。
`AIGC_LABEL_LINE_SLACK_PX` 因此是「当前字号那一个点」的实测值，不是普适常数 ——
已把这句写进常量注记，改字号或改最短边基准后必须重跑 2.3。

## 3. 判据与结论

| 判据 | 依据 | 结果 |
|---|---|---|
| 字芯 ≥ 画面最短边 5% | GB 45438-2025 | ✅ 55px vs 54.0px 线（5.09%） |
| 位于画面边角 | GB 45438-2025 | ✅ 距左 4.54cqw · 距底 16.15cqh（左下） |
| 持续 ≥ 2 秒 | GB 45438-2025 | ✅ 4.0s（窗口外实测 0 差异） |
| 起始画面可见 | 《标识办法》§ 4-四「应当」 | ✅ 事件 0:00:00.00 起 |
| 模型 = 渲染 | 本域「文档数字必须可复算」 | ✅ 逐侧 0.3 / 0.0px |
| 不压字幕、不压内容 | 包内法则 1（底部 20cqh 禁入带） | ✅ 竖屏两侧各 13px；横屏退让（见未验证 ③） |
| 隐式标识读回 | GB 附录 E 七要素 | ✅ `mux_and_burn` 写完 ffprobe 读回，读不回拒绝交付（既有闸门） |

## 4. 未验证 / 遗留代价（如实写）

① **播放周边**不再由角标承担 —— 靠 ② mp4 元数据 + ③ 发布端 `--declaration 内容由AI生成`。
   法律上「应当」的两句已由「起始画面 4 秒 + 元数据 + 平台声明」覆盖，但少了旧实现那一档自我加码。
② **左下角是抖音标题/头像/进度条的叠加区**，平台 UI 会盖在角标上面（旧实现落左上角避开的正是这一层）。
   4 秒窗口内是否真能看见，只有发布后在抖音 App 里才能确认 —— 本次未验。
③ **横屏 1920×1080** 的带装不下角标（带 51px < 墨迹 65.7px），按 `aigc_badge_margin_v` 的退让
   取 `MarginV = lo`，代价是压进底部 20cqh 内容预留带 22.7px。这条只由纯函数断言
   `t_aigc_badge_landscape_band_yields_to_subtitles` 锁住，**没有横屏真实渲染复测**。
④ **擦边字号零余量**：0.729 字面率是本机 · Microsoft YaHei · 该分辨率的实测值，字体回退即失效。
   换机器/换字体后跑 2.3，字芯项会红。
⑤ 探针内容全是占位文案，不构成新闻成片；`news-coral` 的角标几何未重渲复测（同一套函数，
   但「同一套函数」不是「同一张画面」）。

## 5. 一次性脚本的去向

`tmp/` 里本次写下的三个一次性量测脚本 —— `badge_recheck.py`（差值定墨迹界）、
`badge_measure.py` / `badge_timing.py`（早期草稿）、以及 `badge-probe/`、`badge-probe2/`、`badge-neg/`
三个 scratch 目录 —— 已全部删除，判据搬进 `verify_aigc_badge.py`，探针输入搬进
`scripts/fixtures/badge_probe_shots.json` —— 按 ARCHITECTURE §6 的口径，**契约证据不许住在 gitignore 里**：
留在忽略目录的复现命令，换台机器就是一条指向不存在路径的命令。
本记录与 `2026-09-29-contrast-audit-and-stem-gate-verification-lite.md` 用 `git add -f` 显式进版本管理，
因为 §8 的复现指针指向它们，留在忽略目录等于换台机器就没做过。
