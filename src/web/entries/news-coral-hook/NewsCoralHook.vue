<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { gsap } from "../../lib/gsap-runtime";
import { readVariables } from "../../lib/hyperframes-bridge";
import type { HookVariables } from "../../lib/data.contract";

/**
 * news-coral · hook
 *
 * 迁移自 skills/douyin-pro/templates/hyperframes_path_b/news-coral/compositions/hook.html
 * 保持与原版字节级一致：DOM 结构 / CSS / GSAP timeline / 数据占位契约。
 *
 * 数据流：mount → readBridge().getVariables() → reactive vars → DOM 重新渲染
 * （原版 inline <script> 在模板加载后执行同位置；这里等价）
 */

const vars = ref<Partial<HookVariables>>({});
const hasPhoto = computed(() =>
  Boolean(String(vars.value.imagePath ?? "").trim())
);
const slot = computed(() => Number(vars.value.slotSeconds) || 4);

onMounted(() => {
  vars.value = readVariables();

  // 动量预算（frame.md §4，与原 hook.html 字面同值）
  const INTRO_END = 1.5;
  const MIN_DRIFT = 0.6;
  const driftStart = Math.max(0, Math.min(INTRO_END, slot.value - MIN_DRIFT));
  const driftDur = Math.max(MIN_DRIFT, slot.value - driftStart);

  const tl = gsap.timeline({ paused: true });

  // 入场（法则 8：自带 background 一律 scaleX/scaleY，禁止 opacity）
  tl.fromTo("#h-band", { scaleY: 0 }, { scaleY: 1, duration: 0.5, ease: "power3.out" }, 0);
  tl.fromTo("#h-eb", { scaleX: 0 }, { scaleX: 1, duration: 0.4, ease: "power2.out" }, 0.3);
  tl.fromTo("#h-ac", { scaleX: 0 }, { scaleX: 1, duration: 0.4, ease: "power2.out" }, 0.82);
  tl.fromTo("#h-hair", { scaleX: 0 }, { scaleX: 1, duration: 0.45, ease: "power2.out" }, 1.05);
  tl.fromTo("#h-sup", { opacity: 0, y: 22 }, { opacity: 1, y: 0, duration: 0.4 }, 1.25);

  // 呼吸：整镜剩余时间持续位移
  tl.to("#h-field", { yPercent: -3, duration: driftDur, ease: "none" }, driftStart);
  tl.to("#h-eb", { y: 12, duration: driftDur, ease: "none" }, driftStart);

  // 真实图板（法则 8 例外：asset/img 可用 opacity）
  if (hasPhoto.value) {
    const img = document.getElementById("hk-img") as HTMLImageElement | null;
    const credit = document.getElementById("hk-credit");
    if (img) img.src = String(vars.value.imagePath ?? "");
    if (credit) {
      credit.textContent =
        String(vars.value.imageCredit ?? "") || "图源：Wikimedia Commons";
    }
    tl.fromTo("#hk-img", { opacity: 0 }, { opacity: 1, duration: 0.8, ease: "power2.out" }, 0);
    tl.to("#hk-img", { scale: 1.08, duration: driftStart + driftDur, ease: "power1.inOut" }, 0);
  }

  window.__timelines = window.__timelines ?? {};
  window.__timelines["nc-night-hook"] = tl;
});
</script>

<template>
  <div
    id="root"
    :class="{ 'has-photo': hasPhoto }"
    data-composition-id="nc-night-hook"
    data-width="1080"
    data-height="1920"
  >
    <div class="h-band" id="h-band"></div>
    <div class="h-eb" id="h-eb" data-var-text="kicker">{{ vars.kicker ?? "NEWS" }}</div>
    <div class="h-field" id="h-field">
      <div class="h-hd">
        <div id="h-l1" data-var-text="headTop">{{ vars.headTop ?? "标题第一行" }}</div>
        <div>
          <span id="h-l2" data-var-text="headBottomLead">{{ vars.headBottomLead ?? "第二行" }}</span><span
            class="h-ac"
            id="h-ac"
            data-var-text="headAccent"
            >{{ vars.headAccent ?? "强调" }}</span
          >
        </div>
      </div>
      <div class="h-hair" id="h-hair"></div>
      <div class="h-sup" id="h-sup" data-var-text="support">{{ vars.support ?? "辅助信息" }}</div>
    </div>
    <figure
      v-if="hasPhoto"
      class="hk-photo"
      id="hk-photo"
      data-layout-allow-overflow
    >
      <img
        class="hk-photo-img"
        id="hk-img"
        data-layout-allow-overflow
        alt=""
      />
    </figure>
    <figcaption class="hk-photo-credit" id="hk-credit">图源：Wikimedia Commons</figcaption>
  </div>
</template>

<style>
  /* unscoped: 原 hook.html 的所有 CSS 走全局（@font-face / 通用选择器不能 scoped）
     改色先改 src/web/lib/tokens/coral.ts，再重跑 audit_pack_contrast.py */
  @font-face {
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
  #root {
    position: absolute;
    inset: 0;
    overflow: hidden;
    background: #0a0a0d;
    color: #f5f0e8;
    font-family: "HF CJK", sans-serif;
  }
  /* 通用文字阴影：让任何深浅底图上的文字都自带暗晕，WCAG AA 对比度兜底 */
  #root > *:not([class$="-photo"]):not([class$="-photo-credit"]) {
    z-index: 1;
    text-shadow: 0 1px 3px rgba(0, 0, 0, 0.7), 0 0 1px rgba(0, 0, 0, 0.5);
  }
  .h-band {
    position: absolute;
    inset: 0 0 auto 0;
    height: 22cqh;
    background: #c0392b;
    transform-origin: 50% 0%;
    z-index: 1;
  }
  .h-band::before {
    content: "";
    position: absolute;
    inset: 0;
    background-image: repeating-linear-gradient(
      45deg,
      transparent 0 20px,
      rgba(0, 0, 0, 0.06) 20px 40px
    );
    pointer-events: none;
  }
  .h-eb {
    position: absolute;
    left: 6cqw;
    top: 17cqh;
    background: #ffffff;
    color: #e85d5d;
    font-family: "JetBrains Mono", monospace;
    font-size: 2.9cqw;
    font-weight: 700;
    letter-spacing: 0.16em;
    padding: 1cqh 2cqw;
    transform-origin: 0% 50%;
    z-index: 2;
  }
  .h-field {
    position: absolute;
    inset: 22cqh 0 20cqh 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 0 6cqw;
    z-index: 2;
  }
  .h-hd {
    font-size: 10.5cqw;
    font-weight: 900;
    line-height: 1.24;
    letter-spacing: -0.01em;
    max-width: 88cqw;
  }
  .h-ac {
    display: inline-block;
    background: #c0392b;
    color: #ffffff;
    padding: 0 1.4cqw;
    transform-origin: 0% 50%;
  }
  .h-hair {
    width: 14cqw;
    height: 1.1cqh;
    background: #c0392b;
    margin: 3.6cqh 0;
    transform-origin: 0% 50%;
  }
  .h-sup {
    font-size: 3.9cqw;
    font-weight: 400;
    /* #dcdcdc 在 h-sup 区（mask 0.45 alpha + 中等亮图）实测对比度 ≥ 3.7:1 */
    color: #dcdcdc;
    max-width: 74cqw;
  }
  .hk-photo {
    position: absolute;
    inset: 0;
    margin: 0;
    padding: 0;
    background: transparent;
    overflow: hidden;
    z-index: 0;
    transform-origin: 50% 50%;
  }
  .hk-photo::before {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(
      180deg,
      rgba(0, 0, 0, 0.55) 0%,
      rgba(0, 0, 0, 0) 22%,
      rgba(0, 0, 0, 0) 55%,
      rgba(0, 0, 0, 0.45) 78%,
      rgba(0, 0, 0, 0.75) 100%
    );
    pointer-events: none;
  }
  .hk-photo-img {
    width: 100%;
    height: 100%;
    display: block;
    object-fit: cover;
    transform: scale(1.02);
    transform-origin: 50% 50%;
  }
  .hk-photo-credit {
    position: absolute;
    top: 17cqh;
    right: 6cqw;
    z-index: 3;
    font-family: "JetBrains Mono", monospace;
    font-size: 1.4cqw;
    line-height: 1.3;
    letter-spacing: 0.08em;
    color: rgb(255, 255, 255);
    background: rgba(0, 0, 0, 0.7);
    padding: 0.5cqh 1.4cqw;
    text-align: right;
  }
  /* 图作为底后，标题与辅助行从满屏宽缩到左半 */
  .has-photo .h-hd { max-width: 56cqw; }
  .has-photo .h-sup { max-width: 56cqw; }
</style>