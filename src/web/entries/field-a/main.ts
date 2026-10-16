import { createApp } from "vue";
import FieldA from "./FieldA.vue";

/**
 * HyperFrames Vue mount 入口 —— field-a（第一个 Vue-only 版式：没有静态 HTML 前身）
 *
 * 与 hook-a/hook-b 同契约：loader 把整个 clip（每次唯一 id）+ composition_id 传下来，
 * 真正的挂载节点是 clip 内的 `:scope > .vue-target`，组件从 clip 自身读本镜数据。
 *
 * 独立预览用的包级 id 字面量在这里是合法的 —— 预览页没有引擎，不参与撞键；
 * 组件内部的注册键一律取传下来的 compositionId（闸门守着）。
 */
export function mount(clip: HTMLElement, compositionId: string): void {
  const target = clip.querySelector<HTMLElement>(":scope > .vue-target") ?? clip;
  createApp(FieldA, { compositionId, clip }).mount(target);
}

if (typeof document !== "undefined") {
  const preview = document.getElementById("vue-preview-target");
  if (preview) {
    mount(preview, "field-news-coral");
  }
}
