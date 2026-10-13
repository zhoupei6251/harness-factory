/**
 * data.composition-variables 契约
 *
 * 对应 hook.html 顶部 `data-composition-variables` JSON 数组：
 *   kicker / headTop / headBottomLead / headAccent / support /
 *   imagePath / imageCredit / slotSeconds
 *
 * 字段名错（"headtop" vs "headTop"）在这里编译期就被 TS 拒收，
 * 不再走到渲染时才发现。这是迁移到 Vue 的核心收益之一。
 */

export interface HookVariables {
  kicker: string;
  headTop: string;
  headBottomLead: string;
  headAccent: string;
  support: string;
  imagePath: string;
  imageCredit: string;
  slotSeconds: number;
}

/** 编译期常量：8 个字段是 host.html 挂载契约的一部分，顺序也是版式读取顺序 */
export const HOOK_VARIABLE_IDS = [
  "kicker",
  "headTop",
  "headBottomLead",
  "headAccent",
  "support",
  "imagePath",
  "imageCredit",
  "slotSeconds",
] as const satisfies readonly (keyof HookVariables)[];