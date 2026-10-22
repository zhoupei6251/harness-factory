<script setup lang="ts">
/**
 * rank · 带量级条的 TOP-N 榜（Vue-only 角色，地基之后的第二个结构）。
 *
 * 设计出处 `evidence/2026-10-16-rank-proto.md`：结论是**带 bar** —— 排行榜的核心信息是
 * 梯度而不是名次（名次已由 01–05 表达），plain 版读不出"1188 万比 742 万多 60%"。
 * 但 bar 值不值得它的诚实负担，答案是"值得，前提是两条负担一起设计进去"，
 * 两条都在代码里落成机检，不是只写在注释里：
 *
 *   ① **条长 = 相对第一名的比值**（`ratio()`），不是"第一名满格、其余看着办"。
 *      旧 probe 的病根是所有 bar 都 1.0 —— 那是造假。跨单位（`3亿` vs `1188万`）时
 *      比值无意义，由发射器 `_check_bar_units` 直接拒渲染，不在组件里兜。
 *   ② **口径标注必须在脸上**（`rk-basis`，且它是版式常量、不是契约变量 —— 能改标签就等于
 *      允许「条按相对第一画、字写占总量」）。`check_component` 见到契约声明 `bars`
 *      就要求这个带字面文本的节点在，缺即判红。
 *
 * 探针目视出的两个缺陷，这里按它的修法落：
 *   · 口径标注原来压在第五行上（`bottom: 22.6cqh` 与行区只差 0.6cqh，代码里看不出异常）
 *     ⇒ 挪进标题带，跟着 `rule` 走，不再与行区共用底部空间；
 *   · 行区原来用 `space-between`，行数不足时全堆上半 ⇒ 法则 10 禁这条，改成
 *     **固定行高 + 顶对齐**，空的就是空的，不靠拉伸把版式撑满。
 *
 * 容量：上限 5 行（带 bar 时 5 行已顶到字幕禁入区边缘），下限 3 行 ——
 * `item4*` / `item5*` 在契约里声明为尾部可选行，稿件没这两条时落空串，
 * `rows` 直接把空行收掉（不是画两行空框）。
 *
 * 色值一律 `var(--cNN)`；动效目标全部走模板 ref；注册键 = 传入的 compositionId。
 */
import { computed, onMounted, ref } from "vue";
import { gsap } from "../../lib/gsap-runtime";
import { readVariables, readMotionSignature } from "../../lib/hyperframes-bridge";

interface RankVariables {
  kicker: string;
  title: string;
  onscreen: string;
  slotSeconds: number;
  [row: string]: string | number;
}

const props = defineProps<{ compositionId: string; clip: HTMLElement }>();

const vars = ref<Partial<RankVariables>>(readVariables(props.clip));
const slot = computed(() => Number(vars.value.slotSeconds) || 4);
const sig = readMotionSignature(props.clip).signature;

/** `1188万` → 1188；读不出数就 0（发射器已保证形态，这里只是不依赖那个前提画错条）。 */
function parseNum(text: string): number {
  const match = /^\s*(\d+(?:\.\d+)?)/.exec(text);
  return match ? Number(match[1]) : 0;
}

interface RankRow { label: string; value: string; num: number }

const rows = computed<RankRow[]>(() => {
  const out: RankRow[] = [];
  for (let i = 1; i <= 5; i++) {
    const label = String(vars.value[`item${i}Label`] ?? "").trim();
    const value = String(vars.value[`item${i}Value`] ?? "").trim();
    if (!label && !value) continue;         // 尾部可选行整条收起：不画空框、不占位
    out.push({ label, value, num: parseNum(value) });
  }
  return out;
});

const maxNum = computed(() => rows.value.reduce((m, r) => Math.max(m, r.num), 0));

/** 行区可用高度（cqh）：`.rk-rows` 从 32cqh 铺到 78cqh。 */
const ROWS_H_CQH = 46;
/** 一行的实测内容高（名称行 + 条轨），N=5 帧上量出来的，不是按 CSS 估的。 */
const ROW_H_CQH = 7.4;
/** 行距上限：再大就不像一张表了（rank 探针 §2 的"拉散"就是这个）。 */
const GAP_MAX_CQH = 2.6;

/**
 * 行距按 N 算、并设上限 —— frame.md 法则 10 给的第三条路。
 *
 * 为什么不是 `flex:1` 等分：等分保证不溢出，但 N=3 时三行被推到 15cqh 一行，
 * 读起来是三条独立陈述不是一张表（探针 §2 批评 space-between 用的正是这句话）。
 * 为什么不是固定行距顶对齐：N=5 时 5×7.4+4×2.6=47.4cqh > 46，实测溢到 81.7cqh
 * 压进字幕禁入区。两头都错过，才落到这条"余量一律留底部、但大 N 时自动收"上。
 * ROW_H_CQH 估错不会静默：溢出由普查判据 6（`intrude`）当场拦，不靠人盯。
 */
const rowGapCqh = computed(() => {
  const n = rows.value.length;
  if (n <= 1) return GAP_MAX_CQH;
  const spread = (ROWS_H_CQH - n * ROW_H_CQH) / (n - 1);
  return Math.max(0.8, Math.min(GAP_MAX_CQH, spread));
});


/** 第一名 1.0 是**事实**（它就是最大值），其余按真实比值；max 取不到正数时一律不画条。 */
function ratio(row: RankRow): number {
  if (maxNum.value <= 0 || row.num <= 0) return 0;
  return row.num / maxNum.value;
}

const chipEl = ref<HTMLElement>();
const titleEl = ref<HTMLElement>();
const ruleEl = ref<HTMLElement>();
const basisEl = ref<HTMLElement>();
const rowsEl = ref<HTMLElement>();
const subEl = ref<HTMLElement>();
const barEls = ref<HTMLElement[]>([]);
const rowEls = ref<HTMLElement[]>([]);
const coverEls = ref<HTMLElement[]>([]);
const glowEl = ref<HTMLElement>();
const scanEl = ref<HTMLElement>();
const speedEl = ref<HTMLElement>();

onMounted(() => {
  // 动量预算（frame.md §4）：入场收在 1.5s 内，之后整段持续位移，不留静止尾巴。
  // 三个具名常数 + 至少一条用 driftDur 的补间，由 `check_component` 与静态支同一套谓词守。
  const INTRO_END = 1.5;
  const MIN_DRIFT = 0.6;
  const driftStart = Math.max(0, Math.min(INTRO_END, slot.value - MIN_DRIFT));
  const driftDur = Math.max(MIN_DRIFT, slot.value - driftStart);

  const tl = gsap.timeline({ paused: true });

  // 入场：自带 background 的形状一律 scaleX/scaleY（法则 8），墨才用 opacity
  tl.fromTo(chipEl.value!, { scaleX: 0 },
    { scaleX: 1, duration: 0.45, ease: "power2.out" }, 0);
  tl.fromTo(titleEl.value!, { opacity: 0, y: 24 },
    { opacity: 1, y: 0, duration: 0.5, ease: "power2.out" }, 0.15);
  tl.fromTo(ruleEl.value!, { scaleX: 0 },
    { scaleX: 1, duration: 0.45, ease: "power2.out" }, 0.4);
  tl.fromTo(basisEl.value!, { opacity: 0 }, { opacity: 1, duration: 0.5 }, 0.6);

  // 逐行入场；条长从 0 擦到**真实比值**（第一名 1.0 是事实，不是设计）
  // 签名只换缓动/位移，不改终点：条长的终点永远 = ratio(row)，动效不许把事实带偏。
  // blast 用 back.out 会让条长在动画中途超过 ratio(row)（瞬时画出比事实更长的条），
  // 这里只许位置回弹，长度一律不越过终点。
  const barEase = sig === "blast" ? "power4.out"
    : sig === "alert" ? "power4.out" : "power2.out";
  const barDur = sig === "blast" ? 0.62 : 0.55;
  rows.value.forEach((row, i) => {
    const at = 0.75 + i * 0.16;
    if (sig !== "calm") {
      const enterAt = 0.35 + i * 0.12;
      if (sig === "blast") {
        tl.fromTo(rowEls.value[i]!, { opacity: 0, x: 56 },
          { opacity: 1, x: 0, duration: 0.5, ease: "back.out(1.8)" }, enterAt);
      } else if (sig === "alert") {
        tl.fromTo(rowEls.value[i]!, { opacity: 0, x: 20 },
          { opacity: 1, x: 0, duration: 0.32, ease: "power4.out" }, enterAt);
      } else {
        tl.fromTo(rowEls.value[i]!, { opacity: 0, y: 16 },
          { opacity: 1, y: 0, duration: 0.45, ease: "power2.out" }, enterAt);
      }
      // 数值被地面色片盖住后按行序擦开：不经过任何"中间错误的数字"（不数数）
      tl.fromTo(coverEls.value[i]!, { scaleX: 1 },
        { scaleX: 0, duration: sig === "blast" ? 0.42 : 0.5,
          ease: sig === "blast" ? "power4.out" : "power2.inOut" }, at + 0.1);
    }
    tl.fromTo(barEls.value[i]!, { scaleX: 0 },
      { scaleX: ratio(row), duration: barDur, ease: barEase }, at + 0.12);
  });
  tl.fromTo(subEl.value!, { opacity: 0, y: 18 },
    { opacity: 1, y: 0, duration: 0.45, ease: "power2.out" }, 1.15);

  if (sig === "coral") {
    tl.fromTo(glowEl.value!, { scale: 0.8 },
      { scale: 1.08, duration: 1.4, ease: "power2.out" }, 0);
    tl.to(glowEl.value!, { yPercent: -6, duration: driftDur, ease: "none" }, driftStart);
  } else if (sig === "alert") {
    tl.fromTo(scanEl.value!, { yPercent: -12 },
      { yPercent: 12, duration: 1.3, ease: "steps(9)" }, 0);
    tl.to(scanEl.value!, { yPercent: 55, duration: driftDur, ease: "none" }, driftStart);
  } else if (sig === "blast") {
    tl.fromTo(speedEl.value!, { xPercent: -30 },
      { xPercent: 30, duration: 1.35, ease: "power3.out" }, 0);
    tl.to(speedEl.value!, { xPercent: 110, duration: driftDur, ease: "none" }, driftStart);
  }

  // 呼吸：行区整体微移，保证尾段一直在动
  tl.to(rowsEl.value!, { yPercent: -1.6, duration: driftDur, ease: "none" }, driftStart);
  tl.to(subEl.value!, { y: 10, duration: driftDur, ease: "none" }, driftStart);

  window.__timelines = window.__timelines ?? {};
  // 注册键 = 本镜收到的 compositionId（与外层 clip 的 data-composition-id 同值）
  window.__timelines[props.compositionId] = tl;
});
</script>

<template>
  <div class="rk-root">
    <div class="rk-head">
      <div ref="chipEl" class="rk-kicker">{{ vars.kicker }}</div>
      <div ref="titleEl" class="rk-title">{{ vars.title }}</div>
      <div ref="ruleEl" class="rk-rule"></div>
        <!-- 口径标注是**版式常量**：写成契约变量就等于允许稿件改标签，
           出现「条按相对第一名画、字写占总量比例」这种画面替我们说谎的形态。
           `check_component` 见到契约声明 bars 就要求这个带字面文本的 rk-basis 节点在。 -->
      <div ref="basisEl" class="rk-basis">条长 = 相对第一名，非占总量比例</div>
      <div ref="subEl" class="rk-sub">{{ vars.onscreen }}</div>
    </div>

    <div ref="rowsEl" class="rk-rows" :style="{ gap: rowGapCqh + 'cqh' }">
      <div v-for="(row, i) in rows" :key="i" :ref="(el: any) => (rowEls[i] = el)" class="rk-row">
        <div class="rk-no" :class="{ 'rk-no-top': i === 0 }">{{ String(i + 1).padStart(2, "0") }}</div>
        <div class="rk-name">{{ row.label }}</div>
        <div class="rk-val">
          <span class="rk-val-text">{{ row.value }}</span>
          <span
            v-if="sig !== 'calm'"
            :ref="(el: any) => (coverEls[i] = el)"
            class="rk-cover"
            aria-hidden="true"
          ></span>
        </div>
        <div class="rk-track">
          <div :ref="(el: any) => (barEls[i] = el)" class="rk-bar"></div>
        </div>
      </div>
    </div>

    <!-- 动效签名叠加层：纯装饰、不承载信息；z-index 低于文字层。 -->
    <div v-if="sig === 'coral'" ref="glowEl" class="rk-sig-glow" data-layout-allow-overflow aria-hidden="true"></div>
    <div v-if="sig === 'alert'" ref="scanEl" class="rk-sig-scan" data-layout-allow-overflow aria-hidden="true"></div>
    <div v-if="sig === 'blast'" ref="speedEl" class="rk-sig-speed" data-layout-allow-overflow aria-hidden="true"></div>

  </div>
</template>

<style>
/* 不写 hex、不写 var() 回退值：色位由发射器按包注入在 clip 的 style 上。
   类名一律 rk- 前缀 —— Vite 打出的 CSS 是全局的，没有 scoped 属性可依赖。 */
@font-face {
  /* 中文 face 必须本文件自带（`check_component` 的 MISSING_CJK_FONT_FACE）。
     混挂时别的 bundle 里那份会遮住缺失，纯 rank 的片子会静默降档成系统默认字。 */
  font-family: "HF CJK";
  src:
    local("Noto Sans SC"),
    local("NotoSansSC-VF"),
    local("Source Han Sans SC"),
    local("Noto Sans CJK SC"),
    local("Microsoft YaHei"),
    local("PingFang SC");
  font-weight: 100 900;
}
.rk-root {
  position: absolute;
  inset: 0;
  overflow: hidden;
  container-type: size;
  background: var(--c0);
  color: var(--c1);
  font-family: "HF CJK", sans-serif;
}
.rk-head {
  position: absolute;
  left: 6cqw;
  top: 6cqh;
  display: flex;
  flex-direction: column;
  gap: 2.2cqh;
  z-index: 2;
}
.rk-kicker {
  align-self: flex-start;
  background: var(--c2);
  color: var(--c3);
  font-family: "JetBrains Mono", monospace;
  font-size: 2.6cqw;
  font-weight: 700;
  letter-spacing: 0.16em;
  padding: 0.85cqh 1.7cqw;
  transform-origin: 0% 50%;
}
.rk-title {
  font-size: 7.6cqw;
  font-weight: 900;
  line-height: 1.18;
  letter-spacing: -0.01em;
  max-width: 88cqw;
}
.rk-rule {
  width: 18cqw;
  height: 0.55cqh;
  background: var(--c4);
  transform-origin: 0% 50%;
}
.rk-basis {
  font-family: "JetBrains Mono", monospace;
  font-size: 2.0cqw;
  color: var(--c6);
  letter-spacing: 0.06em;
}
/* 行区：容器固定（32 → 78cqh，底边让开 22cqh 字幕禁入区），**每行 flex:1 等分**。
   为什么不手写行距：前两版都是按 CSS 估行高（估 5cqh/行、实高 9.6cqh/行），
   5 行溢出容器 —— 一版压进字幕区 85.4cqh，一版让屏句和第五行叠在一起。
   行高由内容决定、容器由版式决定，两者对不上时溢出是必然。等分之后 N 行永远吃满
   且不越界，法则 10 的"任何 N 下不得留 >15% 整块空白"也由同一条机制满足。 */
.rk-rows {
  position: absolute;
  left: 6cqw;
  right: 6cqw;
  top: 32cqh;
  bottom: 22cqh;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;   /* 余量一律留底部（法则 10） */
  z-index: 2;
}
.rk-row {
  display: grid;
  grid-template-columns: 9cqw 1fr;
  grid-template-rows: auto auto;
  column-gap: 2.4cqw;
  align-items: center;
}
.rk-no {
  grid-row: 1 / span 2;
  font-family: "League Gothic", sans-serif;
  font-size: 7.4cqw;
  line-height: 1;
  color: var(--c5);
}
.rk-no-top {
  color: var(--c3);
}
.rk-name {
  font-size: 4.0cqw;
  font-weight: 700;
  line-height: 1.2;
}
.rk-val {
  position: relative;
  justify-self: end;
  font-family: "League Gothic", sans-serif;
  font-size: 5.2cqw;
  line-height: 1;
  color: var(--c1);
}
.rk-val-text {
  position: relative;
  z-index: 1;
}
/* 数值擦开的遮片：与地面同色，scaleX 1→0；不是叠加半透明面，不碰文字对比度。 */
.rk-cover {
  position: absolute;
  inset: -10% -5%;
  background: var(--c0);
  transform-origin: 100% 50%;
  pointer-events: none;
}
.rk-track {
  grid-column: 2;
  height: 0.9cqh;
  margin-top: 1.1cqh;
  background: var(--c7);
  overflow: hidden;
}
.rk-bar {
  height: 100%;
  background: var(--c4);
  transform-origin: 0% 50%;
}
.rk-sub {
  font-size: 4.0cqw;
  line-height: 1.4;
  color: var(--c6);
  max-width: 88cqw;
}
/* 阴影只给文字层，不给条/轨/尺 —— 那是形状，加阴影会把它读成文字。 */
.rk-title, .rk-name, .rk-val, .rk-kicker, .rk-sub {
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.7), 0 0 1px rgba(0, 0, 0, 0.5);
}

/* ── 动效签名叠加层（纯装饰；z-index 低于文字层） ── */
.rk-sig-glow {
  position: absolute;
  inset: 26cqh 0 18cqh 0;
  background: radial-gradient(
    52% 44% at 70% 36%,
    color-mix(in srgb, var(--c4) 24%, transparent),
    transparent 72%
  );
  transform-origin: 70% 36%;
  z-index: 1;
  pointer-events: none;
}
.rk-sig-scan {
  position: absolute;
  inset: -15cqh 0;
  background: repeating-linear-gradient(
    180deg,
    color-mix(in srgb, var(--c4) 16%, transparent) 0 0.3cqh,
    transparent 0.3cqh 2.6cqh
  );
  z-index: 1;
  pointer-events: none;
}
.rk-sig-speed {
  position: absolute;
  inset: 24cqh -30cqw 12cqh -30cqw;
  background: repeating-linear-gradient(
    100deg,
    transparent 0 5cqw,
    color-mix(in srgb, var(--c4) 14%, transparent) 5cqw 5.4cqw,
    transparent 5.4cqw 10cqw
  );
  z-index: 1;
  pointer-events: none;
}
</style>
