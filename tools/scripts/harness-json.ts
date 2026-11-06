#!/usr/bin/env node
// harness-json.ts — reads and validates a project's harness.json declaration.
// A declaration is the project's statement of what it needs; without one the
// installers fall back to --profile.
import { readFile } from "node:fs/promises";
import { join } from "node:path";

export const DECLARATION_FILE = "harness.json";

export interface Declaration {
  platforms: string[];
  skills: string[];
  agents: string[];
}

/** Returns null when the project carries no declaration (legacy --profile path). */
export async function readDeclaration(base: string): Promise<Declaration | null> {
  const file = join(base, DECLARATION_FILE);
  let raw: string;
  try {
    raw = await readFile(file, "utf-8");
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw error;
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error(`${DECLARATION_FILE} is not valid JSON`);
  }

  const decl = parsed as Partial<Declaration>;
  for (const key of ["platforms", "skills", "agents"] as const) {
    if (!Array.isArray(decl[key])) {
      throw new Error(`${DECLARATION_FILE} must declare an array for "${key}" (use [] when empty)`);
    }
  }
  if (decl.platforms!.length === 0) {
    throw new Error(`${DECLARATION_FILE} must declare at least one platform`);
  }
  return { platforms: decl.platforms!, skills: decl.skills!, agents: decl.agents! };
}

/** Fails with the full valid list, so a typo does not silently install nothing. */
export function assertKnown(kind: "skill" | "agent" | "platform", declared: string[], available: string[]): void {
  const unknown = declared.filter((name) => !available.includes(name));
  if (!unknown.length) return;
  const hint = available.length <= 60 ? available.join(", ") : `${available.slice(0, 60).join(", ")}, …`;
  throw new Error(
    `${DECLARATION_FILE} names unknown ${kind}(s): ${unknown.join(", ")}\n  available: ${hint}`,
  );
}
