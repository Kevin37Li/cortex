# Task: Implement Window State Persistence

## Summary
Save and restore window position, size, and panel states across app restarts.

## Acceptance Criteria
- [ ] Window state saved on close:
  - Position (x, y)
  - Size (width, height)
  - Maximized state
- [ ] Window state restored on app start
- [ ] Panel states saved:
  - Left sidebar width and collapsed state
  - Right panel width and visibility
- [ ] Graceful handling of invalid saved state (e.g., off-screen position)
- [ ] State persisted in user data directory

## Dependencies
- Task 11: Three-pane layout (for panel states)

## Technical Notes
- Use Tauri's window APIs for position/size
- Store state via Tauri commands or direct file write
- Validate restored state against current screen bounds
- Consider debouncing save operations during resize

## Phase
Phase 1: Foundation
