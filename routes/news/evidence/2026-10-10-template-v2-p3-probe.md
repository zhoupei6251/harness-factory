# 模板 v2 · P3 图片门禁 · 探针入库（2026-10-10）

> 上游：`docs/superpowers/specs/2026-10-10-news-p3-image-gate-design.md` §2/§8
> 覆盖判据：P3-1（分离度）· P3-2（黑名单非摆设）· P3-3（探针入库）
> 实现：`skills/douyin-pro/scripts/image_gate.py`（检测器本体）
> 探针：`skills/douyin-pro/scripts/p3_probe.py`（跑同一份实现，把结论落 JSON）
> 自检：`path_b_selftest.py` 的 6 条 `t_p3_*`（共 147 项，全绿）

## K17 检测器分离度 —— 一张真脸 + 一张真齿轮，四条通道并集分开

**测试图字节摘要**（进 `probe-result.json`，同 sha 同档是判据 4a 的静态锚）：
- `face-01.jpg` sha256[:16] = `2f0a8f079a3e60b7`（Obama 官像，`File:Official portrait of Barack Obama.jpg`，CC BY 3.0）
- `gear-01.jpg` sha256[:16] = `7edcebedaa67e6d5`（海滩弃轮，`File:A gear wheel that washed up on the beach (9273493350).jpg`，CC BY 2.0）

**参数**：短边定标 720（对齐 `commons_media.MIN_SHORT_EDGE`），`minNeighbors=3`、`minSize=24px`、`scaleFactor=1.1`，白名单 `{frontalface_alt2, profileface}` × `{原图, 水平镜像}` 四通道并集。

| 图 | 通道组合 | floor | 命中数 |
|---|---|---|---|
| face-01 | alt2 orig × profileface orig × alt2 mirror × profileface mirror | **G0** | 3 |
| gear-01 | 同上四通道 | None | 0 |

face-01 上的三个框（原图像素坐标）：`(168,536,179²)`（alt2 mirror 命中侧脸方向）、`(456,366,606²)`、`(464,366,597²)`（alt2 orig + mirror 两个近似的正脸框，差 8px 是同脸的两次报）。镜像通道在 Obama 官像上比原图多一路 —— 这佐证 §2 硬法则 1「镜像那一维不是可选」，非对称照片只在一侧起效。

齿轮图在四通道并集全零 —— 这是分离度的另一半，也是"floor=None 是可信的"的唯一实测来源。

## K18 反-反例：`frontalface_default` + `upperbody` 在齿轮图上跑，必报假阳

设计 §2 硬法则 2 把这两张列入黑名单，理由要有一条**可复现的反-反例**撑住（否则"显式拒绝"和"没被选中"就区分不了，黑名单就成了装饰）。

拿 gear-01 显式跑黑名单两通道（探针里 `blacklist_control` 那条），返回 **7 处**命中（`(153,622,60×49)`、`(497,384,80×65)`、`(501,406,77²)`、`(622,333,110²)`、`(625,333,110²)`、`(741,444,74²)`、`(1196,624,36²)`）：锈蚀齿轮圈的圆孔被 `frontalface_default` 认成正脸，`upperbody` 从轮辐阴影里认出 3 处"人上半身"。设计文档 §6.5 曾给"齿轮 default 4 命中、upperbody 7 命中"两个数，本轮实测合起来 7 命中，`frontalface_default` 单独命中数会因 minSize/scaleFactor 具体取值浮动 —— **量级对得上、精确数不作契约**（本轮的 4/7 拆分未逐条落盘）。

结论：**这两张 cascade 一旦被选中，纯机械特写会全部误判成人脸**，从而让 G1/G2 素材被强推 G0（走 §7 落位禁令 → 全弃用）。显式拒绝必须写在代码里，不能靠"没选到"。`image_gate.py` 的 `_DENIED_CASCADES` 就是这条规则的载体，`detect_faces` 默认参数只吃 `_ALLOWED_CASCADES`，黑名单不可达。

## K19 探针入库 = 三件套：图字节 + JSON + 自检断言

判据 P3-3 的"入库"口径要求**同图同档跨会话可复现**。目录 `routes/news/evidence/2026-10-10-p3-probe/` 落三件：

| 文件 | 作用 | 字节 |
|---|---|---|
| `face-01.jpg` | 真脸 fixture（CC BY 3.0，公有可复用） | 308549 |
| `gear-01.jpg` | 无脸 fixture（CC BY 2.0，公有可复用） | 477593 |
| `probe-result.json` | 上一轮探针输出：`capability_ok / primary / blacklist_control` 三段，含 sha 摘要与命中框 | 1963 |
| `media-manifest.json` | Commons 出处记录（title/artist/license/terms/source_url），由 `commons_media.write_manifest` 写 | 1439 |

**自检断言（`path_b_selftest.py` 6 条 t_p3_ 开头）**：
- `t_p3_detector_capability_ok` —— cv2 + 白名单两张 xml 都在（`capability_ok()`）
- `t_p3_face_fixture_hits_four_channel_union` —— face-01 floor=G0 ∧ hits≥1
- `t_p3_gear_fixture_hits_nothing_on_whitelist` —— gear-01 floor=None ∧ hits=0
- `t_p3_blacklist_denials_are_not_decorative` —— gear-01 显式跑黑名单 hits>0（K18 的自动化形式）
- `t_p3_probe_artifact_is_committed` —— 三件套文件存在 ∧ `probe-result.json` 里 face floor=G0 · gear floor=None · blacklist_control hits>0（**本地跑与落盘对不上就是"图或参数漂了"**，探针必须红）
- `t_p3_detector_is_deterministic_on_same_bytes` —— 同 gear-01 连续两次 `detect_faces`，框完全一致（判据 4a 的静态锚）

自检全绿 **147/147**（P2 收官 141 + P3 探针 6）。任何一条 P3-1/2/3 断言坏 → selftest 红，不允许"改测试不改实现"绕过。

## K20 与既有产线的接口边界（本切片只到检测器，不开闸）

设计 §10 的切片顺序：本切片**只交付 `image_gate.py` 与其证据**。以下三条不在本轮：
- `image-gate-ready` 编译期硬编码 False 的现状不动（切片 3 迁到 `capability_ok()` 运行时判定）。
- `asset` 仍在 `CHECKED_REQUIRES`、`has_asset` 形参仍在（切片 3 迁到 `CALLSITE_REQUIRES`）。
- 构建期的 grade 合成（`max(author_grade, detector_floor)`）与 `image_record` 扩字段是切片 2。

**为什么先只做检测器**：设计 §2 强调"探针与产线共用同一实现" —— 现在产线还没调它，先把实现和证据钉死，后续切片 2/3 的调用点迁移就是"接一根已经通好电的线"，不会引出"检测器改一次、产线跟着改一次"的连锁。

## K21 反证：把黑名单从代码里删掉，探针立刻不红但产线漂

（此节记录"为什么不写代码删 blacklist 的反证测试"，不是当前缺陷。）
`_DENIED_CASCADES` 从 `image_gate.py` 移除后，`detect_faces(gear, cascade_names=_DENIED_CASCADES)` 会 AttributeError 而非返回零命中，`t_p3_blacklist_denials_are_not_decorative` 报错而不是通过 —— 这条测试**不需要一个"删除即红"的反证**，因为常量本身是它的引用面；红线来自引用不存在的名字。

真正的漂移风险是"有人悄悄把 blacklist 加进 `_ALLOWED_CASCADES`"—— 那时 `t_p3_gear_fixture_hits_nothing_on_whitelist` 立刻红（gear 在 default+upperbody 上有 7 命中）。这条已经被 K17 的"四通道并集全零"覆盖了。

---

## 附录 · 一图档 · 复算命令

```bash
# 从零刷新证据
python skills/douyin-pro/scripts/p3_probe.py
# 只跑 6 条 P3 自检（本地过滤）
python skills/douyin-pro/scripts/path_b_selftest.py 2>&1 | grep -E "t_p3_|147"
```

`probe-result.json` 与本地 selftest 断言必须同步；任何一方改检测参数、图字节或阈值，`t_p3_probe_artifact_is_committed` 会拿 JSON 里的 floor / hits 与 fresh 运行结果做对比，任一分歧即红。
