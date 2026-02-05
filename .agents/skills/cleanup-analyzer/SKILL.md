---
name: cleanup-analyzer
description: Run static analysis tools and produce structured cleanup recommendations. Use when asked to run cleanup analysis, perform codebase hygiene checks, or when running the equivalent of the Claude /cleanup workflow.
---

# Cleanup Analyzer

## Overview

Run static analysis tools and investigate findings. Return categorized cleanup recommendations. Do not modify code unless explicitly asked.

## Workflow

1. Run analysis tools.

```bash
bun run knip
bun run jscpd
bun run check:all
```

2. Investigate each finding by reading relevant code. Do not report raw tool output without context.

3. Categorize findings.

### Knip

- Keep (intentional):
  - All files in `src/components/ui/` (shadcn).
  - Radix dependencies used by any shadcn component.
  - Barrel exports (`index.ts`).
  - Tauri dependencies (`@tauri-apps/*`).
  - Core deps: `zod`, `react-hook-form`, `@hookform/resolvers`, `date-fns`.
- Safe to remove: unused non-shadcn files with zero imports, unused deps with zero usage.
- Needs review: ambiguous usage, planned features, type-only exports.

### Duplicate Code (jscpd)

- High priority: >15 lines of business logic with complex conditionals.
- Medium priority: 10-15 lines of utilities or transformations.
- Low priority: <10 lines or boilerplate.
- Keep as intentional: shadcn/ui patterns, test setup code, type definitions, Rust error handling idioms.

4. Report any `check:all` errors or warnings with context.

## Output Format

```markdown
## Cleanup Analysis Report

### Knip Findings

#### Safe to Remove (high confidence)

- `file/package` - reason - `location`

#### Needs Review

- `file/package` - context - recommendation

#### Keeping (intentional)

- `file/package` - reason

### Duplicate Code Findings

#### High Priority

- **Description** - X lines
  - Locations: `file:lines`, `file:lines`
  - Recommendation: ...

#### Keep As-Is (intentional)

- **Description** - reason

### Check:all Issues

- ...

### Summary

- X items safe to remove
- Y items need review
- Z duplicates worth addressing
```
