import { createApp } from "vue";
import NewsCoralHook from "./NewsCoralHook.vue";

/**
 * HyperFrames Vue mount 入口
 *
 * host.html 的 loader script 把整个 clip 元素传进来（每个 clip 每次唯一 id="shot-N"），
 * 加上 composition_id。真正的挂载节点是 clip 内的 `:scope > .vue-target`；组件从 clip
 * 自身的 data-variable-values 读本镜数据。
 *
 * spec §7 风险 9：不再按 composition_id 全局找挂载点 —— 同一版式在一次渲染里出现两次时
 * composition_id 相同，全局 getElementById 只会命中第一个，后续镜会挂错节点 / 读错数据。
 *
 * 独立预览（Vite preview 时 main.html 用）：找 caller 放进来的 #vue-preview-target 当 clip。
 */
export function mount(clip: HTMLElement, compositionId: string): void {
  const target = clip.querySelector<HTMLElement>(":scope > .vue-target") ?? clip;
  createApp(NewsCoralHook, { compositionId, clip }).mount(target);
}

// 独立预览：main.html 不写死 #app，让 Vue mount 到 caller 传入的元素
if (typeof document !== "undefined") {
  const preview = document.getElementById("vue-preview-target");
  if (preview) {
    mount(preview, "nc-night-hook");
  }
}
