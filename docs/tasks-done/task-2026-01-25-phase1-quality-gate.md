# Task: Phase 1 Quality Gate

## Summary

Validate that all Phase 1 work meets quality standards before proceeding to Phase 2.

## Acceptance Criteria

- [x] `bun run check:all` passes with no errors (covers all three layers: TypeScript, Rust, Python)
- [x] All UI strings use translation keys (no hardcoded strings in components)
- [x] Translation keys exist in all locale files (`en.json`, `zh.json`) — 139 keys each, zero diff
- [x] Frontend builds without warnings
- [x] Backend starts and responds to health check — verified: `{"status":"healthy"}` with database and Ollama checks passing
- [x] Can create and list items via API — verified: POST creates item (201), GET lists it, DELETE removes it (204)
- [x] App launches and shows empty item list — verified via Vite dev server: three-pane layout with "No items yet" empty state
- [x] CSS uses logical properties (no `text-left`/`text-right`, use `text-start`/`text-end`) — fixed in 9 UI component files
- [x] Generated tauri-specta bindings are up to date

## Dependencies

- All previous Phase 1 tasks (1-10)

## Quality Checks

### Primary Gate

```bash
# Single command covers all checks across TypeScript, Rust, and Python
bun run check:all
```

This runs all 11 checks: `typecheck`, `lint`, `ast:lint`, `format:check`, `rust:fmt:check`, `rust:clippy`, `python:fmt:check`, `python:lint`, `test:run`, `rust:test`, `python:test`.

### Individual Checks (for debugging failures)

```bash
# TypeScript / Frontend
bun run typecheck       # TypeScript type checking
bun run lint            # ESLint
bun run ast:lint        # ast-grep architecture pattern enforcement
bun run format:check    # Prettier formatting
bun run test            # Vitest

# Rust
bun run rust:fmt:check  # Rust formatting
bun run rust:clippy     # Rust linting
bun run rust:test       # Rust tests

# Python
bun run python:fmt:check  # Ruff formatting
bun run python:lint       # Ruff linting
bun run python:test       # Pytest
```

### Tauri Bindings Freshness

```bash
# Regenerate bindings and verify no uncommitted changes
bun run rust:bindings
git diff --exit-code src/lib/tauri-bindings.ts
```

If `git diff` shows changes, the bindings were stale and need to be committed.

### Integration Verification

```bash
# Start backend
bun run python:dev &

# Verify health — expect: {"status": "healthy"}
curl http://localhost:8742/api/health

# Verify items endpoint — expect: {"items": [], "total": 0, "offset": 0, "limit": 20}
curl http://localhost:8742/api/items

# Start frontend (in another terminal)
bun run tauri dev
```

## Milestone Verification

From MVP plan: "Can launch app, see empty item list, backend responds to health checks"

- [x] App window opens without errors — verified via browser at localhost:1420 (2 expected Tauri-only API errors in browser context)
- [x] Three-pane layout visible — left sidebar, main content, right panel all render
- [x] Left sidebar shows navigation — "All Items" and "Conversations" entries visible
- [x] Main content shows empty items list — "All Items" heading with "No items yet. Start by adding your first item."
- [x] Backend health check returns `{"status": "healthy"}` — confirmed with database latency 0ms
- [x] Ollama health check returns status (healthy or unavailable) — returned `"status":"healthy"` with 52ms latency

## Anti-Pattern Review

### Auto-Enforced by `bun run ast:lint`

These patterns are caught automatically — verify no violations in `ast:lint` output:

- [x] No Zustand destructuring (`const { value } = useUIStore()`) — use selector syntax
- [x] Hooks are in `src/hooks/` directory, not scattered elsewhere
- [x] No store subscriptions in `src/lib/` (library code must be store-agnostic)

### Manual Review Required

These patterns require human judgment and cannot be caught by automated tooling:

- [x] Using typed Tauri commands from `@/lib/tauri-bindings`, not `invoke()` — no active `invoke()` usage found
- [x] React Compiler handles memoization (no manual `useMemo`/`useCallback`) — shadcn/ui vendored components retain upstream `useMemo`/`useCallback` by design
- [x] Proper state layer usage (`useState` → Zustand → TanStack Query)
- [x] CSS logical properties used (`text-start`/`text-end`, `ps-*`/`pe-*`, `ms-*`/`me-*`) — no physical `text-left`/`pl-*`/`mr-*`
- [x] Python backend uses custom exception hierarchy from `src/exceptions.py`
- [x] FastAPI exception handlers registered in `src/main.py`

Reference: `AGENTS.md`, `docs/developer/architecture/state-management.md`, `docs/developer/architecture/error-handling.md`

## Translation Completeness

Verify that all translation keys in `en.json` also exist in `zh.json`:

```bash
# Compare key sets between locale files
diff <(jq -S 'paths(scalars) | join(".")' locales/en.json) \
     <(jq -S 'paths(scalars) | join(".")' locales/zh.json)
```

Missing keys in `zh.json` should be added (can use English as placeholder with a TODO comment).

## Files to Review

- All new Python files in `python-backend/`
- Any modified TypeScript files in `src/`
- Translation files in `locales/`
- Rust command definitions in `src-tauri/src/`
- Generated bindings at `src/lib/tauri-bindings.ts`

## Verification

All checks pass, milestone achieved, ready for Phase 2.

---

## Implementation Details

_Tracked: 2026-01-25_

### Files Changed

| File                                             | Change   | Description                                                                        |
| ------------------------------------------------ | -------- | ---------------------------------------------------------------------------------- |
| `src/components/ui/calendar.tsx`                 | Modified | `pl-2 pr-1` → `ps-2 pe-1` (logical padding)                                        |
| `src/components/ui/command.tsx`                  | Modified | `ml-auto` → `ms-auto` (logical margin)                                             |
| `src/components/ui/dropdown-menu.tsx`            | Modified | 9 replacements: `pl-`/`pr-`/`ml-`/`left-`/`right-` → logical equivalents           |
| `src/components/ui/field.tsx`                    | Modified | `ml-4` → `ms-4` (error list margin)                                                |
| `src/components/ui/input-group.tsx`              | Modified | `pl-`/`pr-`/`ml-`/`mr-` → `ps-`/`pe-`/`ms-`/`me-` (addon alignment)                |
| `src/components/ui/native-select.tsx`            | Modified | `pr-9` → `pe-9`, `right-3.5` → `end-3.5` (select arrow)                            |
| `src/components/ui/select.tsx`                   | Modified | `pr-8 pl-2` → `pe-8 ps-2`, `right-2` → `end-2` (item indicator)                    |
| `src/components/ui/sidebar.tsx`                  | Modified | `ml-0`/`ml-2` → `ms-0`/`ms-2`, `text-left` → `text-start`, `pr-8` → `pe-8`         |
| `src/components/ui/tag-input.tsx`                | Modified | `ml-1` → `ms-1` (tag remove button)                                                |
| `package.json`                                   | Modified | Added `python:dev` script for backend development                                  |
| `docs/tasks-todo/task-11-phase1-quality-gate.md` | Modified | Updated acceptance criteria with verification results; expanded quality check docs |

### Dependencies Added

None.

### Acceptance Criteria Status

- [x] `bun run check:all` passes — all 11 checks pass (typecheck, lint, ast:lint, format:check, rust:fmt:check, rust:clippy, python:fmt:check, python:lint, test:run, rust:test, python:test)
- [x] All UI strings use translation keys — verified, 139 keys in both `en.json` and `zh.json`
- [x] Translation keys exist in all locale files — zero diff between key sets
- [x] Frontend builds without warnings — confirmed
- [x] Backend starts and responds to health check — `{"status":"healthy"}` with database and Ollama checks
- [x] Can create and list items via API — POST/GET/DELETE verified
- [x] App launches and shows empty item list — three-pane layout with empty state
- [x] CSS uses logical properties — fixed in 9 UI component files (this task's direct code changes)
- [x] Generated tauri-specta bindings are up to date — confirmed

---

## Learning Report

_Generated: 2026-01-25_

### Summary

Task 11 was a quality gate validating all Phase 1 work (tasks 1-10) before proceeding to Phase 2. The gate covered three layers (TypeScript frontend, Rust middle layer, Python backend) across 11 automated checks, manual architecture pattern review, integration verification, and milestone acceptance.

The direct code changes were small and focused: converting 9 shadcn/ui component files from physical CSS properties (`pl-`, `mr-`, `text-left`, `left-`, `right-`) to CSS logical properties (`ps-`, `me-`, `text-start`, `start-`, `end-`) for RTL language support. A `python:dev` convenience script was also added to `package.json`.

**Metrics:** 11 files changed, 104 insertions, 60 deletions. 39 frontend tests, 4 Rust tests, 89 Python tests — all passing. 92% Python backend coverage.

### Patterns & Decisions

1. **CSS Logical Properties for RTL**: All physical directional CSS classes in vendored shadcn/ui components were replaced with logical equivalents. The mapping is consistent:
   - Padding: `pl-` → `ps-`, `pr-` → `pe-`
   - Margin: `ml-` → `ms-`, `mr-` → `me-`
   - Position: `left-` → `start-`, `right-` → `end-`
   - Text: `text-left` → `text-start`

2. **Vendored Component Updates**: shadcn/ui components are vendored in `src/components/ui/`. Upstream uses physical properties; the project convention is to use logical properties post-vendor. This is a manual step when pulling new components.

3. **`bun run check:all` as Single Gate**: The consolidated check command runs all 11 checks sequentially. This proved effective — a single command validates the entire stack with zero configuration.

4. **shadcn/ui `useMemo`/`useCallback` Exception**: The React Compiler handles memoization automatically per project rules, but vendored shadcn/ui components retain upstream `useMemo`/`useCallback` calls. This is by design — modifying vendored code unnecessarily would create merge friction. Documented in the acceptance criteria notes.

### Challenges & Solutions

1. **Identifying All Physical CSS Properties**: The 9 affected files were found by searching for `pl-`, `pr-`, `ml-`, `mr-`, `text-left`, `left-`, `right-` in `src/components/ui/`. The `dropdown-menu.tsx` had the most replacements (9 instances) due to its many sub-components (item, checkbox item, radio item, label, shortcut, sub-trigger).

2. **Tauri API Errors in Test Environment**: The App test suite logs `Cannot read properties of undefined (reading 'transformCallback')` errors from Tauri API calls in the Vitest environment. These are expected — Tauri APIs aren't available outside the native window context. The errors are caught and logged, not thrown, so tests pass.

3. **CodeRabbit Review**: CodeRabbit completed with no findings for these changes. The CSS logical property conversions are straightforward mechanical transformations with no security or logic concerns.

### Lessons Learned

1. **Quality gates should be explicit and checklistable.** The expanded acceptance criteria (with verification notes) serve as a permanent record of what was validated and how. Future quality gates should follow this pattern.

2. **`check:all` catches cross-layer issues.** Running TypeScript, Rust, and Python checks in a single command prevented missed regressions. The ast-grep rules for architecture patterns (no Zustand destructuring, hooks in correct directory) are particularly valuable.

3. **Vendored UI components need a post-vendor checklist.** When pulling new shadcn/ui components, the following should be applied:
   - Convert physical CSS properties to logical equivalents
   - Verify no `invoke()` calls (should use typed commands)
   - Keep upstream `useMemo`/`useCallback` as-is (React Compiler exception)

4. **Integration verification requires a running backend.** The health check and CRUD endpoint tests run against in-memory SQLite in pytest, but the integration verification (`curl` commands) requires the actual FastAPI server. The new `bun run python:dev` script makes this easier.

### Documentation Impact

- **`docs/developer/ui-ux/i18n-patterns.md`**: Should include the CSS logical property mapping table and note about vendored component post-processing.
- **Quality gate template**: The expanded format of this task file (with verification notes, anti-pattern categories, and translation completeness checks) could serve as a template for future quality gates.
- **Vendored component checklist**: Consider adding a `docs/developer/ui-ux/shadcn-component-checklist.md` for the post-vendor steps (logical properties, i18n, etc.).
