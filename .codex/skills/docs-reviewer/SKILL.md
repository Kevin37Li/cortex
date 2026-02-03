---
name: docs-reviewer
description: Review developer documentation in docs/developer for accuracy and consistency with the codebase. Use when asked to audit developer docs, verify documentation against the implementation, or after completing a feature that may require doc updates.
---

# Docs Reviewer

## Overview
Review developer documentation for correctness, consistency with the codebase, and quality. Return structured recommendations. Do not modify docs unless asked.

## Input
Either:
- A task document (use it to identify which docs likely need updates based on what was implemented)
- No input (general review of all developer docs)

## Workflow
1. Read `docs/developer/quality-tooling/writing-docs.md`.
2. If a task document is provided:
   - Read the task document to understand scope and affected areas.
   - Prioritize reviewing docs relevant to the implementation.
3. Read all files under `docs/developer/` (or a targeted subset if the task scope is narrow).
4. Sample relevant code to validate documented patterns.
5. Review each doc for:
- Correctness
- Codebase consistency
- Evergreenness
- Completeness
- Quality
6. Report findings using the format below.

## Output Format
```markdown
## Developer Docs Review

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
