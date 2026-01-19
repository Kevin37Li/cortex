---
allowed-tools: [Read, Bash, Glob, Grep, TodoWrite, Edit, Write, Task]
description: 'Implement a task from docs/tasks-todo/'
---

# /implement-task - Implement Task

## Purpose

Implement a task from `docs/tasks-todo/` following documented architecture patterns.

## Usage

```
/implement-task <task-name-or-number>
```

Examples:

```
/implement-task 1
/implement-task python-backend-project-structure
/implement-task task-1-python-backend-project-structure.md
```

## Execution

### Phase 1: Task Loading

1. Find the task file in `docs/tasks-todo/` matching the argument (by number or name)
2. Read and understand the task requirements, acceptance criteria, and dependencies
3. Create a todo list based on the task's requirements

### Phase 2: Implementation

1. Read `AGENTS.md` for core patterns and guidelines
2. Selectively read relevant docs from `docs/developer/` as needed for the task
3. Implement the task following the requirements and patterns
4. Write tests if required by the task

### Phase 3: Summary Report

Provide a summary with:

1. **Completed Work**
   - List of files created/modified
   - Key features/functionality implemented
   - Tests added (if any)

2. **Next Steps** (if any)
   - Suggest running `/check` to verify against architecture
   - Note if task should be marked complete with `bun task:complete <name>`
