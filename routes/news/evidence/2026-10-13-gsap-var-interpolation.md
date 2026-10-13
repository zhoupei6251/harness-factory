# GSAP color 补间是否支持 `var(--x)`（判据 0b）

- 探针：`src/web/probes/gsap-var-probe/main.ts`（gsap 3.15.0，与产线同一精确版本；探针为一次性测量件，
  结论落成本文件后即删除，不进 `src/web/entries/`，不入产线 bundle）
- 打包：`npx esbuild src/web/probes/gsap-var-probe/main.ts --bundle --format=esm --outfile=/tmp/gsap-probe/out.js`
  （exit 0，产出 166.0 kB，与计划预期 ~165 kB 相符）
- 运行环境：**真实 Chrome（chrome-devtools MCP）**。注：`file:///` 直开被 Chrome 以 CORS 拒绝
  （`file://` 协议下 `<script type="module">` 属跨源请求，实测报
  `Access to script ... from origin 'null' has been blocked by CORS policy`），
  遂用 `python -m http.server 8765` 本机 http 服务同一 ESM 产物后由 `new_page` 打开
  `http://127.0.0.1:8765/index.html` 测量。浏览器与 `getComputedStyle` 均为真实实现，
  **未**使用 jsdom 近似（计划 Step 2b 明令禁止）。
- t0 / t0.5 / t1 实测（`globalThis.__probe_result`，原文照录）：
  - `t0`  = `rgb(255, 0, 0)`
  - `t05` = `rgba(0, 0, 191, 0.75)`
  - `t1`  = `rgb(0, 0, 255)`
- 辅助观测（同页 `evaluate_script`）：t=1 时元素内联 style 为
  `--x: #ff0000; --y: #0000ff; color: var(--y);` —— GSAP 是把 `var(--y)` **原样字符串**写回内联样式，
  `t1` 的蓝是浏览器 CSS 变量解析的结果，不是 GSAP 补间出来的；`t0` 同理是 `var(--x)` 的原样回写。
- 判读（按 Task 7 写死的口径机械执行）：「能」要求 `t05` 红/蓝两个通道都在中间值
  （如 `rgb(127.x, 0, 127.x)`）。实测 `t05` 红通道为 **0**，不在红→蓝路径上——
  中间帧是 GSAP 从一个解析失败的起点（透明黑）向 `(0,0,255,1)` 的数值插值
  （`191 ≈ 255×0.75`，`0.75` 恰为默认 `power1.out` 在 p=0.5 的缓动值；此机制归因属推断，
  观测事实是红通道在中间帧丢失）。⇒ **不能**
- 结论：**GSAP 的 color 补间不能内插 `var(--x)`**。`t0`/`t1` 的纯色只是 CSS 变量在端点被原样回写后
  由浏览器解析的假象，中间帧证明 GSAP 解析不了 `var()`。
  所以 spec §4 B 方案里「GSAP 从 theme JSON 取 hex 字面量」这条 **必须保留**，不省。
- 判据 0b：**闭合**（证实先验判断）。
