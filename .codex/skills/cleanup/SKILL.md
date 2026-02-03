---
name: cleanup
description: Run static analysis and deliver cleanup recommendations. Use when asked to run /cleanup or perform repo hygiene checks with knip, jscpd, and check:all.
---

# Cleanup

## Overview
Delegate analysis to `$cleanup-analyzer`, then ask whether to create a cleanup task document.

## Workflow
1. Invoke `$cleanup-analyzer` to run tools and report findings.
2. Ask the user if they want a task document created in `docs/tasks-todo/`.

## Output Format
Use the same output format as `$cleanup-analyzer`.
