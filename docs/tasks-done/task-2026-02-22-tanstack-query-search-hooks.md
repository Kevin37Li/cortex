# Task: Create TanStack Query Search Service Hooks

## Summary

Create `src/services/search.ts` with TanStack Query hooks for the search API. The service should provide type-safe search access, stable cache keys, and canonicalized params (trimmed query + defaulted fields) so logically equivalent searches share the same cache entry.

## Acceptance Criteria

- [x] `src/services/search.ts` created with typed search hooks - Implemented in `src/services/search.ts`
- [x] Types re-exported from `api.gen.ts`: `SearchRequest`, `SearchResponse`, `SearchResultItem`; `SearchType` derived from `SearchRequest['search_type']` - `src/services/search.ts:7-9`
- [x] Frontend-only `SearchParams` exported with optional `search_type` and `limit` - `src/services/search.ts:12-16`
- [x] `searchQueryKeys` factory exported with `all`, `searches`, `search(params)` helpers - `src/services/search.ts:38-43`
- [x] Search params are canonicalized in one place (trim query, default `search_type` to `hybrid`, default `limit` to `20`) and the canonicalized object is used for both:
  - Query key generation - `src/services/search.ts:34-36` (via `searchKeyFromNormalizedParams`)
  - `POST /api/search/` request body - `src/services/search.ts:54` (`JSON.stringify(normalized)`)
- [x] `useSearch(params)` uses `useQuery` with:
  - `queryKey` from `searchQueryKeys.search(params)` - `src/services/search.ts:49`
  - `enabled: Boolean(normalized.query)` so empty/whitespace queries are skipped - `src/services/search.ts:56`
  - `apiFetch<SearchResponse>('/api/search/', { method: 'POST', ... })` - `src/services/search.ts:50-55`
- [x] `searchQueryKeys.search()` produces unique keys for distinct searches and stable/equal keys for equivalent params (including whitespace variants that normalize to the same query) - Verified in `src/services/search.test.ts:49-80`
- [x] No explicit error logging in query hook; `apiFetch` remains the single error logging point - No logger import in `search.ts`
- [x] `src/services/search.test.ts` created with tests covering:
  - Query key uniqueness across query/search_type/limit changes - `search.test.ts:49-61`
  - Query key equality for equivalent params objects - `search.test.ts:63-74`
  - Query key/body normalization for surrounding whitespace in query - `search.test.ts:71-73`, `search.test.ts:76-80`
  - Request URL, method (`POST`), headers, and JSON body - `search.test.ts:112-122`
  - Default `search_type` and `limit` when omitted - `search.test.ts:125-149`
  - Disabled state for empty and whitespace-only query - `search.test.ts:151-166`
  - Backend error propagation via `apiFetch` (`result.current.isError`, message assertion) - `search.test.ts:168-225`
- [x] `bun run openapi:sync` run before implementation/testing to ensure search types exist in `src/types/api.gen.ts` - Confirmed via typecheck
- [x] Frontend checks pass for this task scope:
  - `bun run test:run` - 159 tests passing across 25 files
  - `bun run typecheck` - Clean

## Dependencies

- `docs/tasks-done/task-2026-02-16-search-models-and-error-types.md` (search schema contract)
- `docs/tasks-done/task-2026-02-22-search-api-endpoint.md` (`POST /api/search/` route and OpenAPI export)
- `src/lib/api-config.ts` (`apiFetch` behavior + error handling)
- `src/lib/query-client.ts` (global query defaults, including staleTime)
- `src/services/items.ts` and `src/services/items.test.ts` (canonical frontend service/test pattern)

## Technical Notes

### OpenAPI Type Generation

Regenerate types first:

```bash
bun run openapi:sync
```

Search route/types should exist in `src/types/api.gen.ts` before writing the service.

### Type Re-exports

Follow the `items.ts` style:

```typescript
import type { components } from '@/types/api.gen'

export type SearchRequest = components['schemas']['SearchRequest']
export type SearchResponse = components['schemas']['SearchResponse']
export type SearchResultItem = components['schemas']['SearchResultItem']
export type SearchType = SearchRequest['search_type']
```

### Canonical Params + Query Keys

Avoid cache fragmentation from whitespace and omitted optionals by canonicalizing first:

```typescript
export interface SearchParams {
  query: string
  search_type?: SearchType
  limit?: number
}

interface NormalizedSearchParams {
  query: string
  search_type: SearchType
  limit: number
}

function normalizeSearchParams(params: SearchParams): NormalizedSearchParams {
  return {
    query: params.query.trim(),
    search_type: params.search_type ?? 'hybrid',
    limit: params.limit ?? 20,
  }
}

export const searchQueryKeys = {
  all: ['search'] as const,
  searches: () => [...searchQueryKeys.all, 'searches'] as const,
  search: (params: SearchParams) =>
    [...searchQueryKeys.searches(), normalizeSearchParams(params)] as const,
}
```

Do not clamp/transform `limit` beyond defaults in the service; backend validation should remain the source of truth for range errors.

### useSearch Hook

Search is a read operation (idempotent, no side effects), so use `useQuery`:

```typescript
export function useSearch(params: SearchParams) {
  const normalized = normalizeSearchParams(params)

  return useQuery({
    queryKey: searchQueryKeys.search(params),
    queryFn: () =>
      apiFetch<SearchResponse>('/api/search/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(normalized),
      }),
    enabled: Boolean(normalized.query),
  })
}
```

### Scope Boundaries

- Debouncing belongs to Task 8 (UI layer), not this service layer.
- Keyboard focus/Cmd+F behavior belongs to Task 7, not this task.
- Full-repo quality gate belongs to Task 9; this task should still leave targeted frontend checks green.

### Test Pattern

Follow `src/services/items.test.ts`:

- Mock logger before dynamic imports (`trace`, `debug`, `info`, `warn`, `error`)
- Use `vi.stubGlobal('fetch', fetchMock)` in `beforeEach`
- Reuse helper patterns: `createTestQueryClient`, `createWrapper`, `createMockResponse`
- Validate payload details from `fetchMock.mock.calls[0]`

## Files to Create

- `src/services/search.ts` - TanStack Query hooks and search API types
- `src/services/search.test.ts` - Hook/query-key tests

## Verification

```bash
bun run openapi:sync
bun run test:run src/services/search.test.ts
bun run test:run
bun run typecheck
```

---

## Implementation Details

_Tracked: 2026-02-22_

### Files Changed

| File                                   | Change   | Description                                                                                                           |
| -------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------- |
| `src/services/search.ts`               | Created  | TanStack Query hooks with type-safe search API access, canonical params, and query key factory                        |
| `src/services/search.test.ts`          | Created  | 10 tests covering query keys, normalization, request shape, disabled state, and error propagation                     |
| `src/test-utils/query-test-helpers.ts` | Created  | Extracted shared test utilities (`createTestQueryClient`, `createWrapper`, `createMockResponse`) from `items.test.ts` |
| `src/services/items.test.ts`           | Modified | Refactored to import shared helpers from `@/test-utils/query-test-helpers` instead of inline definitions              |

### Dependencies Added

None — all dependencies (`@tanstack/react-query`, `@testing-library/react`, `vitest`) were already in the project.

---

## Learning Report

_Generated: 2026-02-22_

### Summary

Created `src/services/search.ts` (58 lines) and `src/services/search.test.ts` (226 lines) providing a TanStack Query service layer for the `POST /api/search/` endpoint. Additionally extracted shared test helpers into `src/test-utils/query-test-helpers.ts` to eliminate duplication between `items.test.ts` and `search.test.ts`. All 159 tests pass, typecheck is clean.

### Patterns & Decisions

- **Followed the `items.ts` service pattern exactly**: type re-exports from `api.gen.ts`, query key factory, `apiFetch`-based query function. This keeps services consistent and predictable.
- **Extracted `normalizeSearchParams` as a named export**: The task spec showed it as a private function, but exporting it (and `NormalizedSearchParams`) allows tests to inspect normalization behavior directly and may benefit the UI layer in Task 8.
- **Introduced `searchKeyFromNormalizedParams` helper**: Both `searchQueryKeys.search()` and `useSearch()` call `normalizeSearchParams` independently but share the same key structure via this helper, avoiding subtle divergence between query keys and the hook's internal key.
- **Shared test utilities extracted to `src/test-utils/`**: `createTestQueryClient`, `createWrapper`, and `createMockResponse` were duplicated in `items.test.ts`. Extracting them to a shared module reduces maintenance burden and establishes a pattern for future service tests.

### Challenges & Solutions

- **No significant challenges**: The task spec was very well-defined with exact code patterns. Implementation was straightforward.
- **Test helper duplication**: The task spec said to "reuse helper patterns" from `items.test.ts`, but copy-pasting would have created maintenance debt. Extracting to `src/test-utils/query-test-helpers.ts` solved this cleanly and the items tests continued passing after the refactor.

### Lessons Learned

- **Well-specified tasks execute quickly**: The detailed code snippets and test patterns in the task spec made implementation nearly mechanical — a good template for future service-layer tasks.
- **Shared test utilities pay off early**: Even with just two service test files, the extraction already prevented ~40 lines of duplication and will simplify every future TanStack Query test.
- **Interior whitespace test case was a good addition**: The spec didn't explicitly require testing that interior whitespace is preserved (only leading/trailing trimming), but adding `search.test.ts:76-80` caught a potential edge case worth documenting.

### Documentation Impact

- **`src/test-utils/` is a new directory**: Future service tests should import from `@/test-utils/query-test-helpers` rather than defining their own helpers. This pattern should be noted in testing docs.
- **Search service pattern mirrors items**: No new documentation needed for the service pattern itself — it follows the established `items.ts` convention exactly.
