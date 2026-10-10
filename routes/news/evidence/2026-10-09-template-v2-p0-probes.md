# 新闻域模板 v2 — P0 四探针验证单

> 日期：2026-10-09 ｜ 被测设计：`docs/superpowers/specs/2026-10-09-news-template-v2-design.md` §8
> 目的：在铺 31 套之前，先把四个「任一翻车就得回 §5 改族签名」的假设打成结论。
> 探针代码按 spec §8「不保留代码」落在被忽略的 `.harness-news-runtime/probe/`，
> 本文把**命令行原文与实测输出**逐条留下，任何一条都能照抄复跑。

## 0. 环境前置（先说清，否则后面的数字没有口径）

本机默认 Node 是 v20.9.0，而 `hyperframes@0.8.141` 要求 **Node ≥ 22**：

```
$ node -v
v20.9.0
$ ./node_modules/.bin/hyperframes --version
HyperFrames requires Node.js >= 22 (current: 20.9.0). Switch Node versions and retry.
```

这不是版式失败，`routes/news/ARCHITECTURE.md` §订正与提速验证单 §0 都记过同一件事。
处置沿用提速项目的做法：**运行时 PATH 前缀注入，不 `nvm use`、不动全局默认**。

```
export PATH="/d/Users/zhoupei/AppData/Local/nvm/v23.11.1:$PATH"   # 实测 node v23.11.1
HF=/d/work/xinyue/aigc_platfrom_back/harness-factory/node_modules/.bin/hyperframes
$ "$HF" --version  →  0.8.141        # 出处 = 项目 node_modules，不走 npx
```

Python 侧无需新增依赖（实测已在盘）：Python 3.12.3、`edge-tts 7.2.8`、`PyYAML 6.0.3`、`cv2 4.13.0`。

---

## P0-1 · 构建期切 span + `fromTo` 逐字，seek 抽帧稳不稳 —— **通过**

**结论：可用，且是这份设计里最稳的一条。** 杂志族的招牌（逐字上涌 + 衬线大字）成立。

探针：`.harness-news-runtime/probe/p01-charrise/index.html` —— 18 个码点各一个
`<span class="p1-ch">`（构建期切好，运行时不 split），一条
`fromTo("#p1-title .p1-ch", {y:14,opacity:0}, {y:0,opacity:1,duration:0.7,stagger:0.045})`。

```
$ "$HF" check . --strict --json                 → ok=True  errors=0 warnings=0
$ "$HF" check . --strict --json --at-transitions → ok=True  errors=0 warnings=0
$ "$HF" snapshot . --at 0.35,0.6,0.9,1.4,3.0 --no-end -o snapA
$ "$HF" snapshot . --at 0.35,0.6,0.9,1.4,3.0 --no-end -o snapB
$ (cd snapA && md5sum *.png|sort) > a; (cd snapB && md5sum *.png|sort) > b; diff a b
IDENTICAL (seek-stable)     # 5 张 PNG 两次抓取逐字节一致
```

三点各自要记清：

1. **D3 的死因确实被绕开了。** 老 `hook.html:224` 撤掉的方案是 `onStart` 里 split + `tl.from`；
   seek 模型下 `onStart` 不触发。本探针把切分挪到构建期、动画一律 `fromTo`，
   于是「第 3 个字在 t=0.6 是什么状态」只由关键帧决定，与播放历史无关 —— 上面的哈希一致就是这件事的证据。
2. **中途态是真·渐进**，不是「全有或全无」：t=0.6s 帧里「拾荒二十」已立起、「一」在半途、
   后面几个字还是低透明度。逐字节奏 0.045s/字在 18 字上摊 0.81s，配 0.7s 单字时长，重叠但不糊。
3. **思源宋体在渲染机上是真衬线**（见 `snapA/frame-01-at-0.6s.png`：横细竖粗、笔画端脚清楚），
   `@font-face { font-family:"HF CJK Serif"; src: local("Noto Serif SC") }` 生效。
   裁决 7 由此从「字体文件在盘上」升级为「渲染出来确实是它」。

**成本**：18 字 = 18 个 DOM 节点 + 1 条 tween（`stagger` 在 GSAP 内部展开，不额外加 JS 行数）。
DOM 膨胀对渲染时长的影响并进 P0-4 / 判据 6 一起量，不单独猜。

---

## P0-2 · `clip-path` 在 `check --strict` 下报不报 overflow —— **有条件通过，并且推翻 spec 法则 11 的一句话**

这条探针跑出了本轮最有价值的负面结论，所以拆成三问。

### (a) 遮罩揭示（盒子本来就在框内）—— **合法**

`.harness-news-runtime/probe/p02-clip/`：`#p2-surface` 带 `background:#1f3a68`，
`clip-path: inset(100% 0 0 0) → inset(0% 0 0 0)`；`#p2-label` 横向 `inset(0 100% 0 0) → inset(0 0% 0 0)`。

```
$ "$HF" check . --strict --json → EXIT=0, ok=True
  lint 0/0 · runtime 0/0 · layout 0 errors 0 warnings (9 samples) · contrast 4 checked 4 passed
```

**带底色面块用 `clip-path` 揭示，完全干净** —— 法则 11 的前半句成立，法则 8 的替身找到了。

### (b) 用 `clip-path` 去藏一个越界的盒子 —— **不合法，而且 `clip-path` 遮不住检测器**

`.harness-news-runtime/probe/p02b-bleed/`：`#p2b-bleed` 的 `left:-15cqw; width:130cqw`，
靠 `clip-path: inset(0 0 0 15cqw)` 裁回画布；对照组 `#p2b-inside` 同样越界，但靠祖先
`overflow:hidden` 裁。

```
$ "$HF" check . --strict --json --at-transitions → EXIT=1, ok=False, layout: 2 errors 3 warnings
  error   text_box_overflow  #p2b-bleed   containerSelector=#root        rect.left=-162 right=1220.41
  error   text_box_overflow  #p2b-inside  containerSelector=div.p2b-clip-parent
  warning canvas_overflow    #p2b-inside / #p2b-bleed
  warning container_overflow #p2b-inside
```

**被推翻的说法**：spec §7 法则 11 原文「`clip-path: inset()` 不改几何不混色，完全合规」。
「不混色」对（对比度段 0 问题），「不改几何」恰恰是问题所在 —— 检测器量的是**布局盒与文本行盒**，
`clip-path` 只改像素不改布局盒，所以越界照报；`overflow:hidden` 同样照报（对照组）。
**结论：`clip-path` 是「怎么显形」的合法手段，不是「可以出界」的许可证。**
杂志族/胶片族想要的「大字出血到画布外」不能靠裁切实现，只能让盒子本身留在画布内、
靠满幅字号顶到边（视觉上出血），或者接受被 `--strict` 拦下。

### (c) 顺带量到的一条：从画布外滑入，今天**过不了严格采样、却过了产线**

`.harness-news-runtime/probe/p02c-slide/`：`#p2c-title` 从 `x:-110cqw` 滑入，
`#p2c-band` 从 `x:120cqw, y:40cqh` 对角擦入，`#p2c-slant` 静态 `rotate(-3deg)`。

```
$ "$HF" check . --strict --json --at-transitions → ok=False  layout: 1 error 1 warning（#p2c-title 在 t=0.2 半途出界）
$ "$HF" check . --strict --json                  → ok=True   layout: 0 errors 0 warnings（同一份文件，只剩 3 条 info）
```

差别只在采样点：产线 `gate_hyperframes_check`（`path_b_build.py:1874-1907`）传的是
`check . --strict --json --caption-zone=…`，**不带 `--at-transitions`**，默认 9 个中点采样
（0.222/0.667/…）刚好错过元素还在界外的瞬间。

- 好消息：**旋转合法** —— `rotate(-3deg)` 的色块在两种采样下都零问题，号外族的 45° 硬阴影、
  街采族的 ±1.5° 马克笔带都不受影响。
- 需要拍板的：**「从画布外擦入」目前是踩在采样漏缝上过关的**，不是被明确允许。
  号外族（字压线擦入）与竞技族（对角擦入）的签名依赖它。
  建议：新体系**不用**界外起点，擦入一律改成「盒子就位 + `clip-path` 揭示」（(a) 已证明合法），
  视觉上等价、且不怕哪天产线加上 `--at-transitions`。这是 P1 原语库的设计约束，不是阻塞项。

---

## P0-3 · edge-tts 中文 `WordBoundary` 返词还是返字 —— **返词，§6.4 全部成立**

`.harness-news-runtime/probe/p03-wordboundary/probe.py`（`edge_tts.Communicate(..., boundary=...)`，
CLI 无此旗标，必须走 Python API）。输入 42 字真稿句，音色 `zh-CN-XiaoxiaoNeural`。

```
=== boundary=WordBoundary ===
audio_bytes=57888  events=20
char-count distribution: min=1 max=5 mean=1.90
first 14 event texts: ["湖南","常德","71岁","老人","捡","了","21","年","废品","民政","部门","救助","时","才"]
multi-char events: 13/20
span from first to last event: 8.99s  (source text 42 chars)

=== boundary=SentenceBoundary ===
audio_bytes=57888  events=1
first event text: 整句 42 字一条
```

四点结论：

1. **返词**，而且分词质量是能直接用的水平（「湖南」「常德」「71岁」「老人」「废品」「民政」「部门」），
   不是随机两字切。§8 担心的「若是字级就得在发射器侧做词组聚合」**不发生**，
   §6.4 的「精确子串匹配强调词」按原设计走。
2. **D5 的根因同步证实**：`SentenceBoundary` 整句只给 1 条 cue —— 今天管线里
   `synthesize_audio`（`path_b_build.py:2073`）shell 调 CLI 拿到的就是这个，
   所以现在的字幕只能整句跳。改成 Python API + `boundary="WordBoundary"` 即解。
3. **换 boundary 不改音频**：两次 `audio_bytes` 都是 57888。也就是说 P2 引入逐词时序
   不会动到 mp3 字节，判据 4 的确定性面不因此扩大。
4. **数字被当成词**：`"71岁"` / `"21"` / 隐含的 `"3700元"` 各自成事件 ——
   这对「数字+单位」强调源（§6.4 三源之一）是好消息，匹配粒度天然对齐。

**残留风险（不阻塞 P1）**：WordBoundary 依赖微软服务。P2 落地时按 spec §6.4 的
`cues.json` 落盘方案处理 —— 首次合成把词数组写进 work_dir，重跑读文件不重问服务。

---

## P0-4 · 同稿两渲哈希基线（改造前测）—— **渲染器是确定的；判据 4 的口径写错了**

**先说结论，因为它跟直觉相反**：`final.mp4` 两次哈希**不一致**，但这**不是**「确定性 MP4 坏了」，
而是判据 4 把不该进判据的东西算进去了。真凶是**配音**，不是渲染。

### 第一层：整片哈希确实不一致

同一份 `badge_probe_shots.json`、同一命令、跑两遍（Node 前缀注入、`--gpu --quality=delivery --fps=30`）：

```
run1/final.mp4  1a05b713f69879c471029d21f0094334
run2/final.mp4  9efa9eabb45b3641cc18ef9700091eee     ← 不同
w-run1/silent.mp4  d1efa7bdbabeb10c4188003a25347cd6
w-run2/silent.mp4  68fe8a155bc2af25da87365ba04be7c4  ← 不同
scene_*.vtt     IDENTICAL      scene_*.mp3  DIFFERS（但时长逐条一致：8.976/8.400/8.880/8.712/8.064）
w-run1/index.html == w-run2/index.html  (b2c48197…)   w-run1/compositions/*.html == w-run2 的
```

发射器输出**逐字节相同**（index.html 与 7 份 composition 全等），时间轴长度也相同
（mp3 时长一一对应），可 `silent.mp4` 还是不同。所以差异一定在渲染的某个输入里。

### 第二层：把渲染器单独拎出来测（同一目录连渲两次）

```
$ cd w-run1 && hf render -c index.html -o det-a.mp4 … ; hf render … -o det-b.mp4
det-a.mp4  d1efa7bd…   det-b.mp4  d1efa7bd…   原生 silent.mp4  d1efa7bd…   ← 三者全等
$ cd w-run2 && 同样两遍
re-a.mp4   68fe8a15…   re-b.mp4   68fe8a15…   原生 silent.mp4  68fe8a15…   ← 三者全等
```

**渲染器对自己的输入是纯函数**：同目录重跑必然复现自己，跨进程、跨时间都复现。
法则 10 担心的「跨渲染漂移」在引擎侧**没有发生**。

### 第三层：拆流定位（决定性一步）

`silent.mp4` 名字叫 silent，其实**带音轨**（宿主的 `<audio>` 被编码进去了）：

```
$ ffprobe -show_entries stream=codec_type,codec_name w-run1/silent.mp4
0,h264,video
1,aac,audio
$ ffmpeg -i $d/silent.mp4 -an -c:v copy → 视频流哈希
   w-run1  7e08468ac9803eded81f28e245f9f96a
   w-run2  7e08468ac9803eded81f28e245f9f96a   ← **两次独立成片，视频流逐字节相同**
$ ffmpeg -i $d/silent.mp4 -vn -c:a copy → 音频流哈希
   w-run1  e49cc839e06f07437871bc2a017c1e41
   w-run2  6aadd9952cc9679a0a7b80334b369b15   ← 不同的只有音频
```

**归因完成**：不一致 100% 来自 edge-tts 现场合成的 mp3 字节（微软服务每次返回的编码字节不同，
但解码时长稳定），经 `<audio>` 进入 `silent.mp4`，再进 `final.mp4`。视频侧零漂移。

### 这条要回写 spec —— 判据 4 现在的写法是**永久红**的

spec §1 判据 4 写的是「同稿渲染两次，`final.mp4` 哈希一致」。按现状这一条**永远不可能过**，
而且失败信息不指向真因（P4 的「确定性哈希门」若照抄这个口径，会把一个健康的渲染器
当成 bug 追三周）。建议改成两条可分别归因的断言：

- **4a 视频确定性**：`ffmpeg -an -c:v copy` 后的视频流哈希两次一致 —— 实测**现在就成立**。
- **4b 音频可复现性**：把 `scene_*.mp3` 与 `cues.json` 落盘进 work_dir，重跑读文件不重问服务
  （与 §6.4 已有的 `cues.json` 方案同构，只是把缓存对象从 cues 扩到 mp3）。
  做到了 4b，`final.mp4` 整片哈希才会一致。

**顺带量到的计时**（同稿 5 镜 43s，`--gpu --quality=delivery --fps=30`）：
`run1 total 72.18s`（render 34.88 / gate 15.05 / dub 13.41 / mux 6.66）、
`run2 total 93.52s`（render 49.45 / mux 9.89）。
与提速项目热跑基线 65.92s 同量级；run2 的 render 段抖到 49s 是 GPU/系统负载，
判据 6（旗舰包 > 基线 ×1.5 = 98.9s 触发停止）用**中位数或多次取优**，不要用单次。

---

## 决策门判定（spec §8）

| 探针 | 判定 | 对设计的影响 |
|---|---|---|
| P0-1 逐字 span | **通过** | 杂志族招牌（衬线大字 + 逐字上涌）成立，裁决 7 拿到渲染级证据 |
| P0-2 `clip-path` | **有条件通过** | 法则 11 需改写：`clip-path` 只解决「怎么显形」，不解决「可以出界」；界外擦入改道 |
| P0-3 `WordBoundary` | **通过（返词）** | §6.4 字幕设计原样成立，无需词组聚合层 |
| P0-4 确定性哈希 | **渲染器确定；判据 4 口径要改** | 拆成 4a 视频流哈希（已成立）+ 4b mp3/cues 落盘 |

**放行结论：四个探针无一触发「停止实施」。** P1 可以开工。

但 P0 顺手抓出**三处 spec 写错/写空的地方**，都要回写，否则实施阶段会踩：

1. **§1 判据 4**（上面已述）—— 现口径永久红，且会把健康渲染器当 bug 追。
2. **§7 法则 11**「`clip-path: inset()` 不改几何不混色，完全合规」——
   「不改几何」恰恰是被 `check --strict` 抓住的那一半。
3. **§11「`CJK_FAMILY` 单数常量是唯一静默阻断点：思源宋体一进 `@font-face` 就挂审计」——
   实测方向相反，见下。**

### 附：`CJK_FAMILY` 的真实故障是「假绿」，不是「报错」

`layout_selfcheck.py:336` 的判定是 `any(CJK_FAMILY in block for block in font_faces)`，
而 `"HF CJK"` 是 `"HF CJK Serif"` 的**子串**。实测五种组合（拿 `news-coral/hook.html`
只替换 `@font-face` 段，其余原样）：

| 探针输入 | `MISSING_CJK_FONT_FACE` | 应该报吗 |
|---|---|---|
| 只有 `HF CJK` | 不报 | 对 |
| `HF CJK` + `HF CJK Serif` | 不报 | 对 |
| **只有 `HF CJK Serif`** | **不报** | 错 —— 正文族缺失被放过 |
| **`HF CJK Serif` 的 `local()` 名全写错** | **不报** | 错 —— 静默回落无衬线，杂志族招牌字体没了 |
| 完全没有中文 face | 报 | 对 |

也就是说：思源宋体进来**不会挂审计，而是审计直接失明**。这比 spec 预言的失败模式更坏 ——
按 §11 的说法改，只会去放宽一条本来就该拦的规则，而真正漏的两条（族名被子串吞掉、
`local()` 写错无人拦）一条都补不上。修法见 P1 第一个提交。

> **2026-10-09 P1 落闸时对本节的一次自我订正。** 上面那句"思源宋体进来不会挂审计"
> 把结论写大了，方向取决于**宋体叫什么名字**：
>
> ```
> 'HF CJK' in 'HF CJK Serif'  -> True    # 前缀式（本附录探针用的名字，子串洞成立）
> 'HF CJK' in 'HF Serif CJK'  -> False   # 中缀式（news-policy 产线现用的名字）
> ```
>
> 所以拿产线名做同一个实验（`news-coral/hook.html`，只动字体，实测 `check_layout` 返回码集）：
>
> | 探针输入 | 旧闸结果 | 判定 |
> |---|---|---|
> | 正文用 `"HF Serif CJK"` 但**没有**它的 `@font-face` | `[]` 全绿 | **真失明的第一条**：宋体回落系统默认字，无人报错 |
> | 声明 + 使用都叫 `"HF CJK Serif"`（自造名，不在设计体系里） | `[]` 全绿 | **子串洞**：族名脱纲也放行 |
> | 把声明改成 `"HF Serif CJK"`、正文仍写 `"HF CJK"` | `MISSING_CJK_FONT_FACE` | 旧闸**当场就红**（因为产线名不含子串） |
>
> 结论修正为：**旧闸有三条静默路径（用到未声明 / `local()` 全假 / 前缀式自造族名），
> 但"宋体一进 `@font-face` 就挂审计"和"思源宋体进来不会挂审计"两种说法都不成立** ——
> 后者只对前缀式命名成立。真正的影响没变：闸门的判定必须按**精确族名**走，
> 且允许名单必须把 `HF Serif CJK` 收进去（news-policy 5 个版式已在用，裁决 7 的杂志族也必需）。
