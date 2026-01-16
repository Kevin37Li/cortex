# Task: Verify and Complete Theme System

## Summary
Ensure theme system (light/dark/system) is fully functional for MVP.

## Acceptance Criteria
- [ ] ThemeProvider properly wraps application
- [ ] Three theme modes work correctly:
  - Light: Explicit light theme
  - Dark: Explicit dark theme
  - System: Follows OS preference
- [ ] Theme persisted across app restarts
- [ ] Theme toggle in preferences works
- [ ] All MVP components respect theme variables
- [ ] No flash of wrong theme on app startup

## Dependencies
- None (can be done in parallel)

## Technical Notes
- Existing ThemeProvider in `src/components/ThemeProvider.tsx`
- Theme variables in `src/theme-variables.css`
- Use Tauri's window theme API if available for system detection
- Store preference via Tauri commands (OS-level persistence)

## Phase
Phase 1: Foundation
