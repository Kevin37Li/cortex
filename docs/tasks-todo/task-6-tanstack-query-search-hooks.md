# Task: Create TanStack Query Search Service Hooks

## Summary

Create `src/services/search.ts` with TanStack Query hooks for the search API. This provides the frontend data layer for executing searches with proper caching, loading states, and type safety via the OpenAPI-generated types.

## Acceptance Criteria

- [ ] `src/services/search.ts` created with typed search hooks
- [ ] Types re-exported from `api.gen.ts`: `SearchRequest`, `SearchResponse`, `SearchResultItem`, `SearchType`
- [ ] `searchQueryKeys` factory exported with `all`, `queries`, `query(params)` helpers
- [ ] `useSearch(params)` hook using `useQuery` with:
  - Query key includes search params (query, search_type, limit)
  - `enabled: Boolean(params.query?.trim())` to skip empty queries
  - Calls `POST /api/search/` via `apiFetch`
  - Returns `UseQueryResult<SearchResponse>`
- [ ] `searchQueryKeys.query()` produces unique, stable keys per search params
- [ ] Hook logs errors with `@/lib/logger` (no inline toasts in service hooks)
- [ ] `src/services/search.test.ts` created with tests covering:
  - Query key generation for different params
  - Request URL and method (POST)
  - Disabled state for empty queries
  - Error handling from backend
- [ ] `bun run openapi:sync` run first to ensure search types are generated in `api.gen.ts`
- [ ] All tests pass: `bun run test:run`
- [ ] TypeScript compiles: `bun run typecheck`

## Dependencies

- Task 4: Search API endpoint (backend must exist to generate OpenAPI types)
- Phase 2: `src/lib/api-config.ts` (`apiFetch` helper), `src/lib/query-client.ts`
- Phase 2: `src/services/items.ts` as the canonical pattern to follow

## Technical Notes

### OpenAPI Type Generation

Before implementing, regenerate types to include the search models:

```bash
bun run openapi:sync
```

This will add `SearchRequest`, `SearchResponse`, `SearchResultItem` to `src/types/api.gen.ts`.

### Type Re-exports

Follow the pattern from `src/services/items.ts`:

```typescript
import type { components } from '@/types/api.gen'

export type SearchRequest = components['schemas']['SearchRequest']
export type SearchResponse = components['schemas']['SearchResponse']
export type SearchResultItem = components['schemas']['SearchResultItem']
export type SearchType = components['schemas']['SearchType']
```

### Search Query Keys

```typescript
export interface SearchParams {
  query: string
  search_type?: SearchType
  limit?: number
}

export const searchQueryKeys = {
  all: ['search'] as const,
  queries: () => [...searchQueryKeys.all, 'query'] as const,
  query: (params: SearchParams) =>
    [...searchQueryKeys.queries(), params] as const,
}
```

### useSearch Hook

Search uses `POST` but is semantically a read operation (idempotent, no side effects). TanStack Query supports this well - the query key includes the search params so each unique query string is cached separately:

```typescript
export function useSearch(params: SearchParams) {
  return useQuery({
    queryKey: searchQueryKeys.query(params),
    queryFn: () =>
      apiFetch<SearchResponse>('/api/search/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: params.query,
          search_type: params.search_type ?? 'hybrid',
          limit: params.limit ?? 20,
        }),
      }),
    enabled: Boolean(params.query?.trim()),
  })
}
```

**Why `useQuery` not `useMutation`**: Search is idempotent and read-only. Using `useQuery`:

- Enables automatic caching of repeated searches
- Provides `isLoading`/`isFetching` states naturally
- Supports refetching and stale-while-revalidate
- Disabled until a query is provided via `enabled`

### Debouncing

Debouncing is NOT handled in the service layer. The UI component (Task 8) will debounce the search params before passing to `useSearch`. This keeps the service layer clean and testable.

### Error Handling

Follow the items service pattern - log errors, let TanStack Query handle retry/error states:

```typescript
// TanStack Query already handles error states via isError/error
// The service just logs for observability
```

No explicit `onError` callback is needed in the query definition since `apiFetch` already throws on non-OK responses and TanStack Query catches thrown errors automatically.

### Test Pattern

Follow `src/services/items.test.ts` for the test structure:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock logger before imports
vi.mock('@/lib/logger', () => ({
  logger: { error: vi.fn(), debug: vi.fn(), info: vi.fn(), warn: vi.fn() },
}))

describe('searchQueryKeys', () => {
  it('creates unique keys for different queries', () => {
    const key1 = searchQueryKeys.query({ query: 'python' })
    const key2 = searchQueryKeys.query({ query: 'javascript' })
    expect(key1).not.toEqual(key2)
  })

  it('creates stable keys for same params', () => {
    const params = { query: 'python', search_type: 'hybrid' as const }
    expect(searchQueryKeys.query(params)).toEqual(searchQueryKeys.query(params))
  })
})

describe('useSearch', () => {
  it('sends POST request with search params', async () => {
    // Test that apiFetch is called with correct args
  })

  it('is disabled for empty queries', () => {
    // Test that enabled is false when query is empty/whitespace
  })
})
```

## Files to Create

- `src/services/search.ts` - TanStack Query hooks and types for search API
- `src/services/search.test.ts` - Hook tests

## Verification

```bash
bun run openapi:sync    # Ensure search types are generated
bun run typecheck       # TypeScript compiles
bun run lint            # ESLint passes
bun run test:run        # All tests pass
```
