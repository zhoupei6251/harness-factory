/**
 * 与 Path B (production renderer) 共享的 composition 协议
 *
 * 真实数据流（path_b_build.py + hyperframes 渲染管线）：
 *   1. Python 发射器对每个 composition 在 host.html 里生成一个挂载元素：
 *        <div class="clip"
 *             data-composition-id="nc-night-hook"
 *             data-variable-values='{"kicker":"...","headTop":"...",...}'>
 *      （见 path_b_build.py 的 MOUNT_TPL）
 *   2. hyperframes 引擎（外部 npm 包）按 data-composition-id 选元素、读
 *      dataset.variableValues 注入数据，驱动 GSAP timeline。
 *
 * Vue 应用读数据走**同一条 DOM attribute**，不用自定义 window 协议：
 *   - 不动 host.html
 *   - 不动 path_b_build
 *   - 渲染管线读 DOM attribute 的协议保持一致（单一真相源）
 *
 * POC 限制：本文件只负责「Vue 端能拿到数据」。把 Vue 应用嵌入 host.html 的
 * mount 协议（host.html 怎么引用 Vue bundle、mount target ID 怎么对齐
 * composition_id）是 Tier 3 工作 —— 需改 host.html 模板 + path_b_build 的
 * MOUNT_TPL 形态。本文件独立可测试（Vite preview 时手动 mount）。
 */

import type { HookVariables } from "./data.contract";

/** 从传入的 clip 元素读 data-variable-values。
 *
 * spec §7 风险 9：旧写法用全局 `querySelector([data-composition-id=…])`，同一版式在一
 * 次渲染里出现两次时两个 clip 的 composition_id 相同 ⇒ 永远命中第一个、后续镜读错数据。
 * 现在挂载身份是每次唯一的 clip 元素（loader 传 `mod.mount(clip, …)`），本函数直接读该
 * clip 自己的 data-variable-values，不再全局查找。 */
export function readVariables(clip: Element): HookVariables {
  if (typeof document === "undefined") {
    throw new Error(
      "[hyperframes-bridge] document not available (SSR? POC 仅支持客户端 mount)"
    );
  }
  if (!clip) {
    throw new Error(
      "[hyperframes-bridge] readVariables(clip) 需要一个 clip 元素 —— loader 必须把整个 clip 传进来"
    );
  }
  const raw = clip.getAttribute("data-variable-values");
  if (!raw) {
    throw new Error(
      `[hyperframes-bridge] clip ${clip.id || "(无 id)"} 没有 data-variable-values 属性 ` +
        "(path_b_build 未发射该镜?)"
    );
  }
  try {
    const parsed: unknown = JSON.parse(raw);
    // 编译期已契约化 (HookVariables), 运行时只校验最关键的字段名即可
    if (typeof parsed !== "object" || parsed === null) {
      throw new Error("data-variable-values is not a JSON object");
    }
    return parsed as HookVariables;
  } catch (e) {
    throw new Error(
      `[hyperframes-bridge] failed to parse data-variable-values JSON: ` +
        (e instanceof Error ? e.message : String(e))
    );
  }
}