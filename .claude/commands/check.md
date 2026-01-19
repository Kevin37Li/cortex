---
allowed-tools: [Read, Glob, Grep]
description: 'Check work for adherence with architecture patterns'
---

# /check - Architecture Review

## Purpose

Check work for adherence with documented architecture patterns and specs in `docs/developer/`.

## Usage

```
/check
```

## Execution

Review all work in this session against relevant docs in `docs/developer/` (focus on patterns NOT caught by automated checks).

Read `docs/developer/README.md` to find relevant documentation based on the scope of work being checked. Common docs include:

- `architecture/architecture-guide.md` - high-level patterns
- `architecture/state-management.md` - correct state tier choice (useState vs Zustand vs TanStack Query)
- `core-systems/tauri-commands.md` - using tauri-specta bindings, not raw invoke()
- `ui-ux/i18n-patterns.md` - all UI strings in locale files (if UI was changed)
- `quality-tooling/testing.md` - sufficient test coverage (if logic was added)
- `architecture/error-handling.md` - proper error handling patterns (if error paths were added)
- `python-backend/architecture.md` - Python backend patterns (if Python was changed)
- `ai/overview.md` - AI provider patterns (if AI features were changed)

This list is not exhaustive. Read any docs relevant to the work being reviewed.

## Output

Report any architecture violations found with:

- File and line reference
- Pattern violated
- Suggested fix
