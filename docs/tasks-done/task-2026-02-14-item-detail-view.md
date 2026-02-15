# Task: Implement Item Detail View

## Summary

Build the item detail view that displays the full content, metadata, and processing status of a single item. Shown when a user clicks an item from the list. Displays the item's title, content, content type, source URL, creation date, processing status, and extracted metadata (summary, concepts, entities) once processing is complete.

## Acceptance Criteria

- [x] `ItemDetail` component displays full item data from `useItem(id)` hook - Implemented in `src/components/items/ItemDetail.tsx:59-268`
- [x] Header shows title, content type badge, and absolute creation date - Implemented in `ItemDetail.tsx:184-195`
- [x] Content section renders full item content with preserved line breaks (`whitespace-pre-wrap`) and no `dangerouslySetInnerHTML` - Implemented in `ItemDetail.tsx:197-204`
- [x] Source URL renders only when present and opens in default browser via `openUrl` - Implemented in `ItemDetail.tsx:162-177, 206-221`
- [x] Processing section reuses `ProcessingStatusBadge` for status display - Implemented in `ItemDetail.tsx:223-258`
- [x] Failed state includes retry action wired to `useRetryProcessing` - Implemented in `ItemDetail.tsx:229-240`
- [x] Retry action handles API outcomes (`retried`, `already_queued`, `not_in_queue`) with user feedback - Implemented in `ItemDetail.tsx:147-160`
- [x] Metadata section renders when `processing_status === 'completed'` and shows summary, concept tags, entity tags - Implemented in `ItemDetail.tsx:261-263`, `ItemMetadataSection.tsx:16-87`
- [x] Failed items show processing error details from metadata (`processing_error`, `error_step`) when available - Implemented in `ItemDetail.tsx:243-258`
- [x] Loading state uses skeleton UI - Implemented in `ItemDetail.tsx:74-89`
- [x] Not-found state shows dedicated "Item not found" UI - Implemented in `ItemDetail.tsx:91-134`
- [x] Generic error state shows retry refetch action - Implemented in `ItemDetail.tsx:91-134`
- [x] Back navigation to item list (`/items`) - Implemented in `ItemDetail.tsx:64-72`
- [x] All user-facing strings use i18n keys (English + Chinese) - Implemented in `locales/en.json`, `locales/zh.json`
- [x] Unit tests cover detail states and retry mutation behavior - Implemented in `ItemDetail.test.tsx`, `ItemMetadataSection.test.tsx`, `items.test.ts`

## Dependencies

- Task 12: TanStack Query item service hooks and query keys (`useItem`, `itemQueryKeys`)
- Task 13: Item list/detail navigation source and `ProcessingStatusBadge`
- Phase 1: Routing (`/items/$id` placeholder route exists), UI primitives, i18n setup
- Task 17: Real-time step-level websocket progress (this task should be compatible, not implement websocket integration)

## Technical Notes

- The route `src/routes/items/$id.tsx` already exists as a placeholder — replace it with the actual detail page content.
- Use `useItem(id)` from `src/services/items.ts` for data fetching.
- Metadata is in `item.metadata` and currently includes extraction fields `summary`, `concepts`, `entities`; failed items may also include `processing_error` and `error_step`.
- For source URLs, use `openUrl` from `@tauri-apps/plugin-opener`:
  - `import { openUrl } from '@tauri-apps/plugin-opener'`
- Add `useRetryProcessing` in `src/services/items.ts`:
  - Call `POST /api/processing/retry` with `{ item_id }`
  - Use API-generated schema types (`RetryRequest`, `RetryResponse`) from `components['schemas']`
  - Invalidate `itemQueryKeys.lists()` and `itemQueryKeys.detail(itemId)` on success
  - Log technical errors in the service hook; keep user toasts/notifications in UI handlers (explicit handling)
- `POST /api/processing/retry` returns `outcome` in addition to `retried_count`; UI must handle:
  - `retried`
  - `already_queued`
  - `not_in_queue`
- Replace placeholder translation usage:
  - Keep `items.detail.title`
  - Remove `items.detail.viewing` from route and locale files
- Use `Intl.DateTimeFormat` with `i18n.language` for absolute creation date display in detail view.
- For not-found handling: backend currently returns `Item not found: {id}` message for missing item IDs; use that for 404-specific UI in this task.
- Add test mock for `@tauri-apps/plugin-opener` in `src/test/setup.ts`.
- Follow architecture constraints: no raw `fetch()` in components, no Zustand destructuring anti-patterns.

## Component Structure

```text
src/routes/items/$id.tsx              — Route component (detail page)
src/components/items/
  ├── ItemDetail.tsx                  — Main detail view
  ├── ItemMetadataSection.tsx         — Summary, concepts, entities display
  └── ProcessingStatusBadge.tsx       — Reused from task 13
```

## Translation Keys

Add to `/locales/en.json` and `/locales/zh.json` (remove existing `items.detail.viewing`, keep `items.detail.title`):

```json
{
  "items.detail.content": "Content",
  "items.detail.metadata": "Extracted Metadata",
  "items.detail.summary": "Summary",
  "items.detail.concepts": "Key Concepts",
  "items.detail.entities": "Entities",
  "items.detail.source": "Source",
  "items.detail.created": "Created",
  "items.detail.notFound": "Item not found",
  "items.detail.notFoundDescription": "This item may have been deleted",
  "items.detail.back": "Back to Items",
  "items.detail.retryProcessing": "Retry Processing",
  "items.detail.processingFailed": "Processing failed",
  "items.detail.retryQueued": "Item is already queued for processing",
  "items.detail.retryNotInQueue": "Item is not currently retryable",
  "items.detail.retrySucceeded": "Retry queued"
}
```

## Files to Create/Modify

**Create:**

- `src/components/items/ItemDetail.tsx`
- `src/components/items/ItemMetadataSection.tsx`
- `src/components/items/ItemDetail.test.tsx`
- `src/components/items/ItemMetadataSection.test.tsx`

**Modify:**

- `src/routes/items/$id.tsx` — Replace placeholder with detail page
- `src/services/items.ts` — Add `useRetryProcessing` mutation hook
- `src/services/items.test.ts` — Add retry mutation tests (success + outcomes + errors)
- `src/components/items/index.ts` — Export `ItemDetail` and `ItemMetadataSection`
- `src/test/setup.ts` — Add mock for `@tauri-apps/plugin-opener`
- `locales/en.json` — Add detail keys, remove `items.detail.viewing`
- `locales/zh.json` — Add Chinese translations for new detail keys, remove `items.detail.viewing`

## Covered by Other Tasks

- Live websocket step labels and reconnect behavior are implemented in Task 17 (`useProcessingUpdates` + detail integration).
- Phase-level audit and full regression verification are covered in Task 18.

## Verification

```bash
bun run typecheck
bun run lint
bun run test:run
bun run check:all
```

---

## Implementation Details

_Tracked: 2026-02-14_

### Files Changed

| File                                                | Change   | Description                                                                                                  |
| --------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------ |
| `src/components/items/ItemDetail.tsx`               | Created  | Main detail view component with loading/error/not-found/success states, retry processing, source URL opening |
| `src/components/items/ItemMetadataSection.tsx`      | Created  | Extracted metadata display (summary, concepts, entities) shown when processing is completed                  |
| `src/components/items/ItemMetadataSection.utils.ts` | Created  | Type-safe metadata parsing utilities (getMetadataRecord, getMetadataString, getMetadataStringList)           |
| `src/components/items/ItemDetail.test.tsx`          | Created  | 10 test cases covering all detail states, retry outcomes, source URL handling                                |
| `src/components/items/ItemMetadataSection.test.tsx` | Created  | 2 test cases for metadata rendering and empty-state handling                                                 |
| `src/routes/items/$id.tsx`                          | Modified | Replaced placeholder with actual `ItemDetail` component usage                                                |
| `src/services/items.ts`                             | Modified | Added `useRetryProcessing` mutation hook, exported `RetryRequest`/`RetryResponse` types                      |
| `src/services/items.test.ts`                        | Modified | Added 3 retry mutation tests (outcome handling, error logging, structured errors)                            |
| `src/lib/api-config.ts`                             | Modified | Added `ApiRequestError` class with status/path/code metadata for structured error handling                   |
| `src/lib/api-config.test.ts`                        | Modified | Added test for `ApiRequestError` metadata propagation                                                        |
| `src/components/items/index.ts`                     | Modified | Added exports for `ItemDetail` and `ItemMetadataSection`                                                     |
| `src/test/setup.ts`                                 | Modified | Added mock for `@tauri-apps/plugin-opener`                                                                   |
| `locales/en.json`                                   | Modified | Added 21 detail view i18n keys, removed `items.detail.viewing`                                               |
| `locales/zh.json`                                   | Modified | Added 21 Chinese translation keys, removed `items.detail.viewing`                                            |

### Dependencies Added

- None (all dependencies were already available from prior tasks)

---

## Learning Report

_Generated: 2026-02-14_

### Summary

Built the complete item detail view for Cortex, consisting of 3 new components (`ItemDetail`, `ItemMetadataSection`, `ItemMetadataSection.utils`) and 1 new mutation hook (`useRetryProcessing`). The implementation covers all detail states (loading skeleton, not-found, generic error, full content display), retry processing with outcome-specific toast feedback, source URL opening via Tauri plugin, and extracted metadata display. Enhanced the API layer with a structured `ApiRequestError` class enabling reliable 404 detection for not-found UI. Total: 14 files changed, ~266 lines added, comprehensive test coverage with 15 new test cases.

### Patterns & Decisions

1. **ApiRequestError class** (`api-config.ts`): Extended the generic `Error` → `ApiRequestError` pattern to carry `status`, `path`, and `code` metadata from backend error responses. This enables the detail view to distinguish 404 not-found from generic errors without fragile string matching alone. The error class is constructed in `apiFetch` and used defensively in the component (checking both `code` and `message` for backwards compatibility).

2. **Metadata parsing utilities** (`ItemMetadataSection.utils.ts`): Extracted metadata type narrowing into a separate utils file with pure functions (`getMetadataRecord`, `getMetadataString`, `getMetadataStringList`). This keeps the component clean and makes the parsing logic independently testable. The `Item['metadata']` type from the API schema allows `null | object | array`, so the utils handle all variants safely.

3. **DateTimeFormat caching** (`ItemDetail.tsx:34-52`): Used a module-level `Map` cache for `Intl.DateTimeFormat` instances keyed by locale. This avoids recreating formatters on every render while supporting locale changes.

4. **Retry outcome handling**: The `useRetryProcessing` hook returns the full `RetryResponse` from `mutateAsync`, and the UI component maps outcomes to different toast types (`success`/`info`/`warning`). Technical errors are logged in the hook's `onError`, while user-facing feedback is handled explicitly in the component — following the task spec's separation of concerns.

5. **Component composition**: The route file (`$id.tsx`) is minimal — just param extraction and delegation to `ItemDetail`. The detail component handles all state branching internally, keeping the route clean.

### Challenges & Solutions

1. **Not-found detection**: The backend returns a plain error message `"Item not found: {id}"` without a standardized error code in all cases. Solved by introducing `ApiRequestError` with a `code` field parsed from the structured `{ error, message }` response body. The component checks `code === 'item_not_found'` first, with a fallback to message string matching for robustness.

2. **Metadata type safety**: The `Item['metadata']` type from the OpenAPI schema is `Record<string, unknown> | unknown[] | null`, making it tricky to safely extract string/array fields. The utils approach with explicit type narrowing at each level provides safety without verbose inline checks in the component.

### Lessons Learned

1. **Structured API errors pay off**: Adding `ApiRequestError` was a small investment that made the not-found vs. generic error branching clean and reliable. This pattern should be used for any future error-specific UI handling.

2. **Separate utils from components**: Extracting the metadata parsing into `ItemMetadataSection.utils.ts` kept the component focused on rendering and made the parsing logic easy to test in isolation. Good pattern for any component that needs non-trivial data transformation.

3. **Test structure**: The `createItemQueryResult` / `createRetryMutationResult` helper pattern for mocking TanStack Query return values is clean and reusable. Each test case only specifies the overrides it cares about.

### Documentation Impact

- `docs/developer/core-systems/` could benefit from documenting the `ApiRequestError` pattern for structured error handling in service hooks
- The retry processing endpoint (`POST /api/processing/retry`) and its outcome semantics are now exercised and tested, which validates the API contract
- No existing docs were found to be inaccurate based on this implementation
