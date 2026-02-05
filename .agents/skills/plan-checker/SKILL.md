---
name: plan-checker
description: Validate implementation plans against documented architecture patterns and the existing codebase. Use when asked to review a plan, check a task document, or validate a proposed implementation approach.
---

# Plan Checker

## Overview

Validate an implementation plan against documented patterns and the actual codebase. Identify violations, missing steps, and risks. Do not modify the plan.

## Workflow

1. Read the plan or task document.
2. Always read `AGENTS.md` and `docs/developer/README.md`.
3. Read relevant docs based on plan scope.
4. Verify against the actual codebase:

- Search for existing implementations.
- Validate paths, imports, and names.
- Identify reuse opportunities.

5. If the plan is in `docs/tasks-todo/`:

- List other tasks to understand ordering.
- Check if missing steps are covered by later tasks.

6. Report issues using the format below.

## Output Format

```markdown
## Plan Review: <plan name>

### Codebase Conflicts

1. Proposal vs existing code
   - Existing code: `path` - description
   - Action: reuse or update plan

### Violations Found

1. Step violates pattern in `doc`
   - Issue: ...
   - Fix: ...

### Missing Steps

1. Missing requirement per `doc`
   - Why needed: ...
   - Suggested addition: ...

### Covered by Other Tasks

1. Concern
   - Addressed by: `task-X-name.md`
   - How: ...

### Anti-Pattern Risks

1. Risk description
   - Documented warning: ...
   - Mitigation: ...

### Looks Good

- ...

### Recommendations (Priority Order)

1. ...
2. ...
```
