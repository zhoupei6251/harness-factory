# 每角色变体簇（判据 0a）

口径：去硬编码色值 / `data-composition-id` 字面量 / `__timelines` 键名 / 首尾空白后聚 md5。

| 角色 | pack 数 | 簇数 | 簇规模（降序） | 少数簇 vs 主流簇 diff 行数（归一化后） |
|---|---|---|---|---|
| `hook` | 31 | 2 | [30, 1] | 1 包: 283 行 |
| `stat` | 31 | 2 | [30, 1] | 1 包: 4 行 |
| `rail` | 31 | 2 | [30, 1] | 1 包: 250 行 |
| `quote` | 31 | 2 | [30, 1] | 1 包: 7 行 |
| `catalog` | 31 | 2 | [30, 1] | 1 包: 259 行 |
| `story` | 31 | 2 | [30, 1] | 1 包: 242 行 |
| `closer` | 31 | 2 | [30, 1] | 1 包: 276 行 |

**组件数下界 = 14**（spec 里写的 14 是抽样推定，以本表为准）。

- `hook` 少数簇（1 包）: news-policy
- `stat` 少数簇（1 包）: news-policy
- `rail` 少数簇（1 包）: news-policy
- `quote` 少数簇（1 包）: news-policy
- `catalog` 少数簇（1 包）: news-policy
- `story` 少数簇（1 包）: news-policy
- `closer` 少数簇（1 包）: news-policy
