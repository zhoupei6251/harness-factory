import { createApp } from "vue";
import HookB from "./HookB.vue";

/**
 * HyperFrames Vue mount 入口 —— hook-b（news-policy 孤簇）
 *
 * 与 hook-a 同契约：loader 把整个 clip（每次唯一 id）+ composition_id 传下来，
 * 真正的挂载节点是 clip 内的 `:scope > .vue-target`，组件从 clip 自身读本镜数据。
 *
 * 独立预览（Vite preview 时 main.html 用）：找 #vue-preview-target 当 clip。
 * 这里保留 1 处包级 id 字面量 —— 预览页没有引擎，不参与撞键。
 */
export function mount(clip: HTMLElement, compositionId: string): void {
  const target = clip.querySelector<HTMLElement>(":scope > .vue-target") ?? clip;
  createApp(HookB, { compositionId, clip }).mount(target);
}

if (typeof document !== "undefined") {
  const preview = document.getElementById("vue-preview-target");
  if (preview) {
    mount(preview, "np-hook");
  }
}
