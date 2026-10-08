========================================================================
# news-alert-warning · frame.md（派生变体）

> 派生自 **`news-alert`**。警示警告（alert 基调 + 黄三角）
> 骨架（host.html + 7 个 composition）来自 master，本文件只覆盖**色板**。
> 派生关系记录在案，这样"这个变体为什么长这样"有据可查 —— 详见
> `routes/news/ARCHITECTURE.md` D16。

## 0. 派生声明

| 项 | 值 |
|---|---|
| `derived_from` | `news-alert` |
| 变体名 | `news-alert-warning` |
| 视觉气质 | 警示警告（alert 基调 + 黄三角） |
| 与 master 的差异色 | `#0A0A0D`, `#1A0A08`, `#6B6B6B`, `#B0B0B0`, `#B91C1C`, `#C0392B`, `#D44A4A`, `#DCDCDC`, `#E8E0D4`, `#EBE4D4`, `#ECE8DF`, `#F5F0E8`, `#FEF3C7`, `#FFFFFF` |

## 1. 色板（本包真实用色）

> 色板表由 `routes/news/scripts/gen_variant_frames.py` 按本包 HTML 里的**真实色值**生成，
> 不手抄、不预填（ARCHITECTURE D10 的教训：手抄的"实测值"会直接变成播出事故）。
> 改版式用色后重跑该脚本 + `audit_pack_contrast.py`。

| token | 值 | 用途 |
|---|---|---|
| `ink-light` | `#FFFFFF` | 纯白（亮）（用 8 次） |
| `ink-light-2` | `#EBE4D4` | 米白（亮）（用 8 次） |
| `ink-dim` | `#6B6B6B` | 深灰（暗）（用 8 次） |
| `accent` | `#E85D5D` | 强调（用 7 次） |
| `ink-light-3` | `#F5F0E8` | 暖白（亮）（用 5 次） |
| `ground-alt` | `#B91C1C` | 面/深强调（用 5 次） |
| `accent-deep` | `#C0392B` | 面/深强调（用 5 次） |
| `ground` | `#1A1A1A` | 主底（用 5 次） |
| `ink-dim-2` | `#B0B0B0` | 中灰（暗）（用 4 次） |
| `ground-2` | `#1A0A08` | 主底（用 2 次） |
| `ground-3` | `#0A0A0D` | 主底（用 2 次） |
| `ink-light-4` | `#DCDCDC` | 浅灰（亮）（用 2 次） |
| `ink-light-5` | `#FEF3C7` | 琥珀白（亮）（用 2 次） |
| `accent-deep-2` | `#D44A4A` | 面/深强调（用 1 次） |
| `accent-2` | `#E8E0D4` | 强调（用 1 次） |
| `ink-light-6` | `#ECE8DF` | 浅米（亮）（用 1 次） |

### 1.1 强制规则

1. **本表是本包色板的唯一事实源** —— 版式里出现表外的 hex 就是设计系统开始漏，
   `audit_pack_contrast.py` 会抓 `OFF_PALETTE_HEX` 并红。
2. **底色是 `#1A1A1A`**（本包用得最多的暗色）；强调色见上表 `accent*` 行。
3. 派生变体**不覆盖 master 的版面法则**（字阶、动量预算、屏句规则一律沿用 `news-alert` 的 frame.md），
   本文件只管色板 —— 版面契约的唯一事实源仍是 `news-alert/frame.md`。
========================================================================
