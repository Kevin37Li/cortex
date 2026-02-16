# Task: Phase 3 Quality Gate

## Summary

Final quality gate for Phase 3: verify all checks pass, translation keys are complete (English + Chinese), test coverage meets threshold, architecture anti-patterns are absent, and the end-to-end search flow works. This ensures Phase 3 meets quality standards before moving to Phase 4 (Chat).

## Acceptance Criteria

- [ ] `bun run check:all` passes with no errors
- [ ] All new UI strings have translation keys in `locales/en.json`
- [ ] All new UI strings have Chinese translations in `locales/zh.json`
- [ ] Locale key parity: `diff` between en.json and zh.json scalar paths is empty
- [ ] CSS uses logical properties (no `text-left`/`text-right`, use `text-start`/`text-end`)
- [ ] All Python tests pass: `bun run python:test`
- [ ] Python backend coverage >= 80%: `bun run python:test -- --cov=src --cov-fail-under=80`
- [ ] Frontend tests pass: `bun run test:run`
- [ ] `bun run ast:lint` passes (enforces architecture anti-patterns)
- [ ] No Zustand destructuring anti-patterns in app code (selector syntax only)
- [ ] Store access in `src/lib/**` uses `useStore.getState()` (no store subscriptions)
- [ ] No raw `fetch()` in `src/components/**` or `src/hooks/**` (use TanStack Query hooks/services + `apiFetch`)
- [ ] No active string-based `invoke()` usage in app code (use typed commands from `@/lib/tauri-bindings`)
- [ ] Error handling follows documented patterns (`ApiRequestError` in frontend, structured exceptions in Python)
- [ ] New commands registered with `labelKey` translation key (`focus-search`)
- [ ] `SearchError` exception handler registered in `main.py`
- [ ] Search router registered in `main.py`
- [ ] `bun run openapi:sync` produces no diff (types are up to date)
- [ ] End-to-end smoke test (manual): create a note with content -> wait for processing to complete -> search for keywords from the note -> verify note appears in search results -> click through to item detail

## Dependencies

- Tasks 1-8 (all Phase 3 feature work) are complete

## Technical Notes

### Authoritative Check

```bash
bun run check:all     # Runs ALL checks — this is the gate
```

### Individual Checks (for debugging)

#### Frontend

```bash
bun run typecheck       # TypeScript compiles (includes openapi:sync)
bun run lint            # ESLint passes
bun run ast:lint        # ast-grep architecture patterns
bun run format:check    # Prettier formatted
bun run test:run        # Vitest passes
```

#### Rust

```bash
bun run rust:fmt:check  # Rust formatting
bun run rust:clippy     # Rust linting
bun run rust:test       # Rust tests
```

#### Python

```bash
bun run python:lint      # Ruff linting
bun run python:fmt:check # Ruff formatting
bun run python:test      # All tests pass
```

### Python Coverage (separate)

```bash
bun run python:test -- --cov=src --cov-report=term-missing --cov-fail-under=80
```

### Translation Audit

```bash
# Locale key parity (must be empty output)
diff <(jq -S 'paths(scalars) | join(".")' locales/en.json) \
     <(jq -S 'paths(scalars) | join(".")' locales/zh.json)
```

Grep Phase 3 UI files for hardcoded user-facing strings:

```bash
# Check for missing translation usage
grep -rn "search\." src/components/search/ --include="*.tsx" | grep -v "t(" | grep -v "import" | grep -v "//"
```

Verify `t('...')`, `i18n.t('...')`, and command `labelKey`/`descriptionKey` references map to locale keys.

### Anti-Pattern Review

- No `const { ... } = useUIStore()` destructuring (use selector syntax)
- In `src/lib/**`, store access uses `getState()` (no store subscriptions)
- Callbacks that need current store state use `useStore.getState()`
- No new app-level manual `useMemo`/`useCallback` (React Compiler handles this)
- No active `invoke()` calls in runtime app code (typed bindings only)
- No raw `fetch()` in components/hooks (use TanStack Query hooks/services)
- Error handling follows `docs/developer/architecture/error-handling.md`

### OpenAPI Sync Verification

```bash
bun run openapi:sync
git diff src/types/api.gen.ts  # Should show no changes
```

### Periodic Cleanup (recommended)

Phase boundaries are the right time for cleanup:

```bash
bun run knip   # Detect unused exports, dead code
bun run jscpd  # Detect duplicated code blocks
```

### Files to Review

All files created/modified in tasks 1-8:

**Python backend:**

- `python-backend/src/db/models.py` (search models)
- `python-backend/src/exceptions.py` (SearchError)
- `python-backend/src/services/search.py` (SearchService)
- `python-backend/src/workflows/search.py` (LangGraph search)
- `python-backend/src/api/routes/search.py` (API endpoint)
- `python-backend/src/main.py` (router + exception handler)
- `python-backend/tests/` (search tests)

**Frontend:**

- `src/services/search.ts` (TanStack Query hooks)
- `src/lib/commands/search-commands.ts` (Cmd+F command)
- `src/store/ui-store.ts` (searchFocused state)
- `src/hooks/use-keyboard-shortcuts.ts` (Cmd+F handler)
- `src/components/search/` (all search UI components)
- `locales/en.json` and `locales/zh.json` (search translations)

## Verification

Phase 3 is complete when all acceptance criteria pass, command outputs are captured, and the end-to-end smoke test succeeds.

## Milestone

Can search items and find relevant results.
