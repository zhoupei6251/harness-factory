# 2026-10-13 · hyperframes-vue POC · Tier 3 host.html 嵌入 spec

> 本文档是 Tier 1 POC（`docs/plans/2026-10-13-hyperframes-vue-poc-design.md` + verification-lite）
> 的升档产物。要在 host.html 嵌入 Vue 应用、与原 HTML 版式共存。

## §1 目标

让 `news-coral/hook` 这一镜在 host.html 里**走 Vue 版**——path_b_build 生成 host.html 时：
1. 这一镜的 mount 元素是 `<div data-vue-mount="nc-night-hook" data-variable-values="...">`
2. host.html 头部注入 Vue runtime + 配套 loader script
3. loader script 找到所有 `data-vue-mount` 元素，按 `data-composition-id` 加载对应 Vue bundle，createApp + mount

非 Vue composition 仍走 `MOUNT_TPL`（`<div data-composition-src="compositions/xxx.html">`），与 Vue 共存。

## §2 改动清单

| 文件 | 改动 |
|---|---|
| `path_b_build.py` | 加 `VUE_COMPOSITIONS = {"nc-night-hook": "news-coral-hook"}` 常量；`emit_mount` 检测 composition_id 在表里时换 VUE_MOUNT_TPL；`emit_host` 在 `</head>` 前注入 Vue runtime `<script>` + loader `<script>` |
| `host.html`（每个 pack 的 host 模板） | 在 `</head>` 前加 `{{VUE_INJECTION}}` 占位符。原计划「不动模板、由 emit_host 定位 `</head>` 注入」，实现改为显式占位符：注入点不依赖模板结构，且不含占位符的旧模板自动跳过注入（`path_b_build.py:2336`）。31/31 份 pack 模板已加 |
| `vite.config.ts` | `rollupOptions.output` 加 `entryFileNames: "vue/[name].js"`，让 Vue bundle 路径固定到 `dist/vue/news-coral-hook.js` |
| `tests/web/vue-build.test.ts` | 加 1 条断言：产物入口 chunk 在 `dist/vue/` 子目录（不是 dist 根） |
| `path_b_selftest.py` | 加 N 条断言：VUE_COMPOSITIONS 表里的 composition_id 生成的 mount 元素不含 `data-composition-src`、含 `data-vue-mount` |

## §3 关键协议（设计）

### §3.1 Vite 产物路径（2026-10-13 真渲染后按实测更正）

```
dist/vue/news-coral-hook.js            # entry chunk（被 host.html 动态 import；必须真的导出 mount）
dist/vue/news-coral-hook-preview.js    # main.html 预览入口的 wrapper，产线不引用
dist/vue/assets/news-coral-hook-<hash>.css   # .vue 的 <style>，名字含内容哈希
dist/news-coral-hook.html              # 独立预览入口（产线不引用）
```

两处原稿没料到的约束，都是真渲染逼出来的（证据见 verification §10.a）：

1. **rollup input 必须是 `main.ts` 而不是只有 `main.html`**。HTML 入口下的 `.ts` 只是它的依赖，rollup 不保留其导出签名 ⇒ 产物零 `export{}` ⇒ loader `mod.mount is not a function`。`preserveEntrySignatures` 单独设也无效。
2. **CSS 名不可预测**（内容哈希），所以 `<link>` 不能写死在模板里：由 `path_b_build.stage_vue_assets()` 在发射时扫 `work_dir/vue/assets/` 按 `<bundle>*.css` 过滤，交给 `emit_host` 填进 `{{VUE_CSS_LINKS}}`。顺序上 `stage_vue_assets` 必须在 `emit_host` **之前**调用。

**新增版式不碰 `vite.config.ts`**（2026-10-13 改为目录驱动）。配置扫 `src/web/entries/*/main.ts`，每个命中的子目录自动生成一对 rollup input（`<name>` → `main.ts`，有 `main.html` 时再加 `<name>-preview`）；HTML 扁平化是**一个**插件吃全部入口名，不是每入口一个。所以迁一个版式 = 建目录 + 在 `VUE_COMPOSITIONS` 登记一行：

```
src/web/entries/<bundle>/main.ts        # 必须 export function mount(target, compositionId)
src/web/entries/<bundle>/<Name>.vue     # 版式本体
src/web/entries/<bundle>/main.html      # 可选，独立预览
```

3. **每入口一个 flatten 插件会在第二个 HTML 入口上静默丢文件**（这条是多入口重构逼出来的，不在上面两条的真渲染证据里）。插件的 `closeBundle` 按注册顺序跑，而每个都要搬完 HTML 后 `rmSync(dist/src)`——第一个插件删掉整棵子树时，后面插件的源文件已经没了，预览页不产出且不报错。实测（双入口 probe 构建，`emptyOutDir` 关掉、先清 dist）：分插件版只出 `dist/news-coral-hook.html`，`dist/probe-b.html` 缺失；单插件版两个都出。

`tests/web/vue-build.test.ts` 的入口清单读同一个目录，所以配置退回写死入口时，新目录会以「`dist/vue/<name>.js` 缺失」红灯而不是静默漏构建；预览页断言按 `main.html` 存在与否逐个查 `dist/<name>.html`，上面第 3 条就是它抓到的。该测试**先 `rmSync(dist)` 再 build**——`emptyOutDir: false` 下陈旧产物会让断言假绿（实测：改坏插件后旧的 `dist/probe-b.html` 还在，检查照样 ok）。

### §3.2 VUE_MOUNT_TPL（path_b_build.py 新增）

`data-vue-mount` 只做**存在性标记**（值恒为 `1`），composition_id 由 loader 从 `dataset.compositionId` 取——原稿写的 `data-vue-mount="{composition_id}"` 会让同一个 id 出现在两个属性里，改一处忘一处就分家。

```python
VUE_MOUNT_TPL = (
    '      <div id="{mount_id}" class="clip"'
    ' data-composition-id="{composition_id}"'
    ' data-vue-mount="1"'
    ' data-vue-bundle="{bundle_name}"'
    ' data-variable-values="{values}"'
    ' data-start="{start}" data-duration="{dur}" data-track-index="1"'
    ' data-width="{w}" data-height="{h}">'
    '        <div id="vue-target-{composition_id}"></div>'  # Vue mount target
    '      </div>'
)
```

### §3.3 host.html 注入块（path_b_build.py emit_host 加）

变量**不由 loader 挂全局**，而是组件自己通过 `hyperframes-bridge.readVariables` 从最近的 `[data-composition-id]` 读——原稿的 `window.__hyperframesVars[compId] = vars` 是全局可变状态，改成自读后每个 composition 的数据只经由它自己的 DOM 节点。runtime 与 bundle 路径都带 `vue/` 前缀，相对于 host.html。

```html
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
```

### §3.4 Vue 应用 mount 接口（hyperframes-bridge.ts 改）

Vue 应用导出 `mount(target, compositionId)` 而不是默认 `createApp().mount("#app")`：

```typescript
// src/web/entries/news-coral-hook/main.ts
export function mount(target: HTMLElement, compositionId: string): void {
  // 把 composition_id 传给 bridge
  // bridge 找最近的 [data-composition-id] 读 data-variable-values
  // 不再依赖 window.__hyperframes
  createApp(NewsCoralHook, { compositionId }).mount(target);
}
```

**降耦合**：每个 Vue bundle 是独立 ES module，host.html 用 `import()` 动态加载。

## §4 关键未知（**必须在 spec 阶段解决**）

### §4.1 hyperframes 引擎对 Vue mount target 的行为

**这是最大的未知**。hyperframes 是外部 npm 包，源码不在仓库里。从仓库现有事实推断：

| 引擎行为（推测） | 来源 |
|---|---|
| 引擎按 `data-composition-src` 异步加载 HTML 文件 | path_b_selftest.py line 1309-1316 验证：`audio_file_without_element` 等 check |
| 引擎按 `data-composition-id` 识别每个 clip 驱动 GSAP timeline | path_b_build.py line 461 + host.html line 50 |
| 引擎对**无** `data-composition-src` 的 mount 元素**跳过不渲染** | 未知，需验证 |

**最坏情况**：hyperframes 引擎只认 `data-composition-src`，对 `data-vue-mount` mount 元素**静默跳过**，整镜黑屏但发射器不报错。

**缓解方案**：
1. 真跑一次 `npx hyperframes render` 看产物（需 headless browser）
2. 若引擎不支持：退回 iframe 嵌入（`MOUNT_TPL` 改 iframe，跨域安全 + timeline 隔离问题独立解决）
3. 若引擎支持：继续推进

### §4.2 Vue bundle 跨域加载

`host.html` 在 work_dir 里。Vue bundle 在 `dist/vue/`。Vite build 产物用绝对路径 `/vue/news-coral-hook.js` 还是相对路径 `./vue/news-coral-hook.js`？需 path_b_build 把 Vue bundle 拷到 work_dir（与原 `compositions/*.html` 一起）才能相对路径引用。

**缓解方案**：`path_b_build` 拷 `dist/vue/*.js` 到 `<work_dir>/vue/`，host.html 引用相对路径 `./vue/xxx.js`。

### §4.3 Vue runtime 与 GSAP timeline 跨 bundle 隔离

每个 Vue bundle 各自 import Vue + GSAP。N 个 Vue composition 会让 Vue runtime / GSAP 重复 N 次。

**缓解方案**：Vue runtime 走 `<script src="vue.runtime.global.prod.js">`（外置），各 bundle 只 import 应用代码。GSAP 类似。但 Vite build 不会自动拆——需要 `manualChunks: { vue: ["vue"], gsap: ["gsap"] }` + build 后手动搬出 runtime chunk。

## §5 验证断言（spec 后才有具体验证）

### §5.1 静态断言（必须过）

- [ ] `path_b_build` 生成 host.html 含 Vue runtime `<script>`
- [ ] host.html 含 loader `<script>`，遍历 `[data-vue-mount]`
- [ ] Vue composition 的 mount 元素不含 `data-composition-src`、含 `data-vue-mount` 与 `data-vue-bundle`
- [ ] HTML composition 的 mount 元素**仍**含 `data-composition-src`（不回归）
- [ ] `dist/vue/news-coral-hook.js` 存在
- [ ] `path_b_selftest.py` 全绿（含新增 VUE_COMPOSITIONS 相关断言）
- [ ] `audit_pack_contrast.py news-coral` 全绿
- [ ] `vue-build.test.ts` 全绿（含新断言）

### §5.2 真渲染断言（必须有 headless browser）

- [ ] `npx hyperframes render` 真渲染产物（mp4 或 png 帧序列）含 Vue 镜内容
- [ ] 渲染产物 A/B 对比：原 hook.html vs Vue 版 hook，**至少 1 帧像素差 < 1%**
- [ ] GSAP timeline 正常播放（4 条入场补间 + 呼吸位移）

### §5.3 不可验证的盲点

- §4.1 引擎行为：必须真跑才能确认
- §4.2 跨域：实际部署环境才暴露
- §4.3 包大小：5+ 个 Vue composition 时 cumulative size

## §6 升降级判据

### §6.1 升 Tier 2（已是）

本次改动：**> 200 行**（host.html 改模板 + path_b 改 MOUNT + Vite 改 build config + 新增断言）+ **跨模块**（Vue ↔ Python 发射器）+ **改 schema**（mount 元素属性）。**已升 Tier 2**。

### §6.2 暂停时机

**写完本文档（spec）暂停**。等用户确认「开始写 plan」。

### §6.3 完成判据（升 Tier 3 真接 host.html）

- [ ] spec（本文档）+ plan 独立文档两份
- [ ] 用户确认「开始实施」
- [ ] 主 Agent 改完 + §5.1 静态断言逐条核
- [ ] 真跑 §5.2（需 headless browser，**沙箱内不能跑**——本会话内只能跑静态断言）
- [ ] 写 `verifications/2026-10-13-hyperframes-vue-tier3-verification.md`
- [ ] 可以 commit

## §7 已知风险

| 风险 | 概率 | 缓解 |
|---|---|---|
| hyperframes 引擎不支持 Vue mount target | 中 | §4.1 缓解：iframe 退路 |
| Vue runtime 重复打包导致 mp4 前置 HTML 过大 | 低 | §4.3 缓解：manualChunks |
| Vue reactivity 与 GSAP seek 冲突 | 低 | 真渲染验 |
| path_b 拷 Vue bundle 到 work_dir 与 compositions 混放 | 低 | 命名 `vue/` 子目录隔离 |

## §8 不做

- 不引入 Vite preview server 部署到 CI（产物仍走 path_b 流程）
- 不动 P1 编译路径（hf_primitives / hf_compile / hf_style_spec）
- 不升级 vue-tsc（等 vue-tsc 适配 TS 7）
- 不推广到其它 composition（先把 hook 一镜打通）

---

**确认开始写 plan？** plan 文档需详细到「哪一行改什么、为什么改」，不重复本文档已写的设计选择。