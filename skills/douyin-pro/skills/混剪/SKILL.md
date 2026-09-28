---
name: douyin-montage
description: |
  抖音短视频生产专家团·素材混剪层。负责把原始实拍/下载素材做 AI 高光提取 + 自动粗剪，
  输出带时间戳的 clip_segments，再交给中游脚本优化器写口播、下游渲染通道出片。
  核心工具：zhouxiaoka/autoclip（AI-powered video clipping & highlight generation）。
  触发词：混剪、高光提取、自动剪辑、二创、素材粗剪、autoclip、clip_segments。
agent_created: true
version: "1.0.0"
changelog:
  - version: "1.0.0"
    date: "2026-07-27"
    changes:
      - "【新增模块】对接 zhouxiaoka/autoclip，补齐 douyin-video-skill 缺少的'智能选片/混剪'能力。"
      - "【字段规范】定义 clip_segments 标准输出，直接喂给脚本优化器和渲染通道。"
---

# 抖音素材混剪 · douyin-montage

> 流水线的 **素材预处理环节**。当你手里有原始视频（自己拍的、下载的、直播回放），不知道该剪哪段时，先用它自动挑高光；挑完再交给脚本层写口播，最后走 剪映 / ffmpeg / Remotion 出片。

## 定位

```
采集/原始素材 → 【混剪层】→ 脚本优化 → 绘影/素材准备 → 渲染引擎 → MP4
                 ↑
            AI 高光提取 + 自动粗剪
```

**本层不做的事**：不写口播、不生成画面、不做精修字幕。只负责**把长视频剪成短片段**。

## 核心工具：autoclip

- 仓库：[zhouxiaoka/autoclip](https://github.com/zhouxiaoka/autoclip)
- 能力：AI 高光提取、自动剪辑二创、智能找精彩片段
- 输出：带分数的 clip 时间戳列表

## 安装（一次性）

```bash
# 1. 克隆仓库
git clone https://github.com/zhouxiaoka/autoclip.git

# 2. 进入目录并安装依赖（以仓库 README 为准）
cd autoclip
pip install -r requirements.txt

# 3. 下载所需模型（如有）
# 详见 autoclip 官方 README
```

## 标准输出格式

混剪层必须输出 `clip_segments.json`：

```json
{
  "source_video": "raw/live_20260727.mp4",
  "total_duration_sec": 186.5,
  "method": "autoclip",
  "clips": [
    {
      "clip_id": 0,
      "start": 12.3,
      "end": 18.7,
      "duration_sec": 6.4,
      "score": 0.91,
      "description": "主播展示产品核心卖点"
    },
    {
      "clip_id": 1,
      "start": 45.0,
      "end": 52.5,
      "duration_sec": 7.5,
      "score": 0.88,
      "description": "用户痛点场景"
    }
  ]
}
```

| 字段 | 说明 | 下游消费 |
|------|------|---------|
| `start` / `end` | 片段在原视频中的起止时间（秒） | 渲染层切镜 / ffmpeg concat |
| `score` | AI 高光分数（0-1） | 脚本层优先选高分片段 |
| `description` | 片段内容摘要 | 脚本层写口播参考 |
| `duration_sec` | 片段时长 | 脚本层控制总时长 |

## 与下游的衔接

### → 脚本优化器

把 `clip_segments.json` 作为 `materials` 的一部分传给 抖音脚本优化器：

```python
{
  "topic": "雪螺王茉莉花茶冷启动",
  "content_type": "种草",
  "video_duration": 45,
  "materials": {
    "clip_segments": "clip_segments.json",
    "raw_video": "raw/live_20260727.mp4"
  }
}
```

脚本优化器会：
1. 按 `score` 排序，优先挑高分片段；
2. 按 `video_duration` 控制总时长，自动取舍；
3. 基于 `description` 写每段口播；
4. 输出带 `source="video_clip"` 的 `shot_plan`。

### → 渲染引擎

`shot_plan` 中 `source="video_clip"` 的槽，渲染层按 `start/end` 从原视频裁切：

```bash
# ffmpeg 裁切单段
ffmpeg -ss 12.3 -to 18.7 -i raw/live_20260727.mp4 -c copy clip_0.mp4
```

裁切好的片段可直接：
- 喂给 `jianying` 通道精修；
- 用 `ffmpeg` 通道直接 concat 成片；
- 作为 `remotion` 通道的 `image`/`video` 素材（需额外适配）。

## 快速使用

### 方式 A：直接调 autoclip（以官方 CLI 为准）

```bash
cd autoclip
python main.py --input /path/to/raw.mp4 --output /path/to/clip_segments.json
```

### 方式 B：用 skill 包装脚本（推荐）

```bash
python scripts/run_autoclip.py \
  --input raw/live_20260727.mp4 \
  --output clip_segments.json \
  --top-k 5
```

脚本会：
1. 检查 autoclip 是否已克隆；
2. 调 autoclip 生成原始结果；
3. 归一化为标准 `clip_segments.json`。

## 局限与注意

- autoclip 只做**选片**，不做**精修**；字幕、转场、BGM 仍需下游处理。
- 高光分数是参考，不是圣旨；重要片段若分数低，应人工补回。
- 素材合规：只用授权/自有素材，禁止直接搬运他人视频。
- 本层不处理口播稿，写好 clip 后必须进脚本层。

## 典型工作流

```
1. 上传直播回放 / 实拍素材
2. 运行 autoclip → clip_segments.json
3. 把 clip_segments 交给 抖音脚本优化器 → optimized_script + shot_plan
4. 配音（edge_tts / 百炼 / CosyVoice）
5. 渲染（剪映精修 / ffmpeg快速拼接 / Remotion模板化）
6. 质量门检查 → 发布
```

## 触发话术

- "我有一段直播回放，帮我挑高光剪成抖音"
- "用 autoclip 给这个视频做混剪"
- "把素材粗剪一下，再写口播"
- "从这段视频里提取精彩片段"
