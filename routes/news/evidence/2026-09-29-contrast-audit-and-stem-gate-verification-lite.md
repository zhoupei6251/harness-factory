# 2026-09-29 · 色板复算闸门 + 版式词表上闸 —— 验证记录（lite）

**范围**：把一次性的 `.harness-news-runtime/tmp/contrast_policy.py` 升级成受版本管理的
`skills/douyin-pro/scripts/audit_pack_contrast.py`，并把它接进 `path_b_selftest.py`；
同时把自动选版的版式词表从 `choose_layout` 的散装字面量收成 `path_b_build.AUTO_LAYOUT_STEMS`
并上闸。**不含**任何渲染成片（见文末「未验证」）。

结论：**三道闸全绿；基线 42 处手抄假数全部订正（复算可复现）；审计器对伪造文档确实停机
（EXIT=1）；10 个未落地 pack 的 16 个词表外计划名清点复现。** 过程中查出的两处会被
"照文档办事"的人直接带进成片的错误（`news-blast` 的 1.18:1 巨号红字、`news-coral` 注释里
那个反向订正的 2.92），都已在文档与版式头注里改判。

---

## 1. 被验对象

```
skills/douyin-pro/scripts/audit_pack_contrast.py   16812 B   ★ 新增：frame.md 色板/对比度表复算
skills/douyin-pro/scripts/path_b_selftest.py        +58 行   判据 6 接入 + 审计器负例 + 词表锁
skills/douyin-pro/scripts/path_b_build.py           +34/-…   AUTO_LAYOUT_STEMS 单一词表（行为等价）
routes/news/{ARCHITECTURE,MEMORY}.md                        D9 重写 / 新增 D10 / §6 留存口径 / §8 实测
skills/news-workflow/SKILL.md                              三道闸 + 「补包前先重映射版式名」
templates/hyperframes_path_b/*/frame.md                     12 包对比度表改为复算值
templates/hyperframes_path_b/news-coral/compositions/*.html  4 文件（仅注释里的数值与依据）
```

`git diff --stat` = 21 文件 / +268 −117。coral 那 4 个 composition 的改动全在 `/* */` 头注内，
CSS 值一字未动（复算改的是**判读理由**，不是配色）。

## 2. 命令与实测输出（仓库根执行）

### 2.1 三道闸

```bash
python skills/douyin-pro/scripts/path_b_selftest.py
python skills/douyin-pro/scripts/audit_pack_contrast.py
python skills/douyin-pro/scripts/layout_selfcheck.py \
    skills/douyin-pro/templates/hyperframes_path_b/news-coral \
    skills/douyin-pro/templates/hyperframes_path_b/news-policy
```

```
[selftest] 61 项 · style=news-coral
  ok    t_auto_layout_stems_are_the_only_vocabulary
  ok    t_contrast_auditor_catches_a_planted_wrong_ratio
  ok    t_pack_contrast_docs_match_palette_math
[selftest] 全绿 61/61                                                      EXIT=0

对比度审计通过：12 个 pack 的 frame.md 色板与文档一致（0 条警告）          EXIT=0

版式自检通过：12 个文件，0 条违规                                          EXIT=0
```

58 → 61：新增的 3 项里只有 `t_pack_contrast_docs_match_palette_math` 扫全仓（12 包逐表复算），
另两项是**负例**（自己造证据、不依赖仓库当前内容）。

### 2.2 基线复算：42 处漂移是可复现的，不是记忆里的数

把**订正前的文档基线**（本轮改动落库前的那一次提交 `6f44f8e`；此后 HEAD 会前进，所以这里钉死 sha）
导出到忽略目录，再用审计器的 `discover_packs` + `audit_pack` 统计硬违规：

```bash
rm -rf .harness-news-runtime/tmp/contrast-baseline-6f44f8e && mkdir -p .harness-news-runtime/tmp/contrast-baseline-6f44f8e
git archive 6f44f8e skills/douyin-pro/templates/hyperframes_path_b | tar -x -C .harness-news-runtime/tmp/contrast-baseline-6f44f8e
python - <<'PY'
import sys, collections
from pathlib import Path
sys.path.insert(0, "skills/douyin-pro/scripts")          # 审计器取当前工作区那份（它只读文档表，无版本差）
import audit_pack_contrast as apc
root = Path(".harness-news-runtime/tmp/contrast-baseline-6f44f8e/skills/douyin-pro/templates/hyperframes_path_b")
packs, by_pack, by_rule = apc.discover_packs(root), collections.Counter(), collections.Counter()
for p in packs:
    hard = [f for f in apc.audit_pack(p)[1] if not f.warning]
    if hard:
        by_pack[p.name] = len(hard)
    for f in hard:
        by_rule[f.rule] += 1
print("pack 数:", len(packs), " 硬违规总数:", sum(by_pack.values()))
print("按 pack:", dict(sorted(by_pack.items(), key=lambda kv: -kv[1])))
print("按规则:", dict(by_rule))
PY
```

```
pack 数: 12  硬违规总数: 42
按 pack: {'news-coral': 8, 'news-blast': 4, 'news-explainer': 4, 'news-ink': 4, 'news-thread': 4,
          'news-world': 4, 'news-alert': 3, 'news-bulletin': 3, 'news-onsite': 3, 'news-stat': 3,
          'news-takes': 2}
按规则: {'DOC_RATIO_DRIFT': 42}
```

即 **11 个包 / 42 处**（`news-policy` 在 `6f44f8e` 里已订正，故 0 处）。基线里
`VERDICT_CONTRADICTS_ARITHMETIC` 为 0 —— 本仓没有"判读写反"的实例，该规则目前只由 §2.3 的
伪造样本证明它有效，别当成"仓库里已扫过一遍也没事"。

### 2.3 负例（审计器真的会停机，而不是打印建议）

伪造一份 `frame.md`（色板 ink/paper/gold，把 `ink / paper` 写成 9.99、把 2.54 判成"大字档"）：

```bash
python skills/douyin-pro/scripts/audit_pack_contrast.py .harness-news-runtime/tmp/planted-pack
```

```
planted-pack:DOC_RATIO_DRIFT:违规 —— 「ink / paper」文档写 9.99，按色板复算 15.20（ink #1a1a1a / paper #f5efe3）
planted-pack:VERDICT_CONTRADICTS_ARITHMETIC:违规 —— 「gold / paper」2.54 低于大字线 3.0，判定却写成大字可过

对比度审计不过：1 个 pack 里 2 条违规（另有 0 条警告）                      EXIT=1
```

临时样本跑完即删（`tmp/planted-pack`），伪造内容已在 selftest 的
`t_contrast_auditor_catches_a_planted_wrong_ratio` 里固化成断言 —— 这条负例从此不需要人再手动跑。

### 2.4 词表越界清单（D9 的依据，复现）

从 12 包 `frame.md` §7 抽 `*.html` 计划名（排除 `host` / `placeholder`），与
`path_b_build.AUTO_LAYOUT_STEMS` 求差：

```
词表: ['catalog', 'closer', 'hook', 'quote', 'rail', 'stat', 'story']
§7 计划名越界的 pack 数: 10  越界词干数: 16
  news-alert      ['list-steps', 'risk-callout']
  news-blast      ['play', 'score']
  news-bulletin   ['list']
  news-explainer  ['diagram', 'list']
  news-ink        ['evidence', 'lead-detail']
  news-onsite     ['clock', 'sit']
  news-stat       ['compare', 'drilldown']
  news-takes      ['chain']
  news-thread     ['segment']
  news-world      ['map', 'region']
可渲染 pack: ['news-coral', 'news-policy']
```

**这条坑是静默的**：照这些名字建文件不报错、`load_style_pack` 也放行（显式 `"layout"` 点名能用），
但自动模式永远选不到 —— 得到一个"看着齐备、实际惰性"的版式。
`t_auto_layout_stems_are_the_only_vocabulary` 现在双向锁死：`choose_layout` 点名表 ⊆ 词表 **且**
点名表 = 词表（防止词表里出现从不被优先点名的死名），再加每个可渲染 pack 的词干 ⊆ 词表。
最后一个 pack 变可渲染的那一刻生效。

## 3. 复算锚点（审计器自身对不对）

对 WCAG 2.x 公开锚点复核，公式与判读线都是外部事实，不是自证：

```
black / white        21.00   （规范上界 21:1）
#767676 / #ffffff     4.54   ≥ 4.5 过正文线
#777777 / #ffffff     4.48   < 4.5 不过 —— 阈值确实在咬
LARGE_TEXT_CQW     2.2222…  1080 宽下 1cqw=10.8px ⇒ 24px
BODY_MIN_RATIO          4.5
LARGE_MIN_RATIO         3.0
```

比对精度用**文档自己的小数位数**（写 15.20 就按两位比，写 5.16 按两位比），避免"四舍五入制造假违规"。

被改判的关键读数（`news-blast`，全部由审计器逐字校验）：

```
score(#C0392B) / pitch(#2D6A4F)     1.18   ✗ 红字压绿草等于没有字
gold(#B8923E)  / pitch              2.20   ✗ 连大字线 3.0 也不过
white(#F8F9FA) / pitch              6.06   ✓
white          / pitch-dark        10.51   ✓
score          / white              5.16   ✓ 白字下的红条（形状）合法
```

旧文档写的是 `score / pitch 5.0`、`gold / pitch 6.2`，而 §3 字阶据此把 22cqw 的主队比分染红。
**1.18:1 的 22cqw（≈238px）巨号字是要播出看不清的**，所以这一条不是文档瑕疵，是产品缺陷，
在文档阶段（还没有 HTML）就被拦下并改判为 white 数字 + score 只做红牌/下划条。

`news-coral` 的反向订正也记一下：注释原写"coral/ink = 2.92，连大字都不过"，复算真值 **5.10**
（根因是把 `L(ink)` 记成 0.0554，真值 0.0103）。数学过了，"珊瑚只作形状"仍然是**法则**（L1/L2）
而不是算术结论 —— 审计器据此区分 `DOC_RATIO_DRIFT` 与 `VERDICT_CONTRADICTS_ARITHMETIC`：
**法则可以比数学严，数学不行。**

## 4. 与一次性脚本的交接

`tmp/contrast_policy.py`（只覆盖 news-policy、硬编码 hex、无退出码契约）自本记录起**作废**：
它的判据被 `audit_pack_contrast.py` 覆盖并扩到 12 包，规则名/CLI/退出码进版本管理。
文件仍留在忽略目录（不删是为了对照旧实现），但**仓库内没有任何文档指向它**
（`grep -rn contrast_policy` 只命中 ARCHITECTURE.md §6 那句历史说明）。
这条正好是 §6 新写的留存口径的活例：**契约证据进 `scripts/`，一次性跑动留在忽略目录。**

## 5. 未验证 / 下一步

- ⏳ **未渲染任何成片**：本轮全部门禁都在"文档 + 发射前结构"层。1.18:1 那条改的是 frame.md
  的设计判读，`news-blast` 至今只有 `placeholder.html`，所以"改完真的好看"没有画面证据。
- ⏳ **审计器不校验 composition 实际用的色对**：它验的是 frame.md §2 色板 ↔ §2.1 对比表的一致性。
  版式 HTML 里写死的 hex 由 `OFF_PALETTE_HEX`（色板外 hex）和 `layout_selfcheck` 兜，
  但"某个字色是否真的压在它声称的地面上"需要渲染后目视/pixel 采样，未做。
- ⏳ **浏览器端的抗锯齿与字体回退**未测（需真渲）。
- ⏳ `VERDICT_CONTRADICTS_ARITHMETIC` 在仓库现状下命中 0，只有伪造样本证明它有效；
  下次谁改判定文案时要留意这条不是"从来没响过所以没用"。
- ⏳ 下一个补的包按 ARCHITECTURE §9：**`news-stat`**，动手前先按 §2.4 把 `compare` / `drilldown`
  重映射到词干，补完删 `placeholder.html`，再跑 `audit_pack_contrast.py`。
