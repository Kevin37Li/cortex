# Task: Phase 3 Quality Gate

## Summary

Final quality gate for Phase 3: verify all checks pass, translation keys are complete (English + Chinese), test coverage meets threshold, architecture anti-patterns are absent, and the end-to-end search flow works. This ensures Phase 3 meets quality standards before moving to Phase 4 (Chat).

## Acceptance Criteria

- [x] `bun run check:all` passes with no errors
- [x] `bun run python:typecheck` passes (explicitly verified; included in `check:all`)
- [x] All new UI strings have translation keys in `locales/en.json`
- [x] All new UI strings have Chinese translations in `locales/zh.json`
- [x] Locale key parity: `diff` between en.json and zh.json scalar paths is empty
- [x] Runtime translation key audit across Phase 3 files (`t('...')`, `i18n.t('...')`, `labelKey`, `descriptionKey`) has no missing keys in `en.json` or `zh.json`
- [x] CSS uses logical properties (no `text-left`/`text-right`, use `text-start`/`text-end`)
- [x] All Python tests pass: `bun run python:test`
- [x] Python backend coverage >= 80%: `bun run python:test -- --cov=src --cov-fail-under=80`
- [x] Frontend tests pass: `bun run test:run`
- [x] `bun run ast:lint` passes (enforces architecture anti-patterns)
- [x] No Zustand destructuring anti-patterns in app code (selector syntax only)
- [x] No `useUIStore(...)` subscriptions in `src/lib/**` (only `useUIStore.getState()`)
- [x] No store hook destructuring in app runtime code (`const { ... } = use*Store(...)`)
- [x] No raw `fetch()` in `src/components/**` or `src/hooks/**` (use TanStack Query hooks/services + `apiFetch`)
- [x] No active runtime string-based `invoke()` usage in app code (ignore docs/comments/tests)
- [x] Error handling follows documented patterns (`ApiRequestError` in frontend, structured exceptions in Python)
- [x] New commands registered with `labelKey` translation key (`focus-search`)
- [x] `SearchError` exception handler registered in `main.py`
- [x] Search router registered in `main.py`
- [x] `bun run openapi:sync` produces no diff in `openapi.json` and `src/types/api.gen.ts`
- [ ] End-to-end smoke test (manual): create a note with content -> wait for processing to complete -> search for keywords from the note -> verify note appears in search results -> click through to item detail

## Dependencies

- Tasks 1-8 (all Phase 3 feature work) are complete

## Technical Notes

### Pre-Flight

```bash
git status --short  # Prefer a clean working tree before running the gate
```

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
bun run python:typecheck # mypy type checking
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

Review Phase 3 files for translation usage and key mapping:

```bash
# Translation call sites and command metadata in Phase 3 scope
rg -n "t\\(|i18n\\.t\\(|labelKey:|descriptionKey:" \
  src/components/search \
  src/routes/items/index.tsx \
  src/lib/commands/search-commands.ts \
  src/hooks/use-keyboard-shortcuts.ts
```

Verify all referenced keys exist in both locale files.

### Anti-Pattern Review

- No `const { ... } = useUIStore()` / `useProcessingStore()` destructuring (use selector syntax)
- In `src/lib/**`, `useUIStore` access uses `getState()` only (no subscriptions)
- Callbacks that need current store state use `useStore.getState()`
- No new app-level manual `useMemo`/`useCallback` (React Compiler handles this)
- No active `invoke()` calls in runtime app code (typed bindings only; ignore docs/comments/tests)
- No raw `fetch()` in components/hooks (use TanStack Query hooks/services)
- Error handling follows `docs/developer/architecture/error-handling.md`

```bash
# Zustand destructuring (runtime code only)
rg -n "const\\s*\\{[^\\n]*\\}\\s*=\\s*use[A-Za-z0-9]*Store\\(" src --glob '!**/*.md'

# Store subscriptions in lib/ (disallowed; getState is allowed)
rg -n "useUIStore\\(" src/lib --glob '!**/*.md'

# Raw fetch in components/hooks (disallowed)
rg -n "\\bfetch\\(" src/components src/hooks

# invoke() usage: inspect matches and ignore comments/tests/docs
rg -n "\\binvoke\\(" src --glob '!**/*.test.*' --glob '!**/*.md'
```

### OpenAPI Sync Verification

```bash
bun run openapi:sync
git diff -- openapi.json src/types/api.gen.ts  # Should show no changes
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
- `python-backend/src/workflows/utils.py` (shared workflow utilities used by search)
- `python-backend/src/api/routes/search.py` (API endpoint)
- `python-backend/src/main.py` (router + exception handler)
- `python-backend/tests/` (search tests)

**Frontend:**

- `src/services/search.ts` (TanStack Query hooks)
- `src/lib/commands/search-commands.ts` (Cmd+F command)
- `src/store/ui-store.ts` (searchFocused state)
- `src/hooks/use-keyboard-shortcuts.ts` (Cmd+F handler)
- `src/routes/items/index.tsx` (debounced search integration)
- `src/components/search/` (all search UI components)
- `src/components/search/search-result-card.utils.ts` (snippet formatting)
- `locales/en.json` and `locales/zh.json` (search translations)

## Execution Results

Record command outputs and evidence when running this gate:

- `bun run check:all`: PASS. Full pipeline succeeds (typecheck, lint, ast-grep, format check, rust fmt/clippy/tests, python fmt/lint/typecheck/tests, vitest).
- `bun run python:typecheck`: PASS. `Success: no issues found in 37 source files`.
- `bun run python:test -- --cov=src --cov-report=term-missing --cov-fail-under=80`: PASS. `363 passed`, total coverage `92.58%` (threshold 80%).
- Locale parity diff result: PASS. `Locale parity: OK (no diff)`.
- Translation key audit result: PASS. Audited Phase 3 translation usages (`t(...)`, `i18n.t(...)`, `labelKey`, `descriptionKey`) with pluralization-aware checks; `Audited keys: 16`, no missing keys in `en.json` or `zh.json`.
- Anti-pattern audit result: PASS.
  - No Zustand destructuring matches.
  - No `useUIStore(...)` subscriptions in `src/lib/**`.
  - No store hook destructuring in runtime code.
  - No raw `fetch()` in `src/components/**` or `src/hooks/**`.
  - No runtime `invoke()` usage in app code.
  - No `text-left`/`text-right` usage in Phase 3 search/UI scope.
- OpenAPI sync diff result (`openapi.json`, `src/types/api.gen.ts`): PASS. `bun run openapi:sync` followed by `git diff -- openapi.json src/types/api.gen.ts` produced no diff.
- Manual smoke test result (steps + outcome): NOT RUN in this session (requires live app runtime). Pending user verification.

## Verification

Phase 3 is complete when all acceptance criteria pass, command outputs are captured, and the end-to-end smoke test succeeds.

## Milestone

Can search items and find relevant results.
