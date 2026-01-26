# Task: Implement Processing Progress Indicators

## Summary

Connect the frontend to the processing status WebSocket to display real-time progress indicators for items being processed. Items in the list and detail view show live updates as they move through processing steps (parsing → chunking → embedding → extracting → completed).

## Acceptance Criteria

- [ ] WebSocket connection to `ws://localhost:8742/api/ws/processing` established on app mount
- [ ] Processing events update item status in real-time (no polling needed)
- [ ] Item list: items being processed show animated progress indicator with current step name
- [ ] Item detail: processing items show step-by-step progress (e.g., "Embedding chunks... 60%")
- [ ] On `completed` event: TanStack Query cache invalidated so item data refreshes with metadata
- [ ] On `failed` event: error state shown with retry option
- [ ] WebSocket reconnects automatically on disconnect (simple retry with backoff)
- [ ] Graceful fallback: if WebSocket unavailable, items still show status from last query fetch
- [ ] All progress text strings use i18n translation keys

## Dependencies

- Task 10: Processing status WebSocket endpoint
- Task 12: TanStack Query service hooks (for cache invalidation)
- Task 13: Item list (display target)
- Task 16: Item detail view (display target)

## Technical Notes

- Per state management decision tree: WebSocket events update TanStack Query cache
- Use `useEffect` for WebSocket lifecycle management
- Consider a custom hook: `useProcessingUpdates()` that manages the WebSocket and returns current processing state
- On receiving a `completed` event, call `queryClient.invalidateQueries({ queryKey: ['items'] })` to refresh data
- WebSocket reconnection: simple retry after 2s, 4s, 8s (exponential backoff, max 30s)
- This is UI-only — all data flows from the WebSocket endpoint created in Task 10

## Custom Hook Pattern

```typescript
// src/hooks/use-processing-updates.ts
export function useProcessingUpdates() {
  const queryClient = useQueryClient()
  const [processingItems, setProcessingItems] = useState<Map<string, ProcessingUpdate>>()

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8742/api/ws/processing')

    ws.onmessage = (event) => {
      const update: ProcessingUpdate = JSON.parse(event.data)
      setProcessingItems(prev => new Map(prev).set(update.item_id, update))

      if (update.status === 'completed' || update.status === 'failed') {
        queryClient.invalidateQueries({ queryKey: ['items'] })
        queryClient.invalidateQueries({ queryKey: ['items', update.item_id] })
      }
    }

    return () => ws.close()
  }, [queryClient])

  return processingItems
}
```

## Translation Keys

Add to `/locales/en.json`:

```json
{
  "processing.step.parsing": "Parsing content...",
  "processing.step.chunking": "Splitting into chunks...",
  "processing.step.embedding": "Generating embeddings...",
  "processing.step.extracting": "Extracting metadata...",
  "processing.step.validating": "Validating results...",
  "processing.step.storing": "Saving results...",
  "processing.progress": "Processing: {step}",
  "processing.reconnecting": "Reconnecting..."
}
```

## Files to Create/Modify

**Create:**

- `src/hooks/use-processing-updates.ts` — WebSocket hook for processing events

**Modify:**

- `src/components/items/ItemList.tsx` — Integrate processing updates
- `src/components/items/ItemCard.tsx` — Show live processing step
- `src/components/items/ItemDetail.tsx` — Show detailed progress
- `src/components/items/ProcessingStatusBadge.tsx` — Accept live step data
- `locales/en.json` — Add translation keys
- `locales/zh-CN.json` — Add Chinese translations

## Verification

```bash
bun run typecheck
bun run lint
bun run test
bun run check:all
```
