---
name: docs-reviewer
description: Review developer documentation in docs/developer for accuracy and consistency with the codebase. Use when asked to audit developer docs, verify documentation against the implementation, or after completing a feature that may require doc updates.
---

# Docs Reviewer

## Overview

Review developer documentation for correctness, consistency with the codebase, and quality. Always review all docs relevant to the code scope being evaluated. Return structured recommendations. Do not modify docs unless asked.

## Input

Either:

- A task document:
  - Use it to identify the implementation scope for that task.
  - Code scope = only implementation for that task.
  - Review all `docs/developer/` files relevant to that code scope.
- No input:
  - Code scope = whole codebase.
  - Review all `docs/developer/` files relevant to the whole codebase.

## Workflow

1. Read `docs/developer/quality-tooling/writing-docs.md`.
2. Determine code scope:
   - Task document provided: read it and derive task implementation scope.
   - No task document: use whole codebase as scope.
3. Map code scope to relevant documentation under `docs/developer/`.
   - Do not limit review only to docs explicitly named in the task file.
   - Include any architecture/index docs needed for consistency and navigation.
4. Read all mapped docs (a targeted subset is allowed only when code scope is narrow and justified).
5. Sample relevant code in scope to validate documented patterns.
6. Review each mapped doc for:

- Correctness
- Codebase consistency
- Evergreenness
- Completeness
- Quality

7. Report findings using the format below.

## Output Format

```markdown
## Developer Docs Review

### Scope Reviewed

- Code scope: <task implementation | whole codebase>
- Docs reviewed: <list or summary>

### <document-name.md>

**Status:** Needs Updates | Good | Minor Issues

#### Issues Found

- **Criterion:** Issue description at location
  - **Fix:** ...

---

### Summary by Criterion

| Criterion            | Total Issues |
| -------------------- | ------------ |
| Correctness          | X            |
| Codebase Consistency | X            |
| Evergreenness        | X            |
| Completeness         | X            |
| Quality              | X            |

### Priority Recommendations

1. Most important fix
2. Next fix
```
