import { defineConfig, type Plugin, type UserConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "node:path";
import { copyFileSync, existsSync, readdirSync, rmSync } from "node:fs";

const ENTRIES_DIR = resolve(__dirname, "src/web/entries");

/**
 * src/web/entries/ 下的每个子目录就是一个 composition 入口：
 *   main.ts   → host.html loader 消费的 entry bundle（导出 mount）
 *   main.html → 独立预览页（可选）
 * 新增版式只要建目录，配置不用改。
 */
function scanEntries(): string[] {
  return readdirSync(ENTRIES_DIR, { withFileTypes: true })
    .filter((dir) => dir.isDirectory())
    .filter((dir) => existsSync(resolve(ENTRIES_DIR, dir.name, "main.ts")))
    .map((dir) => dir.name)
    .sort();
}

/**
 * Vite 6 的多 HTML entry 把 HTML 直接 fs.writeFile 到 dist/<entry 相对路径>/<basename>，
 * 不经过 generateBundle bundle 对象。需要在 closeBundle 阶段搬文件。
 *
 * 把 dist/src/web/entries/<name>/main.html 搬到 dist/<name>.html，
 * 让产物路径跟原静态 pack 的 composition HTML 同级（dist 根）。
 *
 * 一个插件处理全部入口，而不是每入口一个：closeBundle 按插件顺序跑，而每个插件
 * 搬完都要删 dist/src 子树——拆成 N 个时第一个插件就把后面还没搬的 HTML 连带删了，
 * 第 2 个及以后的预览页会静默不产出。
 */
function flattenHtmlEntries(entryNames: string[]): Plugin {
  const distDir = resolve(__dirname, "dist");
  const sourceRoot = resolve(distDir, "src");

  return {
    name: "flatten-html-entries",
    closeBundle() {
      for (const entryName of entryNames) {
        const sourcePath = resolve(
          sourceRoot,
          "web",
          "entries",
          entryName,
          "main.html"
        );
        if (!existsSync(sourcePath)) continue;
        copyFileSync(sourcePath, resolve(distDir, `${entryName}.html`));
      }
      rmSync(sourceRoot, { recursive: true, force: true });
    },
  };
}

/**
 * HyperFrames templates → static HTML 多入口构建
 *
 * 每个 entry 是一个 .vue 单文件组件，build 出等价静态 HTML（带 GSAP + Vue runtime），
 * 交给现有 Python 渲染管线（path_b_build.py + headless browser）继续消费。
 *
 * 不破坏：Python 渲染管线、host.html、frame.md、path_b_selftest.py。
 */
export default defineConfig((): UserConfig => {
  const entries = scanEntries();
  const previewEntries: string[] = [];
  const input: Record<string, string> = {};
  for (const name of entries) {
    // host.html 的 loader 契约是 `mod.mount(target, compId)`，产物必须真的导出 mount。
    // 实测：只把 main.html 当 input 时产物里没有任何 `export{}`（preserveEntrySignatures
    // 设 allow-extension / strict 都不救，HTML 入口下的 .ts 只是它的依赖而非入口），
    // 于是真渲染报 `mod.mount is not a function` + timeline 未注册。
    // 解法：main.ts 自己作入口（导出得以保留），main.html 退为独立的预览入口。
    input[name] = resolve(ENTRIES_DIR, name, "main.ts");
    if (existsSync(resolve(ENTRIES_DIR, name, "main.html"))) {
      previewEntries.push(name);
      input[`${name}-preview`] = resolve(ENTRIES_DIR, name, "main.html");
    }
  }

  return {
    plugins: [vue(), flattenHtmlEntries(previewEntries)],
    build: {
      outDir: "dist",
      emptyOutDir: false,
      rollupOptions: {
        input,
        preserveEntrySignatures: "strict",
        output: {
          entryFileNames: "vue/[name].js",
          chunkFileNames: "vue/chunks/[name]-[hash].js",
          assetFileNames: "vue/assets/[name]-[hash][extname]",
        },
      },
    },
    esbuild: {
      target: "es2022",
    },
  };
});