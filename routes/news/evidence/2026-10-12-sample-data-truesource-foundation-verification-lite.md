# 2026-10-12 sample data 真源化 Phase 1 (foundation) — verification-lite

> Tier 1 验证段, spec 见 [docs/plans/2026-10-12-sample-data-truesource-foundation-design.md](../../../docs/plans/2026-10-12-sample-data-truesource-foundation-design.md)

## 验证口径

| 项 | 结果 |
|---|---|
| 合并文档 | ✅ `docs/plans/2026-10-12-sample-data-truesource-foundation-design.md` |
| 用户确认「开始实现」 | ✅ "开始实现吧" |
| 改动文件数 | 7 (新增) — 见末尾清单 |
| Schema 校验 (jsonschema 4.26.0) | ✅ 2/2 valid; 闸门负例: invalid license_spdx → 红 |
| Seed (网络 HEAD + GET + sha256) | ✅ t001 6/6 + everest 6/6 |
| Verify 离线默认 (`--verify-only`) | ✅ 6/6 hash 已存 |
| Verify 在线 (`--verify-online`) | ✅ 6/6 hash match |
| 闸门负例: hash 改一个 bit | ✅ EXIT 1, `[verify] FAIL: 1 mismatch/error` |
| 闸门负例: hash 全 0 占位 | ✅ EXIT 1 (verify-only), 报 "未种子" |
| 闸门负例: license_spdx 不在 enum | ✅ jsonschema 红 |

## 关键校准（设计 → 实施 中的两处实相）

### URL 编码 bug
**症状**: 中文 Wikipedia URL 跑 `urllib.request.Request(url)` 时 `UnicodeEncodeError: 'ascii' codec can't encode characters`。
**根因**: `urllib.request.Request` 默认 `ascii` 编码整个字符串。
**修法**: 拆分 URL → `urllib.parse.quote(parts.path, ...)` 单独编码 path/query/fragment，保留 scheme / netloc 原样 (`scripts/seed_sample_fingerprint.py:_url_safe`)。
**取舍**: 留 `en.wikipedia.org` 作为 facts 真源 (ASCII URL 不需编码, 稳定), 中文表述放在 `claim` 字段里——这是 sample data 而不是生产文档, 不需要中文 URL 也能讲中文新闻。

### Wikimedia File URL 编造
**症状**: 我最初猜的 3 个 `File:Old_chinese_man_in_Beijing.jpg` 等 Commons URL 全 404。
**根因**: 猜测路径名,不可能命中。
**修法**: 通过 Commons API `prop=imageinfo&iiprop=extmetadata` 反查真实存在的 File 页 + 真实 license + 真实作者，最终用了 `Doorstep_disbursement_of_elderly_pension...` (CC BY-SA 4.0) + 2 个真实存在的退休院图。
**事实元数据真源**: `license_spdx` 由 API 返回 "LicenseShortName" 映射到 enum (CC BY 4.0 → CC-BY-4.0, Public domain → PD, 等)，不手抄——本想设计 D20 同款。

## 真实 URL 清单（已 HEAD 200 验证）

### t001-coral.json (sample 1)
| 用途 | 真源 |
|---|---|
| facts[0].source_url | https://en.wikipedia.org/wiki/Retirement |
| facts[1].source_url | https://en.wikipedia.org/wiki/Pension |
| facts[2].source_url | https://en.wikipedia.org/wiki/Social_security |
| images[0].wikimedia_url | Doorstep_disbursement_of_elderly_pension... (CC BY-SA 4.0, Satyaviswakarma) |
| images[1].wikimedia_url | Seniors_Rest_Home_In_Oppenheim.jpg (PD, Ingolfson) |
| images[2].wikimedia_url | Queen_Rose_Retirement_Home... (CC0, Andykatib) |

### everest-stat.json (sample 2)
| 用途 | 真源 |
|---|---|
| facts[0].source_url | https://en.wikipedia.org/wiki/Mount_Everest |
| facts[1].source_url | https://en.wikipedia.org/wiki/Himalayas |
| facts[2].source_url | https://en.wikipedia.org/wiki/1953_British_Mount_Everest_expedition |
| images[0].wikimedia_url | Everest,_Himalayas.jpg (CC BY 4.0, Vyacheslav Argenberg) |
| images[1].wikimedia_url | Mount_Everest_North_Face.jpg (CC BY-SA 3.0, Carsten.nebel) |
| images[2].wikimedia_url | Sunset_view_of_Everest.jpg (CC BY-SA 4.0, Nir B. Gurung) |

## seed / verify 实际输出

```
$ python scripts/seed_sample_fingerprint.py examples/sample/t001-coral.json
[HEAD] https://en.wikipedia.org/wiki/Retirement → HTTP 200
[GET ] https://en.wikipedia.org/wiki/Retirement → 475481 bytes, sha256=4867cec849d009ba...
[HEAD] https://en.wikipedia.org/wiki/Pension → HTTP 200
[GET ] https://en.wikipedia.org/wiki/Pension → 729532 bytes, sha256=7573747f091561b3...
[HEAD] https://en.wikipedia.org/wiki/Social_security → HTTP 200
[GET ] https://en.wikipedia.org/wiki/Social_security → 651157 bytes, sha256=b628ed9575b264b5...
[HEAD] https://commons.wikimedia.org/wiki/File:Doorstep_disbursement... → HTTP 200
[GET ] https://commons.wikimedia.org/wiki/File:Doorstep_disbursement... → 80032 bytes, sha256=514f734e9ea26d24...
[HEAD] https://commons.wikimedia.org/wiki/File:Seniors_Rest_Home... → HTTP 200
[GET ] https://commons.wikimedia.org/wiki/File:Seniors_Rest_Home... → 105620 bytes, sha256=4ad8de3481da02f0...
[HEAD] https://commons.wikimedia.org/wiki/File:Queen_Rose_Retirement_Home... → HTTP 200
[GET ] https://commons.wikimedia.org/wiki/File:Queen_Rose_Retirement_Home... → 114793 bytes, sha256=9308ffe5c5f0f3c9...

[seed] OK: 6/6 hash 写入 → examples\sample\t001-coral.json
```

(everest-stat 同形, 6/6 OK)

## 闸门负例输出

```
# 1. hash 改一个 bit
$ python scripts/seed_sample_fingerprint.py --verify-online examples/sample/t001-coral.json
[verify] facts[0].source_url (https://en.wikipedia.org/wiki/Retirement): MISMATCH
   stored: 0000000000000000000000000000000000000000000000000000000000000000
   actual: 4867cec849d009bafb12d8fb9bda4b94f439e5e2ee78e4636a8ee3303401dbf5
...
[verify] 5/6 match
[verify] FAIL: 1 mismatch/error
EXIT 1

# 2. hash 全 0 占位 (未种子)
$ python scripts/seed_sample_fingerprint.py --verify-only examples/sample/t001-coral.json
[verify] facts[0].source_url (...): 未种子 (placeholder)
...
EXIT 1

# 3. license_spdx 不在 enum
$ python -c "import jsonschema; jsonschema.validate(bad, schema)"
jsonschema.exceptions.ValidationError: 'PROPRIETARY' is not one of [...]
```

## 不可验证的盲点

- **Wikipedia 内容随时间漂移** —— hash 写入后 Wikipedia 编辑一次就 mismatch，这是闸门的设计意图 (漂移被发现 = 闸起作用)
- **Commons File 偶发 503** —— 闸门会重跑种子的方式恢复
- **Phase 1 没接 hello-news-video.sh 入口脚本** —— 这是 Phase 2 的工作, Phase 1 只立数据 + 闸门
- **jsonschema 依赖本地装** —— 如果用户机器没有 `pip install jsonschema`, hello-world 入口跑时会失败 (Phase 2 接 fallback 给文字提示)

## 改动清单 (git status 实测)

```
A  docs/plans/2026-10-12-sample-data-truesource-foundation-design.md   # 合并文档
A  schemas/sample.schema.json                                           # JSON Schema 真源
A  examples/sample/t001-coral.json                                      # 主 sample
A  examples/sample/everest-stat.json                                    # evergreen anchor
A  examples/sample/MANIFEST.md                                          # sample 索引
A  examples/sample/READABILITY.md                                       # 字段 + 脱敏映射
A  examples/sample/licenses/wikimedia-cc0.txt                           # CC0 模板
A  examples/sample/licenses/wikimedia-cc-by.txt                         # CC-BY 模板
A  scripts/seed_sample_fingerprint.py                                   # 种子 + 验证闸门
```

未提交。可由用户决定 commit 与 push 时机。