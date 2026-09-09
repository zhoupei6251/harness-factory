#!/usr/bin/env node
import { readFile, mkdir, copyFile, stat } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");

type Platform = "claude" | "codex" | "trae" | "workbuddy";
type Route = "code" | "novel" | "news";

const PLATFORMS: Platform[] = ["claude", "codex", "trae", "workbuddy"];

const PLATFORM_DIR: Record<Platform, string> = {
  claude: ".claude",
  codex: ".codex",
  trae: ".trae",
  workbuddy: ".codebuddy",
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
      console.log("Usage: bootstrap.ts [--platform claude|codex|trae|workbuddy|all] [--route code|novel|news]");
      process.exit(0);
    }
  }
  return { platform, route };
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

const { platform, route } = parseArgs(process.argv.slice(2));

if (platform === "all") {
  for (const p of PLATFORMS) await projectPlatform(p);
} else {
  await projectPlatform(platform);
}
await projectRoute(route);
await createRuntimeDirs(route);

console.log("");
console.log(`Harness Factory bootstrap complete (platform=${platform}, route=${route}).`);
console.log("Next: see ENTRY.md and core/intent-routing.md");
