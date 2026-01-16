# Task: Set Up Frontend Routing for MVP Screens

## Summary
Configure React Router with routes for MVP screens (items list, item detail, conversations).

## Acceptance Criteria
- [ ] React Router configured in App.tsx
- [ ] Routes defined:
  - `/` - Redirects to /items
  - `/items` - Items list view
  - `/items/:id` - Item detail view
  - `/conversations` - Conversations list
  - `/conversations/:id` - Chat view
  - `/settings` - Settings page
- [ ] Navigation between routes working
- [ ] 404 handling for unknown routes
- [ ] URL reflects current view state

## Dependencies
- None (frontend already exists)

## Technical Notes
- Use React Router v6+ patterns
- Consider lazy loading for larger route components
- Sidebar navigation should update based on current route
- Follow patterns in `docs/developer/architecture/architecture-guide.md`

## Phase
Phase 1: Foundation
