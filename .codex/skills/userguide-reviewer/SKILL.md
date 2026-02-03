---
name: userguide-reviewer
description: Review user guide documentation against actual system features. Use when asked to audit docs/userguide, verify user-facing docs after feature work, or identify missing end-user documentation.
---

# Userguide Reviewer

## Overview
Review user guide docs against actual system features and return update recommendations. Do not modify docs unless asked.

## Workflow
1. Read all content in `docs/userguide/`.
2. Inspect the UI codebase for user-facing features:
- `src/components/`
- `src/store/`
- `src/lib/commands/`
- `src/lib/shortcuts.ts`
- `src/i18n/`
- menu definitions and preferences
3. Compare documented features with implementation.
4. Report gaps, outdated content, and clarity issues.

## Output Format
```markdown
## User Guide Review

### Features Not Documented
- Feature name - found in `path`
  - User impact: ...
  - Suggested section: ...
  - Key points to cover: ...

### Outdated Content
- Section says X but actual behavior is Y
  - Location: `path`
  - Fix: ...

### Accuracy Issues
- Issue description
  - Location: ...
  - Fix: ...

### Tone/Clarity Issues
- Section - issue description
  - Suggestion: ...

### Recommended Updates (Priority Order)
1. ...
2. ...
```
