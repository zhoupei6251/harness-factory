<script setup lang="ts">
/**
 * field · none 态 —— 「画面主导镜」在没有影像时该长什么样。
 *
 * 设计主张（探针证据 routes/news/evidence/2026-10-16-field-proto.md）：
 * 无图**不是留一个空洞**，而是让本镜最关键的事实当画面主体（`ghost` 巨号 12% 墨），
 * 配斜纹地面 + 顶部径向光撑住 0–64cqh，底部文字带坐在字幕禁入区上方。
 *
 * 图态（real / schematic）本轮刻意不做：影像供给实测 0/9 可用，
 * 变量没数据源就写进契约 = 造一个没人喂数据的死接口。供给那条等拍定再加。
 *
 * 三处已定改动来自探针目视：
 *   ① 眉标位只放事件/栏目词 —— 代码里不写"无图"类自证文案（那是道歉，且观众本来不知道）；
 *   ② ghost 放大并垂直居中在画面区，压掉探针那版 36–62cqh 的空带；
 *   ③ 通用文字阴影只给文字层，不给 ghost —— 否则 12% 水印会被两层阴影打成实黑
 *      （静态支那条 `#root > *:not(...)` 就是这个病，见 spec §3-A）。
 *
 * 色值一律 var(--cNN)，不写 hex、不写回退值 —— 槽位由发射器按包注入在 clip 上。
 * 动效目标全部走模板 ref（clip 作用域契约）：不引 id 选择器字符串、不碰 document。
 * 时间轴注册键 = loader 传进来的 compositionId，写死包级字面量会让重复版式的两镜共键。
 */
import { computed, onMounted, ref } from "vue";
import { gsap } from "../../lib/gsap-runtime";
import { readVariables } from "../../lib/hyperframes-bridge";

interface FieldVariables {
  kicker: string;
  ghost: string;
  place: string;
  title: string;
  onscreen: string;
  slotSeconds: number;
}

const props = defineProps<{ compositionId: string; clip: HTMLElement }>();

const vars = ref<Partial<FieldVariables>>(readVariables(props.clip));
const slot = computed(() => Number(vars.value.slotSeconds) || 4);

const chipEl = ref<HTMLElement>();
const ghostEl = ref<HTMLElement>();
const placeEl = ref<HTMLElement>();
const ruleEl = ref<HTMLElement>();
const titleEl = ref<HTMLElement>();
const subEl = ref<HTMLElement>();
const fieldEl = ref<HTMLElement>();

onMounted(() => {
  // 动量预算（frame.md §4）：入场 ≤1.5s，之后持续呼吸，不留静止尾巴
  const INTRO_END = 1.5;
  const MIN_DRIFT = 0.6;
  const driftStart = Math.max(0, Math.min(INTRO_END, slot.value - MIN_DRIFT));
  const driftDur = Math.max(MIN_DRIFT, slot.value - driftStart);

  const tl = gsap.timeline({ paused: true });

  // 法则 8：自带 background 的面一律 scaleX/scaleY 擦入，禁止 opacity
  tl.fromTo(chipEl.value!, { scaleX: 0 }, { scaleX: 1, duration: 0.45, ease: "power2.out" }, 0.1);
  tl.fromTo(ruleEl.value!, { scaleX: 0 }, { scaleX: 1, duration: 0.5, ease: "power2.out" }, 0.8);
  // 墨（无底色的文字）才用 opacity
  tl.fromTo(ghostEl.value!, { opacity: 0, yPercent: 6 },
    { opacity: 1, yPercent: 0, duration: 0.9, ease: "power2.out" }, 0.15);
  tl.fromTo(placeEl.value!, { opacity: 0 }, { opacity: 1, duration: 0.6 }, 0.7);
  tl.fromTo(titleEl.value!, { opacity: 0, y: 26 },
    { opacity: 1, y: 0, duration: 0.5, ease: "power2.out" }, 0.95);
  tl.fromTo(subEl.value!, { opacity: 0, y: 18 },
    { opacity: 1, y: 0, duration: 0.45, ease: "power2.out" }, 1.2);

  // 呼吸：ghost 与文字带反向微移，画面一直在动但不出血
  tl.to(ghostEl.value!, { yPercent: -2.2, duration: driftDur, ease: "none" }, driftStart);
  tl.to(fieldEl.value!, { yPercent: -1.2, duration: driftDur, ease: "none" }, driftStart);

  window.__timelines = window.__timelines ?? {};
  window.__timelines[props.compositionId] = tl;
});
</script>

<template>
  <div class="fd-root">
    <div class="fd-stage">
      <div ref="ghostEl" class="fd-ghost" data-layout-ignore="true">{{ vars.ghost }}</div>
      <div ref="placeEl" class="fd-place">{{ vars.place }}</div>
    </div>
    <div ref="chipEl" class="fd-kicker">{{ vars.kicker }}</div>
    <div ref="fieldEl" class="fd-copy">
      <div ref="ruleEl" class="fd-rule"></div>
      <div ref="titleEl" class="fd-title">{{ vars.title }}</div>
      <div ref="subEl" class="fd-sub">{{ vars.onscreen }}</div>
    </div>
  </div>
</template>

<style>
/* 不写 hex、不写 var() 回退值：色位由发射器按包注入在 clip 的 style 上。
   类名一律 fd- 前缀 —— Vite 打出的 CSS 是全局的，没有 scoped 属性可依赖。 */
.fd-root {
  position: absolute;
  inset: 0;
  overflow: hidden;
  container-type: size;
  background: var(--c0);
  color: var(--c1);
  font-family: "HF CJK", sans-serif;
}
/* 画面区 0–64cqh：斜纹 + 顶部径向光撑住，不留空洞 */
.fd-stage {
  position: absolute;
  inset: 0 0 36cqh 0;
  overflow: hidden;
  background:
    repeating-linear-gradient(135deg,
      rgba(232, 93, 93, 0.075) 0 1.6cqw, transparent 1.6cqw 4.2cqw),
    radial-gradient(120% 78% at 50% 8%, rgba(232, 93, 93, 0.16), transparent 62%);
}
/* 事实当主体：巨号 12% 墨，与 story 的序号水印同一套语言。
   ⚠ 这一层拿不到文字阴影 —— 两层黑阴影会把 12% 填充叠成实黑（spec §3-A）。 */
.fd-ghost {
  /* 12% 水印是装饰层（frame.md §壁纸序号），必须带 data-layout-ignore="true"：
     少了它，`check --strict` 会按正文对比度判这条巨号字（实测 1.31:1 ⇒ 整片被拒渲染）。 */
  position: absolute;
  left: 6cqw;
  top: 50%;
  transform: translateY(-50%);
  font-family: "League Gothic", sans-serif;
  font-size: 30cqw;
  line-height: 0.84;
  letter-spacing: -0.01em;
  color: var(--c7);
  white-space: nowrap;
  pointer-events: none;
}
.fd-place {
  position: absolute;
  left: 6.4cqw;
  bottom: 6cqh;
  font-family: "JetBrains Mono", monospace;
  font-size: 3.1cqw;
  letter-spacing: 0.22em;
  color: var(--c6);
}
/* 眉标片：白片 + 共享强调色字（3.41，大字号过 AA）。自带底色 ⇒ 只做 scaleX 擦入 */
.fd-kicker {
  position: absolute;
  left: 6cqw;
  top: 6cqh;
  background: var(--c2);
  color: var(--c3);
  font-family: "JetBrains Mono", monospace;
  font-size: 2.7cqw;
  font-weight: 700;
  letter-spacing: 0.16em;
  padding: 0.9cqh 1.8cqw;
  transform-origin: 0% 50%;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.7), 0 0 1px rgba(0, 0, 0, 0.5);
}
/* 文字带：底边坐在 20cqh 字幕禁入区上方（法则 1，量出来的数） */
.fd-copy {
  position: absolute;
  left: 6cqw;
  right: 6cqw;
  bottom: 22cqh;
  display: flex;
  flex-direction: column;
  gap: 2.2cqh;
}
.fd-rule {
  width: 18cqw;
  height: 0.55cqh;
  background: var(--c4);
  transform-origin: 0% 50%;
}
.fd-title {
  font-size: 8.4cqw;
  font-weight: 900;
  line-height: 1.2;
  letter-spacing: -0.01em;
  max-width: 88cqw;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.7), 0 0 1px rgba(0, 0, 0, 0.5);
}
.fd-sub {
  font-size: 4.1cqw;
  font-weight: 400;
  line-height: 1.45;
  color: var(--c5);
  max-width: 88cqw;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.7), 0 0 1px rgba(0, 0, 0, 0.5);
}
</style>
