#!/usr/bin/env node
import { readFile, writeFile, mkdir, copyFile, stat } from "node:fs/promises";
import { constants } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");

type Platform = "claude" | "codex" | "trae" | "workbuddy" | "qoder";
type Route = "code";

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
};

const ROUTE_BASE: Record<Route, string> = {
  code: ".ai-runtime-artifacts",
};

// Per-platform deltas for `templates/harness.template.md`. Each harness file
// shares the same workflow, with only platform-specific loading conventions.
interface HarnessDelta {
  title: string;
  intro: string;
  section_0: string; // platform loading conventions; empty when the import is native
  load_order: string;
  cross_end: string; // full cross-platform tail (header + bullets)
}
const HARNESS_DELTAS: Record<"CLAUDE" | "AGENTS" | "GEMINI", HarnessDelta> = {
  CLAUDE: {
    title: "CLAUDE.harness.md — harness-factory 可分发 harness 规则",
    intro: [
      "> 本文件由 `harness-factory/scripts/install-into-project.ts` 在 other 模式下被目标项目 `@harness-factory/CLAUDE.harness.md` 引用。  ",
      "> 代码任务按风险加载规则、取证、实现和验证。",
    ].join("\n"),
    section_0: "",
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
      "> 与其他平台共用同一代码工作流。",
    ].join("\n"),
    section_0: [
      "## §0 Codex / Qoder 加载约定",
      "",
      "- Codex: 本机存在 `~/.codex/AGENTS.md` 优先；项目根 `AGENTS.md` 为入口",
      "- Qoder: 与 Codex 共用 `AGENTS.md` 入口（qoder 不区分）",
      "- 入口文件按其文字指令条件读取 `harness-factory/AGENTS.harness.md`（即本文件）；不存在则 fallback 到 `AGENTS.md` 自身内容",
      "- 已加载的规则不重复读取；子目录规则按改动范围加载。",
    ].join("\n"),
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
      "> 与其他平台共用同一代码工作流。",
    ].join("\n"),
    section_0: [
      "## §0 Gemini 加载约定",
      "",
      "- Gemini: 项目根 `GEMINI.md` 为入口；用户全局 `~/.gemini/GEMINI.md` 也可叠加",
      "- 入口文件按其文字指令条件读取 `harness-factory/GEMINI.harness.md`（即本文件）；不存在则 fallback 到 `GEMINI.md` 自身内容",
      "- 已加载的规则不重复读取；显式说明必要的假设与边界。",
    ].join("\n"),
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
      if (r === "code") {
        route = r;
      } else {
        console.error(`Unknown route: ${r}`);
        process.exit(1);
      }
    } else if (argv[i] === "-h" || argv[i] === "--help") {
      console.log("Usage: bootstrap.ts [--platform claude|codex|trae|workbuddy|qoder|all] [--route code]");
      process.exit(0);
    } else {
      console.error(`Unknown or incomplete argument: ${argv[i]}`);
      process.exit(1);
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
  try {
    // Project state belongs to the project; bootstrap only initializes it once.
    await copyFile(src, resolve(ROOT, "MEMORY.md"), constants.COPYFILE_EXCL);
    console.log(`[ok] route ${route}: initialized ./MEMORY.md`);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "EEXIST") {
      throw error;
    }
    console.log("[ok] preserved project MEMORY.md");
  }
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
    // Substitute platform tokens. Collapse 3+ consecutive newlines to 2
    // (handles the empty-section_0 case for CLAUDE without breaking the others).
    const content = (HARNESS_BANNER + template)
      .replace(/\$\{PLATFORM_TITLE\}/g, delta.title)
      .replace(/\$\{PLATFORM_INTRO\}/g, delta.intro)
      .replace(/\$\{PLATFORM_SECTION_0\}/g, delta.section_0)
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
