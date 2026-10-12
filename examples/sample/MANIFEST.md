# examples/sample/ — 真源化 sample data

> 给新人的 hello-world 输入。新人 clone 仓库, 装好 edge-tts / datasketch / jsonschema,
> 然后跑 `python scripts/seed_sample_fingerprint.py examples/sample/t001-coral.json`
> 种子 → 跑 `path_b_build.py --sample examples/sample/t001-coral.json`(Phase 2 入口)
> → 5 分钟拿到 output.mp4。

## 现有 sample

| id | template | 形态 | 真源等级 |
|---|---|---|---|
| [t001-coral.json](t001-coral.json) | news-coral | 人物故事型 | A: 维基百科 (zh) + Wikimedia Commons (CC-BY-3.0 / CC0-1.0), 脱敏后 (原 t001 是真实人, 不引) |
| [everest-stat.json](everest-stat.json) | news-stat | 数据型 | A: 维基百科 (en) + Wikimedia Commons, 8848.86m (中尼联名 2020) |

## 真源化闸 (Ptrue-source 决策)

每条 sample 都有 source_fingerprint_sha256 字段, 该字段
- **不** 在 sample JSON 里手工填 (起始为 64 个 0)
- **由** `scripts/seed_sample_fingerprint.py` 种子:HEAD/GET + sha256 填入
- **跑前验证**:`--verify-only` flag, 比对存储 hash vs 现拉 hash
- **闸门**: 任一不匹配 → EXIT 1, 不静默放过 (R6)

详细设计: [docs/plans/2026-10-12-sample-data-truesource-foundation-design.md](../../docs/plans/2026-10-12-sample-data-truesource-foundation-design.md)

## 字段级真源

- `id`: sample 主键 (kebab-case)
- `display_title`: 脱敏后的展示标题
- `template`: 渲染 pack 名, 选自 32 个真模板 (ALL_TEMPLATES 现算)
- `voice`: edge-tts voice 名
- `facts[]`: 选题事实, 每条有 claim / source_url / source_label / source_fingerprint_sha256
- `images[]`: 镜图, 每张有 scene_position / wikimedia_url / license_spdx / credit / source_fingerprint_sha256
- `scenes[]`: 5 镜脚本, 每镜有 position / layout / kicker / title / body / onscreen

schema 字段类型真源: [../../schemas/sample.schema.json](../../schemas/sample.schema.json)
字段含义: [./READABILITY.md](./READABILITY.md)

## 许可证 (sample 里 image 使用许可)

- [licenses/wikimedia-cc0.txt](licenses/wikimedia-cc0.txt) — CC0 公共领域, 不需保留署名
- [licenses/wikimedia-cc-by.txt](licenses/wikimedia-cc-by.txt) — CC BY 3.0, 须保留署名

## 脱敏

t001-coral 原案件涉及真实人物 (湖南常德 · 71岁拾荒老人), sample metadata 不保留
真人真名真部门, 全部脱敏为 "湖南某地 · 退休人员 · 当地社保部门"。原 video archive
保留在 `routes/news/videos/` 是项目内部 reference, 不进 sample。

脱敏映射表: [READABILITY.md#脱敏映射](READABILITY.md)

## 不在 sample 范围 (运行时生成)

- `aigc.json` / `media-credits.json` / `ledger.jsonl` / `build.log` / `contact-sheet.jpg`
- sample 是 **输入契约**, 不镜面交付件 schema, 防双源漂移 (D20)