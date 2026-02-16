# Task: Phase 2 Quality Gate and Translation Audit

## Summary

Final quality gate for Phase 2: verify all translation keys are complete (English + Chinese), all checks pass, all tests pass, and the end-to-end flow works (create note → process → view metadata). This task ensures Phase 2 meets the quality standards before moving to Phase 3.

## Acceptance Criteria

- [x] `bun run check:all` passes with no errors
- [x] All new UI strings have translation keys in `locales/en.json`
- [x] All new UI strings have Chinese translations in `locales/zh.json`
- [x] CSS uses logical properties (no `text-left`/`text-right`, use `text-start`/`text-end`)
- [x] All Python tests pass: `bun run python:test`
- [x] Python backend coverage is >= 80%: `bun run python:test -- --cov=src --cov-fail-under=80`
- [x] Frontend tests pass: `bun run test:run`
- [x] `bun run ast:lint` passes (enforces architecture anti-patterns)
- [x] No Zustand destructuring anti-patterns in app code (selector syntax only)
- [x] Store access in `src/lib/**` uses `useStore.getState()` (no store subscriptions)
- [x] Callbacks that need latest store state use `useStore.getState()` where applicable
- [x] No raw `fetch()` in `src/components/**` or `src/hooks/**` (use TanStack Query hooks/services + `apiFetch`)
- [x] No active string-based `invoke()` usage in app code (use typed commands from `@/lib/tauri-bindings`)
- [x] No blocking AI operations in UI path; processing flow remains async with progress indicators
- [x] Error handling follows documented patterns (`ApiRequestError` in frontend, structured exceptions in Python)
- [x] New commands registered with `labelKey` translation key
- [x] If new Zustand stores were added, `.ast-grep/rules/zustand/no-destructure.yml` is updated
- [x] If new Tauri commands were added, `src/test/setup.ts` includes mocks
- [ ] End-to-end smoke test: create a note → verify it appears in list → verify processing starts → verify metadata appears in detail view (manual, pending)

## Execution Results (2026-02-16)

- `bun run check:all`: passed (typecheck, lint, ast-grep, format, Rust checks/tests, frontend tests, Python tests)
- `bun run python:test -- --cov=src --cov-report=term-missing --cov-fail-under=80`: passed with `TOTAL 90.99%` coverage
- Locale parity check (`diff` + `jq`): no differences between `locales/en.json` and `locales/zh.json` scalar key paths
- Runtime translation key audit (`t(...)`, `i18n.t(...)`, `labelKey`, `descriptionKey` across `src/**` excluding tests): missing keys in `en.json` = `0`, in `zh.json` = `0`
- CSS logical property audit: no `text-left` / `text-right` matches in `src/`
- Raw fetch audit: no `fetch(` matches in `src/components/**` or `src/hooks/**`
- String-based invoke audit: no active runtime `invoke(...)` usage detected

## Dependencies

- Tasks 12-17 (Phase 2 feature work) are complete

## Technical Notes

- Per MVP plan "Quality Gate (Per Phase)": run `bun run check:all`, verify translations, confirm tests pass, review anti-patterns
- Per AGENTS.md and state management docs: avoid Zustand destructuring; use `getState()` in non-React contexts/callbacks that need latest state
- React Compiler handles memoization; no new app-level manual `useMemo`/`useCallback` (vendored shadcn/ui exceptions may exist)
- The smoke test is manual (no automated E2E framework in MVP); run by user and record results
- If any issues found, fix them before marking this task complete
- Python mypy type-checking is tracked separately in Task 19

## Checklist

### Pre-Flight

```bash
git status --short  # Prefer a clean working tree before running the gate
```

### Authoritative Check

```bash
bun run check:all     # Runs ALL checks below — this is the gate
```

The individual commands below are for reference/debugging when `check:all` fails.

### Frontend Checks (included in check:all)

```bash
bun run typecheck     # TypeScript compiles
bun run lint          # ESLint passes
bun run ast:lint      # ast-grep architecture patterns
bun run format:check  # Prettier formatted
bun run test:run      # Vitest passes (single-run, not watch mode)
```

### Rust Checks (included in check:all)

```bash
bun run rust:fmt:check  # Rust formatting
bun run rust:clippy     # Rust linting
bun run rust:test       # Rust tests
```

### Python Checks (included in check:all)

```bash
bun run python:lint      # Ruff linting
bun run python:fmt:check # Ruff formatting
bun run python:test      # All tests pass
```

### Python Coverage (separate from check:all)

Coverage is not enforced by `check:all` and must be run manually:

```bash
bun run python:test -- --cov=src --cov-report=term-missing --cov-fail-under=80
```

Type checking with mypy is tracked separately in Task 19.

### Periodic Cleanup (recommended)

Phase boundaries are the right time for periodic cleanup:

```bash
bun run knip   # Detect unused exports, dead code
bun run jscpd  # Detect duplicated code blocks
```

Or use the `/cleanup` command in Claude Code.

### Translation Audit

```bash
# Locale key parity (must be empty output)
diff <(jq -S 'paths(scalars) | join(".")' locales/en.json) \
     <(jq -S 'paths(scalars) | join(".")' locales/zh.json)
```

- Grep changed Phase 2 UI files for hardcoded user-facing strings
- Verify `t('...')`, `i18n.t('...')`, and command `labelKey`/`descriptionKey` references map to locale keys
- Check for obvious orphan keys introduced in this phase (remove or document intentionally reserved keys)

### Anti-Pattern Review

- No `const { ... } = useUIStore()` / `useProcessingStore()` destructuring (use selector syntax)
- In `src/lib/**`, store access uses `getState()` (no store subscriptions)
- Callbacks that need current store state use `useStore.getState()` to avoid stale subscriptions
- No new app-level manual `useMemo`/`useCallback` (React Compiler); ignore existing vendored shadcn/ui exceptions
- No active `invoke()` calls in runtime app code (typed bindings only)
- No raw `fetch()` in components/hooks (use TanStack Query hooks/services)
- No synchronous/blocking AI calls in UI layer (use async patterns with progress indicators)
- Error handling follows `docs/developer/architecture/error-handling.md` (structured Python exceptions, `ApiRequestError` in frontend, no swallowed errors)
- If new stores were added, update `.ast-grep/rules/zustand/no-destructure.yml`
- If new Tauri commands were added, update `src/test/setup.ts`

## Files to Review

- All files created/modified in tasks 12-17
- `src/services/items.ts`
- `src/components/items/ItemList.tsx`
- `src/components/items/QuickNoteDialog.tsx`
- `src/components/items/FileImportButton.tsx`
- `src/components/items/ItemDetail.tsx`
- `src/components/items/ProcessingStatusBadge.tsx`
- `src/hooks/use-processing-websocket.ts`
- `src/store/processing-store.ts`
- `src/lib/commands/note-commands.ts`
- `src/lib/commands/import-commands.ts`
- `locales/en.json` and `locales/zh.json` for completeness
- `.ast-grep/rules/zustand/no-destructure.yml` for new store coverage
- `src/test/setup.ts` for new Tauri command mocks

## Verification

Phase 2 is complete when all acceptance criteria above pass, command outputs are captured, and the end-to-end smoke test succeeds.

## Milestone

Can create a note → see it process → view extracted metadata
