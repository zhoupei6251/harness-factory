/**
 * news-coral 色板常量 · 唯一 token 源（迁移自 frame.md §1）
 *
 * 改色板先改这里，再重跑 audit_pack_contrast.py 复算 13 条对比度。
 * 颜色十六进制必须与 frame.md §1 字面值一致 —— 偏差 1 字符即触发
 * DOC_RATIO_DRIFT 断言。
 */

export const CORAL_TOKENS = {
  coral: "#E85D5D",
  "coral-dark": "#D44A4A",
  cream: "#F5F0E8",
  "cream-dark": "#E8E0D4",
  ink: "#1A1A1A",
  gray: "#6B6B6B",
  "light-gray": "#B0B0B0",
  white: "#FFFFFF",
} as const satisfies Record<string, `#${string}`>;

export type CoralToken = keyof typeof CORAL_TOKENS;

/** WCAG 2.x 相对亮度公式 */
function channelLuminance(c: number): number {
  const s = c / 255;
  return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
}

/** 取色值 sRGB 相对亮度 L */
export function relativeLuminance(hex: `#${string}`): number {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return (
    0.2126 * channelLuminance(r) +
    0.7152 * channelLuminance(g) +
    0.0722 * channelLuminance(b)
  );
}

/** WCAG 对比度比值 (L1+0.05) / (L2+0.05) */
export function contrastRatio(fg: `#${string}`, bg: `#${string}`): number {
  const L1 = Math.max(relativeLuminance(fg), relativeLuminance(bg));
  const L2 = Math.min(relativeLuminance(fg), relativeLuminance(bg));
  return (L1 + 0.05) / (L2 + 0.05);
}

/**
 * news-coral §1.1 对比度实测表的复算自检函数
 *
 * 用于 verify 时断言：Vue 端常量与 frame.md §1.1 表格数字一致
 * （frame.md 是事实源；这里只是编译期 smoke，本文件改色必须先改 frame.md）。
 */
export const CORAL_CONTRAST_REFERENCE = {
  "cream/ink": 15.34,
  "light-gray/ink": 8.03,
  "gray/ink": 3.27,
  "coral/ink": 5.1,
  "ink/coral": 5.1,
  "white/coral": 3.41,
  "white/coral-dark": 4.31,
  "coral/white": 3.41,
  "ink/white": 17.4,
  "gray/white": 5.33,
  "ink/cream": 15.34,
  "gray/cream": 4.7,
  "coral/cream": 3.01,
  "ink/cream-dark": 13.3,
} as const;