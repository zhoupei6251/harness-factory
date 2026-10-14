<script setup lang="ts">
import { onMounted, ref } from "vue";
import { gsap } from "../../lib/gsap-runtime";
import { readVariables } from "../../lib/hyperframes-bridge";
import type { HookVariables } from "../../lib/data.contract";

/**
 * hook-b —— news-policy · hook（红头文件版式，判据 0a 的孤簇）
 *
 * 迁移自 skills/douyin-pro/templates/hyperframes_path_b/news-policy/compositions/hook.html
 * 保持与原版一致：DOM 结构 / CSS / GSAP timeline（属性、时长、缓动、绝对起点逐条同值）
 * / 数据占位契约。变的只有两件事：颜色改吃 `var(--cNN)` 槽位，动效目标改走模板 ref。
 *
 * 为什么单独成簇：Phase 0 判据 0a 实测 7 个角色全部 2 簇 `[30, 1]`，孤簇一律
 * news-policy —— 它是唯一一个「结构也与其余 30 包不同」的 hook（公文蓝双书挡 + 烫金
 * 印章 + 衬线标题，且没有 photo 图板），所以不能塞进 hook-a 用 token 抹平。
 *
 * ## 槽位映射（`pack_slots.declaration_slot_indices` 机检）
 * 槽号 = hex 在源 hook.html 里的**出现序号**，而源文件顶部注释就写着色值
 * （「对 paper #F5EFE3」占了 c0），所以声明槽是 **c1…c11 连续但整体后移一位**。
 * 按位置从 c0 开始铺会整体错位一色 —— 这正是 `news-coral` 那边 c8/c9 陷阱的另一面。
 *
 * ## clip 作用域契约（与 hook-a 同源，`path_b_selftest.py` 机检）
 * 同一版式在一次渲染里会出现多次 ⇒ 每个实例的 DOM 完全重复。所以动效目标一律模板 ref，
 * 既不引 id 选择器字符串（GSAP 用 document 解析，会跨镜驱动每一镜），也不碰全局取节点。
 *
 * 本包无图板：`imagePath` / `imageCredit` 在 news-policy/hook 的变量契约里不存在，
 * 所以这里不读、不渲染 `<figure>`。
 */
const props = defineProps<{ compositionId: string; clip: HTMLElement }>();

const vars = ref<Partial<HookVariables>>(readVariables(props.clip));
const slot = Number(vars.value.slotSeconds) || 4;

const ebEl = ref<HTMLElement>();
const ruleEl = ref<HTMLElement>();
const goldEl = ref<HTMLElement>();
const l1El = ref<HTMLElement>();
const l2El = ref<HTMLElement>();
const acEl = ref<HTMLElement>();
const supEl = ref<HTMLElement>();
const fieldEl = ref<HTMLElement>();
const sealEl = ref<HTMLElement>();

onMounted(() => {
  // 动量预算（frame.md §5，与原 hook.html 字面同值：公文型漂移 0.7 起步）
  const INTRO_END = 1.5;
  const MIN_DRIFT = 0.7;
  const driftStart = Math.max(0, Math.min(INTRO_END, slot - MIN_DRIFT));
  const driftDur = Math.max(MIN_DRIFT, slot - driftStart);

  const tl = gsap.timeline({ paused: true });

  // 入场次序 = 公文的读序：眉标 → 双书挡 → 标题两行 → 强调片 → 施行日期
  // 每条属性 / 时长 / 缓动 / 绝对起点与 hook.html:171-180 逐字对应，只换目标来源。
  tl.fromTo(ebEl.value!, { scaleX: 0 }, { scaleX: 1, duration: 0.4, ease: "power2.out" }, 0.1);
  tl.fromTo(ruleEl.value!, { scaleX: 0 }, { scaleX: 1, duration: 0.55, ease: "power2.out" }, 0.28);
  tl.fromTo(goldEl.value!, { scaleX: 0 }, { scaleX: 1, duration: 0.6, ease: "power2.out" }, 0.5);
  tl.fromTo(l1El.value!, { opacity: 0, y: 52 }, { opacity: 1, y: 0, duration: 0.5, ease: "power3.out" }, 0.55);
  tl.fromTo(l2El.value!, { opacity: 0, y: 52 }, { opacity: 1, y: 0, duration: 0.5, ease: "power3.out" }, 0.72);
  tl.fromTo(acEl.value!, { scaleX: 0 }, { scaleX: 1, duration: 0.45, ease: "power2.out" }, 0.9);
  tl.fromTo(supEl.value!, { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.45 }, 1.12);

  // 呼吸：入场压进 INTRO_END，剩下的整段匀速
  tl.to(fieldEl.value!, { yPercent: -2.4, duration: driftDur, ease: "none" }, driftStart);
  tl.to(sealEl.value!, { yPercent: -9, duration: driftDur, ease: "none" }, driftStart);

  window.__timelines = window.__timelines ?? {};
  // 注册键 = 本镜收到的 compositionId（与外层 clip 的 data-composition-id 同值）。
  window.__timelines[props.compositionId] = tl;
});
</script>

<template>
  <div
    id="root"
    :data-composition-id="compositionId"
    data-width="1080"
    data-height="1920"
  >
    <div class="pk-seal" id="pk-seal" ref="sealEl" data-layout-ignore="true"></div>
    <div class="pk-eb" id="pk-eb" ref="ebEl" data-var-text="kicker">{{ vars.kicker ?? "新规" }}</div>
    <div class="pk-rule" id="pk-rule" ref="ruleEl"></div>
    <div class="pk-gold-rule" id="pk-gold-rule" ref="goldEl"></div>
    <div class="pk-field" id="pk-field" ref="fieldEl">
      <div class="pk-hd">
        <div id="pk-l1" ref="l1El" data-var-text="headTop">{{ vars.headTop ?? "标题第一行" }}</div>
        <div>
          <span id="pk-l2" ref="l2El" data-var-text="headBottomLead">{{ vars.headBottomLead ?? "第二行" }}</span><span
            class="pk-ac"
            id="pk-ac"
            ref="acEl"
            data-var-text="headAccent"
            >{{ vars.headAccent ?? "施行" }}</span
          >
        </div>
      </div>
      <div class="pk-sup" id="pk-sup" ref="supEl" data-var-text="support">{{ vars.support ?? "2026年10月1日施行" }}</div>
    </div>
  </div>
</template>

<style>
  /* unscoped: 原 hook.html 的 CSS 走全局（@font-face / 通用选择器不能 scoped）
     色值一律 `var(--cNN)`，槽位串由发射器挂在 clip 的 style 上（`pack_slots.slot_css`）。
     ⚠️ 这里从 c1 起、不是 c0 —— 源文件顶部注释里的纸色占掉了 c0。 */

  /* news-policy · hook — 首镜「红头文件」：公文蓝细双书挡 + 衬线大标题 + 烫金印章形 + 施行日期
     这一版式的全部色彩决定都来自 frame.md §2.1 的实测对比度（对 paper 纸色）：
     · cobalt / ink / gray 三档才允许承载文字。
     · gold 数学上过不了、crimson 虽够大字但按 §2 强制规则仍只作形状 ——
       所以两者只出现在印章环与发丝线上，这正是 frame.md「gold/crimson 永远只作文字以外元素」的来处。
     带 background 的面一律 scaleX 擦入、禁止 opacity（法则 7 + layout_selfcheck 不变量 5：
     半透明的片底会与地面混色，对比取样直接掉到 3:1 以下）。纯文字才允许淡入。
     几何（1cqw=10.8px / 1cqh=19.2px，画布 1080×1920）：
       眉标片 top 6cqh；双书挡 12cqh（粗 0.9cqh）+ 13.6cqh（烫金 0.35cqh）；
       正文区 `inset: 20cqh 7cqw 20cqh 7cqw` → 区高 60cqh（1152px）、盒宽 86cqw。
       内容最坏高度 = 标题 9cqw×1.18×3行(343px) + gap 3cqh(58) + 施行日期 3.6cqw×1.5×2行(117)
       = 518px ≪ 1152px → 漂移 yPercent -2.4 只吃掉 27px，距字幕禁入区仍有一整块余量（法则 1）。
     施行日期落在 `support`：发射器只从**屏句**取材（见 path_b_build._onscreen_phrase），
     所以脚本第 1 镜必须写一行「屏: 2026年10月1日施行」—— 日期是事实，不许版式自己编。 */
  @font-face {
    font-family: "HF Serif CJK";
    src:
      local("Noto Serif SC"),
      local("Source Han Serif SC"),
      local("SimSun"),
      local("Noto Serif CJK SC"),
      local("Songti SC"),
      local("思源宋体");
    font-weight: 100 900;
  }
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
    background: var(--c1);
    color: var(--c2);
    font-family: "HF Serif CJK", serif;
  }
  /* 公文纸纹：只在 background 里用 px（纹理尺度不参与排版，见 layout_selfcheck 例外表） */
  #root::after {
    content: "";
    position: absolute;
    inset: 0;
    background-image: repeating-linear-gradient(
      0deg,
      transparent 0 38px,
      rgba(31, 58, 104, 0.035) 38px 39px
    );
    pointer-events: none;
  }
  .pk-eb {
    position: absolute;
    left: 7cqw;
    top: 6cqh;
    background: var(--c3);
    color: var(--c4);
    font-family: "JetBrains Mono", monospace;
    font-size: 2.6cqw;
    font-weight: 700;
    letter-spacing: 0.18em;
    padding: 0.9cqh 1.8cqw;
    transform-origin: 0% 50%;
  }
  .pk-rule {
    position: absolute;
    left: 7cqw;
    right: 7cqw;
    top: 12cqh;
    height: 0.9cqh;
    background: var(--c5);
    transform-origin: 0% 50%;
  }
  .pk-gold-rule {
    position: absolute;
    left: 7cqw;
    right: 7cqw;
    top: 13.6cqh;
    height: 0.35cqh;
    background: var(--c6);
    transform-origin: 0% 50%;
  }
  .pk-seal {
    position: absolute;
    right: 9cqw;
    top: 17cqh;
    width: 15cqw;
    height: 15cqw;
    border: 0.55cqw solid var(--c7);
    border-radius: 50%;
    pointer-events: none;
  }
  .pk-field {
    position: absolute;
    inset: 20cqh 7cqw 20cqh 7cqw;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 3cqh;
  }
  .pk-hd {
    font-size: 9cqw;
    font-weight: 700;
    line-height: 1.18;
    color: var(--c8);
    max-width: 86cqw;
  }
  .pk-ac {
    display: inline-block;
    background: var(--c9);
    color: var(--c10);
    padding: 0 1.2cqw;
    transform-origin: 0% 50%;
  }
  .pk-sup {
    font-family: "HF CJK", sans-serif;
    font-size: 3.6cqw;
    font-weight: 400;
    line-height: 1.5;
    color: var(--c11);
    max-width: 74cqw;
  }
</style>
