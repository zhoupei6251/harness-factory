import { createApp } from "vue";
import NewsCoralHook from "./NewsCoralHook.vue";

/**
 * HyperFrames Vue mount 入口
 *
 * host.html 的 loader script 调本函数，传 mount target 元素 + composition_id。
 * Vue 应用 mount 到 target，从最近的 [data-composition-id] 读 data-variable-values。
 *
 * 独立预览（Vite preview 时 main.html 用）：找一个 #vue-preview-target mount 点。
 */
export function mount(target: HTMLElement, compositionId: string): void {
  createApp(NewsCoralHook, { compositionId }).mount(target);
}

// 独立预览：main.html 不写死 #app，让 Vue mount 到 caller 传入的元素
if (typeof document !== "undefined") {
  const preview = document.getElementById("vue-preview-target");
  if (preview) {
    mount(preview, "nc-night-hook");
  }
}