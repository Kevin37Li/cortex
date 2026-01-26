# Task: Create TanStack Query Service Hooks for Items

## Summary

Create the frontend data access layer for items using TanStack Query. This provides type-safe hooks for fetching, creating, updating, and deleting items from the Python backend API, with automatic caching, background refetching, and optimistic updates.

## Acceptance Criteria

- [ ] `src/services/items.ts` created with TanStack Query hooks
- [ ] `useItems(options?)` — Fetches paginated item list (`GET /api/items`)
- [ ] `useItem(id)` — Fetches single item (`GET /api/items/{id}`)
- [ ] `useCreateItem()` — Mutation for creating items (`POST /api/items`)
- [ ] `useUpdateItem()` — Mutation for updating items (`PUT /api/items/{id}`)
- [ ] `useDeleteItem()` — Mutation for deleting items (`DELETE /api/items/{id}`)
- [ ] All hooks use typed API response models (TypeScript interfaces matching Pydantic models)
- [ ] Mutations invalidate relevant queries on success (e.g., creating an item invalidates the item list)
- [ ] API base URL configured as constant (e.g., `http://localhost:8742`)
- [ ] Error handling: API errors are surfaced via TanStack Query's error state
- [ ] Query keys follow consistent naming convention: `['items']`, `['items', id]`

## Dependencies

- Phase 1 complete: TanStack Query client configured in `src/lib/query-client.ts`
- Phase 1 complete: Python backend running with items CRUD endpoints
- Per AGENTS.md: "All Python backend API calls must be wrapped in TanStack Query hooks (in `src/services/`), not called directly with `fetch()` in components"

## Technical Notes

- Per `docs/developer/architecture/state-management.md`: persistent data from Python backend uses TanStack Query
- Per MVP plan anti-patterns: never call `fetch()` directly in components
- Use `@tanstack/react-query` hooks: `useQuery`, `useMutation`, `useQueryClient`
- TypeScript interfaces must match the Python Pydantic models exactly
- The existing `src/services/preferences.ts` may provide a pattern to follow
- API base URL should be defined once (e.g., in a config or constant)

## TypeScript Interfaces

```typescript
// Match Pydantic models from python-backend/src/db/models.py
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

```typescript
// src/services/items.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

const API_BASE = 'http://localhost:8742'

const itemKeys = {
  all: ['items'] as const,
  lists: () => [...itemKeys.all, 'list'] as const,
  list: (params: { offset?: number; limit?: number }) => [...itemKeys.lists(), params] as const,
  details: () => [...itemKeys.all, 'detail'] as const,
  detail: (id: string) => [...itemKeys.details(), id] as const,
}

export function useItems(params?: { offset?: number; limit?: number }) {
  return useQuery({
    queryKey: itemKeys.list(params ?? {}),
    queryFn: async () => {
      const searchParams = new URLSearchParams()
      if (params?.offset) searchParams.set('offset', String(params.offset))
      if (params?.limit) searchParams.set('limit', String(params.limit))
      const res = await fetch(`${API_BASE}/api/items?${searchParams}`)
      if (!res.ok) throw new Error('Failed to fetch items')
      return res.json() as Promise<ItemListResponse>
    },
  })
}

export function useCreateItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (data: ItemCreate) => {
      const res = await fetch(`${API_BASE}/api/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      if (!res.ok) throw new Error('Failed to create item')
      return res.json() as Promise<Item>
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: itemKeys.lists() })
    },
  })
}
```

## Files to Create

- `src/services/items.ts` — TanStack Query hooks for items API

## Verification

```bash
bun run typecheck  # TypeScript compiles
bun run lint       # No lint errors
bun run test       # Existing tests pass
```
