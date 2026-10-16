import { createApp } from "vue";
import RankA from "./RankA.vue";

/**
 * HyperFrames Vue mount 入口 —— rank-a（第二个 Vue-only 版式：带量级条的 TOP-N 榜）
 *
 * 与 hook-a / field-a 同契约：loader 把整个 clip（每次唯一 id）+ composition_id 传下来，
 * 真正的挂载节点是 clip 内的 `:scope > .vue-target`，组件从 clip 自身读本镜数据。
 *
 * 独立预览用的包级 id 字面量在这里是合法的 —— 预览页没有引擎，不参与撞键。
 */
export function mount(clip: HTMLElement, compositionId: string): void {
  const target = clip.querySelector<HTMLElement>(":scope > .vue-target") ?? clip;
  createApp(RankA, { compositionId, clip }).mount(target);
}

if (typeof document !== "undefined") {
  const preview = document.getElementById("vue-preview-target");
  if (preview) {
    mount(preview, "rank-news-coral");
  }
}
