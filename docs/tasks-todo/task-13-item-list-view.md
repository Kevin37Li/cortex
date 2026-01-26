# Task: Implement Item List View with Processing Status Indicators

## Summary

Build the item list UI component that displays all saved items with their processing status. Items show title, content type, creation date, and a status badge (pending/processing/completed/failed). Uses TanStack Query for data fetching and supports click-through to item detail.

## Acceptance Criteria

- [ ] `ItemList` component displays paginated items from the backend
- [ ] Each item row shows: title, content type icon/badge, creation date (relative), processing status indicator
- [ ] Processing status badges: `pending` (gray), `processing` (blue/animated), `completed` (green), `failed` (red with retry option)
- [ ] Empty state: message shown when no items exist with a prompt to create a note
- [ ] Loading state: skeleton loaders while fetching
- [ ] Error state: error message with retry button
- [ ] Click on item navigates to item detail route (`/items/{id}`)
- [ ] Uses `useItems()` hook from `src/services/items.ts`
- [ ] Pagination: load more or infinite scroll (choose simplest for MVP)
- [ ] All user-facing strings use i18n translation keys

## Dependencies

- Task 12: TanStack Query service hooks (`useItems()`)
- Phase 1: Layout shell (`MainWindowShell`), routing (`/items` route), UI components (shadcn/ui)
- Phase 1: i18n setup

## Technical Notes

- Per state management decision tree: item list data uses TanStack Query (persistent data from backend)
- The route `src/routes/items/index.tsx` already exists as a placeholder — implement the actual content
- Use shadcn/ui components: `Card`, `Badge`, `Skeleton`, `ScrollArea`
- Follow existing component patterns (check `MainWindowShell.tsx` for layout context)
- Processing status indicator for `processing` state should have subtle animation (pulse or spinner)
- Date formatting: use relative time ("2 hours ago") with `date-fns` or Intl.RelativeTimeFormat
- Per AGENTS.md: no manual `useMemo`/`useCallback` — React Compiler handles this

## Component Structure

```
src/routes/items/index.tsx         — Route component using ItemList
src/components/items/
  ├── ItemList.tsx                 — List container with query
  ├── ItemCard.tsx                 — Single item row/card
  └── ProcessingStatusBadge.tsx    — Status indicator component
```

## Translation Keys

Add to `/locales/en.json`:

```json
{
  "items.list.title": "All Items",
  "items.list.empty": "No items yet",
  "items.list.emptyDescription": "Create a note or save a web page to get started",
  "items.list.loading": "Loading items...",
  "items.list.error": "Failed to load items",
  "items.list.retry": "Retry",
  "items.status.pending": "Pending",
  "items.status.processing": "Processing",
  "items.status.completed": "Completed",
  "items.status.failed": "Failed",
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

**Modify:**

- `src/routes/items/index.tsx` — Use `ItemList` component
- `locales/en.json` — Add translation keys
- `locales/zh-CN.json` — Add Chinese translations

## Verification

```bash
bun run typecheck
bun run lint
bun run test
bun run check:all
```
