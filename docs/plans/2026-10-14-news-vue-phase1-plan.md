# 静态 composition 退役 · Phase 1（机制 + hook 闭环）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 用 superpowers:subagent-driven-development 逐任务派发。步骤用 `- [ ]`。

**Goal:** 让「一个版式组件 × 每包槽位值」成为版式的唯一生产路径，并把 hook 角色在全部 31 个包上做到与静态支**像素零漂移**，为 Phase 2（其余 6 角色）与 Phase 3（删 227 份静态文件）拆掉全部前置。

**Architecture:** 三层。① `pack_slots.py` 从现有 HTML 抽出**有序色位槽**并用「逐字节还原」自证无损；② 发射器按 `(pack, role)` 路由到组件，并把该包该角色的槽位值以 inline `:root{--cNN:…}` 注入宿主；③ 组件 CSS 只读 `var(--cNN)`，**不补间颜色**（盘上实测补间属性全集里没有颜色，故 JS 侧无需颜色解析）。静态文件本 Phase 一份不删。

**Tech Stack:** Python 3.12（stdlib `tomllib`，无新依赖）、Vue 3 SFC + Vite 6 + GSAP 3.15.0（已钉）、仓库自带 harness（`path_b_selftest.py` 的 `t_*`、`tests/web/vue-build.test.ts` 的 `check()`）。

**Spec:** `docs/plans/2026-10-13-news-static-pack-retire-vue-migration-spec.md`
**证据（本计划的经验前提）:** `routes/news/evidence/2026-10-14-render-census-and-lossless-theme-slots.md`

## Global Constraints

- 台账可复现口径 = **结构一致**，不承诺逐字节（spec §1-2，用户拍方案②）。
- **1:1 保真**：本 Phase 不改变任何包的视觉（用户 2026-10-14 拍）。`hook` 的 11 个色位在 30 个包里取值相同，仍走同一套注入机制，**不开例外分支**。
- 不碰 `hf_compile.py` / `hf_primitives.py` / `hf_style_spec.py` / `hyperframes_path_c` / `spec.toml`（spec §1-4）。
- 不删 `compositions/*.html`（那是 Phase 3）。不碰 `ALL_TEMPLATES` / `decide_pack.PACK_BUCKETS`。
- 组件里**禁止补间颜色**；这条由 Task 3 的断言机检，不是约定。
- 版式组件的 CSS 色值一律 `var(--cNN)`，**不得**出现 `var()` 回退值或硬编码 hex（除三个非色位的结构色，见 Task 5 白名单）。
- 渲染验证一律画面轨：`--skip-render` + `npx hyperframes render -f 25 --quality=draft --no-browser-gpu`，Node ≥22。配音不可用（403），不进任何判据。
- `git push` 由用户做；每次提交前 `git diff --cached --name-only` 逐条核对（本仓已三次发生无关改动被卷入）。
- 闸门基线：`path_b_selftest.py` 202/202、`npm test` exit 0、`tests/web/vue-build.test.ts` 17 条。

---

### Task 1: `pack_slots.py` —— 有序色位槽抽取 + 无损还原闸

**Files:**
- Create: `skills/douyin-pro/scripts/pack_slots.py`
- Test: `skills/douyin-pro/scripts/path_b_selftest.py`

**Interfaces:**
- Consumes: `pb.ALL_TEMPLATES`（:82，31 项）、`pb.pack_dir(style)`（:133）、Phase 0 的 `pb.load_style_pack(style)["layouts"]`
- Produces:
  - `pack_slots.SLOT_RE` = `re.compile(r"#[0-9a-fA-F]{3,8}")`
  - `pack_slots.normalize(text: str) -> str` —— 去 hex / 去 `data-composition-id` 与 `__timelines["…"]` 字面量 / 逐行 strip
  - `pack_slots.template_of(pack: str, role: str) -> tuple[str, list[str]]` —— 返回该包该角色的 `(归一化模板, 有序 hex 列表)`
  - `pack_slots.variant_of(pack: str, role: str) -> str` —— `"a"`（主流簇）或 `"b"`
  - `pack_slots.reconstruct(base_pack: str, role: str, pack: str) -> str` —— 用 base 的文件 + 目标包的 hex 序列 + 目标包的 `composition_id` 回填
  - `pack_slots.verify_pack_role(base_pack: str, role: str, packs: list[str]) -> list[str]`
  - `pack_slots.mainstream_base(role: str) -> str` —— 该角色最大簇的代表包名

- [ ] **Step 1: 写失败测试**

```python
def test_slots_reconstruct_every_pack_byte_exact():
    """Phase 0 证据 §2 量到 7 角色 × 30 包逐字节还原成功。
    本闸把它从「一次性脚本结论」变成仓内持续断言：
    还原失败 = 该角色存在色位/id 之外的差异 = 分层方案前提破了，当场停。"""
    problems = []
    for role in pkv.ROLE_ORDER:
        base = pks.mainstream_base(role)
        packs = [s for s in pb.ALL_TEMPLATES if pks.variant_of(s, role) == "a"]
        problems += pks.verify_pack_role(base, role, packs)
    assert not problems, "槽位无损还原失败:\n  " + "\n  ".join(problems)


def test_variant_b_is_exactly_news_policy():
    """第二簇今天只有一族：news-policy。盘上若长出第三簇，本闸点名，不许静默按 a 处理。"""
    for role in pkv.ROLE_ORDER:
        b = [s for s in pb.ALL_TEMPLATES if pks.variant_of(s, role) == "b"]
        assert b in ([], ["news-policy"]), f"{role} 的第二簇不是 news-policy: {b}"


def test_slot_count_matches_evidence():
    """Phase 0 证据 §2 表里的色位槽数：写死做绊线，改了版式必须显式承认。"""
    want = {"hook": 11, "stat": 12, "rail": 8, "quote": 8,
            "catalog": 8, "story": 9, "closer": 9}
    got = {r: len(pks.template_of(pks.mainstream_base(r), r)[1]) for r in want}
    assert got == want, f"色位槽数漂移: {got} != {want}"
```

- [ ] **Step 2: 跑测试确认失败** —— `python skills/douyin-pro/scripts/path_b_selftest.py 2>&1 | grep -i slots`
  Expected: 非零退出 + 输出含 `No module named 'pack_slots'`（顶层 import 就死，不会打 `ERROR t_…`；口径同 Phase 0 Ruling F）

- [ ] **Step 3: 写实现**

```python
#!/usr/bin/env python3
"""pack_slots —— 静态版式的有序色位槽与无损还原证明（Phase 1 的地基）。

分层方案的等价性不靠人眼看像素：若「主流模板 + 每包有序 hex + 该包 composition_id」
能逐字节还原每个包的原始文件，则该角色不存在色位与 id 之外的差异，可以安全合并为一个组件。
还原不了就是前提破了，当场报错，不许退化成"差不多"。
"""
from __future__ import annotations

import re
from pathlib import Path

import path_b_build as pb
import pack_variants as pkv

HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}")
CID_RE = re.compile(r'data-composition-id="(?P<cid>[^"]+)"')

_cache: dict[tuple[str, str], tuple[str, list[str], str]] = {}


def normalize(text: str) -> str:
    text = re.sub(r'data-composition-id="[^"]*"', 'data-composition-id="ID"', text)
    text = re.sub(r'__timelines\["[^"]*"\]', '__timelines["ID"]', text)
    return "\n".join(line.strip() for line in HEX_RE.sub("HEX", text).splitlines())


def _read(pack: str, role: str) -> str:
    return (Path(pb.pack_dir(pack)) / "compositions" / f"{role}.html").read_text(encoding="utf-8")


def template_of(pack: str, role: str) -> tuple[str, list[str]]:
    text = _read(pack, role)
    return normalize(text), HEX_RE.findall(text)


def mainstream_base(role: str) -> str:
    """最大簇的代表包：取簇内排序第一个，保证跨进程稳定。"""
    buckets = pkv.cluster_role(role)
    biggest = max(buckets.values(), key=len)
    return sorted(biggest)[0]


def variant_of(pack: str, role: str) -> str:
    base = mainstream_base(role)
    return "a" if normalize(_read(pack, role)) == normalize(_read(base, role)) else "b"


def reconstruct(base_pack: str, role: str, pack: str) -> str:
    base = _read(base_pack, role)
    target = _read(pack, role)
    values = HEX_RE.findall(target)
    base_cid = CID_RE.search(base).group("cid")
    target_cid = CID_RE.search(target).group("cid")
    if len(values) != len(HEX_RE.findall(base)):
        raise ValueError(f"{pack}/{role} 色位数 {len(values)} ≠ 模板 {len(HEX_RE.findall(base))}")
    it = iter(values)
    return CID_RE.sub(lambda m: f'data-composition-id="{target_cid}"',
                      HEX_RE.sub(lambda _m: next(it), base.replace(base_cid, target_cid)))


def verify_pack_role(base_pack: str, role: str, packs: list[str]) -> list[str]:
    out = []
    for pack in packs:
        try:
            got = reconstruct(base_pack, role, pack)
        except ValueError as exc:
            out.append(str(exc))
            continue
        if got != _read(pack, role):
            out.append(f"{pack}/{role}: 还原后与原始文件不等（存在色位与 id 之外的差异）")
    return out
```

- [ ] **Step 4: 跑测试确认通过** —— Expected: 全绿，总数 205/205
- [ ] **Step 5: 提交** —— `git add skills/douyin-pro/scripts/pack_slots.py skills/douyin-pro/scripts/path_b_selftest.py && git commit -m "feat(pack): pack_slots 有序色位槽 + 逐字节无损还原闸"`

---

### Task 2: 挂载身份换成每次唯一的 `mount_id`（spec §7 风险 9）

**Files:**
- Modify: `skills/douyin-pro/scripts/path_b_build.py`（`VUE_MOUNT_TPL` 约 :476、loader 串 约 :490）
- Modify: `src/web/lib/hyperframes-bridge.ts`、`src/web/entries/news-coral-hook/main.ts`
- Test: `path_b_selftest.py`、`tests/web/vue-build.test.ts`

**Interfaces:**
- Produces: `VUE_MOUNT_TPL` 的内层挂载点变为 `<div class="vue-target"></div>`（**无 id**）；loader 改为 `clip.querySelector(':scope > .vue-target')`，并把该 clip 元素本身传给 `mod.mount(clip, compId)`
- Consumes: `bridge.readVariables(clip: Element)` —— 从**传入的 clip** 读 `data-variable-values`，不再全局 `querySelector`
- 组件侧时间轴注册键：`window.__timelines[`${compositionId}#${mountIndex}`]`，`mountIndex` 由 loader 从 `clip.id`（`shot-N`）取

- [ ] **Step 1: 写失败测试**

```python
def test_two_same_role_vue_mounts_have_unique_targets():
    """spec §7 风险 9：同一次渲染里同一版式会出现两次（实测 20 镜样本 hook×7），
    旧写法 id="vue-target-{composition_id}" 会生成重复 id ⇒ getElementById 只命中第一个。"""
    pack = pb.load_style_pack("news-coral")
    hook = pack["layouts"]["hook"]
    a = pb.emit_mount(1, hook, {"kicker": "A"}, 0.0, 4.0, 1080, 1920)
    b = pb.emit_mount(7, hook, {"kicker": "B"}, 24.0, 4.0, 1080, 1920)
    assert 'id="vue-target-' not in a and 'id="vue-target-' not in b, \
        "挂载点仍以 composition_id 为 id，重复版式必撞车"
    assert a.count('class="vue-target"') == 1 and b.count('class="vue-target"') == 1
    assert f'id="shot-1"' in a and f'id="shot-7"' in b, "clip 自身 id 必须仍是每次唯一的 mount_id"
```

- [ ] **Step 2: 跑测试确认失败**（Expected: FAIL，消息点名「仍以 composition_id 为 id」）
- [ ] **Step 3: 改 `VUE_MOUNT_TPL` 与 loader**

```python
VUE_MOUNT_TPL = (
    '      <div id="{mount_id}" class="clip"'
    ' data-composition-id="{composition_id}"'
    ' data-vue-mount="1"'
    ' data-vue-bundle="{bundle_name}"'
    ' data-variable-values="{values}"'
    ' data-start="{start}" data-duration="{dur}" data-track-index="1"'
    ' data-width="{w}" data-height="{h}">'
    '        <div class="vue-target"></div>'
    '      </div>'
)
```

loader 脚本体（`VUE_HOST_INJECTION` 内）：

```js
for (const clip of document.querySelectorAll('[data-vue-mount]')) {
  const compId = clip.dataset.compositionId;
  const bundle = clip.dataset.vueBundle;
  const target = clip.querySelector(':scope > .vue-target');
  if (!target) continue;
  const mod = await import('./vue/' + bundle + '.js');
  mod.mount(clip, compId);
}
```

`hyperframes-bridge.ts`：`readVariables(clip: Element)`，删掉模块级 `COMPOSITION_ID` 常量与全局 `querySelector`；`main.ts` 的 `mount(target, id)` 第一参数改为 clip，内部 `target.querySelector(':scope > .vue-target')` 取得真正挂载节点；`__timelines` 键改为 `` `${compositionId}#${clip.id}` ``。

- [ ] **Step 4: 跑测 + 真渲染复验** —— `python skills/douyin-pro/scripts/path_b_selftest.py`（206/206）、`npm test`、`HF_NODE22_DIR=… python routes/news/scripts/pack_render_census.py --only news-coral` 仍须 `pass:true` 且零 WARN
- [ ] **Step 5: 提交** —— `git commit -m "fix(pack): Vue 挂载身份改用每次唯一的 mount_id，消除同版式重复时的 target 撞车"`

---

### Task 3: 主题注入（发射侧 CSS 变量）+「禁止补间颜色」规则闸

**Files:**
- Modify: `path_b_build.py`（`VUE_HOST_INJECTION`、`emit_host`）
- Modify: `pack_slots.py`（导出 `slot_block()`）
- Test: `path_b_selftest.py`、`tests/web/vue-build.test.ts`

**Interfaces:**
- Produces:
  - `pack_slots.slot_css(pack: str, role: str) -> str` —— 形如 `--c0:#0a0a0d;--c1:#e85d5d;…`（**有序**，索引即组件里的 `var(--cN)` 序号）
  - 发射产物：每个 Vue clip 的 clip 元素上带 `style="{slot_css}"`（作用域在 clip 内，避免多镜互相覆盖），宿主 `<style>` 只留公共部分
- Consumes: Task 1 的 `template_of`

- [ ] **Step 1: 写失败测试（三条例）**

```python
def test_slot_css_is_ordered_and_pack_specific():
    a = pks.slot_css("news-coral", "stat")
    b = pks.slot_css("news-alert", "stat")
    assert a.startswith("--c0:") and "--c11:" in a, f"槽位必须按序编号: {a}"
    assert a != b, "stat 的色位随包变化，两包注入串不该相同"
    assert len(re.findall(r"--c\d+:", a)) == 12


def test_vue_clip_carries_its_own_slot_block():
    pack = pb.load_style_pack("news-alert")
    out = pb.emit_mount(2, pack["layouts"]["stat"], {"value": "1"}, 0.0, 4.0, 1080, 1920)
    assert "--c0:" in out, "Vue clip 没带槽位块，色值会掉回组件默认值 ⇒ 串色"


def test_components_must_not_tween_colors():
    """盘上实测：217 份静态版式的补间实参里 0 条颜色语义（属性全集只有
    duration/ease/opacity/scaleX/y/x/scale/yPercent/scaleY）。
    这条把它钉成规则 —— 一旦有人补间颜色，CSS 变量在 GSAP 里不生效（判据 0b 实测），
    必须先改机制再改版式。"""
    offenders = []
    for path in sorted((REPO / "src/web").rglob("*.vue")):
        body = path.read_text(encoding="utf-8")
        for m in re.finditer(r"\.(?:fromTo|to|set|from)\(([\s\S]*?)\)\s*(?:;|\n)", body):
            if re.search(r"\b(color|background|backgroundColor|borderColor|fill|stroke)\b\s*:", m.group(1)):
                offenders.append(path.name)
                break
    assert not offenders, f"组件补间了颜色（CSS 变量在此处不生效）: {sorted(set(offenders))}"
```

- [ ] **Step 2: 确认失败**（`slot_css` 不存在 / clip 无槽位块 / 现有组件若含颜色补间则点名）
- [ ] **Step 3: 实现** —— `slot_css()` 按 `template_of` 的 hex 顺序编号；`emit_mount` 的 Vue 分支拼 `style="{slot_css}"`；非 Vue 分支**不加**（静态支字节不变，普查基线仍可用）
- [ ] **Step 4: 全量回归** —— selftest 209/209、`npm test` exit 0；`pack_render_census.py` 全 31 包仍 pass 且零 WARN（静态支未受影响）
- [ ] **Step 5: 提交** —— `git commit -m "feat(pack): Vue clip 自带有序槽位块，并机检「组件不得补间颜色」"`

---

### Task 4: `(pack, role)` 路由表替换 id 白名单

**Files:**
- Modify: `path_b_build.py`（`VUE_COMPOSITIONS` :471、`emit_mount` :2454、`stage_vue_assets` :2391）
- Test: `path_b_selftest.py`

**Interfaces:**
- Produces: `VUE_ROUTES: dict[tuple[str, str], str]`，键 `(pack, role)`、值 bundle 名；`vue_bundle_for(pack: str, role: str) -> str | None`；`VUE_COMPOSITIONS` **删除**（不留兼容层）
- Consumes: Task 1 的 `variant_of` ⇒ bundle 名 = `f"{role}-{variant}"`（如 `hook-a` / `hook-b`）

- [ ] **Step 1: 写失败测试**

```python
def test_route_table_keys_are_pack_and_role_not_composition_id():
    """217 条镜只有 130 个不同 composition_id（30 包的 hook 同名 nc-night-hook）。
    按 id 登记会一次翻 30 包 —— 本 Phase 靠 1:1 保真侥幸等价，但路由键必须是 (pack, role)。"""
    ids = [pack["layouts"][role]["composition_id"]
           for pack in (pb.load_style_pack(s) for s in pb.ALL_TEMPLATES)
           for role in ("hook",) if "hook" in pack["layouts"]]
    assert len(set(ids)) < len(ids), "样本里 hook id 若已唯一，这条断言该改而不是删"
    assert pb.vue_bundle_for("news-alert", "hook") == "hook-a"
    assert pb.vue_bundle_for("news-policy", "hook") == "hook-b"


def test_stage_vue_assets_collects_bundles_from_pack():
    pack = pb.load_style_pack("news-coral")
    assert "hook-a" in {pb.vue_bundle_for("news-coral", r) for r in pack["layouts"]}
```

- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现**（`vue_bundle_for` 先查 `VUE_ROUTES`，未命中回落 `f"{role}-{pks.variant_of(pack, role)}"` 仅在 `CUTOVER_ROLES` 集合内启用；本 Phase `CUTOVER_ROLES = {"hook"}`）
- [ ] **Step 4: 回归** —— selftest 211/211；`npm test`；普查 31/31 零 WARN
- [ ] **Step 5: 提交**

---

### Task 5: hook 角色闭环 —— `hook-a` / `hook-b` 组件 + 像素零漂移对拍

**Files:**
- Move: `src/web/entries/news-coral-hook/` → `src/web/entries/hook-a/`（`main.ts` + `HookA.vue`；`main.html` 预览页随之更名）
- Create: `src/web/entries/hook-b/`（从 `news-policy/compositions/hook.html` 1:1 移植）
- Delete: `src/web/lib/tokens/coral.ts`（版式自带色直接写进组件 CSS，槽位化由 `--cNN` 承担；`relativeLuminance`/`contrastRatio` 两个纯函数若被引用则迁到 `src/web/lib/contrast.ts` 保留）
- Modify: `tests/web/vue-build.test.ts`（入口名与断言）、`path_b_build.py`（`CUTOVER_ROLES` 生效面）
- Test: 新增 `routes/news/scripts/vue_pixel_ab.py`（静态支 vs Vue 支同 seek 截图比对）

**Interfaces:**
- Produces: `dist/vue/hook-a.js` / `dist/vue/hook-b.js`（入口由目录扫描自动产出，`vite.config.ts` 不改）
- Consumes: Task 3 的 `--cNN` 槽位块、Task 2 的 `mount(clip, compId)` 契约

- [ ] **Step 1: `hook-a` 主题化改造** —— 把 `HookA.vue` 的 `<style>` 里 11 个 hex 依 `template_of("news-coral","hook")` 的**出现顺序**替换为 `var(--c0)…var(--c10)`。白名单：`#fff`/`rgba(0,0,0,.55)` 这类**结构色**（在所有 31 个包中都相同且不属于该角色色位序列的）保留字面量 —— 判据是「出现在 `template_of` 的 hex 序列里」而非人眼判断。

- [ ] **Step 2: 结构闸断言（全量，31 包）**

```python
def test_hook_vue_route_registered_for_every_pack():
    """31 个包的 hook 全部有路由，且包内 bundle 与 variant 一致。"""
    for pack in pb.ALL_TEMPLATES:
        role = "hook"
        want = f"hook-{pks.variant_of(pack, role)}"
        assert pb.vue_bundle_for(pack, role) == want, f"{pack} 路由错"
```

- [ ] **Step 3: 像素对拍工具 `vue_pixel_ab.py`**（同稿同包，两支各渲一次画面轨，取 3 个 seek 点比 PSNR）

```python
"""静态支 vs Vue 支的像素对拍：同稿、同包、同 seek 点，逐帧比 PSNR。

判据：psnr avg ≥ 40 dB 且 maxdiff ≤ 2/255。基线是 Phase 0 普查的静态支产物。
静态支 hook.html 30 包字节相同 ⇒ 两支理论应零漂移；测出漂移即移植改变了外观，当场停。
"""
PSNR_CMD = ["ffmpeg", "-hide_banner", "-i", "{a}", "-i", "{b}",
            "-lavfi", "[0:v][1:v]psnr=stats_file=-", "-f", "null", "-"]
```

- [ ] **Step 4: 跑对拍**（本 Phase 的像素预算按 pack 轮转角色，hook 分到 `news-coral` / `news-world` / `news-noir` / `news-podcast` / `news-alert-warning` 共 5 包）
  Expected: 5/5 达阈（`psnr avg=inf` 也接受 —— 完全相同）
- [ ] **Step 5: `npm test` + selftest + 普查全绿后提交** —— `git commit -m "feat(news): hook 版式改为槽位化组件，31 包路由闭环"`

---

## 交接给 Phase 2 / 3 的边界

- Phase 2 = 其余 6 角色（`stat`/`rail`/`catalog`/`closer` 有色位随包变，`quote`/`story` 不变），逐角色重复 Task 5 的形状；组件总数仍是 14。每个角色的色位槽数已在 `test_slot_count_matches_evidence` 里钉死。
- Phase 3 = 把 `CUTOVER_ROLES` 扩到 7 → `load_style_pack` 改读 `layouts.toml` → 删 217 份 `compositions/*.html` + 10 份 `placeholder.html` + `host.html:5` 的 CDN GSAP。
- 未闭项：`vite` / `@vitejs/plugin-vue` 仍是 caret（产物字节仍部分取决于 lock）；台账重渲只承诺结构一致（spec §1-2）。
