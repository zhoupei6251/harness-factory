# 2026-10-13 · hyperframes-vue POC · Tier 3 host.html 嵌入 plan

> 本文是 spec（`docs/plans/2026-10-13-hyperframes-vue-tier3-host-integration-spec.md`）的实施步骤。
> 顺序：先 Vite 产物路径 → Vue 应用 mount 形态 → path_b_build → 测试 → 静态验证。

## §0 顺序与依赖

```
Step 1 (Vite 输出路径)
    ↓
Step 2 (Vue 应用 mount 形态: 改 main.ts/main.html/NewsCoralHook.vue)
    ↓
Step 3 (path_b_build: VUE_COMPOSITIONS + emit_mount 分支 + emit_host 注入)
    ↓
Step 4 (vue-build.test.ts 新断言)
    ↓
Step 5 (path_b_selftest.py 新断言)
    ↓
Step 6 (全门禁跑一遍: vue-build / selftest / audit / npm test)
    ↓
Step 7 (写 verification-tier3 + commit message 草稿)
```

每步可独立回滚（不依赖后续步）。

## §1 Step 1 · Vite 产物路径改 `vue/`

**改 `vite.config.ts`**：

```typescript
output: {
  entryFileNames: "vue/[name].js",       // 旧: "[name].js"
  chunkFileNames: "vue/chunks/[name]-[hash].js",
  assetFileNames: "vue/assets/[name]-[hash][extname]",
}
```

**验证**：`npm run build:templates` → `find dist` 应有 `dist/vue/news-coral-hook.js`、`dist/vue/assets/news-coral-hook-*.css`。

**回滚**：把 entryFileNames 改回 `[name].js`，清 dist，重 build。

## §2 Step 2 · Vue 应用改 mount 形态

**改 `src/web/entries/news-coral-hook/main.html`**（11 行 → 5 行）：

```html
<!doctype html>
<html lang="zh-CN">
  <head><meta charset="UTF-8" /></head>
  <body></body>  <!-- caller 传 target，不再写死 #app -->
</html>
```

**改 `src/web/entries/news-coral-hook/main.ts`**（8 行 → 25 行）：

```typescript
import { createApp } from "vue";
import NewsCoralHook from "./NewsCoralHook.vue";

/**
 * HyperFrames Vue mount 入口
 *
 * host.html 的 loader script 调本函数：传 mount target 元素 + composition_id，
 * Vue 应用 mount 到 target，从最近的 [data-composition-id="..."] 读 data-variable-values。
 */
export function mount(target: HTMLElement, compositionId: string): void {
  createApp(NewsCoralHook, { compositionId }).mount(target);
}

// Vite preview 时也能独立预览（独立 mount 点 vue app）
if (document.getElementById("vue-preview-target")) {
  mount(document.getElementById("vue-preview-target")!, "nc-night-hook");
}
```

**改 `src/web/entries/news-coral-hook/NewsCoralHook.vue`**（2 处）：

1. `<script setup>`：加 props 接收 compositionId，但实际 hyperframes-bridge 自己 querySelector 不依赖 props；保留 props 是为了 spec §3.4 提到的 contract
2. 删除原 `main.html` 的 `<div id="app">` 后，Vue 应用直接 mount 到 caller 传的 target

**改 `src/web/lib/hyperframes-bridge.ts`**（不变，bridge 已读 DOM dataset.variableValues）。

**验证**：跑 `npm run build:templates` + `tsx tests/web/vue-build.test.ts` —— Step 4 加新断言前全过。

## §3 Step 3 · path_b_build 改动

**改 `skills/douyin-pro/scripts/path_b_build.py`**：

### §3.1 加常量（紧跟 MOUNT_TPL line 466 后）

```python
#: Tier 3 POC: 哪些 composition 走 Vue 版（composition_id -> vue bundle 文件名）。
#: Vue bundle 在 work_dir/vue/<name>.js（path_b 拷贝自 dist/vue/<name>.js）。
#: 任何不在此表里的 composition 仍走 MOUNT_TPL 的 data-composition-src HTML 形态。
VUE_COMPOSITIONS: dict[str, str] = {
    "nc-night-hook": "news-coral-hook",   # news-coral/hook.vue.html
}

#: Vue 版 mount 模板：不引 data-composition-src（hyperframes 引擎不识别 Vue mount），
#: 含 data-vue-mount 标记，host.html 的 loader script 异步 import 对应 bundle。
VUE_MOUNT_TPL = (
    '      <div id="{mount_id}" class="clip"'
    ' data-composition-id="{composition_id}"'
    ' data-vue-mount="1"'
    ' data-vue-bundle="{bundle_name}"'
    ' data-variable-values="{values}"'
    ' data-start="{start}" data-duration="{dur}" data-track-index="1"'
    ' data-width="{w}" data-height="{h}">'
    '        <div id="vue-target-{composition_id}"></div>'
    '      </div>'
)

#: 注入到 host.html </head> 前的 Vue runtime + loader script（仅当任意 mount 是 Vue 版时注入）。
VUE_HOST_INJECTION = """\
    <script src="vue/vue.runtime.global.prod.js"></script>
    <script>
      (async () => {
        for (const clip of document.querySelectorAll('[data-vue-mount]')) {
          const compId = clip.dataset.compositionId;
          const bundle = clip.dataset.vueBundle;
          const target = document.getElementById('vue-target-' + compId);
          if (!target) continue;
          const mod = await import('./vue/' + bundle + '.js');
          mod.mount(target, compId);
        }
      })();
    </script>
"""
```

### §3.2 改 emit_mount（line 2322-2337）

```python
def emit_mount(mount_index: int, layout: dict, values: dict, start: float,
               dur: float, w: int, h: int) -> str:
    payload = dict(values)
    payload["slotSeconds"] = round(dur, 3)
    encoded = html.escape(json.dumps(payload, ensure_ascii=False), quote=True)
    mount_id = f"shot-{mount_index}"
    composition_id = layout["composition_id"]
    common = dict(
        mount_id=mount_id, composition_id=composition_id,
        values=encoded, start=fmt_secs(start), dur=dur, w=w, h=h,
    )
    # Tier 3: Vue 版 composition 用 VUE_MOUNT_TPL，否则原 MOUNT_TPL
    if composition_id in VUE_COMPOSITIONS:
        return VUE_MOUNT_TPL.format(bundle_name=VUE_COMPOSITIONS[composition_id], **common)
    return MOUNT_TPL.format(file_name=layout["file_name"], **common)
```

### §3.3 改 emit_host（line 2288-2319）—— 仅当有 Vue mount 时注入

```python
def emit_host(pack: dict, mounts: list[str], audios: list[str], total: float,
              w: int, h: int) -> str:
    host = pack["host"]
    for token in HOST_PLACEHOLDERS:
        if token not in host:
            raise EmitterError(f"host.html 缺少占位符 {token}")
    # Tier 3: 检查 mounts 里是否有 Vue 版 mount
    has_vue = any('data-vue-mount="1"' in m for m in mounts)
    vue_injection = VUE_HOST_INJECTION if has_vue else ""
    filled = (
        host.replace("{{COMPOSITION_ID}}", HOST_COMPOSITION_ID)
        .replace("{{W}}", str(w))
        .replace("{{H}}", str(h))
        .replace("{{TOTAL}}", fmt_secs(total))
        .replace("{{SCENES}}", "\n".join(mounts))
        .replace("{{AUDIOS}}", "\n".join(audios))
        .replace("{{VUE_INJECTION}}", vue_injection)  # host.html 加占位符
    )
    # 现有 leftover 检查保留
    ...
    # 现有 copy/marker 检查保留（Vue 版 mount 不含 data-composition-src，
    # 故该断言需跳过 Vue 版 mount —— 见 Step 5 新断言补偿）
```

### §3.4 改每个 pack 的 host.html（19 个 pack × host.html）

加 `{{VUE_INJECTION}}` 占位符到 `</head>` 前：

```html
<head>
  <meta charset="UTF-8" />
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <style>...</style>
  {{VUE_INJECTION}}   <!-- 新增：Vue 版 mount 出现时填 loader 脚本，否则空 -->
</head>
```

**注意**：原 host.html line 7 注释提到「占位符少了或多写都算包与脚本不一致 → 停机」——加 `{{VUE_INJECTION}}` 占位符后，emit_host 的 placeholder 检查会因找不到它而停机。需把 VUE_INJECTION 加进 `HOST_PLACEHOLDERS` 集合。

### §3.5 拷 Vue bundle 到 work_dir

在 `path_b_build.py` 主流程的 emit_host 后加：

```python
# Tier 3: 把 Vue bundles 拷到 work_dir/vue/，host.html 引用相对路径
if any('data-vue-mount="1"' in m for m in mounts):
    vue_src = resolve(repo_root, "dist", "vue")
    vue_dst = resolve(work_dir, "vue")
    if os.path.isdir(vue_src):
        os.makedirs(vue_dst, exist_ok=True)
        for entry in os.listdir(vue_src):
            shutil.copyfile(os.path.join(vue_src, entry), os.path.join(vue_dst, entry))
```

## §5 Step 4 · vue-build.test.ts 加断言

在现有 10 条断言后加：

```typescript
check("Vue bundle 落在 dist/vue/news-coral-hook.js", () => {
  const p = resolve(DIST, "vue", "news-coral-hook.js");
  assert(existsSync(p), `not found: ${p}`);
});
check("Vue bundle 路径被 main.ts 通过 import() 引用（loader 用相对路径 ./vue/）", () => {
  // main.ts 应生成 import('./vue/news-coral-hook.js') 的引用
  const js = readFileSync(DIST_ENTRY_JS, "utf8");
  // dist 入口是 dist/news-coral-hook.js 或 dist/vue/news-coral-hook.js？
  // —— Step 1 把所有产物落到 dist/vue/，所以入口就是 vue/news-coral-hook.js。
  // 这里只验证 main.ts 在 main bundle 里没写死绝对路径。
  assert(!js.includes("/dist/vue/"), "main bundle 包含 /dist/vue/ 绝对路径会破坏 host.html 相对路径引用");
});
```

## §6 Step 5 · path_b_selftest.py 加断言

在 `t_all_templates_in_constant` 等 pack 测试附近加新测试组：

```python
# Tier 3: Vue composition mount 元素协议
def t_vue_mount_has_no_composition_src():
    """VUE_COMPOSITIONS 里的 composition_id 走 VUE_MOUNT_TPL，不含 data-composition-src。"""
    from path_b_build import VUE_COMPOSITIONS, emit_mount, VUE_MOUNT_TPL
    layout = PACK["layouts"]["hook"]
    ctx = base_ctx(is_first=True)
    values = pb.fill_variables(layout, pb.parse_input(HOOK_BEAT)[0], ctx)
    out = pb.emit_mount(1, layout, values, 0.0, 4.0, 1080, 1920)
    assert "nc-night-hook" in VUE_COMPOSITIONS
    assert 'data-vue-mount="1"' in out, f"Vue 版 mount 必须含 data-vue-mount: {out}"
    assert 'data-composition-src=' not in out, f"Vue 版 mount 不该含 data-composition-src: {out}"
    assert 'data-vue-bundle="news-coral-hook"' in out

def t_html_mount_still_uses_composition_src():
    """非 VUE_COMPOSITIONS 里的 composition_id 仍走 MOUNT_TPL。"""
    # stat / rail / catalog 等其它 layout
    for name, layout in PACK["layouts"].items():
        if layout["composition_id"] in pb.VUE_COMPOSITIONS:
            continue
        # 用占位 scene 触发 emit_mount
        ...
```

注意：实际写断言时调 emit_mount 需要 layout dict 字段全（name/file_name/path/composition_id/variables）。PACK["layouts"][name] 已具备。

## §7 Step 6 · 全门禁

按顺序：

```bash
npm run build:templates
node node_modules/tsx/dist/cli.mjs tests/web/vue-build.test.ts
python skills/douyin-pro/scripts/path_b_selftest.py
python skills/douyin-pro/scripts/audit_pack_contrast.py news-coral
npm test
```

**期望**：5/5 全过 = Tier 3 工程层完成。

**沙箱不能跑**：真 `npx hyperframes render` 验证 host.html 渲染 Vue mount —— 用户在本地复测。

## §8 Step 7 · 写 verification-tier3

文件：`verifications/2026-10-13-hyperframes-vue-tier3-verification.md`

内容：
- §1 范围 / §2 改动清单 / §3 静态断言实际跑结果 / §4 真渲染断言（本会话跳过，交给用户）/ §5 不可验证盲点（hyperframes 引擎黑盒 + 跨域 + 包体积）/ §7 完成判据 + §8 commit message

## §9 风险与回滚

| 失败点 | 表现 | 回滚 |
|---|---|---|
| §3 emit_host 占位符未在所有 host.html 加 | `EmitterError: host.html 缺少占位符` | revert host.html 改动（git checkout） |
| §3.4 漏改某个 pack 的 host.html | 同上 | 同上 |
| §3.5 拷 Vue bundle 失败（dist/vue 不存在） | `FileNotFoundError` | 提示先跑 `npm run build:templates` |
| §3 VUE_MOUNT_TPL 的 `<div id="vue-target-xxx">` 在 host.html 容器内冲突 | hyperframes 引擎报错 | 改 mount target id 加随机后缀 |
| 静态全过但真渲染失败 | mp4 缺这一镜 | gtm：spec §4.1 → 退到 iframe 嵌入 |

## §10 完成判据

- [ ] spec（本文档的 spec）+ 本 plan 文档两份独立成文
- [ ] 用户确认「开始实施」
- [ ] 主 Agent 改完（§1-§5 全部）
- [ ] §7 5 个门禁全绿
- [ ] §8 verification-tier3 落盘
- [ ] 可以 commit（push 由用户决定）

**实施开始后不暂停**（plan 后已经暂停过，§1-§5 一气呵成）——除非遇到 §9 的失败点。