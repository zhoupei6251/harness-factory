# 2026-09-29 · news-policy 五版式落地 —— 验证记录（lite）

**范围**：`news-policy` pack 的 5 个真 composition（hook / story / catalog / rail / closer）
是否满足 Path B 契约、过版式自检、过 `hyperframes check --strict` 门禁。
**不含**渲染成片与人工肉眼验收（见文末「未验证」）。

结论：**三条全过 —— 版式自检 0 违规、自检 58/58 且可渲染 pack 从 1/12 升到 2/12、
五镜探针 `--check-only` EXIT=0**。过程中查出并订正了 frame.md 的一处不实的对比度判读，见 § 4。

---

## 1. 被验对象

```
skills/douyin-pro/templates/hyperframes_path_b/news-policy/
├── frame.md          10395 B   token 源（色板/字阶/法则/动量/地面/名字映射）
├── host.html          2121 B
└── compositions/
    ├── hook.html      7929 B   np-hook     paper   双书挡 + gold 印章环 + 标题金片
    ├── story.html     8480 B   np-story    paper ⇄ cobalt  领句 + 烫金尺 + 屏句
    ├── catalog.html   9129 B   np-catalog  paper-dark      三要点 + cobalt 序号片
    ├── rail.html      8652 B   np-rail     paper           时间线 cobalt 主脊
    └── closer.html    6468 B   np-closer   cobalt(暗面)    书挡反相 + 金片 CTA + 来源行
```

`placeholder.html` 已删除（占位壳既不进版式选择也不进可渲染计数）。

## 2. 命令与实测输出

### 2.1 版式结构自检（两包一起跑）

```bash
python skills/douyin-pro/scripts/layout_selfcheck.py \
  skills/douyin-pro/templates/hyperframes_path_b/news-policy \
  skills/douyin-pro/templates/hyperframes_path_b/news-coral
```

```
版式自检通过：12 个文件，0 条违规      EXIT=0
```

12 = policy 5 + coral 7。逐条不变量（模板包裹 / 根合成 id == timeline 键 / slotSeconds /
补间目标可解析 / 带 background 禁 opacity / 具名动量常数 + driftDur 位移 / 底部 20cqh 字幕禁入 /
自带 HF CJK @font-face 且拉丁族不写 local() / 排版无 px）全过。

### 2.2 全局自检（可渲染计数递增）

```bash
python scripts/path_b_selftest.py
```

```
[selftest] 58 项 · style=news-coral
  ok    t_full_loadability_progress
      可渲染 pack (有真版式): 2/12 —— news-coral, news-policy
[selftest] 全绿 58/58      EXIT=0
```

项数仍是 58 —— 新增的 pack 由既有参数化断言覆盖，不需要为新包加分支；
`t_placeholder_pack_stops_at_load` 仍 ok（其余 10 包只有占位壳 → 加载期停机）。

### 2.3 发射 + 门禁（五镜探针，逐版式点名）

输入 `.harness-news-runtime/articles/policy-probe-scenes.json`（5 镜，每镜显式 `layout`，
内容全是占位字，只验契约能不能填满）：

```bash
python skills/douyin-pro/scripts/path_b_build.py \
  --input .harness-news-runtime/articles/policy-probe-scenes.json \
  --template news-policy --source "探针·模拟来源" \
  --check-only --work-dir .harness-news-runtime/tmp/policy-gate-verify --keep
```

```
[path_b] 解析到 5 个分镜 | 设计系统 news-policy | 1080x1920
[path_b]   分镜1 → hook     时长 9.1s   start 0.0s   地面 light
[path_b]   分镜2 → catalog  时长 11.8s  start 9.1s   地面 light
[path_b]   分镜3 → story    时长 9.5s   start 20.9s  地面 dark
[path_b]   分镜4 → rail     时长 9.2s   start 30.4s  地面 light
[path_b]   分镜5 → closer   时长 10.3s  start 39.7s  地面 dark
[path_b] ✅ 版式自检通过 (0 违规)
[path_b] ✅ check --strict 通过 (ok=True)
[path_b] ✅ 发射与门禁通过 (未渲染)。      EXIT=0
```

关键读数（这些是"契约真的被走到"的证据，不是脚本客气）：
- **5 个文件名词干全部被解析并挂载** → 证明 `choose_layout` 认这套 canonical 名；
- **story 拿到 `dark`、closer 也是 `dark`** → 双地面翻转（`_tone` 相对上一镜翻转）按 frame.md §6 生效，
  公文暗面走 cobalt 而非黑底；
- **catalog 11.8s / closer 10.3s** → `slotSeconds` 被配音时长驱动，动量预算 `driftDur` 不是死值；
- 完整日志 `.harness-news-runtime/tmp/policy-gate-verify.log`，工程目录同前缀 `policy-gate-verify/`。

## 3. 对比度复算（frame.md §2.1 的数字来源）

脚本 `.harness-news-runtime/tmp/contrast_policy.py`（WCAG 2.x 相对亮度，直接对 token 原值算；
判读线正文 4.5:1 / 大字 3:1；1080 宽下 1cqw=10.8px，故 ≥2.3cqw 算大字）：

```
ink         paper        3.4cqw   15.20  ✓ 条文说明
cobalt      paper        9.0cqw    9.84  ✓ 公文标题/序号
gray        paper        4.4cqw    4.65  ✓ 屏句/节点号(配角)
cobalt      paper-dark   4.4cqw    8.51  ✓ 条目标题
ink         paper-dark   3.4cqw   13.13  ✓ 条文说明(卡衬)
paper       cobalt       9.0cqw    9.84  ✓ closer 地面 / story 暗面
rule        cobalt       3.4cqw    6.23  ✓ 来源行
cobalt-dark gold         3.6cqw    4.85  ✓ 金片上的强调字(正确写法)
gold        paper        9.0cqw    2.54  ✗ 金字(禁止:只作形状)
gold        paper-dark   9.0cqw    2.20  ✗ 金字(禁止)
gold        cobalt       9.0cqw    3.87  过大字线、不过正文线 —— 规则仍禁
crimson     paper        9.0cqw    4.75  数学过大字形, 规则仍禁
paper       paper-dark   4.4cqw    1.16  ✗ 两级米白之间不做文字分层
```

13 组比值与 frame.md §2.1 表逐位一致（复算即复现，不是抄一遍）。

## 4. 与 frame.md 计划的偏差（订正记录，不是悄悄吸收）

| # | 计划 | 实际 | 为什么 |
|---|---|---|---|
| 1 | 版式名 `summary` / `points` / `timeline` | 文件写成 `story.html` / `catalog.html` / `rail.html`，composition id 保留 `np-*` 前缀 | `choose_layout` 只认 7 个文件名词干，词汇表外的名字**永远不会被选中**；映射记进 frame.md §6，D9 也补进了 ARCHITECTURE §5 |
| 2 | `hook` 位「施行日期 12cqw 900 + gold 印章底」 | 3.6cqw 辅助行，日期由脚本写进屏句（`屏: 2026年10月1日施行`） | 发射器没有"只取日期"的取材处，该位由 `_onscreen_phrase` 填整条屏句，12cqw 在 16 字上限下必溢出；且日期不是独立变量 —— 版式不许自己编日期 |
| 3 | `gold / cobalt` 判读写「✗ 连大字档也不过」 | 改成「过大字线(3.0)、不过正文线(4.5)，但按强制规则只作形状」 | 3.87 **确实** 高于 3.0，原句是错的数字判读。禁金字的真正依据是法则（gold 只作形状）+ 正文档不过，不是"大字也不过"。closer.html 头注与 §2.1 细则同步订正 |

第 3 条是本次验证查出来的**文档缺陷**（代码与配色本来就对，写法是"金底深字 4.85"），
已就地改正 —— 留错的话下一个人补 `stat` / `quote` 时会照着"金字一定不过线"的假理由做判断。

## 5. 未验证 / 下一步

- ⏳ **渲染成片**：本轮只 `--check-only`（发射 + 自检 + 门禁），没有 mp4，
  所以「字形回退、实际抗锯齿、动效观感」未验。要出片去掉 `--check-only`。
- ⏳ **人工肉眼验收**：`contact-sheet.jpg` 未生成（属渲染后步骤）。
- ⏳ `news-policy` 的 `quote` / `stat` 刻意不 author（法则 4 政策类不上引文；数字型归 `news-stat`），
  若将来稿件需要，先确认 `choose_layout` 认名字再动手。
- ⏳ 探针内容是占位字（"探针第一条标题"…），**不可发布**；正式发布要走 news-workflow
  全链（fact-check + AIGC 三件套 + 真实 `--aigc-producer` 主体名）。
