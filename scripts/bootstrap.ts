#!/usr/bin/env node
import { readFile, writeFile, mkdir, copyFile, stat } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");

type Platform = "claude" | "codex" | "trae" | "workbuddy" | "qoder";
type Route = "code" | "novel" | "news";

const PLATFORMS: Platform[] = ["claude", "codex", "trae", "workbuddy", "qoder"];

const PLATFORM_DIR: Record<Platform, string> = {
  claude: ".claude",
  codex: ".codex",
  trae: ".trae",
  workbuddy: ".codebuddy",
  qoder: ".qoder",
};

// The auto-loaded entry file each platform natively reads. Projecting to
// platform dirs alone is not enough: each platform only auto-loads its own
// well-known entry point.
// Qoder shares Codex's AGENTS.md, so the two deltas are concatenated into the
// one native file rather than one overwriting the other.
const PLATFORM_NATIVE_ENTRY: Record<Platform, string> = {
  claude: "CLAUDE.md",
  codex: "AGENTS.md",
  qoder: "AGENTS.md",
  trae: ".trae/rules/project_rules.md",
  workbuddy: ".codebuddy/rules/project_rules.md",
};

const ROUTE_RUNTIME: Record<Route, string[]> = {
  code: ["specs", "plans", "decisions", "verifications"],
  novel: ["plans", "memory", "tracking"],
  news: ["plans", "memory", "articles"],
};

const ROUTE_BASE: Record<Route, string> = {
  code: ".ai-runtime-artifacts",
  novel: ".harness-novel-runtime",
  news: ".harness-news-runtime",
};

// Per-platform deltas for `templates/harness.template.md`. Each harness file
// is the SAME canonical §1-§6 rules with a platform-specific title, intro,
// §0 loading convention, §1 Tier 2+ backend, §4 load order, and cross-platform
// tail. Only ~30 lines of real per-platform variation across 130-line files.
interface HarnessDelta {
  title: string;
  intro: string;
  section_0: string; // full `## §0 ...` block; "" if absent (no trailing blank — template provides it)
  tier2_backend: string; // cell content for §1 row "实现" — without leading space (template provides the space)
  raise_note: string; // parenthetical after `**升档判据**` in §2, e.g. `（Tier 1 干到一半发现需要升档）` or "" if no note
  load_order: string; // full `**加载顺序**...` 3-line block
  cross_end: string; // full cross-platform tail (header + bullets)
}
const HARNESS_DELTAS: Record<"CLAUDE" | "AGENTS" | "GEMINI", HarnessDelta> = {
  CLAUDE: {
    title: "CLAUDE.harness.md — harness-factory 可分发 harness 规则",
    intro: [
      "> 本文件由 `harness-factory/scripts/install-into-project.ts` 在 other 模式下被目标项目 `@harness-factory/CLAUDE.harness.md` 引用。  ",
      "> 自包含：包含阶段门禁、Tier 1 分级流水线、证据段模板、加载规则。  ",
      "> 设计稿：[2026-10-10-tier1-pipeline-design.md](docs/superpowers/specs/2026-10-10-tier1-pipeline-design.md)",
    ].join("\n"),
    section_0: "",
    tier2_backend: " `claude-orchestration` + worktree 派发",
    raise_note: "（Tier 1 干到一半发现需要升档）",
    load_order: [
      "**加载顺序**（Claude Code 会话开始时）：",
      "1. `~/.claude/CLAUDE.md`（用户全局记忆）",
      "2. `<cwd>/CLAUDE.md`（项目根，**含本文件的 @import**）",
      "3. `~/.claude/rules/`（用户级 skill 自动发现）",
    ].join("\n"),
    cross_end: [
      "**5 端对应入口**（多端协作时各自加载）：",
      "- Claude Code: 项目根 `CLAUDE.md` 的 `@harness-factory/CLAUDE.harness.md`",
      "- Codex / Qoder: 项目根 `AGENTS.md` 的条件读 `harness-factory/AGENTS.harness.md`（若存在）",
      "- Trae / WorkBuddy: 同 Codex，由模型读 prompt 内指令",
      "- Gemini: 项目根 `GEMINI.md` 的条件读 `harness-factory/GEMINI.harness.md`（若存在）",
    ].join("\n"),
  },
  AGENTS: {
    title: "AGENTS.harness.md — harness-factory 可分发 harness 规则（Codex / Qoder 端）",
    intro: [
      "> 本文件由 `harness-factory/scripts/install-into-project.ts` 在 other 模式下被目标项目 `AGENTS.md` 条件读取。  ",
      "> 模型指令：若你正在阅读的目标项目 `AGENTS.md` 含「请读取 `harness-factory/AGENTS.harness.md`」指令，请按本文件规则工作。  ",
      "> 内容与 `CLAUDE.harness.md` 对齐；差异仅在 §0 模型对话头与 §4 加载入口（Codex/Qoder 读 `AGENTS.md` 入口，不用 `~/.claude/`）。  ",
      "> 设计稿：[2026-10-10-tier1-pipeline-design.md](docs/superpowers/specs/2026-10-10-tier1-pipeline-design.md)",
    ].join("\n"),
    section_0: [
      "## §0 Codex / Qoder 加载约定",
      "",
      "- Codex: 本机存在 `~/.codex/AGENTS.md` 优先；项目根 `AGENTS.md` 为入口",
      "- Qoder: 与 Codex 共用 `AGENTS.md` 入口（qoder 不区分）",
      "- 入口文件按其文字指令条件读取 `harness-factory/AGENTS.harness.md`（即本文件）；不存在则 fallback 到 `AGENTS.md` 自身内容",
      "- 模型与本文件交互：按 §1-§6 规则工作；不强制「加载 SKILL.md 前先声明」之类的 Claude Code 习惯",
    ].join("\n"),
    tier2_backend: " `omx ultrawork` 或对应编排",
    raise_note: "",
    load_order: [
      "**加载顺序**（Codex/Qoder 会话开始时）：",
      "1. `~/.codex/AGENTS.md`（用户全局）",
      "2. `<cwd>/AGENTS.md`（项目根，**含条件读取 `harness-factory/AGENTS.harness.md` 的指令**）",
      "3. 子目录按需加载",
    ].join("\n"),
    cross_end: [
      "**跨端协作**（多端同时工作）：",
      "- Claude Code: 项目根 `CLAUDE.md` 的 `@harness-factory/CLAUDE.harness.md`",
      "- Codex / Qoder / Trae / WorkBuddy: 项目根 `AGENTS.md` 条件读 `harness-factory/AGENTS.harness.md`（本文件）",
      "- Gemini: 项目根 `GEMINI.md` 条件读 `harness-factory/GEMINI.harness.md`",
    ].join("\n"),
  },
  GEMINI: {
    title: "GEMINI.harness.md — harness-factory 可分发 harness 规则（Gemini 端）",
    intro: [
      "> 本文件由 `harness-factory/scripts/install-into-project.ts` 在 other 模式下被目标项目 `GEMINI.md` 条件读取。  ",
      "> 模型指令：若你正在阅读的目标项目 `GEMINI.md` 含「请读取 `harness-factory/GEMINI.harness.md`」指令，请按本文件规则工作。  ",
      "> 内容与 `CLAUDE.harness.md` 对齐；差异仅在 §0 模型对话头与 §4 加载入口（Gemini 读 `GEMINI.md` 入口）。  ",
      "> 设计稿：[2026-10-10-tier1-pipeline-design.md](docs/superpowers/specs/2026-10-10-tier1-pipeline-design.md)",
    ].join("\n"),
    section_0: [
      "## §0 Gemini 加载约定",
      "",
      "- Gemini: 项目根 `GEMINI.md` 为入口；用户全局 `~/.gemini/GEMINI.md` 也可叠加",
      "- 入口文件按其文字指令条件读取 `harness-factory/GEMINI.harness.md`（即本文件）；不存在则 fallback 到 `GEMINI.md` 自身内容",
      "- 模型与本文件交互：按 §1-§6 规则工作；Gemini 习惯在描述中显式说明假设与边界，**保留这个习惯**",
    ].join("\n"),
    tier2_backend: "对应编排",
    raise_note: "",
    load_order: [
      "**加载顺序**（Gemini 会话开始时）：",
      "1. `~/.gemini/GEMINI.md`（用户全局，可选）",
      "2. `<cwd>/GEMINI.md`（项目根，**含条件读取 `harness-factory/GEMINI.harness.md` 的指令**）",
      "3. 子目录按需加载",
    ].join("\n"),
    cross_end: [
      "**跨端协作**（多端同时工作）：",
      "- Claude Code: 项目根 `CLAUDE.md` 的 `@harness-factory/CLAUDE.harness.md`",
      "- Codex / Qoder / Trae / WorkBuddy: 项目根 `AGENTS.md` 条件读 `harness-factory/AGENTS.harness.md`",
      "- Gemini: 项目根 `GEMINI.md` 条件读 `harness-factory/GEMINI.harness.md`（本文件）",
    ].join("\n"),
  },
};

function parseArgs(argv: string[]): { platform: Platform | "all"; route: Route } {
  let platform: Platform | "all" = "all";
  let route: Route = "code";
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--platform" && argv[i + 1]) {
      const p = argv[++i];
      if (p === "all" || (PLATFORMS as string[]).includes(p)) {
        platform = p as Platform | "all";
      } else {
        console.error(`Unknown platform: ${p}`);
        process.exit(1);
      }
    } else if (argv[i] === "--route" && argv[i + 1]) {
      const r = argv[++i];
      if (r === "code" || r === "novel" || r === "news") {
        route = r as Route;
      } else {
        console.error(`Unknown route: ${r}`);
        process.exit(1);
      }
    } else if (argv[i] === "-h" || argv[i] === "--help") {
      console.log("Usage: bootstrap.ts [--platform claude|codex|trae|workbuddy|qoder|all] [--route code|novel|news]");
      process.exit(0);
    }
  }
  return { platform, route };
}

function stripFrontmatter(markdown: string): string {
  const match = markdown.match(/^---\r?\n[\s\S]*?\r?\n---\r?\n/);
  return match ? markdown.slice(match[0].length) : markdown;
}

async function exists(path: string): Promise<boolean> {
  try {
    await stat(path);
    return true;
  } catch {
    return false;
  }
}

async function projectPlatform(plat: Platform): Promise<void> {
  const dst = resolve(ROOT, PLATFORM_DIR[plat], "rules");
  await mkdir(dst, { recursive: true });

  const platformEntry = resolve(ROOT, "platforms", plat, "rules", "ENTRY.md");
  const canonicalEntry = resolve(ROOT, "core/ENTRY.md");
  const usePlatform = await exists(platformEntry);
  await copyFile(usePlatform ? platformEntry : canonicalEntry, resolve(dst, "ENTRY.md"));
  await copyFile(resolve(ROOT, "ENTRY.md"), resolve(dst, "ROOT.md"));
  console.log(`[ok] ${plat}: ${PLATFORM_DIR[plat]}/rules/ (entry source: ${usePlatform ? "platform-specific" : "canonical"})`);
}

async function projectNativeEntry(plats: Platform[]): Promise<void> {
  const entryPath = PLATFORM_NATIVE_ENTRY[plats[0]];
  const generatedNotice = `<!-- Generated by \`npm run bootstrap\` — do not edit. Edit core/ + platforms/ and re-run bootstrap. -->\n\n`;
  let body = stripFrontmatter(await readFile(resolve(ROOT, "ENTRY.md"), "utf-8"));
  body += "\n---\n\n" + stripFrontmatter(await readFile(resolve(ROOT, "core/ENTRY.md"), "utf-8"));
  for (const plat of plats) {
    const delta = resolve(ROOT, "platforms", plat, "rules", "ENTRY.md");
    if (!(await exists(delta))) continue;
    body += "\n---\n\n" + stripFrontmatter(await readFile(delta, "utf-8"));
  }
  const dst = resolve(ROOT, entryPath);
  await mkdir(dirname(dst), { recursive: true });
  await writeFile(dst, generatedNotice + body, "utf-8");
  console.log(`[ok] ${plats.join(" + ")}: native entry ${entryPath}`);
}

/** Platforms sharing one native entry file (codex + qoder on AGENTS.md) are merged. */
function groupByNativeEntry(plats: Platform[]): Platform[][] {
  const byEntry = new Map<string, Platform[]>();
  for (const plat of plats) {
    const group = byEntry.get(PLATFORM_NATIVE_ENTRY[plat]);
    if (group) group.push(plat);
    else byEntry.set(PLATFORM_NATIVE_ENTRY[plat], [plat]);
  }
  return [...byEntry.values()];
}

async function projectRoute(route: Route): Promise<void> {
  const src = resolve(ROOT, "routes", route, "MEMORY.md");
  if (!(await exists(src))) {
    console.log(`[skip] route ${route}: no routes/${route}/MEMORY.md yet`);
    return;
  }
  await copyFile(src, resolve(ROOT, "MEMORY.md"));
  console.log(`[ok] route ${route}: projected to ./MEMORY.md`);
}

async function createRuntimeDirs(route: Route): Promise<void> {
  const base = resolve(ROOT, ROUTE_BASE[route]);
  for (const sub of ROUTE_RUNTIME[route]) {
    await mkdir(resolve(base, sub), { recursive: true });
  }
  console.log(`[ok] runtime dirs created for route=${route} (${ROUTE_BASE[route]})`);
}

const HARNESS_BANNER =
  "<!-- Generated by `npm run bootstrap` — do not edit. Edit templates/harness.template.md and re-run bootstrap. -->\n\n";

async function projectHarnessFiles(): Promise<void> {
  const template = await readFile(
    resolve(ROOT, "templates", "harness.template.md"),
    "utf-8",
  );
  for (const [stem, delta] of Object.entries(HARNESS_DELTAS)) {
    // Substitute 6 platform tokens. Collapse 3+ consecutive newlines to 2
    // (handles the empty-section_0 case for CLAUDE without breaking the others).
    const content = (HARNESS_BANNER + template)
      .replace(/\$\{PLATFORM_TITLE\}/g, delta.title)
      .replace(/\$\{PLATFORM_INTRO\}/g, delta.intro)
      .replace(/\$\{PLATFORM_SECTION_0\}/g, delta.section_0)
      .replace(/\$\{PLATFORM_TIER2_BACKEND\}/g, delta.tier2_backend)
      .replace(/\$\{PLATFORM_TIER1_RAISE_NOTE\}/g, delta.raise_note)
      .replace(/\$\{PLATFORM_LOAD_ORDER\}/g, delta.load_order)
      .replace(/\$\{PLATFORM_CROSS_END\}/g, delta.cross_end)
      .replace(/\n{3,}/g, "\n\n");
    const dst = resolve(ROOT, `${stem}.harness.md`);
    await writeFile(dst, content, "utf-8");
    console.log(`[ok] harness: ${stem}.harness.md (${content.length} chars)`);
  }
}

const { platform, route } = parseArgs(process.argv.slice(2));

const selected = platform === "all" ? PLATFORMS : [platform];
for (const p of selected) await projectPlatform(p);
// Always write the full group sharing a native entry, so `--platform codex`
// cannot clobber the qoder delta merged into the same AGENTS.md.
for (const group of groupByNativeEntry(PLATFORMS)) {
  if (group.some((p) => selected.includes(p))) await projectNativeEntry(group);
}
await projectRoute(route);
await createRuntimeDirs(route);
await projectHarnessFiles();

console.log("");
console.log(`Harness Factory bootstrap complete (platform=${platform}, route=${route}).`);
console.log("Next: see ENTRY.md and core/intent-routing.md");
