# principles.md - design principles

## Core

1. **YAGNI** - You Aren't Gonna Need It. Do not add capability for hypothetical use.
2. **KISS** - Keep It Simple. The dumbest solution that works wins.
3. **DRY** - Dont Repeat Yourself. But: only on the 3rd occurrence.
4. **Separation of concerns** - one module, one reason to change.

## For AI-assisted code

- Explicit beats implicit (no magic values)
- Boring beats clever (3am-debuggable wins)
- Deletion beats addition (remove before adding)
- One file, one purpose (no 500-line god files)

## When NOT to apply

- Security boundaries: validate at trust edges
- Error handling that prevents data loss: be explicit
- Accessibility basics: ship them, do not simplify away
- User explicitly requested full version: build it
