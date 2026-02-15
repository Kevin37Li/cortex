# Task: Implement Processing Progress Indicators

## Summary

Connect the frontend to the processing status WebSocket to display real-time progress indicators for items being processed. Items in the list and detail view show live updates as they move through processing steps (classify → parsing → chunking → extracting → validating → storing → completed).

## Acceptance Criteria

- [ ] WebSocket connection to `/api/ws/processing` (derived from `API_BASE`) is established once at app root (`App.tsx`)
- [ ] Processing events update UI in real time without polling
- [ ] Item list shows live processing status + current step label for processing items
- [ ] Item detail shows live processing status + step label + percentage (e.g., "Extracting metadata... 65%")
- [ ] Detail route sets WebSocket filter with `{"subscribe": itemId}` and clears it on unmount with `{"subscribe": ""}`
- [ ] Active subscription is re-applied automatically after reconnect
- [ ] On `completed`/`failed` events: invalidate `itemQueryKeys.lists()` and `itemQueryKeys.detail(itemId)`
- [ ] `completed`/`failed` live entries are removed from processing store after brief delay (so final state is visible)
- [ ] Failed items continue to show retry affordance in list/detail
- [ ] WebSocket reconnects automatically on disconnect with capped exponential backoff (2s, 4s, 8s, 16s, 30s; max 10 attempts)
- [ ] Graceful fallback: if WebSocket is unavailable, UI falls back to last-fetched TanStack Query data
- [ ] Incoming WebSocket payloads are runtime-validated; malformed/unknown payloads are ignored safely
- [ ] All progress UI strings use i18n keys in `locales/en.json` and `locales/zh.json`
- [ ] WebSocket lifecycle and parse/reconnect failures are logged via `@/lib/logger`

## Dependencies

- Task 10: Processing status WebSocket endpoint
- Task 12: TanStack Query service hooks (for cache invalidation)
- Task 13: Item list (display target)
- Task 16: Item detail view (display target)

## Technical Notes

### State Management

Per the state management decision tree: processing updates are transient state needed across multiple components (ItemList and ItemDetail) but do not persist between sessions → **Zustand store**.

A single WebSocket connection is managed via a hook mounted once in `src/App.tsx`. The connection writes updates into `useProcessingStore`. Components consume processing state via selector syntax (no destructuring).

### WebSocket URL

Derive from `API_BASE` in `src/lib/api-config.ts` — never hardcode the URL:

```typescript
import { API_BASE } from '@/lib/api-config'

function getProcessingWsUrl(): string {
  const url = new URL('/api/ws/processing', API_BASE)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return url.toString()
}
```

### ProcessingUpdate Type

The `ProcessingUpdate` model is not exposed via REST (only WebSocket), so `openapi-typescript` does not generate it. Define it manually, reusing the generated enum types:

```typescript
import type { components } from '@/types/api.gen'

type ProcessingStatus = components['schemas']['ProcessingStatus']
type ProcessingStep = components['schemas']['ProcessingStep']

export interface ProcessingUpdate {
  type: 'processing_update'
  item_id: string
  status: ProcessingStatus
  step: ProcessingStep
  progress: number // 0.0 - 1.0
  message: string
}
```

### WebSocket Subscriptions

The backend supports per-item filtering via `{"subscribe": "item_id"}` (see `python-backend/src/api/routes/ws.py`).

- Item list behavior: no filter (`null`) so all updates are received
- Item detail behavior: set `subscriptionItemId = itemId` on mount, clear on unmount
- Hook behavior: whenever socket opens/re-opens, send the current subscription value; send `{"subscribe": ""}` when subscription is cleared

### Cache Invalidation

Use `itemQueryKeys` from `src/services/items.ts` (already used elsewhere in codebase):

```typescript
import { itemQueryKeys } from '@/services/items'

queryClient.invalidateQueries({ queryKey: itemQueryKeys.lists() })
queryClient.invalidateQueries({
  queryKey: itemQueryKeys.detail(update.item_id),
})
```

### Reconnection Strategy

- Backoff: `2s, 4s, 8s, 16s, 30s` (capped)
- Max attempts: `10`
- Reset attempt counter on successful `onopen`
- Log each reconnect attempt and max-attempt exhaustion via `logger.warn`

### Runtime Payload Validation

Parse JSON, then validate shape before writing to store:

- `type === 'processing_update'`
- `item_id` is string
- `status` in ProcessingStatus union
- `step` in ProcessingStep union
- `progress` is finite number in `[0, 1]`

## Zustand Store Pattern

```typescript
// src/store/processing-store.ts
import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { ProcessingUpdate } from '@/types/processing'

interface ProcessingState {
  processingByItemId: Record<string, ProcessingUpdate>
  subscriptionItemId: string | null
  setUpdate: (update: ProcessingUpdate) => void
  removeItem: (itemId: string) => void
  clearAll: () => void
  setSubscriptionItemId: (itemId: string | null) => void
}

export const useProcessingStore = create<ProcessingState>()(
  devtools(
    set => ({
      processingByItemId: {},
      subscriptionItemId: null,
      setUpdate: update =>
        set(
          state => ({
            processingByItemId: {
              ...state.processingByItemId,
              [update.item_id]: update,
            },
          }),
          undefined,
          'setUpdate'
        ),
      removeItem: itemId =>
        set(
          state => {
            const { [itemId]: _removed, ...rest } = state.processingByItemId
            return { processingByItemId: rest }
          },
          undefined,
          'removeItem'
        ),
      clearAll: () =>
        set(
          {
            processingByItemId: {},
            subscriptionItemId: null,
          },
          undefined,
          'clearAll'
        ),
      setSubscriptionItemId: itemId =>
        set({ subscriptionItemId: itemId }, undefined, 'setSubscriptionItemId'),
    }),
    { name: 'processing-store' }
  )
)
```

## WebSocket Hook Pattern

```typescript
// src/hooks/use-processing-websocket.ts
import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { API_BASE } from '@/lib/api-config'
import { logger } from '@/lib/logger'
import { itemQueryKeys } from '@/services/items'
import { useProcessingStore } from '@/store/processing-store'
import type { ProcessingUpdate } from '@/types/processing'

const MAX_RECONNECT_ATTEMPTS = 10
const COMPLETED_CLEANUP_DELAY_MS = 3000

function getProcessingWsUrl(): string {
  const url = new URL('/api/ws/processing', API_BASE)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return url.toString()
}

function isProcessingUpdate(value: unknown): value is ProcessingUpdate {
  if (!value || typeof value !== 'object') return false
  const update = value as Partial<ProcessingUpdate>
  return (
    update.type === 'processing_update' &&
    typeof update.item_id === 'string' &&
    typeof update.status === 'string' &&
    typeof update.step === 'string' &&
    typeof update.progress === 'number' &&
    Number.isFinite(update.progress) &&
    update.progress >= 0 &&
    update.progress <= 1
  )
}

/**
 * Manages the WebSocket connection for processing updates.
 * Call once at the app root level — updates flow into the Zustand store.
 */
export function useProcessingWebSocket() {
  const queryClient = useQueryClient()
  const subscriptionItemId = useProcessingStore(
    state => state.subscriptionItemId
  )
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    let reconnectAttempts = 0
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    const cleanupTimers = new Map<string, ReturnType<typeof setTimeout>>()
    let disposed = false

    function connect() {
      if (disposed) return
      const ws = new WebSocket(getProcessingWsUrl())
      wsRef.current = ws

      ws.onopen = () => {
        logger.debug('Processing WebSocket connected')
        reconnectAttempts = 0
        ws.send(
          JSON.stringify({
            subscribe: useProcessingStore.getState().subscriptionItemId ?? '',
          })
        )
      }

      ws.onmessage = event => {
        try {
          const raw = JSON.parse(event.data) as unknown
          if (!isProcessingUpdate(raw)) return
          const update: ProcessingUpdate = raw
          useProcessingStore.getState().setUpdate(update)

          if (update.status === 'completed' || update.status === 'failed') {
            queryClient.invalidateQueries({ queryKey: itemQueryKeys.lists() })
            queryClient.invalidateQueries({
              queryKey: itemQueryKeys.detail(update.item_id),
            })

            const existingTimer = cleanupTimers.get(update.item_id)
            if (existingTimer) clearTimeout(existingTimer)

            const timer = setTimeout(() => {
              useProcessingStore.getState().removeItem(update.item_id)
              cleanupTimers.delete(update.item_id)
            }, COMPLETED_CLEANUP_DELAY_MS)
            cleanupTimers.set(update.item_id, timer)
          }
        } catch (err) {
          logger.warn('Failed to parse processing WebSocket message', {
            error: err,
          })
        }
      }

      ws.onerror = event => {
        logger.error('Processing WebSocket error', { event })
      }

      ws.onclose = () => {
        logger.debug('Processing WebSocket closed')
        if (!disposed) scheduleReconnect()
      }
    }

    function scheduleReconnect() {
      if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        logger.warn('Processing WebSocket: max reconnection attempts reached')
        return
      }
      const delay = Math.min(2000 * 2 ** reconnectAttempts, 30000)
      reconnectAttempts++
      logger.warn(
        `Processing WebSocket: reconnecting in ${delay}ms (attempt ${reconnectAttempts})`
      )
      reconnectTimer = setTimeout(connect, delay)
    }

    connect()

    return () => {
      disposed = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      for (const timer of cleanupTimers.values()) clearTimeout(timer)
      cleanupTimers.clear()
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [queryClient])

  useEffect(() => {
    // Keep server-side filter in sync with route changes.
    // null -> {"subscribe": ""} meaning "subscribe to all items".
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    ws.send(JSON.stringify({ subscribe: subscriptionItemId ?? '' }))
  }, [subscriptionItemId])
}
```

## Component Integration

### ProcessingStatusBadge

The existing `ProcessingStatusBadge` already accepts `stepLabel`. Components should derive an effective live status from processing store first, then fall back to query data:

```typescript
// In ItemCard / ItemDetail
const processingUpdate = useProcessingStore(
  state => state.processingByItemId[item.id]
)
const liveStatus = processingUpdate?.status ?? item.processing_status
const stepLabel = processingUpdate
  ? t(`items.processing.step.${processingUpdate.step}`)
  : undefined

<ProcessingStatusBadge
  status={liveStatus}
  stepLabel={stepLabel}
  onRetry={handleRetry}
/>
```

### Detail View Subscription

Set subscription intent from `ItemDetail` lifecycle:

```typescript
const setSubscriptionItemId = useProcessingStore(
  state => state.setSubscriptionItemId
)

useEffect(() => {
  setSubscriptionItemId(itemId)
  return () => setSubscriptionItemId(null)
}, [itemId, setSubscriptionItemId])
```

Render a translated progress line in detail view:

```typescript
const progressPercent = processingUpdate
  ? Math.round(processingUpdate.progress * 100)
  : null

{processingUpdate ? (
  <p className="text-muted-foreground text-sm">
    {t('items.processing.progressPercent', {
      step: t(`items.processing.step.${processingUpdate.step}`),
      percent: progressPercent,
    })}
  </p>
) : null}
```

## Translation Keys

Add to `locales/en.json` under the `items` namespace:

```json
{
  "items.processing.step.classify": "Classifying content...",
  "items.processing.step.parsing": "Parsing content...",
  "items.processing.step.chunking": "Splitting into chunks...",
  "items.processing.step.extracting": "Extracting metadata...",
  "items.processing.step.validating": "Validating results...",
  "items.processing.step.storing": "Saving results...",
  "items.processing.step.completed": "Processing complete",
  "items.processing.step.failed": "Processing failed",
  "items.processing.progressPercent": "{{step}} {{percent}}%",
  "items.processing.reconnecting": "Reconnecting..."
}
```

## Files to Create/Modify

**Create:**

- `src/types/processing.ts` — `ProcessingUpdate` interface (reusing generated enum types)
- `src/store/processing-store.ts` — Zustand store for processing state
- `src/hooks/use-processing-websocket.ts` — WebSocket lifecycle hook (called once at app root)

**Modify:**

- `src/App.tsx` — Mount `useProcessingWebSocket()` once
- `src/components/items/ItemCard.tsx` — Derive live status/step from processing store
- `src/components/items/ItemDetail.tsx` — Derive live status/step/progress + set/clear subscription intent
- `locales/en.json` — Add `items.processing.*` translation keys
- `locales/zh.json` — Add Chinese translations

**No changes needed:**

- `src/components/items/ProcessingStatusBadge.tsx` — Already supports `stepLabel` prop

## Testing

Write tests for:

- **Processing store** (`src/store/processing-store.test.ts`): `setUpdate`, `removeItem`, `clearAll`, `setSubscriptionItemId`
- **WebSocket hook**: mock `WebSocket` via `vi.stubGlobal`, verify:
  - Incoming valid updates are parsed and written to store
  - Invalid payloads / parse failures are ignored and logged (no crash)
  - Cache invalidation runs on `completed` and `failed`
  - Cleanup on unmount closes the WebSocket
  - Reconnection attempts with exponential backoff
  - Current subscription is sent on open and re-sent after reconnect
- **Component integration**:
  - `ItemCard` renders live step label + live status override
  - `ItemDetail` renders live progress percent
  - `ItemDetail` sets/clears subscription intent on mount/unmount

## Verification

```bash
bun run typecheck
bun run lint
bun run test:run
bun run check:all
```

---

## Implementation Details

_Tracked: 2026-02-15_

### Files Changed

| File                                          | Change   | Description                                                                                                                                                                        |
| --------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/types/processing.ts`                     | Created  | `ProcessingUpdate` interface, `ProcessingStatus`/`ProcessingStep` type aliases reusing generated enums, and `isProcessingUpdate` runtime validator                                 |
| `src/store/processing-store.ts`               | Created  | Zustand store with `processingByItemId`, `subscriptionItemId`, `setUpdate`, `removeItem`, `clearProcessingEntries`, `reset`, `setSubscriptionItemId`                               |
| `src/hooks/use-processing-websocket.ts`       | Created  | WebSocket hook with auto-reconnect (capped exponential backoff), payload validation, cache invalidation on terminal states, delayed cleanup of terminal entries, subscription sync |
| `src/store/processing-store.test.ts`          | Created  | Tests for all store actions: `setUpdate`, `removeItem`, `clearProcessingEntries`, `reset`, `setSubscriptionItemId`                                                                 |
| `src/hooks/use-processing-websocket.test.tsx` | Created  | Tests for WebSocket connection, message parsing, invalid payload handling, cache invalidation, reconnect backoff, subscription sync, disconnect cleanup                            |
| `src/App.tsx`                                 | Modified | Added `useProcessingWebSocket()` call at app root (line 20)                                                                                                                        |
| `src/App.test.tsx`                            | Modified | Added mock for `use-processing-websocket` to prevent WebSocket creation in unit tests                                                                                              |
| `src/components/items/ItemCard.tsx`           | Modified | Added processing store selector for live status/step override; passes `liveStatus` and translated `stepLabel` to `ProcessingStatusBadge`                                           |
| `src/components/items/ItemCard.test.tsx`      | Modified | Added test for live processing status rendering from store                                                                                                                         |
| `src/components/items/ItemDetail.tsx`         | Modified | Added processing store selector + subscription lifecycle (`setSubscriptionItemId` on mount/unmount); renders live progress percentage                                              |
| `src/components/items/ItemDetail.test.tsx`    | Modified | Added tests for live progress percent rendering and subscription intent lifecycle                                                                                                  |
| `src/components/items/ItemList.tsx`           | Modified | Passes `onRetryProcessing` callback to `ItemCard` for retry from list view                                                                                                         |
| `src/components/items/ItemList.test.tsx`      | Modified | Added tests for retry from list (success feedback, duplicate prevention)                                                                                                           |
| `locales/en.json`                             | Modified | Added 10 `items.processing.*` translation keys for step labels, progress format, and reconnecting                                                                                  |
| `locales/zh.json`                             | Modified | Added matching Chinese translations for all processing step keys                                                                                                                   |

### Dependencies Added

None — all functionality uses existing dependencies (`zustand`, `@tanstack/react-query`, native `WebSocket` API).

### Acceptance Criteria Status

- [x] WebSocket connection to `/api/ws/processing` (derived from `API_BASE`) is established once at app root (`App.tsx`) — `src/App.tsx:20`, `src/hooks/use-processing-websocket.ts:19-23`
- [x] Processing events update UI in real time without polling — Store updates via `setUpdate` in `use-processing-websocket.ts:130`
- [x] Item list shows live processing status + current step label for processing items — `src/components/items/ItemCard.tsx:84-96`
- [x] Item detail shows live processing status + step label + percentage — `src/components/items/ItemDetail.tsx:156-168`, `262-269`
- [x] Detail route sets WebSocket filter with `{"subscribe": itemId}` and clears it on unmount — `src/components/items/ItemDetail.tsx:69-74`
- [x] Active subscription is re-applied automatically after reconnect — `src/hooks/use-processing-websocket.ts:106`
- [x] On `completed`/`failed` events: invalidate `itemQueryKeys.lists()` and `itemQueryKeys.detail(itemId)` — `src/hooks/use-processing-websocket.ts:134-138`
- [x] `completed`/`failed` live entries are removed from processing store after brief delay — `src/hooks/use-processing-websocket.ts:140-144` (3s delay)
- [x] Failed items continue to show retry affordance in list/detail — `ItemCard.tsx:97-99`, `ItemDetail.tsx:249-259`
- [x] WebSocket reconnects automatically on disconnect with capped exponential backoff — `src/hooks/use-processing-websocket.ts:67-93` (2s, 4s, 8s, 16s, 30s; max 10 attempts)
- [x] Graceful fallback: if WebSocket is unavailable, UI falls back to last-fetched TanStack Query data — Components use `processingUpdate?.status ?? item.processing_status` pattern
- [x] Incoming WebSocket payloads are runtime-validated; malformed/unknown payloads are ignored safely — `src/types/processing.ts:47-66`, `use-processing-websocket.ts:110-127`
- [x] All progress UI strings use i18n keys in `locales/en.json` and `locales/zh.json` — 10 keys added per locale
- [x] WebSocket lifecycle and parse/reconnect failures are logged via `@/lib/logger` — Multiple `logger.debug`, `logger.warn`, `logger.error` calls throughout hook

---

## Learning Report

_Generated: 2026-02-15_

### Summary

Implemented real-time processing progress indicators by connecting the frontend to a backend WebSocket at `/api/ws/processing`. The implementation follows the state management onion pattern: a single Zustand store (`useProcessingStore`) holds transient processing updates, fed by a single WebSocket connection managed via `useProcessingWebSocket` hook mounted once at `App.tsx`. Components (`ItemCard`, `ItemDetail`) consume live state via selector syntax, falling back to TanStack Query data when no live update is available.

- **15 files changed** (5 created, 10 modified)
- **~664 lines added** across implementation and tests
- All 13 acceptance criteria met
- Zero new dependencies added

### Patterns & Decisions

1. **State management onion**: Processing state is transient (not persisted) but shared across `ItemCard` and `ItemDetail` — correctly placed in Zustand per the decision tree. Components access state via selector syntax (`useProcessingStore(state => state.processingByItemId[id])`) to prevent render cascades.

2. **Store action separation**: The store has `clearProcessingEntries` (clears entries but preserves `subscriptionItemId`) and `reset` (clears everything). This allows component-level cleanup without breaking subscription tracking.

3. **Runtime payload validation**: Rather than trusting WebSocket data, `isProcessingUpdate()` validates every field including enum membership via `satisfies readonly ProcessingStatus[]` arrays. This catches backend schema drift at runtime without crashing.

4. **WebSocket lifecycle in a single hook**: The `useProcessingWebSocket` hook manages connection, reconnection, message parsing, subscription sync, cache invalidation, and cleanup timers — all in one place. This keeps the concern isolated from components, which only consume store state.

5. **Reconnect backoff with explicit delay table**: Used `RECONNECT_DELAYS_MS = [2000, 4000, 8000, 16000, 30000]` instead of computing `Math.min(2000 * 2 ** n, 30000)`, making backoff behavior explicit and easily testable.

6. **Disconnect cleanup**: On WebSocket close, non-terminal processing entries are removed from the store (since they're now stale), while terminal entries (`completed`/`failed`) are preserved until their delayed cleanup fires. This prevents showing outdated "processing" indicators after a disconnect.

### Challenges & Solutions

1. **Testing WebSocket behavior**: Used a `MockWebSocket` class with `triggerOpen()`, `triggerMessage()`, `triggerClose()` helpers and `vi.stubGlobal('WebSocket', MockWebSocket)`. This provided full control over connection lifecycle in tests without needing an actual server.

2. **Subscription sync across reconnects**: The subscription state lives in Zustand, so on reconnect the hook reads `useProcessingStore.getState().subscriptionItemId` and re-sends it. A separate `useEffect` on `subscriptionItemId` handles live subscription changes while the socket is open.

3. **Preventing duplicate cleanup timers**: When a terminal status arrives for an item that already has a cleanup timer (e.g., from a rapid status change), the existing timer is cleared before scheduling a new one via `clearCleanupTimer()`.

### Lessons Learned

1. **Store test patterns**: Testing Zustand stores directly via `getState()` and `setState()` is clean and fast — no rendering needed. The `reset()` action in `beforeEach` keeps tests isolated.

2. **`isProcessingUpdate` type guard with enum arrays**: Using `satisfies readonly T[]` ensures the enum arrays stay in sync with the generated OpenAPI types at compile time while enabling runtime membership checks.

3. **Non-string WebSocket messages**: Added an explicit check for `typeof event.data !== 'string'` before JSON parsing — the WebSocket API can deliver `Blob` or `ArrayBuffer` data, which would otherwise cause confusing errors.

### Documentation Impact

- No new patterns requiring documentation — the implementation follows established Zustand store, hook, and selector patterns already documented in `docs/developer/architecture/state-management.md`.
- The `isProcessingUpdate` runtime validator pattern could be documented as a reference for other WebSocket-based features if more are added in the future.
- The `ProcessingUpdate` type in `src/types/processing.ts` demonstrates the pattern for manually defining types not covered by `openapi-typescript` (WebSocket-only models).
