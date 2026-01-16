# Task: Create Item Detail View Component

## Summary
Implement the item detail panel that shows full item content and metadata.

## Acceptance Criteria
- [ ] ItemDetail component in right panel
- [ ] Displays when item selected:
  - Title (editable in future)
  - Full content (rendered markdown for md files)
  - Source URL (clickable link for web captures)
  - Content type badge
  - Created/updated timestamps
  - Processing status with progress indicator
- [ ] Empty state when no item selected
- [ ] Loading state while fetching full item
- [ ] Scroll independently of items list

## Dependencies
- Task 8: Items CRUD endpoints (backend)
- Task 11: Three-pane layout
- Task 18: Items list view (for selection)

## Technical Notes
- Fetch full item content only when selected (ItemSummary in list)
- Use TanStack Query with item ID as key
- Consider markdown rendering library (react-markdown)
- Connections section added in Phase 6

## Phase
Phase 1: Foundation
