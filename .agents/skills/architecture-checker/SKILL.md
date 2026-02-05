---
name: architecture-checker
description: Check code for adherence to Cortex architecture patterns and documented rules in AGENTS.md and docs/developer. Use when asked to review architecture compliance, check changes for pattern adherence, or run an architecture check on uncommitted changes, a commit range, or the full codebase.
---

# Architecture Checker

## Overview

Review code for compliance with documented architecture patterns. Report violations, missing requirements, and anti-pattern risks. Do not modify code.

## Workflow

1. Determine scope.

- No scope provided: check uncommitted changes.
- Commit hash provided: check changes since that commit.
- "all" or "codebase": check the full codebase.

2. Identify files in scope.

- Uncommitted:

```bash
git diff --name-only
git diff --cached --name-only
```

- Since commit:

```bash
git diff --name-only <commit>
```

- Full codebase: include `src/`, `src-tauri/`, and `python-backend/`.

3. Load docs.

- Always read `AGENTS.md` and `docs/developer/README.md`.
- Read relevant docs based on files in scope.

4. Read files in scope.

5. Check patterns not enforced by tooling.

- State management tier choice and Zustand selector usage.
- Tauri command usage via `@/lib/tauri-bindings`.
- i18n string handling and RTL-safe CSS.
- Error handling patterns.
- Testing expectations for business logic.
- Python backend async and repository patterns when relevant.

6. Report findings using the format below.

## Output Format

```markdown
## Architecture Review: <scope>

### Files Checked

- `path`

### Violations Found

1. **`path:line`** violates **<pattern>** in `doc`
   - **Issue:** ...
   - **Fix:** ...

### Missing Requirements

1. **`path`** - ... per `doc`
   - **Suggested addition:** ...

### Anti-Pattern Risks

1. **`path:line`** - ...
   - **Documented warning:** ...
   - **Mitigation:** ...

### Looks Good

- ...

### Summary

- X violations found
- Y missing requirements
- Z anti-pattern risks
```

If no issues, state: "No architecture violations found."
