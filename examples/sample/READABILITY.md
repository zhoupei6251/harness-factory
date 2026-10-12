# sample 文件 READABILITY

> 给新人 + 维护者:每个字段是什么意思、跑动到哪、脱敏为什么这么做。

## 字段表 (top-level)

| 字段 | 类型 | 跑动到哪 | 含义 |
|---|---|---|---|
| `schema_version` | const "1" | sample.schema.json `$id` 锁定 | 当前 schema 版本 |
| `id` | kebab-case | sample 索引 / 临时目录 / ledger.jsonl 主键 | sample 唯一标识 |
| `display_title` | string | 第一镜 hook.title / 上屏静态文字 | 脱敏后的展示标题 |
| `template` | enum 32-pack | `path_b_build.ALL_TEMPLATES` 渲染入口 | 选用哪个 pack (32 个真版式之一) |
| `voice` | enum edge-tts | edge-tts CLI `--voice` | TTS 配音 (项目锁零云费, edge-tts 走 Edge) |
| `facts[]` | array | fact-check 闸输入 | 选题事实, 每条带 source 真源 |
| `images[]` | array | 渲染时 commons_media 取图 | 镜图, 每张带 Wikimedia 真源 |
| `scenes[]` | array | `path_b_build.py --input` JSON 数组 | 5 镜脚本, 渲染入口 |

## facts[] 字段

| 字段 | 类型 | 跑动到哪 |
|---|---|---|
| `claim` | string | fact-check 闸比对项 + 第 3 / 第 4 镜 body |
| `source_url` | URL (Wikimedia 优先) | seed_sample_fingerprint.py HEAD/GET |
| `source_label` | string | 视频简介 + 字幕里 "据 XX 报道" |
| `source_fingerprint_sha256` | sha256 | 真源化闸, 不允许人工填 |

## images[] 字段

| 字段 | 类型 | 跑动到哪 |
|---|---|---|
| `scene_position` | int (1-based) | 镜 N 引用 (与 scenes[N].position 对齐) |
| `wikimedia_url` | Wikimedia File URL | commons_media 抓图 |
| `license_spdx` | SPDX 标识 | media-credits.json 该行许可 |
| `credit` | string | media-credits.json 该行署名 |
| `source_fingerprint_sha256` | sha256 | 真源化闸, 不允许人工填 |

## scenes[] 字段

| 字段 | 类型 | 跑动到哪 |
|---|---|---|
| `position` | int (1-based) | 镜序号, 渲染时按此排序 |
| `layout` | enum (7 个 AUTO_LAYOUT_STEMS) | `path_b_build.AUTO_LAYOUT_STEMS` 选版 |
| `kicker` | string | 镜左上角小标 |
| `title` | string | 镜主标题 |
| `body` | string | TTS 配音主体 |
| `onscreen` | string | 屏上文字 (含 `｜` 分隔标记语法) |

## 脱敏映射表 (针对 t001-coral.json)

> t001 是 harness-factory 内部 reference (见 `routes/news/videos/`),
> 涉及真实人物 + 真实地名 + 真实部门 + 真实手机号 —— **不进 sample data**。
> sample 取所有真实字段的脱敏版本, 让 hello-world 跑得动 + 不暴露当事人。

| 字段类型 | 原 t001 真实值 | sample 脱敏值 | 脱敏理由 |
|---|---|---|---|
| 地名 (省级-市级) | 湖南常德 | 湖南某地 | 真实市级定位, 个人可识别 |
| 人物描述 | 71岁拾荒老人 | 湖南某地退休人员 | 年龄+身份+经济状态三重标签 |
| 数字 (具体) | 每月 3700 元养老金 | 退休人员养老金发放金额 (量级保留, 数字模糊) | 精确金额可被关联检索识别 |
| 部门回应 | 常德市社会救助事务中心 | 当地社保部门公开回应 | 真实政府部门 + 姓名可被反向定位 |

**保留**: 新闻事实的本质(有养老金发放规范 / 多缴多得 / 部门公开报告)。
**替换**: 一切可定位到真人 / 真部门 / 真地名的标识符。

## 真源化闸

### seed 阶段
```
$ python scripts/seed_sample_fingerprint.py examples/sample/t001-coral.json
[HEAD] https://zh.wikipedia.org/wiki/中华人民共和国养老保险 → 200
[GET ] https://zh.wikipedia.org/wiki/中华人民共和国养老保险 → 200
[seed] facts[0].source_fingerprint_sha256 = abc123...
... (重复每个 facts / images 字段)
EXIT 0
```

### verify 阶段 (--verify-only flag, 离线默认)
```
$ python scripts/seed_sample_fingerprint.py --verify-only examples/sample/t001-coral.json
[verify] facts[0] hash match ✓
[verify] facts[1] hash match ✓
[verify] facts[2] hash match ✓
[verify] images[0] hash match ✓
[verify] images[1] hash match ✓
[verify] images[2] hash match ✓
EXIT 0
```

### 闸门触发 (任一 hash 不匹配)
```
[verify] facts[0] hash MISMATCH
  stored: <原 hash>
  actual: <新 hash>
EXIT 1  ← 闸门, 不静默放过 (R6)
```

### 失败模式 (网路 5xx / 4xx)
```
[HEAD] https://zh.wikipedia.org/wiki/... → 503
[ERROR] HEAD 503: 服务暂不可用, 重跑种子 (网络抖动常见)
EXIT 1  ← 闸门, 不写假 hash 蒙混过关
```

## 不在 sample 范围 (运行时生成)

sample 是**输入契约**, 不镜面交付件 schema:
- `aigc.json` — 渲染时 path_b_build 写
- `media-credits.json` — 渲染时 path_b_build 写
- `ledger.jsonl` — news-curate 写
- `build.log` — 渲染时 path_b_build 写
- `contact-sheet.jpg` — 渲染时 path_b_build 写

sample 文件被 hello-world 读, sample 文件**不允许包含**这些 sidecar 字段。
双源必漂 (D20), 见 [DESIGN-lsh.md §5](../../routes/news/DESIGN-lsh.md)。