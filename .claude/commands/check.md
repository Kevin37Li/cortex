---
allowed-tools: [Task]
description: 'Check work for adherence with architecture patterns'
---

# /check - Architecture Review

## Usage

```
/check                    # Check uncommitted changes (default)
/check abc1234            # Check changes since commit abc1234
/check all                # Check the entire codebase
```

## Execution

Use the Task tool to spawn the `architecture-checker` agent with the appropriate input:

- **No arguments**: Pass "uncommitted" as the prompt
- **Commit hash argument**: Pass the commit hash as the prompt
- **"all" or "codebase" argument**: Pass "all" as the prompt

The agent runs in its own context window and returns a structured report of any architecture violations found.

## Example Task Invocations

Default (uncommitted changes):

```
Task(subagent_type="architecture-checker", prompt="Check uncommitted changes for architecture pattern compliance")
```

Since a commit:

```
Task(subagent_type="architecture-checker", prompt="Check all changes since commit abc1234 for architecture pattern compliance")
```

Entire codebase:

```
Task(subagent_type="architecture-checker", prompt="Check the entire codebase for architecture pattern compliance")
```
