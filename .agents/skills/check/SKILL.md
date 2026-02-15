---
name: check
description: 'Run a thorough senior-level code review for Cortex changes: architecture compliance plus bugs, code smells, risk assessment, and practical improvement suggestions.'
---

# Check (Senior Code Review)

## Overview

Run a comprehensive, read-only code review. Include architecture compliance by delegating rule-level architecture checks to `$architecture-checker`, then extend with a senior-engineer review focused on bugs, regressions, risk, maintainability, and test gaps.

## Workflow

1. Interpret scope from the request.

- No argument: uncommitted changes.
- Commit hash: changes since that commit.
- "all" or "codebase": full codebase.

2. Run architecture validation first.

- Invoke `$architecture-checker` with the derived scope.
- Treat `$architecture-checker` as the source of truth for documented architecture-rule violations.
- Reuse its findings in the final report and do not restate the same issue as a new finding.

3. Gather review evidence.

- Identify files in scope (`git diff --name-only`, staged + unstaged when needed).
- Read the changed code and nearby context.
- Run quality checks when possible (prefer `bun run check:all` for thorough coverage).
- If a check cannot run, note it explicitly and continue with manual review.

4. Perform a senior-level manual review across these categories:

- Correctness and potential bugs (logic flaws, edge cases, null/undefined handling, async/race conditions).
- Cross-cutting design fit and interaction risks not already covered by `$architecture-checker` findings.
- Security and data safety risks.
- Error handling and observability gaps.
- Performance risks (render cascades, unnecessary allocations, N+1 patterns, expensive loops/queries).
- Maintainability/code smells (duplication, long functions, hidden coupling, dead code, unclear naming, magic values).
- Test coverage and regression risk (missing unit/integration tests for business logic).

5. Suggest improvements.

- Provide practical, high-impact improvements even when code is technically correct.
- Prioritize suggestions by risk reduction and implementation effort.

## Output Format

```markdown
## Senior Code Review: <scope>

### Files Checked

- `path`

### Architecture Findings (from `$architecture-checker`)

- Reused architecture violations/missing requirements/anti-pattern risks
- Note only net-new architecture concerns here if they were not already reported by `$architecture-checker`

### Findings (ordered by severity)

1. **[Critical|High|Medium] `path:line`**
   - **Category:** Bug | Security | Performance | Code Smell | Testing | Cross-Cutting Design
   - **Issue:** ...
   - **Impact/Risk:** ...
   - **Recommendation:** ...

### Improvement Suggestions (non-blocking)

1. **`path:line`** - ...
   - **Why improve:** ...
   - **Suggested change:** ...

### Test Gaps

1. **`path`** - Missing/weak coverage for ...
   - **Suggested tests:** ...

### Checks Run

- `bun run check:all` - pass/fail (or not run, with reason)
- Any other checks used

### Summary

- X critical/high findings
- Y medium findings
- Z non-blocking improvements
```

If there are no findings, explicitly say: "No architecture violations, bugs, or significant code smells found in scope."
