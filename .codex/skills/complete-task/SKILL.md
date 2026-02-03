---
name: complete-task
description: Generate a learning report for a completed task and update the task file. Use when asked to run /complete-task or to document task completion in docs/tasks-todo.
---

# Complete Task

## Overview
Record implementation details for a completed task and append a learning report. Trigger a docs review based on the work.

## Workflow
1. Locate the task file in `docs/tasks-todo/` by number or name.
2. Read the task to understand acceptance criteria and required files.
3. Gather implementation data:
```bash
git status -sb
git diff --name-only
git diff --name-only --cached
```
4. Read changed files relevant to the task.
5. Append an `Implementation Details` section to the task file and update acceptance criteria checkboxes.
6. Analyze the implementation and generate a `Learning Report` section.
7. Invoke `$docs-reviewer` with the task document to target the doc review.
8. Summarize results and suggest `bun task:complete <task>` to move the task to done.

## Implementation Details Template
```markdown
---

## Implementation Details

_Tracked: YYYY-MM-DD_

### Files Changed

| File              | Change   | Description |
| ----------------- | -------- | ----------- |
| `path/to/file`    | Created  | ...         |
| `path/to/other`   | Modified | ...         |

### Dependencies Added
- `package@version` - purpose

### Acceptance Criteria Status
- [x] Criteria 1 - Implemented in `file:line`
- [ ] Criteria 2 - Not implemented (reason)
```

## Learning Report Template
```markdown
---

## Learning Report

_Generated: YYYY-MM-DD_

### Summary
...

### Patterns and Decisions
...

### Challenges and Solutions
...

### Lessons Learned
...

### Documentation Impact
...
```
