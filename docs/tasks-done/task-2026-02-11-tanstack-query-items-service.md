# Task: Create TanStack Query Service Hooks for Items

## Summary

Create the frontend item data layer in `src/services/` using TanStack Query hooks. This task centralizes HTTP access to the local Python sidecar API and provides typed hooks for list/detail CRUD operations with consistent caching, invalidation, and error handling.

## Acceptance Criteria

- [x] `src/lib/api-config.ts` is created with:
  - [x] `API_BASE = 'http://127.0.0.1:8742'` — `api-config.ts:3` (env-overridable via `VITE_API_BASE`)
  - [x] shared `apiFetch<T>()` helper used by item services — `api-config.ts:44-93` (with function overloads for json/void)
  - [x] backend error parsing for structured API errors (`{ error, message }`) — `api-config.ts:19-42` (also handles FastAPI `detail[]` arrays)
  - [x] explicit support for endpoints returning no body (204) so callers do not parse JSON for delete — `api-config.ts:79-81`
- [x] `src/services/items.ts` is created with typed models and hooks:
  - [x] `useItems(params?)` for `GET /api/items/` (list + pagination) — `items.ts:50-55`
  - [x] `useItem(id)` for `GET /api/items/{id}` — `items.ts:57-63`
  - [x] `useCreateItem()` for `POST /api/items/` (201) — `items.ts:65-82`
  - [x] `useUpdateItem()` for `PUT /api/items/{id}` — `items.ts:84-103`
  - [x] `useDeleteItem()` for `DELETE /api/items/{id}` (204) — `items.ts:106-125`
- [x] `itemQueryKeys` is exported with factory helpers:
  - [x] `all`, `lists`, `list(params)`, `details`, `detail(id)` — `items.ts:23-30`
- [x] Mutations invalidate relevant cache entries:
  - [x] create invalidates list queries — `items.ts:76`
  - [x] update invalidates list queries and updated item detail — `items.ts:95-98`
  - [x] delete invalidates list queries and deleted item detail cache — `items.ts:115-119`
- [x] Hooks log technical errors with `@/lib/logger` and throw to TanStack Query (no inline toasts in service hooks) — `items.ts:79,100,122`
- [x] `src/services/items.test.ts` is added and covers:
  - [x] query key behavior and request URL generation — `items.test.ts:81-174` (5 tests)
  - [x] mutation success paths and query invalidation — `items.test.ts:176-240` (2 tests)
  - [x] structured error parsing from backend responses — `items.test.ts:242-306` (2 tests)
  - [x] delete 204 behavior (no JSON parsing attempted) — `items.test.ts:308-350`

## Dependencies

- Phase 1 complete: TanStack Query client configured in `src/lib/query-client.ts`
- Phase 1 complete: Python backend items endpoints available
- Architecture rule from `AGENTS.md`: components must consume service hooks, not call raw `fetch()` directly

## Technical Notes

- Per `docs/developer/architecture/state-management.md`: backend persistent data belongs in TanStack Query.
- Per `docs/developer/architecture/architecture-guide.md`: frontend communicates directly with the local sidecar API over HTTP.
- FastAPI route definitions use `/items/` for list/create and `/items/{id}` for detail/update/delete. Use these canonical paths in service code to avoid redirect round-trips.
- Follow `src/services/preferences.ts` for query-key and logging style, but do **not** copy toast behavior from preferences mutations into item service hooks.
- Use `params?.offset !== undefined` / `params?.limit !== undefined` when building query strings (avoid truthy checks that drop explicit `0` values).
- Keep default query timings from `src/lib/query-client.ts`; no per-hook override required in this task.
- Item hook interfaces should align with current backend contract in `python-backend/src/db/models.py`. `content_type` and `processing_status` may be represented as TypeScript string unions based on current supported values.

## TypeScript Interfaces

```typescript
// Based on python-backend/src/db/models.py and current DB-enforced values
export interface Item {
  id: string
  title: string
  content: string
  content_type: 'webpage' | 'note' | 'file'
  source_url: string | null
  created_at: string
  updated_at: string
  processing_status: 'pending' | 'processing' | 'completed' | 'failed'
  metadata: Record<string, unknown> | null
}

export interface ItemCreate {
  title: string
  content: string
  content_type: 'webpage' | 'note' | 'file'
  source_url?: string | null
  metadata?: Record<string, unknown> | null
}

export interface ItemUpdate {
  title?: string | null
  content?: string | null
  source_url?: string | null
  metadata?: Record<string, unknown> | null
}

export interface ItemListResponse {
  items: Item[]
  total: number
  offset: number
  limit: number
}
```

## Hook Patterns

### Shared API config (`src/lib/api-config.ts`)

```typescript
import { logger } from '@/lib/logger'

export const API_BASE = 'http://127.0.0.1:8742'

type ApiFetchOptions = RequestInit & { expect?: 'json' | 'none' }

export async function apiFetch<T>(
  path: string,
  options?: ApiFetchOptions
): Promise<T> {
  const { expect = 'json', ...init } = options ?? {}

  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, init)
  } catch (error) {
    logger.error('Network request failed', { path, error })
    throw new Error('Network request failed')
  }

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const message =
      typeof body?.message === 'string'
        ? body.message
        : `API error: ${res.status}`
    logger.error(`API request failed: ${message}`, {
      path,
      status: res.status,
      error: body?.error,
    })
    throw new Error(message)
  }

  if (expect === 'none' || res.status === 204) {
    return undefined as T
  }

  return (await res.json()) as T
}
```

### Service hooks (`src/services/items.ts`)

```typescript
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api-config'

export interface ItemListParams {
  offset?: number
  limit?: number
}

export const itemQueryKeys = {
  all: ['items'] as const,
  lists: () => [...itemQueryKeys.all, 'list'] as const,
  list: (params: ItemListParams = {}) =>
    [...itemQueryKeys.lists(), params] as const,
  details: () => [...itemQueryKeys.all, 'detail'] as const,
  detail: (id: string) => [...itemQueryKeys.details(), id] as const,
}

export function useItems(params?: ItemListParams) {
  return useQuery({
    queryKey: itemQueryKeys.list(params ?? {}),
    queryFn: async () => {
      const searchParams = new URLSearchParams()
      if (params?.offset !== undefined) {
        searchParams.set('offset', String(params.offset))
      }
      if (params?.limit !== undefined) {
        searchParams.set('limit', String(params.limit))
      }
      const query = searchParams.toString()
      const path = query ? `/api/items/?${query}` : '/api/items/'
      return apiFetch<ItemListResponse>(path)
    },
  })
}

export function useItem(id: string) {
  return useQuery({
    queryKey: itemQueryKeys.detail(id),
    queryFn: () => apiFetch<Item>(`/api/items/${id}`),
    enabled: Boolean(id),
  })
}

export function useCreateItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: ItemCreate) =>
      apiFetch<Item>('/api/items/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: itemQueryKeys.lists() })
    },
  })
}

export function useUpdateItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ItemUpdate }) =>
      apiFetch<Item>(`/api/items/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }),
    onSuccess: (_updated, variables) => {
      queryClient.invalidateQueries({ queryKey: itemQueryKeys.lists() })
      queryClient.invalidateQueries({
        queryKey: itemQueryKeys.detail(variables.id),
      })
    },
  })
}

export function useDeleteItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/api/items/${id}`, {
        method: 'DELETE',
        expect: 'none',
      }),
    onSuccess: (_result, deletedId) => {
      queryClient.invalidateQueries({ queryKey: itemQueryKeys.lists() })
      queryClient.removeQueries({ queryKey: itemQueryKeys.detail(deletedId) })
    },
  })
}
```

## Files to Create

- `src/lib/api-config.ts` - Shared API base URL and `apiFetch()` helper
- `src/services/items.ts` - TanStack Query hooks and types for items API
- `src/services/items.test.ts` - Hook tests with mocked fetch + query client assertions

## Verification

```bash
bun run typecheck
bun run lint
bun run test:run
bun run check:all
```

---

## Implementation Details

_Tracked: 2026-02-11_

### Files Changed

| File                                            | Change   | Description                                                                                                                                |
| ----------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/lib/api-config.ts`                         | Created  | Shared `apiFetch()` with overloads for json/void, structured error parsing, FastAPI `detail[]` support                                     |
| `src/lib/api-config.test.ts`                    | Created  | 4 tests covering network errors, non-JSON error bodies, FastAPI detail arrays, invalid success JSON                                        |
| `src/services/items.ts`                         | Created  | TanStack Query hooks (useItems, useItem, useCreateItem, useUpdateItem, useDeleteItem) with query key factory                               |
| `src/services/items.test.ts`                    | Created  | 9 tests covering query keys, URL generation, mutation invalidation, error parsing, delete 204                                              |
| `python-backend/export_openapi.py`              | Created  | Script to export FastAPI OpenAPI spec to `openapi.json`                                                                                    |
| `python-backend/src/db/models.py`               | Modified | Added `ContentType` StrEnum, moved `ProcessingStatus`/`ProcessingStep` enums above item models, replaced raw strings with enums            |
| `python-backend/src/services/parsing.py`        | Modified | Updated to use `ContentType` enum instead of string literals                                                                               |
| `python-backend/src/workflows/processing.py`    | Modified | Updated `ProcessingState.content_type` to use `ContentType` enum                                                                           |
| `docs/developer/python-backend/architecture.md` | Modified | Added "OpenAPI Type Generation" section documenting the pipeline                                                                           |
| `package.json`                                  | Modified | Added `openapi:export`, `openapi:generate`, `openapi:sync` scripts; `openapi-typescript` devDep; `typecheck` now runs `openapi:sync` first |
| `eslint.config.js`                              | Modified | Added `src/types/api.gen.ts` to ignore list                                                                                                |
| `.gitignore`                                    | Modified | Added `openapi.json` and `src/types/api.gen.ts`                                                                                            |
| `bun.lock`                                      | Modified | Updated lockfile for new dependency                                                                                                        |

### Dependencies Added

- `openapi-typescript@^7.13.0` (devDependency) — Generates TypeScript types from OpenAPI JSON spec

### Key Metrics

- **New frontend code**: 93 lines (api-config) + 125 lines (items service) = 218 lines
- **New test code**: 111 lines (api-config tests) + 351 lines (items tests) = 462 lines
- **Tests**: 13 total (4 api-config + 9 items), all passing
- **Typecheck**: Clean

---

## Learning Report

_Generated: 2026-02-11_

### Summary

Built the frontend item data layer consisting of a shared `apiFetch()` utility and five TanStack Query hooks for CRUD operations on items. Went beyond the original spec by introducing an OpenAPI type generation pipeline (`Pydantic → OpenAPI JSON → openapi-typescript → api.gen.ts`) so frontend types stay in sync with the backend contract automatically rather than being hand-maintained TypeScript interfaces. Also hardened the Python backend by replacing raw string fields with proper `StrEnum` types.

### Patterns & Decisions

1. **OpenAPI type generation over manual interfaces**: The task spec defined manual TypeScript interfaces. The implementation instead uses `openapi-typescript` to generate types from the FastAPI OpenAPI spec. This ensures the frontend-backend contract can never drift silently — a Pydantic model change flows through to TypeScript automatically via `bun run openapi:sync`.

2. **Function overloads for `apiFetch`**: Instead of the spec's single generic signature with `undefined as T` cast, the implementation uses TypeScript function overloads — `apiFetch<T>(path, jsonOptions): Promise<T>` and `apiFetch(path, noneOptions): Promise<void>`. This gives callers proper void typing for DELETE without unsafe casts.

3. **FastAPI `detail[]` error parsing**: The spec only handled `{ error, message }` structured errors. The implementation additionally parses FastAPI's validation error format (`{ detail: [{ msg, loc, type }] }`), joining multiple messages with semicolons. Tested with the `api-config.test.ts` suite.

4. **Success body JSON parse protection**: Added a try/catch around `response.json()` on success responses (not in original spec) so a corrupted successful response throws `"Invalid API response"` with logging rather than an opaque JSON parse error.

5. **`encodeURIComponent` on IDs**: Detail/update/delete endpoints use `encodeURIComponent(id)` for safety, unlike the spec which passed IDs raw. Tests verify this with a `specialItemId = 'item/with spaces?#'` fixture.

6. **Python StrEnum consolidation**: Moved `ProcessingStatus` and `ProcessingStep` enums above item models and added `ContentType` StrEnum. This replaced raw string fields across `models.py`, `parsing.py`, and `processing.py`, improving type safety on the backend side.

7. **Environment-overridable API_BASE**: Used `import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8742'` instead of a hardcoded constant, allowing test/dev flexibility.

### Challenges & Solutions

1. **Trailing slash semantics**: FastAPI with prefix="/items" and route "/" requires a trailing slash for list/create endpoints — omitting it causes a 307 redirect. The implementation documents this in a code comment at `items.ts:32-34` and consistently uses `/api/items/` for collection endpoints vs `/api/items/{id}` for detail.

2. **Test setup with mocked modules**: The tests use `vi.mock()` with `await import()` pattern to properly mock `@/lib/logger` before importing modules that depend on it. This avoids the common pitfall of logger calls not being captured.

3. **Avoiding truthy checks on offset/limit**: Per the spec's technical note, `params?.offset !== undefined` is used (not `params?.offset`) so that `offset: 0` is correctly included in the query string.

### Lessons Learned

1. **OpenAPI codegen is high-value for Pydantic↔TypeScript**: The one-time setup cost of the `openapi:sync` pipeline pays off immediately — no manual interface maintenance, and `typecheck` catches contract drift automatically since it runs `openapi:sync` first.

2. **Function overloads improve DX**: The void overload for `expect: 'none'` means delete callers get `Promise<void>` instead of `Promise<T>` with an unsafe cast. Worth the small extra complexity in `api-config.ts`.

3. **Test coverage for error edge cases matters**: Testing FastAPI's `detail[]` format and non-JSON error bodies caught real parsing paths that would have failed silently with the simpler spec approach.

### Documentation Impact

- **Updated**: `docs/developer/python-backend/architecture.md` — Added "OpenAPI Type Generation" section covering the pipeline, scripts, when to regenerate, and frontend usage pattern.
- **Potentially affected**: `docs/developer/architecture/state-management.md` — May want to reference the items service as a canonical TanStack Query example now that it exists.
- **New pattern to document**: The `openapi:sync` pipeline and `api.gen.ts` generation pattern should be referenced in any "adding a new API endpoint" guide.
