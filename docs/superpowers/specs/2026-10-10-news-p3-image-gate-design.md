# 新闻域 P3 · 图片门禁与纹理化设计

> 日期：2026-10-10 ｜ 状态：设计对齐完成，待用户复审 → 转 writing-plans
> 上游：`2026-10-09-news-template-v2-design.md` §6.5（本设计把该节从 prose 升级为可实现契约）
> 覆盖判据：模板 v2 验收表判据 7「含可辨认人脸的图不得进入首镜 / closer / 人物镜 / 含专名镜」
> 关联：P2 已落地的地面翻色 `_subtitle_palette`（`path_b_build.py`）—— 示意标注复用其对比口径

---

## 0. 一句话目标

让"图库照片"能以**纹理**身份安全进入编译包（path_c）版式：本地零网络的人脸检测给图片定档（G0/G1/G2），档决定用哪个取图原语、是否强制"示意画面"标注、以及能否落在高指认性镜头。**门禁本身是安全边界，不是审美选项。**

## 0.1 本轮不做（显式排除，防范围蔓延）

- **不接真实素材源**（正版图库 API / AI 生图 / 人工传图）——沿用现有 Commons 取图（`commons_media.py`）。
- **不解人脸以外的指认维度**：地标、品牌 logo、门牌招牌文字、"同图反复用于同选题"仍靠大裁切+强压色间接消解（模板 v2 §11 记为后续迭代）。
- **不动 31 套 path_b 存量包**：`compiled=False`，走不到 spec.toml 的 grade→原语这条路。把"满屏 `.hk-photo` 退役 + 强制标注"扩到存量包是**独立迁移轮**（会动字节冻结产物），见 §9。

---

## 1. 架构根：两阶段 · 两事实

`check_preconditions` 在**编译期**跑（`hf_compile.py:545`，把 spec.toml 编成 pack 时对每个版式的原语核前置）；**逐镜取图 + 定档在构建期**跑（`path_b_build.py` images 段，`:3161-3175`）。两条事实在不同阶段，不可混成一个 flag：

| 事实 | 语义 | 判定阶段 | 载体 |
|---|---|---|---|
| `image-gate-ready` | "门禁这个**能力**在不在"（能否把图片原语选进版式） | **编译期** | `hf_compile.py:545` 传入 `check_preconditions` |
| `asset` / `grade` | "这一镜**有没有**图、几档" | **构建期** | 取图后写入 `image_record` |

推论（这是本设计唯一的结构性改动，见决策 A）：**`asset` 从编译期检查器退出**。编译期不知道某镜最终取不取到图，所以 `photo-duotone` 的 `requires=(asset, image-gate-ready)` 里，只有 `image-gate-ready` 在编译期核；`asset` 交构建期的"空路径塌槽"兜（`hf_primitives.py:474-478` 已实现：`path_var` 为空 → `display:none`）。

---

## 2. 组件①：检测器模块 `image_gate.py`（新建）

纯函数、本地零网络、可独立测、可被探针与产线共用同一实现（探针不许另写一份，否则探针绿≠产线绿）。

```
GradeResult = {
    detector_available: bool,        # cv2 可 import ∧ 4 张 cascade 加载成功
    faces: list[Box],                # 命中的连通域 (x, y, w, h)，供 mask 复检用
    floor: "G0" | None,              # 只有检测器能给的档：有脸=G0，无脸=None
}

capability_ok() -> bool              # detector_available 的对外单点判定
detect_faces(image_path: str) -> GradeResult
crop_and_recheck(image_path, faces) -> bool   # mask 掉人脸区后复检，仍命中=True（用于弃用判定）
```

**四通道并集**（模板 v2 §6.5，本次要有产物背书）：`{frontalface_alt2, profileface} × {原图, 水平镜像}`，`minNeighbors≥3`、`minSize≥24px`。

**硬编码黑名单**：`frontalface_default`（齿轮/锈螺栓圈误报 4 个）、`upperbody`（误报 7 个）。代码里显式拒绝这两个 cascade，注释引该实测——**探针必须含一条反-反例证明黑名单不是摆设**（拿齿轮图跑 `frontalface_default` 必报误命中）。

**职责边界**：检测器**只判"有没有可指认的脸"**（→ floor=G0），**不判 G1/G2**。场景可推断性本轮不可测，交给作者声明（§3）。

**检测输入定标**：喂进检测器的必须是**确定分辨率**的图。`minSize≥24px` 依赖像素尺度，同一图不同尺寸 grade 会翻——故在 `detect_faces` 入口把缩略图统一 normalize 到一个固定基准（如短边 720px，对齐 `commons_media.MIN_SHORT_EDGE`）再检。

**确定性**：`detect_faces` = 图字节纯函数 → 同图同档，不破判据 4a。

---

## 3. 组件②：grade 合成 + 作者合同

作者合同只加**可选**字段（`image` 现有语义不动：`false`=无图，字符串=取图查询，见 `commons_media.image_query:371`）：

```jsonc
"imageGrade": "scene" | "material"   // 新增·可选：声明意图档（G1 / G2），默认 scene
"person": true                        // 新增·可选：人物镜（触发 G0 落位禁令）
"namedSubject": true                  // 新增·可选：含专名镜（同上）
```

**作者不能声明 G0。** G0 = "有可指认的脸"，是机器事实、不是意图。作者只在 `scene`(G1，需强裁切去识别) / `material`(G2，可满屏压色) 两档里选。

**合成**（取更受限一侧，序 `G0 > G1 > G2`）：
```
final_grade = max(author_grade, detector_floor)
```
`detector_floor` 两个来源，**只会抬不会降**：
1. 检出脸 → `floor = G0`。
2. **检测器不可用/超时** → `floor = G0`（§6.5 硬规则 3：不能相信"没测到脸"，按最坏当可指认）。

**两个"保守"分清**（关键，别混）：
- 检测器坏 → G0（整图弃用级，走 §7 落位弃用）。
- 作者没写 `imageGrade`（有图、检测器正常、无脸）→ 默认 **G1**，不是 G0。理由：默认 G0 会让"作者漏标一次"就永久丢图，过苛；G1 仍强制裁切+压色去识别，安全且可用。**G0 只留给"真检出脸"和"检测器失效"两种。**

**产物落点**：`path_b_build._resolve_shot_image`（`:2092-2117`）取图成功后，同段调 `image_gate.detect_faces` → 合成 grade → 写回 `image_record`：`{grade, detector_available, faces}`。§5/§6/§7 只读这份 record，不再各自检测（检测成本单点，结论单点）。

---

## 4. 组件③：开闸条件 + `asset` 迁移出编译期

**`image_gate_ready` 不是硬编码 True**，而是运行时能力判定：
```
image_gate_ready := image_gate.capability_ok()
                   # = cv2 可 import ∧ 4 张 cascade 加载成功 ∧ 自检探针跑通
```
任一不满足 → 门保持**关**（维持现状：`photo-*` 原语一律拒编，`hf_compile.py:545` 传 `False`）。
理由：检测器跑不动时即便选中原语、构建期也会因"检测器失效→G0"把图全弃，等于选了个空槽——不如不选。

**`asset` 从 `CHECKED_REQUIRES` 移到 `CALLSITE_REQUIRES`**（`hf_primitives.py:576 / 581`）：
- `CHECKED_REQUIRES`（编译期入参可判）保留：`solid-ground`, `image-gate-ready`, `accent-allows-large-text`。
- `CALLSITE_REQUIRES`（别处构造性满足）新增条目：
  ```
  "asset": "构建期 resolve_variable 读 image_record；无图 → imagePath='' →
            原语 pre_js 空路径塌槽（hf_primitives.py:474-478），版式退化为无图态"
  ```
- 现 `check_preconditions` 里 `require=="asset" and not has_asset` 这条分支（`:682`）删除；`has_asset` 形参一并删（编译期拿不到这个事实，留着就是假接口）。
- 兜底不变：任何 `requires` 既不在 CHECKED 也不在 CALLSITE → 报"没有任何实现"（`:691`）。`asset` 移过去后仍被这条覆盖。

**改动面**：`GATED_REQUIRES`/`check_preconditions` 签名、`hf_compile.py:545` 调用点、自检 `path_b_selftest.py:2121-2146`（现有断言"has_asset=False 也拒"改为"编译期只由 image_gate_ready 决定；asset 由构建期塌槽兜"）。

---

## 5. 组件④：纹理化 = grade → 原语选择（编译期，作者声明驱动）

"纹理强度按 grade" 落到架构上不是"调一个原语的参数"，而是"**grade 决定选哪个取图原语**"：

| 作者声明 grade | 允许的原语 | 禁用 | 理由 |
|---|---|---|---|
| **G2** material | `photo-duotone`（满屏可，`hf_primitives.py:446`）/ `ken-burns-in`（`:513`）| — | 纯材质无场景可指认，满屏压色 S<0.15 |
| **G1** scene | **仅** `photo-local-crop`（25–35% 局部，`:485`）| `photo-duotone` 满屏 | 场景具指认性，必须裁到失去场景 |
| **G0** | 编译期不可声明（机器专属）| — | 构建期若检出脸 → §7 弃图 |

- **新增一条编译期一致校验**（可机判，非 prose）：版式若取了 `photo-duotone` 满屏但作者标的却是 `scene`(G1) → **拒编**。校验落在 `hf_compile` 的原语循环里（紧邻 `check_preconditions` 那圈，`:543`）。
- duotone 的 `opacity`/饱和度、local-crop 的 `width`/`position` 等**档内参数**仍由配方在各自档边界内自调；grade 只划**档的边界**（能不能满屏、必须多局部），不替配方定小数。

---

## 6. 组件⑤：示意标注（新原语 `schematic-tag`）

- **几何**（§6.5）：左下、安全区内、**z-index 高于所有原语**（挂在最后一条轨，且不进任何会被入场元素/容器裁切叠压的层——用高 track-index 保证"禁被任何入场元素遮挡"）、等宽 `2.0cqw`、字距 `.08em`、大字档对比 ≥3:1（复用 P2 `_subtitle_palette` 的地面翻色口径，不新造对比逻辑）。
- **文案两行**：第一行 `示意画面 · 与报道对象无直接关联`；第二行降为附属版权署名。
- **触发点 = 构建期**：`emit_composition` 读本镜 `image_record.grade`，凡 `grade != real` **强制注入**，无开关无例外（有图且非 real 才注入；无图/`image:false` 不注入）。
- **与现 credit 的关系**：`photo-duotone` 现有 `credit` figcaption（`:469`，右下、1.4cqw）降级为**附属署名**；`schematic-tag` 是**另一条更强的免责文字**，左下、压在所有元素上。两者不合并——一个免责（观众可见）、一个署名（版权可查）。

---

## 7. 组件⑥：落位禁令（构建期，按可判性拆两半）

判据 7「G0 不得进 首镜 / closer / 人物镜 / 含专名镜」的落地：

- **自动半（位置/版式事实，机器必判）**：`shot_index == 0`（首镜）或 `layout == closer`，且该镜 `grade == G0` → 触发弃用。
- **声明半（作者标记，尊重才判）**：镜带 `person` 或 `namedSubject` 且 `grade == G0` → 触发弃用。**没打标记的镜不触发落位禁令**（但只要有图非 real 仍出标注）。
- **弃用动作** = 构建期把该镜 `imagePath` 置空 → 复用 §4 塌槽，图消失、版式退化为无图态。§6.5 硬规则 2 的"裁掉人脸连通域复检、仍命中则弃用"：先 `image_gate.crop_and_recheck`，仍命中 → 置空弃用。

---

## 8. 验收口径（全可机判，除审美项）

| # | 判据 | 口径 / 证据 |
|---|---|---|
| P3-1 | 检测器分离度 | 探针：s1 侧脸四通道至少一路命中→floor=G0；s2 齿轮四通道全零→floor=None |
| P3-2 | 黑名单非摆设 | 探针反-反例：s2 齿轮跑 `frontalface_default` 必报误命中（证明显式排除有意义） |
| P3-3 | 探针**入库** | 检测器脚本 + 两张测试图 + 命中框数据落 `routes/news/evidence/`，不再只活 prose |
| P3-4 | grade 合成 | selftest 断 `max` 四组合：作者G2+脸→G0；作者G1+无脸→G1；作者G2+无脸→G2；未声明+无脸→G1 |
| P3-5 | 检测器失效保守 | mock `detector_available=False`（喂齿轮图）→ 结果仍 G0，证保守来自"失效"非"内容" |
| P3-6 | 开闸分层 | `capability_ok()=False`→`photo-*` 拒编；`=True`+作者声明 G1/G2→可选中。且编译期不再因 `has_asset=False` 拒（asset 已移出） |
| P3-7 | grade⟷原语一致 | 作者标 scene(G1) 却用满屏 `photo-duotone` → 编译期拒编（新增校验） |
| P3-8 | 示意标注强制 | 有图且 `grade!=real` → 成片 HTML 必含 `schematic-tag` 且 track 序最高；无图/`image:false` → 不含 |
| P3-9 | 落位禁令 | G0 落 `index==0`/`closer`/声明`person`/`namedSubject` → `imagePath` 置空；未声明标记的普通镜 G0 不触发落位弃 |
| P3-10 | 画面确定性 | 含图旗舰同稿双渲染，判据 4a 视频流哈希一致（检测器为纯函数，继承 asset 层既有 Commons 非确定性，不新增破口） |
| P3-审 | 审美 | 人工：含图旗舰出帧与老包同稿并排，用户认可放行（沿用模板 v2 判据 1 口径） |

---

## 9. 待用户复审的两条架构决策（可否决）

- **决策 A（已核实为"顺既有架构"，非新发明）**：把 `asset` 从 `CHECKED_REQUIRES` 迁到 `CALLSITE_REQUIRES`，编译期只核 `image-gate-ready`，`has_asset` 形参删除。理由：编译期拿不到"本镜有无图"这个事实，留在检查器入参里是个恒为 `False` 的假接口（现状正是 `hf_compile.py:545` 不传、恒 `False`）。代码库已有这两桶模型（`hf_primitives.py:576/581`），迁移是遵循而非扩张。
- **决策 B（scope 边界）**：31 套 path_b 存量包 P3 不接门禁与标注，`.hk-photo` 满屏退役 + 强制标注留作独立迁移轮。理由：存量包 `compiled=False`、字节冻结，扩接会破坏裁决 3"仅编译包走原生、存量包逐字节不变"的既有契约。

---

## 10. 交接

复审通过后 → `writing-plans` 拆实施计划。建议垂直切片顺序（示踪弹优先，先打通一条含图端到端再铺参数）：
1. `image_gate.py` + 探针入库（P3-1/2/3）——先证检测器可信，再谈用它。
2. grade 合成 + `image_record` 扩字段 + 作者合同字段（P3-4/5）。
3. `asset`→CALLSITE 迁移 + `capability_ok` 开闸（P3-6，决策 A）。
4. grade→原语一致校验（P3-7）。
5. `schematic-tag` 原语 + 构建期强制注入（P3-8）。
6. 落位禁令 + `crop_and_recheck` 弃用（P3-9）。
7. 含图旗舰端到端渲染 + 判据 4a 补测（P3-10 + 审美 P3-审，需 Node 22，见记忆：`nvm use 22.20.0` 与渲染同一次调用）。
