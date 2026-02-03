---
name: check
description: Run an architecture compliance check for Cortex code changes. Use when asked to run /check, check architecture patterns, or review changes against AGENTS.md and docs/developer.
---

# Check (Architecture Review)

## Overview
Parse scope from the request and delegate the actual review to `$architecture-checker`.

## Workflow
1. Interpret scope from the request.
- No argument: uncommitted changes.
- Commit hash: changes since that commit.
- "all" or "codebase": full codebase.

2. Invoke `$architecture-checker` with the derived scope.

## Output Format
Use the same output format as `$architecture-checker`.
