---
allowed-tools: [Read, Bash, Glob, TodoWrite, Edit]
description: 'Check work for adherance with architecture and run checks'
---

# /check - Check Work

## Purpose

Check work for adherence with architecture, run checks, and suggest a commit message.

## Usage

```
/check
```

## Execution

1. **Architecture adherence** - Check all work in this session against these docs (focus on patterns NOT caught by automated checks):
   - `docs/developer/architecture/architecture-guide.md` - high-level patterns
   - `docs/developer/architecture/state-management.md` - correct state tier choice (useState vs Zustand vs TanStack Query)
   - `docs/developer/core-systems/tauri-commands.md` - using tauri-specta bindings, not raw invoke()
   - `docs/developer/ui-ux/i18n-patterns.md` - all UI strings in locale files (if UI was changed)
   - `docs/developer/quality-tooling/testing.md` - sufficient test coverage (if logic was added)
   - `docs/developer/architecture/error-handling.md` - proper error handling patterns (if error paths were added)

2. **Cleanup** - Remove any unnecessary comments or `console.log` statements introduced during development, and clean up any "leftovers" from approaches that didn't work.

3. **Automated checks** - Run `bun run check:all` and fix any errors. This runs: typecheck, lint, ast-grep rules, format check, Rust checks, and tests.

4. **Commit message** - Suggest a concise commit message summarizing the work done in this session.
