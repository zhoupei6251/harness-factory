# 静态 composition 退役 · Phase 0（契约层 + 两道探针）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把发射器目前从 217 份 `compositions/*.html` 里正则抠出来的版式元数据，落成两份机器可读真源（`theme.toml` / `layouts.toml`），并证明与原 HTML 逐字段等价；同时跑完两道会改变后续计划的探针（变体簇数、GSAP 变量补间）。

**Architecture:** Phase 0 **不改渲染**，只加文件 + 加断言。新真源与旧 HTML 并存，等价闸保证任何漂移当场停机。Phase 1（14 个组件）与 Phase 3（删静态）各自另出计划——本计划的探针结果决定那两个计划的规模。

**Tech Stack:** Python 3.12（stdlib `tomllib` / 自研写出，无新依赖）、Vite 6 + Vue 3 + GSAP、tsx、仓库自带 harness（`path_b_selftest.py` 的 `check()`、`tests/web/vue-build.test.ts` 的 `check()`）。

**Spec:** `docs/plans/2026-10-13-news-static-pack-retire-vue-migration-spec.md`（§3 硬约束、§4 四层形态、§5 P0/P1 前置、§6 判据 0a/0b/1/2/3、§7 风险 2/3/5/6/7）

## Global Constraints

- **两个证据文件已作为桩存在并入库**：`routes/news/evidence/2026-10-13-pack-variant-clusters.md`
  与 `routes/news/evidence/2026-10-13-gsap-var-interpolation.md`。原因：`npm run validate`
  要求已跟踪文档里的 evidence pointer 必须指向已跟踪文件，而计划必须先给出确定文件名。
  桩文件顶部自标「未实测，桩文件」，**Task 6 Step 5 / Task 7 Step 3 是覆盖写入**，不是新建。
  执行时不要把桩内容当证据引用。

- 只动 `path_b` 手抄包；**不碰** `hf_compile.py` / `hf_primitives.py` / `hf_style_spec.py` / `hyperframes_path_c`（spec §1-4）。
- 本 Phase 不删任何文件、不改渲染路径、不改 `ALL_TEMPLATES` / `decide_pack.PACK_BUCKETS`。
- 每个任务结束时 `python skills/douyin-pro/scripts/path_b_selftest.py` 必须全绿，`npm test` 必须 exit 0。
- 提交信息用仓库现有风格（`feat(pack):` / `test(pack):` / `chore(deps):`），**只 commit 不 push**（AGENTS.md：push 是用户的事）。
- 断言一律给可机检口径；不允许「大致一致」「基本相同」。
- **开工前置（P0 之前）**：当前工作树带着一整批未提交的 Tier-3 Vue 集成改动，其中就包括本计划要反复 `git add` 的
  `path_b_selftest.py` 与 `path_b_build.py`。先把那批单独提交掉（提交信息由用户定，push 仍由用户决定），
  否则本计划每条 `git add path_b_selftest.py` 都会把上一批在途改动卷进不相干的提交里——
  这个仓库已经发生过两次「我自己的 `git rm` 把删除扫进无关提交」。**未清干净前不要开 P0。**
- 新增 TOML 键名用 snake_case 之外的原样 token 名（`coral`、`cream-dark` 这些是 frame.md 里的既有名，不重命名）。

---

### Task 1: 钉死 gsap / vue 版本（spec §7 风险 7）

**Files:**
- Modify: `package.json:27`（`"gsap": "^3.15.0"`）与 `"vue"` 那行
- Test: `tests/web/vue-build.test.ts`

**Interfaces:**
- Consumes: 无
- Produces: `package.json` 里 `gsap`/`vue` 为精确版本；`tests/web/vue-build.test.ts` 新增断言「声明版本 == lock 解析版本」

- [ ] **Step 1: 写失败断言**

在 `tests/web/vue-build.test.ts` 的 mount 契约断言之后追加：

```ts
check("渲染依赖版本已钉死（spec §7 风险 7：caret 范围让产物字节取决于 lock）", () => {
  const pkg = JSON.parse(readFileSync(resolve(ROOT, "package.json"), "utf8"));
  const deps = { ...pkg.dependencies, ...pkg.devDependencies };
  const lock = JSON.parse(readFileSync(resolve(ROOT, "package-lock.json"), "utf8"));
  for (const name of ["gsap", "vue"]) {
    const declared: string = deps[name];
    assert(
      /^\d+\.\d+\.\d+$/.test(declared),
      `${name} 声明为 ${declared}，不是精确版本 —— Vite 打进 bundle 的字节会随 lock 解析漂`
    );
    const resolved = lock.packages?.["node_modules/" + name]?.version;
    assert(
      resolved === declared,
      `${name} 声明 ${declared} 但 lock 解析 ${resolved} —— 两者必须一致`
    );
  }
});
```

- [ ] **Step 2: 跑测试确认它失败**

Run: `npm run test:web`
Expected: FAIL —— `gsap 声明为 ^3.15.0，不是精确版本`

- [ ] **Step 3: 钉版本**

```bash
npm install --save-exact gsap@3.15.0 vue@3.5.43
```

Expected：`package.json` 变成 `"gsap": "3.15.0"`、`"vue": "3.5.43"`（当前实测已安装即这两个版本，所以不该有实际升级）。

- [ ] **Step 4: 重建产物并确认字节未变**

```bash
rm -rf dist && npm run build:templates
md5sum dist/vue/news-coral-hook.js
```

Expected：`18e44aa98fa78cb8bb1d08324e9476a8`（今天真渲染用的就是这份；若变化说明版本真的动了，停下来报，不要继续）

- [ ] **Step 5: 跑全套 + 提交**

Run: `npm test` → exit 0

```bash
git add package.json package-lock.json tests/web/vue-build.test.ts
git commit -m "chore(deps): 钉死 gsap/vue 精确版本并加声明-解析一致性断言"
```

---

### Task 2: `theme.toml` 抽取器（frame.md 色板表 → 机器可读）

**Files:**
- Create: `skills/douyin-pro/scripts/pack_theme.py`
- Test: `skills/douyin-pro/scripts/path_b_selftest.py`

**Interfaces:**
- Consumes: `<pack>/frame.md` 的色板表行（实测 31/31 可解析，形如 `` | `coral` | `#E85D5D` | 主强调… | ``）
- Produces:
  - `pack_theme.parse_frame_md_palette(text: str) -> dict[str, str]`（token 名 → 小写 hex，保序）
  - `pack_theme.write_theme(pack_dir: str) -> str`（写 `<pack_dir>/theme.toml`，返回路径）
  - `pack_theme.THEME_FILENAME = "theme.toml"`
  - `pack_theme.load_theme(pack_dir: str) -> dict[str, str]`

- [ ] **Step 1: 写失败测试**

在 `path_b_selftest.py` 末尾（`if __name__ == "__main__"` **之前**）加：

```python
def t_parse_frame_md_palette_reads_named_hex_rows():
    text = (
        "## 1. 色板\n\n"
        "| token | 值 | 用途 |\n|---|---|---|\n"
        "| `coral` | `#E85D5D` | 主强调 |\n"
        "| `ink` | `#1A1A1A` | 墨底 |\n"
    )
    got = pack_theme.parse_frame_md_palette(text)
    assert got == {"coral": "#e85d5d", "ink": "#1a1a1a"}, f"读到 {got}"


def t_parse_frame_md_palette_ignores_unnamed_rows():
    text = "| 说明 | `#fff` | 不是 token 行 |\n| `a-b` | `red` | 值不是 hex |\n"
    assert pack_theme.parse_frame_md_palette(text) == {}, "非 token 行被收进来了"


def t_parse_frame_md_palette_only_reads_palette_sections():
    # 盘上实测 31 包的 398 行色板全落在标题含「色板」的小节内；
    # 不带这个限定的全文扫，将来任何一张 `| \`x\` | \`#hex\` |` 形状的非色板表都会被误收成 token。
    text = (
        "## 3. 字幕禁入区\n\n"
        "| `top` | `#000000` | 这不是色板 |\n"
        "\n## 1. 色板\n\n"
        "| `coral` | `#E85D5D` | 主强调 |\n"
    )
    assert pack_theme.parse_frame_md_palette(text) == {"coral": "#e85d5d"}, "色板以外的小节被读进来了"
```

并在文件顶部 import 段加 `import pack_theme  # noqa: E402`。

- [ ] **Step 2: 跑测试确认失败**

Run: `python skills/douyin-pro/scripts/path_b_selftest.py 2>&1 | grep palette`
Expected: `ERROR t_parse_frame_md_palette_reads_named_hex_rows: ModuleNotFoundError: No module named 'pack_theme'`

- [ ] **Step 3: 写最小实现**

```python
#!/usr/bin/env python3
"""pack_theme — frame.md 色板表 → theme.toml（Vue 路的主题真源）。

frame.md 是给人读的表（spec §2：31/31 可机器解析），theme.toml 是给发射器和
Vite 读的。真源仍是 frame.md：本模块每次抽取都以 frame.md 为准，串色闸
（Task 3）保证 theme.toml 不漂出它。

只认标题含「色板」的小节：实测 31 包的 398 行色板全在这类小节里，
而 `| \`名字\` | \`#hex\` |` 这个表格形状并不为色板独有——不限定小节，
将来任何一张同形状的表都会被误当成 token 源。
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

THEME_FILENAME = "theme.toml"

#: 形如 | `coral` | `#E85D5D` | 用途 | —— token 名列 + 值列必须是 hex。
_ROW_RE = re.compile(
    r"^\|\s*`(?P<name>[A-Za-z0-9][A-Za-z0-9_-]*)`\s*\|\s*"
    r"`(?P<hex>#[0-9a-fA-F]{3,8})`\s*\|",
    re.MULTILINE,
)

#: 只认标题含「色板」的 `##` 小节。
_PALETTE_KEYWORD = "色板"


def parse_frame_md_palette(text: str) -> dict[str, str]:
    """色板小节 → {token 名: 小写 hex}。同名后出现的覆盖前面的（frame.md 不重复列名）。"""
    palette: dict[str, str] = {}
    in_palette = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_palette = _PALETTE_KEYWORD in line
            continue
        if not in_palette:
            continue
        match = _ROW_RE.match(line)
        if match:
            palette[match.group("name")] = match.group("hex").lower()
    return palette


def write_theme(pack_dir: str) -> str:
    pack = Path(pack_dir)
    palette = parse_frame_md_palette((pack / "frame.md").read_text(encoding="utf-8"))
    if not palette:
        raise ValueError(f"{pack}: frame.md 里没解析到任何色板行（小节标题须含「色板」）")
    lines = [
        "# 编译产物：由 pack_theme.write_theme 从 frame.md 色板表生成，勿手改。",
        "schema = \"news-theme/1\"",
        "",
        "[tokens]",
    ]
    lines += [f'{name} = "{hex_value}"' for name, hex_value in palette.items()]
    out = pack / THEME_FILENAME
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(out)


def load_theme(pack_dir: str) -> dict[str, str]:
    path = Path(pack_dir) / THEME_FILENAME
    with path.open("rb") as fh:
        raw = tomllib.load(fh)
    return {str(k): str(v).lower() for k, v in raw.get("tokens", {}).items()}
```

> `_ROW_RE` 带 `re.MULTILINE` 是为别处整文扫也能用；这里逐行 `.match()` 不受影响。

- [ ] **Step 4: 跑测试确认通过**

Run: `python skills/douyin-pro/scripts/path_b_selftest.py 2>&1 | tail -2`
Expected: `[selftest] 全绿 190/190`（今天基线 187 + 本任务 3 条）

- [ ] **Step 5: 提交**

```bash
git add skills/douyin-pro/scripts/pack_theme.py skills/douyin-pro/scripts/path_b_selftest.py
git commit -m "feat(pack): pack_theme 抽取器 —— frame.md 色板表 → theme.toml"
```

---

### Task 3: 串色闸（判据 1，31/31 全跑）

**Files:**
- Modify: `skills/douyin-pro/scripts/pack_theme.py`
- Test: `skills/douyin-pro/scripts/path_b_selftest.py`

**Interfaces:**
- Consumes: Task 2 的 `parse_frame_md_palette` / `load_theme`；`path_b_build.ALL_TEMPLATES`（31 个包名）
- Produces: `pack_theme.verify_pack(pack_dir: str) -> list[str]`（问题列表，空 = 一致）

- [ ] **Step 1: 写失败测试**

```python
def t_theme_matches_frame_md_for_every_path_b_pack():
    problems = []
    for style in pb.ALL_TEMPLATES:
        pack_dir = os.path.join(pb.TEMPLATE_ROOT, style)
        if not os.path.isfile(os.path.join(pack_dir, pack_theme.THEME_FILENAME)):
            problems.append(f"{style}: 没有 theme.toml")
            continue
        problems += pack_theme.verify_pack(pack_dir)
    assert not problems, "串色闸失败:\n  " + "\n  ".join(problems)
```

> `pb.ALL_TEMPLATES`（`path_b_build.py:82`，31 项）与 `pb.TEMPLATE_ROOT`（:75，= `templates/hyperframes_path_b`）都已实测存在。
> `pack_theme` 在 selftest 顶部已 import，Task 3 不需要改 `path_b_build.py`。

- [ ] **Step 2: 跑测试确认失败**

Run: `python skills/douyin-pro/scripts/path_b_selftest.py 2>&1 | grep theme_matches`
Expected: FAIL —— `没有 theme.toml`（31 条）

- [ ] **Step 3: 生成 31 份 theme.toml 并补 verify_pack**

```bash
python -c "import sys; sys.path.insert(0, 'skills/douyin-pro/scripts')
import pack_theme as pt, path_b_build as pb, os
root = pb.TEMPLATE_ROOT
for s in pb.ALL_TEMPLATES: print(pt.write_theme(os.path.join(root, s)))"
```

`pack_theme.py` 追加：

```python
def verify_pack(pack_dir: str) -> list[str]:
    """theme.toml 必须与同目录 frame.md 色板表逐条相等（串色闸）。"""
    pack = Path(pack_dir)
    expected = parse_frame_md_palette((pack / "frame.md").read_text(encoding="utf-8"))
    if not expected:
        return [f"{pack.name}: frame.md 色板表解析为空 —— 闸等于没设"]
    if not (pack / THEME_FILENAME).exists():
        return [f"{pack.name}: 缺 {THEME_FILENAME}"]
    actual = load_theme(str(pack))
    problems = []
    for name, hex_value in expected.items():
        got = actual.get(name)
        if got is None:
            problems.append(f"{pack.name}: frame.md 有 `{name}`={hex_value} 但 theme.toml 缺")
        elif got != hex_value:
            problems.append(f"{pack.name}: `{name}` theme.toml={got} != frame.md={hex_value}")
    for name in actual:
        if name not in expected:
            problems.append(f"{pack.name}: theme.toml 有 `{name}` 但 frame.md 色板表里没有（凭空多出的 token）")
    return problems
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python skills/douyin-pro/scripts/path_b_selftest.py 2>&1 | tail -2`
Expected: 全绿；总数 +1

- [ ] **Step 5: 故意串一次色，证明闸会响**

```bash
python - <<'EOF'
import sys; sys.path.insert(0, "skills/douyin-pro/scripts")
import pack_theme as pt, path_b_build as pb, os, pathlib
p = pathlib.Path(os.path.join(pb.TEMPLATE_ROOT, "news-coral", pt.THEME_FILENAME))
orig = p.read_text(encoding="utf-8")
p.write_text(orig.replace('#e85d5d', '#00ff00', 1), encoding="utf-8")
print("已改脏")
EOF
python skills/douyin-pro/scripts/path_b_selftest.py 2>&1 | grep -E "FAIL.*theme_matches|串色"
```

Expected: FAIL 且消息点名 `news-coral: \`coral\` theme.toml=#00ff00 != frame.md=#e85d5d`

```bash
git checkout -- skills/douyin-pro/templates/hyperframes_path_b/news-coral/theme.toml 2>/dev/null \
  || python -c "import sys; sys.path.insert(0,'skills/douyin-pro/scripts'); import pack_theme as pt,path_b_build as pb,os; pt.write_theme(os.path.join(pb.TEMPLATE_ROOT,'news-coral'))"
```

- [ ] **Step 6: 跑全套 + 提交**

```bash
git add skills/douyin-pro/templates/hyperframes_path_b/*/theme.toml skills/douyin-pro/scripts/pack_theme.py skills/douyin-pro/scripts/path_b_selftest.py
git commit -m "feat(pack): 31 份 theme.toml + 串色闸（theme ↔ frame.md 逐条相等）"
```

> 本任务不改 `path_b_build.py`，别把它混进这次提交。提交前跑一次 `git status --short` 确认只含这三类文件。

---

### Task 4: `layouts.toml` 抽取器（判据 2 的前半）

**Files:**
- Create: `skills/douyin-pro/scripts/pack_layouts.py`
- Test: `skills/douyin-pro/scripts/path_b_selftest.py`

**Interfaces:**
- Consumes: `path_b_build.load_style_pack(style) -> dict`（现有；返回 `{"layouts": {role: {"composition_id","ground_hex","ground_tone","variables","file_name","name","path","primitives"}}}`）
- Produces:
  - `pack_layouts.write_layouts(pack_dir: str, pack: dict) -> str`（写 `<pack_dir>/layouts.toml`）
  - `pack_layouts.load_layouts(pack_dir: str) -> dict[str, dict]`（role → 记录）
  - `pack_layouts.LAYOUTS_FILENAME = "layouts.toml"`
  - `pack_layouts.verify_pack(pack_dir: str, live_pack: dict) -> list[str]`

- [ ] **Step 1: 写失败测试（写进 temp 目录，不碰仓库里的 pack）**

```python
def t_layouts_toml_roundtrip_keeps_loader_fields():
    # 用 tempfile 而不是 live["dir"]：测试往真 pack 目录写 layouts.toml，
    # 会把未审的产物留在工作树里，git status 当场不干净（AGENTS.md 的 hygiene gate）。
    for style in ("news-coral", "news-alert"):
        live = pb.load_style_pack(style)
        with tempfile.TemporaryDirectory() as tmp:
            pkl.write_layouts(tmp, live)
            got = pkl.load_layouts(tmp)
            assert set(got) == set(live["layouts"]), (
                f"{style}: 版式名集合不一致 {set(got) ^ set(live['layouts'])}")
            for role, rec in got.items():
                want = live["layouts"][role]
                assert rec["composition_id"] == want["composition_id"], f"{style}/{role} id 漂"
                assert rec["ground_hex"] == want["ground_hex"], f"{style}/{role} 地面色漂"
                assert rec["ground_tone"] == want["ground_tone"], f"{style}/{role} 明暗漂"
                assert rec["variable_ids"] == [v["id"] for v in want["variables"]], (
                    f"{style}/{role} 变量表漂")
            assert pkl.verify_pack(tmp, live) == [], f"{style}: round-trip 应零问题"
```

> `tempfile` 已在 `path_b_selftest.py` 顶部 import（现有测试就用它）。
> `verify_pack(tmp, live)` 这行同时把 Task 4 的实现和 Task 5 的闸口径绑在一起：同一份比对逻辑，别写两份。

顶部 import 段加 `import pack_layouts as pkl  # noqa: E402`。

- [ ] **Step 2: 跑测试确认失败**

Run: `python skills/douyin-pro/scripts/path_b_selftest.py 2>&1 | grep layouts_toml`
Expected: `ERROR ... ModuleNotFoundError: No module named 'pack_layouts'`

- [ ] **Step 3: 写实现**

```python
#!/usr/bin/env python3
"""pack_layouts — 版式登记表（spec §3：发射器现在的版式元数据长在 HTML 里）。

删掉 compositions/*.html 之后，发射器仍需知道每个版式的
composition_id / 变量契约 id / 地面色 / 地面明暗。这四样现在由
load_style_pack() 从 HTML 正则抠出来；本模块把它们落成 layouts.toml，
P3 改读这里。真源在 P3 之前仍是 HTML —— verify_pack 负责证明两边没分家。
"""
from __future__ import annotations

import tomllib
from pathlib import Path

LAYOUTS_FILENAME = "layouts.toml"

#: 落到登记表里的字段。HTML 里的 path/file_name 是过渡期才有的东西，不进来。
FIELDS = ("composition_id", "ground_hex", "ground_tone")


def _toml_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_layouts(pack_dir: str, pack: dict) -> str:
    lines = [
        "# 编译产物：由 pack_layouts.write_layouts 从 compositions/*.html 抽出，勿手改。",
        "schema = \"news-layouts/1\"",
        "",
    ]
    for role in sorted(pack["layouts"]):
        layout = pack["layouts"][role]
        lines.append(f"[layouts.{role}]")
        for field in FIELDS:
            lines.append(f"{field} = {_toml_str(str(layout[field]))}")
        ids = [var["id"] for var in layout["variables"]]
        lines.append("variable_ids = [" + ", ".join(_toml_str(i) for i in ids) + "]")
        lines.append("")
    out = Path(pack_dir) / LAYOUTS_FILENAME
    out.write_text("\n".join(lines), encoding="utf-8")
    return str(out)


def load_layouts(pack_dir: str) -> dict[str, dict]:
    with (Path(pack_dir) / LAYOUTS_FILENAME).open("rb") as fh:
        raw = tomllib.load(fh)
    return {role: dict(rec) for role, rec in raw.get("layouts", {}).items()}


def verify_pack(pack_dir: str, live_pack: dict) -> list[str]:
    """layouts.toml 与 load_style_pack() 当次读出的逐字段相等（等价闸）。"""
    path = Path(pack_dir) / LAYOUTS_FILENAME
    if not path.exists():
        return [f"{Path(pack_dir).name}: 缺 {LAYOUTS_FILENAME}"]
    got = load_layouts(pack_dir)
    live = live_pack["layouts"]
    problems = [f"{Path(pack_dir).name}: 登记表缺版式 {role}" for role in set(live) - set(got)]
    problems += [f"{Path(pack_dir).name}: 登记表多出版式 {role}" for role in set(got) - set(live)]
    for role in set(got) & set(live):
        rec, want = got[role], live[role]
        for field in FIELDS:
            if str(rec.get(field)) != str(want[field]):
                problems.append(f"{Path(pack_dir).name}/{role}: {field} "
                                f"登记表={rec.get(field)} != HTML={want[field]}")
        if list(rec.get("variable_ids", [])) != [v["id"] for v in want["variables"]]:
            problems.append(f"{Path(pack_dir).name}/{role}: variable_ids 不一致")
    return problems
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python skills/douyin-pro/scripts/path_b_selftest.py 2>&1 | tail -2`
Expected: 全绿

- [ ] **Step 5: 提交**

```bash
git add skills/douyin-pro/scripts/pack_layouts.py skills/douyin-pro/scripts/path_b_selftest.py
git commit -m "feat(pack): pack_layouts 版式登记表（composition_id/地面色/变量表换源）"
```

---

### Task 5: 217 条全量等价闸 + 变量 id 取值来源闸（判据 2、3）

**Files:**
- Create: `skills/douyin-pro/templates/hyperframes_path_b/<31 pack>/layouts.toml`（由 Step 3 命令行生成）
- Test: `skills/douyin-pro/scripts/path_b_selftest.py`

**Interfaces:**
- Consumes: Task 4 的 `pkl.verify_pack(pack_dir, live_pack)` / `pkl.write_layouts(pack_dir, live_pack)`；`path_b_build.DERIVERS`（:2160）/ `INDEXED_VAR_RE`（:2188）
- Produces: 31 份提交在库里的 `layouts.toml`（P3 改读它）；两条全量闸

- [ ] **Step 1: 写失败测试（只读比对，绝不在测试里生成被检物）**

```python
def t_layouts_equivalence_gate_covers_all_217_layouts():
    """layouts.toml 是**提交物**，本闸只拿它比 live HTML。
    若在断言前先 write_layouts 重刷一遍，committed 文件与 HTML 分家会被当场覆盖掉——
    那等于把闸删了。生成动作只属于本任务的 Step 3 命令行。"""
    problems, total = [], 0
    for style in pb.ALL_TEMPLATES:
        live = pb.load_style_pack(style)
        problems += pkl.verify_pack(live["dir"], live)
        total += len(live["layouts"])
    assert not problems, "等价闸失败:\n  " + "\n  ".join(problems)
    assert total == 217, f"版式总数应为 7 × {len(pb.ALL_TEMPLATES)} = {7 * len(pb.ALL_TEMPLATES)}，实得 {total}"
```

> 生成动作在 Step 3 用命令行做一次，产物随本任务提交。之后的任何会话里，这份文件与 HTML 一旦分家，此闸立刻红。

- [ ] **Step 1b: 变量 id 必须都有取值来源（词表 = 三条并集，不是 `DERIVERS` 一条）**

```python
#: 发射器给变量填值的三条来源。今天实测 1943 条变量 = 1571 条 DERIVERS 命中
#: + 372 条 INDEXED 语法 + imagePath/imageCredit 硬分支，无来源者 0 条。
IMAGE_SOURCED_IDS = {"imagePath", "imageCredit"}   # resolve_variable 里写死的取图分支


def t_every_layout_variable_id_has_a_source():
    unknown = []
    for style in pb.ALL_TEMPLATES:
        for role, layout in pb.load_style_pack(style)["layouts"].items():
            for var in layout["variables"]:
                var_id = var["id"]
                if var_id in pb.DERIVERS:
                    continue
                if pb.INDEXED_VAR_RE.match(var_id):
                    continue
                if var_id in IMAGE_SOURCED_IDS:
                    continue
                unknown.append(f"{style}/{role}: {var_id}")
    assert not unknown, ("这些变量 id 三条来源都不沾，抽取出来也填不进: "
                         + ", ".join(sorted(set(unknown))[:12]))
```

> **为什么不用 `register_indexed_derivers` 把 `itemN*` 灌进 `DERIVERS` 再判**：那个函数是运行时往全局
> 字典上挂推导器（`DERIVERS.setdefault`），测试若先跑过它，断言会因为**执行顺序**而变绿——
> 那是假绿。这里直接比 `INDEXED_VAR_RE` 这条语法本身，与跑测顺序无关。

- [ ] **Step 2: 跑测试确认失败**

Run: `python skills/douyin-pro/scripts/path_b_selftest.py 2>&1 | grep -E "217|has_a_source"`
Expected: 至少第一条 FAIL/ERROR（未生成 31 份 layouts.toml）

- [ ] **Step 3: 生成 31 份 `layouts.toml`（一次性命令行，不在测试里）**

```bash
python - <<'EOF'
import sys; sys.path.insert(0, "skills/douyin-pro/scripts")
import pack_layouts as pkl, path_b_build as pb
for style in pb.ALL_TEMPLATES:
    live = pb.load_style_pack(style)
    print(pkl.write_layouts(live["dir"], live))
EOF
```

Expected: 打印 31 个 `…/hyperframes_path_b/<pack>/layouts.toml` 路径，无异常。

再跑闸：

Run: `python skills/douyin-pro/scripts/path_b_selftest.py 2>&1 | tail -3`
Expected: 全绿；`total == 217`

若 `t_every_layout_variable_id_has_a_source` 报出无来源 id：**不要**加推导器凑数。停下报用户——那说明手抄包里有发射器填不了的死变量，属于 spec §7 之外的新发现。

- [ ] **Step 4: 故意改错一条，证明闸响**

```bash
python - <<'EOF'
import sys, pathlib; sys.path.insert(0, "skills/douyin-pro/scripts")
p = pathlib.Path("skills/douyin-pro/templates/hyperframes_path_b/news-coral/layouts.toml")
t = p.read_text(encoding="utf-8")
p.write_text(t.replace('composition_id = "nc-night-hook"', 'composition_id = "nc-night-hook-BOGUS"', 1), encoding="utf-8")
EOF
python skills/douyin-pro/scripts/path_b_selftest.py 2>&1 | grep -E "FAIL.*equivalence|composition_id"
```

Expected: FAIL 且消息点名 `news-coral/hook: composition_id 登记表=nc-night-hook-BOGUS != HTML=nc-night-hook`
（id 实测为 `nc-night-hook` —— 就是今天真渲染成功的那条镜。）

恢复：`python -c "import sys;sys.path.insert(0,'skills/douyin-pro/scripts');import pack_layouts as pkl,path_b_build as pb;pkl.write_layouts(pb.load_style_pack('news-coral')['dir'], pb.load_style_pack('news-coral'))"`

- [ ] **Step 5: 跑全套 + 提交**

Run: `npm test`（exit 0）+ `python skills/douyin-pro/scripts/path_b_selftest.py`（全绿）

```bash
git add skills/douyin-pro/templates/hyperframes_path_b/*/layouts.toml \
        skills/douyin-pro/scripts/pack_layouts.py \
        skills/douyin-pro/scripts/path_b_selftest.py
git status --short   # 确认没把别的在途改动一起带进来
git commit -m "feat(pack): 31 份 layouts.toml + 217 条等价闸 + 变量 id 取值来源闸"
```

> 不用 `git add skills/douyin-pro/scripts/` 这种目录级加法：当前工作树里 `path_b_build.py` 带着
> **本次迁移之外**的未提交改动（Tier-3 发射那批），目录级 `add` 会把它一起卷进这条提交。

---

### Task 6: 探针 0a —— 每角色真实变体簇（判据 0a，决定 Phase 1 的组件数）

**Files:**
- Create: `skills/douyin-pro/scripts/pack_variants.py`
- Create: `routes/news/evidence/2026-10-13-pack-variant-clusters.md`（脚本产出）
- Test: `skills/douyin-pro/scripts/path_b_selftest.py`

**Interfaces:**
- Consumes: 31 × 7 份 `compositions/*.html`
- Produces: `pack_variants.normalize(text: str) -> str`、`pack_variants.cluster_role(role: str) -> dict[str, list[str]]`（簇指纹 → pack 名列表）、`pack_variants.report() -> str`

- [ ] **Step 1: 写失败测试（锚定今天手工量到的两个已知事实）**

```python
def t_variant_clusters_hook_has_the_measured_two_shapes():
    clusters = pkv.cluster_role("hook")
    assert len(clusters) == 2, f"hook 归一化后应 2 簇，实得 {len(clusters)}: {list(clusters)}"
    sizes = sorted(len(v) for v in clusters.values())
    assert sizes == [1, 30], f"hook 簇规模应为 [1, 30]（news-policy 独一份），实得 {sizes}"


def t_normalize_strips_colors_ids_and_whitespace():
    a = '<div id="root" data-composition-id="nc-a" style="color:#E85D5D">\n  x  \n</div>'
    b = '<div id="root" data-composition-id="zz-z" style="color:#000000">\nx\n</div>'
    assert pkv.normalize(a) == pkv.normalize(b), "去色/去 id/去空白后两条应等值"
```

并在 `path_b_selftest.py` 顶部 import 段加 `import pack_variants as pkv  # noqa: E402`。

> `[1, 30]` 这两个数已用同一归一化口径预跑过一遍：`news-policy` 独一簇，其余 30 包同簇。
> 若执行时数字不同，说明盘上又动了，照实改测试并在提交信息里写明新分布——不要改归一化口径去凑。

- [ ] **Step 2: 跑测试确认失败**

Run: `python skills/douyin-pro/scripts/path_b_selftest.py 2>&1 | grep -i variant`
Expected: `ERROR ... No module named 'pack_variants'`

- [ ] **Step 3: 写实现**

```python
#!/usr/bin/env python3
"""pack_variants — 每角色的真实结构变体簇（spec §6 判据 0a）。

今天用 md5 抽样量到「每角色 2 变体」，但那是抽样结论。本脚本把它变成逐行证据：
去掉硬编码色值、data-composition-id 字面量、__timelines 键名与首尾空白后聚类，
簇数 = Phase 1 需要的组件数下界。簇数 > 2 的角色照实报，不压缩。
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import path_b_build as pb

ROLE_ORDER = ("hook", "stat", "rail", "quote", "catalog", "story", "closer")

_SUBS = (
    (re.compile(r"#[0-9a-fA-F]{3,8}\b"), ""),
    (re.compile(r"rgba?\([^)]*\)"), ""),
    (re.compile(r'data-composition-id="[^"]*"'), 'data-composition-id="ID"'),
    (re.compile(r'__timelines\["[^"]*"\]'), '__timelines["ID"]'),
)


def normalize(text: str) -> str:
    """去色 / 去 id 字面量 / 逐行首尾空白。空行保留 —— 它们是有结构的空白，不是噪声。"""
    for pattern, repl in _SUBS:
        text = pattern.sub(repl, text)
    return "\n".join(line.strip() for line in text.splitlines())


def _pack_dir(style: str) -> Path:
    return Path(pb.pack_dir(style))


def cluster_role(role: str) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {}
    for style in pb.ALL_TEMPLATES:
        path = _pack_dir(style) / "compositions" / f"{role}.html"
        if not path.is_file():
            continue
        fingerprint = hashlib.md5(
            normalize(path.read_text(encoding="utf-8")).encode("utf-8")
        ).hexdigest()[:12]
        buckets.setdefault(fingerprint, []).append(style)
    return buckets


def report() -> str:
    lines = ["# 每角色变体簇（判据 0a）", "",
             "口径：去硬编码色值 / `data-composition-id` 字面量 / `__timelines` 键名 / 首尾空白后聚 md5。",
             "", "| 角色 | pack 数 | 簇数 | 簇规模（降序） |", "|---|---|---|---|"]
    total = 0
    for role in ROLE_ORDER:
        buckets = cluster_role(role)
        sizes = sorted((len(v) for v in buckets.values()), reverse=True)
        total += len(buckets)
        lines.append(f"| `{role}` | {sum(sizes)} | {len(buckets)} | {sizes} |")
    lines += ["", f"**组件数下界 = {total}**（spec 里写的 14 是抽样推定，以本表为准）。", ""]
    for role in ROLE_ORDER:
        for fingerprint, styles in cluster_role(role).items():
            if len(styles) <= 1 or len(styles) == len(pb.ALL_TEMPLATES):
                continue
            lines.append(f"- `{role}` 非主流簇（{len(styles)} 包）: {', '.join(sorted(styles))}")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python skills/douyin-pro/scripts/path_b_selftest.py 2>&1 | tail -2`
Expected: 全绿。若 `hook` 不是 `[1, 30]`，**照实记录真实数字**并把测试改成实际簇数——这条测的是盘上事实，不是我的预期。

- [ ] **Step 5: 产出证据文件**

```bash
python -c "import sys;sys.path.insert(0,'skills/douyin-pro/scripts');import pack_variants as kv;open('routes/news/evidence/2026-10-13-pack-variant-clusters.md','w',encoding='utf-8').write(kv.report())"
cat routes/news/evidence/2026-10-13-pack-variant-clusters.md
```

Expected: 表格里 7 行，末尾给出组件数下界。

- [ ] **Step 6: 提交**

```bash
git add skills/douyin-pro/scripts/pack_variants.py routes/news/evidence/2026-10-13-pack-variant-clusters.md skills/douyin-pro/scripts/path_b_selftest.py
git commit -m "feat(pack): 判据 0a —— 每角色真实变体簇量化并落证据"
```

> **闸后动作（人来定）**：若组件数下界明显 > 14，回 spec §7 风险 5 更新数字，再决定 Phase 1 是否分批。不要把计划改成迁就数字。

---

### Task 7: 探针 0b —— GSAP 能否补间 `var(--x)`（判据 0b）

**Files:**
- Create: `src/web/probes/gsap-var-probe/main.ts`（一次性探针，不进 `entries/`，故不被 Vite 扫成产线入口）
- Create: `routes/news/evidence/2026-10-13-gsap-var-interpolation.md`

**Interfaces:**
- Consumes: `gsap` npm 包（与产线同一版本）
- Produces: 一条结论 —— **能** 或 **不能**，附两帧实测颜色值

- [ ] **Step 1: 写探针（浏览器里跑，不用引擎）**

```ts
// src/web/probes/gsap-var-probe/main.ts
// 一次性探针：验证 GSAP 的 color 补间能否吃 var(--x)。结论写进 evidence 后即删。
import { gsap } from "gsap";

const box = document.createElement("div");
box.style.setProperty("--x", "#ff0000");
box.style.setProperty("--y", "#0000ff");
box.style.color = "var(--x)";
box.textContent = "probe";
document.body.appendChild(box);

const tl = gsap.timeline({ paused: true });
tl.fromTo(box, { color: "var(--x)" }, { color: "var(--y)", duration: 1 });

const at = (t: number) => {
  tl.time(t);
  return getComputedStyle(box).color;
};

(globalThis as any).__probe_result = {
  t0: at(0), t05: at(0.5), t1: at(1),
};
```

- [ ] **Step 2: 用 chrome-devtools MCP 真跑一次，取三色值**

打包用 esbuild（仓库里 vite 自带，实测可跑；**不要**用 `vite build <文件>`——vite 的位置参数是 root 不是入口）：

```bash
mkdir -p /tmp/gsap-probe
npx esbuild src/web/probes/gsap-var-probe/main.ts --bundle --format=esm \
  --outfile=/tmp/gsap-probe/out.js
```

Expected: `out.js` 约 165 kB（gsap 全量打进来），无报错。探针自己会把结果写到
`globalThis.__probe_result`，页码引一行即可，存成 `/tmp/gsap-probe/index.html`：

```html
<!doctype html><meta charset="utf-8"><body>
<script type="module" src="./out.js"></script>
```

然后按顺序调用 MCP 工具（三个都在本会话已暴露）：
1. `mcp__plugin_chrome-devtools-mcp_chrome-devtools__new_page` → `url: file:///tmp/gsap-probe/index.html`
2. `...__evaluate_script` → 表达式 `globalThis.__probe_result`（等 1s 让 module 执行完；返回 `{t0,t05,t1}`）
3. `...__close_page`

判读口径（写死，不凭感觉）：
- `t0` == `rgb(255, 0, 0)` 且 `t1` == `rgb(0, 0, 255)` 且 `t05` 是两个通道都在中间值（如 `rgb(127.x, 0, 127.x)` 或 GSAP 的 `rgba(...)` 形式）⇒ **能补间**
- `t05` 与 `t0` 完全相同，或 `t05` 为 `rgb(0, 0, 0)` / 空串 / 含 `NaN` ⇒ **不能**（GSAP 解析不了 `var(--x)`，直接退化）

- [ ] **Step 2b: 若本机无法起 Chrome**

不要改成「用 jsdom 近似」——jsdom 不算 CSS 变量，结论会是假的。停下报用户，把判据 0b 标为**未闭**，
B 方案按「必须保留 hex 字面量」这个保守分支执行（保守分支不阻塞 Phase 1）。

- [ ] **Step 3: 写结论**

`routes/news/evidence/2026-10-13-gsap-var-interpolation.md`：

```markdown
# GSAP color 补间是否支持 var(--x)（判据 0b）

- 探针：src/web/probes/gsap-var-probe/main.ts（gsap <版本>）
- t0 / t0.5 / t1 实测：<值> / <值> / <值>
- 结论：**能 / 不能** —— 所以 spec §4 的 B 方案里「GSAP 从 theme JSON 取 hex 字面量」这条
  <可以省掉 / 必须保留>。
```

- [ ] **Step 4: 按结论回写 spec**

在 spec §4 那段先验注记后面追加一行实测结论（含日期与三色值）。**不改 A/B 选择本身**，只改 B 内部要不要那层解析。

- [ ] **Step 5: 删探针 + 提交**

```bash
rm -rf src/web/probes
rm -rf dist && npm run build:templates && npm run test:web >/dev/null 2>&1; echo "exit=$?"
git add routes/news/evidence/2026-10-13-gsap-var-interpolation.md docs/plans/2026-10-13-news-static-pack-retire-vue-migration-spec.md
git commit -m "docs(news): 判据 0b 实测 —— GSAP var() 补间能力回写 spec"
```

Expected: `exit=0`（探针不在 `entries/` 下，删掉后构建产物应与 Task 1 Step 4 的 md5 一致）

---

## Self-Review

**1. Spec coverage**（本计划只覆盖 P0 + P1 前置；P1 七轮、P2、P3 各有后续计划）

| spec 条目 | 覆盖任务 |
|---|---|
| §7 风险 7（gsap caret） | Task 1 |
| §4 L2 `theme.toml` | Task 2、3 |
| §4 L0 `layouts.toml` | Task 4、5 |
| §6 判据 1（串色闸 31/31） | Task 3 Step 1 |
| §6 判据 2（等价闸 217/217） | Task 5 Step 1 |
| §6 判据 3（变量 id 有取值来源，三条并集） | Task 5 Step 1b |
| §6 判据 0a（变体簇） | Task 6 |
| §6 判据 0b（GSAP var） | Task 7 |
| §5-P1 步骤 1-4（14 组件 / 217 登记 / 结构闸 / 像素抽样） | **不在本计划**（等 Task 6 的簇数出来再定规模） |
| §5-P2 路由切换、§5-P3 删静态 | **不在本计划** |
| §3 硬约束（版式元数据长在 HTML 里） | Task 4/5 换源，本计划不删 HTML 所以不触发 |

**2. Placeholder 扫描**：无 TBD/TODO。Task 7 Step 2 原来是「择一（浏览器控制台 / MCP）」——那等于把执行方式推给执行者，已改成写死的一条命令（`npx esbuild … --bundle --format=esm`，本机实测 165 kB 产出）+ 三个具名 MCP 调用顺序 + 三色值判读口径；并补了 Step 2b 作为「Chrome 起不来」时的唯一出路（停下报未闭，走保守分支，**不许**用 jsdom 近似——jsdom 不算 CSS 变量，结论会是假的）。

**3. 类型一致性**：`verify_pack` 在 `pack_theme`（入参 `pack_dir`）与 `pack_layouts`（入参 `pack_dir, live_pack`）签名不同——两者语义不同（前者自己读 frame.md，后者要比对传入的 live），保留差异，调用点（Task 3 Step 1 / Task 5 Step 1）已按各自签名写。`load_theme` / `load_layouts` 均返回 `dict`，键为 token 名 / 版式名，与 Produces 段一致。

**4. 计划内引用已逐条核过盘上（不再留「执行时以盘上为准」的活口）**：
`pb.ALL_TEMPLATES`（:82，31 项）、`pb.TEMPLATE_ROOT`（:75，指向 `templates/hyperframes_path_b`）、
`pb.pack_dir(style)`（:133）、`pb.DERIVERS`（:2160）、`pb.INDEXED_VAR_RE`（:2188）、`load_style_pack` 返回体的键
（`dir` / `layouts`，layout 内 `composition_id` / `ground_hex` / `ground_tone` / `variables[{id,…}]`）
均已实跑确认；`news-coral/hook` 的 `composition_id = "nc-night-hook"`、`ground_hex = "#0a0a0d"`、
`ground_tone = "dark"` 为 Task 5 Step 4 的替换字面量来源。Task 6 的 `[1, 30]` 亦已用同一归一化口径预跑一遍，
落单的那个 pack 是 `news-policy`。

**5. 自审抓出并修掉的四个缺陷**（都在写计划时用真实数据跑出来，不是排版问题）：

| # | 缺陷 | 后果 | 修法 |
|---|---|---|---|
| 1 | 判据 3 写成「变量 id ⊆ `DERIVERS`」 | 今天 1943 条变量里 **796 条会红**——`item*/step*` 由 `INDEXED_VAR_RE` 语法在运行时挂表，`imagePath/imageCredit` 走 `resolve_variable` 硬分支，都不在 `DERIVERS` 字面键里 | 词表改成三条并集，并按真实分布写死预期（1571 + 372 + 图片位，无来源 0 条）；spec §5/§6 同步改 |
| 2 | Task 5 的等价闸在断言前 `write_layouts` 重刷提交物 | committed 文件与 HTML 一旦分家会被当场覆盖 ⇒ **闸自己把自己关掉** | 生成只留 Step 3 命令行；测试只读比对 |
| 3 | Task 4 的 round-trip 测试往真 pack 目录写 `layouts.toml` | 工作树留下未审产物，撞 AGENTS.md 的 hygiene gate | 改 `tempfile.TemporaryDirectory()` |
| 4 | Task 2 的抽取器扫全文 | 别处任何一张 `| \`x\` | \`#hex\` |` 形状的表都会被误收成 token | 限定小节标题含「色板」；实测 31 包的 398 行色板恰好全在这类小节内（`1. 色板` / `1. 色板（本包真实用色）` / `2. 色板` 三种写法），限定不丢行 |
