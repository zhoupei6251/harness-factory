#!/usr/bin/env tsx
/**
 * Vue build 端到端测试
 *
 * 跑 `vite build` → 校验产物存在 + 静态结构 + 关键元素 ID + GSAP 打包。
 * 本测试自身不真渲染（只做产物结构断言）。真渲染已在本机跑通：
 * 见 verifications/2026-10-13-hyperframes-vue-poc-verification-lite.md §10。
 *
 * 入口清单来自 src/web/entries/ 目录扫描，跟 vite.config.ts 读同一个真源——
 * 配置若退回写死入口，新增版式会在这里报「bundle 缺失」而不是静默漏掉。
 *
 * 跑法（测试自己清 dist 再 build，不需要先跑 build:templates）：
 *   tsx tests/web/vue-build.test.ts
 */
import { execSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync, rmSync, statSync } from "node:fs";
import { resolve, dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..", "..");
const DIST = resolve(ROOT, "dist");
const ENTRIES_SRC = resolve(ROOT, "src", "web", "entries");

/** src/web/entries/ 下含 main.ts 的子目录 = 一个 composition 入口 */
const entryNames = readdirSync(ENTRIES_SRC, { withFileTypes: true })
  .filter((d) => d.isDirectory())
  .filter((d) => existsSync(resolve(ENTRIES_SRC, d.name, "main.ts")))
  .map((d) => d.name)
  .sort();

const bundlePath = (name: string): string => resolve(DIST, "vue", `${name}.js`);

/** 有 main.html 的入口 = 有独立预览页，产物必须落到 dist/<name>.html */
const previewNames = entryNames.filter((name) =>
  existsSync(resolve(ENTRIES_SRC, name, "main.html")),
);

// hook 版式是唯一有逐字段内容断言的入口（其余版式共享下面的通用断言）
// Task 4：入口目录改名 hook-a —— bundle 名现在由 `vue_bundle_for(pack, role)`
// 按 `f"{role}-{variant}"` 推导（path_b_build 发射的 data-vue-bundle 就是它）。
const HOOK = "hook-a";
const DIST_HTML = resolve(DIST, `${HOOK}.html`);
const DIST_ENTRY_JS = bundlePath(HOOK);

const FAILURES: Array<[string, string]> = [];

function check(name: string, fn: () => void): void {
  try {
    fn();
    console.log(`  ok    ${name}`);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    FAILURES.push([name, msg]);
    console.log(`  FAIL  ${name}: ${msg}`);
  }
}

function assert(cond: unknown, msg: string): asserts cond {
  if (!cond) throw new Error(msg);
}

// 1. 跑 build
// vite.config 里 emptyOutDir=false，陈旧产物会让断言假绿——实测：把 flatten 插件改坏后
// 旧的 dist/probe-b.html 还在原地，「预览页落到 dist/<name>.html」照样 ok。所以先清 dist。
console.log("[vue-build] cleaning dist");
rmSync(DIST, { recursive: true, force: true });
console.log("[vue-build] running: npx vite build");
execSync("npx vite build", { cwd: ROOT, stdio: "inherit" });

// 2. 静态产物断言
check("src/web/entries/ 至少有一个入口", () => {
  assert(
    entryNames.length > 0,
    `no entry (dir with main.ts) under ${ENTRIES_SRC} —— 入口目录被清空了`
  );
});

for (const name of entryNames) {
  check(`dist/vue/${name}.js 存在（entry chunk）`, () => {
    assert(existsSync(bundlePath(name)), `not found: ${bundlePath(name)}`);
  });
}

for (const name of previewNames) {
  check(`${name}: 预览页落到 dist/${name}.html（flatten 插件搬齐每个 HTML 入口）`, () => {
    // 实测：若按「一入口一插件」拆开，插件们各自在 closeBundle 里 rmSync(dist/src)，
    // 第一个插件删掉子树后，后面插件的源文件已不存在 ⇒ 第 2 个预览页静默不产出。
    // 双 HTML 入口的 probe 构建证实了这点（dist/probe-b.html 缺失）。
    const p = resolve(DIST, `${name}.html`);
    assert(existsSync(p), `not found: ${p}`);
  });
}

const html = existsSync(DIST_HTML) ? readFileSync(DIST_HTML, "utf8") : "";

check("产物不含硬编码 #app mount 点（Tier 3: caller 传 target）", () => {
  // main.html 改后不再写 <div id="app">——loader script 调 mod.mount(target, compId)
  if (html.includes('<div id="app">')) {
    throw new Error("Tier 3 产物不该含硬编码 #app; caller 传 mount target");
  }
});

check("产物不含 CDN 引用（hyperframes 在无网环境也跑）", () => {
  if (html.includes("cdn.jsdelivr.net") || html.includes("unpkg.com")) {
    throw new Error("CDN reference found in built HTML");
  }
});

check(`产物引用 entry chunk (${HOOK}.js)`, () => {
  if (!html.includes(`${HOOK}.js`)) {
    throw new Error("entry chunk not referenced from HTML");
  }
});

check(`产物含 data-composition-id="nc-night-hook"`, () => {
  // 实际值在 bundle JS 里（Vue template 编译后），HTML 里可能不出现
  // 检查 bundle JS 是否含这个字面量
  const js = readFileSync(DIST_ENTRY_JS, "utf8");
  if (!js.includes("nc-night-hook")) {
    throw new Error('"nc-night-hook" not bundled');
  }
});

check(`${HOOK}: composition 身份不写死（注册键与根 id 都用传入 compositionId）`, () => {
  // Task 4：发射器给每条 Vue 镜唯一 `data-composition-id`（vue_clip_id =
  // 包级 id + `__` + 挂载序号），loader 逐镜 `mod.mount(clip, compId)` 传下来；
  // 组件必须注册 `window.__timelines[props.compositionId]`、模板必须
  // `:data-composition-id="compositionId"`。引擎按 `__timelines[<元素自身 id>]`
  // 驱动（Task 2 Step 0 实测），任何写死形态都会让重复版式两镜撞键。
  const js = readFileSync(DIST_ENTRY_JS, "utf8");
  // main.ts 的独立预览入口允许保留 1 处包级 id 字面量（无引擎，不参与撞键）。
  const hits = js.split("nc-night-hook").length - 1;
  assert(
    hits <= 1,
    `bundle 里 "nc-night-hook" 出现 ${hits} 次（>1 = 注册键或模板 id 被写死回包级字面量）`
  );
  assert(
    !/window\.__timelines\[\s*["']/.test(js),
    '发现 window.__timelines["<字面量>"] 形态 —— 注册键必须是传入的 compositionId'
  );
});

check("GSAP 关键 API (timeline / fromTo) 出现在 dist 任一 JS", () => {
  const jsFiles: string[] = [];
  const walk = (dir: string): void => {
    for (const entry of readdirSync(dir)) {
      const p = join(dir, entry);
      const s = statSync(p);
      if (s.isDirectory()) walk(p);
      else if (entry.endsWith(".js")) jsFiles.push(p);
    }
  };
  walk(DIST);
  assert(jsFiles.length > 0, "no .js files in dist");
  // GSAP 必须出现在某 .js 里（入口 chunk 或独立 chunk 都算）
  let found = false;
  for (const f of jsFiles) {
    const text = readFileSync(f, "utf8");
    if (text.includes("fromTo") || text.includes("timeline")) {
      found = true;
      break;
    }
  }
  assert(found, "no fromTo/timeline API in any dist JS file");
});

check("hook 关键元素 ID 出现在 entry bundle", () => {
  const js = readFileSync(DIST_ENTRY_JS, "utf8");
  // 这些 ID 是 Vue template 的元素 attribute，编译后保留为字符串字面量
  const ids = [
    "h-band", "h-eb", "h-field", "h-l1", "h-l2",
    "h-ac", "h-hair", "h-sup", "hk-photo", "hk-img", "hk-credit",
  ];
  for (const id of ids) {
    if (!js.includes(id)) {
      throw new Error(`#${id} not bundled`);
    }
  }
});

check("@font-face HF CJK 声明被保留（在 JS 或 CSS 任一处）", () => {
  const targets: string[] = [];
  const walk = (dir: string): void => {
    for (const entry of readdirSync(dir)) {
      const p = join(dir, entry);
      const s = statSync(p);
      if (s.isDirectory()) walk(p);
      else if (entry.endsWith(".css") || entry.endsWith(".js")) targets.push(p);
    }
  };
  walk(DIST);
  let found = false;
  for (const f of targets) {
    const text = readFileSync(f, "utf8");
    if (text.includes("HF CJK")) {
      found = true;
      break;
    }
  }
  assert(found, "HF CJK font face missing from bundle (checked all .css/.js in dist)");
});

check("8 个数据占位字段 (kicker/headTop/headBottomLead/headAccent/support/imagePath/imageCredit/slotSeconds) 出现", () => {
  const js = readFileSync(DIST_ENTRY_JS, "utf8");
  for (const v of ["kicker", "headTop", "headBottomLead", "headAccent", "support", "imagePath", "imageCredit", "slotSeconds"]) {
    if (!js.includes(v)) {
      throw new Error(`field "${v}" missing from bundle`);
    }
  }
});

// ---- Tier 3: 每个入口的通用产物契约 ----

for (const name of entryNames) {
  check(`${name}: entry bundle 不含硬编码 /dist/vue/ 绝对路径（host.html 用相对 ./vue/）`, () => {
    const js = readFileSync(bundlePath(name), "utf8");
    assert(
      !js.includes("/dist/vue/"),
      "entry bundle 含 /dist/vue/ 绝对路径会破坏 host.html 的相对路径引用"
    );
  });
}

// ---- Tier 3 mount 边界：host.html 的 loader 靠 `mod.mount(target, compId)` 调用 ----

for (const name of entryNames) {
  check(`${name}: entry bundle 导出 mount 函数（loader 的 mod.mount 契约）`, () => {
    const js = readFileSync(bundlePath(name), "utf8");
    // 真渲染实测：以 main.html 为唯一 rollup input 时，产物里根本没有 `export{}`
    // （把 preserveEntrySignatures 设成 allow-extension / strict 也不救），
    // loader 拿到命名空间后 `mod.mount is not a function`，GSAP timeline 永不注册，
    // hyperframes 报 sub_timeline_script_failure。改为 main.ts 直接作入口后导出才出现。
    assert(
      /export\s*\{[^}]*\bas\s+mount\b/.test(js) ||
        /export\s+(async\s+)?function\s+mount\b/.test(js),
      `dist/vue/${name}.js 没有导出 mount —— host.html 的 loader 会抛 TypeError`
    );
  });
}

// Task 5：注册键不写死这条从「只查 hook-a」扩到**每个入口**。
// hook-b 是本次新增的第二个组件；引擎按 `__timelines[<元素自身 id>]` 驱动，
// 任何 `__timelines["字面量"]` 形态都会让同版式两镜撞键（Task 2 实测过这个失效模式）。
for (const name of entryNames) {
  check(`${name}: 时间轴注册键不写死（window.__timelines[...] 不得接字面量）`, () => {
    const js = readFileSync(bundlePath(name), "utf8");
    assert(
      !/window\.__timelines\[\s*["']/.test(js),
      `dist/vue/${name}.js 出现 window.__timelines["<字面量>"] —— 注册键必须是传入的 compositionId`
    );
  });
}

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

check("bundle 内 GSAP 版本 == 声明版本（spec §5-P0 判据 3 的原文口径）", () => {
  // 上一条只比「package.json 声明 == package-lock 解析」，管的是**依赖怎么装**；
  // spec §5-P0 第 3 条要的是「**bundle 内** GSAP 版本 == 声明版本」，管的是**产物是不是这次的**。
  // 两者不等价：声明/锁一致但 dist/ 是旧 GSAP 编出来的陈旧产物时，只有这条会红。
  //
  // 锚点形态实测：GSAP 在产物里写 `…version=…version=…version="3.15.0"`，
  // 全文 `version\s*=\s*"\d+\.\d+\.\d+"` 这种「版本赋值标记」命中**恰好 1 次**，值就是 gsap 版本；
  // vue 的 3.5.43 不以该形态出现。
  //
  // Task 5 重锚（**不是放宽**）：原来只读 `dist/vue/hook-a.js`，那是单入口时代的形状。
  // 第二个入口 hook-b 一进来，Vite 就把共享的 GSAP 提到 `dist/vue/chunks/hyperframes-*.js`，
  // 入口 chunk 里连 `gsap` 字样都没有了 —— 旧读法会报「找不到标记」，而产物其实是好的。
  // 现在扫**全部** dist JS，并要求：含 GSAP 的文件里版本标记全局恰好一处、且等于声明值。
  // 比原来严（原来只保证 hook-a 那一份里有），且换 chunk 名 / 换入口数都不用再改这条。
  const pkg = JSON.parse(readFileSync(resolve(ROOT, "package.json"), "utf8"));
  // gsap/vue 现在都声明在 devDependencies（与被测产物同口径：合并两块，与上一条检查一致）
  const deps = { ...(pkg.dependencies ?? {}), ...(pkg.devDependencies ?? {}) };
  const declared: string = deps["gsap"] as string;
  assert(
    typeof declared === "string" && /^\d+\.\d+\.\d+$/.test(declared),
    `package.json 的 gsap 声明 ${declared} 不是精确版本，无法拿去比 bundle`
  );
  const jsFiles: string[] = [];
  const walk = (dir: string): void => {
    for (const entry of readdirSync(dir)) {
      const p = join(dir, entry);
      const s = statSync(p);
      if (s.isDirectory()) walk(p);
      else if (entry.endsWith(".js")) jsFiles.push(p);
    }
  };
  walk(DIST);
  const markers: Array<[string, string]> = [];
  for (const f of jsFiles) {
    const text = readFileSync(f, "utf8");
    if (!text.toLowerCase().includes("gsap")) continue;
    for (const m of text.matchAll(/version\s*=\s*"(\d+\.\d+\.\d+)"/g)) {
      markers.push([relative(DIST, f), m[1]]);
    }
  }
  assert(
    markers.length > 0,
    `dist 下所有含 GSAP 的 JS 里都找不到 version="x.y.z" 形态的 GSAP 版本标记 —— ` +
      "GSAP/Vite 换了产物写法，这条锚需要人工重新对齐（别改成放宽断言）"
  );
  assert(
    markers.length === 1,
    `GSAP 版本标记出现 ${markers.length} 处（${markers.map((m) => m.join(":")).join(", ")}) —— ` +
      "打了多份 GSAP，产物字节不再由单一版本决定"
  );
  assert(
    markers[0][1] === declared,
    `GSAP 版本标记是 ${markers[0][1]}（在 ${markers[0][0]}），不是声明值 ${declared} —— dist 是陈旧产物或打了别的 GSAP`
  );
});

for (const name of entryNames) {
  check(`${name}: .vue 的 <style> 编译出 dist/vue/assets/${name}-*.css（发射器靠它发 <link>）`, () => {
    const assetDir = resolve(DIST, "vue", "assets");
    assert(existsSync(assetDir), `not found: ${assetDir}`);
    // 文件名带内容哈希，按 <name> 前缀匹配 —— 与 path_b_build.stage_vue_assets 的 glob 同口径
    const css = readdirSync(assetDir).filter((f) => f.startsWith(`${name}-`) && f.endsWith(".css"));
    assert(
      css.length > 0,
      `没有 ${name} 的 CSS 资产 —— 该入口的 <style> 会整块丢失，第 N 镜渲染成无样式`
    );
  });
}

check("hook 的 CSS 资产含 @font-face 与 #root 定位规则", () => {
  const assetDir = resolve(DIST, "vue", "assets");
  assert(existsSync(assetDir), `not found: ${assetDir}`);
  const css = readdirSync(assetDir).filter(
    (f) => f.startsWith(`${HOOK}-`) && f.endsWith(".css"),
  );
  assert(css.length > 0, `没有 ${HOOK} 的 CSS 资产`);
  const text = readFileSync(join(assetDir, css[0]), "utf8");
  assert(
    text.includes("@font-face") && text.includes("#root"),
    "CSS 资产缺少 @font-face / #root 定位规则 —— 第 1 镜会渲染成无样式"
  );
});

if (FAILURES.length > 0) {
  console.error(`\n[vue-build] ${FAILURES.length} failure(s):`);
  for (const [name, msg] of FAILURES) {
    console.error(`  - ${name}: ${msg}`);
  }
  process.exit(1);
}
console.log("\n[vue-build] all ok");