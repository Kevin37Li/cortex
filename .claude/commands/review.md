---
allowed-tools: [Read, Bash, Glob, Grep, TodoWrite, Edit, Write]
description: 'Run automated checks and CodeRabbit review on uncommitted changes'
---

# /review - Automated Checks & Code Review

## Purpose

Run automated checks (`bun run check:all`) and iterative AI code review using CodeRabbit on uncommitted changes. Fix all check errors and critical/major review issues. Ignore nits. Maximum 2 CodeRabbit review cycles.

## Usage

```
/review
```

## Execution

### Automated Checks

Run `bun run check:all` and fix any errors. This runs: typecheck, lint, ast-grep rules, format check, Rust checks, and tests.

### CodeRabbit Review Loop (Max 2 iterations)

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

### Summary Report

Provide a summary with:

1. **Automated Check Results**
   - Errors found and fixed from `bun run check:all`
   - Final check status (pass/fail)

2. **CodeRabbit Review Results**
   - Critical issues found and fixed (per iteration)
   - Final review status

3. **Ignored Issues (Nits)**
   - List each ignored nit with a brief reason why it was skipped
   - Format: `[File:Line] Issue description - Reason ignored`

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
