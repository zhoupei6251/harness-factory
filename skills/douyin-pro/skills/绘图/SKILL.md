---
name: douyin-image-generator
description: 抖音短视频生产专家团·图像层（生产级 5.0）。双向采图：① AI 生成模式（可切换 HY-Image-V3.0 / HY-Image-Lite / ImageGen / ImageEdit / HY-Video-1.5 / YT-Video-2.0 / YT-Video-HumanActor / YT-Video-FX / 3D 模型 共九种模型，统一 generate_assets() 入口，图/视频/3D 全模型覆盖） ② 素材摄入模式（真实图片/视频帧上传后自动按 shot_plan beat 映射）。输出 asset_map.json 对接下游渲染引擎。触发词："绘图""AI生图""素材摄入""配图生成""切换生图模型""上传素材匹配"。
agent_created: true
version: "5.0.0"
changelog:
  - version: "5.0.0"
    date: "2026-07-22"
    changes:
      - "初始版本：双向采图——AI 生成（全模型可切换）+ 素材摄入（自动映射）。统一 generate_assets() 和 ingest_assets() 入口，支持图像/视频/3D 全模型，输出 asset_map.json 对接下游渲染。"
---

# 抖音短视频生产专家团 · 图像层（绘影）

> **生产级 5.0，自包含图像采编引擎**。不写口播、不定策略、不做渲染——只负责一件事：把分镜描述（`shot_plan`）变成实际可用的图片文件。
> 本文件是图像层的主入口；下游渲染引擎（`skills/video-render-engine/SKILL.md`）通过 `image_map.json` 消费产出。

---

## 🚀 30 秒调用速查卡

**三种方式使用本技能**：

### 方式 A：一句话 AI 生图（最快）

直接说：
> "用 HY-Image-V3.0 给我的 shot_plan 批量生图，9:16 竖屏，风格是暖色调电影感"

绘影自动读 `shot_plan` → 逐槽调 `generate_assets()` → 产出 `image_map.json`。

### 方式 B：上传素材自动匹配

> "我有一组产品实拍图，帮我按 shot_plan 的 beat 自动匹配"

上传图片后，绘影跑 `ingest_assets()` → 自动按语义相似度/关键词映射 → 产出 `image_map.json`。支持手动覆盖。

### 方式 C：自由切换模型后批跑

> "切换到 ImageGen，然后重新跑整批生图"

随时切换模型，后续 `generate_assets()` 全部走新模型。

---

## ⚠️ 前置依赖

| 依赖 | 用途 | 缺失时 |
|------|------|--------|
| ImageGen 工具（WorkBuddy 内置） | AI 文生图/图生图 | 禁用 ImageGen / ImageEdit 模型，HY-Image 系列仍可用 |
| HY-Image 系列（WorkBuddy 多模态 Skill） | AI 生图（HY-Image-V3.0 / HY-Image-Lite） | 降级到 ImageGen 或仅走素材摄入模式 |
| 中游 `shot_plan`（含 `visual_prompt` + `source` + `suggested_channel`） | 分镜描述，生图/匹配的输入依据 | 无法运行——绘影不自行产生 visual_prompt |
| 素材摄入模式需用户上传图片/视频帧 | 真实图片映射 | 降级到纯 AI 生图模式 |

> 绘影层本身无外部 API 依赖，所有生图工具均为 WorkBuddy 内置。

---

## Overview / When to Use

### 四层架构中的位置

```
大脑层 → 中游 脚本优化器 → 绘影 图像层（本技能） → 下游 渲染引擎 → 成片
  定方向/合规              产出 shot_plan         图像采编             出片
```

| 层级 | 角色 | 核心任务 | 边界 |
|------|------|---------|------|
| 大脑层 | 策略+合规 | 定方向/选题/红线 | 不写口播、不画图 |
| 中游 | 脚本优化器 | 产出 optimized_script + shot_plan | 不做图像 |
| **绘影（本技能）** | **图像采编** | **shot_plan → 实际图片文件** | **不写稿、不配音、不渲染** |
| 下游 | 渲染引擎 | 配音+合成成片 | 只执行，不采图 |

### When to Use

- 已有 `shot_plan`，需要为每槽生成对应的 9:16 配图。
- 需要统一风格锚定，保证整批图片视觉一致。
- 手上有真实产品图/场景图，想自动匹配到对应 beat。
- 需要在不同生图模型间切换（免费额度 vs 高质量 vs 快速出图）。
- 数字人/纯口播场景 → 可跳过绘影（无图像需求）。

---

## 🇨🇳 国内全适配

**所有生图工具均为 WorkBuddy 内置**，无需外网注册/API Key/境外服务：

| 工具 | 调用方式 | 网络要求 |
|------|---------|---------|
| HY-Image-V3.0 | WorkBuddy 多模态 Skill / DeferExecute ImageGen | 国内直连 |
| HY-Image-Lite | WorkBuddy 多模态 Skill / DeferExecute ImageGen | 国内直连 |
| ImageGen | DeferExecute ImageGen | 国内直连 |
| ImageEdit | DeferExecute ImageGen（需传入基准图） | 国内直连 |

> 素材摄入模式纯本地文件操作，零网络依赖。

---

## Architecture（双向管道）

```
                    shot_plan（中游产出）
                    ├── visual_prompt
                    ├── source（ai_gen / asset_pool）
                    └── suggested_channel
                              │
                 ┌────────────┴────────────┐
                 │                         │
          source=ai_gen              source=asset_pool
                 │                         │
                 ▼                         ▼
    ┌────────────────────┐    ┌────────────────────┐
    │  AI 生图分支        │    │  素材摄入分支       │
    │  generate_assets()  │    │  ingest_assets()    │
    │  全模型可切换       │    │  自动映射 + 手动覆盖 │
    └────────────────────┘    └────────────────────┘
                 │                         │
                 └────────────┬────────────┘
                              ▼
                      image_map.json
                     （统一格式输出）
                              │
                              ▼
                       下游渲染引擎
                  （按 beat_index 取图）
```

---

## 双向采图模式 · 决策表

`shot_plan` 每槽的 `source` 字段决定走哪条分支：

| source 值 | 模式 | 行为 | 需要用户提供 |
|-----------|------|------|------------|
| `ai_gen` | AI 生图 | 调用 WorkBuddy 内置生图工具，按 `visual_prompt` 逐槽生成 | 无（可选指定模型和风格） |
| `asset_pool` | 素材摄入 | 匹配用户上传的真实图片，按语义映射到对应 beat | 图片文件（jpg/png，≥1080x1920） |

> 未明确 `source` 字段时，默认走 `ai_gen`（AI 生图）。用户可随时在单槽级别覆盖。

---

## 模式一：AI 生成（全模型切换）

### 模型切换 API

```python
generate_assets(shot_plan, model="hy-image-v3.0", style="电商产品摄影", aspect="9:16")
```

- `shot_plan`：中游产出的分镜列表（每槽含 `visual_prompt`）
- `model`：九种模型可选（见下方对比表），默认 `hy-image-v3.0`
- `style`：整批风格锚定词（追加到所有 `visual_prompt` 前缀）
- `aspect`：出图比例，默认 `9:16`（视频模型为 9:16 竖屏）

### 全模型对比表

**图模型（静态配图）**：

| 模型 | 调用方式 | 特点 | 适用场景 |
|------|---------|------|---------|
| **HY-Image-V3.0** | WorkBuddy 多模态 Skill / DeferExecute ImageGen | 80B 参数，千字语义，文字渲染精准 | 画面精细控制、含文字元素（标题卡片等） |
| **HY-Image-Lite** | WorkBuddy 多模态 Skill / DeferExecute ImageGen | 快速响应，轻量推理 | 快速原型、批量低价跑量 |
| **ImageGen** | DeferExecute ImageGen | 通用文生图 | 标准场景，无特殊需求 |
| **ImageEdit** | DeferExecute ImageGen（需传入基准图） | 基于已有图片二次创作 | 风格统一、迭代优化、以图改图 |

**视频模型（动态片段）**：

| 模型 | 调用方式 | 特点 | 适用场景 |
|------|---------|------|---------|
| **HY-Video-1.5** | DeferExecute VideoGen | 文生视频/图生视频，5-10秒，场景切换 | 动态画面：蒸汽升腾、茶水倾倒、火焰等需要动态的 beat |
| **YT-Video-2.0** | DeferExecute VideoGen | 图生视频，动态连贯，画面过渡自然 | 产品展示动效、图片转动态转场 |
| **YT-Video-HumanActor** | DeferExecute VideoGen | 单张照片驱动人像视频，还原表情姿态 | 人物出镜 beat（替代静态肖像） |
| **YT-Video-FX** | DeferExecute VideoGen | 图片特效模板（飘雪/变身/万物归尘等） | 特效 beat，增加视觉冲击力 |

**3D 模型**：

| 模型 | 调用方式 | 特点 | 适用场景 |
|------|---------|------|---------|
| **3D 模型生成** | WorkBuddy 多模态 Skill（文生3D/图生3D） | 生成可旋转 3D 模型 | 产品 3D 展示、立体化呈现 |

**模型切换命令示例**：
- "切换到 HY-Image-V3.0"（默认，最高画质静态图）
- "用 HY-Video-1.5 生成这段蒸汽镜头的动态视频"
- "切换到 YT-Video-2.0，把产品图转成动态展示"
- "用 ImageGen 快速出原型"
- "切 3D 模型，给这个产品生成 360 展示"
- "用 YT-Video-HumanActor，这个人设 beat 要动态出镜"
- "所有图用 hy-image-lite 快速跑，后面再换 V3.0 精修"

### 风格锚定

为整批生成注入统一的视觉风格，避免画面跳来跳去。做法：

**为所有 beat 共享一条 `style_anchor` 前缀**，如：
```
"暖色调、电影感、浅景深、电商产品摄影风格"
```

每槽 `visual_prompt` 实际送入生成工具的 prompt 变为：
```
{style_anchor} + "，" + {visual_prompt}
```

> 注意：视频模型的 prompt 需额外追加动态描述（如"5 秒循环、慢动作"），3D 模型需追加"纯色背景、产品居中"。

**风格锚定词库（四套常用预设）**：

| 风格预设 | style_anchor | 适用赛道 |
|---------|-------------|---------|
| 电商产品摄影 | "暖色调、浅景深、电商产品摄影风格、柔光箱打光" | 带货/种草 |
| 科技知识风 | "冷色调、干净线条、科技感、信息图风格" | 知识/教程 |
| 电影叙事感 | "电影感、自然光、中等对比度、纪实摄影风格" | 剧情/观点 |
| 清新生活风 | "自然光、柔和色调、生活场景、日系清新风格" | 美妆/生活方式 |

### 批量生成示例

```python
def generate_assets(shot_plan: list, model="hy-image-v3.0", style="", aspect="9:16"):
    """逐槽调用生成工具，落盘 beat_NNN.{png|mp4|glb}，返回 asset_map"""
    asset_map = {"source_mode": "ai_gen", "model_used": model, "beat_assets": []}
    for i, beat in enumerate(shot_plan):
        prompt = f"{style}，{beat['visual_prompt']}" if style else beat["visual_prompt"]
        # 根据模型类型确定后缀
        if model in ("hy-video-1.5", "yt-video-2.0", "yt-video-humanactor", "yt-video-fx"):
            asset_path = f"beat_{i:03d}.mp4"
        elif model == "3d":
            asset_path = f"beat_{i:03d}.glb"
        else:
            asset_path = f"beat_{i:03d}.png"
        # 调用 WorkBuddy 内置生成（伪代码）
        if model == "hy-image-v3.0":
            call_hy_image_v3(prompt, output=asset_path, aspect=aspect)
        elif model == "hy-image-lite":
            call_hy_image_lite(prompt, output=asset_path, aspect=aspect)
        elif model == "imagegen":
            call_imagegen(prompt, output=asset_path, aspect=aspect)
        elif model == "imageedit":
            base = beat.get("base_image") or asset_map["beat_assets"][0]["asset_path"]
            call_imageedit(prompt, base_image=base, output=asset_path, aspect=aspect)
        elif model == "hy-video-1.5":
            call_videogen(prompt, model="hy-video-1.5", duration=5, output=asset_path)
        elif model == "yt-video-2.0":
            call_videogen(prompt, model="yt-video-2.0", image=beat.get("base_image"), output=asset_path)
        elif model == "yt-video-humanactor":
            call_videogen(prompt, model="yt-video-humanactor", image=beat.get("portrait"), output=asset_path)
        elif model == "yt-video-fx":
            call_videogen(prompt, model="yt-video-fx", image=beat.get("base_image"), output=asset_path)
        elif model == "3d":
            call_3d_gen(prompt, output=asset_path)  # 多模态 Skill 图生3D/文生3D
        asset_map["beat_assets"].append({
            "beat_index": i,
            "beat_text": beat.get("beat_text", ""),
            "asset_path": asset_path,
            "asset_type": "video" if asset_path.endswith(".mp4") else ("3d" if asset_path.endswith(".glb") else "image"),
            "source": "ai_gen"
        })
    return asset_map
```

### AI 生图 · 质量自检

每批生成后，逐张检查：

- [ ] 风格一致性：所有图片视觉风格统一（色调/光线/质感）——抽查首/中/尾三张比对
- [ ] 分辨率：9:16 竖屏，宽度 ≥1080px（否则剪映/抖音上传拒收）
- [ ] 无崩图：无明显畸变/乱码/错误渲染（尤其含文字元素时）
- [ ] visual_prompt 耦合：画面内容与对应 beat 的口播文案语义匹配
- [ ] 文件完整：每槽都有对应图片文件落盘，无缺失

---

## 模式二：素材摄入（自动映射）

### 入口

```python
ingest_assets(images=["/path/to/photo1.jpg", "/path/to/photo2.jpg", ...], shot_plan=...)
```

- `images`：用户上传的图片/视频帧路径列表
- `shot_plan`：中游产出的分镜列表

### 自动映射逻辑

```python
def ingest_assets(images: list[str], shot_plan: list[dict]) -> dict:
    """遍历每槽 visual_prompt，用语义相似度匹配用户图片，输出 best-fit image_map"""
    image_map = {"source_mode": "asset_pool", "model_used": None, "beat_images": []}
    for i, beat in enumerate(shot_plan):
        if beat.get("source") != "asset_pool":
            continue  # 跳过 ai_gen 槽
        prompt = beat["visual_prompt"]
        # 提取 prompt 关键词（物体名/场景/颜色/动作）
        keywords = extract_keywords(prompt)
        # 基于文件名或图片内容（OCR/CLIP 等）匹配最佳图片
        best_match = find_best_match(keywords, images)
        image_map["beat_images"].append({
            "beat_index": i,
            "beat_text": prompt,
            "image_path": best_match["path"],
            "source": "asset_pool",
            "original_name": best_match.get("original_name", "")
        })
    return image_map
```

**匹配策略（按优先级）**：
1. **文件名关键词匹配**：如 `visual_prompt` 含"口红"，优先匹配文件名含"口红""唇膏""lipstick"的图片
2. **手动覆盖**：用户显式指定"beat_3 → photo2.jpg"，覆盖自动结果
3. **默认分配**：无法匹配时，按顺序分配剩余未用图片

### 手动覆盖

支持在 `ingest_assets()` 调用时传入 `overrides` 字典：

```python
ingest_assets(
    images=["photo1.jpg", "photo2.jpg", "photo3.jpg"],
    shot_plan=shot_plan,
    overrides={"beat_001": "photo2.jpg"}  # 强制指定
)
```

用户在对话中也可以直接说：
> "beat 第 3 个用 IMG_5402.jpg，beat 第 5 个用 product_shot.png"

### 素材摄入 checklist

- [ ] 分辨率 ≥ 1080x1920（竖屏最低要求，低于此分辨率剪映拉伸模糊）
- [ ] 比例 9:16（若有偏差需先裁剪/letterbox 后再摄入）
- [ ] 格式 jpg/png（不接受 bmp/tiff/webp 等非标准格式）
- [ ] 文件可读、无损坏（用 PIL/ImageMagick `identify` 预检）
- [ ] 图片内容合法（不含平台违规内容）

---

## 输出规范：image_map.json

两种模式产出**一致格式**的统一输出。下游渲染引擎只读这一个文件：

```json
{
  "source_mode": "ai_gen",
  "model_used": "hy-image-v3.0",
  "beat_images": [
    {
      "beat_index": 0,
      "beat_text": "主播特写、手指向前勾引动作、背景虚化",
      "image_path": "beat_000.png",
      "source": "ai_gen"
    },
    {
      "beat_index": 1,
      "beat_text": "手机屏幕录制完播率数据曲线上升动画",
      "image_path": "screenshot_001.jpg",
      "source": "asset_pool",
      "original_name": "IMG_5402.jpg"
    },
    {
      "beat_index": 2,
      "beat_text": "小黄车购物车图标弹窗特写、暖光",
      "image_path": "beat_002.png",
      "source": "ai_gen"
    }
  ]
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `source_mode` | enum | ✅ | `ai_gen` 或 `asset_pool`（整批主模式） |
| `model_used` | string/null | ✅ | 所用模型名；素材摄入模式为 null |
| `beat_images` | list[object] | ✅ | 每槽图片映射列表 |
| `beat_images[].beat_index` | int | ✅ | 对应 shot_plan 的索引（从 0 起） |
| `beat_images[].beat_text` | string | ✅ | 原 beat 文案（含 visual_prompt 片段） |
| `beat_images[].image_path` | string | ✅ | 图片文件路径（渲染引擎直接引用） |
| `beat_images[].source` | enum | ✅ | `ai_gen` 或 `asset_pool`（单槽粒度可覆盖整批模式） |
| `beat_images[].original_name` | string | ⬜ | 素材摄入模式下用户的原始文件名（可追溯） |

---

## 与上下游 handoff

### 中游 → 绘影：消费 shot_plan

绘影从主理人（司远）接收 `shot_plan`，只消费以下字段：

| shot_plan 字段 | 用途 | 必读 |
|---------------|------|------|
| `visual_prompt` | 生图 prompt 或素材匹配关键词 | ✅ |
| `source` | `ai_gen` / `asset_pool` —— 决定走哪条分支 | ✅ |
| `suggested_channel` | 仅供参考（不影响绘影决策） | ⬜ |

### 绘影 → 下游：输出 image_map.json

下游渲染引擎（`skills/video-render-engine/SKILL.md`）通过 `render()` 的 `shots` 参数消费：当 `image_map` 提供时，`render()` 直接按 `beat_index` 取图；不提供时，按原方式外部准备图片。

手交手流程：
```
中游（司远/润笔）--shot_plan--> 绘影 --image_map.json--> 下游渲染引擎
```

---

## Error Code

绘影层专属错误码（E201–E206）：

| 码 | 含义 | 处置 |
|----|------|------|
| **E201** | `shot_plan` 为空或缺失 `visual_prompt` | 退回中游补全 shot_plan 后再调用绘影 |
| **E202** | 生图模型调用失败（HY-Image/ImageGen 不可用） | 检查 WorkBuddy 多模态 Skill 是否就绪；降级到素材摄入模式或换模型 |
| **E203** | 单张图片生成失败（超时/崩图/格式异常） | 记录失败槽位 → 跳过该槽继续 → 生成后单独补跑失败槽 |
| **E204** | 素材图片分辨率不达标（<1080x1920） | 提示用户替换高分辨率素材或走 AI 生图补位 |
| **E205** | 素材匹配失败（无合适映射） | 输出未匹配槽位列表 → 提示用户手动指定或切换为 ai_gen |
| **E206** | `image_map.json` 输出不完整（有槽缺图） | 补跑缺失槽位 → 合并 → 重新输出完整 image_map |

---

## 故障恢复与降级策略

### 单槽失败恢复

```python
def retry_failed_beats(failed_indices: list[int], shot_plan, model, style):
    """仅重新生成失败槽位，不重跑全部"""
    for idx in failed_indices:
        beat = shot_plan[idx]
        prompt = f"{style}，{beat['visual_prompt']}" if style else beat["visual_prompt"]
        img_path = f"beat_{idx:03d}.png"
        call_model(prompt, model=model, output=img_path)
    # 合并回 image_map
```

### 模型降级链

当首选模型不可用时，自动降级：
```
HY-Image-V3.0 → HY-Image-Lite → ImageGen → (失败) → 提示用户切换素材摄入
```

用户也可主动设置降级策略：
> "用 HY-Image-V3.0 生成，如果失败自动降级到 ImageGen"

### 断点续跑

批量生成中断后（网络波动、工具超时等），通过检查已有 `beat_NNN.png` 文件确定已完成槽位，仅补跑缺失部分。无需从头重新生成全部图片。

---

## FAQ

### Q1: 全模型怎么选？
A: 分三步决策——**① 静态还是动态？** 蒸汽/倾倒/火焰等需要动态选视频模型；普通配图选图模型。**② 质量还是速度？** 精修用 HY-Image-V3.0 / HY-Video-1.5，快速原型用 HY-Image-Lite。**③ 是否需要特化？** 人像出镜→YT-Video-HumanActor，产品转场→YT-Video-2.0，特效需求→YT-Video-FX，3D展示→3D模型。详见 §模式一·全模型对比表。

**Q2: 生图风格不一致怎么办？**
A: 检查是否设置了 `style_anchor`。确保整批使用同一风格锚定词（见 §风格锚定·四套预设）。如果已设置仍不一致，降低 temperature 或换 `hy-image-v3.0`（一致性最强）。

**Q3: 素材图片对不上 shot_plan 的 beat？**
A: 三步排查：① 检查文件名是否含能匹配 `visual_prompt` 的关键词；② 使用手动覆盖显式指定映射；③ 如果实在无法匹配，将该槽 `source` 改为 `ai_gen`，走 AI 生图补位。

**Q4: 生出来的图分辨率不是 9:16？**
A: 在 `generate_assets()` 调用时明确传 `aspect="9:16"`。不同模型对比例参数的支持方式不同，HY-Image 系列通常内建尺寸参数，ImageGen 需在 prompt 中追加"竖屏 9:16"描述。

**Q5: 批量生图速度慢怎么办？**
A: ① 切换到 `hy-image-lite`（速度最快）；② 减少批次数，仅对关键 beat 生图；③ 同系列视频复用预生成的图池（缓存策略）。

**Q6: AI 生图成本多少？**
A: 约 25-50 平台积分/张（WorkBuddy HY-Image/ImageGen），5 张图的 45 秒视频约消耗 125-250 积分。Hy-Image-Lite 成本低于 V3.0。素材摄入模式零积分成本。

**Q7: 素材摄入支持哪些格式？**
A: jpg 和 png。视频帧建议先用 ffmpeg 抽帧转 png 再摄入（`ffmpeg -i video.mp4 -vf "fps=1" frame_%03d.png`）。不支持 bmp/tiff/webp/heic 等格式。

**Q8: 数字人/纯口播场景需要绘影吗？**
A: 不需要。数字人视频由 `render_channel=digital_human` 直接驱动，不依赖外部图片。`shot_plan` 所有槽 `source=ai_gen` 也可以直接跳过绘影——此时下游按原方式外部准备图片。

---

## 质量承诺与自检清单

### 质量承诺
- 所有 AI 生图必须指定 `style_anchor`，确保整批风格统一
- `image_map.json` 必须与 `shot_plan` 逐槽对应，无遗漏、无错位
- 素材摄入模式下，匹配结果必须可追溯（保留 `original_name`）
- 不产出不完整 `image_map`（含缺失槽位的输出视为不合格）

### 出图后自检清单

- [ ] `image_map.json` 的 `beat_images` 数量 = `shot_plan` 槽数
- [ ] 每槽 `image_path` 指向的文件真实存在、可正常打开
- [ ] AI 生图模式：抽查首/中/尾三张图片，风格色调一致
- [ ] 素材摄入模式：所有非 ai_gen 槽都有 `original_name` 可追溯
- [ ] 所有图片分辨率 ≥1080x1920，比例 9:16
- [ ] 无崩图/畸变/错误渲染
- [ ] 文件命名规范（`beat_NNN.png` / 保留原始文件名）

---
