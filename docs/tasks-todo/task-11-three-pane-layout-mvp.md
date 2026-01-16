# Task: Implement Three-Pane Layout for MVP

## Summary
Enhance the existing layout to support the MVP three-pane structure: sidebar, content area, detail panel.

## Acceptance Criteria
- [ ] Left sidebar with:
  - Navigation items (All Items, Conversations)
  - Quick note creation button
  - Collapsible on narrow screens
- [ ] Main content area:
  - Search input at top
  - Scrollable content list/view
  - Responsive width
- [ ] Right detail panel:
  - Shows selected item details
  - Collapsible/hidden when no selection
  - Resizable via drag handle
- [ ] Responsive behavior for different screen sizes
- [ ] Layout state persisted (panel widths, collapsed state)

## Dependencies
- Task 10: Frontend routing

## Technical Notes
- Use existing layout components in `src/components/layout/`
- Store panel state in Zustand ui-store
- Use CSS Grid or Flexbox for layout
- Consider ResizeObserver for responsive behavior

## Phase
Phase 1: Foundation
