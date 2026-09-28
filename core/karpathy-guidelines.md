# karpathy-guidelines.md - thinking rules for coding

## Mindset

1. **Think before coding** - understand the problem, then write the line
2. **Simplicity first** - the best code is the code never written
3. **Surgical changes** - touch what needs touching, no more
4. **Goal-driven execution** - know the pass criteria before starting

## Operational rules

- Read the file before editing it
- Read at least 1 sibling file for style alignment
- Run the build/test before claiming done
- No commits without diff review
- No abstractions until the second occurrence

## Anti-patterns

- Adding "future flexibility" to a single-use path
- Wrapping in interfaces with one implementation
- Creating factory for one product
- Adding config for a value that never changes
