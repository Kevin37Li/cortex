---
allowed-tools: [Read, Bash, Glob, Grep, TodoWrite, Edit, Write, Task]
description: 'Generate learning report for a completed task and update docs'
---

# /complete-task - Complete Task with Learning Report

## Purpose

Generate a comprehensive learning report for a completed task from `docs/tasks-todo/`, append it to the task file, and trigger documentation review based on what was implemented.

## Usage

```
/complete-task <task-name-or-number>
```

Examples:

```
/complete-task 5
/complete-task health-check-endpoint
/complete-task task-5-health-check-endpoint.md
```

## Execution

### Phase 1: Task Loading

1. Find the task file in `docs/tasks-todo/` matching the argument (by number or name)
2. Read the task file to understand the requirements
3. Extract key information: acceptance criteria, technical notes, files to create/modify

### Phase 2: Implementation Tracking

Gather and record what was actually implemented. This creates a factual record before analysis.

#### 2.1 Gather Implementation Data

1. **Check uncommitted changes** for this task:

   ```bash
   git status
   git diff --name-only           # Modified tracked files
   git diff --name-only --cached  # Staged files
   ```

2. **Read the files created/modified** as listed in the task spec (and any additional files found in the uncommitted changes)

3. **Identify key implementation details:**
   - Actual files created vs planned
   - Dependencies added (check package.json, pyproject.toml, Cargo.toml changes)
   - Configuration changes
   - Test files added

#### 2.2 Update Task File with Implementation Details

Append an `## Implementation Details` section to the task file immediately:

```markdown
---

## Implementation Details

_Tracked: YYYY-MM-DD_

### Files Changed

| File               | Change   | Description       |
| ------------------ | -------- | ----------------- |
| `path/to/file.ts`  | Created  | Brief description |
| `path/to/other.py` | Modified | What was changed  |

### Dependencies Added

- `package-name@version` - Purpose

### Acceptance Criteria Status

- [x] Criteria 1 - Implemented in `file.ts:45`
- [x] Criteria 2 - Implemented in `other.py:20`
- [ ] Criteria 3 - Not implemented (reason)
```

Use the Edit tool to append this section. Update the original acceptance criteria checkboxes if they exist.

### Phase 3: Implementation Analysis

With the implementation details now recorded, analyze the work:

1. **Review the implementation** to understand:
   - What patterns were used
   - What challenges were encountered (look for TODOs, FIXMEs, complex code)
   - What decisions were made and why
   - Any deviations from the original spec

2. **Compare against acceptance criteria:**
   - What was completed vs planned
   - Any scope changes during implementation

### Phase 4: Generate Learning Report

Based on the tracked implementation details, create a learning report covering:

#### 1. Summary

- High-level overview of what was built
- Key metrics (files changed, lines of code, test coverage if applicable)

#### 2. Patterns & Decisions

- Architectural patterns used and why
- Key design decisions and rationale
- Deviations from original task spec (if any) and why

#### 3. Challenges & Solutions

- Technical challenges encountered
- How they were resolved
- Workarounds implemented (if any)

#### 4. Lessons Learned

- What worked well
- What could be improved
- Recommendations for similar future tasks

#### 5. Documentation Impact

- Which existing docs might need updates
- New patterns that should be documented
- Areas where documentation was helpful or lacking

### Phase 5: Append Learning Report

Append the learning report to the task file after the Implementation Details section:

```markdown
---

## Learning Report

_Generated: YYYY-MM-DD_

### Summary

[content]

### Patterns & Decisions

[content]

### Challenges & Solutions

[content]

### Lessons Learned

[content]

### Documentation Impact

[content]
```

### Phase 6: Documentation Review

Invoke the `docs-reviewer` agent to review and update documentation based on the learning report:

```
Use the Task tool with:
- subagent_type: "docs-reviewer"
- prompt: Include the task file path and learning report summary, asking the agent to:
  1. Review docs affected by this implementation
  2. Update docs that are now outdated based on the learnings
  3. Add new documentation for patterns/decisions discovered
```

### Phase 7: Summary

Provide a final summary with:

1. **Implementation Tracked** - Confirmation that files changed and criteria status were recorded
2. **Learning Report Added** - Confirmation the analysis was appended
3. **Documentation Updates** - Summary of what the docs-reviewer agent found/updated
4. **Next Steps**:
   - Suggest running `bun task:complete <name>` to move task to done
   - Note any manual documentation updates still needed

## Report Quality Guidelines

- Be specific and concrete, not generic
- Include actual file paths, line numbers, and code references
- Note specific versions or configurations used
- Capture tribal knowledge that isn't obvious from the code
- Focus on insights that would help future developers
- Link acceptance criteria to specific file locations where they were implemented
