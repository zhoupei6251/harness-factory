# 2026-10-12 sample data 真源化 (Phase 1：foundation) — design

> Tier 1 合并文档（spec + plan + 验证合一），brainstorming 已敲定 3 条: B → 方案 3 → 方案 A (t001 + everest anchor) → 只锁生产数据 → 方案 Y (hash 指纹 + 可选在线)。
>
> **Phase 1 范围**: seed_sample_fingerprint.py + 2 份 sample JSON + MANIFEST.md + licenses/。**hello-news-video.sh 入口脚本留 Phase 2**, 避免一次性 PR 没回灌。

## 1. 改动范围 (Tier 1 触发判据)

| 项 | 判定 |
|---|---|
| 改动文件数 | 5 (新增 sample/t001-coral.json + sample/everest-stat.json + sample/MANIFEST.md + sample/licenses/*.txt + scripts/seed_sample_fingerprint.py) |
| 改动行数(估) | ~300 行(2 JSON × ~80 行 + 2 许可模板 × 30 行 + MANIFEST ~50 行 + 种子脚本 ~120 行) |
| 公共 API 改动 | 否 |
| 数据库 schema | 否 (sample data 独立 schema, 走 schemas/sample.schema.json) |
| 构建脚本 | 否 |
| 多模块联动 | 否 (仅 examples/sample, scripts/**) |
| 新依赖 | 无 (hash 用 stdlib hashlib; URL 抓取用 urllib.request) |

✅ Tier 1, 走主 Agent 直做。

## 2. 设计

### 2.1 目录与文件

```
examples/
├── sample/
│   ├── t001-coral.json       # 主 sample (人物故事型, 脱敏版 t001)
│   ├── everest-stat.json     # evergreen anchor (数据型)
│   ├── MANIFEST.md             # sample 索引 + 真源说明 (新人读这份入门)
│   ├── licenses/
│   │   ├── wikimedia-cc0.txt    # CC0 通用模板 (项目内套用)
│   │   └── wikimedia-cc-by.txt  # CC-BY 模板 (含署名要求)
│   └── READABILITY.md         # 字段说明 + "跑动会去哪"
scripts/
└── seed_sample_fingerprint.py   # URL 指纹种子脚本 (一次性, 写完丢)
schemas/
└── sample.schema.json           # sample 文件 JSON Schema (D20 同源)
```

### 2.2 sample JSON 字段(锁的生产数据)

```json
{
  "schema_version": "1",
  "id": "t001-coral",
  "display_title": "湖南某地退休人员养老金发放情况",
  "template": "news-coral",
  "voice": "zh-CN-XiaoxiaoNeural",

  "facts": [
    {
      "claim": "湖南某地退休人员养老金发放金额与支出规范一致",
      "source_url": "https://www.thepaper.cn/newsDetail_forward_...",
      "source_label": "澎湃新闻",
      "source_fingerprint_sha256": "<种子脚本生成>"
    }
  ],

  "images": [
    {
      "scene_position": 2,
      "wikimedia_url": "https://commons.wikimedia.org/wiki/File:...",
      "license_spdx": "CC-BY-3.0",
      "credit": "Author Name (Wikimedia Commons)",
      "source_fingerprint_sha256": "<种子脚本生成>"
    }
  ],

  "scenes": [
    {
      "position": 1,
      "layout": "hook",
      "kicker": "今日关注",
      "title": "湖南某地",
      "body": "退休人员养老金发放情况",
      "onscreen": "湖南某地｜退休人员"
    }
  ]
}
```

**不锁**(运行时填): aigc.json / media-credits.json / ledger.jsonl / build.log / contact-sheet.jpg。
**理由**: sample 是**输入契约**不是**交付件副本**。双源必漂(D20 同款风险)。

### 2.3 脱敏规则 (针对 t001)

| 原 t001 | 脱敏后 |
|---|---|
| 湖南常德 | 湖南某地 |
| 71岁拾荒老人 | 湖南某地退休人员 |
| 每月 3700 元养老金 | 退休人员养老金发放金额(数字保留作为量级口径,非具体金额) |
| 官方回应:常德市社会救助事务中心 | 当地社保部门公开回应 |

**保留**: 新闻事实 (数字量级、报告口径、发布时间、来源链)。
**替换**: 真人真地名 / 真部门名 / 真身份证号 / 真手机号(任一出现即脱敏)。
**写档规则**: `sample/READABILITY.md` 单列"脱敏映射表",新人能查到"为什么这么改"。

### 2.4 真源化闸 (方案 Y)

**种子脚本** `scripts/seed_sample_fingerprint.py`:

```
对 sample JSON 每个 source_url / wikimedia_url:
  1. urllib.request HEAD(url)  → 200 才继续, 否则停机报错(不假绿)
  2. urllib.request GET(url)   → content
  3. hashlib.sha256(content).hexdigest()  → 写回 JSON 的 source_fingerprint_sha256

输出: 同一个 sample JSON, 字段填齐, 退出码 0
```

**验收时跑**:
```
# 离线默认 (无网络) — 比 hash 一致即过
$ python scripts/seed_sample_fingerprint.py --verify-only examples/sample/t001-coral.json
[verify] 5 facts: 5/5 hash 匹配
[verify] 3 images: 3/3 hash 匹配
EXIT 0

# paranoid (--verify-online flag)
$ python scripts/seed_sample_fingerprint.py --verify-online examples/sample/t001-coral.json
[HEAD] https://www.thepaper.cn/... → 200
[GET ] https://commons.wikimedia.org/... → 200
[verify] 5 facts: 5/5 GET 200
EXIT 0

# 任一 404
$ python scripts/seed_sample_fingerprint.py --verify-only examples/sample/t001-coral.json
[verify] 5 facts: 4/5 hash 匹配, 1/5 hash 不匹配 (real hash: <新>, json hash: <旧>)
EXIT 1  ← 闸触发, 不假绿
```

**与 D19 Ptrue-source 决策的接口**:种子脚本复用同一 source-of-truth 闸的"报字段 + hash 锁"约定(读 ./core/NEVER.md 或类似定位真源化原则文档)。如果 D19 已经有 Python 库形式的真源化接口,直接复用;否则种子脚本独立,但写一个 schema 共享文档。

## 3. 证据段 (合并文档 §3 模板)

### 3.1 改动触及的代码 (R1)
[codebase-memory-mcp 不可用, 已降级] 原因:本次改动全部新增 + 手改文件 < 5; 替代手段 = Read/Grep 手工取证。
| 符号 | qualified_name | 角色 |
|---|---|---|
| examples/sample/t001-coral.json | (新) | 直接新增 |
| examples/sample/everest-stat.json | (新) | 直接新增 |
| scripts/seed_sample_fingerprint.py | (新) | 直接新增 |
| schemas/sample.schema.json | (新) | JSON Schema 真源(锁字段类型) |

### 3.2 影响面
- **inbound callers**: 无(本次纯新增, hello-news-video.sh 留 Phase 2)
- **outbound callees**: hashlib(标准库) / urllib.request(标准库)
- **跨服务 / 异步链路**: 无(本地)

### 3.3 验证断言 (改完逐条核)
- [ ] `python scripts/seed_sample_fingerprint.py --verify-only sample/t001-coral.json` 退出码 0
- [ ] `python scripts/seed_sample_fingerprint.py --verify-only sample/everest-stat.json` 退出码 0
- [ ] 模拟 404:把一个 source_url 改坏,verify 退出码 1,不静默放行 (R6)
- [ ] 模拟 hash 漂移:把 sample JSON 中一个 fingerprint 字段手工改一个 bit,verify 退出码 1
- [ ] `jsonschema -i sample/t001-coral.json schemas/sample.schema.json` 校验通过 (JSON Schema 真源)
- [ ] `sample/READABILITY.md` 包含"脱敏映射表"段(全部 4 字段都有映射行)
- [ ] `sample/MANIFEST.md` 列出 2 个 sample + 每个的 claim 数 + image 数 + 数据真源等级

### 3.4 不可验证的盲点
- **Wikimedia Commons 5% 节点偶发 503**:种子脚本一次 5xx 即停;重跑种子可解决
- **t001 原案件已写为内部 reference**, 留 `routes/news/videos/` 不进 sample 是设计的一部分
- **JSON Schema 校验靠 jsonschema CLI** — 用户本地装没有的会失败;Phase 2 改 hello-world 入口时自带 fallback(失败给文字提示不阻挡)

## 4. 实施计划

| 步 | 操作 | 闸 / 验证 |
|---|---|---|
| 1 | 创建目录结构 | mkdir examples/sample/licenses/ |
| 2 | 写 `schemas/sample.schema.json` | 字段类型真源 |
| 3 | 写 `examples/sample/t001-coral.json`(脱敏版, 不含 fingerprint) | §2.2 字段全 |
| 4 | 写 `examples/sample/everest-stat.json` | §2.2 字段全 |
| 5 | 写 `examples/sample/licenses/{wikimedia-cc0,wikimedia-cc-by}.txt` | CC 模板 |
| 6 | 写 `examples/sample/MANIFEST.md` | sample 索引 + 真源说明 |
| 7 | 写 `examples/sample/READABILITY.md` | 字段 + 脱敏映射 |
| 8 | 写 `scripts/seed_sample_fingerprint.py` | §2.4 种子脚本 |
| 9 | 跑种子(填实 fingerprint) | 退出码 0, 文件 hash 写入 |
| 10 | 跑 verify 闸 (离线 + 在线) | §3.3 全过 |
| 11 | 模拟 404 + hash 漂移负例 | §3.3 闸门红闸 |
| 12 | 写 verification-lite 段 | `routes/news/evidence/2026-10-12-sample-data-truesource-foundation-verification-lite.md` |
| 13 | git commit + git push(用户点头) | push 要先问(MEMORY.md) |

## 5. 完成判据 (Tier 1)

1. ✅ 合并文档已写(本文件)
2. ⏳ 用户确认「开始实现」
3. ⏳ 主 Agent 改完 + 内联断言(§3.3 逐条核)
4. ⏳ seed + verify 闸全部绿
5. ⏳ `routes/news/evidence/2026-10-12-*-verification-lite.md` 落盘
6. ⏳ 可以 commit, push 由用户决定

## 6. 不在 Phase 1 范围(留 Phase 2+)

- `hello-news-video.sh` 入口脚本(串 6 个 skill):Phase 2
- `hf doctor` 环境体检:Phase 2
- `docs/user-guide/{5min-quickstart,role-based,troubleshoot}.md`:Phase 2
- README 顶部 5 分钟跑通段重写:Phase 2
- sample data 多 pack 拓展(政策型):Phase 3