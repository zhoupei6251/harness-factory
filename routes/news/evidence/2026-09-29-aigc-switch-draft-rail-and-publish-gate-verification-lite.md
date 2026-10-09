# 2026-09-29 · AIGC 标识的开关按层落地（草稿轨 `--draft` + 发布闸门 `check_publishable.py`）—— 验证记录（lite）

**范围**：给"内容由AI生成"这件事加**两层开关**——渲染层 `path_b_build.py --draft`、发布层
`check_publishable.py --allow-undeclared`——并把默认值定回**三件全开**（用户同日口径：
先要"默认关掉"，随后改口"那还是默认都打开吧"）。开关的代价设计是：**关完之后这份东西发不出去**，
而不是"发出去但没标"。
**不含**新的新闻成片（用 5 镜 news-policy 版式探针，探针文案是占位的，`请勿发布`）。

结论：**两条轨都在同一台机器、同一份 fixture 上验过；草稿轨被闸门拒绝（EXIT=1）且 `ffprobe` 里
确实查不到 `AIGC` 键；交付轨闸门 EXIT=0 且角标三项几何在真像素上复现。**
过程中查出两处真缺陷：① 版本管理里的探针 fixture 原本是发射器的**产出**形态，照文档命令重跑必停；
② `verify_aigc_badge.py` 的时序基准用裸 `silent.mp4`，把**字幕像素**当成了角标（窗口外实测虚高到 8.5%）。

---

## 1. 被验对象

```
skills/douyin-pro/scripts/check_publishable.py   ★ 新增：发布闸门（纯判据 check() + CLI）
skills/douyin-pro/scripts/path_b_build.py        --draft 帮助文本订正；草稿轨台账只留 draft 一段
skills/douyin-pro/scripts/verify_aigc_badge.py   时序基准改为"同刻重烧无 AIGC 条 ASS"；空档判失败
skills/douyin-pro/scripts/fixtures/badge_probe_shots.json
                                                 ★ 订正：从"产出形态"重写为合法**输入**（5 镜）
skills/douyin-pro/scripts/path_b_selftest.py     66 项（+草稿轨 1 项、+发布闸门 2 项）
routes/news/{ARCHITECTURE,MEMORY}.md             D11 决策 · §2 流程加 Step 4.5 · §3 树 · §8 实测
skills/news-workflow/SKILL.md                    步骤 4 草稿轨 · 步骤 5 前置闸门 · 硬规则 6/7
skills/douyin-upload/SKILL.md                    三件套表加"命令先由闸门给"
```

## 2. 命令与实测输出（仓库根执行）

**机器前提**：`npx -y hyperframes` 要 **Node ≥ 22**。本机 nvm 默认曾指向 20.9.0，此时渲染第 5 步
`hyperframes check --strict` 只产出空 `check.json` + `HyperFrames requires Node.js >= 22`，
表现为"门禁未通过"，其实是运行时版本问题。下面的渲染命令都带 PATH 前缀（**没有**跑 `nvm use`，
那是机器级副作用、不在本次授权范围）：

```bash
export PATH="/d/Users/zhoupei/AppData/Local/nvm/v23.11.1:$PATH"   # git bash 写法
```

### 2.1 三道闸（改动后复跑，全绿）

```bash
python skills/douyin-pro/scripts/path_b_selftest.py
python skills/douyin-pro/scripts/audit_pack_contrast.py
python skills/douyin-pro/scripts/layout_selfcheck.py \
    skills/douyin-pro/templates/hyperframes_path_b/news-coral \
    skills/douyin-pro/templates/hyperframes_path_b/news-policy
```

```
  ok    t_draft_badge_absent_but_subtitles_kept
      可渲染 pack (有真版式): 2/12 —— news-coral, news-policy
  ok    t_full_loadability_progress
  ok    t_publish_gate_default_requires_declaration
  ok    t_publish_gate_refuses_draft_and_missing_sidecar
  ok    t_aigc_badge_sits_in_the_gap_between_content_and_subtitles
  ok    t_aigc_badge_landscape_band_yields_to_subtitles
[selftest] 全绿 66/66
对比度审计通过：12 个 pack 的 frame.md 色板与文档一致（0 条警告）
版式自检通过：12 个文件，0 条违规
```

（项数 66 由脚本自己打印 —— 文档不抄数，`path_b_selftest.py` 按 `t_` 前缀自动收集，加一条断言就涨一项。）

### 2.2 交付轨（默认，不带 `--draft`）

```bash
python skills/douyin-pro/scripts/path_b_build.py \
    --input skills/douyin-pro/scripts/fixtures/badge_probe_shots.json \
    --template news-policy --source 版式探针 \
    --work-dir .harness-news-runtime/tmp/switch-live/work \
    --output .harness-news-runtime/tmp/switch-live/final.mp4
```

台账 `.harness-news-runtime/tmp/switch-live/aigc.json`（逐字）：

```json
{
  "file": "final.mp4",
  "metadata_key": "AIGC",
  "implicit": {
    "AIGC": {
      "Label": "1",
      "ContentProducer": "harness-news-pathb",
      "ProduceID": "f3a4c8487d55d86eafe6956138aa020f",
      "ReservedCode1": "9ce34f147fc925b9137a5b9c7685391aa6057e6e",
      "ContentPropagator": "",
      "PropagateID": "",
      "ReservedCode2": ""
    }
  },
  "explicit": {
    "text": "AI 生成合成内容",
    "position": "bottom-left",
    "font_size_px": 75,
    "glyph_height_px": 54.7,
    "short_side_px": 1080,
    "margin_v_px": 303,
    "shown_seconds": 4.0,
    "burned_in": true
  },
  "resolution": "1080x1920"
}
```

闸门与像素复测：

```bash
python skills/douyin-pro/scripts/check_publishable.py .harness-news-runtime/tmp/switch-live/final.mp4
python skills/douyin-pro/scripts/verify_aigc_badge.py \
    --work .harness-news-runtime/tmp/switch-live/work \
    --video .harness-news-runtime/tmp/switch-live/final.mp4
```

```
✅ ①② 齐活: final.mp4
   ① 角标 AI 生成合成内容 · bottom-left · 字芯 54.7px / 最短边 1080px · 4.0s
   ② 元数据键 AIGC · Label=1
③ 必须带: --declaration 内容由AI生成
   成功凭据 = 日志出现「自主声明已选择「内容由AI生成」」, 没有这行按未声明处理
   发布命令: sau douyin upload-video --account <账号> --file .harness-news-runtime/tmp/switch-live/final.mp4 --title … --desc … --tags … --declaration 内容由AI生成
EXIT=0
```

```
[aigc_badge] 成片 final.mp4 1080×1920 · 43.0s (silent 43.0s)
[aigc_badge] ASS: 字号 75 描边 5 阴影 1 对齐 1(1=左下) MarginL 48 MarginV 303 窗口 0.00–4.00s

[1 字芯] 白色像素 x 49–465=417px · y 1555–1609=55px
[1 字芯] 最短边 1080 的 5.09% | 5% 线 54.0px
[1 字芯] 距左 49px = 4.54cqw(ASS MarginL 48 → 模型 48px) | 距底 310px = 16.15cqh

[2 几何] 实测墨迹(含描边阴影) x 43–472 · y 1549–1615 = 67px
[2 几何] 模型 ink_bounds(mv=303) = 1549.3–1615.0 | 上侧差 0.3px 下侧差 0.0px

[3 时序] 基准 = silent 同刻帧重烧「无 AIGC 条」ASS vs 成片 · bbox (43, 1549, 473, 1616) = 28810px
       时刻 |    bbox 差异 |      占比 | 判定
t=   0.20s |      22061 |   76.6% | 角标在  ✓
t=   2.00s |      22063 |   76.6% | 角标在  ✓
t=   3.85s |      22061 |   76.6% | 角标在  ✓
t=   4.20s |          0 |    0.0% | 角标不在  ✓
t=  23.50s |          3 |    0.0% | 角标不在  ✓
t=  42.81s |          0 |    0.0% | 角标不在  ✓

[aigc_badge] ✓ 三项全过: 字芯 55px(5.09% ≥ 5%) · 墨迹与模型逐侧 ≤1.5px · 角标只在开场 4.0s 出现
EXIT=0
```

### 2.3 草稿轨（`--draft`）

```bash
python skills/douyin-pro/scripts/path_b_build.py \
    --input skills/douyin-pro/scripts/fixtures/badge_probe_shots.json \
    --template news-policy --source 版式探针 --draft \
    --work-dir .harness-news-runtime/tmp/switch-draft/work \
    --output .harness-news-runtime/tmp/switch-draft/draft.mp4
```

台账 `.harness-news-runtime/tmp/switch-draft/aigc.json`（逐字 —— **没有** `explicit` /
`metadata_key` / `implicit` 三段，缺什么记什么缺）：

```json
{
  "file": "draft.mp4",
  "draft": {
    "reason": "--draft 草稿渲染: ① 画面角标与 ② 隐式元数据都没有",
    "burned_in": false,
    "to_publish": "去掉 --draft 重渲一次, 让 ①② 落进成片"
  },
  "resolution": "1080x1920"
}
```

三份独立凭据（闸门、文件元数据、像素）：

```bash
python skills/douyin-pro/scripts/check_publishable.py .harness-news-runtime/tmp/switch-draft/draft.mp4
ffprobe -v error -show_entries format_tags -of default=noprint_wrappers=1 .harness-news-runtime/tmp/switch-draft/draft.mp4
python skills/douyin-pro/scripts/verify_aigc_badge.py \
    --work .harness-news-runtime/tmp/switch-draft/work \
    --video .harness-news-runtime/tmp/switch-draft/draft.mp4
```

```
❌ 拒绝发布 draft.mp4:
   · 这是 --draft 草稿(① 角标与 ② 元数据都没写), 不得发布 —— 去掉 --draft 重渲一次, 让 ①② 落进成片
EXIT=1
```

```
TAG:minor_version=512
TAG:major_brand=isom
TAG:compatible_brands=isomiso2avc1mp41
TAG:hyperframes_version=0.8.91
TAG:hyperframes_renderer=hyperframes
TAG:encoder=Lavf62.8.102
```

（对比交付轨的同一命令：`TAG:AIGC={"AIGC":{"Label":"1","ContentProducer":"harness-news-pathb",…}}`）

```
[aigc_badge] 成片 ASS 里没有 AIGC 事件 —— 显式标识根本没烧, 不必再量像素
EXIT=1
```

草稿轨**只**少了 ①②：字幕照常烧（`t_draft_badge_absent_but_subtitles_kept` 锁的就是"少了角标
但配音字幕还在"，用词表逐行比对 ASS 事件），所以它能用来调版式、量留白。

### 2.4 逃生门与两个负例

```bash
# A: 交付件 + --allow-undeclared（③ 可以不带，但必须警告 + 留痕）
python skills/douyin-pro/scripts/check_publishable.py .harness-news-runtime/tmp/switch-live/final.mp4 --allow-undeclared
# B: 草稿 + --allow-undeclared（逃生门救不了草稿）
python skills/douyin-pro/scripts/check_publishable.py .harness-news-runtime/tmp/switch-draft/draft.mp4 --allow-undeclared
# C: 无侧车的老成片（把交付件复制一份、旁边不放 aigc.json）
mkdir -p .harness-news-runtime/tmp/switch-nosidecar
cp .harness-news-runtime/tmp/switch-draft/draft.mp4 .harness-news-runtime/tmp/switch-nosidecar/legacy.mp4
python skills/douyin-pro/scripts/check_publishable.py .harness-news-runtime/tmp/switch-nosidecar/legacy.mp4
```

```
✅ ①② 齐活: final.mp4
   ① 角标 AI 生成合成内容 · bottom-left · 字芯 54.7px / 最短边 1080px · 4.0s
   ② 元数据键 AIGC · Label=1
⚠️  --allow-undeclared: ③ 平台自主声明不带 —— 《标识办法》§ 4-四 的「应当」里, 元数据过抖音转码即失, ③ 是唯一活到平台侧的那一件。
   请在 routes/news/MEMORY.md 的 videos[].declaration 记 undeclared, 谁决定的、什么时候, 事后能查。
   发布命令(无 --declaration): sau douyin upload-video --account <账号> --file .harness-news-runtime/tmp/switch-live/final.mp4 --title … --desc … --tags …
EXIT=0
```

```
❌ 拒绝发布 draft.mp4:
   · 这是 --draft 草稿(① 角标与 ② 元数据都没写), 不得发布 —— 去掉 --draft 重渲一次, 让 ①② 落进成片
EXIT=1
```

```
❌ 拒绝发布 legacy.mp4:
   · 没有 aigc.json —— ①② 无从谈起(无侧车的老成片一律重渲): path_b_build.py 重跑一次再发
EXIT=1
```

三条各证明一件事：A 证明 ③ 的开关**存在但要付留痕**；B 证明渲染层的开关**不能靠发布层的开关
抵消**（关过的 ①② 不会因为 ③ 也关掉就变成可发）；C 证明"没有台账"不等于"台账说没问题"——
默认拒绝而不是默认放行。C 这条输出是 `main()` 与纯函数 `check(None)` **改到同一句话**之后复跑的：
原先 CLI 打的是 `❌ 找不到台账: <路径>`，与判据函数两条措辞不一致，容易被读成两种拒绝理由。

## 3. 缺陷订正 ①：受版本管理的探针 fixture 是产出形态

`fixtures/badge_probe_shots.json` 收进去的是发射器**产出的 shots 文件**（每镜只有 `values`，
没有 `body`），而 `parse_input` 的 JSON 分支要 `body`/`text` 当配音正文 —— 照上一条记录 §2.2 的
原命令重跑，分镜 1 就停在 `分镜1 正文为空, 无话可配`。已重写为**合法输入**（5 镜显式 `layout` +
`body` 占位配音 + `items`/`onscreen`，文案全部标 `探针·` / `请勿发布`）。

角标几何与那份记录 §2.3 **逐字相同**（字芯 55px / 5.09%、墨迹 y 1549–1615 vs 模型 1549.3–1615.0、
距左 49px = 4.54cqw、距底 310px = 16.15cqh、窗口内 76.6%）—— 这些数只由分辨率与 ASS 样式决定，
与镜头时长无关。**变的是总时长**：50.0s → 43.0s，所以窗口外采样点从 `27.00 / 49.79` 变成
`23.50 / 42.81`。

## 4. 缺陷订正 ②：时序基准把字幕当成了角标

旧 §3 的基准是**裸 `silent.mp4`**（烧 ASS 之前），文档写着"差异只可能来自角标"。这句话在
43.0s 探针上不成立：角标 bbox `(43,1549,473,1616)` 落在字幕带上，`t=23.50s` 处成片与裸 silent
差 **2454 px = 8.5%**，全是那一行字幕的笔画 —— 而旧代码只按 `ratio > 15%` 判"在不在"，
8.5% 落在空档里却被打了 `✓`（脚本自己的注释写着"落进空档按失败处理"，代码没做）。

两处都改了：

- **基准改成同刻重烧**：新增 `burn_at()`，把"删掉 AIGC 条"的 ASS 烧到 `silent` 在**同一时刻**的帧上，
  两边只剩角标之差。不能先抽静帧再烧 —— 静帧输入的时间轴从 0 起算，libass 会选错字幕行
  （实测那样得到的基准帧与裸抽帧逐像素相同，等于没改）。
- **空档真的判失败**：`half = OFF_RATIO <= ratio <= ON_RATIO` 直接进 `fails`，与注释一致。

改完在同一条成片上复跑：窗口外 `t=23.50s` 从 **2454 px（8.5%）→ 3 px（0.0%）**，`EXIT=0`
（§2.2 那张时序表就是改后的完整输出：窗口内三行 76.6%，另外两个窗口外点 0.0%）。
空档分支的停机也真取到过一次（改基准前，同一时刻报
`✗ t=23.50s 差异占比 8.5% 落在判据空档 [1%, 15%] —— 角标在不在判不出来, 按失败处理`，EXIT=1），
所以"这一支会停机"不是纸面断言。旧基准下其余几行的取值未留表对照 —— 只有 `t=23.50s` 这一行
是当场逐字记下来的，其余按 §2.2 的新输出为准。

## 5. 判据与结论

| 判据 | 依据 | 结果 |
|---|---|---|
| 开关在渲染层存在 | 用户要"两个都要" | ✅ `--draft`：①② 都不做，字幕照常 |
| 开关在发布层存在 | 同上 | ✅ `--allow-undeclared`：③ 可不带，带警告与留痕要求 |
| 默认三件全开 | 用户改口"还是默认都打开吧"；《标识办法》§ 4-四 | ✅ 两个 flag 都要显式敲，不敲即全开 |
| 关标识的代价 = 发不出去 | D11 | ✅ 草稿 EXIT=1；逃生门救不了草稿（§2.4 B） |
| 台账如实（不装作"标识在只是没开"） | D11 | ✅ 草稿侧车**不含** `explicit`/`metadata_key`/`implicit` 三段 |
| ② 真的进了文件而不是只进了台账 | GB 45438-2025 附录 E | ✅ `ffprobe` 读回 `TAG:AIGC … Label":"1"`；草稿无此键 |
| ① 的几何仍达标 | GB 5% 字高 / 边角 / ≥2s | ✅ 55px=5.09% · 左下 · 窗口内 76.6%、窗口外 0.0% |
| 无台账 = 拒绝而非放行 | R6 不静默 | ✅ §2.4 C EXIT=1 |
| 三道闸仍全绿 | 硬规则 ⑥ | ✅ 66/66 · 12 pack 0 警告 · 12 文件 0 违规 |

## 6. 未验证 / 遗留代价（如实写）

① **没有真的发布**：本机抖音账号未登录（`sau douyin check` 不 valid），③ 那条命令与
   「自主声明已选择」凭据本次只在代码与文档层，未在平台侧跑通。
② 闸门本身只在**探针产物**与纯函数上验过（`t_publish_gate_*` 两条断言 + §2.2–2.4 的真实文件），
   没验过"抖音转码后元数据是否还在"—— 这一点 ARCHITECTURE D8 已按"过转码即失"记为代价，
   仍未做平台侧复测。
③ `--draft` 的**速度**收益未量化（草稿轨仍要走 TTS + HyperFrames 渲染，只是少了烧角标与写元数据；
   想快调版式应当用 `--check-only`，那是另一条既有轨道）。
④ 基准带字幕后，同一时刻两边应当**逐像素抵消**，所以窗口外读到 0 不再依赖"该时刻字幕笔画恰好
   不进 bbox"这种巧合；实测 `t=23.50s` 残留 **3px** 是两次编码的噪声（超 `PX_EPS=24` 的像素只有 3 个），
   占比 0.0%。**代价是空档停机**：以后若同刻两边字幕因编码噪声差落进 `[1%, 15%]` 就会红，
   那属于重跑可复现的抖动，不是角标掉了 —— 处理方式是多跑一次或加大采样间隔，不许调阈值。
⑤ 探针内容是占位文案，不构成新闻成片；`news-coral` 未重渲复测（同一套函数≠同一张画面）。

## 7. scratch 去向

本次的跑动产物 `.harness-news-runtime/tmp/switch-live/`（9.7MB）、`switch-draft/`（9.7MB）、
`switch-nosidecar/`（1.6MB）（各含 1 个 43.0s mp4 + 工作目录，`du -sh` 实测）在记录写完后**已删除**
—— 一次性产物按 ARCHITECTURE §6
留在忽略目录；本记录与 `badge_probe_shots.json`、`check_publishable.py`、`verify_aigc_badge.py`
是契约证据，进版本管理（本文件用 `git add -f` 拉进来，因为 §8 的复现指针指向它）。
删掉之后 §2.2 / §2.3 的命令仍可重跑（渲染会自建这两个目录），代价是要联网 + Node ≥ 22 + 每条约数分钟。
