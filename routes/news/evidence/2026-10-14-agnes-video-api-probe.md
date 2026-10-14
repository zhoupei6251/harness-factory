# 2026-10-14 · Agnes 视频 API 接入探针（结论：不接入）

> 用用户的 Key 在真账号上实测。所有数字都是本机跑出来的原始返回，不是 README 转述。
> **Key 不写入本文件**，命令里一律 `$AGNES_API_KEY`。

## 0. 一句话结论

**不接入。** 三条独立否决，任一单独成立：① 视频通道依赖付费档才能验到 2K，与「零云费」口径冲突；
② 免费档内 `aspect_ratio:"9:16"` 产不出正立竖屏（转正后是横屏）；③ 200s 换 4.5s 素材，
相对现状 28.7s 出整片倒挂 35 倍。

## 1. 三个来源的真实关系（避免下次又当三个选项调研）

| 来源 | 是什么 | 证据 |
|---|---|---|
| `video.lichuanyang.top` | **不是独立产品**，是 lcy362 仓库的托管版 | 仓库 GitHub `homepage` 字段即该域；README JSON-LD `author.url = lichuanyang.top`、`sameAs` 含该域与 Gitee 镜像 `sandgrid/agnes-video-generator` |
| `lcy362/agnes-video-generator` | **主仓库**，v7.1.0 | 515★ / 185 fork / 2 open issue；最后 push **2026-10-13** |
| `uglylee/free-video-generator` | **手工转投的旧版**，不是 fork | `fork=false, parent=null`；13★ / 21 fork / **12 open issue 无人回**；5 个 commit 全在 **2026-07-08 当天**，此后零维护；根目录与 lcy362 同构但缺 `web/` `frontend/` `bin/` `.github/` `README_ZH` |

**它治不了我们的真 blocker**：`core/audio/tts.py` 就是 `import edge_tts` + 默认 `zh-CN-XiaoxiaoNeural`
（与我们同库同音色），失败后重试若干次退化成**静音占位**。edge-tts 403 换到它身上照样撞。

## 2. API 契约（可复现，三条命令）

```bash
# 1) 模型清单（顺带验证 Key 属于哪个站点）
curl -s -H "Authorization: Bearer $AGNES_API_KEY" \
  "https://apihub.agnes-ai.com/v1/models?all=true"

# 2) 提交
curl -s -X POST "https://apihub.agnes-ai.com/v1/videos" \
  -H "Authorization: Bearer $AGNES_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"agnes-video-2.5","prompt":"…","mode":"text",
       "seconds":"4","size":"720P","aspect_ratio":"9:16"}'
# → 200 {"id":"task_…","video_id":"task_…","task_id":"task_…"}

# 3) 轮询（注意：api root 不带 /v1，且 2.5 需带 model_name）
curl -s -H "Authorization: Bearer $AGNES_API_KEY" \
  "https://apihub.agnes-ai.com/agnesapi?video_id=<id>&model_name=agnes-video-2.5"
# → {"status":"completed","url":"….mp4","seconds":"4","size":"720P",
#    "created_at":…,"started_at":…,"completed_at":…}
```

站点路由（实测，与 `core/config.py:1266` 注释一致）：

| 域名 | 本 Key |
|---|---|
| `apihub.agnes-ai.com`（国际站） | ✅ 200，1.33s |
| `apihub.agnes-ai.cn`（国内备用） | ✅ 200，0.40s |
| `api.agnes-ai.cn`（国内站专属） | ❌ 401「无效的令牌」 |

模型清单实测 **10 个**：video 2（`agnes-video-2.5` / `agnes-video-2.5-flash`）、image 3、text 5。
⚠️ **`agnes-video-v2.0` 不在列表内** —— 即 lcy362 的 `DEFAULT_VIDEO_MODEL` 已失效，
它那套 `num_frames`/`frame_rate` 老协议对本账号无用，只能走 2.5 的 `seconds`/`size`/`aspect_ratio`。

## 3. 唯一一次成功出片的完整数字

```
created_at 1791962737 → started_at 1791962767 → completed_at 1791962937
排队 30s + 生成 170s = 端到端 200s，产出 4.48s 素材
```

进度回传形态：`progress` 0 → 10 后**在 10% 停留约 180s**，然后直接跳 100。
`internal_status` 到完成时仍是 `"pending"` —— **只有顶层 `status` 可信**，别拿 `internal_status` 判完成。

产物 ffprobe：

```
h264 + aac · 720×1280 · 24fps · nb_frames=107 · duration=4.48s · 3.21 Mbps · 1.80 MB
音轨非静音：mean_volume −27.8 dB / max_volume −14.2 dB（自带环境音，配音时须丢）
```

## 4. 三道闸（准确 code，这是"能不能用"的真正答案）

| 请求 | HTTP | code | 原文关键句 | 含义 |
|---|---|---|---|---|
| `2.5-flash` + 720P | **503** | `video_queue_full` | "video queue is full, please retry later" | 队列饱和，~0.73s 直接拒（不是排队等）。**12/12 全拒**，t+0→t+330s 每 30s 一次 |
| `2.5` + 720P（额度耗尽后） | **429** | `rate_limit_exceeded` | "You've reached the API rate limit for **free users**. Upgrade to a **Token Plan**…" | 免费用户有速率上限，且**存在付费 Token Plan** |
| `2.5` + **2K**（任意 aspect_ratio） | **403** | `insufficient_user_quota` | "Insufficient user quota, remaining: **＄0.000000**" | **2K 按美元计价，本账号余额 $0 ⇒ 2K 不在免费档内** |

闸是**按端点/模型分池**的，不是账号一把全关：视频通道 403/429/503 的同时，
`agnes-image-2.5-flash` 仍 200 正常出图（11.5s）。

⚠️ 解析陷阱：额度提示里的美元符号是**全角 `＄`（U+FF04）**，不是 ASCII `$`。
机检若按 `$` 匹配该字符串会漏。

`GET /v1/dashboard/billing/subscription` → `{"has_payment_method":true,"soft_limit_usd":100000000,
"hard_limit_usd":100000000,"system_hard_limit_usd":100000000}`；
`/v1/dashboard/billing/usage` → `{"object":"list","total_usage":10}`（无金额明细，`10` 不可解读为钱）。
**所以"完全免费、没有用量限制"（lcy362 README 原话）不成立**，以 API 回复为准。

## 5. U3：竖屏躺倒，且转正后是横屏（本轮最重要的发现）

请求 `aspect_ratio:"9:16"`，产物容器是 720×1280（竖），但：

- 抽帧目视：**画面横躺 90°**
- `ffprobe` 查 `stream_side_data=rotation` 与 `stream_tags=rotate` → **均无**
  ⇒ 不是"元数据没写对、播放器自己会转"，是**像素本身存成横的**
- 事后转正实测：
  - `transpose=2`（逆时针）→ **1280×720 正立横屏** ✅ 方向正确
  - `transpose=1`（顺时针）→ 1280×720 但上下颠倒 ❌

lcy362 源码把这个签名写成 `_needs_portrait_rotation_fix(perf_w, perf_h, cont_w, cont_h)`，
判据 `perf_w > perf_h and ch > cw`（`core/api/agnes_video.py:139`），
文档字符串称「U3：2.5 系列『容器竖、像素横』的竖屏躺倒缺陷」。
**它的"修复"只是把画面转正 —— 转完就是横屏。**

⇒ 结论：我们要的 1080×1920 竖屏，这条路**一次都没拿到过竖屏画面**。

## 6. 未验证的边界（诚实标注，别当已证）

1. **2K 能否出正立竖屏：未验证，且在免费档内不可验证**（403 无余额）。
   所以"aspect_ratio 被忽略"只对 **720P + mode=text + 2.5** 这一格成立，
   未排除 `size` 档冲突、`mode` 差异、flash/2.5 差异三种可能。
2. **观测污染**：429 出现在 12 次 503 重试之后，无法干净区分"flash 池本来饱和"与
   "我的重试打满免费额度"。能确定的只有顺序（前 12 次 503，第 13 次起 429）。
3. **本次消耗**：探针用掉了该账号的免费视频额度（1 次成功 + 若干次被拒），只换回一条 4.5s 素材。
4. 图像端点质量：出的"老人拾荒"纪实照**照片级拟真、无水印无 C2PA**，
   但**中文招牌与垃圾分类字样全是乱码伪汉字**（"佫朱束"等）——放进新闻成片一眼即假。

## 7. 重开条件（什么情况下这条裁决要重审）

同时满足才值得重测：

1. 先确认 **Token Plan 价格**并接受它（否则与「零云费」口径直接冲突，不必再测）；
2. 实测 `size:"2K"` + `aspect_ratio:"9:16"` 能否出**正立竖屏**（本轮撞 403 未测到）；
3. 用途限定在 **`news-explainer`**（科普/原理，画面本应是画出来的而非拍出来的）——
   突发/现场/调查类**永不适用**，AI 生成的"现场画面"是虚构素材；
4. 且 ① 角标必须从 `no-badge` 改回 `full`：平台产物无水印无 C2PA
   （`core/config.py:880 DEFAULT_WATERMARK_ENABLED = False`），
   标识责任 100% 落回我们自己的 `aigc.json` + `check_publishable.py`。

## 8. 产物位置

`.harness-news-runtime/tmp/agnes-probe-2026-10-14/`（已 gitignore，不进仓）：
`agnes_v.mp4`（原始，躺倒）、`agnes_v_rot_ccw.mp4`（转正=横屏，方向正确）、
`agnes_v_rot_cw.mp4`（错方向，对比用）、`f0.png` / `f80.png` / `check_ccw.png` / `check_cw.png`、
`agnes_img.png`（图像端点产物，中文乱码）。
