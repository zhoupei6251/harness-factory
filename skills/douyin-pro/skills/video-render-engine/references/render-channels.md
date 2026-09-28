# 渲染通道深潜（render-channels）

> SKILL.md §9 的代码级补充。本文件给出四个渲染通道（剪映 / Remotion / ffmpeg / 数字人）的**完整可复制内容**：OpenAPI 字段映射、完整 Remotion 工程、ffmpeg cookbook、数字人驱动步骤清单。

---

## 1. 剪映（jianying）

### 1.1 shot_plan → 剪映轨道字段映射

中游 `shot_plan` 每个 beat 映射为一条剪映轨道片段：

| shot_plan 字段 | 剪映轨道含义 | 说明 |
|----------------|--------------|------|
| `beat` | 片段序号 / 轨道索引 | 决定铺轨顺序 |
| `visual_prompt` | 素材检索 / 生图提示词 | 必须具体，禁泛描述 |
| `source` | 素材来源 | `asset_pool`（素材库）/ `ai_gen`（AI 生图） |
| `duration_sec` | 片段时长（秒） | 必须对应 TTS 实际音频时长回写值（见 SKILL §8.7） |

### 1.2 OpenAPI / 命令行映射范式

```python
# 将 shot_plan 映射为剪映可消费的工程 JSON（范式，字段以剪映 OpenAPI 为准）
import json

def shot_plan_to_jianying(shot_plan: list, audio_path: str) -> dict:
    tracks = []
    t = 0.0
    for beat in shot_plan:
        dur = beat["duration_sec"]
        tracks.append({
            "track_index": beat["beat"],
            "start": t,
            "duration": dur,
            "material": {
                "type": beat["source"],          # asset_pool / ai_gen
                "prompt": beat["visual_prompt"],
            },
        })
        t += dur
    project = {
        "audio": audio_path,
        "tracks": tracks,
        "aspect_ratio": "9:16",
        "ai_label": {"mode": "overlay", "duration_sec": 3},
    }
    with open("jianying_project.json", "w", encoding="utf-8") as f:
        json.dump(project, f, ensure_ascii=False, indent=2)
    return project

# shot_plan_to_jianying(shot_plan, audio["audio_path"])
```

### 1.3 常见模板

- **带货快出模板**：口播轨 + 商品特写轨 + 小黄车弹窗 + 转场「闪白」。
- **知识口播模板**：主播特写 + 数据截图 + 关键词字幕条。
- **Vlog 模板**：AI 生图序列 + 轻音乐垫底 + Ken Burns 缓动。

---

## 2. Remotion（remotion）

> **完整可跑工程**：`templates/remotion/`（含 package.json / tsconfig / src / public / README）。
> **自动编排脚本**：`scripts/render_remotion.py`（读 shot_plan + image_map + 音频 → 输出 MP4）。
> 下面给出工程关键片段，便于理解或二次开发。

### 2.1 完整 package.json

```json
{
  "name": "douyin-remotion-template",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "studio": "remotion studio src/index.tsx",
    "render": "remotion render src/index.tsx DouyinVideo out.mp4",
    "render:props": "remotion render src/index.tsx DouyinVideo out.mp4 --props=props.json"
  },
  "dependencies": {
    "@remotion/cli": "4.0.240",
    "@remotion/core": "4.0.240",
    "@remotion/player": "4.0.240",
    "react": "18.3.1",
    "react-dom": "18.3.1"
  },
  "devDependencies": {
    "@types/react": "18.3.12",
    "@types/web": "0.0.166",
    "typescript": "5.6.3"
  }
}
```

### 2.2 可跑的 src/index.tsx（含 `<Audio>`、`<Sequence>` 按 beat 切镜、中文字体）

```tsx
import React from "react";
import {
  Composition,
  Sequence,
  Audio,
  Img,
  AbsoluteFill,
  staticFile,
} from "remotion";

// 中文字体需显式 @font-face 引入（把 NotoSansSC.woff2 放 public/）
const fontStyle = {
  fontFamily: "Noto Sans SC",
  color: "white",
};

// 单 beat 画面：按 shot_plan 渲染对应素材
const BeatScene: React.FC<{ prompt: string; src: string }> = ({ prompt, src }) => (
  <AbsoluteFill style={{ ...fontStyle, justifyContent: "center", alignItems: "center" }}>
    <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
    <AbsoluteFill style={{ bottom: 80, left: 40, fontSize: 48, textShadow: "0 2px 8px #000" }}>
      {prompt}
    </AbsoluteFill>
  </AbsoluteFill>
);

// 主合成：遍历 shot_plan 用 <Sequence> 按 beat 切镜
export const DouyinVideo: React.FC<{ shots?: any[] }> = ({ shots = [] }) => {
  const fps = 25;
  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <Audio src={staticFile("audio.wav")} />
      {shots.map((beat) => (
        <Sequence
          key={beat.beat}
          from={Math.round(beat.beat * 5 * fps)}   // 每 beat 约 5s 起始
          durationInFrames={Math.round(beat.duration_sec * fps)}
        >
          <BeatScene prompt={beat.visual_prompt} src={`beat_${beat.beat}.png`} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="DouyinVideo"
    component={DouyinVideo}
    durationInFrames={300}   // 12s @ 25fps，按实际音频调整
    fps={25}
    width={1080}
    height={1920}
    defaultProps={{ shots: [] }}
  />
);
```

### 2.3 渲染命令

```bash
# 安装依赖
cd templates/remotion
npm install

# 本地预览 Studio（调试分镜）
npx remotion studio src/index.tsx

# 用真实数据渲染：先写 props.json，再执行
npm run render:props

# 或通过 skill 脚本全自动编排
python scripts/render_remotion.py \
  --shot-plan shot_plan.json \
  --image-map image_map.json \
  --audio out.wav \
  --output final.mp4
```

> 中文字体：模板已在 `public/style.css` 内置 `@font-face` 回退链（Noto Sans SC → Microsoft YaHei → PingFang SC）。如仍方块，把 `NotoSansSC.woff2` 放 `public/` 即可。

### 2.4 自动编排脚本参数

```bash
python scripts/render_remotion.py \
  --shot-plan shot_plan.json      # 中游 shot_plan（必须）
  --image-map image_map.json      # beat_index -> image_path（必须）
  --audio out.wav                 # 48k 配音（必须）
  --output final.mp4              # 输出路径（默认 out.mp4）
  --aspect-ratio 9:16             # 9:16 / 1:1 / 16:9
  --ai-label-duration 3           # AI 标识显示秒数
  --ai-label-text "本视频含 AI 生成内容"
  --title "片头标题"
```

---

## 3. ffmpeg（ffmpeg）

> cookbook：每条带说明。所有合成前请确保音频已 48k 归一化（见 dubbing-methods.md §5）。

### 3.1 图片序列 → 视频（配音）

```bash
# 25fps，图片命名 img001.png / img002.png ...
ffmpeg -r 25 -i img%03d.png -i audio.wav -c:v libx264 -pix_fmt yuv420p out.mp4
```

### 3.2 横竖屏 9:16（scale + 居中 crop）

```bash
# 任意输入 → 1080x1920，保持比例并黑边填充
ffmpeg -i in.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2" -c:a copy out_9x16.mp4
```

### 3.3 字幕烧录（中文需指定字体）

```bash
# sub.srt 需 UTF-8；FontName 必须含中文
ffmpeg -i out.mp4 -vf "subtitles=sub.srt:force_style='FontName=Noto Sans SC,FontSize=36'" -c:a copy out_sub.mp4
```

### 3.4 音频 48k 归一化

```bash
# 任意音频 → 48k / 16bit / 单声道 wav
ffmpeg -i in.mp3 -ar 48000 -ac 1 -c:a pcm_s16le out.wav
```

### 3.5 拼接多个片段

```bash
# 先生成片段列表 list.txt：file 'part1.mp4' / file 'part2.mp4'
ffmpeg -f concat -safe 0 -i list.txt -c copy merged.mp4
```

### 3.6 烧录 AI 标识（前 5 秒叠加文字）

```bash
# 用 drawtext 在前 3 秒叠加 "本视频含 AI 生成内容"
ffmpeg -i out.mp4 -vf "drawtext=text='本视频含 AI 生成内容':fontfile=NotoSansSC.ttf:fontsize=48:fontcolor=white:x=(w-text_w)/2:y=h-120:enable='between(t,0,3)'" -c:a copy out_label.mp4
```

> 坑点：务必 `-pix_fmt yuv420p`，否则抖音无法上传；字幕 / 标识字体文件需本地存在。

---

## 4. 数字人（digital_human）

### 4.1 驱动步骤清单（国产方案如 HeyGem 范式）

1. **授权确认**：取得肖像权人书面授权，记录授权链（红线，缺则 E005 终止）。
2. **准备素材**：
   - 授权肖像图（高清、正脸、光照均匀）**或** 驱动视频（授权真人视频）；
   - 已生成的 48k 配音 `out.wav`（见 dubbing-methods.md）。
3. **执行驱动**（命令行范式，以实际工具为准）：

```bash
# 音频 + 肖像 → 口型同步数字人视频
python digital_human_drive.py \
    --audio out.wav \
    --portrait authorized_speaker.jpg \
    --output digital_human.mp4

# 或音频 + 驱动视频（替换口型与声音）
python digital_human_drive.py \
    --audio out.wav \
    --drive_video ref_clip.mp4 \
    --output digital_human.mp4
```

4. **输出后处理**：
   - 叠加前 5 秒 AI 标识（`ffmpeg drawtext`，见 §3.6）；
   - 转 9:16 竖屏（见 §3.2）；
   - 抽检口型同步误差，长句末端漂移明显则重驱。

### 4.2 输入要求

| 输入 | 要求 |
|------|------|
| 肖像图 | 授权、高清、正脸、光照均匀、无遮挡 |
| 驱动视频 | 授权、清晰、口型幅度明显便于驱动 |
| 配音 | 48k / 16bit / 单声道 wav，与口播稿一致 |

### 4.3 输出后处理要点

- 必须叠加 AI 标识（前 5 秒 ≥3 秒可见）。
- 统一转 9:16 竖屏适配抖音。
- 口型同步非 100% 完美，长句末端易漂移，需人工抽检。
- 成片入库前过 §13 质量门（数字人授权项必查）。
