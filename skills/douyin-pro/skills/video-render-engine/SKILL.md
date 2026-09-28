---
name: video-render-engine
description: 抖音短视频生产专家团·下游渲染层（生产级 5.1）。把中游优化好的脚本变成带 AI 配音的成片：配音层（百炼/GPT-SoVITS/VoxCPM2/CosyVoice/edge-tts 五选一，统一 dub() 接口，含免费直出）+ 渲染通道（剪映/Remotion/ffmpeg/数字人/HyperFrames 五选一，含开源免费直出）。内嵌可运行部署/推理/合成脚本、组合编排决策树、批量流水线、与中游 handoff 完整对接。触发词："视频渲染引擎""AI配音出片""百炼配音""GPT-SoVITS配音""CosyVoice配音""VoxCPM2""edge-tts直出""剪映混剪""Remotion渲染""ffmpeg合成""HyperFrames渲染""数字人视频""下游渲染"。
agent_created: true
version: "5.2.2"
changelog:
  - version: "5.2.2"
    date: "2026-07-28"
    changes:
      - "版本对齐至包 v5.2.2（多 Agent 模式章节：根 SKILL.md 新增子模块→专家团成员映射与并发编排说明；本模块内容未变更，随包升级版本号保持与根 SKILL.md / settings.json 一致）。"
  - version: "5.2.1"
    date: "2026-07-28"
    changes:
      - "版本对齐至包 v5.2.1（本模块内容未变更：配音层 5 选 1 + 渲染通道 5 选 1 + Remotion 通道；随包升级版本号，保持与根 SKILL.md / settings.json 一致）。"
  - version: "5.1.8"
    date: "2026-07-25"
    changes:
      - "【T.C.E 六轮评审综合重构】同步包版本至 v5.1.8；根 SKILL.md 结构性重写（去重50%+、一键安装前置、[付费][免费]标签、Path B 动画风醒目提示、自救卡内嵌不跳文档、独立避坑清单）。本模块内容未变更，版本对齐。"
    date: "2026-07-22"
    changes:
      - "【Path B 可用性修复·重要】订正 §9.6 的 HyperFrames 合成格式：旧文档误写 window.__hf / body 挂 data-composition-id / <audio> 轨道 / init --template minimal / render [id] --output，全部与真实 CLI 不符。改为已验证格式（#root data-* + .clip 分镜 + GSAP window.__timelines），并标注'旧写法会渲染失败'。"
      - "【Path B 资产落地】新增可直接使用资产：templates/hyperframes_path_b/（已 lint 0 错）、scripts/path_b_build.py（脚本→分段配音→HTML→渲染→ffmpeg 合成→MP4 全链路）、scripts/install_path_b_deps.py（装依赖+自检）、references/path_b_runbook.md（一站式手册）。§9.6/§9.7 已指向这些资产。"
  - version: "5.1.1"
    date: "2026-07-22"
    changes:
      - "【Path A 参考】新增数字人训练方法：§9.8 数字人训练方法（建模·Path A 参考）+ references/digital-human-training.md（形态选择/三要素/训练数据硬标准/本地开源训练/SaaS 秒级克隆/合规红线/Path A 串联）。§9.5 增加指向训练方法的指针。"
  - version: "5.1.0"
    date: "2026-07-21"
    changes:
      - "【Path B 免费直出】新增 edge-tts 免费配音（§8.8，无需 API Key，--write-subtitles 自动对齐字幕）与 HyperFrames 开源渲染（§9.6，HTML→Puppeteer+FFmpeg→MP4），组合为端到端零云费直出（§9.7）。dubbing_method 枚举新增 edge_tts；render_channel 枚举新增 hyperframes。"
  - version: "5.0.0"
    date: "2026-07-21"
    changes:
      - "【全面化】8 个组件全部章节级深入：4 种配音（百炼/GPT-SoVITS/VoxCPM2/CosyVoice）+ 4 个渲染通道（剪映/Remotion/ffmpeg/数字人），各含是什么/部署或用法/接统一接口/可运行脚本/坑点/成本/局限。"
      - "【统一接口】新增 render() 渲染契约，与 dub() 并列；定义 render_channel 枚举 jianying/remotion/ffmpeg/digital_human。"
      - "【编排】新增组合编排决策树（8 组件如何选）、批量流水线示例、与中游 handoff 完整对接 JSON 示例。"
      - "【脚本】内嵌 conda 部署、推理 CLI、ffmpeg 归一化与合成命令、Remotion 项目骨架、数字人驱动步骤等真实可跑片段。"
  - version: "0.2.0"
    date: "2026-07-21"
    changes:
      - "新增百炼配音与剪映混剪两节详细介绍，与中游完成能力归位。"
  - version: "0.1.0"
    date: "2026-07-21"
    changes:
      - "初始版本：统一配音接口 + 四渲染通道。"
---

# 视频渲染引擎 (video-render-engine)

> 抖音短视频生产专家团 · 下游渲染层（生产级 5.0，自包含）。把中游优化好的脚本，变成**带 AI 配音的成片**。
> 本文件即可独立使用：所有组件（4 种配音 + 4 个渲染通道）均有章节级说明、可运行片段与坑点；更深的代码级片段见 `references/dubbing-methods.md` 与 `references/render-channels.md`。

---

## 1. 定位 + 30 秒调用速查卡

**定位**：流水线的**最后一环**。它不负责"写什么"，只负责"怎么出片"——拿到口播稿 → 选配音（4 选 1）→ 选通道（4 选 1）→ 合成成片，并执行上游判定的 AI 标识埋点。

**30 秒调用速查卡**：

1. **对话式**：直接说"用 CosyVoice 给这段脚本配音，走剪映混剪出 9:16 竖屏"。
2. **变量模板式**：填 `text` + `dubbing_method` + `render_channel` + `aspect_ratio`，其余用默认：
   ```json
   {
     "text": "今天教你三招提升完播率…",
     "dubbing_method": "cosyvoice",
     "render_channel": "jianying",
     "aspect_ratio": "9:16",
     "ai_label_config": { "mode": "overlay", "duration_sec": 3 }
   }
   ```
3. **专家包调度式**：由主理人（上游大脑 + 中游优化器）把 `optimized_script / shot_plan / dubbing_method / render_channel / digital_human / publish_platform / ai_label_config` 字段直接喂进来，引擎只管出片。

---

## 2. 前置依赖

| 依赖 | 用途 | 缺失时 |
|------|------|--------|
| ffmpeg | 音视频合成 / 转码 / 横竖屏 / 48k 归一化 | 禁用 ffmpeg 通道，其余可用 |
| 剪映 / 剪映专业版 | 混剪导出（GUI 或 OpenAPI） | 禁用剪映通道 |
| Node.js（≥18）+ Remotion | 程序化视频合成 | 禁用 Remotion 通道 |
| GPT-SoVITS / VoxCPM2 / CosyVoice 其一 | 本地 AI 配音 | 至少需一种；默认 CosyVoice |
| 百炼（阿里云）账号 + 声音克隆音色 | AI 配音（国产方案） | 缺失时可用其余本地方案替代 |
| 数字人运行时（如 HeyGem / 开源数字人） | 数字人通道 | 禁用数字人通道 |
| **edge-tts（Path B 免费直出）** | 免费 TTS，无需 API Key，`--write-subtitles` 自动对齐字幕 | 缺失时 Path B 不可用，其余通道不受影响 |
| **HyperFrames + Node.js（≥22）+ FFmpeg（Path B 免费直出）** | HTML→MP4 开源渲染（Puppeteer+FFmpeg） | 缺失时 Path B 不可用，其余通道不受影响 |
| `render_channel` 选择 | 决定走哪个渲染后端（见 §6） | 缺省 `jianying` |

> 每条 TTS 后端建议独立 conda 环境，输出统一归一化到 **48k / 16bit wav** 后再进渲染通道。所有后端输出格式一致，渲染通道**无需关心音色来源**。

---

## 3. Overview / When to Use

**Overview**：本引擎是流水线的最后一环。它拿到文本 / 分镜 → 选配音 → 选通道 → 合成成片。所有合规闸门（见上游大脑层）在进渲染前已由上游判定，引擎只执行 `ai_label_config` 的标识埋点。引擎把"配音"与"渲染"解耦为两层，每层 4 选 1，组合出 16 种出片路径。

**When to Use**：
- 已有 `optimized_script`，要变成可发布的抖音成片。
- 需要 AI 配音，但想自由选择声音模型（中文克隆 / 情感 / 离线 / 轻量）。
- 需要数字人出镜 / 程序化批量渲染 / 本地 ffmpeg 合成 / 完全离线零外网。

---

## 4. 国内全适配

| 环节 | 工具 | 网络要求 |
|------|------|---------|
| AI 配音 | 百炼（通义/阿里云）声音克隆 / CosyVoice（通义）/ VoxCPM2 / GPT-SoVITS（本地） | 百炼需国内直连；CosyVoice 需国内直连；GPT-SoVITS / VoxCPM2 可纯本地零外网 |
| 混剪 | 剪映（国产） | 零外网 |
| 程序化 | Remotion（Node，国产云部署友好） | 零外网 |
| 合成 | ffmpeg（本地） | 零外网 |
| 数字人 | HeyGem 等国产方案 | 多数本地 |

> 结论：除了"百炼 / CosyVoice 云端推理"需要国内直连外，其余组件均可做到**零外网、纯本地**部署。

---

## 5. Architecture

```
optimized_script + shot_plan + dubbing_method + render_channel + digital_human + ai_label_config
        │
        ▼
   ┌─────────────────────────────┐
   │  [配音层 · 4 选 1]            │
   │  百炼 / GPT-SoVITS /          │
   │  VoxCPM2 / CosyVoice         │ ──→ 归一化 48k / 16bit wav
   └─────────────────────────────┘
        │
        ▼
   ┌─────────────────────────────┐
   │  [渲染通道 · 4 选 1]          │
   │  剪映 / Remotion /            │
   │  ffmpeg / 数字人              │ ──→ 成片（带 AI 标识埋点）
   └─────────────────────────────┘
        │
        ▼
   统一质量门 → 出片自检总卡 → 交付
```

> 配音层与渲染层正交：任意配音 × 任意通道 = 合法路径（数字人通道通常搭配离线或 CosyVoice 音色，但接口上不强制）。

---

## 6. Input Protocol（handoff 字段，来自中游 / 上游）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `optimized_script` / `text` | string | ✅ | 优化后口播稿 |
| `title_options` | list[string] | ⬜ | 标题候选（上游 / 中游给） |
| `shot_plan` | list[object] | ⬜ | 分镜（景别 / 视角 / 焦点），驱动画面 / 数字人 |
| `video_duration` | int(秒) | ⬜ | 默认按脚本字数估算 |
| `aspect_ratio` | enum | ⬜ | `9:16`(默认) / `1:1` / `16:9` |
| `dubbing_method` | enum | ✅ | `edge_tts`(免费直出·Path B) / `baike`(百炼) / `gptsovits` / `voxcpm2` / `cosyvoice`(默认) |
| `render_channel` | enum | ⬜ | `hyperframes`(免费直出·Path B) / `jianying`(默认) / `remotion` / `ffmpeg` / `digital_human` |
| `digital_human` | bool | ⬜ | 是否走数字人通道（等价于 `render_channel="digital_human"`） |
| `publish_platform` | string | ⬜ | 抖音主端 / 极速版（影响尺寸 / 标识） |
| `ai_label_config` | object | ⬜ | AI 标识埋点（前 5 秒 ≥3 秒可见） |
| `image_map` | JSON | ⬜ | 绘影层产出的 beat→图片路径映射。提供时 render() 直接消费；不提供时按原方式（外部准备图片） |

> `render_channel="digital_human"` 时，引擎自动视作数字人通道；`digital_human: true` 与 `render_channel="digital_human"` 二选一即可，前者优先。

---

## 7. 统一接口契约

### 7.1 配音 `dub()` 契约

**输入统一签名**：

```python
dub(text, method, reference_audio=None, language="zh", emotion=None, instruct=None, speed=1.0)
```

**输出统一结构**：

```json
{
  "audio_path": "out.wav",
  "duration_sec": 12.3,
  "sample_rate": 48000,
  "method_used": "cosyvoice",
  "alignment": [ {"char": "你", "start": 0.2, "end": 0.5}, ... ]
}
```

- 所有 `method` 输出统一为 48k / 16bit wav，渲染通道无需关心来源。
- `alignment` 为可选逐字符时间戳，用于数字人 / 字幕精确对齐。

### 7.2 渲染 `render()` 契约（5.0 新增）

**输入统一签名**：

```python
render(audio_path, channel, shots=None, aspect_ratio="9:16", ai_label_config=None)
```

**输出统一结构**：

```json
{
  "video_path": "out.mp4",
  "duration_sec": 12.3,
  "channel_used": "jianying",
  "resolution": "1080x1920"
}
```

- `channel` 取值：`jianying`(默认) / `remotion` / `ffmpeg` / `digital_human`。
- `shots` 即中游 `shot_plan`（分镜列表）；ffmpeg / 数字人通道可只给 `audio_path` 走极简模式。
- `ai_label_config` 控制前 5 秒 AI 标识埋点（见 §13 质量门）。

### 7.3 端到端最小示例

```python
audio = dub(text="今天教你三招…", method="cosyvoice", language="zh")
video = render(audio["audio_path"], channel="jianying",
               shots=shot_plan, aspect_ratio="9:16",
               ai_label_config={"mode": "overlay", "duration_sec": 3})
# → video["video_path"] == "out.mp4", resolution "1080x1920"
```

---

## 8. 配音层（4 自部署 + 1 免费直出）

### 8.1 决策总表

| 方式 | 特点 | 何时选 | 成本 / 部署难度 |
|------|------|--------|----------------|
| 百炼（阿里云声音克隆） | 国产、国内直连、中文音色丰富、克隆成本低、合规无风险 | 中文专属克隆音色、追求低成本的国产方案 | 低（按量计费，零本地部署） |
| GPT-SoVITS | 固定角色音、本地部署、音色最稳 | 稳定人设 IP、离线零外网 | 中（需 GPU + 微调，本地零云费） |
| VoxCPM2 | 轻量快速、资源占用低 | 批量、低延迟、无强人设要求 | 低（本地推理，CPU 也可） |
| CosyVoice（默认） | 多语 / 情感 / 指令控制强、开源生态好 | 通用首选，需表情情绪 / 跨语言 | 中（需权重，可本地） |
| edge-tts（免费直出·Path B） | 微软免费 TTS，无需 API Key，`--write-subtitles` 自动对齐字幕 | 免费优先、零配置、快速出片、无需训练 | 零（pip install edge-tts，无云费） |

> 详细部署范式与调用见 `references/dubbing-methods.md`。

---

### 8.2 百炼配音（阿里云百炼声音克隆）

> 中游 `douyin-script-optimizer` 只产出 `optimized_script` / `shot_plan`，TTS 与混剪由本下游技能负责。以下为百炼配音的详细实操。

**是什么**：阿里云百炼平台的语音合成 / 声音克隆能力：国产、国内直连、中文音色丰富、克隆成本低、合规无风险，是中文短视频配音的优选国产方案。

**怎么开通**：
1. 开通阿里云百炼（通义）服务：访问百炼控制台，完成实名与开通。
2. 创建 API Key，妥善保存。
3. 训练 / 选择声音克隆音色：准备一段授权清晰、无背景噪声的参考音频（违规风险低、已获授权的真人声音），上传训练专属克隆音色；或直接选用平台预置中文音色。

**怎么接统一接口**：与本引擎统一 `dub()` 接口对齐，传 `method="baike"` 即可，输出同样归一化到 48k / 16bit wav，再进渲染通道：

```python
dub(
    text="今天教你三招…",
    method="baike",                 # 百炼声音克隆
    reference_audio="speaker_A.pt", # 已训练的克隆音色（或平台音色 id）
    language="zh",
    speed=1.0,
)
```

**⚠️ 字符清洗坑（送百炼前必做）**：`optimized_script` 直接送入百炼 TTS 前必须清理 Markdown 符号 / Emoji / 装饰性特殊字符，否则会被念出来或报错。清洗要点（通用脚本见 §8.6）：

```python
import re
script = optimized_script
for pat, rep in [
    (r'#\w+', ''),        # 话题标签 #xxx
    (r'\*[^*]+\*', ''),   # Markdown 加粗
    (r'`[^`]+`', ''),     # 行内代码
    (r'\n{3,}', '\n\n'),  # 多余空行
    (r'[丨|●■→←↑↓]', ''), # 装饰符号（TTS 会乱读）
]:
    script = re.sub(pat, rep, script)
if len(script.strip()) < 20:
    raise Exception("清洗后文案过短，请检查原始输出")
# 输出即百炼可直接消费的纯文本
```

**⚠️ 时长估算坑（绝不能直接拿去对齐剪映）**：`estimated_duration` 是基于 ~4.5 字/秒 的粗估，百炼实际合成常有 ±10% 偏差，绝不能直接拿去对齐剪映时间轴：
1. 先跑 TTS 拿到实际音频文件；
2. 用 `ffprobe -i audio.mp3 -show_entries format=duration -v quiet -of csv="p=0"` 取精确时长；
3. 用实际时长回写 `shot_plan` 的 beat 边界再进剪映混剪；偏差 >±1s 必须返工重裁。

**💰 成本**：按量计费（合成字符 / 时长），无本地显卡投入；克隆音色一次性训练成本低。
**局限**：属云端服务，需国内网络直连；无法离线。

---

### 8.3 GPT-SoVITS 配音（详细）

**是什么**：开源本地 TTS，少样本即可克隆固定说话人音色，可**完全离线零外网**运行，适合需要稳定"人设 IP"的账号。音色一旦微调锁定，批量产出一致性最高。

**conda 部署命令**：

```bash
# 1) 建独立环境（Python 3.9，GPT-SoVITS 官方推荐）
conda create -n gptsovits python=3.9 -y
conda activate gptsovits

# 2) 克隆仓库并安装依赖（以官方仓库为准）
git clone https://github.com/RVC-Boss/GPT-SoVITS.git
cd GPT-SoVITS
pip install -r requirements.txt

# 3) 准备参考音频并微调（1~数分钟无噪单人声即可少样本微调）
#    参考音频放 ./raws/speaker_A.wav，运行预处理 + 训练脚本（详见官方 docs）
python tools/preprocess_text.py --text "参考文本…" --language zh
#    （训练命令以官方仓库 README 为准，此处为范式示意）
```

**接统一接口**：

```python
dub(
    text="今天教你三招…",
    method="gptsovits",
    reference_audio="speaker_A.pt",   # 已微调的固定音色
    language="zh",
    speed=1.0,
)
```

**可运行推理 CLI 示例**（范式，参数名以本地推理脚本为准）：

```bash
conda activate gptsovits
python inference.py \
    --method gptsovits \
    --text "今天教你三招提升完播率" \
    --reference_audio ./weights/speaker_A.pt \
    --output ./out.wav
```

**坑点**：
- 参考音频需**无噪声、单人声**；含背景音乐 / 混音会污染音色。
- 首次微调务必**锁定 `speaker`**，避免后续推理漂移。
- 输出采样率可能与 48k 不一致 → 必须重采样归一化（见 §8.7）。

**成本**：本地零云费，仅显卡折旧；一次性微调算力成本可控。
**局限**：需 GPU（显存越大推理越快）；部署比云端方案重。

---

### 8.4 VoxCPM2 配音（详细）

**是什么**：轻量级本地 TTS，资源占用低、延迟小，加载预训练多说话人模型后按 `speaker_id` 选声即可，**无需微调**，适合批量、低延迟、无强人设要求的场景。

**conda 部署命令**：

```bash
# 独立环境（Python 3.10，通常比 GPT-SoVITS 更轻）
conda create -n voxcpm2 python=3.10 -y
conda activate voxcpm2

# 安装 VoxCPM2 及依赖（以官方仓库为准）
git clone https://github.com/your-org/VoxCPM2.git   # 占位，请替换为实际仓库
cd VoxCPM2
pip install -r requirements.txt
```

**接统一接口**（用 `speaker_id` 选声，不传 `reference_audio`）：

```python
dub(
    text="点下方小黄车…",
    method="voxcpm2",
    reference_audio=None,             # 用 speaker_id 选声
    language="zh",
    speed=1.05,
)
```

**可运行推理 CLI 示例**：

```bash
conda activate voxcpm2
python inference.py \
    --method voxcpm2 \
    --text "点下方小黄车下单" \
    --speaker_id speaker_A \
    --output ./out.wav
```

**坑点**：
- 跨说话人音质差异大，批量时**固定 `speaker_id`** 保证一致性。
- 长文本可能截断 → 按标点**切句后拼接**（见 §8.7 时长对齐中的切句思路）。
- 同样需归一化到 48k。

**成本**：本地推理，CPU 也可跑，零云费；比 GPT-SoVITS 更省资源。
**局限**：音色自然度通常略逊于微调方案；人设感弱。

---

### 8.5 CosyVoice 配音（详细）

**是什么**：通义开源 TTS，多语言、情感控制、自然语言指令（instruct）能力强，开源生态好，是引擎**默认后端**。支持三种模式：基础 TTS / 情感 TTS（emotion）/ 指令 TTS（instruct），还能跨语言合成。

**conda 部署命令**：

```bash
# 独立环境（Python 3.10）
conda create -n cosyvoice python=3.10 -y
conda activate cosyvoice

# 安装 CosyVoice（通义开源版），准备模型权重（以官方仓库为准）
git clone https://github.com/FunAudioLLM/CosyVoice.git
cd CosyVoice
pip install -r requirements.txt
# 下载模型权重（需国内直连或已缓存）
```

**接统一接口 · 三个调用示例**：

```python
# ① 基础 TTS
dub(text="欢迎来到我的直播间", method="cosyvoice", language="zh")

# ② 带情感（emotion 模式）
dub(text="这个真的绝了", method="cosyvoice", emotion="开心", language="zh")

# ③ 带指令（instruct 模式）
dub(text="三招搞定", method="cosyvoice",
    instruct="用兴奋、带货催促的语气", language="zh")

# ④ 跨语言
dub(text="Hello everyone", method="cosyvoice", language="en")
```

**可运行推理 CLI 示例**：

```bash
conda activate cosyvoice
python inference.py \
    --method cosyvoice \
    --text "这个真的绝了" \
    --emotion "开心" \
    --output ./out.wav
```

**坑点**：
- 首次需下载模型权重，确保国内直连或已缓存。
- `instruct` 模式对指令措辞敏感，建议沉淀几条有效指令模板。
- 输出同样归一化 48k 后入通道。

**成本**：本地推理可离线（权重缓存后）；云端部署可选。
**局限**：首次权重体积大；`instruct` 效果依赖指令质量。

---

### 8.6 共享坑 · 字符清洗（所有 TTS 通用）

百炼对特殊字符最敏感（会念出或报错），CosyVoice / GPT-SoVITS / VoxCPM2 也会因符号产生停顿或乱读。**所有 `dub()` 调用前统一清洗**：

```python
import re

def clean_for_tts(text: str) -> str:
    """所有 TTS 后端通用的字符清洗。"""
    rules = [
        (r'#\w+', ''),            # 话题标签 #xxx
        (r'\*[^*]+\*', ''),       # Markdown 加粗
        (r'_{2,}[^_]+_{2,}', ''), # Markdown 斜体/下划线
        (r'`[^`]+`', ''),         # 行内代码
        (r'!\[[^\]]*\]\([^)]*\)', ''),  # Markdown 图片
        (r'\[[^\]]+\]\([^)]+\)', ''),   # Markdown 链接
        (r'https?://\S+', ''),    # 裸 URL
        (r'\n{3,}', '\n\n'),      # 多余空行
        (r'[丨|●■◆→←↑↓✓✔✘❌⭐🔥]', ''),  # 装饰/emoji 符号
        (r'\s{2,}', ' '),         # 多余空格
    ]
    for pat, rep in rules:
        text = re.sub(pat, rep, text)
    return text.strip()

clean = clean_for_tts(optimized_script)
if len(clean) < 20:
    raise ValueError("清洗后文案过短，请检查原始输出")
```

> 经验：百炼 > CosyVoice > VoxCPM2 > GPT-SoVITS 对特殊字符的敏感度递减，但统一清洗最稳妥。

---

### 8.7 共享坑 · 时长对齐（所有方法适用）

任何 TTS 的真实时长都与估算有偏差：百炼 ±10%、CosyVoice / GPT-SoVITS / VoxCPM2 也各有偏差。**统一步骤**：
1. 先跑 TTS 拿到实际音频文件（`out.wav`）；
2. 用 `ffprobe` 取精确时长：
   ```bash
   ffprobe -i out.wav -show_entries format=duration -v quiet -of csv="p=0"
   ```
3. 用实际时长回写 `shot_plan` 的 beat 边界，再进渲染通道；
4. 偏差 >±1s 必须返工重裁（见各渲染通道的声画匹配约束）。

**长文本切句拼接（VoxCPM2 / GPT-SoVITS 常用）**：

```python
import re
def split_sentences(text: str, max_len: int = 80):
    """按标点切句，避免单次推理截断。"""
    parts = re.split(r'(?<=[。！？.!?；;])', text)
    return [p.strip() for p in parts if p.strip()]

# 逐句推理后按时间戳拼接为单条 48k wav（拼接逻辑由各后端 CLI 负责）
```

---

### 8.8 edge-tts 配音（免费直出 · Path B）

**是什么**：微软提供的**免费**在线 TTS，**无需任何 API Key**，支持中文多音色（如 `zh-CN-XiaoxiaoNeural`），且关键能力是 `--write-subtitles` 可**一次性同时生成 mp3 + 对齐的 srt 字幕**，避免音画不同步。是 Path B 端到端直出的默认配音方式。

**怎么用（一次性生成配音 + 字幕）**：

```bash
pip install edge-tts

edge-tts \
  --voice zh-CN-XiaoxiaoNeural \
  --rate +5% \
  --write-media /tmp/douyin-factory/audio/[video_id].mp3 \
  --write-subtitles /tmp/douyin-factory/srt/[video_id].srt \
  --text "完整旁白文案..."
```

> ⚠️ **必须一次性同时生成 mp3 和 srt**，禁止分开生成再手动对齐（会导致音画不同步）。edge-tts 的 srt 时间戳与音频天然对齐。

**接统一接口**：传 `method="edge_tts"` 即可，输出同样归一化到 48k / 16bit wav 后再进渲染通道：

```python
dub(
    text="今天教你三招…",
    method="edge_tts",          # 免费直出
    voice="zh-CN-XiaoxiaoNeural",
    rate="+5%",
)
```

**常用中文音色**：
- `zh-CN-XiaoxiaoNeural`（女声，推荐默认）
- `zh-CN-YunxiNeural`（男声，活泼）
- `zh-CN-XiaoyiNeural`（女声，温柔）

**⚠️ 字符清洗坑（同 §8.6）**：`optimized_script` 送 TTS 前必须清理 Markdown 符号 / Emoji / 装饰字符，否则会被念出来。清洗函数见 §8.6。

**💰 成本**：零（微软免费额度，无需信用卡）。
**局限**：音色为微软预设，不可克隆专属人声（需专属克隆请走 百炼 / GPT-SoVITS / CosyVoice）；需联网调用微软接口（非纯离线）。

---

> 如上游绘影层已产出 `image_map.json`，渲染通道可直接按 beat_index 取图，无需手动准备素材。

## 9. 渲染通道层（4 自部署 + 1 免费直出）

### 9.1 决策总表

| 通道 | 适用 | 输入 | 输出 | 成本 / 适用规模 |
|------|------|------|------|----------------|
| 剪映混剪 | 新手 / 带货 / 快出 | 音频 + 素材 / 分镜 | 成片（GUI 或 OpenAPI） | 低（订阅制），中小规模 |
| Remotion | 程序化 / 模板化 / 批量 | 音频 + React 场景 | 成片（代码可控） | 低（Node 本地），适合大规模模板 |
| ffmpeg | 本地极简合成 / 转码 | 音频 + 图片序列 / 视频 | 成片（零依赖云） | 零，单机即可大规模 |
| 数字人 | 出镜口播 | 音频 + 肖像 / 驱动视频 | 数字人成片 | 中（授权/算力），IP 人设场景 |
| HyperFrames（免费直出·Path B） | 程序化 HTML→MP4、风格模板化、字幕/背景/BGM 合成 | 音频 + HTML 合成文件（或 JSON 制作包） | 成片（开源，Puppeteer+FFmpeg） | 零（Node≥22 + FFmpeg 本地），适合模板化批量 |

> 完整可复制内容（OpenAPI 字段映射、Remotion 工程、ffmpeg cookbook、数字人步骤）见 `references/render-channels.md`。

---

### 9.2 剪映混剪（详细）

> 消费中游传来的 `shot_plan` 与 `optimized_script` 的 TTS 音频，完成声画对齐成片。中游只负责产出符合下列硬约束结构的 `shot_plan`，实际混剪由本下游执行。

**是什么**：字节跳动出品的剪映（专业版 / 企业版 / OpenAPI）：抖音生态深度集成、模板丰富、操作门槛低，本地无需联网即可剪辑，是抖音成片最顺手的混剪通道。

**怎么用**：
- **GUI 手动混剪**：导入 TTS 音频 + 按 `shot_plan` 准备的素材/AI 生图，按 beat 铺轨道、加转场与字幕，导出 mp4。
- **OpenAPI / 命令行**：将 `shot_plan` 的逐槽（beat / visual_prompt / source）映射为剪辑轨道，程序化批量出片。
- 输入：本引擎产出的 48k wav 配音 + 中游 `shot_plan` 驱动的视觉素材。

**接统一接口**：

```python
render(audio["audio_path"], channel="jianying",
       shots=shot_plan, aspect_ratio="9:16",
       ai_label_config={"mode": "overlay", "duration_sec": 3})
```

**⚠️ 声画匹配硬约束（核心）**：
1. `shot_plan` 每槽 ≤5s；`visual_prompt` 必须具体（如"办公桌咖啡杯特写、热气袅袅"），禁泛描述（"办公室场景""相关画面"）；`source` 不得留空（asset_pool / ai_gen）。
2. 剪映轨道切点必须严格对应 beat 时间边界，无跨 beat 素材。
3. 以 TTS **实际音频时长**为基准倒推精确时间戳，偏差 >±0.5s 不合格（见 §8.7 时长对齐）。

**✅ 出片前校验清单（任一条不过禁止导出 mp4）**：
- [ ] 每 ≤5s 一槽？visual_prompt 具体？
- [ ] 剪映切点 = beat 边界？无跨 beat 素材？
- [ ] 音频实际 vs 预估偏差 < ±1s？
- [ ] 逐拍听：听到 A、画面也在 A？
- [ ] AI 生图风格一致？
- [ ] 无任何一拍画面与口播明显无关？

**💡 提质小技巧**：
- AI 味重：在剪映叠加滤镜 / Ken Burns 动效增加动感。
- 图不够动：走图生视频（YT-Video-2.0 / HY-Video-1.5）补动态。

**💰 成本参考**：一次性投入音色训练 ¥100–500 + 剪映订阅 ¥30–100/月（与配音/生图按主题缓存复用摊薄）。
**局限**：剪映通道依赖本机剪映，无 GUI 环境跑不了（见 Known Limitations）。

---

### 9.3 Remotion 渲染（详细）

**是什么**：基于 React 的**程序化视频**框架——用代码（组件 + `<Composition>`）定义每一帧画面，适合模板化、批量、可版本管理的出片。导出的视频由 `@remotion/cli` 在 Node 环境渲染，**国产云部署零外网**。

**现成可跑工程**：`templates/remotion/`（已含 package.json / tsconfig / React 组件 / 中文字体配置 / 渲染脚本）。

**一键渲染（推荐）**：

```bash
cd templates/remotion
npm install

# 预览
npm run studio

# 用真实数据渲染：把图片和音频放 public/，写 props.json
npm run render:props
```

**通过 skill 脚本自动编排**：`scripts/render_remotion.py` 会自动：

1. 读 `shot_plan.json` + `image_map.json` + 配音音频；
2. 把素材复制到 `templates/remotion/public/`；
3. 生成 `props.json`；
4. 调用 `npx remotion render` 输出 MP4。

```bash
python scripts/render_remotion.py \
  --shot-plan shot_plan.json \
  --image-map image_map.json \
  --audio out.wav \
  --output final.mp4 \
  --aspect-ratio 9:16 \
  --ai-label-duration 3
```

**接统一接口**：

```python
render(audio["audio_path"], channel="remotion",
       shots=shot_plan, aspect_ratio="9:16",
       ai_label_config={"mode": "overlay", "duration_sec": 3})
```

**数据格式（props.json）**：

```json
{
  "shots": [
    {
      "beat": 0,
      "visual_prompt": "主播特写、手指向前勾引动作",
      "source": "ai_gen",
      "duration_sec": 3.0,
      "image": "beat_0.png",
      "caption": "今天教你三招"
    }
  ],
  "audioFile": "audio.wav",
  "totalDurationSec": 12,
  "aspectRatio": "9:16",
  "aiLabelConfig": {
    "mode": "overlay",
    "duration_sec": 3,
    "text": "本视频含 AI 生成内容"
  },
  "title": "三招提升完播率"
}
```

**坑点**：
- 需 Node.js（≥18）环境；无 Node 的机器禁用该通道。
- 首包下载慢（需拉取 Chromium 渲染内核），建议镜像 / 缓存。
- **中文字体已内置 `@font-face` 回退**（Noto Sans SC → Microsoft YaHei → PingFang SC），如仍方块，把 `NotoSansSC.woff2` 放 `public/` 即可。
- Remotion 吃的是结构化素材，不智能选片；混剪请走 `混剪` 子技能。

**成本**：本地 / 国产云 Node 环境即可，零外网、零按量费用，适合大规模模板。
**局限**：动态视觉需组件开发（本模板已封装常用字幕/标题/切镜，可直接改文案和图）；富模板动画开发成本仍高于剪映拖拽。

---

### 9.4 ffmpeg 合成（详细）

**是什么**：本地**极简零云依赖**合成——用一条命令把图片序列 + 配音变成视频，或做横竖屏转码、字幕烧录、音频归一化。无模板动效，但最稳、最快、可完全脚本化。

**接统一接口**：

```python
render(audio["audio_path"], channel="ffmpeg",
       shots=None, aspect_ratio="9:16",
       ai_label_config={"mode": "burn_sub", "duration_sec": 3})
```

**命令集（cookbook，完整版见 `references/render-channels.md`）**：

```bash
# ① 图片序列 + 音频 → 视频（25fps，img001.png 起）
ffmpeg -r 25 -i img%03d.png -i audio.wav -c:v libx264 -pix_fmt yuv420p out.mp4

# ② 横竖屏 9:16：scale 后居中 crop（1080x1920）
ffmpeg -i in.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2" -c:a copy out_9x16.mp4

# ③ 字幕烧录（需字幕文件 sub.srt，中文需指定字体）
ffmpeg -i out.mp4 -vf "subtitles=sub.srt:force_style='FontName=Noto Sans SC'" -c:a copy out_sub.mp4

# ④ 音频 48k 归一化（所有 TTS 输出统一标准）
ffmpeg -i in.mp3 -ar 48000 -ac 1 out.wav
```

**坑点**：
- 必须 `-pix_fmt yuv420p`，否则部分播放器（含抖音）黑屏 / 无法上传。
- 帧率需与音频对齐（图片序列 `-r` 与合成 fps 一致），否则音画不同步。
- 字幕编码：中文字幕必须指定含中文的 `FontName`，否则乱码 / 方块。

**成本**：零（ffmpeg 本地开源）。
**局限**：无模板动效，需自管素材（图、字幕、转场靠外部生成）。

---

### 9.5 数字人视频（详细）

**是什么**：出镜口播形态——用授权肖像 + 配音驱动数字人"开口说话"，适合 **IP 人设 / 真人出镜感** 内容，无需真人出镜录制。

**驱动方式**（国产方案如 HeyGem 等）：
- **音频 + 肖像**：给定一张授权肖像图 + 配音音频，生成口型同步的数字人视频。
- **音频 + 驱动视频**：给定一段真人视频（授权）+ 配音，替换口型与声音。
- 本质都是"音频驱动口型"，输出即数字人成片。

**授权硬要求**：**必须取得肖像权人明确授权**，禁止未授权人脸 / 克隆他人形象。这是合规红线（见 Hard Constraints）。

> 📚 **想训练/克隆专属数字人模型？** 本文只讲"驱动（推理）"。训练（建模）方法（形态选择 / 形象+声音+驱动三要素 / 训练数据硬标准 / 本地开源训练 / SaaS 秒级克隆 / 合规红线 / Path A 串联）→ 见 `references/digital-human-training.md` 与本章 §9.8。

**接统一接口**：

```python
render(audio["audio_path"], channel="digital_human",
       shots=None, aspect_ratio="9:16",
       ai_label_config={"mode": "overlay", "duration_sec": 3,
                        "portrait": "authorized_speaker.jpg"})
# 或等价地：render(..., digital_human=True, ...)
```

**可运行驱动步骤（范式，以 HeyGem 等工具为准）**：

```bash
# 1) 准备授权肖像 / 驱动视频与已生成的 48k 配音
# 2) 调用数字人驱动（命令行范式）
python digital_human_drive.py \
    --audio out.wav \
    --portrait authorized_speaker.jpg \
    --output digital_human.mp4
```

**坑点**：
- 肖像**授权**是硬前提，缺授权一律不出片。
- 驱动素材质量直接决定成片（肖像分辨率 / 光照 / 驱动视频清晰度）。
- 口型同步存在误差，长句末端易漂移，需抽检。

**成本**：中（算力 + 授权管理）；比纯配音合成高。
**局限**：强依赖授权素材；口型同步非 100% 完美；不适合无 IP 的纯搬运。

---

### 9.6 HyperFrames 渲染（免费直出 · Path B）

**是什么**：Heygen 开源的视频渲染 **CLI**（npm 包 `hyperframes`，Node≥22）。用 **HTML 文件定义视频合成**（分镜 / 文字动画 / 背景），经内置 Chromium（Puppeteer）+ FFmpeg 渲染为 MP4。零云费、模板化，是 Path B 端到端直出的默认渲染通道。

**环境要求**：Node.js ≥ 22、`ffmpeg` + `ffprobe`、`edge-tts`（配音，见 §8.8）、首次渲染会自动下载 Chromium（或手动 `npx hyperframes browser ensure`）。

**真实合成格式（已用 `hyperframes lint` 验证通过）**：
- 根 `<div id="root" data-composition-id="main" data-start="0" data-duration="<总秒>" data-width="1080" data-height="1920">`
- 每个分镜一个 `<div class="clip" data-start="<起秒>" data-duration="<秒>" data-track-index="1">`
- 动画用 GSAP，在底部 `<script>` 注册 `window.__timelines["main"]`
- 分辨率由 `<meta viewport content="width=1080, height=1920">` 与 `#root` 的 `data-width/height` 决定

> ⚠️ **重要更正**：旧文档曾写 `window.__hf` 全局对象、`body` 上挂 `data-composition-id`、`<audio>` 配音轨道——**这些都是错的**（系早期误写）。真实字段就是上面的 `data-*` 属性 + `window.__timelines`。照旧写法会渲染失败，请以此处为准。

**Step 1：edge-tts 生成配音 + 字幕**（见 §8.8，输出每段 `.mp3` + `.vtt`）

**Step 2：生成合成 HTML**（按配音时长排布分镜时序 —— 下面的 `data-duration` 应等于各段配音时长）

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      /* 中文系统字体: 用 src: local() 声明, 渲染器即可识别(无需字体文件) */
      @font-face { font-family: "Microsoft YaHei"; src: local("Microsoft YaHei"); }
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { width: 1080px; height: 1920px; overflow: hidden; background: #0b1020; }
      #root { width: 1080px; height: 1920px; position: relative; }
      .clip { position: absolute; inset: 0; display: flex; flex-direction: column;
              justify-content: center; padding: 120px; }
      h1 { font-size: 96px; font-weight: 800; color: #fff; }
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0"
         data-duration="12" data-width="1080" data-height="1920">
      <div id="s1" class="clip" data-start="0" data-duration="6" data-track-index="1">
        <h1>第一镜标题</h1>
      </div>
      <div id="s2" class="clip" data-start="6" data-duration="6" data-track-index="1">
        <h1>第二镜标题</h1>
      </div>
    </div>
    <script>
      window.__timelines = window.__timelines || {};
      const tl = gsap.timeline({ paused: true });
      tl.from("#s1", { opacity: 0, y: 80, duration: 0.6 }, 0);
      tl.from("#s2", { opacity: 0, y: 80, duration: 0.6 }, 6);
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
```

**Step 3：渲染静帧视频 + ffmpeg 合成音频/字幕**

```bash
# 渲染画面(不含音轨) → silent.mp4
npx hyperframes render -c composition.html -o silent.mp4
# 拼音频 + 烧字幕 → 最终 final.mp4
ffmpeg -i silent.mp4 -i narration.mp3 -vf "subtitles=subs.vtt" \
       -c:a aac -shortest -movflags +faststart final.mp4
```

> HyperFrames 只负责"画面"，音频与字幕由 `ffmpeg` 在外部合成——这是已验证可用的组合（**不要在 HTML 里塞 `<audio>` 轨道**）。

**Step 4：质量验证**

```bash
ls -lh final.mp4
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 final.mp4
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 final.mp4
```

合格标准：文件 > 1MB；时长在目标 ±5s 内；分辨率 1080×1920（竖）或 1920×1080（横）。

**⚠️ 常见渲染错误**：
- 渲染卡住 / 报缺浏览器 → `npx hyperframes browser ensure` 装 Chromium；`npx hyperframes doctor` 看环境全貌。
- `lint` 报字体错（`font_family_without_font_face`）→ 中文字体用 `@font-face { src: local("字体名") }` 声明（见上方模板）。
- 无声 → 确认 `narration.mp3` 已生成（edge-tts 那步联网成功）。

**💰 成本**：零（开源 + 本地渲染）。
**局限**：需 Node≥22 + FFmpeg + Chromium；HTML 语法错会渲染失败（先 `npx hyperframes lint <项目目录>` 校验）。

**📦 本 skill 内置现成资产（开箱即用，已验证）**：
- 模板工程：`templates/hyperframes_path_b/`（已 `lint` 0 错，改文字即可 `render`）
- 串联脚本：`scripts/path_b_build.py`（脚本文本 → 分段配音 → 生成 HTML → 渲染 → 合成 → `final.mp4`）
- 安装脚本：`scripts/install_path_b_deps.py`（装依赖 + 环境自检）
- 一站式手册：`references/path_b_runbook.md`

---

### 9.7 Path B 端到端直出（edge-tts + HyperFrames 组合）

> 给「免费优先、不想配环境、要快速出片」的用户。整条链路零云费：采集（content-collector 零配置）→ 脚本（抖音优化器对话直跑）→ **edge-tts 免费配音 + HyperFrames 开源渲染 → MP4**。

**怎么跑（推荐，已验证）**：直接用内置串联脚本 + Runbook，不用手写命令：

```bash
python scripts/install_path_b_deps.py --auto   # 一次性装依赖(或 --check 只检测)
python scripts/path_b_build.py --input 脚本.txt --output final.mp4
```

完整步骤、输入格式（纯文本 / JSON）、排错表见 **`references/path_b_runbook.md`**。

**概念层接口**（供 skill 内部编排引用）：

```python
# 1) 配音（免费，带自动对齐字幕）— 见 §8.8
dub(text=optimized_script, method="edge_tts",
    voice="zh-CN-XiaoxiaoNeural", rate="+5%")

# 2) 渲染（开源 HTML→MP4）— 真实落地见 §9.6
render(channel="hyperframes", composition="composition.html",
       output="final.mp4", aspect_ratio="9:16")
```

> 上面的 `render(...)` 是编排层统一抽象；真实命令是 §9.6 的 `npx hyperframes render -c ... -o ...` + `ffmpeg` 合成，`scripts/path_b_build.py` 已封装好整条链路。

**前置检查**：`pip install edge-tts` + Node≥22 + `ffmpeg` + `npx hyperframes`。任一缺失则 Path B 不可用，自动降级到 Path A 的其余通道（剪映 / ffmpeg / Remotion）。

---

### 9.8 数字人训练方法（建模 · Path A 参考）

> 本节是 **Path A（高质量生产）** 的参考内容：讲"数字人模型从哪来"。§9.5 是"有了模型怎么驱动出片"，本节是"模型怎么训练/克隆"。完整方法论（含训练数据硬标准、本地开源训练命令范式、SaaS 平台清单、合规红线、Path A 串联示例）见 **`references/digital-human-training.md`**。

**核心结论（速览）**：
- **数字人 = 形象 + 声音 + 驱动**，三者齐备才能出片。声音克隆见 §8（百炼/GPT-SoVITS/CosyVoice/VoxCPM2），驱动见 §9.5，本节补"形象克隆 + 整体训练"。
- **两种路线**：
  - **本地训练（免费·私有）**：LivePortrait / MuseTalk / HeyGem 等开源，需 NVIDIA 显卡 + CUDA，素材不出本机。
  - **SaaS 秒级克隆（按量计费）**：即创(字节) / 硅基 / 腾讯智影 / 阿里如影 / 百度曦灵 / 闪剪 等，上传授权素材→平台自动生成形象+声音。
- **训练数据硬标准**：授权肖像视频 1–5 分钟、正脸、≥1080p、单一机位、均匀光、无遮挡；授权人声 10–30s 干净单人声；**必须书面授权**。
- **合规红线**：授权是硬前提；数字人视频必须加显式（画面）+隐式（元数据）AI 标识（见 §9.5 与大脑层合规六闸）；**禁止克隆他人/公众人物/未成年人**。
- **Path A 出片串联**：`dub(method="baike"/...)` 生成专属音色 → `render(channel="digital_human", portrait=训练好的形象)` 驱动出片。

> 选型：要私有/有显卡 → 本地训练；要快/不想配环境 → SaaS；品牌矩阵号 → 本地训专属 + SaaS 做变体。

---

## 10. 组合编排 · 决策树

按"是否需人设 IP / 是否离线 / 是否批量 / 是否出镜"四个维度选组合：

```
需要真人出镜口播？
├─ 是 → 数字人通道
│        └─ 音色：CosyVoice（情感/指令） 或 百炼（中文克隆）
│        组合：CosyVoice + 数字人（IP 人设口播）
│
└─ 否 → 是否完全离线零外网？
         ├─ 是 → 本地配音 + ffmpeg
         │       组合：GPT-SoVITS + ffmpeg（离线零外网）
         │
         └─ 否 → 是否批量 / 模板化？
                  ├─ 是 → 程序化渲染
                  │       组合：CosyVoice + Remotion（批量模板）
                  │       组合：百炼 + Remotion（中文专属 + 程序化）
                  │
                  └─ 否 → 快出 / 带货
                          组合：百炼 + 剪映（带货快出）
                          组合：CosyVoice + 剪映（通用快出）
```

**5 个推荐组合速查**：
| 场景 | 配音 | 通道 | 理由 |
|------|------|------|------|
| 带货快出 | 百炼 | 剪映 | 中文克隆成本低 + 拖拽快出 |
| 批量模板化 | CosyVoice | Remotion | 程序化可版本管理、批量 |
| 完全离线零外网 | GPT-SoVITS | ffmpeg | 本地零云 + 极简合成 |
| 口播 IP 人设 | CosyVoice | 数字人 | 情感/指令 + 出镜感 |
| 中文专属 + 程序化 | 百炼 | Remotion | 中文克隆 + 模板批量 |

---

## 11. 批量流水线

遍历 `optimized_script` 列表 → `dub()` → `render()` → 质量自检 → 落盘。含并发与限速提示：

```python
import concurrent.futures as cf
from pathlib import Path

def produce_one(item: dict) -> dict:
    """单条出片：配音 → 渲染 → 自检。失败不影响其他条。"""
    try:
        audio = dub(text=item["text"],
                    method=item.get("dubbing_method", "cosyvoice"),
                    language="zh")
        video = render(audio["audio_path"],
                       channel=item.get("render_channel", "jianying"),
                       shots=item.get("shot_plan"),
                       aspect_ratio=item.get("aspect_ratio", "9:16"),
                       ai_label_config=item.get("ai_label_config"))
        # 质量自检（见 §13）
        assert Path(video["video_path"]).exists(), "成片缺失"
        return {"ok": True, "video": video["video_path"], "item": item["id"]}
    except Exception as e:
        # E006：单条失败隔离，记录后继续
        return {"ok": False, "error": str(e), "item": item.get("id")}

def batch_pipeline(items: list, max_workers: int = 2, rate_limit: float = 0.2):
    """批量出片。max_workers 控制并发，rate_limit 控制云端 TTS 限速（秒/条）。"""
    results = []
    with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(produce_one, it): it for it in items}
        for fut in cf.as_completed(futures):
            res = fut.result()
            results.append(res)
            if not res["ok"]:
                print(f"[WARN] 单条失败隔离: {res}")
            # 云端 TTS（百炼/ CosyVoice）建议加限速，避免触发限流
            import time; time.sleep(rate_limit)
    ok = sum(1 for r in results if r["ok"])
    print(f"批量完成：{ok}/{len(results)} 成功")
    return results

# 用法
# batch_pipeline(optimized_script_list, max_workers=2, rate_limit=0.2)
```

> 并发提示：本地 GPU 配音（GPT-SoVITS / VoxCPM2 / CosyVoice）建议 `max_workers=1~2` 避免显存争用；云端 TTS 用 `rate_limit` 限速防限流。

---

## 12. 与中游 handoff 完整对接示例

中游 `douyin-script-optimizer` 产出的 handoff JSON（节选），引擎直接消费：

```json
{
  "optimized_script": "今天教你三招提升完播率。第一，前 3 秒抛钩子；第二，每 5 秒一个视觉爆点；第三，结尾强引导。点下方小黄车，三招带走。",
  "title_options": ["三招提升完播率", "完播率低的救星来了"],
  "shot_plan": [
    {
      "beat": 0,
      "visual_prompt": "主播特写、手指向前勾引动作、背景虚化",
      "source": "ai_gen",
      "duration_sec": 3.0
    },
    {
      "beat": 1,
      "visual_prompt": "手机屏幕录制完播率数据曲线上升动画",
      "source": "asset_pool",
      "duration_sec": 4.0
    },
    {
      "beat": 2,
      "visual_prompt": "小黄车购物车图标弹窗特写、暖光",
      "source": "ai_gen",
      "duration_sec": 3.5
    }
  ],
  "dubbing_method": "cosyvoice",
  "render_channel": "jianying",
  "aspect_ratio": "9:16",
  "digital_human": false,
  "publish_platform": "douyin",
  "ai_label_config": {
    "mode": "overlay",
    "duration_sec": 3,
    "text": "本视频含 AI 生成内容"
  }
}
```

**引擎如何消费它产出成片**：
1. 取 `optimized_script` + `dubbing_method="cosyvoice"` → 调 `dub()` → 得 48k wav + 实际 `duration_sec`（见 §8.7 回写 `shot_plan` beat 边界）。
2. 取 `render_channel="jianying"` + `shot_plan` + `ai_label_config` → 调 `render()` → 剪映按 beat 铺轨道、叠加前 3 秒 AI 标识 → 得 `1080x1920` 成片。
3. 过 §13 质量门 → 落盘交付。

---

## 13. 统一质量门 + 出片自检总卡

**统一质量门**（所有通道共性项 + 数字人专属项）：
- [ ] 音频 48k / 16bit wav，时长与脚本匹配（偏差 <±1s）
- [ ] 成片尺寸 = `aspect_ratio`（9:16 → 1080x1920）
- [ ] 前 5 秒含可见 AI 标识 ≥3 秒
- [ ] 无私域导流信息（上游闸门已判，引擎执行）
- [ ] 字幕 / 口型与配音对齐（字幕、数字人场景必查）
- [ ] **数字人专属**：肖像已授权、口型同步误差可接受、无未授权人脸

**出片自检总卡**（交付前逐项过）：
- [ ] 音频 48k wav、时长与脚本匹配
- [ ] 成片尺寸 = aspect_ratio
- [ ] 前 5 秒含可见 AI 标识 ≥3 秒
- [ ] 无私域导流信息
- [ ] 口型 / 字幕与配音对齐（数字人 / 字幕场景）
- [ ] 数字人肖像授权链完整（数字人通道）
- [ ] 逐拍听：听到 A、画面也在 A（剪映 / Remotion 通道）

---

## 14. Hard Constraints / Scope Boundary / Known Limitations

**Hard Constraints**：
- 不写最终口播稿（那是上游 / 中游的事）。
- 配音输出必须先归一化 48k wav 再进通道。
- `ai_label_config` 未提供时，默认在前 5 秒叠加可见 AI 标识（≥3 秒）。
- 数字人通道必须基于授权肖像，禁止未授权人脸。

**Scope Boundary**：
- 做：配音 + 合成 + 横竖屏 + 标识埋点 + 数字人驱动。
- 不做：选题 / 脚本撰写 / 流量运营 / 投放（上游中游负责）。

**Known Limitations**：
- 剪映通道依赖本机剪映，**无 GUI 环境跑不了**（需降级到 ffmpeg / Remotion）。
- Remotion 通道需 Node.js（≥18）环境，首包下载慢。
- ffmpeg 通道无模板动效，需自管素材。
- 数字人质量受制于驱动素材；口型同步非 100% 完美。
- 跨账号结构雷同风险由上游矩阵闸门判定，引擎只执行。

---

## 15. 新手 5 件事 / references 指引

**新手 5 件事**：
1. 先确认至少一种 TTS 后端已就绪（见 §8 部署命令）。
2. 默认 `cosyvoice` + `jianying` + `9:16` 跑通一条。
3. 用 `ffmpeg` 通道验证本地合成链路（零云依赖，最快）。
4. 确认 `ai_label_config` 生效（前 5 秒标识）。
5. 跑质量自检总卡（§13）再交付。

**references 指引**：
- `references/dubbing-methods.md`：四种 TTS 部署范式（百炼 / GPT-SoVITS / VoxCPM2 / CosyVoice）的 conda 部署、推理 CLI、调用示例、统一接口映射、ffmpeg 48k 归一化小节、输出规范。
- `references/render-channels.md`：四个渲染通道（剪映 / Remotion / ffmpeg / 数字人）的代码级深潜——OpenAPI 字段映射、完整 Remotion 工程、ffmpeg cookbook、数字人驱动步骤清单。

---

## 16. Quick Start / Customization Guide

**Quick Start**：

```python
# 最小出片：配音 + 渲染
audio = dub("今天教你三招…", method="cosyvoice", language="zh")
video = render(audio["audio_path"], channel="jianying",
               aspect_ratio="9:16",
               ai_label_config={"mode": "overlay", "duration_sec": 3})
print(video["video_path"], video["resolution"])
```

**Customization Guide**：
- 换音色：在 `dub()` 传 `reference_audio`（GPT-SoVITS / 百炼）或 `speaker_id`（VoxCPM2）或 `emotion`/`instruct`（CosyVoice）。
- 换通道：传 `render(channel="remotion" | "ffmpeg" | "digital_human")`。
- 批量：循环 / `batch_pipeline()`（见 §11），并发与限速按环境调。
- 换尺寸：传 `aspect_ratio="1:1" | "16:9"`。
- 数字人：传 `render(channel="digital_human", ai_label_config={..., "portrait": "authorized.jpg"})`。

---

## 17. Error Code

| 码 | 含义 | 处置 |
|----|------|------|
| E001 | 无可用 TTS 后端 | 装 CosyVoice 或本地 GPT-SoVITS / VoxCPM2 / 百炼 |
| E002 | 音频非 48k | 用 §8.7 / render-channels ffmpeg 归一化重采样 |
| E003 | 通道依赖缺失 | 细分：剪映缺失→装剪映；Remotion→装 Node+@remotion/cli；数字人→装运行时；否则降级 ffmpeg |
| E004 | ai_label 未生效 | 强制叠加前 5 秒标识（overlay / burn_sub） |
| E005 | 数字人未授权肖像 | 终止出片，补齐授权后再跑 |
| E006 | 批量中单条失败 | 隔离该条（见 §11 `produce_one` 异常捕获），继续其余 |

---

## 18. FAQ

- Q: 能完全离线吗？ A: 能，用本地 GPT-SoVITS + ffmpeg 通道（配音与合成均零外网）。
- Q: 默认配音是哪个？ A: CosyVoice（多语/情感/指令，开源生态好）。
- Q: 能用百炼配音吗？ A: 能，`method='baike'`，需开通阿里云百炼声音克隆；中文音色与成本优于多数方案。
- Q: 四种配音怎么选？ A: 中文克隆低成本→百炼；稳定人设/离线→GPT-SoVITS；批量轻量→VoxCPM2；情感/跨语言/通用→CosyVoice。
- Q: 数字人要授权吗？ A: 必须基于授权肖像，禁止未授权人脸（E005）。
- Q: Remotion 中文显示方块？ A: 需显式 `@font-face` 加载中文字体（如 Noto Sans SC）并在组件指定 `fontFamily`。
- Q: ffmpeg 字幕乱码？ A: 烧录时指定中文 `FontName`（如 `force_style='FontName=Noto Sans SC'`），并保证 srt 为 UTF-8。
- Q: 批量会互相影响吗？ A: 不会，单条失败由 E006 隔离（见 §11）。
- Q: 时长对不上剪映？ A: 先跑 TTS 取实际时长（ffprobe），回写 beat 边界，偏差 >±1s 返工（§8.7）。
- Q: 四个通道怎么组合？ A: 见 §10 决策树与推荐组合表。

---

## 19. Quality Commitment / Success Validation Checklist

**Quality Commitment**：不达质量自检总卡（§13）的不交付；标识 / 合规由上游闸门把关，引擎保证执行埋点。

**Success Validation Checklist**：
- [ ] 输入字段完整（至少 text + dubbing_method）
- [ ] 配音成功且 48k
- [ ] 成片按尺寸产出（`render_channel` 生效）
- [ ] AI 标识埋点生效（前 5 秒 ≥3 秒）
- [ ] 自检总卡全过（含数字人授权项，如适用）
