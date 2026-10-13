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

/** 单 composition 的 id —— 与 NewsCoralHook.vue 顶部 data-composition-id 一致 */
export const COMPOSITION_ID = "nc-night-hook";

export function readVariables(): HookVariables {
  if (typeof document === "undefined") {
    throw new Error(
      "[hyperframes-bridge] document not available (SSR? POC 仅支持客户端 mount)"
    );
  }
  const mount = document.querySelector<HTMLElement>(
    `[data-composition-id="${COMPOSITION_ID}"]`
  );
  if (!mount) {
    throw new Error(
      `[hyperframes-bridge] no element with data-composition-id="${COMPOSITION_ID}". ` +
        "host.html must mount this composition via path_b_build.MOUNT_TPL."
    );
  }
  const raw = mount.dataset.variableValues;
  if (!raw) {
    throw new Error(
      `[hyperframes-bridge] [data-composition-id="${COMPOSITION_ID}"] ` +
        "has no data-variable-values attribute (path_b_build not run?)"
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