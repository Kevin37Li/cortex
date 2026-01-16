# Task: Connect Frontend to Backend Health Check

## Summary
Establish frontend-to-backend communication and verify connectivity via health endpoints.

## Acceptance Criteria
- [ ] HTTP client configured for backend communication (localhost:8742)
- [ ] TanStack Query setup for data fetching
- [ ] Health check query that polls `/api/health`
- [ ] Status indicator showing backend connection state:
  - Connected: Backend responding
  - Disconnected: Backend unreachable
- [ ] Automatic reconnection attempts when disconnected
- [ ] Error boundary for backend communication failures

## Dependencies
- Task 7: Health check endpoint (backend)
- Task 11: Three-pane layout (for status indicator placement)

## Technical Notes
- Use fetch or axios for HTTP client
- Configure TanStack Query with appropriate defaults (stale time, retry)
- Status indicator could be in titlebar or sidebar footer
- Consider WebSocket for real-time status (future enhancement)
- Follow patterns in `docs/developer/architecture/state-management.md`

## Phase
Phase 1: Foundation
