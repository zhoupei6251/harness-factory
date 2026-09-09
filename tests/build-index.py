#!/usr/bin/env python3
"""Regenerate skills/INDEX.md from current skills/<name>/SKILL.md frontmatter.

Usage: python3 tests/build-index.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(ROOT, "skills")
INDEX = os.path.join(SKILLS_DIR, "INDEX.md")


def get_description(skill_md: str) -> str:
    content = open(skill_md, "r", encoding="utf-8").read(2000)
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            for line in content[3:end].split("\n"):
                if line.startswith("description:"):
                    return line.split(":", 1)[1].strip().strip('"').strip("'")
    for line in content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("---"):
            return line[:80]
    return ""


def main() -> int:
    if not os.path.isdir(SKILLS_DIR):
        print(f"no skills/ dir at {SKILLS_DIR}")
        return 1
    skill_dirs = sorted(
        e for e in os.listdir(SKILLS_DIR)
        if os.path.isdir(os.path.join(SKILLS_DIR, e))
    )
    rows = []
    for s in skill_dirs:
        sm = os.path.join(SKILLS_DIR, s, "SKILL.md")
        desc = get_description(sm) if os.path.exists(sm) else "(missing SKILL.md)"
        rows.append((s, desc))
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write("# Skill Index\n\n")
        f.write(f"Auto-generated. Total: {len(rows)} skills.\n\n")
        f.write("| Skill | Description |\n")
        f.write("|-------|-------------|\n")
        for s, d in rows:
            d_safe = d.replace("|", "\\|")[:100]
            f.write(f"| {s} | {d_safe} |\n")
    print(f"wrote {INDEX} ({len(rows)} skills)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
