# 2026-10-13 · HyperFrames news-coral · Vue POC 设计 + 实施 + 验证（Tier 1 合并）

## §1 目标

把 `skills/douyin-pro/templates/hyperframes_path_b/news-coral/compositions/hook.html`
（256 行手写 HTML + `<style>` + GSAP `<script>` + 数据占位 + 对比度审计注释）迁成
Vue 3 单文件组件，**通过 Vite 多入口 build 出静态 HTML**，跑完跟原版像素级一致。

POC 验证通过后，所有 56 份 composition（8 个模板 × 7 layout）按相同模式推广。

## §3 不做什么（显式边界）

| 不做 | 原因 |
|---|---|
| 不改 Python 渲染管线 | headless browser / FFmpeg / AIGC 角标 / 字幕 ASS / Commons 图层—— 一行不动 |
| 不替换 GSAP | GSAP 仍是 GSAP，Vite build 时打包进产物，不走 CDN（hyperframes 可能在无网环境） |
| 不引入 SSR | 截图管线只看最终 DOM，SSR 增加复杂度无收益 |
| 不动 hf_primitives / hf_compile / path_b_build | P1 编译路径另起一刀，本次 POC 走老路径（手写 spec → host + 7 layout） |
| 不引入 Pinia / Vue Router / Vuex | 单组件只一个 ref/reactive 不需要全局状态 |
| 不动 host.html | host.html 的 `{{COMPOSITION_ID}}` 等占位符由 path_b_build.py 替换，不在 POC 范围 |
| 不替代 path_b_selftest.py | 那测的是 Python 发射器；新增 `tests/web/vue-build.test.ts` 验证产物 |

## §4 POC 范围

**一个 composition = `news-coral` 的 `hook`**（首镜钩子）。理由：
- 包含全部"难"的元素：珊瑚火带 + 白底眉标片 + 反相强调词 + Ken Burns 图层 + 6 条 GSAP 补间
- 数据占位符 8 个（kicker / headTop / headBottomLead / headAccent / support / imagePath / imageCredit / slotSeconds）—— 类型最多
- 是其他 6 个 composition（stat / rail / quote / closer / catalog / story）的样板，迁通一个就能照抄

**产物路径**：POC build 出来的静态 HTML 写到
`skills/douyin-pro/templates/hyperframes_path_b/news-coral/compositions/vue-hook.html`（新文件，与原 `hook.html` 并存）。
A/B 比对：跑两次 path_b_build，一次吃原 hook.html、一次吃 vue-hook.html，对比 final.mp4 字节哈希。

## §5 设计

### §5.1 组件树

```
src/web/entries/news-coral-hook/
├── main.ts                       (Vue 应用 mount + GSAP 编排)
├── NewsCoralHook.vue            (单文件组件: template + script setup + style scoped)
└── data.contract.ts             (8 个字段的 TypeScript 类型契约,编译期拒拼错)

src/web/lib/
├── hyperframes-bridge.ts        (window.__hyperframes.getVariables() 协议适配)
├── gsap-runtime.ts              (npm gsap,无 CDN)
└── tokens/coral.ts               (色板常量, 与 frame.md §1 同值; 自动校准通过 audit_pack_contrast.py)
```

### §5.2 数据流（关键：保留 Python 协议）

```python
# path_b_build.py 写入 index.html:
#   <div data-variable-values='{"kicker": "...", "headTop": "..."}'>
#   <script>window.__hyperframes = { getVariables: () => JSON.parse(div.dataset.variableValues) }</script>
```

```typescript
// web/lib/hyperframes-bridge.ts
export interface HyperframesBridge {
  getVariables: () => Record<string, string | number>;
}
export function readBridge(): HyperframesBridge {
  const w = window as unknown as { __hyperframes?: HyperframesBridge };
  if (!w.__hyperframes) throw new Error("hyperframes bridge missing — host.html not mounted");
  return w.__hyperframes;
}
```

```vue
<!-- NewsCoralHook.vue -->
<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { gsap } from "../lib/gsap-runtime";
import { readBridge, type Variables } from "../lib/data.contract";
const vars = ref<Variables>({} as Variables);
const hasPhoto = computed(() => Boolean(String(vars.value.imagePath ?? "").trim()));
const slot = computed(() => Number(vars.value.slotSeconds) || 4);
onMounted(() => {
  vars.value = readBridge().getVariables() as Variables;
  // GSAP timeline —— 逻辑从原 hook.html 末段搬运,fromTo 一律不改,seek 仍安全
  const tl = gsap.timeline({ paused: true });
  tl.fromTo("#h-band", { scaleY: 0 }, { scaleY: 1, duration: 0.5, ease: "power3.out" }, 0);
  tl.fromTo("#h-eb",   { scaleX: 0 }, { scaleX: 1, duration: 0.4, ease: "power2.out" }, 0.3);
  // ...其余 4 条照原 hook.html
  (window as unknown as { __timelines: Record<string, gsap.core.Timeline> })
    .__timelines["nc-night-hook"] = tl;
});
</script>

<template>
  <div id="root" data-composition-id="nc-night-hook" data-width="1080" data-height="1920">
    <div class="h-band" id="h-band" />
    <div class="h-eb"   id="h-eb"   data-var-text="kicker">{{ vars.kicker }}</div>
    <div class="h-field" id="h-field">
      <div class="h-hd">
        <div id="h-l1" data-var-text="headTop">{{ vars.headTop }}</div>
        <div><span id="h-l2" data-var-text="headBottomLead">{{ vars.headBottomLead }}</span><span class="h-ac" id="h-ac" data-var-text="headAccent">{{ vars.headAccent }}</span></div>
      </div>
      <div class="h-hair" id="h-hair" />
      <div class="h-sup"  id="h-sup"  data-var-text="support">{{ vars.support }}</div>
    </div>
    <figure v-if="hasPhoto" class="hk-photo" id="hk-photo" data-layout-allow-overflow>
      <img class="hk-photo-img" id="hk-img" data-layout-allow-overflow :src="vars.imagePath" alt="" />
    </figure>
    <figcaption class="hk-photo-credit" id="hk-credit">图源：Wikimedia Commons</figcaption>
  </div>
</template>

<style scoped>
  /* 原 hook.html 的 <style> 段逐行搬运;scoped 让选择器带 [data-v-hash] 不污染全局 */
  /* @font-face 必须放在 unscoped 区块(Vue scoped 加不到 @font-face 规则上),
     用 <style> 第二个块(unscoped) 单独声明 */
</style>
<style>
  @font-face { font-family: "HF CJK"; src: local("Noto Sans SC"), ..., local("PingFang SC"); font-weight: 100 900; }
</style>
```

### §5.3 Vite 配置

```typescript
// vite.config.ts
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "node:path";
export default defineConfig({
  plugins: [vue()],
  build: {
    rollupOptions: {
      input: {
        "news-coral/hook": resolve(__dirname, "src/web/entries/news-coral-hook/main.html")
    },
    outDir: "dist",
    emptyOutDir: false
  }
});
```

**入口 HTML**：`src/web/entries/news-coral-hook/main.html` —— Vite 默认模板，body 里只 `<div id="app"></div>` + `<script type="module" src="./main.ts"></script>`。**不写 GSAP CDN 引用**。

**GSAP 引入**：`src/web/lib/gsap-runtime.ts` 里 `import { gsap } from "gsap"`，Vite 自动 tree-shake 打包进产物 chunk。

### §5.4 Build 命令

```jsonc
// package.json 加 4 个脚本:
"build:templates":      "vite build --mode production",
"build:templates:dev":  "vite build --mode development",
"preview:templates":    "vite preview --port 4173",
"typecheck:templates":  "vue-tsc --noEmit -p tsconfig.web.json"
```

devDeps 加：`vue@^3.5`、`vite@^6`、`@vitejs/plugin-vue@^5`、`vue-tsc@^2`、`gsap@^3.12`（gsap 升到与 CDN 同主版本 3.14）。

## §6 证据（Evidence）

### §6.1 改动触及的代码（手工 Read 取证）

| 符号 | 路径 | 行数 | 角色 |
|---|---|---|---|
| `hook.html` | `skills/douyin-pro/templates/hyperframes_path_b/news-coral/compositions/hook.html` | 256 | **等价迁出**；保留作 A/B 基线 |
| `host.html` | `skills/douyin-pro/templates/hyperframes_path_b/news-coral/host.html` | 59 | **不动**（POC 范围外） |
| `frame.md` | `skills/douyin-pro/templates/hyperframes_path_b/news-coral/frame.md` | 162 | **不动**；§1 色板常量化进 `tokens/coral.ts`，由 `audit_pack_contrast.py` 校准 |
| `path_b_selftest.py` | `skills/douyin-pro/scripts/path_b_selftest.py` | 4237 | **不动**；既验证 Python 发射器；新增 web 产物对照测 |
| `audit_pack_contrast.py` | `skills/douyin-pro/scripts/` | — | **不动**；是 §1 色板的复算闸门，搬常量时必须跑过 |
| `package.json` | 根 | 27 | 加 4 个脚本 + 5 个 devDep |
| `tsconfig.json` | 根 | 26 | **不动**（已是 strict + erasableSyntaxOnly） |

### §6.2 影响面（手工 Read 取证）

- **inbound 调用方**（谁调 hook.html 的产物）：
  - `path_b_build.py` —— 通过 `{{SCENES}}` 把多个 composition 嵌入 host.html
  - `npy hyperframes render` —— 命令行渲染最终 mp4
  - **`hf_primitives.py` 当前 P0/P1 编译路径尚未切到现状**（spec 已就绪，编译路径在试运行），POC 不动 P1
- **outbound 被调用方**（hook.html 调什么）：
  - `window.__hyperframes.getVariables()` —— 数据注入协议
  - `gsap.timeline(...)` —— 动画库
  - `window.__timelines["nc-night-hook"] = tl` —— 时间轴登记

### §6.3 验证断言（改完逐条核）

- [ ] `npm run build:templates` 产物存在 `dist/news-coral/hook.html`（Vite 默认 SPA + 我们的多入口配置）
- [ ] 产物内**含 GSAP 打包后代码**（不引 CDN）：`grep -q "gsap" dist/news-coral/hook.html` 且产物无 `cdn.jsdelivr.net` 引用
- [ ] 产物内 Vue mount 点存在：`<div id="app">` + 挂载脚本
- [ ] 产物的 `__hyperframes.getVariables()` 协议**仍由 host.html 在挂载时写入**（Vite 产物不覆盖 host.html）
- [ ] 跑 `python skills/douyin-pro/scripts/path_b_build.py` 两次：一次原 hook.html、一次 vue-hook.html，两份 final.mp4 字节哈希一致（**用 ffmpeg -hide_banner -i 比对**；不依赖像素级）
- [ ] `npm run typecheck:templates`（vue-tsc 校验 .vue script setup + types）= 0 错误
- [ ] `python skills/douyin-pro/scripts/path_b_selftest.py` 全绿（原 Python 闸门不被新代码影响）
- [ ] `python skills/douyin-pro/scripts/audit_pack_contrast.py news-coral` 全绿（§1 色板常量化后复算 0 漂移）
- [ ] CJK 字体闸门绿：`t_cjk_gate_green_on_shipped_packs` 跑得通（保证 HF CJK 的 @font-face 写法没被 Vue 吞掉）

### §6.4 不可验证的盲点

- **像素级一致**：POC 不真跑 headless browser 截图对比——除非用户额外跑 `npy hyperframes render` 真渲染。POC 验证级别是「结构 + 字节哈希」一致，**视觉差 ≤ 1% 像素**只能等真渲染
- **GSAP seek 回退行为**：原 hook.html 用 `fromTo` 是因为 `from()` 在 seek 回退时失步（D3 死法）。Vue 版也用 `fromTo`，但 Vue reactivity 触发的 re-render 行为是否影响 GSAP 引用同一元素——**只通过真渲染验证**
- **scoped CSS 选择器冲突**：原 hook.html 的 `#root > *:not(...)` 这类通用选择器在 Vue scoped 下可能因 `[data-v-hash]` 加不到 `:not` 内部而失效。POC 用 `:deep()` 兜底，但**真实覆盖效果只在真渲染可见**
- **生产构建压缩后产物大小**：GSAP 完整 ~70KB gzip 后 ~25KB——Vite 默认压缩会让 dist HTML 多 ~30KB。**性能影响盲点**

## §7 工具降级声明

> `[codebase-memory-mcp 降级声明]`
> 本次 POC 范围 ≤200 行 / 单 composition 范畴改动，证据已通过 Read + Grep 直接源码取证（hook.html / host.html / frame.md / path_b_selftest.py / hf_primitives.py / tsconfig.json 全已 Read）。codebase-memory-mcp 的 `search_graph` / `trace_path` 对单文件 POC 收益低于手工 Read，**未调用**。若升 Tier 2（推广到 56 份 composition），改用 `search_graph` 取全局 caller/callee 图。

## §8 完成判据

1. ✅ 合并文档已写（本文件，含证据段）
2. ⏳ 用户确认「开始实现」
3. ⏳ 主 Agent 改完 + §6.3 验证断言逐条核（不自动跑 `npm run build:templates` —— 用户跑）
4. ⏳ 写 `verifications/2026-10-13-hyperframes-vue-poc-verification-lite.md`，证据闭环
5. ⏳ **可以 commit**（不自动 push，push 由用户决定）

## §9 实施步骤（主 Agent 直做，Tier 1）

1. `npm install --save-dev vue@^3.5 vite@^6 @vitejs/plugin-vue@^5 vue-tsc@^2 gsap@^3.14`
2. 写 `tsconfig.web.json`（extends root，include 加 `main: ["src/web/**/*.ts", "src/web/**/*.vue"]`，开 `jsx: "preserve"` + `"types": ["vite/client"]`）
3. 写 `vite.config.ts`（§5.3）
4. 写 `src/web/lib/data.contract.ts`（8 个字段的 zod schema 或纯 interface）
5. 写 `src/web/lib/gsap-runtime.ts`（`export { gsap } from "gsap"`）
6. 写 `src/web/lib/hyperframes-bridge.ts`（§5.2）
7. 写 `src/web/lib/tokens/coral.ts`（色板常量，从 frame.md §1 搬，每条带 `color_hex()` 复算自检函数）
8. 写 `src/web/entries/news-coral-hook/main.html`（Vite 默认模板 + `<div id="app"></div>`）
9. 写 `src/web/entries/news-coral-hook/main.ts`（`createApp(NewsCoralHook).mount("#app")`）
10. 写 `src/web/entries/news-coral-hook/NewsCoralHook.vue`（§5.2）
11. 改 `package.json` 加 4 个脚本（§5.4）
12. 写 `tests/web/vue-build.test.ts`：跑 `vite build` → 断言 §6.3 八条
13. 跑 `npm run typecheck:templates`、`npm run build:templates`、`npm test`、`python skills/douyin-pro/scripts/path_b_selftest.py`
14. 写 `verifications/2026-10-13-hyperframes-vue-poc-verification-lite.md`，把每条断言的证据（截图/输出/哈希）贴进去

## §10 升级信号

如果实施过程中发现：
- 改动 ≥ 200 行 → 升 Tier 2，分头加 plan + spec
- 改动跨 ≥ 3 个文件超 §9 范围 → 升 Tier 2
- 发现 hf_primitives 的 P1 编译路径已被切到现状 → 暂停，问用户走 P1 还是手写 POC

**未升 Tier 2 之前，本文件同时是 spec + plan + 验证断言合一**（按 CLAUDE.harness.md §2 Tier 1）。