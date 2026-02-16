# Task: Add Python mypy Type Checking

## Summary

Add mypy-based static type checking to the Python backend with an incremental rollout that does not block active feature delivery. This task introduces tooling, configuration, baseline code fixes required for the current backend, and a dedicated bun script for repeatable type checks.

## Acceptance Criteria

- [x] `mypy` added to Python backend dev dependencies
- [x] `python-backend/uv.lock` updated after dependency change
- [x] mypy configuration added to `python-backend/pyproject.toml` with module-scoped overrides (no global `ignore_missing_imports`)
- [x] Root script added to `package.json`: `python:typecheck` = `cd python-backend && uv run mypy src` (expanded from initial scoped-module target)
- [x] Baseline type-check command succeeds for the agreed scope: `src/services`, `src/api`, `src/db` (validated via broader `src` run)
- [x] Baseline code issues currently blocking mypy are fixed (see "Baseline Remediation")
- [x] Python static-analysis docs updated to include `python:typecheck` workflow
- [x] Follow-up decision documented: `python:typecheck` is now gated in `check:all` after successful baseline rollout

## Dependencies

- Task 18: Phase 2 quality gate complete (completed on 2026-02-15)
- Existing Python lint/test workflow in root `package.json`

## Technical Notes

- Keep rollout incremental to avoid large refactors in one step
- Start with practical settings, then tighten over time
- Prefer explicit typing on public interfaces and service boundaries first
- Add `ignore_missing_imports` only where required, not globally unless necessary for baseline
- Use per-module mypy overrides for known untyped dependencies (`readability`, `sqlite_vec`) in the initial rollout
- If additional libraries need stubs, pin or add type packages as needed

## Suggested mypy Configuration

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
check_untyped_defs = true
no_implicit_optional = true
exclude = ["tests/"]

[[tool.mypy.overrides]]
module = ["readability", "sqlite_vec"]
ignore_missing_imports = true
```

Tune strictness after baseline passes.

## Baseline Remediation (Required)

Current baseline mypy run (captured 2026-02-16) reports errors in these areas:

- `python-backend/src/services/parsing.py` - untyped third-party import (`readability`)
- `python-backend/src/db/database.py` - optional row indexing assumptions
- `python-backend/src/db/repositories/items.py` - type confusion around `list` return typing
- `python-backend/src/services/embeddings.py` - untyped third-party import (`sqlite_vec`)
- `python-backend/src/services/processing.py` - downstream typing issue from repository result typing

Minimum remediation for this task:

1. Add module-scoped overrides for untyped dependencies in mypy config.
2. Fix optional `fetchone()` handling in `db/database.py` to avoid indexing nullable values.
3. Resolve repository typing issue in `db/repositories/items.py` that causes invalid list typing.
4. Re-run mypy and fix resulting dependent typing errors in `services/processing.py`.

## Files to Modify

- `python-backend/pyproject.toml` — Add mypy config and dev dependency
- `python-backend/uv.lock` — Lock updated Python dev dependency graph
- `package.json` — Add `python:typecheck` script using the existing backend tooling
- `docs/developer/quality-tooling/static-analysis.md` — Add Python type-check workflow reference (and note gate status)

## Verification

```bash
bun run python:typecheck
bun run python:lint
bun run python:test
```

Optional follow-up verification (when evaluating `check:all` integration):

```bash
bun run check:all
```

---

## Implementation Details

_Tracked: 2026-02-16_

### Files Changed

| File                                                | Change   | Description |
| --------------------------------------------------- | -------- | ----------- |
| `package.json`                                      | Modified | Added `python:typecheck` and included it in `check:all`. |
| `python-backend/pyproject.toml`                    | Modified | Added `[tool.mypy]` settings with module-scoped overrides and added `mypy` to dev dependencies. |
| `python-backend/uv.lock`                            | Modified | Updated lockfile with `mypy` and transitive dependencies. |
| `python-backend/src/db/database.py`                 | Modified | Fixed nullable `fetchone()` handling before tuple indexing in verification queries. |
| `python-backend/src/db/repositories/items.py`       | Modified | Introduced `ItemList` type alias and normalized list-return signatures. |
| `python-backend/src/api/dependencies.py`            | Modified | Added `isinstance` checks for app-state singleton dependencies to satisfy runtime/type safety. |
| `python-backend/src/providers/base.py`              | Modified | Corrected abstract `stream_chat` signature to return `AsyncIterator[str]` without `async def`. |
| `python-backend/src/providers/ollama.py`            | Modified | Tightened response-shape validation and normalized embedding vectors to `list[float]`. |
| `python-backend/src/workflows/processing.py`        | Modified | Added explicit node/update type aliases and casts around LangGraph compile/invoke boundaries for mypy compatibility. |
| `docs/developer/quality-tooling/static-analysis.md` | Modified | Documented mypy usage in quick-reference table and Python tooling commands. |
| `.prettierignore`                                   | Modified | Ignored `python-backend/.mypy_cache/` artifacts. |
| `docs/tasks-todo/task-19-python-mypy-type-checking.md` | Modified | Marked acceptance criteria complete and recorded implementation/learning notes. |

### Dependencies Added

- `mypy>=1.19.1` - Python static type checking for backend source.
- `mypy-extensions==1.1.0` - transitive mypy dependency for typing helpers.
- `pathspec==1.0.4` - transitive mypy dependency used for file pattern matching.

### Verification Executed

- `bun run python:typecheck` -> `Success: no issues found in 33 source files`
- `bun run python:lint` -> `All checks passed!`
- `bun run python:test` -> `237 passed`

---

## Learning Report

_Generated: 2026-02-16_

### Summary

The Python backend now has a reproducible mypy workflow, baseline typing blockers were resolved, and type checking is integrated into the main `check:all` gate.

### Patterns and Decisions

- Used module-scoped mypy overrides for untyped third-party modules (`readability`, `sqlite_vec`) instead of enabling global `ignore_missing_imports`.
- Chose to type-check full `python-backend/src` rather than only selected subpackages, which made the quality gate stronger without additional command complexity.
- Kept fixes localized to boundary points (database row nullability, app-state singleton retrieval, provider JSON decoding, LangGraph typing seams) to avoid broad refactors.

### Challenges and Solutions

- Challenge: mypy reported nullable database row indexing and ambiguous collection return typing.
  Solution: added explicit `None` guards for `fetchone()` and introduced concrete list type aliases for repository methods.
- Challenge: dynamic framework boundaries (FastAPI app state, LangGraph compiled graph typing) triggered type uncertainty.
  Solution: added runtime type checks and narrow `cast(...)` usage only at integration boundaries.
- Challenge: provider response payloads were assumed shape-safe at runtime.
  Solution: validated response structures before property access and normalized values to expected typed forms.

### Lessons Learned

- Incremental rollout can still end with broad coverage when blockers are resolved early.
- Strict typing at IO/framework edges yields high impact with relatively small code changes.
- Capturing type-checking in both docs and shared scripts reduces drift between local workflows and CI gates.
