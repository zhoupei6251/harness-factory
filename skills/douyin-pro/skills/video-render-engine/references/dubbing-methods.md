# 配音方式部署范式（dubbing-methods）

> 四种 TTS 后端统一到引擎的 `dub()` 接口。每条后端建议独立 conda 环境，输出统一归一化为 **48k / 16bit wav**。本文件在 SKILL.md §8 基础上补充**可运行片段**：百炼 SDK 调用、各本地后端的 conda 部署序列与推理 CLI、ffmpeg 48k 归一化小节。

---

## 1. 百炼（阿里云声音克隆）

**定位**：国产、国内直连、中文音色丰富、克隆成本低、合规无风险，是中文专属克隆音色的优选国产方案。

**开通步骤**：
- 开通阿里云百炼（通义）服务并创建 API Key。
- 准备一段授权清晰、无噪声的参考音频，训练专属克隆音色；或选用平台预置中文音色。
- 取得调用地址 / SDK 凭证（百炼 TTS API）。

**Python 最小调用片段**（dashscope / 阿里云 SDK 风格，以官方文档为准；需 `DASHSCOPE_API_KEY` 与 `voice_id`）：

```python
# 需 pip install dashscope（以官方文档为准）
import os
from dashscope import SpeechSynthesizer

os.environ["DASHSCOPE_API_KEY"] = "your_api_key"   # 替换为你的百炼 API Key

resp = SpeechSynthesizer.call(
    model="sambert-voiceclone",        # 声音克隆模型名，以官方为准
    text="今天教你三招…",
    voice="speaker_A",                 # 已训练的克隆音色 id / 平台音色 id
    sample_rate=48000,                 # 直接要 48k
    format="wav",
)
with open("out.wav", "wb") as f:
    f.write(resp.get_audio_data())     # 落盘为 48k wav
```

> ⚠️ 上述为通用 SDK 风格示意，具体 `model` / 方法名 / 参数以阿里云百炼官方文档为准；API Key 切勿硬编码进仓库，用环境变量注入。

**与统一 `dub()` 接口映射**：
- `method="baike"` 选择百炼后端；其余参数（`text` / `reference_audio` / `language` / `speed`）与 GPT-SoVITS 等一致。
- 输出同样归一化 48k / 16bit wav，渲染通道无需关心来源。

**已知坑点**：
- 字符清洗：`optimized_script` 送入前必须去除 Markdown 符号 / Emoji / 装饰字符（见 SKILL.md「§8.6 共享坑·字符清洗」），否则会被念出或报错。
- 时长偏差：百炼实际合成常有 ±10% 偏差，绝不能用 `estimated_duration` 直接对齐剪映；先跑 TTS 取实际音频、用 ffprobe 取精确时长再回写 beat 边界。

---

## 2. GPT-SoVITS（本地 · 固定人设音）

**定位**：音色最稳、可完全离线，适合需要稳定"人设 IP"的账号。

**conda 部署完整命令序列**：

```bash
# 1) 建独立环境（Python 3.9，官方推荐）
conda create -n gptsovits python=3.9 -y
conda activate gptsovits

# 2) 克隆仓库并安装依赖（以官方仓库 README 为准）
git clone https://github.com/RVC-Boss/GPT-SoVITS.git
cd GPT-SoVITS
pip install -r requirements.txt

# 3) 准备参考音频（无噪单人声），放 ./raws/speaker_A.wav
mkdir -p raws && cp /path/to/ref.wav raws/speaker_A.wav

# 4) 预处理 + 微调（命令名以官方 docs 为准，此处为范式）
python tools/preprocess_text.py --text "参考文本…" --language zh
python tools/extract_feature.py
python tools/train_gpt.py
python tools/train_sovits.py
# 产物：./weights/speaker_A.pt（固定音色，务必锁定 speaker）
```

**本地推理 CLI 示例**（范式，参数名以本地推理脚本为准）：

```bash
conda activate gptsovits
python inference.py \
    --method gptsovits \
    --text "今天教你三招提升完播率" \
    --reference_audio ./weights/speaker_A.pt \
    --output ./out.wav
```

**调用示例（统一接口映射）**：
```python
dub(
    text="今天教你三招…",
    method="gptsovits",
    reference_audio="speaker_A.pt",   # 已微调的固定音色
    language="zh",
    speed=1.0,
)
```

**已知坑点**：
- 参考音频需无噪声、单人声；混音会污染音色。
- 首次微调务必锁定 `speaker` 避免后续漂移。
- 输出采样率可能与 48k 不一致 → 必须重采样归一化（见文末 ffmpeg 小节）。

---

## 3. VoxCPM2（轻量 · 快速）

**定位**：资源占用低、延迟小，适合批量、对强人设无要求的场景。

**conda 部署完整命令序列**：

```bash
# 1) 独立环境（Python 3.10，通常比 GPT-SoVITS 更轻）
conda create -n voxcpm2 python=3.10 -y
conda activate voxcpm2

# 2) 安装 VoxCPM2 及依赖（以实际仓库 README 为准）
git clone https://github.com/your-org/VoxCPM2.git   # 占位，请替换为实际仓库
cd VoxCPM2
pip install -r requirements.txt

# 3) 加载预训练多说话人模型，按 speaker_id 选声（无需微调）
```

**本地推理 CLI 示例**：

```bash
conda activate voxcpm2
python inference.py \
    --method voxcpm2 \
    --text "点下方小黄车下单" \
    --speaker_id speaker_A \
    --output ./out.wav
```

**调用示例（统一接口映射）**：
```python
dub(
    text="点下方小黄车…",
    method="voxcpm2",
    reference_audio=None,             # 用 speaker_id 选声
    language="zh",
    speed=1.05,
)
```

**已知坑点**：
- 跨说话人音质差异大，批量时固定 `speaker_id` 保证一致性。
- 长文本可能截断 → 按标点切句后拼接（见 SKILL.md §8.7 切句思路）。
- 同样需归一化到 48k。

---

## 4. CosyVoice（默认 · 多语 / 情感 / 指令）

**定位**：多语言、情感控制、自然语言指令（instruct）能力强，开源生态好，是引擎默认后端。

**conda 部署完整命令序列**：

```bash
# 1) 独立环境（Python 3.10）
conda create -n cosyvoice python=3.10 -y
conda activate cosyvoice

# 2) 安装 CosyVoice（通义开源版）
git clone https://github.com/FunAudioLLM/CosyVoice.git
cd CosyVoice
pip install -r requirements.txt

# 3) 下载模型权重（需国内直连或已缓存）
#    （权重拉取命令以官方仓库为准）
```

**本地推理 CLI 示例**（三模式）：

```bash
conda activate cosyvoice

# 基础
python inference.py --method cosyvoice --text "欢迎来到我的直播间" --output a.wav

# 带情感
python inference.py --method cosyvoice --text "这个真的绝了" --emotion "开心" --output b.wav

# 带指令
python inference.py --method cosyvoice --text "三招搞定" \
    --instruct "用兴奋、带货催促的语气" --output c.wav
```

**调用示例（统一接口映射）**：
```python
# 基础
dub(text="欢迎来到我的直播间", method="cosyvoice", language="zh")

# 带情感
dub(text="这个真的绝了", method="cosyvoice", emotion="开心", language="zh")

# 带指令
dub(text="三招搞定", method="cosyvoice",
     instruct="用兴奋、带货催促的语气", language="zh")

# 跨语言
dub(text="Hello everyone", method="cosyvoice", language="en")
```

**已知坑点**：
- 首次需下载模型权重，确保国内直连或已缓存。
- `instruct` 模式对指令措辞敏感，建议沉淀几条有效指令模板。
- 输出同样归一化 48k 后入通道。

---

## 5. ffmpeg 统一归一化 48k 一条命令

所有后端输出在进入渲染通道前，**统一重采样到 48k / 16bit 单声道 wav**：

```bash
# 任意后端输出 → 标准 48k / 16bit / 单声道 wav
ffmpeg -i in.mp3 -ar 48000 -ac 1 -c:a pcm_s16le out.wav

# 若是 m4a / ogg 同理
ffmpeg -i in.m4a -ar 48000 -ac 1 -c:a pcm_s16le out.wav

# 批量（bash 循环）
for f in raw_*.mp3; do
  ffmpeg -i "$f" -ar 48000 -ac 1 -c:a pcm_s16le "norm_${f%.mp3}.wav"
done
```

> 归一化后所有后端输出均为 48k / 16bit wav，渲染通道无需关心音色来源。

---

## 统一接口映射总表

| 引擎参数 | 百炼 | GPT-SoVITS | VoxCPM2 | CosyVoice |
|---------|------|-----------|---------|-----------|
| 音色来源 | 百炼克隆音色 / 平台音色 | `reference_audio`(微调) | `speaker_id` | 默认模型 / `reference_audio` |
| 情感 | ⚠️ 部分音色支持 | ❌ | ❌ | `emotion` ✅ |
| 指令 | ❌ | ❌ | ❌ | `instruct` ✅ |
| 离线 | ❌ 需国内直连 | ✅ | ✅ | ⚠️ 需权重缓存 |
| 归一化 | 重采样→48k | 重采样→48k | 重采样→48k | 重采样→48k |

## 输出规范（所有后端一致）

```json
{
  "audio_path": "out.wav",
  "duration_sec": 12.3,
  "sample_rate": 48000,
  "method_used": "cosyvoice",
  "alignment": [ {"char": "你", "start": 0.2, "end": 0.5} ]
}
```

> 归一化后所有后端输出均为 48k / 16bit wav，渲染通道无需关心来源。
