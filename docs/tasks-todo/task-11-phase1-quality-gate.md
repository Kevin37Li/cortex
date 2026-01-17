# Task: Phase 1 Quality Gate

## Summary

Validate that all Phase 1 work meets quality standards before proceeding to Phase 2.

## Acceptance Criteria

- [ ] `bun run check:all` passes with no errors
- [ ] All UI strings use translation keys
- [ ] Python tests pass (`cd python && uv run pytest`)
- [ ] Frontend builds without warnings
- [ ] Backend starts and responds to health check
- [ ] Can create and list items via API
- [ ] App launches and shows empty item list

## Dependencies

- All previous Phase 1 tasks (1-10)

## Quality Checks

### Frontend Checks

```bash
# Run all checks
bun run check:all

# Individual checks if needed
bun run typecheck     # TypeScript
bun run lint          # ESLint
bun run test          # Vitest
```

### Backend Checks

```bash
cd python

# Run tests with coverage
uv run pytest --cov=app

# Type checking (if using mypy)
uv run mypy app/

# Linting (if using ruff)
uv run ruff check app/
```

### Integration Verification

```bash
# Start backend
cd python && uv run uvicorn app.main:app --port 8742 &

# Verify health
curl http://localhost:8742/api/health

# Verify items endpoint
curl http://localhost:8742/api/items

# Start frontend (in another terminal)
bun run tauri dev
```

## Milestone Verification

From MVP plan: "Can launch app, see empty item list, backend responds to health checks"

- [ ] App window opens without errors
- [ ] Three-pane layout visible
- [ ] Left sidebar shows navigation
- [ ] Main content shows empty items list
- [ ] Backend health check returns `{"status": "healthy"}`
- [ ] Ollama health check returns status (healthy or unavailable)

## Anti-Pattern Review

Check for these issues from `docs/plans/mvp-plan.md`:

- [ ] No Zustand destructuring (`const { value } = useUIStore()`)
- [ ] Using typed Tauri commands, not `invoke()`
- [ ] React Compiler handles memoization (no manual useMemo/useCallback)
- [ ] Proper state layer usage (useState → Zustand → TanStack Query)

## Files to Review

- All new Python files in `python/`
- Any modified TypeScript files in `src/`
- Translation files in `locales/`

## Verification

All checks pass, milestone achieved, ready for Phase 2.
