---
name: review
description: Run automated checks and code review on uncommitted changes. Use when asked to run /review, run bun run check:all, or perform a CodeRabbit review loop.
---

# Review

## Overview
Run automated checks and a CodeRabbit review loop. Fix critical and major issues only. Ignore nits.

## Workflow
1. Run automated checks and fix errors.
```bash
bun run check:all
```
2. Run CodeRabbit review (max 2 iterations):
```bash
coderabbit review --prompt-only --type uncommitted
```
3. Categorize findings:
- Critical/Major: security issues, bugs, logic errors, missing error handling, type errors, breaking changes.
- Nits: naming suggestions, docstrings, optional refactors, style tweaks.
4. Fix critical/major findings only.
5. Stop after the second iteration if no critical issues remain.

## Summary Format
```markdown
### Automated Check Results
- Errors found and fixed
- Final status

### CodeRabbit Review Results
- Critical issues fixed per iteration
- Final review status

### Ignored Issues (Nits)
- `file:line` Issue - reason ignored
```
