/**
 * GSAP 引入：npm 包（不再走 CDN）
 *
 * 理由：hyperframes 可能在无网环境渲染，CDN 引用会失败。
 * Vite build 时把 gsap 打包进产物（chunk），浏览器零依赖加载。
 *
 * gsap 主版本对齐原 CDN 版本 3.14.x（避免动画曲线参数兼容性问题）。
 */
export { gsap } from "gsap";