---
allowed-tools: [Read, Bash, Glob, Grep, TodoWrite, Edit, Write, Task]
description: 'Implement a task with iterative coderabbit review'
---

# /implement-task - Implement Task with CodeRabbit Review

## Purpose

Implement a task from `docs/tasks-todo/` with iterative AI code review using CodeRabbit. Only fix critical/major issues, ignore nits. Maximum 2 review cycles.

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

### Phase 3: CodeRabbit Review Loop (Max 2 iterations)

For each iteration (maximum 2):

1. **Run CodeRabbit review:**
   ```bash
   coderabbit review --prompt-only --type uncommitted
   ```

2. **Analyze findings and categorize:**
   - **Critical/Major**: Security issues, bugs, logic errors, breaking changes, missing error handling
   - **Nits (ignore)**: Style preferences, minor naming suggestions, optional improvements, documentation suggestions

3. **Fix critical/major issues only** - Do not fix nits

4. **Second iteration**: If this is the second run and no critical issues remain, stop the loop

### Phase 4: Summary Report

Provide a summary with:

1. **Completed Work**
   - List of files created/modified
   - Key features/functionality implemented
   - Tests added (if any)

2. **CodeRabbit Review Results**
   - Critical issues found and fixed (per iteration)
   - Final review status

3. **Ignored Issues (Nits)**
   - List each ignored nit with a brief reason why it was skipped
   - Format: `[File:Line] Issue description - Reason ignored`

4. **Next Steps** (if any)
   - Suggest running `/check` to verify against architecture
   - Note if task should be marked complete with `bun task:complete <name>`

## Critical Issue Examples

Fix these:
- SQL injection vulnerabilities
- Missing null/undefined checks that could crash
- Incorrect business logic
- Missing required error handling
- Type errors
- Breaking API changes

## Nit Examples

Ignore these:
- "Consider renaming X to Y for clarity"
- "Could add a docstring here"
- "This could be slightly more performant"
- "Consider extracting to a helper function"
- Style/formatting preferences not caught by linter
