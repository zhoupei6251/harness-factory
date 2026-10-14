# 31 pack 画面轨普查 + 静态版式的无损槽位化证明（2026-10-14）

回答两个问题：**「新闻域的模板现在都能跑通吗」**、**「静态 HTML 能不能等价地换成 Vue，而不是靠人眼看像素」**。
两条都是盘上实测，命令与产物可复现。

---

## §1 画面轨真渲染普查：31/31 通过

命令（已入库，不再是一次性 Temp 脚本）：

```bash
HF_NODE22_DIR="D:/Users/zhoupei/AppData/Local/nvm/v22.20.0" \
  python routes/news/scripts/pack_render_census.py
```

条件：稿件 `t001-scenes.json`（5 镜）· 每包 `--skip-render` 发射 → `hyperframes render -f 25 --quality=draft --no-browser-gpu`
· 三路并行 · 零配音（`edge-tts` 403 未解，见 `2026-10-13-hyperframes-vue-poc-verification-lite.md` §10.b）。

逐包判据（五条全绿才算 pass）：`emit_exit==0` 且 `index.html` 生成 · `render_exit==0` ·
`silent.mp4 > 100 KB` · `render.log` 里 `WARN|ERROR` 计数 `==0` · 终值 `framesCompleted == totalFrames > 0`。

| 指标 | 结果 |
|---|---|
| 通过 | **31/31** |
| 每包 clip 数 | 5 |
| 帧数 | 1309/1309（全部） |
| WARN / ERROR | 0（全部） |
| `silent.mp4` | 1.9 – 3.0 MB |
| 产物目录 | `.harness-news-runtime/tmp/render-census/<pack>/`（`index.html` / `silent.mp4` / `render.log` / `emit.log` / `row.json`）+ `_summary.md` |

**`data-vue-mount` 分布：30 个包 = 2（首镜走 Vue），只有 `news-policy` = 0。**
即「发射器现在真正用 Vue 的只有 hook 一条镜，且因为它按 `composition_id` 命中白名单、而这 30 个包的 hook 同名，
这一条 Vue bundle 实际服务 30 个包」。其余 6 个版式仍是静态 HTML 填充。

## §1.a 普查判据的**覆盖边界**（Phase 1 Task 2 修复轮实测出来，必须和上面的结论一起读）

普查走 `--skip-render`，而发射器在该分支里**整步跳过取图**（日志：`分镜 → images: 跳过 (--skip-render / --check-only 不取图)`），
于是每镜 `imagePath` 恒为空串 ⇒ **§1 的 31/31 只覆盖「无图镜」的发射与渲染**。
带图路径（图位、`has-photo` 修饰类、署名行、`#hk-img` 补间）在本普查里**从未被执行**。

已知的唯一带图真覆盖来自 Phase 1 Task 2 的重复版式 fixture（两镜同 `hook`、各带一张不同纯色图，真渲染逐帧核对）。
⇒ 把 Vue 支当交付之前，验收必须显式含带图镜；`pack_render_census.py` 需加取图支或另建带图 fixture（已记进 Phase 1 计划的遗留）。

### 普查脚本自己错过的三处（写明，免得下次照抄）

1. 判据五原本用 `re.search` 取**第一条** `totalFrames/framesCompleted` —— 那是 capture 起点的
   checkpoint（`framesCompleted:0`），于是首轮 21 个包全被误判失败。现取**最后一条**（assemble 终值）。
2. 首版跑完 `rm -rf` 临时目录，产物没处复核。现全部保留。
3. 附带一条 Windows 口径：`subprocess` 不带 shell 时裸 `npx` 报 `ENOENT`（PATHEXT 不解析），须 `npx.cmd`。

---

## §2 静态版式可以**无损槽位化**（这条才是能否等价替换的关键）

问：把版式从 HTML 搬进 Vue 后，凭什么说没改外观？
答：先证明「主流模板 + 每包一组槽位值」能**逐字节还原**每个包的原始文件。还原不了就说明那不是颜色差异，
分层方案要改。

口径：`norm(t)` = 把 `data-composition-id` / `__timelines["…"]` 的字面量换成 `ID`、所有 hex 换成 `HEX`、逐行 strip。
按 `norm` 聚类取最大簇的第一个包原文件作模板，再把每包的**有序 hex 列表**与**该包的 `composition_id`** 回填。

| 角色 | 主流簇 | 色位槽数 | `composition_id` 出现次数 | 逐字节还原 |
|---|---|---|---|---|
| `hook` | 30/31 | 11 | 2 | **30/31，0 失败** |
| `stat` | 30/31 | 12 | 2 | **30/31，0 失败** |
| `rail` | 30/31 | 8 | 2 | **30/31，0 失败** |
| `quote` | 30/31 | 8 | 2 | **30/31，0 失败** |
| `catalog` | 30/31 | 8 | 2 | **30/31，0 失败** |
| `story` | 30/31 | 9 | 2 | **30/31，0 失败** |
| `closer` | 30/31 | 9 | 2 | **30/31，0 失败** |

⇒ **7 个角色全部无损**。每个角色 = 1 个主流模板 + 1 个第二簇（一律是 `news-policy`）
⇒ 版式组件数 **14** 由「抽样推定」升级为「逐行实证」。
⇒ 还原需要的槽位只有两类：**有序色值位** + **`composition_id` 位**，没有别的自由度。

### 顺带证伪了我自己的一条推断

`spec §7 风险 8` 原来写「按 `composition_id` 登记白名单会让 29 个别主题包错色」。**错**：
`hook.html` 在这 30 个包里**字节完全相同**（`diff` 0 行，11 个色位取的是同一套值）——
即 hook 版式今天根本不随包换色，全用 `coral` 那套硬编码色。30 镜走 Vue 与走静态视觉等价。
已在 spec 撤回，并换成同一轮复查量出的真缺陷（风险 9：挂载点 id 用 `composition_id`，
同一次渲染同版式重复即撞车，实测 20 镜样本 hook×7 / story×6 / closer×7）。

### 这条不是待拍项：迁移期按 1:1 保真（2026-10-14 用户已拍）

既然 `hook` 的 11 个色位在 30 个包里全是同一个 `coral` 值，迁 Vue 时有两种做法：

- **1:1 保真**（**已选**）：组件保留这些值原样，不随包换色 —— 视觉零变化，与 §1 的普查基线可比。
- 顺带主题化（**未选**）：把 hook 的色位也接上各包 `theme.toml`。这会**改变现有成片外观**
  （29 个包的 hook 换色），且 `theme.toml` 里没有 hook 的语义位定义 —— 属于设计变更，不是迁移。

⇒ 迁移期真正需要随包注入色值的只有 `stat`/`rail`/`catalog`/`closer` 四个角色；
`hook`/`quote`/`story` 的槽位在 30 个包里取值相同，注入结果等于原值（**仍走同一套机制，不开例外分支**，
例外分支正是 31 份手抄文件的来路）。

---

## §3 槽位注入（Task 3，2026-10-14）

发射侧把每角色文件的**有序 hex** 编号为 CSS 自定义属性 `--c0 … --cN`，挂到 Vue clip 元素自身的
`style` 上（作用域在 clip 内，两镜不同包/角色互不覆盖）；静态支（`MOUNT_TPL`）**不带** `style`，
所以 §1 的 31/31 逐字节普查基线不受影响。实现：`pack_slots.slot_css(pack, role)` +
`path_b_build.emit_mount` 的 Vue 分支。

### 实测槽数（`slot_css` 计数 == `template_of(...)[1]` 的 hex 数，逐角色）

命令（离线，只读盘）：

```bash
python - <<'PY'
import sys; sys.path.insert(0, "skills/douyin-pro/scripts")
import pack_slots as pks, re
for role in ("hook","stat","rail","quote","catalog","story","closer"):
    n = len(re.findall(r"--c\d+:", pks.slot_css("news-coral", role)))
    print(role, n)
PY
```

| 角色 | 槽数 `--c0…` | 与 §2 表一致 |
|---|---|---|
| `hook` | 11 | ✅ |
| `stat` | 12 | ✅ |
| `rail` | 8 | ✅ |
| `quote` | 8 | ✅ |
| `catalog` | 8 | ✅ |
| `story` | 9 | ✅ |
| `closer` | 9 | ✅ |

### 「盘上 0 条颜色补间」= 机检闸门 `t_components_must_not_tween_colors`

§2 证明分层方案的**色位**能无损还原；本条把「主题注入只能是 CSS、不能是 GSAP 补间」钉成规则
（GSAP 无法插值 `var(--x)`，见 §2 / 判据 0b）。盘点命令（扫 `compositions/*.html` 全部
`fromTo/to/set/from` 实参里的属性键）：

```bash
python - <<'PY'
import sys, re; from pathlib import Path
sys.path.insert(0, "skills/douyin-pro/scripts")
import path_b_build as pb
CALL = re.compile(r"\.(?:fromTo|to|set|from)\s*\(([\s\S]*?)\)\s*(?:;|\n)")
COLOR = re.compile(r"\b(color|background|backgroundColor|borderColor|fill|stroke)\b\s*:")
files, props, offenders = [], set(), []
for pack in pb.ALL_TEMPLATES:
    d = Path(pb.pack_dir(pack)) / "compositions"
    if d.is_dir():
        files += [f for f in d.glob("*.html") if f.name != "placeholder.html"]
for f in files:
    for m in CALL.finditer(f.read_text(encoding="utf-8")):
        props.update(re.findall(r"([A-Za-z_][\w]*)\s*:", m.group(1)))
        if COLOR.search(m.group(1)):
            offenders.append(f.name)
print("非占位版式文件数:", len(files))
print("被补间的属性全集:", sorted(props))
print("补间了颜色的文件:", sorted(set(offenders)) or "无")
PY
```

**实测结果（2026-10-14）**：
- 非占位版式文件 **217** 份（31 包 × 7 角色，`news-editorial-warm` 等编译包补齐到 217 口径；占位壳已排除）；
- 被补间的属性全集 = `{duration, ease, opacity, scale, scaleX, scaleY, x, y, yPercent}`；
- **补间了颜色的文件 = 无（0 条）**。

⇒ 全 217 份静态版式的补间里 **0 条颜色语义**，主题注入因此**只能是 CSS 变量**，无需给 GSAP 开例外；
`t_components_must_not_tween_colors` 现扫 `src/web/**/*.vue`（当前组件同样 0 命中）把这条固化为闸门。
若日后需要颜色补间，闸门会当场 FAIL，强制先改机制（不能悄悄用 `var(--x)` 骗过渲染）。

### 发射产物取证（单包真渲染 `--only news-coral`）

`.harness-news-runtime/tmp/render-census/news-coral/index.html` 内 5 个 `class="clip"`：
首镜走 Vue（`data-vue-mount`），其余 4 镜走静态 HTML。逐条属性：

```
vue=True  style='--c0:#0a0a0d;--c1:#f5f0e8;--c2:#c0392b;--c3:#ffffff;--c4:#e85d5d;
                  --c5:#c0392b;--c6:#ffffff;--c7:#c0392b;--c8:#dcdcdc;--c9:#b0b0b0;--c10:#dcdcdc;'
vue=False style=None   （×4 条静态 clip）
```

⇒ Vue clip 自带 11 个 hook 槽（`--c0…--c10`），静态 clip 一律无 `style`（字节不变）。
`row.json`：`emit_exit=0 · render_exit=0 · warn=0 · frames 1309/1309 · pass:true`。
