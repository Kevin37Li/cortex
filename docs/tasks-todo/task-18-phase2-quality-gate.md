# Task: Phase 2 Quality Gate and Translation Audit

## Summary

Final quality gate for Phase 2: verify all translation keys are complete (English + Chinese), all checks pass, all tests pass, and the end-to-end flow works (create note → process → view metadata). This task ensures Phase 2 meets the quality standards before moving to Phase 3.

## Acceptance Criteria

- [ ] `bun run check:all` passes with no errors
- [ ] All new UI strings have translation keys in `locales/en.json`
- [ ] All new UI strings have Chinese translations in `locales/zh-CN.json`
- [ ] CSS uses logical properties (no `text-left`/`text-right`, use `text-start`/`text-end`)
- [ ] All Python tests pass: `cd python-backend && uv run pytest -v`
- [ ] Python coverage > 80% for new modules
- [ ] Frontend tests pass: `bun run test`
- [ ] No Zustand destructuring anti-patterns in new code
- [ ] All API calls in components use TanStack Query hooks (no raw `fetch()`)
- [ ] New commands registered with `labelKey` translation key
- [ ] End-to-end smoke test: create a note → verify it appears in list → verify processing starts → verify metadata appears in detail view

## Dependencies

- Tasks 1-17: All Phase 2 tasks complete

## Technical Notes

- Per MVP plan "Quality Gate (Per Phase)": run `bun run check:all`, verify translations, confirm tests pass, review anti-patterns
- Per AGENTS.md: check for Zustand destructuring, manual useMemo/useCallback, raw invoke() calls
- The smoke test is manual (no automated E2E framework in MVP)
- If any issues found, fix them before marking this task complete

## Checklist

### Frontend Checks

```bash
bun run typecheck     # TypeScript compiles
bun run lint          # ESLint passes
bun run format:check  # Prettier formatted
bun run test          # Vitest passes
bun run check:all     # All checks combined
```

### Backend Checks

```bash
cd python-backend
uv run ruff check src/      # Linting
uv run ruff format --check src/  # Formatting
uv run mypy src/             # Type checking
uv run pytest -v             # All tests pass
uv run pytest --cov=src --cov-fail-under=80  # Coverage threshold
```

### Translation Audit

- Grep for hardcoded strings in new components
- Verify every `t('key')` call has a corresponding entry in both locale files
- Check that no translation keys are orphaned (defined but unused)

### Anti-Pattern Review

- No `const { ... } = useUIStore()` destructuring (use selector syntax)
- No manual `useMemo`/`useCallback` (React Compiler handles this)
- No `await invoke('command')` (use typed bindings)
- No raw `fetch()` in components (use TanStack Query hooks)

## Files to Review

- All files created/modified in tasks 12-17
- `locales/en.json` and `locales/zh-CN.json` for completeness
- `src/services/items.ts` for proper hook patterns

## Verification

Phase 2 is complete when all acceptance criteria above pass and the end-to-end smoke test succeeds.

## Milestone

Can create a note → see it process → view extracted metadata
