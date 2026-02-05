# Task: Add Python mypy Type Checking

## Summary

Add mypy-based static type checking to the Python backend with an incremental rollout that does not block active feature delivery. This task introduces tooling, configuration, and a dedicated bun script for repeatable type checks.

## Acceptance Criteria

- [ ] `mypy` added to Python backend dev dependencies
- [ ] mypy configuration added to `python-backend/pyproject.toml`
- [ ] Root script added to `package.json`: `python:typecheck`
- [ ] Baseline type-check command succeeds for agreed scope (initially `src/services`, `src/api`, `src/db`)
- [ ] Documented excludes for third-party stubs or dynamic modules that are out of scope for initial rollout
- [ ] Optional follow-up: wire `python:typecheck` into `check:all` after baseline is stable

## Dependencies

- Task 18: Phase 2 quality gate complete
- Existing Python lint/test workflow in root `package.json`

## Technical Notes

- Keep rollout incremental to avoid large refactors in one step
- Start with practical settings, then tighten over time
- Prefer explicit typing on public interfaces and service boundaries first
- Add `ignore_missing_imports` only where required, not globally unless necessary for baseline
- If `aiosqlite` or other libraries need stubs, pin or add type packages as needed

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
```

Tune strictness after baseline passes.

## Files to Modify

- `python-backend/pyproject.toml` — Add mypy config and dev dependency
- `package.json` — Add `python:typecheck` script using the existing backend tooling
- `docs/developer/quality-tooling/testing.md` or related quality doc — Add Python type-check workflow reference

## Verification

```bash
bun run python:typecheck
bun run python:lint
bun run python:test
```
