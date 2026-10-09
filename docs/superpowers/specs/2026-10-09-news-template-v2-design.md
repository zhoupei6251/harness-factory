# 新闻域模板 v2 设计（31 套同等质量 · 原语库 + 配方编译 · 字幕进体系）

> 日期：2026-10-09 ｜ 状态：设计已批准，待用户复审 → 转实施计划
> 路线：方案 B（视觉原语库 + 风格 spec 编译）；方案 A（token 注入）与方案 C（31 套全手工）已否决
> 上游背景：`skills/douyin-pro/templates/hyperframes_path_b/`（现存 31 包；原 32 包，2026-10-09 删 `news-coral-night`，理由见裁决 15 与 `routes/news/ARCHITECTURE.md` D23）、`routes/news/pack-decision.md`（12 体裁路由）
> 关联：提速设计 `2026-10-09-news-render-speedup-design.md`（本设计不得使单条摊薄时长退化超过其阈值）

---

## 1. 目标与验收口径

**目标**：把新闻域出片的视觉水位从"模板感/PPT 感"提升到"信息流原生、能打完播率"的水平，产出 **31 套同等质量、每套都能独立上片**的模板包。

**验收口径（全部可机判，除第 1 项）**：

| # | 判据 | 口径 |
|---|---|---|
| 1 | 审美水位 | **人工判断**：P1 旗舰包出帧，与老包**同稿并排**比对，用户认可后放行 |
| 2 | `hyperframes check --strict` | 全绿，零违规 |
| 3 | 编译前色对预校验 | spec 声明的每个文字/底色对 WCAG 达标（正文 4.5 / 大字 3.0），不过即拒编 |
| 4 | 确定性 | 同稿渲染两次，`final.mp4` 哈希一致 |
| 5 | 区分度门禁 | 任意两套之间，`grid.grammar` / `type.display` / `motion.signature` / `color.value-ladder` 四项**至少两项不同** |
| 6 | 渲染时长 | 以提速项目所立 `timing.json` 基线为准；旗舰包单条摊薄 > 基线 ×1.5 → 停止并回报 |
| 7 | 合规门禁 | 含可辨认人脸的图不得进入首镜 / closer / 人物镜 / 含专名镜 |

**判据 5 是这份设计里最重要的一条新增**。它把"别做成模板感"从主观愿望变成一个编译期可拒的断言——31 套塌回一套，历史上发生过（见 §3），必须有闸。

## 2. 非目标（本轮不做）

- **不做真实素材源接入**（正版图库 API / AI 生图 / 人工传图）。本轮只在 Commons 现状下把图降级为纹理 + 加合规门禁。
- **不动 AIGC 角标**。它的 5% 最短边字高有实测字面率 0.729 校准（`aigc_badge_font_size`），迁进 HTML 等于重做一遍已通过的国标验证，纯亏。
- **不改 `hyperframes` 引擎本身**。`check --strict` 是外部黑盒，我们只适配它。
- **不做老包升级**。现存 31 包整体归档（原 32，删除见裁决 15），新体系另落 `hyperframes_path_c/`。
- **不引入 GSAP 插件**（见裁决 10）。

## 3. 现状诊断（实测证据，非印象）

> **测量时点**：下表全部数字取自 32 包状态（2026-10-08/09）。2026-10-09 删掉 `news-coral-night` 后现存 31 包（裁决 15 / D23）。**删除后复跑 `audit_pack_contrast.py`：仍是 24 条 OFF_PALETTE_HEX、仍是同样 10 个包**（与 D19 记的 32 包基线同数，且被删的包不在其中），所以下表 D1/D2 的结论不因删除而失效 —— 被删的那个包恰好是"零独有色"的，删除只会让同质化判断更成立，不会更弱。

| # | 缺陷 | 证据 |
|---|---|---|
| D1 | **32 包共用同一个红**，连色都没换，只是换布局名 | `audit_pack_contrast.py:104` 实测：`#e85d5d` 在 32 包色板声明中出现 **32** 次、`#c0392b` **41** 次、`#d44a4a` **34** 次。同脚本 `:84` 给了更硬、不可辩驳的口径：**`#e85d5d` 命中 12/12 个 master 包色板**（作主强调）。注意前者数的是"声明次数"（一包多 token 可指向同色，故 >32 正常），只能看量级；后者才是"每包都有"的证据 |
| D2 | **同质被工具链制度化** | `SHARED_TOKEN_MIN_PACKS = 6`（D18, 2026-10-08）把 18 个色值提升为跨包共享层，`OFF_PALETTE_HEX` 从此放行。止血决策正确，副作用是审计器改为保护同质 |
| D3 | **动效词汇只有一个动作** | 7 版式全用 `scaleX/scaleY` 擦入 + `yPercent:-3` 漂移；`hook.html:224` 的逐字入场注释记录的是 `onStart` 里 split + `tl.from` —— **`onStart` 在 seek 时不触发、`from` 违反"一律 fromTo"**，该方案在 seek 模型下必然失步，撤掉是对的 |
| D4 | **首镜用真人照片构成错误指认** | `t001-v10/media-credits.json`：湖南常德拾荒者新闻的首镜满屏图 = 巴西累西腓拾荒者（`Wilfredor`/CC0，`relevance: 2`），**面部清晰可辨**；另三镜为废弃水泥厂齿轮（`relevance: 2`）、意大利造纸回收（`relevance: 1`）、智能手机（`relevance: 1`） |
| D5 | **字幕不在设计体系内**，且设计体系在为它让位 | `path_b_build.py:366-369` 静态 ASS（`h/32`=60px、描边 3px、两行封顶），ffmpeg 在 HyperFrames 之后烧；`frame.md` 法则 1 的底部 20cqh 禁入区 = 给未设计图层让位 |
| D6 | **色相打架** | `t001-v10` 抽帧第 1 格：蓝色火带与珊瑚红眉标片同框，两个高饱和无关色对撞。WCAG 审计管明度不管色相关系 |
| D7 | **中文只有一把 sans**，"杂志感"无从落地 | `frame.md §2` CJK 固定 `HF CJK`（Noto Sans SC）。而 `typography.csv` 中 `Chinese Traditional` / `Japanese Elegant` / `News Editorial` / `Magazine Style` / `Editorial Classic` **五条独立记录一致推荐衬线标题** |

## 4. 已锁裁决

| # | 裁决 | 依据 |
|---|---|---|
| 1 | 业务基准 = **信息流原生 + 完播率优先** | 用户选定 |
| 2 | **字幕收进 HyperFrames** 成为一级公民；AIGC 角标留 ASS | 用户选定 |
| 3 | **排版/图形为王，图只做纹理**（不追求电影感纪实） | 用户选定；且 D4 使满屏纪实路线不可信 |
| 4 | 架构 = **原语库 + 配方编译**（方案 B） | 31 套同等质量只有生成式系统能满足 |
| 5 | 规模 = **31 套 = 9 族 × 变体**，同等质量全可上片 | 用户硬性要求 |
| 6 | **族 = 版面语法差异；变体 = 语法内参数差异** | 反"模板感"的结构性保证 |
| 7 | **思源宋体进 CJK 族集合** | `NotoSerifSC-VF.ttf` 已装于 `C:\Windows\Fonts`，OFL 免费商用；D7 |
| 8 | **街采族保留，排在 P5 末位** | 手绘感参数化过头会退化为"卡通"，须待原语库被前八族磨稳 |
| 9 | **瑞士族 `drift: none` 例外**；`MIN_DRIFT` 由全局铁律降为族级默认值 | 该族性格即"不动的权威感" |
| 10 | **零 GSAP 插件依赖** | 见 §6.2；`RoughEase` 不在 CDN（404）且其内部随机本就摧毁确定性 |
| 11 | **审计上移到编译前**；事后审计降级为编译器回归测试 | `contrast_ratio()` 数学已在 Python（`audit_pack_contrast.py:155-177`），非重写。这是"审计只抓人、不抓编译器"的时序问题的解 |
| 12 | **`SHARED_TOKENS` 清空**：族间共享**角色**，不共享**色值** | D1/D2 |
| 13 | **强调色的明度是族级参数**（号外 `#DC2626` / 杂志 `#B45309` / 竞技 `#EF4444` / 警示 `#7F1D1D`） | `colors.csv` News/Media 推荐 `#DC2626`；现用 `#E85D5D` 是抬明度后的 breaking red，抬明度＝降冲击 |
| 14 | **双轨目录** `templates/hyperframes_path_c/`，老包原地归档 | `path_b_build.py` 2637 行同时服务产线；且新旧并存才能同稿并排判水位 |
| 15 | **老体系先减到 31：物理删除 `news-coral-night`**（2026-10-09 已执行，记录见 `ARCHITECTURE.md` D23） | 判据是"删掉后能力不减"，三条可复算：① 按 frame.md 色板 token 表算**独有色 = 0**（全库仅 4 个包为 0，另 3 个是 master，其中 `news-coral` 还是 `DEFAULT_STYLE`）；② 它的 13 色是其余 19 个包色板的**真子集**，即它没给系统带来任何一个色；③ 暗底能力由同派生的 `news-dusk`(`#7c3aed`) / `news-noir`(`#080808`) 承接，且 `news-dusk` 本来就在人物/故事的 `secondary` 里。反证也已记：`t001-v8` 用它真出过片，但删模板不动历史成片 |

## 5. 9 族 / 31 套

切法：**族 = 网格语法 + 字体角色 + 动效词汇表**；变体 = 同语法内的色相关系、字重档、纹理密度。

| 族 | 网格语法 | CJK 标题 / 正文（本地已装） | 拉丁位（引擎自动供给） | 动效签名 | 禁忌（≥3，编译期断言） | 变体 |
|---|---|---|---|---|---|---|
| 号外 Neubrutalism | 粗黑描边包幅 + 45° 硬阴影 + 字压线 | 汉仪中黑 900 / 等线 | `Space Mono`·`Bebas Neue` | `expo.out`+`none`，`back.out(2.8)` 过冲，≤0.9s | 禁 fade；禁 `sine/power2`；禁 >1s 入场 | 4 |
| 杂志 Editorial | 非对称栏 + 首字下沉 + 大负空间 | **思源宋体 900** / Noto Sans SC 400 | `Libre Bodoni`·`Newsreader` | `clip-path` 遮罩上涌 + 逐字 `y:14→0`，1.4s | 禁一切过冲；禁 <0.5s 入场；禁圆角 | 4 |
| 数据 Data-Dense | 数字主角 + 网格底纹 | Noto Sans SC 900 / 400 | `Fira Code`·`League Gothic` | 条形 `scaleX`、折线 `strokeDashoffset`、数字滚动 | 禁装饰动效抢数字；禁 >2 元素同动；禁假比例 | 4 |
| 街采 Anti-Polish | 手绘圈注 + 故意不对齐 | 等线 700 / 等线 | `Caveat`（仅批注） | `strokeDashoffset` 圈注生长、马克笔带 ±1.5°、烘焙手抖 | 禁完美对齐；禁 `ease:"none"` 匀速；禁对称 | 3 |
| 胶片 Vintage Analog | 颗粒 + 漏光 + 暗角 + 白边 | **思源宋体 700** / Noto Sans SC | `Abril Fatface`（仅 hero） | 遮罩 + 颗粒 opacity 抖 + zoom 1.02→1.06 | 禁现代 UI（圆角·阴影·chip）；禁 >1 高饱和色 | 3 |
| 霓虹 Cyberpunk | 扫描线 + RGB 三层分离 | 奇黑 900 / Noto Sans SC | `JetBrains Mono`·`Chakra Petch` | `steps(n)` 主导 + 打字机 | 禁平滑长曲线；禁暖色；禁 fade | 3 |
| 瑞士 Swiss | 严格 12 栏 + 大留白 | Noto Sans SC 900 / 400 | `Inter` + `Inter` | 仅 `opacity` + `y:8`，8px 节拍 | 禁装饰动效；禁过冲；**禁漂移**（裁决 9） | 3 |
| 竞技 Vibrant Block | 撞色块 + 记分牌 | 奇黑 900 / Noto Sans SC | `Russo One` | 对角擦入 + 数字翻滚 + 烘焙纸屑，≤0.6s | 禁任何 >0.8s 动作；禁慢入场；禁 serif | 4 |
| 图解 Bento/Schematic | 模块卡 + 分步流程 | Noto Sans SC 700 / Noto Sans SC | `Space Grotesk`·`DM Sans` | 卡片 `back.out(1.7)` + `clip-path` 插值 + 箭头 | 禁步骤同时出现；禁无出处比例 | 3 |

合计 **4+4+4+3+3+3+3+4+3 = 31**（按上表「变体」列自上而下求和；任一族变体数改动须重算此式，且不得改总数 31）。

**字体策略的结构性不对称**（决定上表分工）：`frame.md §2` 已 probe 验证 **CJK 只能 `local()`**（引擎字体缓存无 `noto-sans-sc`，加 `local()` 反而使自动下载失效），而**拉丁族写裸名即由引擎自动供给**。故 CJK 选择锁死在已装集合、承担语义；拉丁侧无上限、只做数字/眉标/点缀。

两条库内警告带走：`Bebas Neue` 是 all-caps 显示族，中文无大小写 → 只能待在拉丁位；`Caveat` 库内自注 "use sparingly for accents"。

## 6. 组件设计

### 6.1 组件 ①：风格 spec 语言（`schema: hf-style/1`）

每套 = 一份 YAML，七层：`grid` / `type` / `color` / `motion` / `subtitle` / `layouts` / `taboos`。

**立场：spec 声明结构，不只声明值。** 只装 token 的 YAML 就是被否决的方案 A。

关键项：
- `grid.grammar` —— **有限集**，编译器按名取骨架，不允许自由发挥
- `color.saturation-budget` —— `{max-hues-per-frame: 1, accent-min-S: .45, support-max-S: .15}`，直接治 D6
- `color.value-ladder` —— 明度阶梯，"看起来像什么"由它决定，不是色值表
- `color.accents[].role` —— `shape-only` / `shape-or-large-text`，是现有法则 L1/L2 的泛化
- `motion.easing.forbidden` + `taboos[]` —— 禁忌必须是**可执行断言**（裁决见法则 13）
- `grid.safe.bottom: auto` —— 由 `subtitle.position` 反算，D5 的根治

### 6.2 组件 ②：视觉原语库（44 个，三档）

原语是 **Python 函数**（不是 HTML 串），因为法则 10 要求随机在编译期烘焙。每个原语声明**前置条件**而非只有参数：

```
ground: ink|paper|any · requires: [solid-ground] · seek_safe: by-construction
contrast: inherits|self-proofs|requires-chip · budget: {paint, frames}
```

- **P0 · 12**：`clip-wipe-up` `char-rise` `rule-pull` `block-chip` `hairline` `giant-numeral` `photo-duotone` `photo-local-crop` `ken-burns-in` `drift-y` `cue-fade` `keyword-tint`
- **P1 · 18**：破格斜切、半调网点、扫描线、胶片颗粒、暗角呼吸、竖排大字、编号水印、首字下沉、条形生长、折线绘制、数字滚动、对比标尺、RGB 分离、glitch 烘焙、霓虹描边、视差分层、纸屑、示意标注
- **P2 · 14**：手绘圈注、马克笔高亮、胶带条、贴纸倾斜、手绘箭头、涂改线、遮罩局部显影、色键混合、进度脊、环形弧、迷你趋势、括号框、打字机、过曝闪

**零插件替代方案**（裁决 10）：逐字 = 构建期按码点切 span；圈注 = SVG `pathLength="1"` + core `attr:{strokeDashoffset:1→0}`；打字机 = 构建期切 span 逐个 `opacity`；纸屑 = 构建期烘焙抛物线关键帧；形状变形 = `clip-path` 顶点插值（唯一有画质让渡项）。理由：`19be62b` 刚为"每次 npx 重装"踩过坑，多一个 CDN 就多一个离线故障面；插件重建 DOM 与 `data-var-text`/`getVariables()` 注入顺序耦合；构建期烘焙天然满足法则 10。代价：多约 200 行 Python。

### 6.3 组件 ③：编译器

`spec.yaml` → 7 版式 HTML + 字幕轨 composition + **frame.md（降级为编译产物）**。

顶部标注 `# 本文件由 styles/<id>.yaml 编译生成，勿手改`。**真源上移到 YAML**，`frame.md` 的"唯一 token 源"地位让位。

**版式名不变**（`hook/stat/rail/quote/catalog/story/closer`）—— 这是发射器与版式之间唯一的契约面，`MOUNT_TPL`、`data-composition-variables`、`choose_layout()` 全部原样可用。**本设计最大的降风险项。**

### 6.4 组件 ④：字幕轨（cue 驱动）

**更正记录**：本设计早期判断"真逐词数据已在管线里"**错误**。实测 `scene_1.vtt` 整镜仅一条 cue（`00:00:00,100 --> 00:00:06,187`）——CLI 默认走 `SentenceBoundary`。

修法：`edge_tts` 7.2.8 的 `TTSConfig` 支持 `boundary="WordBoundary"`（`communicate.py:335`）。`synthesize_audio`（`path_b_build.py:2073`）从 shell 调 CLI 改为调 Python API；`doctor` 门禁项由"可执行定位"换成"可 import"。

- **挂载**：每镜一个字幕 composition，挂最高 track（与 `MOUNT_TPL` 同构、失败隔离）。不用全片常驻层。
- **时基**：发射器负责 `+data-start` 平移；composition 内部只见 `0..slotSeconds`。
- **入退场**：每词两个 `fromTo`（`opacity 0→1` 落在词 start，`1→0` 落在 end）。均 seek 可回退。字幕轨是**唯一允许退场的层**（法则 14），且纯墨无底色面，不触法则 8。
- **强调匹配**：`onscreenAccent` / `｜` / "数字+单位" 三源改为与 words 数组**精确子串匹配**；匹配不上即不高亮，**禁止按比例猜**（与法则 5 同立场）。
- **降级**：WordBoundary 依赖微软服务，失败时**只降级时序**（按字符数比例分配每个词的 start/end），**不降级"哪个词被强调"**——强调仍走精确子串匹配，匹配不上就不高亮。两处"比例"的口径不同：前者是无外部时序数据时的兜底切分，后者是被明令禁止的猜测（法则 5）。解析结果**必须落盘 `cues.json` 进 work_dir 当可复现输入**，重跑读文件不重问服务——否则两条路径时序不同会破坏"同稿同片"。
- **禁入区协商**：`grid.safe.bottom` 由 `subtitle.position` 反算；但抖音右侧点赞栏要求左右各留 6%，此宽度约束硬，与字幕归谁渲染无关。

### 6.5 组件 ⑤：图片门禁与纹理化

**门禁实现（本地零网络，已实测）**：`{frontalface_alt2, profileface} × {原图, 水平镜像}` 四通道并集，`minNeighbors≥3`、`minSize≥24px`。

实测分离度：s1（累西腓拾荒者，侧脸朝左）`profileface` 命中 `(118,188,52×52)`；镜像后 `frontalface_alt2` 命中 ×2；s2（齿轮）**四通道全零**。
**禁用 `frontalface_default`（齿轮图误报 4 个）与 `upperbody`（误报 7 个）** —— 锈螺栓圈被当正脸。

**asset_grade 三档**：
- **G0 可指认** —— 任一通道命中人脸（s1 在此）
- **G1 场景可推断** —— 无人但场景具指认性
- **G2 纯材质** —— 纹理/特写（s2 在此）

**硬规则**：
1. **G0 禁入首镜、closer、人物镜、含专名镜**；首镜是"暗示这是谁"的最强位置
2. G0 要用只能裁掉人脸连通域后**复检**，仍命中则弃用
3. 检测器不可用/超时 → **一律降级为 G0**（宁可少用图，不可错指认人）
4. **首镜改为排版主导**，图库照片不进首帧（推翻现有 `.hk-photo` 满屏设计）

**纹理化强度按 grade**：G2 可满屏 + duotone 压向族色 + S<0.15；G1 强制裁到 25–35% 局部以失去场景指认；G0 默认不用。

**「示意画面」强制标注**：左下、安全区内、z 高于所有原语（禁止被任何入场元素遮挡）、等宽 2.0cqw、字距 .08em、大字档 ≥3:1。第一行 `示意画面 · 与报道对象无直接关联`，第二行降为附属的版权署名（现有 credit 视觉上像权威背书，其实是免责信息）。**凡 `grade != real` 一律强制，无例外无开关。**

一个机制解决三个问题：大裁切 + 强压色 → 图失去指认性（合规）、不再抢文字戏（审美）、同图反复用于同选题也不被察觉（观感）。

### 6.6 组件 ⑥：审计与门禁改造

| 位置 | 现状 | 改为 |
|---|---|---|
| `audit_pack_contrast.py:110` `SHARED_TOKENS` | 18 个色值跨包共享白名单 | **清空**（裁决 12）；改为共享角色不共享色值 |
| `audit_pack_contrast.py:56` 表头指纹 + `parse_palette():212` | 从 frame.md 解析 markdown 表取色板 | 改读 spec；表仍生成供人读。**新增编译前入口**调 `contrast_ratio()` 预校验，不过即拒编 |
| `layout_selfcheck.py:43` `CAPTION_RESERVE_CQH=20.0` | 写死 | 从 spec `subtitle.position` 反算 |
| `layout_selfcheck.py:49` `BUDGET_CONSTANTS` | `MIN_DRIFT` 全局 | 族级默认值；瑞士族 `drift:none` 走例外表 |
| `layout_selfcheck.py:55` `CJK_FAMILY` | **单数字符串** `"HF CJK"` | **必须改成集合**，否则思源宋体一进 `@font-face` 审计就挂 |
| `layout_selfcheck.py:52` `CANONICAL_LATIN_FAMILIES` | 3 个拉丁族 | 扩充；拉丁侧仍走裸名自动供给 |

**新增检查**：
- 法则 10 静态检查：生成 HTML 里出现 `Math.random(` 即失败
- 法则 11 配额：`filter: blur(` 元素数 × 覆盖帧数 超 `≤2 / ≤40%` 拒编
- 饱和预算：从 hex 算 HSL 的 S，数每版式高饱和 accent 数，超 `max-hues-per-frame` 拒编
- **区分度门禁**（验收判据 5）：任意两套四项至少两项不同
- **确定性哈希门**：同稿两渲比对 mp4 哈希 —— 唯一能证明法则 10 真守住的手段

烧录后的 `check --strict` 与事后审计**保留**，语义降级为**编译器回归测试**（抓编译器自己写跑偏，不再抓人）。

### 6.7 组件 ⑦：路由改造

`routes/news/pack-decision.md` + `routes/news/scripts/decide_pack.py`：12 体裁 → 9 族 × 变体的决策表。体裁映射见 §5 表；同族多变体按情绪/昼夜/强弱选。

## 7. 新增版面法则（10–14）

- **法则 10 · 构建期随机一律禁用。** 同一 page load 内 seek 稳定，但**跨渲染会变**，两次跑同稿出两支片子即作废"确定性 MP4"。所有随机值由 `seed = hash(norm_key)` 的 PRNG 在**编译期**烘焙成常量关键帧。
- **法则 11 · `clip-path` 是 `opacity` 的合法替身，`blur` 要配额。** 法则 8 禁的是"带底色面块用 opacity"（α≈0.72 混色 → 2.5:1 不过审）；`clip-path: inset()` 不改几何不混色，完全合规。`filter: blur()` 每帧重算，配额 `≤2 元素 / ≤40% 帧`。
- **法则 12 · `onUpdate` 写 DOM 允许，禁累积状态。** 数字滚动走 `fromTo` 到代理对象 + `onUpdate` 回写 `innerHTML`，seek 会重放故安全；但累加计数器会失步。
- **法则 13 · 每族必须声明 ≥3 项禁忌，且为编译期断言。** 31 套会不会长成一套，取决于禁忌有没有写死。差异靠"这族不许干什么"守，不靠"我想不一样"。
- **法则 14 · 字幕轨是唯一允许退场的层。** 它承载瞬时信息，cue 结束必须消失；纯墨无底色面故不触法则 8。

## 8. 阶段 0 · 四个探针（先拿结论，不保留代码）

| # | 探针 | 若失败的后果 |
|---|---|---|
| P0-1 | 构建期切 span + `fromTo` 逐字，seek 抽帧比对稳定性 | 逐字入场不可用，杂志族招牌手法要换 |
| P0-2 | `clip-path` 在 `check --strict` 下是否报 `container_overflow` | 杂志族与胶片族招牌手法要换替身 |
| P0-3 | **edge-tts 中文 `WordBoundary` 返回词还是字** | 若是字级，逐词高亮需在发射器侧做词组聚合；**§6.4 全部成立与否取决于此** |
| P0-4 | 同稿两渲哈希基线（**改造前测**） | 若现在就不一致，"确定性 MP4"本身是坏的，与本设计无关但更该先修 |

**决策门**：P0-3 与 P0-2 任一失败 → 停止实施、回报用户、回 §5 调整对应族签名。不硬做。

## 9. 排期

1. **P0** 四探针（§8）
2. **P1 旗舰包 = 决策门**：12 个 P0 原语 + 编译器最小版 + **杂志族·暖纸**一套 → 出片 → **与老包同稿并排，用户看帧判定**。不认可即停在此处，损失只有 P1
3. **P2** 字幕轨（WordBoundary + `cues.json` 落盘 + 禁入区反算）
4. **P3** 图片门禁（四通道 + grade + 纹理化 + 示意标注）
5. **P4** 审计上移（编译前预校验 + 5 道新检查 + 确定性哈希门）
6. **P5** 铺 31 套，族顺序：**杂志 → 号外 → 数据 → 瑞士 → 竞技 → 图解 → 霓虹 → 胶片 → 街采**。每族先出 1 个变体验收，再铺同族其余变体

## 10. 待决项

| # | 事项 | 说明 |
|---|---|---|
| Q1 | ~~老 32 包是否物理删一个~~ **已决（2026-10-09 执行完毕）** | 删 `news-coral-night`，老体系 32 → **31**，与新体系套数对齐。判据与影响面见裁决 15 和 `ARCHITECTURE.md` D23；`path_b_selftest` 86/86、`curate_selftest` 33/33、`layout_selfcheck` 227 文件 0 违规、`audit_pack_contrast` 24 条与删除前同数（D19 的刻意保留项，未受影响） |
| Q2 | `grid.grammar` 有限集的具体成员 | 9 族各一个骨架？还是族内变体共用？P1 编译器最小版必须先定，否则区分度门禁（判据 5）无从计算 |
| Q3 | 变体的区分轴是否够 | 同族 4 变体若只靠色温/字重，是否仍会显同质感？P1 验收时一并判定 |

## 11. 风险与已知张力

- **本设计的成败不在编译器，在原语库的审美水位。** 编译器只忠实展开写进去的东西；原语平庸则 31 套平庸 31 次。所以 P1 是决策门而非进度点。
- **渲染时长与审美直接对撞。** 提速项目刚把单条压进 3 分钟，而 `blur`、大面积 `clip-path`、逐字 span 带来的 DOM 节点膨胀都是每帧成本。`budget` 字段与验收判据 6 是为此而设，不是装饰。
- **`SHARED_TOKENS` 清空会让 `OFF_PALETTE_HEX` 违规量反弹。** D18 那次是 561 条。这次必须**逐包按族重新声明色板**，不能靠机械重映射——`audit_pack_contrast.py:88-91` 那段教训（"审计的判据要跟设计意图一致，不为了让工具变绿而毁掉产物"）照搬有效。
- **人脸检测不是充分条件。** 指认性还有地标、品牌 logo、门牌招牌文字，以及"同图反复出现在同选题"。本轮只解人脸这一维，其余靠 §6.5 的纹理化间接消解（大裁切 + 强压色使图不可识别）。地标/logo 检测列为后续迭代。
- **`WordBoundary` 依赖外部服务**，与"本地零网络"的门禁设计（§6.5）方向相反。`cues.json` 落盘是唯一把外部不确定性变成可复现输入的手段，必须做。
- **`CJK_FAMILY` 单数常量是本设计唯一的静默阻断点**：不改则思源宋体一进 `@font-face` 就挂审计，且失败信息不指向真因。排在 P1 之前完成。
- **人工审美验收不可自动化。** 判据 1 明确标为人工判断；其余六项全部机判。别把"好看"写进断言里自欺。
