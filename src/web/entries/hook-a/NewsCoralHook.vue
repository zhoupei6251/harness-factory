<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { gsap } from "../../lib/gsap-runtime";
import { readVariables } from "../../lib/hyperframes-bridge";
import type { HookVariables } from "../../lib/data.contract";

/**
 * news-coral · hook
 *
 * 迁移自 skills/douyin-pro/templates/hyperframes_path_b/news-coral/compositions/hook.html
 * 保持与原版一致：DOM 结构 / CSS / GSAP timeline（属性、时长、缓动、绝对起点逐条同值）
 * / 数据占位契约。只有「目标怎么拿到」变了，见下面的 clip 作用域契约。
 *
 * 数据流：loader 传整个 clip（每次唯一 id="shot-N"）→ mount → readVariables(clip)
 * → vars → 渲染出本镜文案。本镜数据从传入的 clip 自身读，不再按 composition_id
 * 全局查找（spec §7 风险 9：同版式重复时全局查找只命中第一个）。
 *
 * ## clip 作用域契约（Phase 1 全部组件通用，`path_b_selftest.py` 机检）
 *
 * 同一次渲染里同一版式会出现两次以上（实测 20 镜样本 hook×7），Vue 把模板渲进各自
 * clip 的 `.vue-target` ⇒ **每个实例的 DOM 完全重复**（两棵树都有 `id="h-band"`）。
 * 于是两种「按全局取节点」的写法都错，而且错得不一样：
 *   ① 用 `document` 全局按 id 捞节点（getElementById 那一类）—— 只命中文档第一个，
 *     后挂载的实例会把自己的 imagePath 写进**前一镜**的 `<img>`：前一镜显示别人的图、
 *     本镜反而一张图都没有；
 *   ② 把补间目标写成以 `#` 开头的 id 选择器字符串（fromTo / to / from / set 的首参）——
 *     GSAP 用 `document` 解析选择器，命中的是**所有**同 id 节点，于是后注册的 timeline
 *     同时驱动前面每一镜，并按后镜的 slotSeconds 时序补间。
 * 正确写法（本文件采用）：动效目标与 photo 节点一律走**模板 ref**，每个实例只拿到自己
 * 子树里的元素；既不引 id 选择器字符串，也不碰 `document.*`。闸门
 * `t_components_scope_all_targets_to_their_own_clip` 逐行守这两条形。
 * ⚠️ 那条闸门是纯文本形检查、不跳注释 —— 所以本注释只描述被禁形态，不写死字面例子
 *   （写了就把自己判红）。真实反例见 task-2-report.md 的修复前取证段。
 *
 * vars 在 setup 期就读（原来在 onMounted 里读）：`<figure v-if="hasPhoto">` 必须在
 * **首次**渲染就出现，onMounted 时 `imgEl` / `creditEl` 这两个 ref 才拿得到节点。
 * 读的还是同一个 clip 的同一个属性，时序表一个数字没动。
 *
 * 时间轴登记键 = **loader 传进来的那个 compositionId**（Task 4）：发射器给每条 Vue 镜
 * 唯一的 `data-composition-id`（`vue_clip_id` = 包级 id + `__` + 挂载序号），loader 逐镜
 * `mod.mount(clip, compId)` 把它交下来。引擎契约（Task 2 Step 0 实测
 * `pollSubCompositionTimelines`）是「逐 `[data-composition-id]` 元素查
 * `__timelines[<该元素的 id>]`」⇒ 注册键必须等于本镜 id，两者都取传入值、都不写死。
 * 写死包级字面量会让重复版式的两镜共键：第二条注册覆盖第一条，
 * `fromTo` 的 immediateRender 把首镜压在 opacity:0（改前证据见 task-2-report.md）。
 */
const props = defineProps<{ compositionId: string; clip: HTMLElement }>();

const vars = ref<Partial<HookVariables>>(readVariables(props.clip));
const hasPhoto = computed(() =>
  Boolean(String(vars.value.imagePath ?? "").trim())
);
const slot = computed(() => Number(vars.value.slotSeconds) || 4);

// 动效 / photo 节点：全部是本实例自己的元素（clip 作用域契约）
const bandEl = ref<HTMLElement>();
const ebEl = ref<HTMLElement>();
const acEl = ref<HTMLElement>();
const hairEl = ref<HTMLElement>();
const supEl = ref<HTMLElement>();
const fieldEl = ref<HTMLElement>();
const imgEl = ref<HTMLImageElement>();
const creditEl = ref<HTMLElement>();

onMounted(() => {
  // 动量预算（frame.md §4，与原 hook.html 字面同值）
  const INTRO_END = 1.5;
  const MIN_DRIFT = 0.6;
  const driftStart = Math.max(0, Math.min(INTRO_END, slot.value - MIN_DRIFT));
  const driftDur = Math.max(MIN_DRIFT, slot.value - driftStart);

  const tl = gsap.timeline({ paused: true });

  // 入场（法则 8：自带 background 一律 scaleX/scaleY，禁止 opacity）
  // 每条的属性 / 时长 / 缓动 / 绝对起点与 hook.html:230-239 逐字对应，只换目标来源。
  // 节点在首次渲染就全部就位（vars 于 setup 读），所以 .value 必然有值；万一模板与动效
  // 表不一致，GSAP 会打 `GSAP target ... not found` ⇒ 普查的零 WARN 判据当场红，不会静默。
  tl.fromTo(bandEl.value!, { scaleY: 0 }, { scaleY: 1, duration: 0.5, ease: "power3.out" }, 0);
  tl.fromTo(ebEl.value!, { scaleX: 0 }, { scaleX: 1, duration: 0.4, ease: "power2.out" }, 0.3);
  tl.fromTo(acEl.value!, { scaleX: 0 }, { scaleX: 1, duration: 0.4, ease: "power2.out" }, 0.82);
  tl.fromTo(hairEl.value!, { scaleX: 0 }, { scaleX: 1, duration: 0.45, ease: "power2.out" }, 1.05);
  tl.fromTo(supEl.value!, { opacity: 0, y: 22 }, { opacity: 1, y: 0, duration: 0.4 }, 1.25);

  // 呼吸：整镜剩余时间持续位移
  tl.to(fieldEl.value!, { yPercent: -3, duration: driftDur, ease: "none" }, driftStart);
  tl.to(ebEl.value!, { y: 12, duration: driftDur, ease: "none" }, driftStart);

  // 真实图板（法则 8 例外：asset/img 可用 opacity）
  if (hasPhoto.value) {
    const img = imgEl.value;
    const credit = creditEl.value;
    if (img) img.src = String(vars.value.imagePath ?? "");
    if (credit) {
      credit.textContent =
        String(vars.value.imageCredit ?? "") || "图源：Wikimedia Commons";
    }
    tl.fromTo(imgEl.value!, { opacity: 0 }, { opacity: 1, duration: 0.8, ease: "power2.out" }, 0);
    tl.to(imgEl.value!, { scale: 1.08, duration: driftStart + driftDur, ease: "power1.inOut" }, 0);
  }

  window.__timelines = window.__timelines ?? {};
  // 注册键 = 本镜收到的 compositionId（与外层 clip 的 data-composition-id 同值）。
  // 不许退回字符串字面量 —— 闸门 t_bundle_identity_never_hardcoded（vue-build.test.ts）守着。
  window.__timelines[props.compositionId] = tl;
});
</script>

<template>
  <div
    id="root"
    :class="{ 'has-photo': hasPhoto }"
    :data-composition-id="compositionId"
    data-width="1080"
    data-height="1920"
  >
    <div class="h-band" id="h-band" ref="bandEl"></div>
    <div class="h-eb" id="h-eb" ref="ebEl" data-var-text="kicker">{{ vars.kicker ?? "NEWS" }}</div>
    <div class="h-field" id="h-field" ref="fieldEl">
      <div class="h-hd">
        <div id="h-l1" data-var-text="headTop">{{ vars.headTop ?? "标题第一行" }}</div>
        <div>
          <span id="h-l2" data-var-text="headBottomLead">{{ vars.headBottomLead ?? "第二行" }}</span><span
            class="h-ac"
            id="h-ac"
            ref="acEl"
            data-var-text="headAccent"
            >{{ vars.headAccent ?? "强调" }}</span
          >
        </div>
      </div>
      <div class="h-hair" id="h-hair" ref="hairEl"></div>
      <div class="h-sup" id="h-sup" ref="supEl" data-var-text="support">{{ vars.support ?? "辅助信息" }}</div>
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
        ref="imgEl"
        data-layout-allow-overflow
        alt=""
      />
    </figure>
    <figcaption class="hk-photo-credit" id="hk-credit" ref="creditEl">图源：Wikimedia Commons</figcaption>
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