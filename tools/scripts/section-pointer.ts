#!/usr/bin/env node
// section-pointer.ts — does a doc that says `<file>.md § <section>` name a
// heading that exists?
//
// Why this is its own module: structure-audit.ts cannot be loaded by a test
// (it runs a whole-repo audit at import time and needs every schema on disk), so
// the check would only ever be exercised against this repo — which carries no
// such pointer today, leaving it permanently dormant. The pure part lives here
// and the fixture in tools/tests/ drives it.
//
// Case it was written for (2026-11-12): the project CLAUDE.md ranked
// `guides/routing.md § 阶段门禁` above every other document. routing.md had no
// such section — it never did — so the rule that won every conflict resolved to
// nothing, and two contradictory gate rules shipped side by side.

// Trailing sentence punctuation is part of the prose, not the section name:
// "see `x.md` § Gate." names "Gate". A backtick or `>` ends the pointer too.
export const SECTION_PTR = /`([A-Za-z0-9._/-]+\.md)`\s*§\s*([^\s`>,.;:!?)]+)/g;

/** True when a heading in `text` carries `section`, ignoring hashes and whitespace. */
export function hasSection(text: string, section: string): boolean {
  const needle = section.replace(/\s+/g, "");
  return text
    .split(/\r?\n/)
    .filter((line) => /^#{1,6}\s/.test(line))
    .some((line) => line.replace(/^#{1,6}\s+/, "").replace(/\s+/g, "").includes(needle));
}

export interface DanglingPointer {
  /** Doc containing the pointer, as given. */
  doc: string;
  /** The file the pointer names. */
  target: string;
  /** The section named after `§`. */
  section: string;
  /** "missing-file" when the target is not readable, "missing-section" otherwise. */
  reason: "missing-file" | "missing-section";
}

/**
 * Check every section pointer in `docs`. `read` must return the file's text or
 * null when it cannot be read; callers keep the filesystem out of this module so
 * tests can pass a plain map.
 */
export function findDanglingPointers(
  docs: Array<{ path: string; text: string }>,
  read: (path: string) => string | null,
): DanglingPointer[] {
  const dangling: DanglingPointer[] = [];
  for (const { path, text } of docs) {
    for (const m of text.matchAll(SECTION_PTR)) {
      const target = read(m[1]);
      if (target === null) {
        dangling.push({ doc: path, target: m[1], section: m[2], reason: "missing-file" });
      } else if (!hasSection(target, m[2])) {
        dangling.push({ doc: path, target: m[1], section: m[2], reason: "missing-section" });
      }
    }
  }
  return dangling;
}
