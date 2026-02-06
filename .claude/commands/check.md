---
allowed-tools: [Task]
description: 'Senior engineer code review: architecture compliance + bugs, code smells, and improvements'
---

# /check - Senior Engineer Code Review

## Usage

```
/check                    # Check uncommitted changes (default)
/check abc1234            # Check changes since commit abc1234
/check all                # Check the entire codebase
```

## Execution

Spawn **two agents in parallel** using the Task tool:

1. **`architecture-checker`** — Checks architecture pattern compliance (its existing scope)
2. **`general-purpose`** — Performs a senior engineer code review for bugs, code smells, security, performance, and improvements

### Scope determination (applies to both agents)

- **No arguments**: Uncommitted changes
- **Commit hash argument**: Changes since that commit
- **"all" or "codebase" argument**: Entire codebase

Wait for both agents to complete, then present their combined results to the user.

## Agent 1: Architecture Checker

Runs its standard architecture pattern compliance checks. No additional instructions needed.

```
Task(subagent_type="architecture-checker", prompt="Check uncommitted changes for architecture pattern compliance")
```

## Agent 2: Senior Code Review

This agent performs a thorough code review **separate from architecture patterns** (those are handled by Agent 1). It should:

1. **Determine scope** using the same git commands as the architecture-checker
2. **Read the changed files**
3. **Review as a Senior Engineer** covering:
   - **Potential Bugs** — Race conditions, off-by-one errors, null/undefined handling, unhandled promise rejections, incorrect types, logic errors, missing edge cases
   - **Code Smells** — Dead code, overly complex functions, deep nesting, god objects/functions, duplicated logic, magic numbers/strings, poor naming, missing error handling
   - **Security Concerns** — Injection vulnerabilities, unsafe data handling, exposed secrets, improper input validation at system boundaries
   - **Performance Issues** — Unnecessary re-renders, missing cleanup in effects, N+1 queries, unbounded data structures, expensive operations in hot paths
   - **Concrete Improvements** — Clearer abstractions, better naming, simplified control flow, opportunities to leverage existing utilities in the codebase

4. **Organize findings by severity:**
   - **Critical** — Bugs or security issues that will cause problems in production
   - **Warning** — Code smells or issues that should be addressed
   - **Suggestion** — Improvements to readability, maintainability, or performance

5. **Each finding must include:** file path, line number(s), clear description, and a concrete fix recommendation

**Do NOT** review for architecture pattern compliance — that is handled by the other agent.

## Example Parallel Invocations

Default (uncommitted changes):

```
Task(subagent_type="architecture-checker", prompt="Check uncommitted changes for architecture pattern compliance")

Task(subagent_type="general-purpose", prompt="Perform a Senior Engineer code review of uncommitted changes (use `git diff` and `git diff --cached` to determine files). Read each changed file thoroughly. Review for: (1) potential bugs and logic errors, (2) code smells and maintainability issues, (3) security concerns, (4) performance issues, (5) concrete improvement suggestions. Do NOT check architecture pattern compliance (another agent handles that). Organize findings by severity: Critical, Warning, Suggestion. Each finding must include file path, line numbers, description, and fix recommendation. If no issues found, say so.")
```

Since a commit:

```
Task(subagent_type="architecture-checker", prompt="Check all changes since commit abc1234 for architecture pattern compliance")

Task(subagent_type="general-purpose", prompt="Perform a Senior Engineer code review of all changes since commit abc1234 (use `git diff abc1234` to determine files). Read each changed file thoroughly. Review for: (1) potential bugs and logic errors, (2) code smells and maintainability issues, (3) security concerns, (4) performance issues, (5) concrete improvement suggestions. Do NOT check architecture pattern compliance (another agent handles that). Organize findings by severity: Critical, Warning, Suggestion. Each finding must include file path, line numbers, description, and fix recommendation. If no issues found, say so.")
```

Entire codebase:

```
Task(subagent_type="architecture-checker", prompt="Check the entire codebase for architecture pattern compliance")

Task(subagent_type="general-purpose", prompt="Perform a Senior Engineer code review of the entire codebase (check all source files in src/, src-tauri/, and python-backend/). Read files thoroughly. Review for: (1) potential bugs and logic errors, (2) code smells and maintainability issues, (3) security concerns, (4) performance issues, (5) concrete improvement suggestions. Do NOT check architecture pattern compliance (another agent handles that). Organize findings by severity: Critical, Warning, Suggestion. Each finding must include file path, line numbers, description, and fix recommendation. If no issues found, say so.")
```
