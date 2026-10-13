# 2026-10-13 · hyperframes-vue-poc · verification-lite

> Tier 1 完成判据（CLAUDE.harness.md §2）：合并文档已写、用户确认、主 Agent 改完、内联断言全绿、本文件落盘。
> 本文件 = 证据闭环。push 由用户决定。

## §1 范围与不变量

| 项 | 值 |
|---|---|
| 仓库 | `aigc_platfrom_back/harness-factory`（已存在 memory index `MEMORY.md`） |
| 分支 | main（harness-factory 自身不分子 policy —— 见 `harness-factory/CLAUDE.md` Workflow 段） |
| POC 范围 | 1 个 composition：`skills/douyin-pro/templates/hyperframes_path_b/news-coral/compositions/hook.html` → `src/web/entries/news-coral-hook/NewsCoralHook.vue` |
| 不动 | Python 渲染管线 / host.html / frame.md / path_b_selftest.py / hf_primitives P1 路径 / tsconfig.json |

## §2 改动清单（实际落地）

| 文件 | 类型 | 行数（增减） | 角色 |
|---|---|---|---|
| `package.json` | 改 | +4 scripts | build:templates / build:templates:dev / preview:templates / typecheck:templates |
| `vite.config.ts` | 新 | 65 | 多入口 build + 产物扁平化 plugin |
| `tsconfig.web.json` | 新 | 15 | Vue 子项目 TS 配置（extends 根） |
| `src/web/lib/data.contract.ts` | 新 | 27 | HookVariables 类型契约（编译期拒拼错） |
| `src/web/lib/gsap-runtime.ts` | 新 | 6 | gsap npm 引入（替代 CDN） |
| `src/web/lib/hyperframes-bridge.ts` | 新 | 24 | `window.__hyperframes.getVariables()` 协议适配 |
| `src/web/lib/tokens/coral.ts` | 新 | 67 | 色板常量 + WCAG 复算工具 |
| `src/web/entries/news-coral-hook/main.html` | 新 | 10 | Vite 入口 HTML |
| `src/web/entries/news-coral-hook/main.ts` | 新 | 8 | createApp mount |
| `src/web/entries/news-coral-hook/NewsCoralHook.vue` | 新 | 219 | 单文件组件（template + script setup + style unscoped） |
| `tests/web/vue-build.test.ts` | 新 | 142 | 端到端 build + 10 条静态断言 |

**改动总计**：1 改 + 10 新 = 11 文件，**净增 ~700 行**。POC 边界内。

devDependencies 增量（`package.json`）：

```
"@vitejs/plugin-vue": "^5.2.4",
"gsap": "^3.15.0",
"vite": "^6.4.4",
"vue": "^3.5.43",
"vue-tsc": "^2.2.12"
```

## §3 验证断言（设计文档 §6.3 逐条核）

| # | 断言 | 结果 | 证据 |
|---|---|---|---|
| 1 | `npm run build:templates` 产物存在 `dist/news-coral-hook.html` | ✅ | build 输出："✓ built in 571ms"；`find dist -type f` → 3 个产物 |
| 2 | 产物含 GSAP 打包后代码（不引 CDN） | ✅ | `dist/news-coral-hook.js` 137 kB（含 Vue runtime + GSAP），HTML 引用 `<script src="/news-coral-hook.js">`、无 `cdn.jsdelivr.net` / `unpkg.com` |
| 3 | 产物含 Vue mount 点 `<div id="app">` | ✅ | `dist/news-coral-hook.html` line 11 |
| 4 | 产物保留 `__hyperframes.getVariables()` 协议（host.html 仍写入） | ⚠️ **不在 POC 产物里** | 本次 build 产物是 composition 自身，**bridge 协议由 host.html 在挂载时写入**（POC 范围外，未实现 host.html 端注入）—— 见盲点 §5 |
| 5 | 跑 path_b_build 两次（一次原 hook.html、一次 vue-hook.html）对比 final.mp4 字节哈希 | ⚠️ **未跑** | 沙箱无 headless browser；见盲点 §5 |
| 6 | `npm run typecheck:templates` = 0 错误 | ❌ **vue-tsc 不兼容 TS 7** | vue-tsc 2.x 内部 `import typescript/lib/tsc` —— TS 7 exports 字段已变更。**降级**：用 `vite build` 跑 esbuild 编译代替；产出文件已含全部类型推导产物。验证见 §3.a |
| 7 | `python path_b_selftest.py` 全绿（Python 端不被影响） | ✅ | `[selftest] 全绿 181/181` |
| 8 | `python audit_pack_contrast.py news-coral` 全绿 | ✅ | `对比度审计通过：1 个 pack 的 frame.md 色板与文档一致（0 条警告）` |
| 9 | CJK 字体闸门（`t_cjk_gate_green_on_shipped_packs`）绿 | ✅ | path_b_selftest.py 内 7 条相关测试全过 |
| 10 | `vue-build.test.ts` 10 条静态断言全绿 | ✅ | 见 §3.b |

### §3.a 验证 #6 降级说明

`vue-tsc@^2.2.12` 在 `typescript@^7.0.2` 下报 `ERR_PACKAGE_PATH_NOT_EXPORTED`：
```
Error [ERR_PACKAGE_PATH_NOT_EXPORTED]: Package subpath './lib/tsc' is not defined by "exports"
```
**降级路径**：用 `vite build` 自带的 esbuild 做 `.vue` + `.ts` 编译校验。esbuild 编译过 + 产物结构断言过 = 等价类型校验（不验证 `+Strict` 模式下的 null check，但本仓库 .vue 文件无 strict-null 风险）。**等 vue-tsc 升级到支持 TS 7 再启用 `npm run typecheck:templates`**。已在 verification §6 记录后续动作。

> **2026-10-13 更正（上面这段的判断是错的，保留原文以留痕）**
>
> 1. esbuild **不做任何类型检查**——它只做语法级类型擦除（`--isolatedModules` 语义），`const x: number = "s"` 一样编译通过。所以「esbuild 编译过 = 等价类型校验」不成立，当时的 §3.b 断言覆盖的是产物结构，不是类型。
> 2. 实际缺口比记录的大：`tsconfig.web.json` 的 `"@web/*": ["src/web/*"]` 缺 `./` 前缀 → `tsc` 直接报 TS5090；extends 来的 `lib` 只有 `ES2023` 无 `DOM` → `document` / `HTMLElement` 报 TS2584/TS2304。这两个错误当时**没被发现**，因为 vue-tsc 在读取任何 tsconfig 之前就崩在 `require.resolve('typescript/lib/tsc')` 上——崩溃把配置错误遮蔽了。
> 3. 已修：`@web/*` 死别名删除（全仓 0 引用）、`lib` 加 `DOM`/`DOM.Iterable`、新增 `src/web/vue-shims.d.ts`；`typecheck:templates` 更名为 **`typecheck:web`**，改用 `node node_modules/typescript/lib/tsc.js -p tsconfig.web.json`，并已进 `npm test` 链。红测验过：注入 `const __probe: number = "not a number"` → exit 1 / TS2322。
> 4. **剩余真实缺口**：`.vue` 单文件组件的 `<script setup>` 内部仍零类型检查（`tsc` 不能解析 `.vue`，vue-tsc 被 TS 7 挡）。`vue-tsc` 依赖仍装着，恢复路径是等其支持 TS 7 后加回一个会崩的入口——不要再放一个永远红的 script 而不标注。

### §3.b vue-build.test.ts 10 条断言（实际跑）

```
[vue-build] running: npx vite build
  ok    dist/news-coral-hook.html 存在
  ok    dist/news-coral-hook.js 存在（entry chunk）
  ok    产物含 <div id="app"> Vue 挂载点
  ok    产物不含 CDN 引用（hyperframes 在无网环境也跑）
  ok    产物引用 entry chunk (news-coral-hook.js)
  ok    产物含 data-composition-id="nc-night-hook"
  ok    GSAP 关键 API (timeline / fromTo) 出现在 dist 任一 JS
  ok    hook 关键元素 ID 出现在 entry bundle
  ok    @font-face HF CJK 声明被保留（在 JS 或 CSS 任一处）
  ok    8 个数据占位字段 (kicker/headTop/headBottomLead/headAccent/support/imagePath/imageCredit/slotSeconds) 出现

[vue-build] all ok
```

## §4 仓库存量门禁（**不破坏**）

### §4.a `npm test` 全套

跑了 `validate` + `typecheck` (TS 7 root) + `check-bootstrap` + 3 个 tsx 测试。

```
> npm test
... (bootstrap.test.ts / install-template.test.ts / downstream-render.test.ts 全过)

All install-template tests passed.
All downstream tests passed.
```

**关键观察**：仓库存量 `typecheck`（TS 7 root）绿 —— `tsconfig.web.json` 用 `extends` 不污染根 include 范围。

### §4.b Python 端

`path_b_selftest.py`：**181/181 全绿**。
`audit_pack_contrast.py news-coral`：1 pack / 0 warnings。

**Vue 重写触及 `images/news/courses/compositions/hook.html` 一处都不修改**（§3 已确认未变更），仅新增 `src/web/` 与 `tests/web/`。Python 渲染管线消费的还是原 `hook.html`，新增的 Vue 产物是**并行可选入口**（后续通过 path_b_build 的 entry 选择开关接入）。

## §5 不可验证的盲点（沿用设计文档 §6.4）

| # | 盲点 | 影响 | 后续动作 |
|---|---|---|---|
| 1 | **像素级一致** | POC 验证级别 = 字节 + 结构一致；视觉差 ≤1% 像素只能等真跑 `npx hyperframes render` | 用户跑一次真渲染 + 截图 A/B 对比 |
| 2 | **GSAP seek 回退** | Vue reactivity 是否影响 GSAP 引用同一元素——只通过真渲染验证 | 真跑一次 seek 回退测 |
| 3 | **scoped CSS 选择器冲突** | `.has-photo .h-hd` 这类修饰选择器在 Vue unscoped 下未带 `[data-v-hash]`，与原 hook.html 全局语义一致；但如未来误加 `scoped` 关键字可能破坏 | ✅ 真渲染已验（§10）—— 但前提是 `<link>` 真的发出去，见 §10.a #2 |
| 4 | **GSAP chunk 大小** | 137 kB → 53.76 kB gzip（entry chunk 含 Vue + GSAP + 业务代码）—— 比原 CDN 引用 27 kB gzip 大 ~2x | 后续用 `manualChunks` 拆 gsap 独立 chunk |
| 5 | **bridge 协议实战** | 本次 POC 产物没接 host.html 的 `__hyperframes` 注入；只有在 host.html 挂载时（path_b_build 写入）才生效。本次 build 产物独立测试时 bridge 缺失是预期 | ✅ 已闭环（§10）：host.html 端到端真渲染跑通，第 1 镜 8 字段注入生效 |

## §6 后续动作（升 Tier 2 / 推广前的硬门）

按设计文档 §10「升级信号」，**本次不升 Tier 2**。但下次升 Tier 2 时必须先解决：

1. **vue-tsc 适配 TS 7**：盯 vue-tsc PR / 升级到 3.x；届时新增 `typecheck:vue`（`vue-tsc --noEmit -p tsconfig.web.json` 并把 `.vue` 加回 include）而**不是**复活 `typecheck:web`——两者检查对象不同，前者管 `.vue` 模板，后者管 `.ts` + `vite.config.ts`。`typecheck:templates` 这个旧名已废弃（它指向一个启动即崩的入口）。
2. **GSAP chunk 拆分**：`build.rollupOptions.output.manualChunks` 把 `gsap` 拆独立 chunk（避免 raw）
4. **bridge 端到端验证**：~~改 host.html / path_b_build 加 Vue 入口选择 + 跑一次真 hyperframes render~~ ✅ 已跑（§10），并顺手补了 §10.a 两个断裂的闸门
5. **像素级 A/B 对比**：原 hook.html vs vue-build 产物各渲染一次，比 final.mp4 字节哈希 / 关键帧像素 diff
6. **推广到 56 份**：先迁另外 6 个 news-coral composition（stat / rail / quote / closer / catalog / story），验证同模板 7 个 composition 一致性后，再推广到 8 个模板

## §7 完成判据勾选

| # | 判据 | 状态 |
|---|---|---|
| 1 | 合并文档已写（含证据段） | ✅ `docs/plans/2026-10-13-hyperframes-vue-poc-design.md` |
| 2 | 用户确认「开始实现」 | ✅ 用户答「开始实现吧」 |
| 3 | 主 Agent 改完 + §6.3 验证断言逐条核 | ✅ 6/10 全过；2 警告（盲点 4/5）；1 降级（vue-tsc）；1 沙箱无 headless browser（盲点 1） |
| 4 | 写 `verifications/*-verification-lite.md`，证据闭环 | ✅ **本文件** |
| 5 | **可以 commit**（不自动 push，push 由用户决定） | ⏳ 由用户 git add + git commit + git push |

## §8 推荐 commit message（用户手工 commit 时用）

```
feat(news-curate): news-coral hook 版式改用 Vue 3 + Vite 单文件组件（开发时）POC

把 skills/douyin-pro/templates/.../news-coral/compositions/hook.html (256 行手写
HTML+CSS+GSAP inline) 迁成 src/web/entries/news-coral-hook/NewsCoralHook.vue。

收益（仅开发时）：
- 单文件组件：template + script setup (TS 7) + style 集中
- 8 个字段类型契约（src/web/lib/data.contract.ts）编译期拒拼错
- GSAP 走 npm 包（无 CDN），hyperframes 在无网环境也跑
- Vite 多入口 build 出 dist/news-coral-hook.{html,js}

不动：Python 渲染管线 / host.html / frame.md / path_b_selftest.py / hf_primitives。
产物路径 dist/news-coral-hook.html 与原 hook.html 同级，可选入口接入。

降级：vue-tsc 2.x 不兼容 TS 7（ERR_PACKAGE_PATH_NOT_EXPORTED），用 esbuild 编译代替。

验证：
- vue-build.test.ts 10/10
- path_b_selftest.py 181/181
- audit_pack_contrast.py news-coral 1/0 warnings
- npm test 全套（validate / typecheck / check-bootstrap / 3 tsx）

见 docs/plans/2026-10-13-hyperframes-vue-poc-design.md + verifications/2026-10-13-hyperframes-vue-poc-verification-lite.md
```

## §9 工具降级声明（沿用设计文档 §7）

`codebase-memory-mcp` 在 POC 范围（单文件 256 行）下收益低于手工 Read，未调用。

## §10 本机真渲染实测（2026-10-13，闭 §5 盲点 3/5 与 §6 第 4 条）

环境：Node 22.20.0（`nvm use` 与渲染**同一条命令**内完成）· Chrome headless-shell 150.0.7871.24 · `--no-browser-gpu` 软件光栅。

发射（零网络，绕开下面记的配音阻塞）：

```bash
python skills/douyin-pro/scripts/path_b_build.py --input .harness-news-runtime/articles/t001-scenes.json \
  --style news-coral --source 新闻拆解 --skip-render --work-dir .harness-news-runtime/tmp/vue-emit-rc2
cd .harness-news-runtime/tmp/vue-emit-rc2 && npx hyperframes render -c index.html -o silent.mp4 -f 30 --quality=draft --no-browser-gpu
```

**结论：Vue mount 这条路真渲染跑得通** —— 第 1 镜（`nc-night-hook`，0–8.378s）出片 3.0 MB / 52.3s / 1570 帧，`render complete` 无 correctness warning；t=5s 抽帧肉眼核对：kicker「湖南常德」/ headTop「拾荒21年」/ headBottomLead「账户里」/ headAccent「42万」（珊瑚红底块）/ support「他自己完全不知道」/ hairline 全部上屏，8 字段注入生效，GSAP timeline 注册成功（未注册即 `sub_timeline_script_failure`，见下）。

### §10.a 第一次真渲染炸出来的两个断裂（都已修 + 加了断言）

| # | 实测症状 | 根因 | 修法 | 闸门 |
|---|---|---|---|---|
| 1 | `Render blocked … sub_timeline_script_failure: … (still unregistered: nc-night-hook) (runtime-error:TypeError: mod.mount is not a function)` | rollup input 只有 `main.html` 时，`main.ts` 是它的**依赖**而非入口 ⇒ 产物里没有任何 `export{}`，`import()` 拿到的命名空间没有 `mount`。把 `preserveEntrySignatures` 设成 `allow-extension` / `strict` 都不救（实测两种都试过） | `vite.config.ts`：`main.ts` 直接作入口（导出得以保留，产物 `export{Vh as mount}`），`main.html` 退为独立预览入口 `news-coral-hook-preview.js` | `vue-build.test.ts` 新增「entry bundle 导出 mount 函数」 |
| 2 | 第 1 镜无样式（`@font-face HF CJK` + `#root` 定位整块丢失）—— 修好 #1 后才会暴露 | `.vue` 的 `<style>` 被 Vite 拆成 `assets/<bundle>-<hash>.css`，哈希名不可预测，而 `VUE_HOST_INJECTION` 只发 `<script>`，**没有任何 `<link>`**；Vue 版又没有 `compositions/<layout>.html` 那一层（hyperframes 不认 Vue mount），这支 link 是样式唯一来路 | `path_b_build.py`：把拷资产那段抽成 `stage_vue_assets(work_dir, pack)`，**在 `emit_host` 之前**调用并交出扫到的 CSS 路径；`emit_host` 按 `<bundle>*.css` 过滤后填 `{{VUE_CSS_LINKS}}`（不过滤会把别的 composition 全局类名盖进来） | `path_b_selftest.py` 新增 2 条：`t_emit_host_links_vue_css_before_runtime` / `t_stage_vue_assets_returns_nothing_for_html_only_pack`；`vue-build.test.ts` 新增「CSS 资产含 @font-face + #root」 |

门禁复跑：`npm test` 8 步全绿（web 断言 12 → 14 条）· `path_b_selftest.py` 187/187。

### §10.b 仍未闭的三项（不是 Vue 的问题）

1. **配音阻塞产线整链**：`edge-tts` 打 `speech.platform.bing.com` 稳定 `403 Invalid response status`（同一条最小 `Communicate(...).save()` 复现，与 `path_b_build.py` 无关）。本次把责任定位到服务端，四条证据：
   · `python -m edge_tts --list-voices` **200**（同主机、同 `TrustedClientToken`，唯一差别是不带 `Sec-MS-GEC`）⇒ 出口 / 代理 / 防火墙正常；
   · 本机 UTC 与微软服务器 `Date` 头差 **0.9s**，且 7.2.8 的 `DRM.handle_client_response_error` 本来就会在 403 后按服务端日期自校偏移重试 ⇒ 不是时钟；
   · 装的是 PyPI 最新 7.2.8（2026-09-28 装入），上游仓库最新提交仍是 7.2.8、无任何 403 / DRM / handshake 修复在飞 ⇒ **升级与装 git main 都无解**（我先前写的「要么升级 edge-tts」这条已作废，实测推翻）；
   · 同一份客户端 2026-10-12 09:51 还能出片（`.harness-news-runtime/tmp/news-1012/workB/*.mp3` 的 mtime 为证）⇒ 变化发生在服务端侧。
   `.harness-news-runtime/tts-cache/` 为空 ⇒ 没有可复用的持久配音缓存，`--check-only` 走真配音分支必挂（`scene_1.mp3` 落成 0 字节即握手前就拒）。本次用 `--skip-render`（估算时长支）绕开，**画面轨结论不受影响**，但 `final.mp4` 整片仍跑不出来。剩下两条腿都要人拍：换网络出口再试一次（零改动，能区分 IP 限流与全局策略），或走 Path A 的备选音色通道（要 Key / 云费）。
2. **§5 盲点 1（像素级 A/B）没做**：本次只验「Vue 版渲染得出来且内容正确」，没跟原 hook.html 版逐帧 diff。
3. **图源署名是存量行为，不是 Vue 引入的**：无图时 `figcaption#hk-credit` 仍显示硬编码「图源：Wikimedia Commons」。基线 `templates/hyperframes_path_b/news-coral/compositions/hook.html` 同样如此（`.hk-photo{display:none}` 只管 figure，credit 是 root 直接子元素且无 display 闸门），Vue 版是**忠实移植**。新闻域里这是一条虚构的图源署名，要不要改是版式口径，不属本次范围。

### §10.c 迁移前置：入口改成目录驱动（2026-10-13 同日）

迁第 2 个版式前，`vite.config.ts` 里入口是写死的（input 一对 + flatten 插件一份），推广就是 N 处手工复制。改为扫 `src/web/entries/*/main.ts`，迁版式 = 建目录 + `VUE_COMPOSITIONS` 登记一行。重构中实测出两条：

| # | 现象 | 根因 | 处理 |
|---|---|---|---|
| 1 | 分插件版只产出 `dist/news-coral-hook.html`，第二个预览页 `dist/probe-b.html` **静默缺失** | 每入口一个 flatten 插件时，各自 `closeBundle` 搬完就 `rmSync(dist/src)`；第一个插件删掉整棵子树，后面插件的源文件已不存在，且不报错 | 合并为单插件吃全部入口名；`vue-build.test.ts` 新增「预览页落到 dist/<name>.html」逐入口断言 |
| 2 | 上面那条断言在改坏配置后**照样 ok**（假绿） | `emptyOutDir: false` ⇒ 陈旧 `dist/probe-b.html` 是上一次构建留下的 | 测试改为先 `rmSync(dist)` 再 build |

分支双向验证：双入口 probe 下，坏配置 exit=1 且报 `not found: dist\probe-b.html`，好配置该断言 ok；无 `<style>` 的 probe 入口也让 CSS 断言按预期 exit=1。`vue-build.test.ts` 单入口下 14 → 15 条，其中 5 条（bundle 存在 / 预览页存在 / 不含 `/dist/vue/` / 导出 mount / CSS 资产）改为按扫描到的入口循环，**每个新版式自动 +5**，不是写死在 hook 上。

回归证据：删掉 probe 后 `rm -rf dist && npm run build:templates`，4 个产物 md5 与重构前**逐字节一致**（含 `export{Vh as mount}` 那个 entry chunk），故无需重跑真渲染。`npm test` exit=0 / `typecheck:web` exit=0 / `path_b_selftest.py` 187/187。

> 过程事故一条，已完全恢复：我用 `cat >` 想看 `main.html` 内容时把它覆盖了（该文件未入库，git 救不回）。从上一段会话 transcript 里取回逐行原文重建，再以「重建产物 md5 == 事故前 md5（`c1db638e…`）」证明还原无偏差。教训：查看文件用 Read，别对未入库文件用重定向。

证据全部通过 Read + Grep + ls 直取（6 个源文件全过）。升 Tier 2（推广 56 份 composition）时改用 `search_graph` 取全局 caller/callee 图。
