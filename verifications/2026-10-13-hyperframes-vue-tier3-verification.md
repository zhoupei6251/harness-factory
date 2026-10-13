# 2026-10-13 · hyperframes-vue POC · Tier 3 verification（host.html 嵌入）

> 本文是 Tier 1 POC + Tier 3 嵌入 host.html 整套验证证据闭环。
> Tier 1: `docs/plans/2026-10-13-hyperframes-vue-poc-design.md` + `verifications/2026-10-13-hyperframes-vue-poc-verification-lite.md`
> Tier 3: `docs/plans/2026-10-13-hyperframes-vue-tier3-host-integration-spec.md` + `-plan.md` + **本文**

## §1 改动总览（Tier 1 + Tier 3 合并）

| 文件 | 类型 | 角色 |
|---|---|---|
| `vite.config.ts` | 新 | 多入口 build + 产物扁平化 + `vue/` 子目录 |
| `tsconfig.web.json` | 新 | Vue 子项目 TS 配置 |
| `src/web/lib/data.contract.ts` | 新 | HookVariables 类型契约 |
| `src/web/lib/gsap-runtime.ts` | 新 | gsap npm 引入 |
| `src/web/lib/hyperframes-bridge.ts` | 改 | DOM attribute 读法（修正原 window.__hyperframes 误猜） |
| `src/web/lib/tokens/coral.ts` | 新 | 色板常量 + WCAG 工具 |
| `src/web/entries/news-coral-hook/main.html` | 改 | Tier 3: 去掉 `<div id="app">`，caller 传 target |
| `src/web/entries/news-coral-hook/main.ts` | 改 | 导出 `mount(target, compId)` 函数 |
| `src/web/entries/news-coral-hook/NewsCoralHook.vue` | 新 | 单文件组件 |
| `tests/web/vue-build.test.ts` | 新 | 12 条端到端断言（含 Tier 3 vue/ 子目录断言） |
| `skills/douyin-pro/scripts/path_b_build.py` | 改 | VUE_COMPOSITIONS + VUE_MOUNT_TPL + VUE_HOST_INJECTION + emit_mount 分支 + emit_host Vue 注入 + 拷 Vue bundle |
| `skills/douyin-pro/scripts/path_b_selftest.py` | 改 | 加 4 条 Tier 3 断言 |
| `skills/douyin-pro/templates/hyperframes_path_b/*/host.html` | 改 ×31 | 加 `{{VUE_INJECTION}}` 占位符 |
| `package.json` | 改 | +4 scripts |

**总计**：1 改 + 10 新（Tier 1）+ 5 改 + 31 批量改 host.html（Tier 3）= 47 文件。

## §2 Tier 3 关键改动

### §2.1 path_b_build.py 新增（spec §3 实现）

```python
VUE_COMPOSITIONS: dict[str, str] = {
    "nc-night-hook": "news-coral-hook",
}

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

VUE_HOST_INJECTION = """\
    <script src="vue/vue.runtime.global.prod.js"></script>
    <script type="module">
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

### §2.2 emit_mount 分支

```python
if layout["composition_id"] in VUE_COMPOSITIONS:
    return VUE_MOUNT_TPL.format(bundle_name=VUE_COMPOSITIONS[layout["composition_id"]], **common)
return MOUNT_TPL.format(file_name=layout["file_name"], **common)
```

### §2.3 emit_host Vue 注入

```python
# 占位符 {{VUE_INJECTION}} 仅 path_b 包有（31 个），path_c 的编译产物不含——保持兼容
has_vue_placeholder = "{{VUE_INJECTION}}" in host
has_vue = any('data-vue-mount="1"' in m for m in mounts)
vue_injection = VUE_HOST_INJECTION if has_vue else ""
filled = host.replace(...) ... 
if has_vue_placeholder:
    filled = filled.replace("{{VUE_INJECTION}}", vue_injection)
```

### §2.4 拷 Vue bundle + runtime 到 work_dir

```python
if has_vue_mount:
    vue_dst = os.path.join(work_dir, "vue")
    os.makedirs(vue_dst, exist_ok=True)
    repo_root = Path(__file__).resolve().parent.parent.parent
    vue_src = repo_root / "dist" / "vue"
    # 递归拷（含 assets/ 子目录）
    _copy_tree(vue_src, vue_dst)
    # Vue runtime 从 node_modules 拷
    shutil.copyfile(repo_root / "node_modules/vue/dist/vue.runtime.global.prod.js",
                    os.path.join(vue_dst, "vue.runtime.global.prod.js"))
```

## §3 验证断言逐条核

### §3.1 vue-build.test.ts 12/12 ✅

```
ok    dist/news-coral-hook.html 存在
ok    dist/news-coral-hook.js 存在（entry chunk）
ok    产物不含硬编码 #app mount 点（Tier 3: caller 传 target）
ok    产物不含 CDN 引用（hyperframes 在无网环境也跑）
ok    产物引用 entry chunk (news-coral-hook.js)
ok    产物含 data-composition-id="nc-night-hook"
ok    GSAP 关键 API (timeline / fromTo) 出现在 dist 任一 JS
ok    hook 关键元素 ID 出现在 entry bundle
ok    @font-face HF CJK 声明被保留（在 JS 或 CSS 任一处）
ok    8 个数据占位字段 ... 出现
ok    Vue bundle 落在 dist/vue/news-coral-hook.js（host.html 相对路径 ./vue/）
ok    entry bundle 不含硬编码 /dist/vue/ 绝对路径（host.html 用相对 ./vue/）

[vue-build] all ok
```

### §3.2 path_b_selftest.py 185/185 ✅（原 181 + Tier 3 加 4）

新增：
- `t_vue_compose_hook_uses_vue_mount_tpl` —— VUE_COMPOSITIONS 里的 hook 走 VUE_MOUNT_TPL（不含 data-composition-src，含 data-vue-mount + vue-target 子元素）
- `t_non_vue_layouts_keep_composition_src_html` —— stat 等 HTML 版 layout 仍走 MOUNT_TPL（兼容性不退化）
- `t_emit_host_injects_vue_loader_when_any_vue_mount` —— emit_host 检测 mounts 有 Vue 版时注入 loader script（vue.runtime.global.prod.js + import('./vue/...')）
- `t_emit_host_skips_vue_loader_when_no_vue_mount` —— path_c/news-editorial-warm 的 host.html 不含 `{{VUE_INJECTION}}` 占位符时，emit_host 不引入 Vue（P1 编译包兼容性不退化）

### §3.3 audit_pack_contrast.py news-coral 0 warnings ✅

### §3.4 npm test 全套 ✅

```
> validate / typecheck (TS 7 root) / check-bootstrap
> bootstrap.test.ts / install-template.test.ts / downstream-render.test.ts
All bootstrap tests passed.
All downstream tests passed.
```

## §4 不可验证的盲点（spec §4 沿用）

| # | 盲点 | 影响 | 后续动作 |
|---|---|---|---|
| 1 | **hyperframes 引擎对 Vue mount target 的行为** | 引擎可能只认 `data-composition-src`，对 `data-vue-mount` mount 元素**静默跳过**，整镜黑屏但发射器不报错 | **必须在真渲染环境复测** —— `npx hyperframes render` |
| 2 | Vue bundle 跨域 / 相对路径 | §2.4 已递归拷到 work_dir/vue/，loader script 用 `./vue/<bundle>.js` 相对引用；运行时跨域不会触发（同源） | 真渲染时验 |
| 3 | Vue runtime + GSAP 多 bundle 重复打包 | 每个 Vue composition 各自 import Vue + GSAP → 累积体积 | 后续 `manualChunks` 拆 |
| 4 | Vue reactivity 与 GSAP seek 冲突 | DOM 由 Vue 渲染、GSAP 通过选择器找元素 ID —— mount 后 ID 已存在，但 Vue 后续 re-render 可能破坏引用 | 真渲染时验 |

## §5 已知风险（plan §9 沿用）

| 风险 | 表现 | 缓解 |
|---|---|---|
| §2.3 path_c/news-editorial-warm 编译产物与仓库不一致 | `t_hf_compile_is_deterministic...` FAIL | 已撤回 path_c 的占位符改动 |
| hyperframes 引擎不支持 Vue mount target | 真渲染时 Vue 镜黑屏 | 退到 iframe 嵌入（重新设计 spec §3） |
| Vue runtime 拷失败 | loader script 引用 404 | log 输出明确路径，调试可见 |

## §6 完成判据

| # | 判据 | 状态 |
|---|---|---|
| 1 | spec（Tier 3）+ plan 独立成文 | ✅ `docs/plans/2026-10-13-hyperframes-vue-tier3-host-integration-{spec,plan}.md` |
| 2 | 用户确认「开始实施」 | ✅ 用户答「开始实施」 |
| 3 | 主 Agent 改完（§1-§7 全部） | ✅ Step 1-7 全完成 |
| 4 | §3 静态断言全绿 | ✅ vue-build 12/12 + selftest 185/185 + audit 0 warnings + npm test 全套 |
| 5 | 真跑 `npx hyperframes render` 渲染验证 | ❌ **沙箱无 headless browser**，必须用户本地复测 |
| 6 | verification-tier3 落盘 | ✅ **本文件** |
| 7 | 可以 commit（push 由用户决定） | ⏳ 由用户 git add + git commit |

## §7 推荐 commit message（用户手工 commit 用）

```
feat(news-curate): news-coral hook 走 Vue 3 + Vite 嵌入 host.html（Tier 3）

把 news-coral/compositions/hook.html 的 Vue 版（dist/vue/news-coral-hook.js）
嵌入 host.html：path_b_build 检测 VUE_COMPOSITIONS 表里的 composition_id 走
VUE_MOUNT_TPL（不含 data-composition-src），emit_host 注入 Vue runtime +
loader script 到 </head> 前，loader 调 mod.mount(target, compId) 把 Vue
应用挂到 mount target。

收益：
- Vue 应用 mount 后从 host.html 的 [data-composition-id] 读 data-variable-values
  —— 与 hyperframes 引擎读 DOM attribute 是同一份真相源
- bridge 协议零自定义 window 协议
- path_b 拷 Vue bundle + Vue runtime 到 work_dir/vue/，loader 用相对路径

协议扩展：
- host.html 加可选占位符 {{VUE_INJECTION}}（仅 path_b 31 个包加，path_c 不加）
- emit_host 检测占位符存在性后选择性替换（保持 path_c 编译产物兼容）

Tier 1 已有（本次 commit 合并）：
- Vite 多入口 build + 产物扁平化（dist/news-coral-hook.html）
- Vue 应用 mount target 改 caller 传入（不写死 #app）
- bridge 改读 DOM attribute（不再读 window.__hyperframes）

验证：
- vue-build.test.ts 12/12（含 Tier 3 vue/ 子目录断言）
- path_b_selftest.py 185/185（含 4 条 Tier 3 断言）
- audit_pack_contrast.py news-coral 0 warnings
- npm test 全套绿

盲点：hyperframes 引擎对 Vue mount target 的行为是外部 npm 包黑盒——真渲染
验证必须在本地用 npx hyperframes render 跑一次。如果引擎不识别
data-vue-mount 元素，整镜黑屏但发射器不报错（plan §9 退路：iframe 嵌入）。

见 docs/plans/2026-10-13-hyperframes-vue-{poc-design,tier3-host-integration-{spec,plan}}.md
+ verifications/2026-10-13-hyperframes-vue-{poc-verification-lite,tier3-verification}.md
```

## §8 工具降级声明

`codebase-memory-mcp` 在 POC + Tier 3 范围（单 composition + 集成 host.html）下收益低于手工 Read，未调用。证据全部通过 Read + Grep + Bash 直接取证（host.html 模板、path_b_build.py 发射器、hyperframes 协议、hf_compile 编译产物）。升 Tier 4（推广 56 份 composition）时改用 `search_graph` 取全局 caller/callee 图。

## §9 用户复测清单（本地真渲染验证）

```bash
# 1. 跑 Vite build 产出 dist/vue/
npm run build:templates

# 2. 准备一条稿件（参考 skills/douyin-pro/templates/hyperframes_path_b/news-coral/README.md）
#    让其中第一镜是 hook（走 VUE_COMPOSITIONS）

# 3. 跑 path_b_build 生成 work_dir + 拷 Vue bundle
python skills/douyin-pro/scripts/path_b_build.py --input <稿> --output <out.mp4> ...

# 4. 验证 work_dir/vue/ 存在
ls <work_dir>/vue/
# 期望：vue.runtime.global.prod.js + news-coral-hook.js + assets/*.css

# 5. 渲染
npx -y hyperframes render -c <work_dir>/index.html -o <out>.mp4

# 6. 视觉验证：第 1 镜（hook）是否渲染出 Vue 组件内容
#    - 不黑屏
#    - GSAP timeline 4 条入场补间 + 呼吸位移正常
#    - data-variable-values 的 8 字段正确注入（kicker / headTop / ...）

# 7. 如果黑屏：检查 hyperframes 引擎日志（[hyperframes-bridge] no element with... 等）
#    - 引擎可能不识别 [data-vue-mount] —— 回退到 iframe 嵌入
```