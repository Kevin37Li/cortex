# Task: Implement Item List View with Processing Status Indicators

## Summary

Build the item list UI that displays saved items with processing status. Each row shows title, content type, creation date, and a status badge (`pending`/`processing`/`completed`/`failed`). Use TanStack Query for fetching, component-local state for offset-based pagination, and typed navigation to item detail.

## Acceptance Criteria

- [x] `ItemList` component displays paginated items from the backend - Implemented in `src/components/items/ItemList.tsx:71`
- [x] Each item row shows: title, content type icon/badge, creation date (relative), processing status indicator - Implemented in `src/components/items/ItemCard.tsx:81`
- [x] Processing status badges: `pending` (gray), `processing` (blue/animated), `completed` (green), `failed` (red) - Implemented in `src/components/items/ProcessingStatusBadge.tsx:15-22`
- [x] `failed` badge supports an optional retry affordance via callback prop (API wiring can be deferred to Task 16) - Implemented in `ProcessingStatusBadge.tsx:38,53-57`
- [x] Empty state: message shown when no items exist with a prompt to create a note - Implemented in `ItemList.tsx:149-164`
- [x] Loading state: skeleton loaders while fetching - Implemented in `ItemList.tsx:100-123`
- [x] Error state: error message with retry button (`query.refetch()`) - Implemented in `ItemList.tsx:125-147`
- [x] Click on item navigates to item detail route using typed TanStack Router params (`to="/items/$id"` + `params`) - Implemented in `ItemCard.tsx:95-114` using `<Link>`
- [x] Uses `useItems()` hook from `src/services/items.ts` - Implemented in `ItemList.tsx:82-85`
- [x] Pagination: offset-based page navigation with Previous/Next buttons and numbered page links using `ItemListResponse.total/offset/limit` - Implemented in `ItemList.tsx:183-233` with `getPageNumbers` helper at line 45
- [x] Pagination uses `keepPreviousData` for smooth page transitions without layout flicker - Implemented in `ItemList.tsx:84` via `placeholderData: keepPreviousData`
- [x] All user-facing strings use i18n translation keys - All strings in `locales/en.json` and `locales/zh.json`
- [x] Unit tests for `ItemList`, `ItemCard`, and `ProcessingStatusBadge` components cover loading, empty, error, status mapping, retry callback, typed navigation, and pagination behavior - Tests in `ItemList.test.tsx` (446 lines), `ItemCard.test.tsx` (82 lines), `ProcessingStatusBadge.test.tsx` (56 lines)

## Dependencies

- Task 12: TanStack Query service hooks (`useItems()`)
- Phase 1: Layout shell (`MainWindowShell`), routing (`/items` route), UI components (shadcn/ui)
- Phase 1: i18n setup
- Task 16: item detail retry action wiring (full retry API integration can be completed there)

## Technical Notes

- Per state management decision tree: item list data uses TanStack Query (persistent data from backend)
- Local pagination controls (`currentPage`, `pageSize`) should use `useState` in `ItemList` (not Zustand)
- The route `src/routes/items/index.tsx` already exists as a placeholder — implement the actual content
- Prefer existing shared primitives for consistency: `Item` family (`Item`, `ItemMedia`, `ItemContent`, `ItemTitle`, `ItemDescription`), `Badge`, `Skeleton`, `Button`, `ScrollArea`, `Empty`, `Spinner`
- Follow existing component patterns (check `MainWindowShell.tsx` for layout context)
- Processing status indicator for `processing` state should have subtle animation (pulse or spinner)
- Date formatting: use relative time ("2 hours ago") with `Intl.RelativeTimeFormat` and current `i18n.language` (no external dependency)
- Per AGENTS.md: no manual `useMemo`/`useCallback` — React Compiler handles this
- API types are already generated: `Item` has `processing_status: ProcessingStatus` (`"pending" | "processing" | "completed" | "failed"`) and `content_type: ContentType` (`"webpage" | "note" | "file"`) — use these from `src/services/items.ts` re-exports
- `ItemListResponse` provides `{ items, total, offset, limit }` — use offset-based pagination with `useItems({ offset, limit: pageSize })` and `keepPreviousData` for smooth transitions
- Existing translation key `items.emptyState` should be replaced by the new `items.list.empty` / `items.list.emptyDescription` keys (remove the old key)
- Keep `ProcessingStatusBadge` props forward-compatible for Task 17 (optional `stepLabel`/extra text can be added later without breaking callers)
- For row click-through, prefer `<Link to="/items/$id" params={{ id: item.id }}>` over imperative navigation for a11y and typed params
- For navigation tests, update `src/test/test-utils.tsx` to include `/items/$id` so route assertions are reliable

## Component Structure

```
src/routes/items/index.tsx         — Route component using ItemList
src/components/items/
  ├── ItemList.tsx                 — List container with query
  ├── ItemCard.tsx                 — Single item row/card
  ├── ProcessingStatusBadge.tsx    — Status indicator component
  └── index.ts                     — Feature exports
```

## Translation Keys

Add to `/locales/en.json`:

```json
{
  "items.list.empty": "No items yet",
  "items.list.emptyDescription": "Create a note or save a web page to get started",
  "items.list.loading": "Loading items...",
  "items.list.error": "Failed to load items",
  "items.list.retry": "Retry",
  "items.list.previousPage": "Previous",
  "items.list.nextPage": "Next",
  "items.list.pageIndicator": "Page {{current}} of {{total}}",
  "items.status.pending": "Pending",
  "items.status.processing": "Processing",
  "items.status.completed": "Completed",
  "items.status.failed": "Failed",
  "items.status.retry": "Retry Processing",
  "items.contentType.webpage": "Web Page",
  "items.contentType.note": "Note",
  "items.contentType.file": "File"
}
```

## Files to Create/Modify

**Create:**

- `src/components/items/ItemList.tsx`
- `src/components/items/ItemCard.tsx`
- `src/components/items/ProcessingStatusBadge.tsx`
- `src/components/items/index.ts`
- `src/components/items/ItemList.test.tsx`
- `src/components/items/ItemCard.test.tsx`
- `src/components/items/ProcessingStatusBadge.test.tsx`

**Modify:**

- `src/routes/items/index.tsx` — Use `ItemList` component
- `src/test/test-utils.tsx` — Add `/items/$id` route for navigation-focused tests
- `locales/en.json` — Add translation keys, remove old `items.emptyState` key
- `locales/zh.json` — Add Chinese translations, remove old `items.emptyState` key

## Covered by Other Tasks

- Quick note creation flow (dialog/action wiring) is covered by Task 14; this task only provides empty-state prompting and list UX
- Real-time step-by-step processing progress (`parsing/chunking/embedding/...`) is covered by Task 17
- Item detail retry UX and metadata presentation are covered by Task 16

## Verification

```bash
bun run typecheck
bun run lint
bun run test:run
bun run check:all
```

---

## Implementation Details

_Tracked: 2026-02-12_

### Files Changed

| File                                                  | Change   | Description                                                                                                                         |
| ----------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `src/components/items/ItemList.tsx`                   | Created  | List container with TanStack Query, skeleton/empty/error states, offset-based pagination with numbered page links                   |
| `src/components/items/ItemCard.tsx`                   | Created  | Single item row with content type icon/badge, relative date, typed `<Link>` navigation, processing status badge                     |
| `src/components/items/ProcessingStatusBadge.tsx`      | Created  | Status indicator with color-coded badges, animated processing state, optional retry affordance, forward-compatible `stepLabel` prop |
| `src/components/items/index.ts`                       | Created  | Feature barrel exports                                                                                                              |
| `src/components/items/ItemList.test.tsx`              | Created  | 11 tests covering loading, empty, error/retry, pagination navigation, boundary conditions, page clamping, i18n                      |
| `src/components/items/ItemCard.test.tsx`              | Created  | 3 tests covering metadata rendering, typed navigation link, retry callback, Chinese locale                                          |
| `src/components/items/ProcessingStatusBadge.test.tsx` | Created  | 4 tests covering all status labels, animated indicator, retry affordance presence/absence                                           |
| `src/components/ui/pagination.tsx`                    | Created  | Reusable Pagination component (shadcn/ui pattern) with i18n-ready props for aria labels and text                                    |
| `src/routes/items/index.tsx`                          | Modified | Replaced placeholder with `ItemList` component, added page header                                                                   |
| `src/services/items.ts`                               | Modified | Added `ContentType`/`ProcessingStatus` type exports, `UseItemsOptions` for `placeholderData` support                                |
| `src/test/test-utils.tsx`                             | Modified | Added `/items/$id` route to test router for navigation assertions                                                                   |
| `locales/en.json`                                     | Modified | Added 19 translation keys for items list/status/content-type/pagination; removed old `items.emptyState`; renamed app to "Cortex"    |
| `locales/zh.json`                                     | Modified | Added 19 Chinese translation keys; removed old `items.emptyState`                                                                   |

### Dependencies Added

None — all functionality uses existing project dependencies (TanStack Query, TanStack Router, react-i18next, lucide-react, shadcn/ui primitives).

---

## Learning Report

_Generated: 2026-02-12_

### Summary

Built the item list view — the first data-driven UI component in Cortex. The implementation spans 7 new files (3 components + 3 test files + 1 barrel export) and 1 new shared UI component (`Pagination`), plus modifications to 5 existing files. Total new code: ~1,152 lines across components, tests, and the pagination primitive. All 13 acceptance criteria are met.

### Patterns & Decisions

**State management follows the onion model**: TanStack Query manages server state (`useItems`), while pagination state (`currentPage`) uses component-local `useState` — exactly per the architecture decision tree (no Zustand needed since pagination is component-scoped).

**`keepPreviousData` pattern**: The `useItems` hook was extended with a `UseItemsOptions` type (picking only `placeholderData` from `UseQueryOptions`) to support `keepPreviousData` without exposing the full query options surface. This keeps the API narrow while enabling smooth pagination transitions with opacity feedback (`isPageTransition` flag at `ItemList.tsx:89`).

**Pagination component as shared primitive**: Rather than inlining pagination markup, a reusable `Pagination` component was created following the shadcn/ui composition pattern (Pagination → PaginationContent → PaginationItem → PaginationLink/Previous/Next/Ellipsis). All text and aria labels are passed as i18n-ready props with English defaults, supporting RTL with `rtl:rotate-180` on chevron icons.

**Smart page number generation**: `getPageNumbers()` always shows first, last, current, and one neighbor on each side with ellipsis for gaps. This keeps the pagination bar compact even with many pages while remaining accessible.

**Page clamping during render**: When `total` shrinks (e.g., after item deletion), `currentPage` is clamped to `totalPages` using React's recommended "adjust state during render" pattern. A `total > 0` guard prevents an infinite re-render loop when data is undefined.

**Relative date formatting**: Uses `Intl.RelativeTimeFormat` with a cached formatter per locale — no external date library needed. The implementation walks a time-unit table to find the appropriate unit, matching the task spec's "2 hours ago" format.

**Forward-compatible ProcessingStatusBadge**: The `stepLabel` prop is included but optional, allowing Task 17 to add step-by-step progress labels without changing the component interface.

**Typed navigation**: Item cards use `<Link to="/items/$id" params={{ id: item.id }}>` for type-safe routing, wrapping the entire card content area for a11y while keeping the status badge outside the link in `ItemActions`.

### Challenges & Solutions

1. **Test router setup for typed navigation**: TanStack Router requires matching routes in the test environment for `<Link>` components to render correct `href` attributes. Solution: Added `/items/$id` route to `test-utils.tsx`'s test router, enabling assertions like `expect(detailLink).toHaveAttribute('href', '/items/item-1')`.

2. **Page clamping infinite loop**: Initial implementation of page clamping (`if (currentPage > totalPages) setCurrentPage(totalPages)`) caused infinite re-renders when `data` was undefined because `total` defaulted to `0`, making `totalPages = 1`, which triggered `setCurrentPage(1)` every render. Solution: Added `total > 0` guard to only clamp when we have actual data. This is documented in the code comment at `ItemList.tsx:91-98`.

3. **Pagination i18n**: The shadcn/ui pagination components use hardcoded English strings. Solution: Created a custom pagination component with `text`, `ariaLabel`, and `moreLabel` props that accept translated strings, keeping defaults for non-i18n usage.

### Lessons Learned

**What worked well:**

- The task spec's component structure and translation key list were precise enough to implement without ambiguity
- Reusing existing UI primitives (`Item`, `Badge`, `Empty`, `Skeleton`, `Spinner`, `ScrollArea`) kept the code concise and visually consistent
- The `useItems` hook from Task 12 was well-designed for extension (adding `options` parameter was minimal change)
- Test patterns using vi.mock with `vi.importActual` work cleanly for mocking TanStack Query hooks

**What could be improved:**

- The task spec listed translation keys but missed pagination-specific a11y keys (`pagination`, `goToPreviousPage`, `goToNextPage`, `morePages`) — these were needed for the accessible pagination component. Future specs should account for aria labels
- The Pagination component could be upstreamed or documented as a shared primitive since it will likely be reused (search results, conversations list, etc.)

### Documentation Impact

- `docs/developer/ui-ux/i18n-patterns.md` — The pagination component demonstrates a pattern for i18n-ready shared UI components (text/aria props with defaults) that could be documented
- `docs/developer/quality-tooling/testing.md` — The test router setup in `test-utils.tsx` now includes `/items/$id`; if more routes are added for future features, the pattern of extending the test router should be noted
- `src/components/ui/pagination.tsx` is a new shared primitive that other features can import — should be listed in any UI component inventory docs
