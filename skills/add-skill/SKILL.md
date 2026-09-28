---
name: add-skill
description: "Add a new skill to harness-factory. Walks through SKILL.md + _meta.json creation, schema validation, and bootstrap sync."
tags: [Runbook]
triggers: ["add skill", "new skill", "create skill", "add a skill"]
---

# add-skill

Add a new skill to `harness-factory/skills/<name>/`.

## When to use
- User says "add skill" / "new skill" / "create skill"
- Need to capture a new technique / rule / pattern as a reusable skill

## Steps

1. Create `skills/<name>/SKILL.md` with frontmatter matching `schemas/skill.schema.json`
2. Create `skills/<name>/_meta.json` with the same `name` / `description` / `tags`
3. Run `npm run validate` to confirm both parse
4. (Optional) Run `npm run bootstrap` to project the skill to platform rules dirs

## SKILL.md template
```markdown
---
name: <kebab-case>
description: "<one-line: what + when>"
tags: [Rules, Runbook]
---

# <name>

## When to use
<triggers>

## Steps
1. ...
```

## _meta.json template
```json
{
  "name": "<same>",
  "description": "<same>",
  "tags": ["Rules", "Runbook"],
  "version": "0.1.0"
}
```
