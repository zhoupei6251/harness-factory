#!/usr/bin/env node
import { writeFile, mkdir, copyFile, stat } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");

type Platform = "claude" | "codex" | "trae" | "workbuddy";
type Route = "code" | "novel" | "news";
type Mode = "shim" | "copy";

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

function toPosix(p: string): string {
  return p.replace(/\\/g, "/");
}

function parseArgs(argv: string[]): { platform: Platform | "all"; route: Route; mode: Mode; target: string } {
  let platform: Platform | "all" = "all";
  let route: Route = "code";
  let mode: Mode = "shim";
  let target = ROOT;
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
    } else if (argv[i] === "--mode" && argv[i + 1]) {
      const m = argv[++i];
      if (m === "shim" || m === "copy") {
        mode = m as Mode;
      } else {
        console.error(`Unknown mode: ${m} (expected shim|copy)`);
        process.exit(1);
      }
    } else if (argv[i] === "--target" && argv[i + 1]) {
      target = resolve(argv[++i]);
    } else if (argv[i] === "-h" || argv[i] === "--help") {
      console.log("Usage: bootstrap.ts [--platform claude|codex|trae|workbuddy|all] [--route code|novel|news] [--mode shim|copy] [--target <dir>]");
      console.log("");
      console.log("  --mode shim (default): platform entry files are thin stubs referencing the");
      console.log("                         shared harness-factory content (one source of truth).");
      console.log("  --mode copy:           full content is copied into each platform dir (legacy).");
      console.log("  --target <dir>:        where to project platform dirs (default: harness-factory root).");
      process.exit(0);
    }
  }
  return { platform, route, mode, target };
}

async function exists(path: string): Promise<boolean> {
  try {
    await stat(path);
    return true;
  } catch {
    return false;
  }
}

/** Write a thin stub that points back to the shared harness-factory file. */
async function writeShim(dst: string, sharedAbs: string, label: string): Promise<void> {
  const stub = `# ${label} (shim)

This platform's rules live in the shared harness — do NOT edit this stub.

Read and follow: ${toPosix(sharedAbs)}

If that path is unavailable, bootstrap again from harness-factory:
\`npm run bootstrap -- --platform <name> --route <route> --target <this dir>\`
`;
  await writeFile(dst, stub, "utf-8");
}

async function projectPlatform(plat: Platform, target: string, mode: Mode): Promise<void> {
  const dst = resolve(target, PLATFORM_DIR[plat], "rules");
  await mkdir(dst, { recursive: true });

  const platformEntry = resolve(ROOT, "platforms", plat, "rules", "ENTRY.md");
  const canonicalEntry = resolve(ROOT, "core/ENTRY.md");
  const usePlatform = await exists(platformEntry);
  const entrySrc = usePlatform ? platformEntry : canonicalEntry;

  if (mode === "shim") {
    // One shared set: stub references the source of truth instead of duplicating it.
    await writeShim(resolve(dst, "ENTRY.md"), entrySrc, `${plat} rules`);
    await writeShim(resolve(dst, "ROOT.md"), resolve(ROOT, "ENTRY.md"), `${plat} root entry`);
  } else {
    await copyFile(entrySrc, resolve(dst, "ENTRY.md"));
    await copyFile(resolve(ROOT, "ENTRY.md"), resolve(dst, "ROOT.md"));
  }
  console.log(`[ok] ${plat}: ${PLATFORM_DIR[plat]}/rules/ (entry source: ${usePlatform ? "platform-specific" : "canonical"}, mode: ${mode})`);
}

async function projectRoute(route: Route, target: string, mode: Mode): Promise<void> {
  const src = resolve(ROOT, "routes", route, "MEMORY.md");
  if (!(await exists(src))) {
    console.log(`[skip] route ${route}: no routes/${route}/MEMORY.md yet`);
    return;
  }
  const dst = resolve(target, "MEMORY.md");
  if (mode === "shim" && (await exists(dst))) {
    // Never clobber an existing MEMORY.md in shim mode — it holds live session state.
    console.log(`[skip] route ${route}: ${toPosix(dst)} already exists (shim mode preserves it)`);
    return;
  }
  await copyFile(src, dst);
  console.log(`[ok] route ${route}: projected to ${toPosix(dst)}`);
}

async function createRuntimeDirs(route: Route, target: string): Promise<void> {
  const base = resolve(target, ROUTE_BASE[route]);
  for (const sub of ROUTE_RUNTIME[route]) {
    await mkdir(resolve(base, sub), { recursive: true });
  }
  console.log(`[ok] runtime dirs created for route=${route} (${ROUTE_BASE[route]})`);
}

const { platform, route, mode, target } = parseArgs(process.argv.slice(2));

if (platform === "all") {
  for (const p of PLATFORMS) await projectPlatform(p, target, mode);
} else {
  await projectPlatform(platform, target, mode);
}
await projectRoute(route, target, mode);
await createRuntimeDirs(route, target);

console.log("");
console.log(`Harness Factory bootstrap complete (platform=${platform}, route=${route}, mode=${mode}, target=${toPosix(target)}).`);
console.log("Next: see ENTRY.md and core/intent-routing.md");
