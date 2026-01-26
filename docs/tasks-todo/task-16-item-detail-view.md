# Task: Implement Item Detail View

## Summary

Build the item detail view that displays the full content, metadata, and processing status of a single item. Shown when a user clicks an item from the list. Displays the item's title, content (with basic formatting), content type, source URL, creation date, processing status, and extracted metadata (summary, concepts, entities) once processing is complete.

## Acceptance Criteria

- [ ] `ItemDetail` component displays full item data from `useItem(id)` hook
- [ ] Header: title, content type badge, creation date
- [ ] Content section: full item content with basic text formatting (paragraphs preserved)
- [ ] Source URL: clickable link if present (opens in default browser)
- [ ] Processing status section: status badge, show metadata when completed
- [ ] Metadata section (when `processing_status === 'completed'`): summary, concept tags, entity tags
- [ ] Failed state: error message with retry button (calls retry endpoint)
- [ ] Processing state: animated indicator with current step (if WebSocket connected)
- [ ] Loading state: skeleton loader
- [ ] 404 state: "Item not found" message
- [ ] Back navigation to item list
- [ ] All user-facing strings use i18n translation keys

## Dependencies

- Task 12: TanStack Query service hooks (`useItem()`)
- Task 13: Item list (navigation source)
- Phase 1: Routing (`/items/{id}` route exists as placeholder), UI components

## Technical Notes

- The route `src/routes/items/$id.tsx` already exists as a placeholder — implement the actual content
- Use `useItem(id)` from `src/services/items.ts` for data fetching
- Metadata is stored in item's `metadata` JSON field — shape depends on extraction service output
- For source URLs, use Tauri's shell API to open in default browser: `open(url)`
- Use shadcn/ui components: `Card`, `Badge`, `Separator`, `ScrollArea`, `Skeleton`
- Per state management: item data uses TanStack Query (persistent data from backend)

## Component Structure

```
src/routes/items/$id.tsx              — Route component
src/components/items/
  ├── ItemDetail.tsx                  — Main detail view
  ├── ItemMetadataSection.tsx         — Summary, concepts, entities display
  └── ProcessingStatusBadge.tsx       — (reuse from task 13)
```

## Translation Keys

Add to `/locales/en.json`:

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
  "items.detail.processingFailed": "Processing failed"
}
```

## Files to Create/Modify

**Create:**

- `src/components/items/ItemDetail.tsx`
- `src/components/items/ItemMetadataSection.tsx`

**Modify:**

- `src/routes/items/$id.tsx` — Use `ItemDetail` component
- `locales/en.json` — Add translation keys
- `locales/zh-CN.json` — Add Chinese translations

## Verification

```bash
bun run typecheck
bun run lint
bun run test
bun run check:all
```
