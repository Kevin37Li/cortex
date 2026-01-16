# Task: Create Items List View Component

## Summary
Implement the items list view that displays saved items in the main content area.

## Acceptance Criteria
- [ ] ItemsList component showing all items
- [ ] Each item row displays:
  - Title
  - Content type icon (note, webpage, markdown)
  - Created date (relative: "2 hours ago")
  - Processing status indicator
- [ ] Empty state when no items exist
- [ ] Loading state while fetching
- [ ] Error state if fetch fails
- [ ] Click item to select (shows in detail panel)
- [ ] Keyboard navigation (up/down arrows)

## Dependencies
- Task 8: Items CRUD endpoints (backend)
- Task 11: Three-pane layout
- Task 16: Frontend-backend integration

## Technical Notes
- Use TanStack Query for data fetching
- Virtualize list if performance issues (react-window)
- Use shadcn/ui components for consistent styling
- Item selection state in Zustand ui-store

## Phase
Phase 1: Foundation
